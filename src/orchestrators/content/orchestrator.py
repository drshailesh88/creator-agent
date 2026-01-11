"""Content Orchestrator - Routes content creation requests to specialized agents."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import logging
import re

from ..base.orchestrator import (
    BaseOrchestrator,
    OrchestratorRequest,
    TaskType,
    ConversationMemory
)
from .agents.researcher import ResearcherAgent
from .agents.writer import WriterAgent
from .agents.graphics import GraphicsAgent
from .agents.social import SocialAgent


logger = logging.getLogger(__name__)


@dataclass
class ContentMemory(ConversationMemory):
    """Extended memory for content-specific context."""

    # Content-specific context
    research_cache: Dict[str, Any] = field(default_factory=dict)
    content_drafts: List[Dict[str, Any]] = field(default_factory=list)
    generated_assets: List[Dict[str, Any]] = field(default_factory=list)

    def cache_research(self, query: str, results: Any) -> None:
        """Cache research results for reuse."""
        self.research_cache[query] = {
            "results": results,
            "timestamp": None  # Will be set by caller
        }

    def get_cached_research(self, query: str) -> Optional[Any]:
        """Get cached research if available."""
        return self.research_cache.get(query)

    def add_draft(self, draft: Dict[str, Any]) -> None:
        """Add a content draft."""
        self.content_drafts.append(draft)

    def add_asset(self, asset: Dict[str, Any]) -> None:
        """Add a generated asset."""
        self.generated_assets.append(asset)


class ContentOrchestrator(BaseOrchestrator):
    """
    Content Orchestrator for managing content creation workflows.

    Routes requests to specialized agents:
    - Researcher: Data gathering, research, summarization
    - Writer: Content creation in various formats
    - Graphics: Visual content generation prompts
    - Social: Social media optimization
    """

    # Keywords for task classification
    RESEARCH_KEYWORDS = [
        "research", "find", "search", "lookup", "investigate", "gather",
        "summarize", "analyze", "study", "explore", "discover", "pubmed",
        "papers", "articles", "data", "statistics", "facts"
    ]

    WRITE_KEYWORDS = [
        "write", "create", "draft", "compose", "author", "blog", "article",
        "newsletter", "post", "essay", "content", "copy", "script",
        "linkedin", "academic", "twitter thread"
    ]

    GRAPHICS_KEYWORDS = [
        "graphic", "image", "infographic", "chart", "diagram", "visual",
        "illustration", "picture", "design", "banner", "thumbnail",
        "generate image", "create visual", "dall-e", "midjourney"
    ]

    SOCIAL_KEYWORDS = [
        "social", "twitter", "linkedin", "facebook", "instagram", "tiktok",
        "hashtag", "engagement", "viral", "platform", "share", "retweet",
        "post to", "schedule", "optimize for"
    ]

    def _initialize(self) -> None:
        """Initialize content orchestrator components."""
        # Register agent classes
        self.register_agent_class("researcher", ResearcherAgent)
        self.register_agent_class("writer", WriterAgent)
        self.register_agent_class("graphics", GraphicsAgent)
        self.register_agent_class("social", SocialAgent)

        # Override session creation to use ContentMemory
        self._content_sessions: Dict[str, ContentMemory] = {}

        logger.info("Content Orchestrator initialized")

    def get_or_create_session(self, session_id: str) -> ContentMemory:
        """Get or create a content-specific memory for a session."""
        if session_id not in self._content_sessions:
            self._content_sessions[session_id] = ContentMemory(
                max_messages=self._max_memory_messages
            )
        return self._content_sessions[session_id]

    async def _analyze_task(self, request: OrchestratorRequest) -> TaskType:
        """
        Analyze the request to determine task type.

        Uses keyword matching and context analysis to classify the request.
        """
        content_lower = request.content.lower()
        task_lower = request.task.lower()
        combined = f"{task_lower} {content_lower}"

        # Check explicit task type first
        if request.task in ["research", "researcher"]:
            return TaskType.RESEARCH
        if request.task in ["write", "writer", "writing"]:
            return TaskType.WRITE
        if request.task in ["graphics", "graphic", "image", "visual"]:
            return TaskType.GRAPHICS
        if request.task in ["social", "social_media"]:
            return TaskType.SOCIAL

        # Score-based classification
        scores = {
            TaskType.RESEARCH: self._score_keywords(combined, self.RESEARCH_KEYWORDS),
            TaskType.WRITE: self._score_keywords(combined, self.WRITE_KEYWORDS),
            TaskType.GRAPHICS: self._score_keywords(combined, self.GRAPHICS_KEYWORDS),
            TaskType.SOCIAL: self._score_keywords(combined, self.SOCIAL_KEYWORDS),
        }

        # Get highest scoring task type
        max_score = max(scores.values())
        if max_score > 0:
            for task_type, score in scores.items():
                if score == max_score:
                    return task_type

        # Default to write for content creation
        return TaskType.WRITE

    def _score_keywords(self, text: str, keywords: List[str]) -> int:
        """Score text based on keyword matches."""
        score = 0
        for keyword in keywords:
            if keyword in text:
                score += 1
                # Bonus for exact word match
                if re.search(rf'\b{keyword}\b', text):
                    score += 1
        return score

    async def _route_to_agent(self, task_type: TaskType, request: OrchestratorRequest) -> str:
        """
        Determine which agent should handle the request.

        Maps task types to agent names and handles special cases.
        """
        # Direct mapping
        agent_map = {
            TaskType.RESEARCH: "researcher",
            TaskType.WRITE: "writer",
            TaskType.GRAPHICS: "graphics",
            TaskType.SOCIAL: "social",
        }

        agent_name = agent_map.get(task_type, "writer")

        # Check for compound tasks that might need multiple agents
        # For now, we route to the primary agent
        # Future: implement agent chaining

        return agent_name

    async def research_and_write(
        self,
        topic: str,
        output_format: str = "blog",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compound task: Research a topic and then write about it.

        This demonstrates agent chaining within the orchestrator.
        """
        session_id = session_id or "compound-task"
        memory = self.get_or_create_session(session_id)

        # Step 1: Research
        research_request = OrchestratorRequest(
            task="research",
            content=f"Research the topic: {topic}",
            parameters={"sources": ["pubmed", "web"]},
            session_id=session_id
        )

        research_response = await self.process(research_request)

        if not research_response.success:
            return {
                "success": False,
                "error": "Research step failed",
                "details": research_response.errors
            }

        # Cache research results
        memory.cache_research(topic, research_response.result)

        # Step 2: Write based on research
        write_request = OrchestratorRequest(
            task="write",
            content=f"Write a {output_format} about: {topic}",
            parameters={
                "format": output_format,
                "research_context": research_response.result
            },
            session_id=session_id
        )

        write_response = await self.process(write_request)

        if write_response.success:
            memory.add_draft({
                "topic": topic,
                "format": output_format,
                "content": write_response.result
            })

        return {
            "success": write_response.success,
            "research": research_response.result,
            "content": write_response.result,
            "execution_time": research_response.execution_time + write_response.execution_time
        }

    async def create_content_package(
        self,
        topic: str,
        platforms: List[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a complete content package for multiple platforms.

        Includes research, main content, graphics prompts, and social posts.
        """
        platforms = platforms or ["blog", "twitter", "linkedin"]
        session_id = session_id or "content-package"
        memory = self.get_or_create_session(session_id)

        results = {
            "topic": topic,
            "platforms": {},
            "graphics": None,
            "success": True
        }

        # Step 1: Research
        research_request = OrchestratorRequest(
            task="research",
            content=f"Research the topic thoroughly: {topic}",
            session_id=session_id
        )
        research_response = await self.process(research_request)
        results["research"] = research_response.result

        # Step 2: Create content for each platform
        for platform in platforms:
            if platform == "blog":
                write_request = OrchestratorRequest(
                    task="write",
                    content=f"Write a comprehensive blog post about: {topic}",
                    parameters={"format": "blog", "research_context": research_response.result},
                    session_id=session_id
                )
            elif platform == "twitter":
                write_request = OrchestratorRequest(
                    task="write",
                    content=f"Create a Twitter thread about: {topic}",
                    parameters={"format": "twitter", "research_context": research_response.result},
                    session_id=session_id
                )
            elif platform == "linkedin":
                write_request = OrchestratorRequest(
                    task="write",
                    content=f"Write a LinkedIn post about: {topic}",
                    parameters={"format": "linkedin", "research_context": research_response.result},
                    session_id=session_id
                )
            else:
                continue

            response = await self.process(write_request)
            results["platforms"][platform] = response.result

        # Step 3: Generate graphics prompts
        graphics_request = OrchestratorRequest(
            task="graphics",
            content=f"Create visual content prompts for: {topic}",
            parameters={"type": "infographic"},
            session_id=session_id
        )
        graphics_response = await self.process(graphics_request)
        results["graphics"] = graphics_response.result

        return results
