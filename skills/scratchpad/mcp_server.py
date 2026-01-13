#!/usr/bin/env python3
"""
Scratchpad MCP Server for Clawdbot

A shared infrastructure for managing long-form content creation with multiple documents.
Provides persistence across context refreshes, progress tracking, and seamless handovers.
"""

import os
import sys
import json
import asyncio
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# MCP Protocol imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource, ResourceTemplate
except ImportError:
    print("Error: MCP SDK not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("scratchpad")

# Configuration
SCRATCHPAD_DIR = Path(os.environ.get("SCRATCHPAD_DIR", "~/.clawdbot/scratchpad")).expanduser()


class SessionStatus(str, Enum):
    """Status of a research session."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class DocumentStatus(str, Enum):
    """Status of document processing."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"


@dataclass
class Note:
    """A single note entry."""
    id: str
    content: str
    timestamp: str
    document_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    section: Optional[str] = None


@dataclass
class DocumentProgress:
    """Progress tracking for a document."""
    document_id: str
    path: str
    status: str = DocumentStatus.NOT_STARTED.value
    position: Optional[str] = None
    notes: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class HandoverState:
    """State captured during a handover."""
    timestamp: str
    summary: str
    next_steps: List[str]
    context_snapshot: Dict[str, Any]


@dataclass
class Session:
    """A research session with documents, notes, and progress."""
    id: str
    task: str
    name: Optional[str]
    status: str
    created_at: str
    updated_at: str
    documents: List[DocumentProgress] = field(default_factory=list)
    notes: List[Note] = field(default_factory=list)
    handovers: List[HandoverState] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Scratchpad:
    """
    File-based scratchpad storage system.
    Persists sessions, notes, and progress to JSON files.
    """

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.sessions_dir = storage_dir / "sessions"
        self.current_session_file = storage_dir / "current_session.json"
        self._current_session_id: Optional[str] = None

        # Ensure directories exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Load current session if exists
        self._load_current_session_id()

    def _load_current_session_id(self):
        """Load the current session ID from file."""
        if self.current_session_file.exists():
            try:
                data = json.loads(self.current_session_file.read_text())
                self._current_session_id = data.get("session_id")
            except (json.JSONDecodeError, IOError):
                self._current_session_id = None

    def _save_current_session_id(self, session_id: Optional[str]):
        """Save the current session ID to file."""
        self._current_session_id = session_id
        self.current_session_file.write_text(json.dumps({
            "session_id": session_id,
            "updated_at": datetime.now().isoformat()
        }, indent=2))

    def _session_path(self, session_id: str) -> Path:
        """Get the path to a session file."""
        return self.sessions_dir / f"{session_id}.json"

    def _load_session(self, session_id: str) -> Optional[Session]:
        """Load a session from disk."""
        path = self._session_path(session_id)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
            return Session(
                id=data["id"],
                task=data["task"],
                name=data.get("name"),
                status=data["status"],
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                documents=[DocumentProgress(**d) for d in data.get("documents", [])],
                notes=[Note(**n) for n in data.get("notes", [])],
                handovers=[HandoverState(**h) for h in data.get("handovers", [])],
                metadata=data.get("metadata", {})
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None

    def _save_session(self, session: Session):
        """Save a session to disk."""
        session.updated_at = datetime.now().isoformat()
        path = self._session_path(session.id)

        data = {
            "id": session.id,
            "task": session.task,
            "name": session.name,
            "status": session.status,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "documents": [asdict(d) for d in session.documents],
            "notes": [asdict(n) for n in session.notes],
            "handovers": [asdict(h) for h in session.handovers],
            "metadata": session.metadata
        }

        path.write_text(json.dumps(data, indent=2))

    @property
    def current_session(self) -> Optional[Session]:
        """Get the current active session."""
        if self._current_session_id:
            return self._load_session(self._current_session_id)
        return None

    def start_session(
        self,
        task: str,
        document_paths: Optional[List[str]] = None,
        session_name: Optional[str] = None
    ) -> Session:
        """Start a new research session."""
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        documents = []
        if document_paths:
            for path in document_paths:
                doc_id = str(uuid.uuid4())[:8]
                documents.append(DocumentProgress(
                    document_id=doc_id,
                    path=path,
                    status=DocumentStatus.NOT_STARTED.value
                ))

        session = Session(
            id=session_id,
            task=task,
            name=session_name,
            status=SessionStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
            documents=documents,
            notes=[],
            handovers=[],
            metadata={}
        )

        self._save_session(session)
        self._save_current_session_id(session_id)

        return session

    def save_notes(
        self,
        content: str,
        document_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        section: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Note:
        """Save notes to the scratchpad."""
        sid = session_id or self._current_session_id
        if not sid:
            raise ValueError("No active session. Start a session first.")

        session = self._load_session(sid)
        if not session:
            raise ValueError(f"Session {sid} not found.")

        note = Note(
            id=str(uuid.uuid4())[:8],
            content=content,
            timestamp=datetime.now().isoformat(),
            document_id=document_id,
            tags=tags or [],
            section=section
        )

        session.notes.append(note)
        self._save_session(session)

        return note

    def get_notes(
        self,
        document_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        section: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[Note]:
        """Retrieve notes with optional filters."""
        sid = session_id or self._current_session_id
        if not sid:
            return []

        session = self._load_session(sid)
        if not session:
            return []

        notes = session.notes

        if document_id:
            notes = [n for n in notes if n.document_id == document_id]

        if tags:
            notes = [n for n in notes if any(t in n.tags for t in tags)]

        if section:
            notes = [n for n in notes if n.section == section]

        return notes

    def mark_progress(
        self,
        document_id: str,
        status: str,
        position: Optional[str] = None,
        notes: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> DocumentProgress:
        """Mark progress on a document."""
        sid = session_id or self._current_session_id
        if not sid:
            raise ValueError("No active session.")

        session = self._load_session(sid)
        if not session:
            raise ValueError(f"Session {sid} not found.")

        # Find the document
        doc = None
        for d in session.documents:
            if d.document_id == document_id or d.path == document_id:
                doc = d
                break

        if not doc:
            # Create new document entry
            doc = DocumentProgress(
                document_id=document_id,
                path=document_id,
                status=status,
                position=position,
                notes=notes
            )
            session.documents.append(doc)
        else:
            doc.status = status
            if position:
                doc.position = position
            if notes:
                doc.notes = notes

        if status == DocumentStatus.IN_PROGRESS.value and not doc.started_at:
            doc.started_at = datetime.now().isoformat()
        elif status == DocumentStatus.COMPLETED.value:
            doc.completed_at = datetime.now().isoformat()

        self._save_session(session)
        return doc

    def get_progress(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get overall progress for a session."""
        sid = session_id or self._current_session_id
        if not sid:
            return {"error": "No active session"}

        session = self._load_session(sid)
        if not session:
            return {"error": f"Session {sid} not found"}

        total_docs = len(session.documents)
        completed = sum(1 for d in session.documents if d.status == DocumentStatus.COMPLETED.value)
        in_progress = sum(1 for d in session.documents if d.status == DocumentStatus.IN_PROGRESS.value)
        not_started = sum(1 for d in session.documents if d.status == DocumentStatus.NOT_STARTED.value)

        return {
            "session_id": session.id,
            "session_name": session.name,
            "task": session.task,
            "status": session.status,
            "documents": {
                "total": total_docs,
                "completed": completed,
                "in_progress": in_progress,
                "not_started": not_started,
                "progress_percent": round((completed / total_docs * 100) if total_docs > 0 else 0, 1)
            },
            "notes_count": len(session.notes),
            "handovers_count": len(session.handovers),
            "document_details": [
                {
                    "id": d.document_id,
                    "path": d.path,
                    "status": d.status,
                    "position": d.position
                }
                for d in session.documents
            ]
        }

    def handover(
        self,
        summary: Optional[str] = None,
        next_steps: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> HandoverState:
        """Prepare for context refresh, save all state."""
        sid = session_id or self._current_session_id
        if not sid:
            raise ValueError("No active session to hand over.")

        session = self._load_session(sid)
        if not session:
            raise ValueError(f"Session {sid} not found.")

        # Generate summary if not provided
        if not summary:
            progress = self.get_progress(sid)
            doc_progress = progress.get("documents", {})
            summary = (
                f"Processed {doc_progress.get('completed', 0)}/{doc_progress.get('total', 0)} documents. "
                f"Collected {progress.get('notes_count', 0)} notes."
            )

        # Capture context snapshot
        context_snapshot = {
            "progress": self.get_progress(sid),
            "recent_notes": [asdict(n) for n in session.notes[-5:]],
            "current_documents": [
                {"id": d.document_id, "path": d.path, "status": d.status, "position": d.position}
                for d in session.documents if d.status == DocumentStatus.IN_PROGRESS.value
            ]
        }

        handover_state = HandoverState(
            timestamp=datetime.now().isoformat(),
            summary=summary,
            next_steps=next_steps or [],
            context_snapshot=context_snapshot
        )

        session.handovers.append(handover_state)
        session.status = SessionStatus.PAUSED.value
        self._save_session(session)

        return handover_state

    def resume_session(self, session_id: str) -> Session:
        """Resume a paused session."""
        session = self._load_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        session.status = SessionStatus.ACTIVE.value
        self._save_session(session)
        self._save_current_session_id(session_id)

        return session

    def list_sessions(
        self,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """List all sessions with optional status filter."""
        sessions = []

        for session_file in self.sessions_dir.glob("*.json"):
            try:
                data = json.loads(session_file.read_text())
                if status and status != "all" and data.get("status") != status:
                    continue

                sessions.append({
                    "id": data["id"],
                    "task": data["task"],
                    "name": data.get("name"),
                    "status": data["status"],
                    "created_at": data["created_at"],
                    "updated_at": data["updated_at"],
                    "document_count": len(data.get("documents", [])),
                    "notes_count": len(data.get("notes", [])),
                    "is_current": data["id"] == self._current_session_id
                })
            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by updated_at descending
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions[:limit]

    def get_writing_context(
        self,
        session_id: Optional[str] = None,
        format: str = "detailed"
    ) -> Dict[str, Any]:
        """Get all notes formatted for writing phase."""
        sid = session_id or self._current_session_id
        if not sid:
            return {"error": "No active session"}

        session = self._load_session(sid)
        if not session:
            return {"error": f"Session {sid} not found"}

        # Group notes by section
        notes_by_section: Dict[str, List[Note]] = {}
        notes_by_document: Dict[str, List[Note]] = {}
        all_tags: set = set()

        for note in session.notes:
            # By section
            section = note.section or "general"
            if section not in notes_by_section:
                notes_by_section[section] = []
            notes_by_section[section].append(note)

            # By document
            doc_id = note.document_id or "general"
            if doc_id not in notes_by_document:
                notes_by_document[doc_id] = []
            notes_by_document[doc_id].append(note)

            # Collect tags
            all_tags.update(note.tags)

        if format == "outline":
            # Condensed outline format
            result = {
                "session_id": session.id,
                "task": session.task,
                "sections": {
                    section: [n.content[:100] + "..." if len(n.content) > 100 else n.content
                              for n in notes]
                    for section, notes in notes_by_section.items()
                },
                "key_tags": list(all_tags)[:10]
            }
        elif format == "summary":
            # Brief summary
            result = {
                "session_id": session.id,
                "task": session.task,
                "total_notes": len(session.notes),
                "sections": list(notes_by_section.keys()),
                "documents_covered": len(notes_by_document),
                "key_themes": list(all_tags)[:5]
            }
        else:
            # Detailed format (default)
            result = {
                "session_id": session.id,
                "task": session.task,
                "name": session.name,
                "progress": self.get_progress(sid),
                "notes_by_section": {
                    section: [asdict(n) for n in notes]
                    for section, notes in notes_by_section.items()
                },
                "notes_by_document": {
                    doc_id: [asdict(n) for n in notes]
                    for doc_id, notes in notes_by_document.items()
                },
                "all_tags": list(all_tags),
                "handover_history": [asdict(h) for h in session.handovers]
            }

        return result


# Initialize scratchpad storage
scratchpad = Scratchpad(SCRATCHPAD_DIR)


# MCP Tool definitions

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available scratchpad tools."""
    return [
        Tool(
            name="start_session",
            description=(
                "Start a new research session with documents. Creates a tracked workspace "
                "for notes and progress that persists across context refreshes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Description of the research task or goal"
                    },
                    "document_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Paths to documents to process in this session"
                    },
                    "session_name": {
                        "type": "string",
                        "description": "Optional friendly name for the session"
                    }
                },
                "required": ["task"]
            }
        ),
        Tool(
            name="save_notes",
            description=(
                "Save research notes to the scratchpad. Notes persist across context "
                "refreshes and can be tagged and organized by section."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The notes content to save"
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Optional: Associate notes with a specific document"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for organizing notes"
                    },
                    "section": {
                        "type": "string",
                        "description": "Optional section name (e.g., 'key_findings', 'quotes', 'questions')"
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="get_notes",
            description=(
                "Retrieve notes from the scratchpad. Can filter by document, tags, or section."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Filter notes by document ID"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter notes by tags"
                    },
                    "section": {
                        "type": "string",
                        "description": "Filter notes by section"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Get notes from a specific session (defaults to current)"
                    }
                }
            }
        ),
        Tool(
            name="mark_progress",
            description=(
                "Mark reading/processing progress on a document. Tracks where you left off "
                "for seamless continuation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The document to mark progress on"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["not_started", "in_progress", "completed", "needs_review"],
                        "description": "Current status of the document"
                    },
                    "position": {
                        "type": "string",
                        "description": "Where you left off (e.g., 'page 15', 'section 3.2')"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about current progress"
                    }
                },
                "required": ["document_id", "status"]
            }
        ),
        Tool(
            name="get_progress",
            description=(
                "Get overall research progress across all documents in the session."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Get progress for a specific session (defaults to current)"
                    }
                }
            }
        ),
        Tool(
            name="handover",
            description=(
                "Prepare for context refresh. Saves all state and generates a handover summary "
                "for seamless continuation in a fresh context."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Optional summary of what was accomplished"
                    },
                    "next_steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of next steps to continue"
                    }
                }
            }
        ),
        Tool(
            name="resume_session",
            description=(
                "Resume a paused research session. Loads all saved state and sets it as the "
                "current active session."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID to resume"
                    }
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="list_sessions",
            description=(
                "List all active and paused research sessions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "paused", "completed", "all"],
                        "description": "Filter sessions by status (default: all)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of sessions to return (default: 20)"
                    }
                }
            }
        ),
        Tool(
            name="get_writing_context",
            description=(
                "Get all notes formatted for writing phase. Consolidates research notes "
                "organized by section and document for content creation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session to get writing context for (defaults to current)"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["outline", "detailed", "summary"],
                        "description": "How to format the output (default: detailed)"
                    }
                }
            }
        )
    ]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    resources = []

    # List current session as a resource
    if scratchpad._current_session_id:
        session = scratchpad.current_session
        if session:
            resources.append(Resource(
                uri=f"scratchpad://session/{session.id}",
                name=f"Current Session: {session.name or session.task[:50]}",
                description=f"Active research session with {len(session.notes)} notes",
                mimeType="application/json"
            ))

    return resources


