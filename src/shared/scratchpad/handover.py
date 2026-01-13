"""
Handover management for AI context continuity.

This module provides the key infrastructure for AI agents to "hand over" work
when the context window is full. It preserves ALL important information while
compressing to fit the next context window.

The HandoverManager:
1. Saves all current notes
2. Summarizes notes to compress information
3. Records exact position in current document
4. Creates a handover state that can be used to resume work

Usage:
    from shared.scratchpad import Scratchpad, HandoverManager, HandoverState

    # Create a scratchpad and work on a task
    scratchpad = Scratchpad(session_id="research-123")
    await scratchpad.initialize()
    session = await scratchpad.start_session(task="Research topic X", documents=[...])

    # When context is full, prepare handover
    manager = HandoverManager(scratchpad)
    state = await manager.prepare_handover()
    prompt = await manager.create_handover_prompt(state)

    # Use prompt in the next context to resume
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .models import Session, Note, Document
from .prompts import (
    HANDOVER_PROMPT,
    NOTES_SUMMARIZATION_PROMPT,
    KEY_FINDINGS_EXTRACTION_PROMPT,
)

if TYPE_CHECKING:
    from .scratchpad import Scratchpad


logger = logging.getLogger(__name__)


@dataclass
class HandoverState:
    """
    Complete state for handing over work to a new context.

    This dataclass captures everything needed to resume work in a new
    AI context window. It is designed to be serializable and to fit
    within a reasonable portion of the new context window.

    Attributes:
        session_id: Unique identifier for the session
        task: Description of the task being performed
        documents_completed: List of document paths/titles that are done
        documents_pending: List of document paths/titles still to process
        current_document: The document currently being processed
        current_position: Human-readable position (e.g., "page 15 of 30, paragraph 3")
        notes_summary: Condensed summary of all notes taken so far
        key_findings: List of the most important points discovered
        citations_collected: List of citations in proper format
        next_action: Clear instruction for what to do next
        context_refreshes: Number of times handover has been called
        created_at: Timestamp when this handover state was created
        metadata: Additional context-specific information
    """
    session_id: str
    task: str
    documents_completed: List[str] = field(default_factory=list)
    documents_pending: List[str] = field(default_factory=list)
    current_document: Optional[str] = None
    current_position: str = ""
    notes_summary: str = ""
    key_findings: List[str] = field(default_factory=list)
    citations_collected: List[str] = field(default_factory=list)
    next_action: str = ""
    context_refreshes: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "task": self.task,
            "documents_completed": self.documents_completed,
            "documents_pending": self.documents_pending,
            "current_document": self.current_document,
            "current_position": self.current_position,
            "notes_summary": self.notes_summary,
            "key_findings": self.key_findings,
            "citations_collected": self.citations_collected,
            "next_action": self.next_action,
            "context_refreshes": self.context_refreshes,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HandoverState":
        """Create a HandoverState from a dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()

        return cls(
            session_id=data.get("session_id", ""),
            task=data.get("task", ""),
            documents_completed=data.get("documents_completed", []),
            documents_pending=data.get("documents_pending", []),
            current_document=data.get("current_document"),
            current_position=data.get("current_position", ""),
            notes_summary=data.get("notes_summary", ""),
            key_findings=data.get("key_findings", []),
            citations_collected=data.get("citations_collected", []),
            next_action=data.get("next_action", ""),
            context_refreshes=data.get("context_refreshes", 0),
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )

    @property
    def progress_summary(self) -> str:
        """Get a brief progress summary."""
        total = len(self.documents_completed) + len(self.documents_pending)
        if self.current_document:
            total += 1
        completed = len(self.documents_completed)
        return f"{completed}/{total} documents completed"

    @property
    def estimated_completion(self) -> float:
        """Estimate completion percentage."""
        total = len(self.documents_completed) + len(self.documents_pending)
        if self.current_document:
            total += 1
        if total == 0:
            return 100.0
        return (len(self.documents_completed) / total) * 100


