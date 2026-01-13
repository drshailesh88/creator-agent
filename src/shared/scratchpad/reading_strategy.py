"""Smart reading strategies for multi-document processing.

This module provides various strategies for ordering and processing
multiple documents efficiently within context window constraints.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DocumentPriority(str, Enum):
    """Priority levels for document processing."""

    CRITICAL = "critical"  # Must be processed first
    HIGH = "high"  # Process early
    NORMAL = "normal"  # Default priority
    LOW = "low"  # Process if time allows
    BACKGROUND = "background"  # Process only if nothing else


# Priority to numeric value mapping
PRIORITY_VALUES = {
    DocumentPriority.CRITICAL: 100,
    DocumentPriority.HIGH: 75,
    DocumentPriority.NORMAL: 50,
    DocumentPriority.LOW: 25,
    DocumentPriority.BACKGROUND: 10,
}


@dataclass
class Document:
    """Represents a document for reading strategy planning."""

    id: str
    path: str
    token_count: int
    chunk_count: int
    priority: DocumentPriority = DocumentPriority.NORMAL
    relevance_score: float = 0.0  # 0.0 to 1.0, set by relevance analysis
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Processing state
    chunks_read: int = 0
    is_complete: bool = False

    @property
    def remaining_chunks(self) -> int:
        """Get number of chunks not yet read."""
        return max(0, self.chunk_count - self.chunks_read)

    @property
    def remaining_tokens(self) -> int:
        """Estimate remaining tokens to read."""
        if self.chunk_count == 0:
            return 0
        avg_tokens_per_chunk = self.token_count / self.chunk_count
        return int(self.remaining_chunks * avg_tokens_per_chunk)

    @property
    def progress(self) -> float:
        """Get reading progress as fraction (0.0 to 1.0)."""
        if self.chunk_count == 0:
            return 1.0
        return self.chunks_read / self.chunk_count

    @property
    def filename(self) -> str:
        """Get just the filename from path."""
        return Path(self.path).name

    def mark_chunk_read(self) -> None:
        """Mark one chunk as read."""
        self.chunks_read += 1
        if self.chunks_read >= self.chunk_count:
            self.is_complete = True


@dataclass
class ReadingPlan:
    """A plan for reading multiple documents."""

    documents: List[Document]
    strategy_name: str
    estimated_total_tokens: int
    estimated_turns: int  # Estimated number of context windows needed

    def get_next_document(self) -> Optional[Document]:
        """Get the next document to read."""
        for doc in self.documents:
            if not doc.is_complete:
                return doc
        return None

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get summary of reading progress."""
        completed = [d for d in self.documents if d.is_complete]
        in_progress = [d for d in self.documents if not d.is_complete and d.chunks_read > 0]
        pending = [d for d in self.documents if d.chunks_read == 0]

        tokens_read = sum(
            d.token_count if d.is_complete else
            int(d.token_count * d.progress)
            for d in self.documents
        )

        return {
            "total_documents": len(self.documents),
            "completed": len(completed),
            "in_progress": len(in_progress),
            "pending": len(pending),
            "tokens_read": tokens_read,
            "tokens_remaining": self.estimated_total_tokens - tokens_read,
            "overall_progress": tokens_read / self.estimated_total_tokens if self.estimated_total_tokens > 0 else 1.0,
        }


