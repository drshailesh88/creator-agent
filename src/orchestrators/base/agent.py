"""Base agent class implementing Agno framework patterns."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging
from enum import Enum


logger = logging.getLogger(__name__)


@dataclass
class AgentTool:
    """Definition of a tool available to an agent."""
    name: str
    description: str
    func: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_params: List[str] = field(default_factory=list)

    def to_schema(self) -> Dict[str, Any]:
        """Convert tool to schema format for LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required_params
            }
        }


@dataclass
class AgentResponse:
    """Response from an agent execution."""
    content: Any
    tools_used: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_output: Optional[str] = None


class ResponseFormat(str, Enum):
    """Output format types."""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"


class PromptTemplate:
    """Template for agent prompts with variable substitution."""

    def __init__(self, template: str):
        self.template = template

    def format(self, **kwargs) -> str:
        """Format the template with provided variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            # Return template with missing vars as placeholders
            result = self.template
            for key, value in kwargs.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Implements the Agno framework pattern for agent design:
    - Tool registration and execution
    - Prompt template management
    - Response formatting
    - Context handling
    """

    # Default system prompt - override in subclasses
    SYSTEM_PROMPT = """You are a helpful AI assistant.
Complete the requested task accurately and thoroughly.
Use the available tools when necessary to accomplish the task."""

    def __init__(
        self,
        model: str = "glm-4",
        model_config: Optional[Dict[str, Any]] = None,
        response_format: ResponseFormat = ResponseFormat.TEXT
    ):
        self.model = model
        self.model_config = model_config or {}
        self.response_format = response_format

        # Tool registry
        self._tools: Dict[str, AgentTool] = {}

        # Prompt templates
        self._prompt_templates: Dict[str, PromptTemplate] = {}

        # Initialize agent-specific components
        self._initialize_tools()
        self._initialize_prompts()

    @abstractmethod
    def _initialize_tools(self) -> None:
        """Initialize agent-specific tools. Override in subclasses."""
        pass

    @abstractmethod
    def _initialize_prompts(self) -> None:
        """Initialize agent-specific prompt templates. Override in subclasses."""
        pass

    @abstractmethod
    async def _process(
        self,
        task: str,
        content: str,
        context: Dict[str, Any]
    ) -> Any:
        """Process the task. Override in subclasses with specific logic."""
        pass

    def register_tool(self, tool: AgentTool) -> None:
        """Register a tool with the agent."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[AgentTool]:
        """Get a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get schema for all tools (for LLM function calling)."""
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute_tool(self, name: str, **kwargs) -> Any:
        """Execute a registered tool."""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")

        # Validate required parameters
        for param in tool.required_params:
            if param not in kwargs:
                raise ValueError(f"Missing required parameter: {param}")

        # Execute tool
        if asyncio.iscoroutinefunction(tool.func):
            return await tool.func(**kwargs)
        return tool.func(**kwargs)

    def register_prompt_template(self, name: str, template: str) -> None:
        """Register a prompt template."""
        self._prompt_templates[name] = PromptTemplate(template)

    def get_prompt(self, name: str, **kwargs) -> str:
        """Get a formatted prompt by template name."""
        if name not in self._prompt_templates:
            raise ValueError(f"Prompt template '{name}' not found")
        return self._prompt_templates[name].format(**kwargs)

    def format_response(self, content: Any) -> str:
        """Format response according to agent's response format."""
        if self.response_format == ResponseFormat.JSON:
            import json
            if isinstance(content, str):
                return content
            return json.dumps(content, indent=2, ensure_ascii=False)

        elif self.response_format == ResponseFormat.MARKDOWN:
            if isinstance(content, dict):
                lines = []
                for key, value in content.items():
                    lines.append(f"## {key}\n{value}\n")
                return "\n".join(lines)
            return str(content)

        elif self.response_format == ResponseFormat.HTML:
            if isinstance(content, dict):
                lines = ["<div>"]
                for key, value in content.items():
                    lines.append(f"<h2>{key}</h2><p>{value}</p>")
                lines.append("</div>")
                return "\n".join(lines)
            return f"<p>{content}</p>"

        # Default: TEXT
        return str(content)

    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        return self.SYSTEM_PROMPT

    async def execute(
        self,
        task: str,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Execute the agent on a task.

        Args:
            task: The type of task to perform
            content: The main content/input for the task
            context: Additional context including history, parameters, etc.

        Returns:
            AgentResponse with the result
        """
        start_time = datetime.utcnow()
        tools_used: List[str] = []
        context = context or {}

        try:
            # Process the task
            result = await self._process(task, content, context)

            # Track which tools were used (if implemented by subclass)
            if hasattr(self, '_last_tools_used'):
                tools_used = self._last_tools_used

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return AgentResponse(
                content=self.format_response(result),
                tools_used=tools_used,
                execution_time=execution_time,
                metadata={
                    "task": task,
                    "model": self.model,
                    "response_format": self.response_format.value
                },
                raw_output=str(result)
            )

        except Exception as e:
            logger.exception(f"Error executing agent: {e}")
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return AgentResponse(
                content=f"Error: {str(e)}",
                tools_used=tools_used,
                execution_time=execution_time,
                metadata={
                    "task": task,
                    "error": str(e)
                }
            )

    def _build_messages(
        self,
        task: str,
        content: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Build message list for LLM call."""
        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ]

        # Add conversation history if available
        history = context.get("history", [])
        for msg in history[-5:]:  # Last 5 messages for context
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Add current request
        user_message = f"Task: {task}\n\nContent: {content}"
        messages.append({"role": "user", "content": user_message})

        return messages
