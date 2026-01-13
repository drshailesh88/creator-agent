"""Context window management for multi-turn document processing.

This module provides tools to track and manage context window usage,
enabling agents to process large documents across multiple turns while
knowing when to hand over to fresh context.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextCategory(str, Enum):
    """Categories of content in the context window."""

    SYSTEM_PROMPT = "system_prompt"
    DOCUMENT_CONTENT = "document_content"
    CONVERSATION = "conversation"
    NOTES = "notes"
    TOOL_RESULTS = "tool_results"
    OTHER = "other"


@dataclass
class ContextEntry:
    """A single entry in the context window."""

    category: ContextCategory
    token_count: int
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextUsageReport:
    """Report on current context window usage."""

    total_tokens: int
    max_tokens: int
    used_percentage: float
    remaining_tokens: int
    needs_handover: bool
    breakdown: Dict[str, int]
    entries: List[ContextEntry]

    @property
    def is_critical(self) -> bool:
        """Check if context usage is at critical level (>90%)."""
        return self.used_percentage > 90.0

    @property
    def is_healthy(self) -> bool:
        """Check if context usage is healthy (<60%)."""
        return self.used_percentage < 60.0

    def format_summary(self) -> str:
        """Format a human-readable summary of context usage."""
        status = "CRITICAL" if self.is_critical else "WARNING" if self.needs_handover else "OK"

        lines = [
            f"Context Usage: {self.used_percentage:.1f}% [{status}]",
            f"  Total: {self.total_tokens:,} / {self.max_tokens:,} tokens",
            f"  Remaining: {self.remaining_tokens:,} tokens",
            "",
            "Breakdown by category:",
        ]

        for category, tokens in sorted(
            self.breakdown.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            pct = (tokens / self.total_tokens * 100) if self.total_tokens > 0 else 0
            lines.append(f"  - {category}: {tokens:,} ({pct:.1f}%)")

        if self.needs_handover:
            lines.append("")
            lines.append("** Handover recommended to maintain response quality **")

        return "\n".join(lines)


class ContextManager:
    """
    Manages and tracks context window usage across agent turns.

    Helps agents know when they're approaching context limits and need
    to hand over to a fresh instance, while preserving important state
    in scratchpad notes.

    The default thresholds are calibrated for typical LLM context windows:
    - 100k total context
    - 80% threshold triggers handover warning
    - Reserve 20% for response generation
    """

    # Default maximum context tokens (Claude has 200k, but we're conservative)
    DEFAULT_MAX_TOKENS = 100000

    # Percentage at which to recommend handover
    HANDOVER_THRESHOLD = 80.0

    # Minimum reserved for response generation
    RESPONSE_RESERVE = 20000

    def __init__(
        self,
        max_context_tokens: int = DEFAULT_MAX_TOKENS,
        handover_threshold: float = HANDOVER_THRESHOLD,
        response_reserve: int = RESPONSE_RESERVE,
    ):
        """
        Initialize the context manager.

        Args:
            max_context_tokens: Maximum tokens available in context window.
            handover_threshold: Percentage at which to recommend handover.
            response_reserve: Tokens to reserve for response generation.
        """
        self.max_tokens = max_context_tokens
        self.handover_threshold = handover_threshold
        self.response_reserve = response_reserve

        self._entries: List[ContextEntry] = []
        self._current_usage = 0

    @property
    def current_usage(self) -> int:
        """Get current token usage."""
        return self._current_usage

    @property
    def effective_max(self) -> int:
        """Get effective maximum (accounting for response reserve)."""
        return self.max_tokens - self.response_reserve

    def can_fit(self, text: str) -> bool:
        """
        Check if text can fit in the remaining context.

        Args:
            text: The text to check.

        Returns:
            True if the text fits, False otherwise.
        """
        token_estimate = self._estimate_tokens(text)
        return (self._current_usage + token_estimate) <= self.effective_max

    def can_fit_tokens(self, tokens: int) -> bool:
        """
        Check if a given number of tokens can fit.

        Args:
            tokens: Number of tokens to check.

        Returns:
            True if they fit, False otherwise.
        """
        return (self._current_usage + tokens) <= self.effective_max

    def add_to_context(
        self,
        text: str,
        category: ContextCategory = ContextCategory.OTHER,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextEntry:
        """
        Track content added to context.

        Args:
            text: The text being added.
            category: Category of the content.
            description: Human-readable description.
            metadata: Additional metadata to store.

        Returns:
            The ContextEntry created.
        """
        token_count = self._estimate_tokens(text)

        entry = ContextEntry(
            category=category,
            token_count=token_count,
            description=description or f"{category.value} ({token_count} tokens)",
            metadata=metadata or {},
        )

        self._entries.append(entry)
        self._current_usage += token_count

        logger.debug(
            f"Added to context: {category.value} - {token_count} tokens "
            f"(total: {self._current_usage})"
        )

        return entry

    def add_tokens(
        self,
        tokens: int,
        category: ContextCategory = ContextCategory.OTHER,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextEntry:
        """
        Track tokens added to context (when token count is already known).

        Args:
            tokens: Number of tokens being added.
            category: Category of the content.
            description: Human-readable description.
            metadata: Additional metadata to store.

        Returns:
            The ContextEntry created.
        """
        entry = ContextEntry(
            category=category,
            token_count=tokens,
            description=description or f"{category.value} ({tokens} tokens)",
            metadata=metadata or {},
        )

        self._entries.append(entry)
        self._current_usage += tokens

        return entry

    def add_document_chunk(
        self,
        chunk_tokens: int,
        document_id: str,
        chunk_index: int,
        total_chunks: int,
    ) -> ContextEntry:
        """
        Convenience method to track document chunk addition.

        Args:
            chunk_tokens: Token count of the chunk.
            document_id: ID of the source document.
            chunk_index: Index of this chunk.
            total_chunks: Total chunks in the document.

        Returns:
            The ContextEntry created.
        """
        return self.add_tokens(
            tokens=chunk_tokens,
            category=ContextCategory.DOCUMENT_CONTENT,
            description=f"Document chunk {chunk_index + 1}/{total_chunks}",
            metadata={
                "document_id": document_id,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
            },
        )

    def get_remaining_capacity(self) -> int:
        """
        Get remaining token capacity.

        Returns:
            Number of tokens that can still be added.
        """
        return max(0, self.effective_max - self._current_usage)

    def get_usage_percentage(self) -> float:
        """
        Get current usage as a percentage of maximum.

        Returns:
            Usage percentage (0.0 to 100.0).
        """
        return (self._current_usage / self.max_tokens) * 100

    def needs_handover(self) -> bool:
        """
        Check if context is full enough to warrant handover.

        Returns:
            True if handover is recommended.
        """
        return self.get_usage_percentage() >= self.handover_threshold

    def is_full(self) -> bool:
        """
        Check if context is effectively full.

        Returns:
            True if no more content can be added safely.
        """
        return self._current_usage >= self.effective_max

    def reset(self) -> None:
        """
        Reset context tracking (call after handover).

        Clears all tracked entries and resets usage to zero.
        """
        self._entries = []
        self._current_usage = 0
        logger.info("Context manager reset")

    def get_usage_report(self) -> ContextUsageReport:
        """
        Get a detailed report of current context usage.

        Returns:
            ContextUsageReport with breakdown by category.
        """
        # Calculate breakdown by category
        breakdown: Dict[str, int] = {}
        for entry in self._entries:
            category_name = entry.category.value
            breakdown[category_name] = breakdown.get(category_name, 0) + entry.token_count

        return ContextUsageReport(
            total_tokens=self._current_usage,
            max_tokens=self.max_tokens,
            used_percentage=self.get_usage_percentage(),
            remaining_tokens=self.get_remaining_capacity(),
            needs_handover=self.needs_handover(),
            breakdown=breakdown,
            entries=self._entries.copy(),
        )

    def estimate_chunks_remaining(self, avg_chunk_tokens: int) -> int:
        """
        Estimate how many more document chunks can fit.

        Args:
            avg_chunk_tokens: Average token count per chunk.

        Returns:
            Estimated number of chunks that can still be added.
        """
        if avg_chunk_tokens <= 0:
            return 0
        return self.get_remaining_capacity() // avg_chunk_tokens

    def get_handover_summary(self) -> Dict[str, Any]:
        """
        Generate a summary for handover to next agent instance.

        Returns:
            Dictionary containing state to preserve across handover.
        """
        # Get document progress
        doc_entries = [
            e for e in self._entries
            if e.category == ContextCategory.DOCUMENT_CONTENT
        ]

        doc_progress = {}
        for entry in doc_entries:
            doc_id = entry.metadata.get("document_id")
            if doc_id:
                chunk_idx = entry.metadata.get("chunk_index", 0)
                total = entry.metadata.get("total_chunks", 1)

                if doc_id not in doc_progress or chunk_idx > doc_progress[doc_id]["last_chunk"]:
                    doc_progress[doc_id] = {
                        "last_chunk": chunk_idx,
                        "total_chunks": total,
                        "progress_pct": ((chunk_idx + 1) / total) * 100,
                    }

        return {
            "session_stats": {
                "total_tokens_processed": self._current_usage,
                "entries_count": len(self._entries),
            },
            "document_progress": doc_progress,
            "timestamp": datetime.now().isoformat(),
        }

    def _estimate_tokens(self, text: str) -> int:
        """Estimate tokens in text (words * 1.3)."""
        if not text:
            return 0
        return int(len(text.split()) * 1.3)

    def __repr__(self) -> str:
        return (
            f"ContextManager("
            f"usage={self._current_usage}/{self.max_tokens}, "
            f"pct={self.get_usage_percentage():.1f}%, "
            f"needs_handover={self.needs_handover()}"
            f")"
        )


class MultiDocumentContextManager(ContextManager):
    """
    Extended context manager for processing multiple documents.

    Adds features for:
    - Tracking progress across multiple documents
    - Prioritizing documents that fit in remaining space
    - Suggesting optimal reading order
    """

    def __init__(
        self,
        max_context_tokens: int = ContextManager.DEFAULT_MAX_TOKENS,
        **kwargs,
    ):
        super().__init__(max_context_tokens=max_context_tokens, **kwargs)
        self._document_queue: List[Dict[str, Any]] = []
        self._completed_documents: List[str] = []

    def queue_document(
        self,
        document_id: str,
        total_tokens: int,
        total_chunks: int,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a document to the processing queue.

        Args:
            document_id: Unique identifier for the document.
            total_tokens: Total tokens in the document.
            total_chunks: Number of chunks the document was split into.
            priority: Processing priority (higher = process first).
            metadata: Additional metadata about the document.
        """
        self._document_queue.append({
            "document_id": document_id,
            "total_tokens": total_tokens,
            "total_chunks": total_chunks,
            "chunks_processed": 0,
            "priority": priority,
            "metadata": metadata or {},
        })

    def mark_chunk_complete(self, document_id: str) -> None:
        """
        Mark a chunk as processed for a document.

        Args:
            document_id: ID of the document.
        """
        for doc in self._document_queue:
            if doc["document_id"] == document_id:
                doc["chunks_processed"] += 1

                # Check if document is complete
                if doc["chunks_processed"] >= doc["total_chunks"]:
                    self._completed_documents.append(document_id)

                break

    def get_next_document(self) -> Optional[Dict[str, Any]]:
        """
        Get the next document to process based on priority and fit.

        Returns:
            Document info dict, or None if queue is empty.
        """
        remaining = self.get_remaining_capacity()

        # Sort by priority, then by whether it fits
        candidates = [
            doc for doc in self._document_queue
            if doc["document_id"] not in self._completed_documents
            and doc["chunks_processed"] < doc["total_chunks"]
        ]

        if not candidates:
            return None

        # Prefer documents that can complete in remaining space
        def sort_key(doc):
            remaining_tokens = (
                doc["total_tokens"] *
                (doc["total_chunks"] - doc["chunks_processed"]) /
                doc["total_chunks"]
            )
            fits = remaining_tokens <= remaining
            return (-doc["priority"], -fits, remaining_tokens)

        candidates.sort(key=sort_key)
        return candidates[0] if candidates else None

    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get status of the document queue.

        Returns:
            Dictionary with queue statistics.
        """
        total_docs = len(self._document_queue)
        completed = len(self._completed_documents)

        in_progress = [
            doc for doc in self._document_queue
            if doc["document_id"] not in self._completed_documents
            and doc["chunks_processed"] > 0
        ]

        pending = [
            doc for doc in self._document_queue
            if doc["document_id"] not in self._completed_documents
            and doc["chunks_processed"] == 0
        ]

        return {
            "total_documents": total_docs,
            "completed": completed,
            "in_progress": len(in_progress),
            "pending": len(pending),
            "completed_ids": self._completed_documents.copy(),
        }
