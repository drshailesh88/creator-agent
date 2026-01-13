"""
Data models for the Scratchpad system.

These models represent the core data structures used for managing
long-form content creation sessions with multiple documents.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid


@dataclass
class Document:
    """
    Represents a source document being processed in a session.

    Attributes:
        id: Unique identifier for the document
        path: File path or URL to the document
        title: Human-readable title
        total_pages: Total number of pages/sections in the document
        processed_pages: Number of pages/sections already processed
        status: Current processing status (pending, in_progress, complete)
        position: Human-readable position string (e.g., "page 15 of 30")
    """
    id: str
    path: str
    title: str
    total_pages: int = 0
    processed_pages: int = 0
    status: str = "pending"  # pending, in_progress, complete
    position: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.position and self.total_pages > 0:
            self.position = f"page {self.processed_pages} of {self.total_pages}"

    @property
    def progress_percent(self) -> float:
        """Calculate progress as a percentage."""
        if self.total_pages == 0:
            return 0.0
        return (self.processed_pages / self.total_pages) * 100

    @property
    def is_complete(self) -> bool:
        """Check if document processing is complete."""
        return self.status == "complete"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "path": self.path,
            "title": self.title,
            "total_pages": self.total_pages,
            "processed_pages": self.processed_pages,
            "status": self.status,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        """Create a Document from a dictionary."""
        return cls(
            id=data.get("id", ""),
            path=data.get("path", ""),
            title=data.get("title", ""),
            total_pages=data.get("total_pages", 0),
            processed_pages=data.get("processed_pages", 0),
            status=data.get("status", "pending"),
            position=data.get("position", ""),
        )


@dataclass
class Note:
    """
    Represents a note taken while processing documents.

    Attributes:
        id: Unique identifier for the note
        document_id: ID of the source document (optional)
        content: The actual note content
        citations: List of citation references
        timestamp: When the note was created
    """
    id: str
    document_id: Optional[str]
    content: str
    citations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "citations": self.citations,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        """Create a Note from a dictionary."""
        return cls(
            id=data.get("id", ""),
            document_id=data.get("document_id"),
            content=data.get("content", ""),
            citations=data.get("citations", []),
            timestamp=data.get("timestamp", datetime.utcnow()),
        )


@dataclass
class Session:
    """
    Represents a content creation session.

    A session tracks the overall task, all source documents being processed,
    notes taken, and progress through the content creation workflow.

    Attributes:
        id: Unique session identifier
        task: Description of the task (e.g., "Write article on statins")
        documents: List of source documents
        notes: List of notes taken during the session
        status: Session status (active, paused, complete)
        created_at: When the session was created
        updated_at: When the session was last updated
        context_refreshes: Number of times handover was called
    """
    id: str
    task: str
    documents: List[Document] = field(default_factory=list)
    notes: List[Note] = field(default_factory=list)
    status: str = "active"  # active, paused, complete
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    context_refreshes: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        # Convert dict documents to Document objects
        self.documents = [
            Document.from_dict(d) if isinstance(d, dict) else d
            for d in self.documents
        ]
        # Convert dict notes to Note objects
        self.notes = [
            Note.from_dict(n) if isinstance(n, dict) else n
            for n in self.notes
        ]

    @property
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.status == "active"

    @property
    def is_complete(self) -> bool:
        """Check if session is complete."""
        return self.status == "complete"

    @property
    def documents_complete(self) -> int:
        """Count of completed documents."""
        return sum(1 for d in self.documents if d.is_complete)

    @property
    def documents_pending(self) -> int:
        """Count of pending documents."""
        return sum(1 for d in self.documents if d.status == "pending")

    @property
    def overall_progress(self) -> float:
        """Calculate overall progress across all documents."""
        if not self.documents:
            return 0.0
        total_pages = sum(d.total_pages for d in self.documents)
        processed_pages = sum(d.processed_pages for d in self.documents)
        if total_pages == 0:
            return 0.0
        return (processed_pages / total_pages) * 100

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "task": self.task,
            "documents": [d.to_dict() for d in self.documents],
            "notes": [n.to_dict() for n in self.notes],
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "context_refreshes": self.context_refreshes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create a Session from a dictionary."""
        return cls(
            id=data.get("id", ""),
            task=data.get("task", ""),
            documents=data.get("documents", []),
            notes=data.get("notes", []),
            status=data.get("status", "active"),
            created_at=data.get("created_at", datetime.utcnow()),
            updated_at=data.get("updated_at", datetime.utcnow()),
            context_refreshes=data.get("context_refreshes", 0),
        )
