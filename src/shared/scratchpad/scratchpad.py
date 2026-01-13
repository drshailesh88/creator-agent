"""
Main Scratchpad class for managing content creation sessions.

The Scratchpad provides a unified interface for skills to manage
long-form content creation with multiple documents, note-taking,
progress tracking, and context handover for LLM context refreshes.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from .models import Document, Note, Session
from .backends.base import StorageBackend


class InMemoryBackend(StorageBackend):
    """
    Simple in-memory storage backend for testing and simple use cases.

    Data is lost when the process exits. For persistence, use a
    file-based or database backend.
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    async def save_session(self, session: Session) -> None:
        self._sessions[session.id] = session

    async def load_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    async def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def list_sessions(self, status: Optional[str] = None) -> List[Session]:
        sessions = list(self._sessions.values())
        if status:
            sessions = [s for s in sessions if s.status == status]
        return sessions

    async def save_note(self, session_id: str, note: Note) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.notes.append(note)
            session.touch()

    async def get_notes(self, session_id: str, document_id: Optional[str] = None) -> List[Note]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        notes = session.notes
        if document_id:
            notes = [n for n in notes if n.document_id == document_id]
        return notes

    async def delete_note(self, session_id: str, note_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        for i, note in enumerate(session.notes):
            if note.id == note_id:
                session.notes.pop(i)
                session.touch()
                return True
        return False

    async def update_document(self, session_id: str, document: Document) -> None:
        session = self._sessions.get(session_id)
        if session:
            for i, doc in enumerate(session.documents):
                if doc.id == document.id:
                    session.documents[i] = document
                    session.touch()
                    break


class FileBackend(StorageBackend):
    """
    File-based storage backend using JSON files.

    Stores each session as a separate JSON file in the specified directory.
    """

    def __init__(self, storage_dir: Union[str, Path]):
        self.storage_dir = Path(storage_dir)

    async def initialize(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.json"

    async def save_session(self, session: Session) -> None:
        session.touch()
        path = self._session_path(session.id)
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    async def load_session(self, session_id: str) -> Optional[Session]:
        path = self._session_path(session_id)
        if not path.exists():
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return Session.from_dict(data)

    async def delete_session(self, session_id: str) -> bool:
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False

    async def list_sessions(self, status: Optional[str] = None) -> List[Session]:
        sessions = []
        for path in self.storage_dir.glob("*.json"):
            with open(path, "r") as f:
                data = json.load(f)
            session = Session.from_dict(data)
            if status is None or session.status == status:
                sessions.append(session)
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)

    async def save_note(self, session_id: str, note: Note) -> None:
        session = await self.load_session(session_id)
        if session:
            session.notes.append(note)
            await self.save_session(session)

    async def get_notes(self, session_id: str, document_id: Optional[str] = None) -> List[Note]:
        session = await self.load_session(session_id)
        if not session:
            return []
        notes = session.notes
        if document_id:
            notes = [n for n in notes if n.document_id == document_id]
        return notes

    async def delete_note(self, session_id: str, note_id: str) -> bool:
        session = await self.load_session(session_id)
        if not session:
            return False
        for i, note in enumerate(session.notes):
            if note.id == note_id:
                session.notes.pop(i)
                await self.save_session(session)
                return True
        return False

    async def update_document(self, session_id: str, document: Document) -> None:
        session = await self.load_session(session_id)
        if session:
            for i, doc in enumerate(session.documents):
                if doc.id == document.id:
                    session.documents[i] = document
                    await self.save_session(session)
                    break


class Scratchpad:
    """
    Main interface for managing content creation sessions.

    The Scratchpad enables skills to:
    - Start and manage content creation sessions
    - Track progress through multiple source documents
    - Take and organize notes with citations
    - Handle context refreshes (handover) for long-running tasks

    Example:
        scratchpad = Scratchpad(session_id="my-session")
        await scratchpad.initialize()

        # Start a new session
        session = await scratchpad.start_session(
            task="Write article on cardiovascular health",
            documents=["paper1.pdf", "paper2.pdf"]
        )

        # Take notes while processing
        await scratchpad.save_notes(
            content="Key finding: statins reduce LDL by 30-50%",
            document_id="doc-1",
            citations=["Smith et al., 2023, p. 15"]
        )

        # Track progress
        await scratchpad.mark_progress("doc-1", "in_progress", "page 10 of 25")

        # Get handover state for context refresh
        handover = await scratchpad.handover()
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        backend: Optional[StorageBackend] = None,
        storage_dir: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize a Scratchpad instance.

        Args:
            session_id: Unique identifier for this session. If None, a new ID is generated.
            backend: Storage backend to use. If None, uses FileBackend or InMemoryBackend.
            storage_dir: Directory for file-based storage. Used if backend is None.
        """
        self.session_id = session_id or str(uuid.uuid4())

        if backend:
            self._backend = backend
        elif storage_dir:
            self._backend = FileBackend(storage_dir)
        else:
            self._backend = InMemoryBackend()

        self._session: Optional[Session] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the backend and load existing session if available."""
        await self._backend.initialize()
        self._session = await self._backend.load_session(self.session_id)
        self._initialized = True

    async def _ensure_initialized(self) -> None:
        """Ensure the scratchpad is initialized before use."""
        if not self._initialized:
            await self.initialize()

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    async def start_session(
        self,
        task: str,
        documents: List[Union[str, Dict, Document]],
    ) -> Session:
        """
        Start a new content creation session.

        Args:
            task: Description of the task (e.g., "Write article on statins")
            documents: List of document paths, dicts, or Document objects

        Returns:
            The newly created Session
        """
        await self._ensure_initialized()

        # Convert document inputs to Document objects
        doc_objects = []
        for i, doc in enumerate(documents):
            if isinstance(doc, Document):
                doc_objects.append(doc)
            elif isinstance(doc, dict):
                doc_objects.append(Document.from_dict(doc))
            elif isinstance(doc, str):
                # Create Document from path string
                doc_objects.append(Document(
                    id=str(uuid.uuid4()),
                    path=doc,
                    title=Path(doc).stem if "/" in doc or "\\" in doc else doc,
                    status="pending",
                ))
            else:
                raise ValueError(f"Invalid document type: {type(doc)}")

        self._session = Session(
            id=self.session_id,
            task=task,
            documents=doc_objects,
            notes=[],
            status="active",
        )

        await self._backend.save_session(self._session)
        return self._session

    async def get_session(self) -> Optional[Session]:
        """
        Get the current session.

        Returns:
            The current Session or None if no session exists
        """
        await self._ensure_initialized()
        return self._session

    async def end_session(self, status: str = "complete") -> None:
        """
        End the current session.

        Args:
            status: Final status (complete, paused)
        """
        await self._ensure_initialized()
        if self._session:
            self._session.status = status
            self._session.touch()
            await self._backend.save_session(self._session)

    async def pause_session(self) -> None:
        """Pause the current session."""
        await self.end_session(status="paused")

    async def resume_session(self) -> Optional[Session]:
        """Resume a paused session."""
        await self._ensure_initialized()
        if self._session and self._session.status == "paused":
            self._session.status = "active"
            self._session.touch()
            await self._backend.save_session(self._session)
        return self._session

    # -------------------------------------------------------------------------
    # Note Taking
    # -------------------------------------------------------------------------

    async def save_notes(
        self,
        content: str,
        document_id: Optional[str] = None,
        citations: Optional[List[str]] = None,
    ) -> Note:
        """
        Save notes to the scratchpad.

        Args:
            content: The note content
            document_id: Optional ID of the source document
            citations: Optional list of citation references

        Returns:
            The created Note
        """
        await self._ensure_initialized()

        if not self._session:
            raise RuntimeError("No active session. Call start_session() first.")

        note = Note(
            id=str(uuid.uuid4()),
            document_id=document_id,
            content=content,
            citations=citations or [],
            timestamp=datetime.utcnow(),
        )

        self._session.notes.append(note)
        self._session.touch()
        await self._backend.save_session(self._session)

        return note

    async def get_notes(self, document_id: Optional[str] = None) -> List[Note]:
        """
        Get notes, optionally filtered by document.

        Args:
            document_id: Optional document ID to filter by

        Returns:
            List of notes
        """
        await self._ensure_initialized()

        if not self._session:
            return []

        notes = self._session.notes
        if document_id:
            notes = [n for n in notes if n.document_id == document_id]

        return notes

    async def get_all_notes(self) -> str:
        """
        Get all notes concatenated as a single string for writing.

        Returns:
            All notes joined with newlines, formatted for use in writing
        """
        await self._ensure_initialized()

        if not self._session:
            return ""

        parts = []
        for note in self._session.notes:
            part = note.content
            if note.citations:
                part += f"\n  Citations: {', '.join(note.citations)}"
            parts.append(part)

        return "\n\n".join(parts)

    async def delete_note(self, note_id: str) -> bool:
        """
        Delete a specific note.

        Args:
            note_id: ID of the note to delete

        Returns:
            True if deleted, False if not found
        """
        await self._ensure_initialized()

        if not self._session:
            return False

        for i, note in enumerate(self._session.notes):
            if note.id == note_id:
                self._session.notes.pop(i)
                self._session.touch()
                await self._backend.save_session(self._session)
                return True

        return False

    # -------------------------------------------------------------------------
    # Progress Tracking
    # -------------------------------------------------------------------------

    async def mark_progress(
        self,
        document_id: str,
        status: str,
        position: Optional[str] = None,
        processed_pages: Optional[int] = None,
    ) -> Optional[Document]:
        """
        Update progress on a document.

        Args:
            document_id: ID of the document to update
            status: New status (pending, in_progress, complete)
            position: Human-readable position (e.g., "page 15 of 30")
            processed_pages: Number of pages processed

        Returns:
            The updated Document or None if not found
        """
        await self._ensure_initialized()

        if not self._session:
            return None

        for doc in self._session.documents:
            if doc.id == document_id:
                doc.status = status
                if position:
                    doc.position = position
                if processed_pages is not None:
                    doc.processed_pages = processed_pages
                    if doc.total_pages > 0:
                        doc.position = f"page {processed_pages} of {doc.total_pages}"

                self._session.touch()
                await self._backend.save_session(self._session)
                return doc

        return None

    async def get_progress(self) -> Dict:
        """
        Get overall progress summary.

        Returns:
            Dictionary with progress information
        """
        await self._ensure_initialized()

        if not self._session:
            return {
                "documents_total": 0,
                "documents_complete": 0,
                "documents_pending": 0,
                "documents_in_progress": 0,
                "overall_progress": 0.0,
                "notes_count": 0,
            }

        return {
            "documents_total": len(self._session.documents),
            "documents_complete": self._session.documents_complete,
            "documents_pending": self._session.documents_pending,
            "documents_in_progress": sum(
                1 for d in self._session.documents if d.status == "in_progress"
            ),
            "overall_progress": self._session.overall_progress,
            "notes_count": len(self._session.notes),
            "documents": [
                {
                    "id": d.id,
                    "title": d.title,
                    "status": d.status,
                    "position": d.position,
                    "progress": d.progress_percent,
                }
                for d in self._session.documents
            ],
        }

    async def get_next_document(self) -> Optional[Document]:
        """
        Get the next document to process.

        Returns documents in order:
        1. Any document currently in_progress
        2. The first pending document

        Returns:
            The next Document to process, or None if all complete
        """
        await self._ensure_initialized()

        if not self._session:
            return None

        # First, return any in-progress document
        for doc in self._session.documents:
            if doc.status == "in_progress":
                return doc

        # Then, return the first pending document
        for doc in self._session.documents:
            if doc.status == "pending":
                return doc

        return None

    async def get_document(self, document_id: str) -> Optional[Document]:
        """
        Get a specific document by ID.

        Args:
            document_id: ID of the document to retrieve

        Returns:
            The Document or None if not found
        """
        await self._ensure_initialized()

        if not self._session:
            return None

        for doc in self._session.documents:
            if doc.id == document_id:
                return doc

        return None

    # -------------------------------------------------------------------------
    # Handover (Context Refresh)
    # -------------------------------------------------------------------------

    async def handover(self) -> Dict:
        """
        Prepare handover state for context refresh.

        This method is called when the LLM context needs to be refreshed.
        It returns a summary of the current state that can be used to
        resume work in a new context.

        Returns:
            Dictionary containing handover state
        """
        await self._ensure_initialized()

        if not self._session:
            return {"error": "No active session"}

        self._session.context_refreshes += 1
        self._session.touch()
        await self._backend.save_session(self._session)

        return await self.get_handover_state()

    async def get_handover_state(self) -> Dict:
        """
        Get current state for resuming in a new context.

        Returns:
            Dictionary containing all information needed to resume work
        """
        await self._ensure_initialized()

        if not self._session:
            return {"error": "No active session"}

        # Get the current/next document to process
        next_doc = await self.get_next_document()

        # Summarize notes by document
        notes_by_doc: Dict[str, List[str]] = {}
        general_notes: List[str] = []

        for note in self._session.notes:
            if note.document_id:
                if note.document_id not in notes_by_doc:
                    notes_by_doc[note.document_id] = []
                notes_by_doc[note.document_id].append(note.content)
            else:
                general_notes.append(note.content)

        return {
            "session_id": self._session.id,
            "task": self._session.task,
            "status": self._session.status,
            "context_refreshes": self._session.context_refreshes,
            "progress": {
                "total_documents": len(self._session.documents),
                "completed": self._session.documents_complete,
                "pending": self._session.documents_pending,
                "overall_percent": self._session.overall_progress,
            },
            "documents": [
                {
                    "id": d.id,
                    "title": d.title,
                    "path": d.path,
                    "status": d.status,
                    "position": d.position,
                }
                for d in self._session.documents
            ],
            "current_document": {
                "id": next_doc.id,
                "title": next_doc.title,
                "path": next_doc.path,
                "position": next_doc.position,
            } if next_doc else None,
            "notes_summary": {
                "total_notes": len(self._session.notes),
                "notes_by_document": {
                    doc_id: len(notes)
                    for doc_id, notes in notes_by_doc.items()
                },
                "general_notes": len(general_notes),
            },
            "recent_notes": [
                {
                    "content": n.content[:200] + "..." if len(n.content) > 200 else n.content,
                    "document_id": n.document_id,
                    "timestamp": n.timestamp.isoformat(),
                }
                for n in sorted(self._session.notes, key=lambda x: x.timestamp, reverse=True)[:5]
            ],
            "instructions": (
                f"Resume task: {self._session.task}\n"
                f"Context refresh #{self._session.context_refreshes}\n"
                f"Progress: {self._session.documents_complete}/{len(self._session.documents)} documents complete\n"
                f"Next: {'Process ' + next_doc.title + ' from ' + next_doc.position if next_doc else 'All documents complete - ready to write'}"
            ),
        }

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict:
        """
        Serialize the scratchpad state to a dictionary.

        Returns:
            Dictionary representation of the scratchpad
        """
        if not self._session:
            return {"session_id": self.session_id, "session": None}

        return {
            "session_id": self.session_id,
            "session": self._session.to_dict(),
        }

    @classmethod
    async def from_dict(
        cls,
        data: Dict,
        backend: Optional[StorageBackend] = None,
    ) -> "Scratchpad":
        """
        Create a Scratchpad from a dictionary.

        Args:
            data: Dictionary containing scratchpad state
            backend: Optional storage backend to use

        Returns:
            A new Scratchpad instance
        """
        scratchpad = cls(
            session_id=data.get("session_id"),
            backend=backend,
        )

        if data.get("session"):
            scratchpad._session = Session.from_dict(data["session"])
            scratchpad._initialized = True
            if scratchpad._backend:
                await scratchpad._backend.initialize()
                await scratchpad._backend.save_session(scratchpad._session)

        return scratchpad

    async def close(self) -> None:
        """Clean up resources."""
        if self._backend:
            await self._backend.close()
