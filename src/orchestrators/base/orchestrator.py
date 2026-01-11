"""Base orchestrator class implementing Agno framework patterns."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging
from enum import Enum

from .agent import BaseAgent, AgentResponse
from ...shared.llm import (
    LLMFallbackChain,
    Message,
    FallbackResult,
    LLMError,
    SETTINGS as LLM_SETTINGS,
)


logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Types of tasks that can be processed."""
    RESEARCH = "research"
    WRITE = "write"
    GRAPHICS = "graphics"
    SOCIAL = "social"
    ANALYZE = "analyze"
    UNKNOWN = "unknown"


@dataclass
class ConversationMessage:
    """A single message in conversation history."""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationMemory:
    """Manages conversation history and context."""
    messages: List[ConversationMessage] = field(default_factory=list)
    max_messages: int = 100
    context: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to the conversation history."""
        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)

        # Trim if exceeds max
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history as list of dicts."""
        messages = self.messages[-limit:] if limit else self.messages
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            }
            for msg in messages
        ]

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()
        self.context.clear()

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value."""
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return self.context.get(key, default)


@dataclass
class OrchestratorRequest:
    """Request to the orchestrator."""
    task: str
    content: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorResponse:
    """Response from the orchestrator."""
    success: bool
    result: Any
    agent_used: Optional[str] = None
    task_type: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class ToolExecutor:
    """Framework for executing agent tools."""

    def __init__(self):
        self._tool_registry: Dict[str, callable] = {}
        self._execution_history: List[Dict[str, Any]] = []

    def register_tool(self, name: str, func: callable, description: str = "") -> None:
        """Register a tool for execution."""
        self._tool_registry[name] = {
            "func": func,
            "description": description
        }

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self._tool_registry.keys())

    async def execute(self, tool_name: str, **kwargs) -> Any:
        """Execute a registered tool."""
        if tool_name not in self._tool_registry:
            raise ValueError(f"Tool '{tool_name}' not found in registry")

        tool_info = self._tool_registry[tool_name]
        func = tool_info["func"]

        start_time = datetime.utcnow()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(**kwargs)
            else:
                result = func(**kwargs)

            execution_record = {
                "tool": tool_name,
                "args": kwargs,
                "result": result,
                "success": True,
                "timestamp": start_time.isoformat(),
                "duration": (datetime.utcnow() - start_time).total_seconds()
            }
            self._execution_history.append(execution_record)
            return result

        except Exception as e:
            execution_record = {
                "tool": tool_name,
                "args": kwargs,
                "error": str(e),
                "success": False,
                "timestamp": start_time.isoformat(),
                "duration": (datetime.utcnow() - start_time).total_seconds()
            }
            self._execution_history.append(execution_record)
            raise


class BaseOrchestrator(ABC):
    """
    Abstract base class for all orchestrators.

    Implements the Agno framework pattern for multi-agent orchestration:
    - Agent registry and lifecycle management
    - Request routing and delegation
    - Memory management across sessions
    - Tool execution framework
    - Uses LLM fallback chain: GLM-4 -> Kimi K2 -> GPT-4o mini
    """

    # Default model configuration (used as fallback if LLM module fails)
    DEFAULT_MODEL = "glm-4"
    DEFAULT_MODEL_CONFIG = {
        "temperature": LLM_SETTINGS.default_temperature,
        "max_tokens": LLM_SETTINGS.default_max_tokens,
        "top_p": LLM_SETTINGS.default_top_p,
    }

    def __init__(
        self,
        model: str = None,
        model_config: Optional[Dict[str, Any]] = None,
        max_memory_messages: int = 100,
        llm_chain: Optional[LLMFallbackChain] = None,
    ):
        self.model = model or self.DEFAULT_MODEL
        self.model_config = {**self.DEFAULT_MODEL_CONFIG, **(model_config or {})}

        # LLM fallback chain
        self._llm_chain = llm_chain
        self._owns_llm_chain = llm_chain is None  # Track if we created it

        # Agent registry
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}

        # Memory management
        self._sessions: Dict[str, ConversationMemory] = {}
        self._max_memory_messages = max_memory_messages

        # Tool execution
        self.tool_executor = ToolExecutor()

        # Track last LLM provider used
        self._last_llm_provider: Optional[str] = None
        self._last_llm_model: Optional[str] = None

        # Initialize orchestrator-specific components
        self._initialize()

    async def get_llm_chain(self) -> LLMFallbackChain:
        """Get or create the LLM fallback chain."""
        if self._llm_chain is None:
            self._llm_chain = LLMFallbackChain()
            self._owns_llm_chain = True
        return self._llm_chain

    async def llm_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> FallbackResult:
        """
        Send a chat completion request using the LLM fallback chain.

        This method handles the fallback logic automatically:
        1. Try GLM-4 (Zhipu AI) - Primary
        2. Try Kimi K2 (Moonshot AI) - Fallback 1
        3. Try GPT-4o mini (OpenAI) - Fallback 2

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (optional)
            max_tokens: Max tokens to generate (optional)
            **kwargs: Additional provider-specific parameters

        Returns:
            FallbackResult with response and metadata about which provider was used
        """
        chain = await self.get_llm_chain()

        # Convert dict messages to Message objects
        msg_objects = [
            Message(role=m["role"], content=m["content"])
            for m in messages
        ]

        result = await chain.chat(
            messages=msg_objects,
            temperature=temperature or self.model_config.get("temperature"),
            max_tokens=max_tokens or self.model_config.get("max_tokens"),
            **kwargs
        )

        # Track which provider was used
        self._last_llm_provider = result.provider_used
        self._last_llm_model = result.model_used

        logger.info(
            f"LLM request completed via {result.provider_used}/{result.model_used} "
            f"(attempts: {result.attempts}, time: {result.total_time:.2f}s)"
        )

        return result

    async def llm_simple_chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Simplified chat interface that returns just the response content.

        Args:
            user_message: The user's message
            system_prompt: Optional system prompt
            **kwargs: Additional parameters passed to llm_chat

        Returns:
            The response content as a string
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        result = await self.llm_chat(messages, **kwargs)
        return result.response.content

    def get_last_llm_info(self) -> Dict[str, Optional[str]]:
        """Get information about the last LLM provider used."""
        return {
            "provider": self._last_llm_provider,
            "model": self._last_llm_model,
        }

    async def close(self) -> None:
        """Clean up resources including LLM connections."""
        if self._owns_llm_chain and self._llm_chain is not None:
            await self._llm_chain.close()
            self._llm_chain = None

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize orchestrator-specific components. Override in subclasses."""
        pass

    @abstractmethod
    async def _analyze_task(self, request: OrchestratorRequest) -> TaskType:
        """Analyze the request to determine task type. Override in subclasses."""
        pass

    @abstractmethod
    async def _route_to_agent(self, task_type: TaskType, request: OrchestratorRequest) -> str:
        """Determine which agent should handle the request. Override in subclasses."""
        pass

    def register_agent_class(self, name: str, agent_class: Type[BaseAgent]) -> None:
        """Register an agent class for lazy instantiation."""
        self._agent_classes[name] = agent_class
        logger.info(f"Registered agent class: {name}")

    def get_agent(self, name: str) -> BaseAgent:
        """Get or create an agent instance."""
        if name not in self._agents:
            if name not in self._agent_classes:
                raise ValueError(f"Agent '{name}' not registered")

            agent_class = self._agent_classes[name]
            self._agents[name] = agent_class(
                model=self.model,
                model_config=self.model_config
            )
            logger.info(f"Instantiated agent: {name}")

        return self._agents[name]

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agent_classes.keys())

    def get_or_create_session(self, session_id: str) -> ConversationMemory:
        """Get or create a conversation memory for a session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationMemory(
                max_messages=self._max_memory_messages
            )
        return self._sessions[session_id]

    def clear_session(self, session_id: str) -> None:
        """Clear a session's memory."""
        if session_id in self._sessions:
            self._sessions[session_id].clear()

    def delete_session(self, session_id: str) -> None:
        """Delete a session entirely."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    async def process(self, request: OrchestratorRequest) -> OrchestratorResponse:
        """
        Process a request through the orchestrator.

        This is the main entry point for request handling:
        1. Analyze the task to determine type
        2. Route to appropriate agent
        3. Execute agent with context
        4. Update memory and return response
        """
        start_time = datetime.utcnow()
        errors: List[str] = []

        try:
            # Get or create session memory
            session_id = request.session_id or "default"
            memory = self.get_or_create_session(session_id)

            # Add user message to memory
            memory.add_message(
                role="user",
                content=request.content,
                metadata={"task": request.task, "parameters": request.parameters}
            )

            # Analyze task type
            task_type = await self._analyze_task(request)
            logger.info(f"Task analyzed as: {task_type.value}")

            # Route to appropriate agent
            agent_name = await self._route_to_agent(task_type, request)
            logger.info(f"Routing to agent: {agent_name}")

            # Get agent and execute
            agent = self.get_agent(agent_name)

            # Build context from memory
            context = {
                "history": memory.get_history(limit=10),
                "session_context": memory.context,
                **request.parameters
            }

            # Execute agent
            agent_response = await agent.execute(
                task=request.task,
                content=request.content,
                context=context
            )

            # Add assistant response to memory
            memory.add_message(
                role="assistant",
                content=str(agent_response.content),
                metadata={
                    "agent": agent_name,
                    "task_type": task_type.value,
                    "tools_used": agent_response.tools_used
                }
            )

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Get LLM info for metadata
            llm_info = self.get_last_llm_info()

            return OrchestratorResponse(
                success=True,
                result=agent_response.content,
                agent_used=agent_name,
                task_type=task_type.value,
                execution_time=execution_time,
                metadata={
                    "tools_used": agent_response.tools_used,
                    "model": llm_info.get("model") or self.model,
                    "llm_provider": llm_info.get("provider"),
                    "session_id": session_id
                }
            )

        except LLMError as e:
            logger.error(f"LLM error processing request: {e}")
            errors.append(f"LLM Error ({e.provider}/{e.model}): {e.message}")
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return OrchestratorResponse(
                success=False,
                result=None,
                execution_time=execution_time,
                errors=errors,
                metadata={"error_type": "llm_error", "provider": e.provider}
            )

        except Exception as e:
            logger.exception(f"Error processing request: {e}")
            errors.append(str(e))
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return OrchestratorResponse(
                success=False,
                result=None,
                execution_time=execution_time,
                errors=errors
            )

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool through the tool executor."""
        return await self.tool_executor.execute(tool_name, **kwargs)

    def register_tool(self, name: str, func: callable, description: str = "") -> None:
        """Register a tool with the orchestrator."""
        self.tool_executor.register_tool(name, func, description)