class HandoverManager:
    """
    Manages the handover process for AI context continuity.

    The HandoverManager is responsible for:
    1. Saving all current work state
    2. Compressing notes to fit in the next context
    3. Creating clear instructions for resuming work
    4. Generating prompts for the next AI context

    This class works with the Scratchpad class from scratchpad.py to
    prepare comprehensive handover states.

    Example:
        scratchpad = Scratchpad(session_id="research-123")
        await scratchpad.initialize()
        session = await scratchpad.start_session(task="Research", documents=[...])

        # When context is full
        manager = HandoverManager(scratchpad)
        state = await manager.prepare_handover()
        prompt = await manager.create_handover_prompt(state)
    """

    def __init__(
        self,
        scratchpad: "Scratchpad",
        llm_summarizer: Optional[Any] = None,
        max_summary_tokens: int = 2000,
        max_findings: int = 10,
    ):
        """
        Initialize the HandoverManager.

        Args:
            scratchpad: The Scratchpad instance managing the current session
            llm_summarizer: Optional LLM interface for summarization
                           (should have a 'chat' method or be callable)
            max_summary_tokens: Maximum tokens for the notes summary
            max_findings: Maximum number of key findings to include
        """
        self.scratchpad = scratchpad
        self.llm_summarizer = llm_summarizer
        self.max_summary_tokens = max_summary_tokens
        self.max_findings = max_findings

    async def prepare_handover(self) -> HandoverState:
        """
        Prepare the complete state for context refresh.

        This method:
        1. Saves all current notes
        2. Summarizes notes to compress information
        3. Records exact position in current document
        4. Creates a comprehensive handover state

        Returns:
            HandoverState containing everything needed to resume
        """
        session = await self.scratchpad.get_session()
        if not session:
            raise RuntimeError("No active session. Call start_session() first.")

        logger.info(f"Preparing handover for session {session.id}")

        # Get document categorization from the session
        completed = [d for d in session.documents if d.status == "complete"]
        pending = [d for d in session.documents if d.status == "pending"]
        in_progress = [d for d in session.documents if d.status == "in_progress"]
        current = in_progress[0] if in_progress else None

        # Get and summarize notes
        notes = await self.scratchpad.get_notes()
        notes_summary = await self.summarize_notes(notes, session.task)

        # Extract key findings
        key_findings = await self.extract_key_findings(notes, session.task)

        # Collect citations
        citations = self._collect_citations(notes)

        # Determine next action
        next_action = self._determine_next_action(current, pending)

        # Increment context refresh counter and save
        session.context_refreshes += 1
        session.touch()
        # Force save via the backend
        await self.scratchpad._backend.save_session(session)

        state = HandoverState(
            session_id=session.id,
            task=session.task,
            documents_completed=[d.title or d.path for d in completed],
            documents_pending=[d.title or d.path for d in pending],
            current_document=current.title if current else None,
            current_position=current.position if current else "",
            notes_summary=notes_summary,
            key_findings=key_findings[:self.max_findings],
            citations_collected=citations,
            next_action=next_action,
            context_refreshes=session.context_refreshes,
            metadata={
                "total_notes": len(notes),
                "overall_progress": session.overall_progress,
            },
        )

        logger.info(
            f"Handover prepared: {len(completed)} complete, "
            f"{len(pending)} pending, refresh #{session.context_refreshes}"
        )

        return state

    async def create_handover_prompt(self, state: HandoverState) -> str:
        """
        Create a prompt that tells the next context what happened.

        This prompt is designed to be included at the start of a new
        conversation, providing all necessary context for the AI to
        continue the work seamlessly.

        Args:
            state: The handover state to convert to a prompt

        Returns:
            Formatted prompt string for the next context
        """
        # Format document status
        doc_status_lines = []
        for doc in state.documents_completed:
            doc_status_lines.append(f"  - [COMPLETE] {doc}")
        if state.current_document:
            doc_status_lines.append(
                f"  - [IN PROGRESS] {state.current_document} - {state.current_position}"
            )
        for doc in state.documents_pending:
            doc_status_lines.append(f"  - [PENDING] {doc}")

        document_status = "\n".join(doc_status_lines) if doc_status_lines else "No documents"

        # Format key findings
        findings_text = "\n".join(f"- {f}" for f in state.key_findings) if state.key_findings else "None yet"

        # Build the prompt
        total_docs = (
            len(state.documents_completed) +
            len(state.documents_pending) +
            (1 if state.current_document else 0)
        )

        prompt = HANDOVER_PROMPT.format(
            task=state.task,
            completed=len(state.documents_completed),
            total=total_docs,
            document_status=document_status,
            notes_summary=state.notes_summary or "No notes yet",
            current_position=state.current_position or "Not started",
            next_action=state.next_action,
            key_findings=findings_text,
            citations_count=len(state.citations_collected),
            context_refreshes=state.context_refreshes,
        )

        return prompt

    async def resume_from_handover(self, state: HandoverState) -> Dict[str, Any]:
        """
        Resume work from a handover state.

        This method prepares the context needed for the AI to continue
        working on the task.

        Args:
            state: The handover state to resume from

        Returns:
            Dictionary containing:
            - scratchpad: The scratchpad instance
            - current_document: Document to continue with
            - position: Where to start reading
            - context: Additional context for the AI
        """
        session = await self.scratchpad.get_session()
        if not session:
            raise RuntimeError("No active session")

        # Find the current document
        current_doc = None
        if state.current_document:
            for doc in session.documents:
                if doc.title == state.current_document or doc.path == state.current_document:
                    current_doc = doc
                    break

        # If no current doc, get next pending
        if not current_doc:
            pending = [d for d in session.documents if d.status == "pending"]
            if pending:
                current_doc = pending[0]
                current_doc.status = "in_progress"
                await self.scratchpad._backend.update_document(session.id, current_doc)

        return {
            "scratchpad": self.scratchpad,
            "current_document": current_doc,
            "position": state.current_position,
            "context": {
                "task": state.task,
                "notes_summary": state.notes_summary,
                "key_findings": state.key_findings,
                "citations": state.citations_collected,
                "refresh_count": state.context_refreshes,
            },
        }

    async def summarize_notes(
        self,
        notes: List[Note],
        task: str,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Compress notes to fit in the handover prompt.

        If an LLM summarizer is provided, it will be used to create
        an intelligent summary. Otherwise, a simple concatenation
        with truncation is used.

        Args:
            notes: List of notes to summarize
            task: The task description for context
            max_tokens: Maximum tokens for the summary (default from init)

        Returns:
            Summarized notes string
        """
        if not notes:
            return ""

        max_tokens = max_tokens or self.max_summary_tokens

        # Concatenate all notes
        all_content = "\n\n".join(
            f"[{n.document_id or 'General'}] {n.content}"
            for n in notes
        )

        # If we have an LLM summarizer and content is long, use it
        if self.llm_summarizer and len(all_content) > max_tokens * 4:
            try:
                prompt = NOTES_SUMMARIZATION_PROMPT.format(
                    task=task,
                    notes=all_content,
                    max_tokens=max_tokens,
                )
                summary = await self._call_llm(prompt)
                logger.debug(f"Summarized {len(notes)} notes using LLM")
                return summary
            except Exception as e:
                logger.warning(f"LLM summarization failed, using truncation: {e}")

        # Fallback: simple truncation with priority to recent notes
        if len(all_content) > max_tokens * 4:
            # Keep more recent notes (they're at the end)
            truncated = all_content[-(max_tokens * 4):]
            return f"[...truncated...]\n{truncated}"

        return all_content

    async def extract_key_findings(
        self,
        notes: List[Note],
        task: str,
    ) -> List[str]:
        """
        Extract the most important findings from notes.

        Args:
            notes: List of notes to analyze
            task: The task description for context

        Returns:
            List of key finding strings
        """
        if not notes:
            return []

        # If we have an LLM, use it for intelligent extraction
        if self.llm_summarizer:
            try:
                all_content = "\n\n".join(n.content for n in notes)
                prompt = KEY_FINDINGS_EXTRACTION_PROMPT.format(
                    task=task,
                    notes=all_content,
                    max_findings=self.max_findings,
                )
                response = await self._call_llm(prompt)
                # Parse the response into a list
                findings = [
                    line.strip().lstrip("- ").lstrip("* ").lstrip("1234567890. ")
                    for line in response.strip().split("\n")
                    if line.strip() and not line.strip().startswith("#")
                ]
                return findings[:self.max_findings]
            except Exception as e:
                logger.warning(f"LLM extraction failed, using simple extraction: {e}")

        # Fallback: extract first sentence of each note
        findings = []
        for note in notes:
            first_sentence = note.content.split(".")[0].strip()
            if first_sentence and len(first_sentence) > 20:
                findings.append(first_sentence + ".")
        return findings[:self.max_findings]

    def _collect_citations(self, notes: List[Note]) -> List[str]:
        """
        Collect all citations from notes.

        Args:
            notes: List of notes with citations

        Returns:
            List of unique citation strings
        """
        citations = []
        seen = set()
        for note in notes:
            for citation in note.citations:
                if citation not in seen:
                    citations.append(citation)
                    seen.add(citation)
        return citations

    def _determine_next_action(
        self,
        current: Optional[Document],
        pending: List[Document],
    ) -> str:
        """
        Determine what action should be taken next.

        Args:
            current: The document currently being processed
            pending: List of pending documents

        Returns:
            Human-readable next action string
        """
        if current:
            return f"Continue reading '{current.title or current.path}' from {current.position}"

        if pending:
            next_doc = pending[0]
            return f"Start reading '{next_doc.title or next_doc.path}' from the beginning"

        return "All documents processed. Synthesize findings and complete the task."

    async def _call_llm(self, prompt: str) -> str:
        """
        Call the LLM summarizer.

        Args:
            prompt: The prompt to send

        Returns:
            LLM response content
        """
        if hasattr(self.llm_summarizer, "chat"):
            # Handle LLMFallbackChain
            from ..llm import Message
            result = await self.llm_summarizer.chat([
                Message(role="user", content=prompt)
            ])
            return result.response.content
        elif hasattr(self.llm_summarizer, "__call__"):
            # Handle callable
            return await self.llm_summarizer(prompt)
        else:
            raise ValueError("LLM summarizer must have 'chat' method or be callable")
