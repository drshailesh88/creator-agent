"""
Abstract base class for scratchpad storage backends.

This module defines the interface that all storage backends must implement.
Backends can store data in various systems: SQLite, Notion, files, etc.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..models import Session, Note, Document


class StorageBackend(ABC):
    """
    Abstract base class for scratchpad storage backends.

    All storage backends must implement these methods to provide
    persistence for scratchpad sessions and notes.
    """

    @abstractmethod
    async def save_session(self, session: Session) -> None:
        """
        Save or update a session.

        Args:
            session: The session to save
        """
        pass

    @abstractmethod
    async def load_session(self, session_id: str) -> Optional[Session]:
        """
        Load a session by ID.

        Args:
            session_id: The unique session identifier

        Returns:
            The session if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session by ID.

        Args:
            session_id: The unique session identifier

        Returns:
            True if session was deleted, False if not found
        """
        pass

    @abstractmethod
    async def list_sessions(self, status: Optional[str] = None) -> List[Session]:
        """
        List all sessions, optionally filtered by status.

        Args:
            status: Optional status filter (active, paused, complete)

        Returns:
            List of sessions matching the criteria
        """
        pass

    @abstractmethod
    async def save_note(self, session_id: str, note: Note) -> None:
        """
        Save a note to a session.

        Args:
            session_id: The session to add the note to
            note: The note to save
        """
        pass

    @abstractmethod
    async def get_notes(self, session_id: str, document_id: Optional[str] = None) -> List[Note]:
        """
        Get notes for a session, optionally filtered by document.

        Args:
            session_id: The session to get notes from
            document_id: Optional document ID to filter by

        Returns:
            List of notes matching the criteria
        """
        pass

    @abstractmethod
    async def delete_note(self, session_id: str, note_id: str) -> bool:
        """
        Delete a specific note.

        Args:
            session_id: The session containing the note
            note_id: The note to delete

        Returns:
            True if note was deleted, False if not found
        """
        pass

    @abstractmethod
    async def update_document(self, session_id: str, document: Document) -> None:
        """
        Update a document's status and progress.

        Args:
            session_id: The session containing the document
            document: The document with updated information
        """
        pass

    async def initialize(self) -> None:
        """
        Initialize the backend (create tables, directories, etc.).

        Override this method if your backend requires initialization.
        """
        pass

    async def close(self) -> None:
        """
        Clean up resources when the backend is no longer needed.

        Override this method if your backend needs cleanup.
        """
        pass
