"""Notion storage backend for the scratchpad system.

Stores scratchpad data (sessions, notes, documents) in Notion databases
using the official Notion API client (notion-client package).
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from notion_client import AsyncClient
from notion_client.errors import APIResponseError, HTTPResponseError

from ..models import Session, Note, Document
from .base import StorageBackend
from .notion_schema import (
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
        session = Session(id="123", task="Research AI agents")
        await backend.save_session(session)

        # Load a session
        session = await backend.load_session("123")
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

        # Cache for page ID lookups (maps entity IDs to Notion page IDs)
        self._page_id_cache: Dict[str, str] = {}

    # ========================================================================
    # StorageBackend Interface Implementation
    # ========================================================================

    async def initialize(self) -> None:
        """
        Initialize the backend.

        Verifies that the configured databases are accessible.
        """
        required_dbs = ["sessions", "notes", "documents"]
        for db_name in required_dbs:
            if db_name not in self.database_ids:
                logger.warning(f"Database ID not configured for '{db_name}'")
                continue

            try:
                db_id = self.database_ids[db_name]
                await self._execute_with_retry(
                    f"verify_{db_name}_db",
                    self._client.databases.retrieve,
                    database_id=db_id,
                )
                logger.info(f"Verified access to {db_name} database: {db_id}")
            except Exception as e:
                logger.warning(f"Could not verify {db_name} database: {e}")

    async def save_session(self, session: Session) -> None:
        """
        Save a session to Notion.

        If the session already exists (has a cached page ID), it will be updated.
        Otherwise, a new page will be created.

        Args:
            session: The session to save
        """
        db_id = self._get_database_id("sessions")

        # Check if session already exists
        existing_page_id = self._page_id_cache.get(f"session:{session.id}")
        if not existing_page_id:
            existing_page_id = await self._get_session_page_id(session.id)

        properties = self._build_session_properties(session)

        if existing_page_id:
            # Update existing session
            await self._execute_with_retry(
                "update_session",
                self._client.pages.update,
                page_id=existing_page_id,
                properties=properties,
            )
            logger.info(f"Updated session {session.id}")
        else:
            # Create new session
            result = await self._execute_with_retry(
                "save_session",
                self._client.pages.create,
                parent={"database_id": db_id},
                properties=properties,
            )
            self._page_id_cache[f"session:{session.id}"] = result["id"]
            logger.info(f"Saved session {session.id} to Notion (page: {result['id']})")

    async def load_session(self, session_id: str) -> Optional[Session]:
        """
        Load a session from Notion by session ID.

        Args:
            session_id: The session ID to load

        Returns:
            The loaded Session object, or None if not found
        """
        db_id = self._get_database_id("sessions")

        # Query the database for the session
        filter_query = {
            "property": "Session ID",
            "title": {"equals": session_id}
        }

        results = await self.query_database(db_id, filter_query, page_size=1)

        if not results:
            return None

        page = results[0]
        return self._parse_session_from_page(page)

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session by archiving its Notion page.

        Args:
            session_id: The session ID to delete

        Returns:
            True if session was deleted, False if not found
        """
        page_id = await self._get_session_page_id(session_id)
        if not page_id:
            return False

        await self._execute_with_retry(
            "delete_session",
            self._client.pages.update,
            page_id=page_id,
            archived=True,
        )

        # Clear from cache
        self._page_id_cache.pop(f"session:{session_id}", None)
        logger.info(f"Deleted (archived) session {session_id}")
        return True

    async def list_sessions(self, status: Optional[str] = None) -> List[Session]:
        """
        List all sessions, optionally filtered by status.

        Args:
            status: Optional status filter (active, paused, complete)

        Returns:
            List of sessions matching the criteria
        """
        db_id = self._get_database_id("sessions")

        filter_query = None
        if status:
            filter_query = {
                "property": "Status",
                "select": {"equals": status}
            }

        # Sort by updated time descending
        sorts = [{"timestamp": "last_edited_time", "direction": "descending"}]

        results = await self.query_database(db_id, filter_query, sorts=sorts)

        sessions = []
        for page in results:
            try:
                session = self._parse_session_from_page(page)
                sessions.append(session)
            except Exception as e:
                logger.warning(f"Failed to parse session from page {page.get('id')}: {e}")

        return sessions

    async def save_note(self, session_id: str, note: Note) -> None:
        """
        Save a note to a session.

        Args:
            session_id: The session to add the note to
            note: The note to save
        """
        db_id = self._get_database_id("notes")

        properties = {
            "Note ID": build_title(note.id),
            "Content": build_rich_text(note.content),
        }

        if note.citations:
            properties["Citations"] = build_multi_select(note.citations)

        # Add session relation
        session_page_id = await self._get_session_page_id(session_id)
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

        self._page_id_cache[f"note:{note.id}"] = result["id"]
        logger.info(f"Saved note {note.id} to Notion (page: {result['id']})")

    async def get_notes(
        self,
        session_id: str,
        document_id: Optional[str] = None
    ) -> List[Note]:
        """
        Get notes for a session, optionally filtered by document.

        Args:
            session_id: The session to get notes from
            document_id: Optional document ID to filter by

        Returns:
            List of notes matching the criteria
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

        # Sort by created time
        sorts = [{"timestamp": "created_time", "direction": "ascending"}]

        results = await self.query_database(db_id, filter_query, sorts=sorts)

        notes = []
        for page in results:
            try:
                note = self._parse_note_from_page(page)
                notes.append(note)
            except Exception as e:
                logger.warning(f"Failed to parse note from page {page.get('id')}: {e}")

        return notes

    async def delete_note(self, session_id: str, note_id: str) -> bool:
        """
        Delete a specific note by archiving its Notion page.

        Args:
            session_id: The session containing the note
            note_id: The note to delete

        Returns:
            True if note was deleted, False if not found
        """
        page_id = await self._get_note_page_id(note_id)
        if not page_id:
            return False

        await self._execute_with_retry(
            "delete_note",
            self._client.pages.update,
            page_id=page_id,
            archived=True,
        )

        # Clear from cache
        self._page_id_cache.pop(f"note:{note_id}", None)
        logger.info(f"Deleted (archived) note {note_id}")
        return True

    async def update_document(self, session_id: str, document: Document) -> None:
        """
        Update a document's status and progress.

        Args:
            session_id: The session containing the document
            document: The document with updated information
        """
        db_id = self._get_database_id("documents")

        # Check if document already exists
        existing_page_id = await self._get_document_page_id(document.id)

        properties = {
            "Document ID": build_title(document.id),
            "Path": build_rich_text(document.path),
            "Title": build_rich_text(document.title),
            "Total Pages": build_number(document.total_pages),
            "Processed Pages": build_number(document.processed_pages),
            "Status": build_select(document.status),
            "Position": build_rich_text(document.position),
        }

        # Add session relation
        session_page_id = await self._get_session_page_id(session_id)
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
            logger.info(f"Updated document {document.id}")
        else:
            # Create new document
            result = await self._execute_with_retry(
                "save_document",
                self._client.pages.create,
                parent={"database_id": db_id},
                properties=properties,
            )
            self._page_id_cache[f"document:{document.id}"] = result["id"]
            logger.info(f"Saved document {document.id} to Notion (page: {result['id']})")

    async def close(self) -> None:
        """Close the Notion client connection and clear caches."""
        self._page_id_cache.clear()
        logger.info("Notion backend closed")

    # ========================================================================
    # Additional Methods (User-Requested)
    # ========================================================================

    async def update_session(self, session: Session) -> None:
        """
        Update an existing session in Notion.

        This is a convenience method that calls save_session.

        Args:
            session: The session to update
        """
        await self.save_session(session)

    async def append_to_note(self, note_id: str, content: str) -> None:
        """
        Append content to an existing note.

        Args:
            note_id: The note ID to append to
            content: The content to append
        """
        page_id = await self._get_note_page_id(note_id)
        if not page_id:
            raise NotionBackendError(
                message=f"Note not found: {note_id}",
                operation="append_to_note"
            )

        # Get the current content
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

    async def save_document_progress(self, doc: Document) -> None:
        """
        Save or update document progress in Notion.

        This requires the document to have session information available.
        Use update_document if you have the session_id separately.

        Args:
            doc: The document to save
        """
        # Extract session_id from the document's session relation if available
        # For now, we'll need to query based on the document
        db_id = self._get_database_id("documents")

        existing_page_id = await self._get_document_page_id(doc.id)

        properties = {
            "Document ID": build_title(doc.id),
            "Path": build_rich_text(doc.path),
            "Title": build_rich_text(doc.title),
            "Total Pages": build_number(doc.total_pages),
            "Processed Pages": build_number(doc.processed_pages),
            "Status": build_select(doc.status),
            "Position": build_rich_text(doc.position),
        }

        if existing_page_id:
            await self._execute_with_retry(
                "update_document_progress",
                self._client.pages.update,
                page_id=existing_page_id,
                properties=properties,
            )
            logger.info(f"Updated document progress for {doc.id}")
        else:
            result = await self._execute_with_retry(
                "save_document_progress",
                self._client.pages.create,
                parent={"database_id": db_id},
                properties=properties,
            )
            self._page_id_cache[f"document:{doc.id}"] = result["id"]
            logger.info(f"Saved document {doc.id} to Notion (page: {result['id']})")

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
                doc = self._parse_document_from_page(page)
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

        Args:
            session: The session to create

        Returns:
            The Notion page ID
        """
        db_id = self._get_database_id("sessions")
        properties = self._build_session_properties(session)

        result = await self._execute_with_retry(
            "create_session_page",
            self._client.pages.create,
            parent={"database_id": db_id},
            properties=properties,
        )

        page_id = result["id"]
        self._page_id_cache[f"session:{session.id}"] = page_id
        logger.info(f"Created session page {session.id} (page: {page_id})")
        return page_id

    async def update_page_content(self, page_id: str, content: str) -> None:
        """
        Update the content of a Notion page by appending blocks.

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

        Handles pagination automatically to retrieve all matching results.

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

        Implements exponential backoff for retryable errors and
        respects rate limit headers.

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

    def _build_session_properties(self, session: Session) -> Dict[str, Any]:
        """Build Notion properties for a session."""
        return {
            "Session ID": build_title(session.id),
            "Task": build_rich_text(session.task),
            "Status": build_select(session.status),
            "Context Refreshes": build_number(session.context_refreshes),
        }

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

    # ========================================================================
    # Page Parsing Helpers
    # ========================================================================

    def _parse_session_from_page(self, page: Dict[str, Any]) -> Session:
        """Parse a Session object from a Notion page."""
        props = page.get("properties", {})

        # Extract documents and notes from the page
        documents = []
        notes = []

        session = Session(
            id=extract_title(props.get("Session ID", {})),
            task=extract_rich_text(props.get("Task", {})),
            documents=documents,
            notes=notes,
            status=extract_select(props.get("Status", {})) or "active",
            context_refreshes=extract_number(props.get("Context Refreshes", {})),
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
        self._page_id_cache[f"session:{session.id}"] = page["id"]

        return session

    def _parse_document_from_page(self, page: Dict[str, Any]) -> Document:
        """Parse a Document object from a Notion page."""
        props = page.get("properties", {})

        doc = Document(
            id=extract_title(props.get("Document ID", {})),
            path=extract_rich_text(props.get("Path", {})),
            title=extract_rich_text(props.get("Title", {})),
            total_pages=extract_number(props.get("Total Pages", {})),
            processed_pages=extract_number(props.get("Processed Pages", {})),
            status=extract_select(props.get("Status", {})) or "pending",
            position=extract_rich_text(props.get("Position", {})),
        )

        # Cache the page ID
        self._page_id_cache[f"document:{doc.id}"] = page["id"]

        return doc

    def _parse_note_from_page(self, page: Dict[str, Any]) -> Note:
        """Parse a Note object from a Notion page."""
        props = page.get("properties", {})

        # Extract document relation if present
        doc_relations = extract_relation(props.get("Document", {}))
        document_id = doc_relations[0] if doc_relations else None

        note = Note(
            id=extract_title(props.get("Note ID", {})),
            document_id=document_id,
            content=extract_rich_text(props.get("Content", {})),
            citations=extract_multi_select(props.get("Citations", {})),
        )

        # Parse created time if available
        created_time = extract_created_time(props.get("Created", {}))
        if created_time:
            try:
                note.timestamp = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Cache the page ID
        self._page_id_cache[f"note:{note.id}"] = page["id"]

        return note

    # ========================================================================
    # Context Manager Support
    # ========================================================================

    async def __aenter__(self) -> "NotionBackend":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
