"""
Session resume functionality for AI context continuity.

This module provides the infrastructure for resuming AI work sessions
after a context refresh or when returning to an incomplete task.

The SessionResumer:
1. Lists active sessions that can be resumed
2. Loads session state from storage
3. Prepares context for the AI to continue work
4. Creates configured Scratchpad instances for resumed sessions
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import Session, Note, Document
from .backends.base import StorageBackend
from .handover import HandoverState, HandoverManager, Scratchpad
from .prompts import RESUME_SYSTEM_PROMPT, PROGRESS_SUMMARY_TEMPLATE


logger = logging.getLogger(__name__)


@dataclass
class ResumeContext:
    """
    Context information needed to resume a session.

    This dataclass contains all the information an AI needs to
    understand where work left off and what to do next.

    Attributes:
        session_id: The session being resumed
        task: Description of the task
        progress: Human-readable progress summary
        notes_summary: Summary of notes taken so far
        key_findings: List of important findings
        next_steps: What the AI should do next
        handover_count: Number of context refreshes so far
        current_document: Document to continue with
        position: Position within current document
        citations: Citations collected so far
        metadata: Additional context information
    """
    session_id: str
    task: str
    progress: str
    notes_summary: str
    key_findings: List[str] = field(default_factory=list)
    next_steps: str = ""
    handover_count: int = 0
    current_document: Optional[str] = None
    position: str = ""
    citations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "task": self.task,
            "progress": self.progress,
            "notes_summary": self.notes_summary,
            "key_findings": self.key_findings,
            "next_steps": self.next_steps,
            "handover_count": self.handover_count,
            "current_document": self.current_document,
            "position": self.position,
            "citations": self.citations,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResumeContext":
        """Create a ResumeContext from a dictionary."""
        return cls(
            session_id=data.get("session_id", ""),
            task=data.get("task", ""),
            progress=data.get("progress", ""),
            notes_summary=data.get("notes_summary", ""),
            key_findings=data.get("key_findings", []),
            next_steps=data.get("next_steps", ""),
            handover_count=data.get("handover_count", 0),
            current_document=data.get("current_document"),
            position=data.get("position", ""),
            citations=data.get("citations", []),
            metadata=data.get("metadata", {}),
        )

    def to_prompt(self) -> str:
        """Generate a prompt string from this context."""
        findings_text = "\n".join(f"- {f}" for f in self.key_findings) if self.key_findings else "None yet"

        return RESUME_SYSTEM_PROMPT.format(
            task=self.task,
            progress=self.progress,
            notes_summary=self.notes_summary or "No notes taken yet",
            key_findings=findings_text,
            next_steps=self.next_steps,
            current_document=self.current_document or "None",
            position=self.position or "Not started",
            handover_count=self.handover_count,
        )


class SessionResumer:
    """
    Manages resuming paused or interrupted sessions.

    The SessionResumer provides functionality to:
    - List sessions that can be resumed
    - Get context needed to resume a session
    - Create configured Scratchpad instances
    - Handle session lifecycle transitions
    """

    def __init__(
        self,
        backend: StorageBackend,
        llm_summarizer: Optional[Any] = None,
    ):
        """
        Initialize the SessionResumer.

        Args:
            backend: Storage backend for loading sessions
            llm_summarizer: Optional LLM for summarization during resume
        """
        self.backend = backend
        self.llm_summarizer = llm_summarizer

    async def list_active_sessions(self) -> List[Session]:
        """
        List all sessions that can be resumed.

        Returns:
            List of active and paused sessions, sorted by last update
        """
        active = await self.backend.list_sessions(status="active")
        paused = await self.backend.list_sessions(status="paused")

        all_sessions = active + paused
        # Sort by most recently updated
        all_sessions.sort(key=lambda s: s.updated_at, reverse=True)

        logger.debug(f"Found {len(all_sessions)} resumable sessions")
        return all_sessions

    async def list_all_sessions(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Session]:
        """
        List all sessions with optional filtering.

        Args:
            status: Optional status filter (active, paused, complete)
            limit: Maximum number of sessions to return

        Returns:
            List of sessions matching criteria
        """
        sessions = await self.backend.list_sessions(status=status)
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions[:limit]

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a specific session by ID.

        Args:
            session_id: The session to retrieve

        Returns:
            The session if found, None otherwise
        """
        return await self.backend.load_session(session_id)

    async def get_resume_context(self, session_id: str) -> Optional[ResumeContext]:
        """
        Get everything needed to resume a session.

        This method loads the session and prepares a ResumeContext
        containing all information the AI needs to continue work.

        Args:
            session_id: The session to get context for

        Returns:
            ResumeContext if session found, None otherwise
        """
        session = await self.backend.load_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None

        # Format progress information
        progress = self._format_progress(session)

        # Get notes summary
        notes_summary = await self._get_notes_summary(session)

        # Extract key findings from notes
        key_findings = self._extract_findings(session.notes)

        # Determine next steps
        next_steps = self._determine_next_steps(session)

        # Get current document info
        current_doc = None
        position = ""
        for doc in session.documents:
            if doc.status == "in_progress":
                current_doc = doc.title or doc.path
                position = doc.position
                break

        # Collect citations
        citations = []
        for note in session.notes:
            citations.extend(note.citations)
        citations = list(set(citations))  # Deduplicate

        context = ResumeContext(
            session_id=session_id,
            task=session.task,
            progress=progress,
            notes_summary=notes_summary,
            key_findings=key_findings,
            next_steps=next_steps,
            handover_count=session.context_refreshes,
            current_document=current_doc,
            position=position,
            citations=citations,
            metadata={
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "total_documents": len(session.documents),
                "total_notes": len(session.notes),
            },
        )

        logger.info(f"Prepared resume context for session {session_id}")
        return context

    async def resume_session(
        self,
        session_id: str,
        mark_active: bool = True,
    ) -> Optional[Scratchpad]:
        """
        Resume a paused session.

        This method loads the session, optionally marks it as active,
        and returns a configured Scratchpad for continuing work.

        Args:
            session_id: The session to resume
            mark_active: Whether to mark the session as active

        Returns:
            Configured Scratchpad if session found, None otherwise
        """
        session = await self.backend.load_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for resume")
            return None

        # Mark as active if requested
        if mark_active and session.status != "active":
            session.status = "active"
            session.touch()
            await self.backend.save_session(session)
            logger.info(f"Marked session {session_id} as active")

        # Create and return scratchpad
        scratchpad = Scratchpad(session=session, backend=self.backend)
        logger.info(f"Resumed session {session_id}")
        return scratchpad

    async def create_session(
        self,
        task: str,
        documents: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
    ) -> Scratchpad:
        """
        Create a new session.

        Args:
            task: Description of the task
            documents: Optional list of document specifications
            session_id: Optional specific session ID

        Returns:
            Configured Scratchpad for the new session
        """
        import uuid

        # Create document objects
        doc_objects = []
        if documents:
            for doc_spec in documents:
                doc = Document(
                    id=doc_spec.get("id", str(uuid.uuid4())),
                    path=doc_spec.get("path", ""),
                    title=doc_spec.get("title", doc_spec.get("path", "")),
                    total_pages=doc_spec.get("total_pages", 0),
                )
                doc_objects.append(doc)

        # Create session
        session = Session(
            id=session_id or str(uuid.uuid4()),
            task=task,
            documents=doc_objects,
            status="active",
        )

        # Save to backend
        await self.backend.save_session(session)

        # Create and return scratchpad
        scratchpad = Scratchpad(session=session, backend=self.backend)
        logger.info(f"Created new session {session.id} with {len(doc_objects)} documents")
        return scratchpad

    async def pause_session(self, session_id: str) -> bool:
        """
        Pause an active session.

        Args:
            session_id: The session to pause

        Returns:
            True if session was paused, False if not found
        """
        session = await self.backend.load_session(session_id)
        if not session:
            return False

        session.status = "paused"
        session.touch()
        await self.backend.save_session(session)
        logger.info(f"Paused session {session_id}")
        return True

    async def complete_session(self, session_id: str) -> bool:
        """
        Mark a session as complete.

        Args:
            session_id: The session to complete

        Returns:
            True if session was completed, False if not found
        """
        session = await self.backend.load_session(session_id)
        if not session:
            return False

        session.status = "complete"
        session.touch()
        await self.backend.save_session(session)
        logger.info(f"Completed session {session_id}")
        return True

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session to delete

        Returns:
            True if deleted, False if not found
        """
        return await self.backend.delete_session(session_id)

    async def resume_from_handover_state(
        self,
        state: HandoverState,
    ) -> Optional[Scratchpad]:
        """
        Resume a session from a HandoverState.

        This is useful when a handover was prepared but the session
        wasn't directly saved to storage.

        Args:
            state: The handover state to resume from

        Returns:
            Configured Scratchpad if successful
        """
        session = await self.backend.load_session(state.session_id)
        if not session:
            logger.warning(f"Session {state.session_id} not found")
            return None

        # Update session with handover information
        session.context_refreshes = state.context_refreshes
        session.status = "active"
        session.touch()
        await self.backend.save_session(session)

        scratchpad = Scratchpad(session=session, backend=self.backend)
        return scratchpad

    def _format_progress(self, session: Session) -> str:
        """
        Format session progress as a human-readable string.

        Args:
            session: The session to format progress for

        Returns:
            Formatted progress string
        """
        total_docs = len(session.documents)
        completed_docs = session.documents_complete
        pending_docs = session.documents_pending

        # Calculate overall progress
        overall = session.overall_progress

        return PROGRESS_SUMMARY_TEMPLATE.format(
            completed=completed_docs,
            total=total_docs,
            pending=pending_docs,
            overall_percent=overall,
            notes_count=len(session.notes),
            context_refreshes=session.context_refreshes,
        )

    async def _get_notes_summary(
        self,
        session: Session,
        max_length: int = 2000,
    ) -> str:
        """
        Get a summary of session notes.

        Args:
            session: The session to summarize notes from
            max_length: Maximum character length for summary

        Returns:
            Notes summary string
        """
        if not session.notes:
            return ""

        # Concatenate notes
        all_notes = "\n\n".join(
            f"[{n.document_id or 'General'}] {n.content}"
            for n in session.notes
        )

        # If short enough, return as-is
        if len(all_notes) <= max_length:
            return all_notes

        # If we have an LLM, use it for summarization
        if self.llm_summarizer:
            try:
                from ..llm import Message

                prompt = f"""Summarize these research notes concisely, preserving key findings and citations:

