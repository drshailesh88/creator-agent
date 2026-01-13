"""Notion storage backend for the scratchpad system.

Stores scratchpad data (sessions, notes, documents) in Notion databases
using the official Notion API client.
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Generic
from uuid import uuid4

from notion_client import AsyncClient
from notion_client.errors import APIResponseError, HTTPResponseError

from .notion_schema import (
    SESSION_FIELD_MAP,
    DOCUMENT_FIELD_MAP,
    NOTE_FIELD_MAP,
    extract_rich_text,
    extract_title,
    extract_select,
    extract_multi_select,
    extract_number,
    extract_relation,
    extract_created_time,
    extract_last_edited_time,
    build_rich_text,
    build_title,
    build_select,
    build_multi_select,
    build_number,
    build_relation,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Session:
    """Represents a scratchpad session."""
    session_id: str
    task: str
    status: str = "active"  # active, paused, complete
    documents: List[str] = field(default_factory=list)  # Document IDs
    notes: List[str] = field(default_factory=list)  # Note IDs
    context_refreshes: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    notion_page_id: Optional[str] = None  # Notion page ID for updates

    @classmethod
    def create(cls, task: str) -> "Session":
        """Create a new session with a generated ID."""
        return cls(
            session_id=f"session_{uuid4().hex[:12]}",
            task=task,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )


@dataclass
class Document:
    """Represents a document being processed in a session."""
    document_id: str
    session_id: str
    path: str
    title: str = ""
    total_pages: int = 0
    processed_pages: int = 0
    status: str = "pending"  # pending, in_progress, complete
    position: str = ""  # JSON or string representation of current position
    notion_page_id: Optional[str] = None

    @classmethod
    def create(cls, session_id: str, path: str, title: str = "", total_pages: int = 0) -> "Document":
        """Create a new document with a generated ID."""
        return cls(
            document_id=f"doc_{uuid4().hex[:12]}",
            session_id=session_id,
            path=path,
            title=title or path.split("/")[-1],
            total_pages=total_pages,
        )


@dataclass
class Note:
    """Represents a note taken during a session."""
    note_id: str
    session_id: str
    content: str
    document_id: Optional[str] = None
    citations: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    notion_page_id: Optional[str] = None

    @classmethod
    def create(
        cls,
        session_id: str,
        content: str,
        document_id: Optional[str] = None,
        citations: Optional[List[str]] = None
    ) -> "Note":
        """Create a new note with a generated ID."""
        return cls(
            note_id=f"note_{uuid4().hex[:12]}",
            session_id=session_id,
            content=content,
            document_id=document_id,
            citations=citations or [],
            created_at=datetime.utcnow(),
        )


# ============================================================================
# Base Storage Backend Interface
# ============================================================================

class StorageBackend(ABC):
    """Abstract base class for scratchpad storage backends."""

    @abstractmethod
    async def save_session(self, session: Session) -> None:
        """Save a new session."""
        pass

    @abstractmethod
    async def load_session(self, session_id: str) -> Session:
        """Load a session by ID."""
        pass

    @abstractmethod
    async def update_session(self, session: Session) -> None:
        """Update an existing session."""
        pass

    @abstractmethod
    async def save_note(self, note: Note) -> None:
        """Save a new note."""
        pass

    @abstractmethod
    async def get_notes(
        self,
        session_id: str,
        document_id: Optional[str] = None
    ) -> List[Note]:
        """Get notes for a session, optionally filtered by document."""
        pass

    @abstractmethod
    async def append_to_note(self, note_id: str, content: str) -> None:
        """Append content to an existing note."""
        pass

    @abstractmethod
    async def save_document_progress(self, doc: Document) -> None:
        """Save or update document progress."""
        pass

    @abstractmethod
    async def get_documents(self, session_id: str) -> List[Document]:
        """Get all documents for a session."""
        pass


# ============================================================================
# Notion Backend Errors
# ============================================================================

@dataclass
class NotionBackendError(Exception):
    """Custom exception for Notion backend errors."""
    message: str
    operation: str
    status_code: Optional[int] = None
    notion_code: Optional[str] = None
    retry_after: Optional[float] = None

    def __str__(self) -> str:
        return f"[{self.operation}] {self.message}"


# ============================================================================
# Retry Configuration
# ============================================================================

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retryable_status_codes: tuple = (429, 500, 502, 503, 504)

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt using exponential backoff."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        return delay


# ============================================================================
# Notion Backend Implementation
# ============================================================================

class NotionBackend(StorageBackend):
    """
    Notion storage backend for the scratchpad system.

    Stores scratchpad data in Notion databases using the official
    Notion API client (notion-client package).

    Usage:
        backend = NotionBackend(
            api_key="secret_xxx",
            database_ids={
                "sessions": "notion-db-id-for-sessions",
                "notes": "notion-db-id-for-notes",
                "documents": "notion-db-id-for-documents"
            }
        )

        # Save a session
        session = Session.create(task="Research AI agents")
        await backend.save_session(session)

        # Load a session
        session = await backend.load_session("session_abc123")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        database_ids: Optional[Dict[str, str]] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        """
        Initialize the Notion backend.

        Args:
            api_key: Notion API key. If not provided, reads from NOTION_API_KEY env var.
            database_ids: Dictionary mapping database names to Notion database IDs:
                {
                    "sessions": "notion-db-id-for-sessions",
                    "notes": "notion-db-id-for-notes",
                    "documents": "notion-db-id-for-documents"
                }
            retry_config: Configuration for retry behavior.
        """
        self.api_key = api_key or os.environ.get("NOTION_API_KEY")
        if not self.api_key:
            raise NotionBackendError(
                message="Notion API key not provided. Set NOTION_API_KEY environment variable.",
                operation="init"
            )

        self.database_ids = database_ids or {}
        self.retry_config = retry_config or RetryConfig()

        # Initialize the async Notion client
        self._client = AsyncClient(auth=self.api_key)

        # Cache for page ID lookups
        self._page_id_cache: Dict[str, str] = {}

    # ========================================================================
    # Internal Helper Methods
    # ========================================================================

    def _get_database_id(self, db_name: str) -> str:
        """Get the database ID for a given database name."""
        db_id = self.database_ids.get(db_name)
        if not db_id:
            raise NotionBackendError(
                message=f"Database ID not configured for '{db_name}'. "
                        f"Available: {list(self.database_ids.keys())}",
                operation="get_database_id"
            )
        return db_id

    async def _execute_with_retry(
        self,
        operation: str,
        func,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a Notion API call with retry logic.

        Args:
            operation: Name of the operation for error messages
            func: The async function to call
            *args, **kwargs: Arguments to pass to the function

        Returns:
            The result of the function call

        Raises:
            NotionBackendError: If all retries fail
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self.retry_config.get_delay(attempt - 1)
                    logger.info(
                        f"Retrying {operation} after {delay:.1f}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(delay)

                return await func(*args, **kwargs)

            except HTTPResponseError as e:
                last_error = e
                logger.warning(
                    f"Notion API error during {operation} "
                    f"(attempt {attempt + 1}): {e.status} - {e.body}"
                )

                # Check if we should retry
                if e.status not in self.retry_config.retryable_status_codes:
                    break

                # Handle rate limiting
                if e.status == 429:
                    retry_after = float(e.headers.get("Retry-After", 5))
                    await asyncio.sleep(retry_after)

            except APIResponseError as e:
                last_error = e
                logger.warning(
                    f"Notion API response error during {operation} "
                    f"(attempt {attempt + 1}): {e.code} - {e.message}"
                )

                # Don't retry on validation errors
                if e.code in ("validation_error", "invalid_json", "unauthorized"):
                    break

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Unexpected error during {operation} (attempt {attempt + 1}): {e}"
                )

        # All retries failed
        error_msg = str(last_error) if last_error else "Unknown error"
        status_code = None
        notion_code = None

        if isinstance(last_error, HTTPResponseError):
            status_code = last_error.status
        elif isinstance(last_error, APIResponseError):
            notion_code = last_error.code

        raise NotionBackendError(
            message=f"Operation failed after {self.retry_config.max_retries + 1} attempts: {error_msg}",
            operation=operation,
            status_code=status_code,
            notion_code=notion_code,
        )

    # ========================================================================
    # Session Methods
    # ========================================================================

    async def save_session(self, session: Session) -> None:
        """
        Save a new session to Notion.

        Args:
            session: The session to save
        """
        db_id = self._get_database_id("sessions")

        properties = {
            "Session ID": build_title(session.session_id),
            "Task": build_rich_text(session.task),
            "Status": build_select(session.status),
            "Context Refreshes": build_number(session.context_refreshes),
        }

        # Add relations if we have them
        if session.documents:
            doc_page_ids = await self._get_page_ids_for_documents(session.documents)
            if doc_page_ids:
                properties["Documents"] = build_relation(doc_page_ids)

        if session.notes:
            note_page_ids = await self._get_page_ids_for_notes(session.notes)
            if note_page_ids:
                properties["Notes"] = build_relation(note_page_ids)

        result = await self._execute_with_retry(
            "save_session",
            self._client.pages.create,
            parent={"database_id": db_id},
            properties=properties,
        )

        # Cache the page ID
        session.notion_page_id = result["id"]
        self._page_id_cache[f"session:{session.session_id}"] = result["id"]

        logger.info(f"Saved session {session.session_id} to Notion (page: {result['id']})")

    async def load_session(self, session_id: str) -> Session:
        """
        Load a session from Notion by session ID.

        Args:
            session_id: The session ID to load

        Returns:
            The loaded Session object

        Raises:
            NotionBackendError: If session not found or error occurs
        """
        db_id = self._get_database_id("sessions")

        # Query the database for the session
        filter_query = {
            "property": "Session ID",
            "title": {"equals": session_id}
        }

        results = await self.query_database(db_id, filter_query)

        if not results:
            raise NotionBackendError(
                message=f"Session not found: {session_id}",
                operation="load_session"
            )

        page = results[0]
        return self._parse_session_from_page(page)

    async def update_session(self, session: Session) -> None:
        """
        Update an existing session in Notion.

        Args:
            session: The session to update
        """
        # Get the page ID
        page_id = session.notion_page_id
        if not page_id:
            page_id = await self._get_session_page_id(session.session_id)

        if not page_id:
            raise NotionBackendError(
                message=f"Cannot update session {session.session_id}: page not found",
                operation="update_session"
            )

        properties = {
            "Task": build_rich_text(session.task),
            "Status": build_select(session.status),
            "Context Refreshes": build_number(session.context_refreshes),
        }

        # Update relations if we have them
        if session.documents:
            doc_page_ids = await self._get_page_ids_for_documents(session.documents)
            if doc_page_ids:
                properties["Documents"] = build_relation(doc_page_ids)

        if session.notes:
            note_page_ids = await self._get_page_ids_for_notes(session.notes)
            if note_page_ids:
                properties["Notes"] = build_relation(note_page_ids)

        await self._execute_with_retry(
            "update_session",
            self._client.pages.update,
            page_id=page_id,
            properties=properties,
        )

        logger.info(f"Updated session {session.session_id}")

    # ========================================================================
    # Note Methods
    # ========================================================================

    async def save_note(self, note: Note) -> None:
        """
        Save a new note to Notion.

        Args:
            note: The note to save
        """
        db_id = self._get_database_id("notes")

        properties = {
            "Note ID": build_title(note.note_id),
            "Content": build_rich_text(note.content),
        }

        if note.citations:
            properties["Citations"] = build_multi_select(note.citations)

        # Add session relation
        session_page_id = await self._get_session_page_id(note.session_id)
        if session_page_id:
            properties["Session"] = build_relation([session_page_id])

        # Add document relation if specified
        if note.document_id:
            doc_page_id = await self._get_document_page_id(note.document_id)
            if doc_page_id:
                properties["Document"] = build_relation([doc_page_id])

        result = await self._execute_with_retry(
            "save_note",
            self._client.pages.create,
            parent={"database_id": db_id},
            properties=properties,
        )

        # Cache the page ID
        note.notion_page_id = result["id"]
        self._page_id_cache[f"note:{note.note_id}"] = result["id"]

        logger.info(f"Saved note {note.note_id} to Notion (page: {result['id']})")

    async def get_notes(
        self,
        session_id: str,
        document_id: Optional[str] = None
    ) -> List[Note]:
        """
        Get notes for a session, optionally filtered by document.

        Args:
            session_id: The session ID to get notes for
            document_id: Optional document ID to filter by

        Returns:
            List of Note objects
        """
        db_id = self._get_database_id("notes")

        # Build filter - need to filter by session relation
        session_page_id = await self._get_session_page_id(session_id)
        if not session_page_id:
            logger.warning(f"Session {session_id} not found, returning empty notes list")
            return []

        filter_conditions = [
            {
                "property": "Session",
                "relation": {"contains": session_page_id}
            }
        ]

        # Add document filter if specified
        if document_id:
            doc_page_id = await self._get_document_page_id(document_id)
            if doc_page_id:
                filter_conditions.append({
                    "property": "Document",
                    "relation": {"contains": doc_page_id}
                })

        filter_query = {"and": filter_conditions} if len(filter_conditions) > 1 else filter_conditions[0]

        results = await self.query_database(db_id, filter_query)

        notes = []
        for page in results:
            try:
                note = self._parse_note_from_page(page, session_id, document_id)
                notes.append(note)
            except Exception as e:
                logger.warning(f"Failed to parse note from page {page.get('id')}: {e}")

        return notes

    async def append_to_note(self, note_id: str, content: str) -> None:
        """
        Append content to an existing note.

        Args:
            note_id: The note ID to append to
            content: The content to append
        """
        # Get the page ID
        page_id = await self._get_note_page_id(note_id)
        if not page_id:
            raise NotionBackendError(
                message=f"Note not found: {note_id}",
                operation="append_to_note"
            )

        # First, get the current content
        page = await self._execute_with_retry(
            "get_note_page",
            self._client.pages.retrieve,
            page_id=page_id,
        )

        current_content = extract_rich_text(page["properties"].get("Content", {}))
        new_content = current_content + "\n" + content if current_content else content

        # Update with appended content
        await self._execute_with_retry(
            "append_to_note",
            self._client.pages.update,
            page_id=page_id,
            properties={"Content": build_rich_text(new_content)},
        )

        logger.info(f"Appended content to note {note_id}")

    # ========================================================================
    # Document Methods
    # ========================================================================

    async def save_document_progress(self, doc: Document) -> None:
        """
        Save or update document progress in Notion.

        If the document doesn't exist, it will be created.
        If it exists, it will be updated.

        Args:
            doc: The document to save
        """
        db_id = self._get_database_id("documents")

        # Check if document already exists
        existing_page_id = await self._get_document_page_id(doc.document_id)

        properties = {
            "Document ID": build_title(doc.document_id),
            "Path": build_rich_text(doc.path),
            "Title": build_rich_text(doc.title),
            "Total Pages": build_number(doc.total_pages),
            "Processed Pages": build_number(doc.processed_pages),
            "Status": build_select(doc.status),
            "Position": build_rich_text(doc.position),
        }

        # Add session relation
        session_page_id = await self._get_session_page_id(doc.session_id)
        if session_page_id:
            properties["Session"] = build_relation([session_page_id])

        if existing_page_id:
            # Update existing document
            await self._execute_with_retry(
                "update_document",
                self._client.pages.update,
                page_id=existing_page_id,
                properties=properties,
            )
            doc.notion_page_id = existing_page_id
            logger.info(f"Updated document {doc.document_id}")
        else:
            # Create new document
            result = await self._execute_with_retry(
                "save_document",
                self._client.pages.create,
                parent={"database_id": db_id},
                properties=properties,
            )
            doc.notion_page_id = result["id"]
            self._page_id_cache[f"document:{doc.document_id}"] = result["id"]
            logger.info(f"Saved document {doc.document_id} to Notion (page: {result['id']})")

    async def get_documents(self, session_id: str) -> List[Document]:
        """
        Get all documents for a session.

        Args:
            session_id: The session ID to get documents for

        Returns:
            List of Document objects
        """
        db_id = self._get_database_id("documents")

        # Get session page ID for relation filter
        session_page_id = await self._get_session_page_id(session_id)
        if not session_page_id:
            logger.warning(f"Session {session_id} not found, returning empty documents list")
            return []

        filter_query = {
            "property": "Session",
            "relation": {"contains": session_page_id}
        }

        results = await self.query_database(db_id, filter_query)

        documents = []
        for page in results:
            try:
                doc = self._parse_document_from_page(page, session_id)
                documents.append(doc)
            except Exception as e:
                logger.warning(f"Failed to parse document from page {page.get('id')}: {e}")

        return documents

    # ========================================================================
    # Notion-Specific Helper Methods
    # ========================================================================

    async def create_session_page(self, session: Session) -> str:
        """
        Create a session page in Notion and return the page ID.

        This is an alias for save_session that returns the page ID.

        Args:
            session: The session to create

        Returns:
            The Notion page ID
        """
        await self.save_session(session)
        return session.notion_page_id

    async def update_page_content(self, page_id: str, content: str) -> None:
        """
        Update the content of a Notion page.

        This appends content blocks to the page body.

        Args:
            page_id: The Notion page ID
            content: The content to add
        """
        # Split content into chunks (Notion has a 2000 char limit per block)
        chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]

        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": chunk}}
                    ]
                }
            }
            for chunk in chunks
        ]

        await self._execute_with_retry(
            "update_page_content",
            self._client.blocks.children.append,
            block_id=page_id,
            children=children,
        )

        logger.info(f"Updated page content for {page_id}")

    async def query_database(
        self,
        db_id: str,
        filter_query: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query a Notion database with pagination support.

        Args:
            db_id: The database ID to query
            filter_query: Optional filter query
            sorts: Optional sort configuration
            page_size: Number of results per page (max 100)

        Returns:
            List of all matching pages
        """
        all_results = []
        has_more = True
        start_cursor = None

        while has_more:
            query_kwargs = {
                "database_id": db_id,
                "page_size": min(page_size, 100),
            }

            if filter_query:
                query_kwargs["filter"] = filter_query

            if sorts:
                query_kwargs["sorts"] = sorts

            if start_cursor:
                query_kwargs["start_cursor"] = start_cursor

            response = await self._execute_with_retry(
                "query_database",
                self._client.databases.query,
                **query_kwargs,
            )

            all_results.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")

            logger.debug(
                f"Queried database {db_id}: got {len(response.get('results', []))} results, "
                f"has_more={has_more}"
            )

        return all_results

    # ========================================================================
    # Page ID Lookup Helpers
    # ========================================================================

    async def _get_session_page_id(self, session_id: str) -> Optional[str]:
        """Get the Notion page ID for a session."""
        cache_key = f"session:{session_id}"
        if cache_key in self._page_id_cache:
            return self._page_id_cache[cache_key]

        db_id = self._get_database_id("sessions")
        results = await self.query_database(
            db_id,
            {"property": "Session ID", "title": {"equals": session_id}},
            page_size=1,
        )

        if results:
            page_id = results[0]["id"]
            self._page_id_cache[cache_key] = page_id
            return page_id

        return None

    async def _get_document_page_id(self, document_id: str) -> Optional[str]:
        """Get the Notion page ID for a document."""
        cache_key = f"document:{document_id}"
        if cache_key in self._page_id_cache:
            return self._page_id_cache[cache_key]

        db_id = self._get_database_id("documents")
        results = await self.query_database(
            db_id,
            {"property": "Document ID", "title": {"equals": document_id}},
            page_size=1,
        )

        if results:
            page_id = results[0]["id"]
            self._page_id_cache[cache_key] = page_id
            return page_id

        return None

    async def _get_note_page_id(self, note_id: str) -> Optional[str]:
        """Get the Notion page ID for a note."""
        cache_key = f"note:{note_id}"
        if cache_key in self._page_id_cache:
            return self._page_id_cache[cache_key]

        db_id = self._get_database_id("notes")
        results = await self.query_database(
            db_id,
            {"property": "Note ID", "title": {"equals": note_id}},
            page_size=1,
        )

        if results:
            page_id = results[0]["id"]
            self._page_id_cache[cache_key] = page_id
            return page_id

        return None

    async def _get_page_ids_for_documents(self, document_ids: List[str]) -> List[str]:
        """Get Notion page IDs for a list of document IDs."""
        page_ids = []
        for doc_id in document_ids:
            page_id = await self._get_document_page_id(doc_id)
            if page_id:
                page_ids.append(page_id)
        return page_ids

    async def _get_page_ids_for_notes(self, note_ids: List[str]) -> List[str]:
        """Get Notion page IDs for a list of note IDs."""
        page_ids = []
        for note_id in note_ids:
            page_id = await self._get_note_page_id(note_id)
            if page_id:
                page_ids.append(page_id)
        return page_ids

    # ========================================================================
    # Page Parsing Helpers
    # ========================================================================

    def _parse_session_from_page(self, page: Dict[str, Any]) -> Session:
        """Parse a Session object from a Notion page."""
        props = page.get("properties", {})

        session = Session(
            session_id=extract_title(props.get("Session ID", {})),
            task=extract_rich_text(props.get("Task", {})),
            status=extract_select(props.get("Status", {})) or "active",
            documents=extract_relation(props.get("Documents", {})),
            notes=extract_relation(props.get("Notes", {})),
            context_refreshes=extract_number(props.get("Context Refreshes", {})),
            notion_page_id=page["id"],
        )

        # Parse timestamps if available
        created_time = extract_created_time(props.get("Created", {}))
        if created_time:
            try:
                session.created_at = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
            except ValueError:
                pass

        updated_time = extract_last_edited_time(props.get("Updated", {}))
        if updated_time:
            try:
                session.updated_at = datetime.fromisoformat(updated_time.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Cache the page ID
        self._page_id_cache[f"session:{session.session_id}"] = page["id"]

        return session

    def _parse_document_from_page(
        self,
        page: Dict[str, Any],
        session_id: str
    ) -> Document:
        """Parse a Document object from a Notion page."""
        props = page.get("properties", {})

        doc = Document(
            document_id=extract_title(props.get("Document ID", {})),
            session_id=session_id,
            path=extract_rich_text(props.get("Path", {})),
            title=extract_rich_text(props.get("Title", {})),
            total_pages=extract_number(props.get("Total Pages", {})),
            processed_pages=extract_number(props.get("Processed Pages", {})),
            status=extract_select(props.get("Status", {})) or "pending",
            position=extract_rich_text(props.get("Position", {})),
            notion_page_id=page["id"],
        )

        # Cache the page ID
        self._page_id_cache[f"document:{doc.document_id}"] = page["id"]

        return doc

    def _parse_note_from_page(
        self,
        page: Dict[str, Any],
        session_id: str,
        document_id: Optional[str] = None
    ) -> Note:
        """Parse a Note object from a Notion page."""
        props = page.get("properties", {})

        note = Note(
            note_id=extract_title(props.get("Note ID", {})),
            session_id=session_id,
            content=extract_rich_text(props.get("Content", {})),
            document_id=document_id,
            citations=extract_multi_select(props.get("Citations", {})),
            notion_page_id=page["id"],
        )

        # Parse created time if available
        created_time = extract_created_time(props.get("Created", {}))
        if created_time:
            try:
                note.created_at = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Cache the page ID
        self._page_id_cache[f"note:{note.note_id}"] = page["id"]

        return note

    # ========================================================================
    # Context Manager Support
    # ========================================================================

    async def close(self) -> None:
        """Close the Notion client connection."""
        # The notion-client handles connection pooling internally
        # This is a placeholder for any cleanup needed
        self._page_id_cache.clear()
        logger.info("Notion backend closed")

    async def __aenter__(self) -> "NotionBackend":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
