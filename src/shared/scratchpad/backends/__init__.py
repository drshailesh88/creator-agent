"""
Storage backends for the Scratchpad system.

This package contains the abstract base class and implementations
for various storage backends (SQLite, Notion, file-based, etc.).
"""

from .base import StorageBackend
from .notion import NotionBackend, NotionBackendError, RetryConfig
from .notion_schema import (
    SESSIONS_SCHEMA,
    DOCUMENTS_SCHEMA,
    NOTES_SCHEMA,
    SESSION_FIELD_MAP,
    DOCUMENT_FIELD_MAP,
    NOTE_FIELD_MAP,
    build_sessions_properties,
    build_documents_properties,
    build_notes_properties,
)

__all__ = [
    # Base class
    "StorageBackend",
    # Notion backend
    "NotionBackend",
    "NotionBackendError",
    "RetryConfig",
    # Notion schemas
    "SESSIONS_SCHEMA",
    "DOCUMENTS_SCHEMA",
    "NOTES_SCHEMA",
    "SESSION_FIELD_MAP",
    "DOCUMENT_FIELD_MAP",
    "NOTE_FIELD_MAP",
    "build_sessions_properties",
    "build_documents_properties",
    "build_notes_properties",
]