{all_notes}

Keep the summary under {max_length} characters."""

                result = await self.llm_summarizer.chat([
                    Message(role="user", content=prompt)
                ])
                return result.response.content
            except Exception as e:
                logger.warning(f"LLM summarization failed: {e}")

        # Fallback: truncate with indication
        return f"[...{len(all_notes) - max_length} characters truncated...]\n\n{all_notes[-max_length:]}"

    def _extract_findings(
        self,
        notes: List[Note],
        max_findings: int = 10,
    ) -> List[str]:
        """
        Extract key findings from notes.

        Args:
            notes: List of notes to analyze
            max_findings: Maximum number of findings to return

        Returns:
            List of key finding strings
        """
        findings = []
        for note in notes:
            # Extract first sentence or key point
            content = note.content.strip()
            if content:
                # Try to get first meaningful sentence
                sentences = content.split(". ")
                if sentences:
                    first = sentences[0].strip()
                    if len(first) > 20 and first not in findings:
                        findings.append(first + ("." if not first.endswith(".") else ""))

        return findings[:max_findings]

    def _determine_next_steps(self, session: Session) -> str:
        """
        Determine what should be done next in the session.

        Args:
            session: The session to analyze

        Returns:
            Human-readable next steps string
        """
        # Find current document
        current_doc = None
        for doc in session.documents:
            if doc.status == "in_progress":
                current_doc = doc
                break

        if current_doc:
            return f"Continue reading '{current_doc.title or current_doc.path}' from {current_doc.position}"

        # Find next pending document
        pending = [d for d in session.documents if d.status == "pending"]
        if pending:
            next_doc = pending[0]
            return f"Start reading '{next_doc.title or next_doc.path}' from the beginning"

        # All documents complete
        if all(d.status == "complete" for d in session.documents):
            return "All documents processed. Review notes and synthesize findings."

        return "Review session state and determine next action."
