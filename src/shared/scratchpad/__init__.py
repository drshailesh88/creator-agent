"""
Scratchpad - Shared infrastructure for long-form content creation.

The Scratchpad module provides a unified interface for any skill to manage
long-form content creation sessions with multiple documents. It handles:

- Session management: Start, pause, resume, and complete content creation tasks
- Note taking: Save and organize notes with citations while processing documents
- Progress tracking: Track progress through multiple source documents
- Handover: Handle LLM context refreshes seamlessly
- Document chunking: Split large documents into context-window-sized pieces

Example Usage:
    from shared.scratchpad import Scratchpad, Session, Document, Note

    # Create a scratchpad with file-based persistence
    scratchpad = Scratchpad(
        session_id="article-123",
        storage_dir="/path/to/sessions"
    )
    await scratchpad.initialize()

    # Start a new session
    session = await scratchpad.start_session(
        task="Write comprehensive article on cardiovascular health",
        documents=[
            "research_paper_1.pdf",
            "research_paper_2.pdf",
            "clinical_guidelines.pdf"
        ]
    )

    # Take notes while processing documents
    await scratchpad.save_notes(
        content="Statins reduce LDL cholesterol by 30-50%",
        document_id=session.documents[0].id,
        citations=["Smith et al., 2023, p. 15"]
    )

    # Track progress
    await scratchpad.mark_progress(
        document_id=session.documents[0].id,
        status="in_progress",
        position="page 10 of 25"
    )

    # Get handover state for context refresh
    handover = await scratchpad.handover()

    # Get all notes for writing
    all_notes = await scratchpad.get_all_notes()

Custom Backends:
    The scratchpad supports custom storage backends. Implement the
    StorageBackend abstract class to add support for Notion, databases,
    or other storage systems.

    from shared.scratchpad.backends import StorageBackend

    class NotionBackend(StorageBackend):
        async def save_session(self, session: Session) -> None:
            # Save to Notion...
            pass
        # ... implement other methods

    scratchpad = Scratchpad(
        session_id="my-session",
        backend=NotionBackend()
    )
"""

# Core scratchpad classes
from .models import Document, Note, Session
from .scratchpad import Scratchpad, InMemoryBackend, FileBackend
from .backends import StorageBackend

__all__ = [
    # Main scratchpad class
    "Scratchpad",
    # Session and content models
    "Session",
    "Document",
    "Note",
    # Storage backends
    "StorageBackend",
    "InMemoryBackend",
    "FileBackend",
]

# Document processing (chunking for context windows) - optional
try:
    from .document_processor import (
        DocumentChunker,
        DocumentChunk,
        ChunkingMethod,
        ProcessedDocument,
    )
    __all__.extend([
        "DocumentChunker",
        "DocumentChunk",
        "ChunkingMethod",
        "ProcessedDocument",
    ])
except ImportError:
    # Document processor requires the processor skill to be installed
    pass

# Context window management - optional
try:
    from .context_manager import (
        ContextManager,
        ContextUsageReport,
        ContextCategory,
        ContextEntry,
        MultiDocumentContextManager,
    )
    __all__.extend([
        "ContextManager",
        "ContextUsageReport",
        "ContextCategory",
        "ContextEntry",
        "MultiDocumentContextManager",
    ])
except ImportError:
    pass

# Reading strategies for multi-document processing - optional
try:
    from .reading_strategy import (
        ReadingStrategy,
        Document as StrategyDocument,  # Avoid conflict with models.Document
        DocumentPriority,
        ReadingPlan,
        AdaptiveReadingStrategy,
        simple_keyword_relevance,
    )
    __all__.extend([
        "ReadingStrategy",
        "StrategyDocument",
        "DocumentPriority",
        "ReadingPlan",
        "AdaptiveReadingStrategy",
        "simple_keyword_relevance",
    ])
except ImportError:
    pass

__version__ = "0.1.0"