class ReadingStrategy:
    """
    Strategies for processing multiple documents efficiently.

    Provides various ordering strategies to optimize document processing
    based on different priorities: completing more documents, processing
    most relevant first, or balancing across multiple documents.
    """

    @staticmethod
    def sequential(documents: List[Document]) -> List[Document]:
        """
        Process documents in the order given.

        Simple strategy that maintains original order. Good for:
        - Documents that should be read in a specific sequence
        - When order was already determined by user

        Args:
            documents: List of documents to order.

        Returns:
            Documents in original order.
        """
        return documents.copy()

    @staticmethod
    def by_priority(documents: List[Document]) -> List[Document]:
        """
        Process documents by their priority level.

        Higher priority documents are processed first. Good for:
        - Mixed-priority document sets
        - When some documents are more important than others

        Args:
            documents: List of documents to order.

        Returns:
            Documents sorted by priority (highest first).
        """
        return sorted(
            documents,
            key=lambda d: PRIORITY_VALUES.get(d.priority, 50),
            reverse=True,
        )

    @staticmethod
    def by_relevance(
        documents: List[Document],
        query: str,
        relevance_fn: Optional[Callable[[Document, str], float]] = None,
    ) -> List[Document]:
        """
        Process most relevant documents first.

        Uses relevance scoring to prioritize documents most likely to
        contain useful information for the query. Good for:
        - Research tasks where relevance varies
        - Large document sets with limited time

        Args:
            documents: List of documents to order.
            query: The query/task to score relevance against.
            relevance_fn: Optional function to compute relevance.
                         If not provided, uses existing relevance_score.

        Returns:
            Documents sorted by relevance (highest first).
        """
        if relevance_fn:
            # Compute relevance scores
            for doc in documents:
                doc.relevance_score = relevance_fn(doc, query)

        return sorted(
            documents,
            key=lambda d: d.relevance_score,
            reverse=True,
        )

    @staticmethod
    def by_size(
        documents: List[Document],
        ascending: bool = True,
    ) -> List[Document]:
        """
        Process documents by size (token count).

        Processing smallest first maximizes documents completed before
        hitting context limits. Processing largest first ensures the
        biggest documents get full attention.

        Args:
            documents: List of documents to order.
            ascending: If True, process smallest first (default).
                      If False, process largest first.

        Returns:
            Documents sorted by size.
        """
        return sorted(
            documents,
            key=lambda d: d.token_count,
            reverse=not ascending,
        )

    @staticmethod
    def by_completion(documents: List[Document]) -> List[Document]:
        """
        Prioritize documents closest to completion.

        Ensures partial progress is finished before starting new docs.
        Good for:
        - Resuming after context handover
        - Maximizing completed document count

        Args:
            documents: List of documents to order.

        Returns:
            Documents sorted by progress (closest to done first).
        """
        # Incomplete docs sorted by progress (highest first)
        incomplete = [d for d in documents if not d.is_complete]
        complete = [d for d in documents if d.is_complete]

        incomplete.sort(key=lambda d: d.progress, reverse=True)

        return incomplete + complete

    @staticmethod
    def round_robin(
        documents: List[Document],
        chunks_per_turn: int = 1,
    ) -> Generator[Tuple[Document, int], None, None]:
        """
        Read from each document in turn (round-robin).

        Ensures progress on all documents rather than completing one
        at a time. Good for:
        - Getting overview of multiple documents quickly
        - Comparative analysis tasks
        - When all documents are equally important

        Args:
            documents: List of documents to read from.
            chunks_per_turn: Chunks to read from each doc per round.

        Yields:
            Tuples of (document, chunk_index) for reading order.
        """
        # Filter to incomplete documents
        active_docs = [d for d in documents if not d.is_complete]

        while active_docs:
            for doc in active_docs[:]:  # Copy list for safe iteration
                for _ in range(chunks_per_turn):
                    if doc.is_complete:
                        break

                    chunk_idx = doc.chunks_read
                    yield (doc, chunk_idx)
                    doc.mark_chunk_read()

                if doc.is_complete:
                    active_docs.remove(doc)

    @staticmethod
    def greedy_fit(
        documents: List[Document],
        available_tokens: int,
    ) -> List[Document]:
        """
        Select documents that can be completed within token budget.

        Greedy algorithm that maximizes completed documents. Good for:
        - Limited context remaining before handover
        - Maximizing throughput

        Args:
            documents: List of documents to select from.
            available_tokens: Token budget to fit within.

        Returns:
            Subset of documents that fit within budget, ordered by priority.
        """
        # Sort by efficiency: priority / tokens (get most value per token)
        candidates = [d for d in documents if not d.is_complete]
        candidates.sort(
            key=lambda d: PRIORITY_VALUES.get(d.priority, 50) / max(d.remaining_tokens, 1),
            reverse=True,
        )

        selected = []
        remaining_budget = available_tokens

        for doc in candidates:
            if doc.remaining_tokens <= remaining_budget:
                selected.append(doc)
                remaining_budget -= doc.remaining_tokens

        return selected

    @staticmethod
    def interleaved_priority(
        documents: List[Document],
        high_priority_ratio: float = 0.7,
    ) -> Generator[Tuple[Document, int], None, None]:
        """
        Interleave high and normal priority documents.

        Ensures important documents get most attention while still
        making progress on others. Good for:
        - Balanced reading with clear priorities
        - Long sessions with mixed document importance

        Args:
            documents: List of documents to read from.
            high_priority_ratio: Fraction of reads from high priority docs.

        Yields:
            Tuples of (document, chunk_index) for reading order.
        """
        high_priority = [
            d for d in documents
            if d.priority in (DocumentPriority.CRITICAL, DocumentPriority.HIGH)
            and not d.is_complete
        ]
        normal_priority = [
            d for d in documents
            if d.priority not in (DocumentPriority.CRITICAL, DocumentPriority.HIGH)
            and not d.is_complete
        ]

        high_idx = 0
        normal_idx = 0
        read_count = 0

        while high_priority or normal_priority:
            # Decide which queue to read from
            read_high = False
            if high_priority and normal_priority:
                # Use ratio to decide
                read_high = (read_count % 10) < (high_priority_ratio * 10)
            elif high_priority:
                read_high = True

            # Get next document
            if read_high and high_priority:
                doc = high_priority[high_idx % len(high_priority)]
                chunk_idx = doc.chunks_read
                yield (doc, chunk_idx)
                doc.mark_chunk_read()

                if doc.is_complete:
                    high_priority.remove(doc)
                else:
                    high_idx += 1
            elif normal_priority:
                doc = normal_priority[normal_idx % len(normal_priority)]
                chunk_idx = doc.chunks_read
                yield (doc, chunk_idx)
                doc.mark_chunk_read()

                if doc.is_complete:
                    normal_priority.remove(doc)
                else:
                    normal_idx += 1

            read_count += 1

    @classmethod
    def create_plan(
        cls,
        documents: List[Document],
        strategy: str = "by_priority",
        context_size: int = 100000,
        **kwargs,
    ) -> ReadingPlan:
        """
        Create a reading plan using the specified strategy.

        Args:
            documents: List of documents to plan.
            strategy: Strategy name ('sequential', 'by_priority', 'by_size', etc.).
            context_size: Available context window size.
            **kwargs: Additional arguments for the strategy.

        Returns:
            ReadingPlan with ordered documents and estimates.
        """
        # Apply strategy
        strategy_map = {
            "sequential": cls.sequential,
            "by_priority": cls.by_priority,
            "by_size": cls.by_size,
            "by_completion": cls.by_completion,
        }

        strategy_fn = strategy_map.get(strategy, cls.sequential)
        ordered_docs = strategy_fn(documents, **kwargs) if kwargs else strategy_fn(documents)

        # Calculate estimates
        total_tokens = sum(d.token_count for d in ordered_docs)
        estimated_turns = max(1, (total_tokens // context_size) + 1)

        return ReadingPlan(
            documents=ordered_docs,
            strategy_name=strategy,
            estimated_total_tokens=total_tokens,
            estimated_turns=estimated_turns,
        )


def simple_keyword_relevance(doc: Document, query: str) -> float:
    """
    Simple keyword-based relevance scoring.

    Counts query term occurrences in document metadata/filename.
    For better relevance, use embedding-based similarity.

    Args:
        doc: Document to score.
        query: Query string.

    Returns:
        Relevance score from 0.0 to 1.0.
    """
    query_terms = set(query.lower().split())

    # Check filename
    filename_lower = doc.filename.lower()
    filename_matches = sum(1 for term in query_terms if term in filename_lower)

    # Check metadata
    metadata_str = str(doc.metadata).lower()
    metadata_matches = sum(1 for term in query_terms if term in metadata_str)

    total_matches = filename_matches + metadata_matches
    max_possible = len(query_terms) * 2  # Could match in both places

    return min(1.0, total_matches / max_possible) if max_possible > 0 else 0.0


class AdaptiveReadingStrategy:
    """
    Adaptive strategy that adjusts based on context usage and progress.

    Monitors context consumption and automatically adjusts reading order
    to maximize value within remaining context budget.
    """

    def __init__(
        self,
        documents: List[Document],
        context_budget: int,
        target_completion: float = 0.8,  # Target 80% of documents complete
    ):
        """
        Initialize adaptive strategy.

        Args:
            documents: Documents to process.
            context_budget: Total token budget available.
            target_completion: Target fraction of documents to complete.
        """
        self.documents = documents.copy()
        self.context_budget = context_budget
        self.target_completion = target_completion
        self.tokens_used = 0

    def get_next_chunk(self) -> Optional[Tuple[Document, int]]:
        """
        Get the next chunk to read based on current state.

        Considers:
        - Remaining context budget
        - Document priorities
        - Completion progress

        Returns:
            Tuple of (document, chunk_index) or None if done.
        """
        remaining = self.context_budget - self.tokens_used

        # Get incomplete documents
        incomplete = [d for d in self.documents if not d.is_complete]

        if not incomplete:
            return None

        # If low on budget, prioritize completing started documents
        if remaining < self.context_budget * 0.2:
            # Find document closest to completion
            started = [d for d in incomplete if d.chunks_read > 0]
            if started:
                started.sort(key=lambda d: d.remaining_tokens)
                doc = started[0]
                if doc.remaining_tokens <= remaining:
                    return (doc, doc.chunks_read)

        # Otherwise, use priority + size balancing
        incomplete.sort(
            key=lambda d: (
                -PRIORITY_VALUES.get(d.priority, 50),
                -d.progress,  # Prefer more progress
                d.remaining_tokens,  # Prefer smaller remaining
            )
        )

        for doc in incomplete:
            avg_chunk_tokens = doc.token_count / doc.chunk_count if doc.chunk_count > 0 else 0
            if avg_chunk_tokens <= remaining:
                return (doc, doc.chunks_read)

        return None

    def record_chunk_read(self, doc: Document, tokens: int) -> None:
        """
        Record that a chunk was read.

        Args:
            doc: Document the chunk was from.
            tokens: Tokens consumed by the chunk.
        """
        doc.mark_chunk_read()
        self.tokens_used += tokens

    def get_status(self) -> Dict[str, Any]:
        """Get current reading status."""
        completed = sum(1 for d in self.documents if d.is_complete)
        total = len(self.documents)

        return {
            "documents_completed": completed,
            "documents_total": total,
            "completion_rate": completed / total if total > 0 else 1.0,
            "tokens_used": self.tokens_used,
            "tokens_remaining": self.context_budget - self.tokens_used,
            "budget_used_pct": (self.tokens_used / self.context_budget * 100) if self.context_budget > 0 else 100,
        }