@server.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    """List resource templates."""
    return [
        ResourceTemplate(
            uriTemplate="scratchpad://session/{session_id}",
            name="Research Session",
            description="Access a research session's full state"
        ),
        ResourceTemplate(
            uriTemplate="scratchpad://session/{session_id}/notes",
            name="Session Notes",
            description="Access notes from a research session"
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    if uri.startswith("scratchpad://session/"):
        parts = uri.replace("scratchpad://session/", "").split("/")
        session_id = parts[0]

        session = scratchpad._load_session(session_id)
        if not session:
            return json.dumps({"error": f"Session {session_id} not found"})

        if len(parts) > 1 and parts[1] == "notes":
            return json.dumps([asdict(n) for n in session.notes], indent=2)

        return json.dumps(asdict(session), indent=2, default=str)

    return json.dumps({"error": f"Unknown resource URI: {uri}"})


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "start_session":
            session = scratchpad.start_session(
                task=arguments["task"],
                document_paths=arguments.get("document_paths"),
                session_name=arguments.get("session_name")
            )
            result = {
                "success": True,
                "message": f"Research session started! I'm ready to help you with: {session.task}",
                "session_id": session.id,
                "session_name": session.name,
                "documents_to_process": len(session.documents),
                "hint": "Use save_notes to capture insights, mark_progress to track documents."
            }

        elif name == "save_notes":
            note = scratchpad.save_notes(
                content=arguments["content"],
                document_id=arguments.get("document_id"),
                tags=arguments.get("tags"),
                section=arguments.get("section")
            )
            result = {
                "success": True,
                "message": "Notes saved! They'll be here when you need them.",
                "note_id": note.id,
                "timestamp": note.timestamp,
                "section": note.section,
                "tags": note.tags
            }

        elif name == "get_notes":
            notes = scratchpad.get_notes(
                document_id=arguments.get("document_id"),
                tags=arguments.get("tags"),
                section=arguments.get("section"),
                session_id=arguments.get("session_id")
            )
            result = {
                "success": True,
                "count": len(notes),
                "notes": [asdict(n) for n in notes]
            }

        elif name == "mark_progress":
            doc = scratchpad.mark_progress(
                document_id=arguments["document_id"],
                status=arguments["status"],
                position=arguments.get("position"),
                notes=arguments.get("notes")
            )
            status_messages = {
                "not_started": "Queued up and ready when you are!",
                "in_progress": f"Making progress! Currently at: {doc.position or 'the beginning'}",
                "completed": "Nicely done! This one's all wrapped up.",
                "needs_review": "Flagged for another look later."
            }
            result = {
                "success": True,
                "message": status_messages.get(doc.status, "Progress updated!"),
                "document_id": doc.document_id,
                "status": doc.status,
                "position": doc.position
            }

        elif name == "get_progress":
            progress = scratchpad.get_progress(
                session_id=arguments.get("session_id")
            )
            if "error" in progress:
                result = {"success": False, "error": progress["error"]}
            else:
                docs = progress.get("documents", {})
                result = {
                    "success": True,
                    "message": (
                        f"You've completed {docs.get('completed', 0)} of {docs.get('total', 0)} documents "
                        f"({docs.get('progress_percent', 0)}%). "
                        f"Collected {progress.get('notes_count', 0)} notes so far!"
                    ),
                    **progress
                }

        elif name == "handover":
            handover_state = scratchpad.handover(
                summary=arguments.get("summary"),
                next_steps=arguments.get("next_steps")
            )
            result = {
                "success": True,
                "message": (
                    "All saved and ready for a fresh start! Here's where we left off:\n\n"
                    f"Summary: {handover_state.summary}\n\n"
                    f"Next steps: {', '.join(handover_state.next_steps) if handover_state.next_steps else 'Pick up where you left off!'}"
                ),
                "handover": asdict(handover_state),
                "hint": "Use resume_session with the session ID to continue later."
            }

        elif name == "resume_session":
            session = scratchpad.resume_session(
                session_id=arguments["session_id"]
            )
            last_handover = session.handovers[-1] if session.handovers else None
            progress = scratchpad.get_progress(session.id)

            result = {
                "success": True,
                "message": f"Welcome back! Resuming: {session.name or session.task}",
                "session_id": session.id,
                "task": session.task,
                "progress": progress,
                "last_handover": asdict(last_handover) if last_handover else None,
                "notes_count": len(session.notes)
            }

        elif name == "list_sessions":
            sessions = scratchpad.list_sessions(
                status=arguments.get("status"),
                limit=arguments.get("limit", 20)
            )
            result = {
                "success": True,
                "count": len(sessions),
                "sessions": sessions
            }

        elif name == "get_writing_context":
            context = scratchpad.get_writing_context(
                session_id=arguments.get("session_id"),
                format=arguments.get("format", "detailed")
            )
            if "error" in context:
                result = {"success": False, "error": context["error"]}
            else:
                result = {
                    "success": True,
                    "message": "Here's everything organized for writing!",
                    **context
                }

        else:
            result = {"success": False, "error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    except ValueError as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e),
            "hint": "Try starting a new session with start_session first."
        }, indent=2))]

    except Exception as e:
        logger.exception(f"Error in tool {name}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Something went wrong: {str(e)}",
            "hint": "Please try again or check the logs for details."
        }, indent=2))]


async def main():
    """Run the Scratchpad MCP server."""
    logger.info(f"Starting Scratchpad MCP server. Storage: {SCRATCHPAD_DIR}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
