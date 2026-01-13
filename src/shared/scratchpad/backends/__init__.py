"""
Storage backends for the Scratchpad system.

This package contains the abstract base class and implementations
for various storage backends (SQLite, Notion, file-based, etc.).
"""

from .base import StorageBackend

__all__ = ["StorageBackend"]
