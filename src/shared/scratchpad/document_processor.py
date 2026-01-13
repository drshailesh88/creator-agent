"""Document chunking and processing for context-window-aware reading.

This module provides tools to split large documents into chunks that fit
within LLM context windows, enabling efficient processing of documents
that exceed single-turn capacity.
"""

import hashlib
import logging
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import the document processor skill
sys.path.insert(0, str(Path(__file__).parents[4] / "skills" / "document-processor"))
from processor import DocumentProcessor, ProcessedDocument as RawProcessedDocument

logger = logging.getLogger(__name__)


class ChunkingMethod(str, Enum):
    """Methods for splitting documents into chunks."""

    # Split by page boundaries (best for preserving document structure)
    BY_PAGE = "by_page"

    # Split by paragraph boundaries
    BY_PARAGRAPH = "by_paragraph"

    # Split by sentence boundaries (most granular)
    BY_SENTENCE = "by_sentence"

    # Split by fixed token count (precise but may break mid-content)
    BY_TOKENS = "by_tokens"

    # Smart splitting that respects semantic boundaries
    SEMANTIC = "semantic"


@dataclass
class DocumentChunk:
    """A chunk of a document that fits within a context window."""

    document_id: str
    chunk_index: int
    total_chunks: int
    content: str
    start_page: int
    end_page: int
    token_estimate: int

    # Optional metadata
    source_path: Optional[str] = None
    title: Optional[str] = None
    section_headers: List[str] = field(default_factory=list)

    @property
    def is_first(self) -> bool:
        """Check if this is the first chunk."""
        return self.chunk_index == 0

    @property
    def is_last(self) -> bool:
        """Check if this is the last chunk."""
        return self.chunk_index == self.total_chunks - 1

    @property
    def progress_fraction(self) -> float:
        """Get progress through document as fraction (0.0 to 1.0)."""
        if self.total_chunks == 0:
            return 1.0
        return (self.chunk_index + 1) / self.total_chunks

    def get_context_header(self) -> str:
        """Generate a header for context about this chunk's position."""
        parts = []

        if self.title:
            parts.append(f"Document: {self.title}")

        parts.append(f"Chunk {self.chunk_index + 1} of {self.total_chunks}")
        parts.append(f"Pages {self.start_page}-{self.end_page}")
        parts.append(f"~{self.token_estimate:,} tokens")

        if self.section_headers:
            parts.append(f"Sections: {', '.join(self.section_headers[-3:])}")

        return " | ".join(parts)


@dataclass
class ProcessedDocument:
    """A fully processed document ready for chunking."""

    document_id: str
    source_path: str
    content: str
    page_count: int
    word_count: int
    token_estimate: int
    document_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    page_boundaries: List[int] = field(default_factory=list)  # Character positions
    warnings: List[str] = field(default_factory=list)

    @property
    def title(self) -> str:
        """Get document title from metadata or filename."""
        return self.metadata.get("title") or Path(self.source_path).stem


class DocumentChunker:
    """
    Processes documents and splits them into context-window-sized chunks.

    Works with the document-processor skill to extract content from various
    formats, then intelligently splits the content into chunks that fit
    within LLM context windows while preserving semantic coherence.
    """

    # Default maximum tokens per chunk (leaves room for notes + response)
    DEFAULT_MAX_CHUNK_TOKENS = 50000

    # Overlap between chunks to maintain context continuity
    DEFAULT_OVERLAP_TOKENS = 500

    # Page separator used by document processor
    PAGE_SEPARATOR = "\n\n---\n\n"

    def __init__(
        self,
        max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
        overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
        chunking_method: ChunkingMethod = ChunkingMethod.BY_PAGE,
    ):
        """
        Initialize the document chunker.

        Args:
            max_chunk_tokens: Maximum tokens per chunk (default 50000).
                             This leaves room for system prompts, notes, and response.
            overlap_tokens: Number of tokens to overlap between chunks for
                           context continuity (default 500).
            chunking_method: Method to use for splitting documents.
        """
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens
        self.chunking_method = chunking_method
        self._processor = DocumentProcessor()

    async def process_document(self, file_path: str) -> ProcessedDocument:
        """
        Process a document and prepare it for chunking.

        Uses the document-processor skill to extract content from various
        formats (PDF, DOCX, etc.) and prepares metadata for chunking.

        Args:
            file_path: Path to the document file.

        Returns:
            ProcessedDocument ready for chunking.

        Raises:
            FileNotFoundError: If the document doesn't exist.
            ValueError: If the document can't be processed.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        # Process with the document-processor skill
        result = self._processor.process(str(path))

        if not result.success:
            raise ValueError(f"Failed to process document: {result.error}")

        # Generate a stable document ID
        doc_id = self._generate_document_id(file_path, result.content)

        # Find page boundaries in content
        page_boundaries = self._find_page_boundaries(result.content)

        # Estimate total tokens
        token_estimate = self.estimate_tokens(result.content)

        return ProcessedDocument(
            document_id=doc_id,
            source_path=str(path.absolute()),
            content=result.content,
            page_count=result.page_count or len(page_boundaries) + 1,
            word_count=result.word_count,
            token_estimate=token_estimate,
            document_type=result.document_type.value,
            metadata=result.metadata or {},
            page_boundaries=page_boundaries,
            warnings=result.warnings or [],
        )

    async def get_chunks(
        self,
        document: ProcessedDocument,
        method: Optional[ChunkingMethod] = None,
    ) -> List[DocumentChunk]:
        """
        Split a processed document into context-window-sized chunks.

        Args:
            document: A ProcessedDocument from process_document().
            method: Override the default chunking method.

        Returns:
            List of DocumentChunks that together comprise the full document.
        """
        chunking_method = method or self.chunking_method

        # If document fits in a single chunk, return as-is
        if document.token_estimate <= self.max_chunk_tokens:
            return [DocumentChunk(
                document_id=document.document_id,
                chunk_index=0,
                total_chunks=1,
                content=document.content,
                start_page=1,
                end_page=document.page_count,
                token_estimate=document.token_estimate,
                source_path=document.source_path,
                title=document.title,
            )]

        # Choose chunking strategy
        if chunking_method == ChunkingMethod.BY_PAGE:
            return self._chunk_by_pages(document)
        elif chunking_method == ChunkingMethod.BY_PARAGRAPH:
            return self._chunk_by_paragraphs(document)
        elif chunking_method == ChunkingMethod.BY_SENTENCE:
            return self._chunk_by_sentences(document)
        elif chunking_method == ChunkingMethod.BY_TOKENS:
            return self._chunk_by_tokens(document)
        elif chunking_method == ChunkingMethod.SEMANTIC:
            return self._chunk_semantic(document)
        else:
            # Default to page-based chunking
            return self._chunk_by_pages(document)

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text.

        Uses a rough heuristic: tokens ~ words * 1.3
        This accounts for subword tokenization in most LLM tokenizers.

        Args:
            text: The text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        if not text:
            return 0

        # Count words (split on whitespace)
        word_count = len(text.split())

        # Apply multiplier for tokenization overhead
        # Most tokenizers produce ~1.3 tokens per word on average
        token_estimate = int(word_count * 1.3)

        return token_estimate

    def _generate_document_id(self, file_path: str, content: str) -> str:
        """Generate a stable document ID based on path and content hash."""
        path_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{path_hash}_{content_hash}"

    def _find_page_boundaries(self, content: str) -> List[int]:
        """Find character positions of page boundaries in content."""
        boundaries = []
        pos = 0

        while True:
            pos = content.find(self.PAGE_SEPARATOR, pos)
            if pos == -1:
                break
            boundaries.append(pos)
            pos += len(self.PAGE_SEPARATOR)

        return boundaries

    def _get_page_number(
        self,
        char_position: int,
        page_boundaries: List[int],
    ) -> int:
        """Get the page number for a character position."""
        page = 1
        for boundary in page_boundaries:
            if char_position > boundary:
                page += 1
            else:
                break
        return page

    def _extract_section_headers(self, text: str) -> List[str]:
        """Extract markdown-style section headers from text."""
        headers = []
        # Match lines starting with # (markdown headers)
        for match in re.finditer(r'^#{1,6}\s+(.+)$', text, re.MULTILINE):
            headers.append(match.group(1).strip())
        return headers

    def _chunk_by_pages(self, document: ProcessedDocument) -> List[DocumentChunk]:
        """Split document by page boundaries, grouping pages to fit token limit."""
        chunks = []

        # Split content into pages
        pages = document.content.split(self.PAGE_SEPARATOR)

        current_chunk_content = []
        current_chunk_start_page = 1
        current_tokens = 0

        for page_num, page_content in enumerate(pages, start=1):
            page_tokens = self.estimate_tokens(page_content)

            # Check if adding this page would exceed limit
            if current_tokens + page_tokens > self.max_chunk_tokens and current_chunk_content:
                # Save current chunk
                chunk_content = self.PAGE_SEPARATOR.join(current_chunk_content)
                chunks.append(self._create_chunk(
                    document=document,
                    content=chunk_content,
                    chunk_index=len(chunks),
                    start_page=current_chunk_start_page,
                    end_page=page_num - 1,
                ))

                # Start new chunk (with overlap if configured)
                if self.overlap_tokens > 0 and current_chunk_content:
                    # Include last portion of previous chunk for context
                    overlap_content = self._get_overlap_content(
                        current_chunk_content[-1],
                        self.overlap_tokens,
                    )
                    current_chunk_content = [overlap_content, page_content]
                    current_tokens = self.estimate_tokens(overlap_content) + page_tokens
                else:
                    current_chunk_content = [page_content]
                    current_tokens = page_tokens
                current_chunk_start_page = page_num
            else:
                current_chunk_content.append(page_content)
                current_tokens += page_tokens

        # Add final chunk
        if current_chunk_content:
            chunk_content = self.PAGE_SEPARATOR.join(current_chunk_content)
            chunks.append(self._create_chunk(
                document=document,
                content=chunk_content,
                chunk_index=len(chunks),
                start_page=current_chunk_start_page,
                end_page=len(pages),
            ))

        # Update total_chunks in all chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks

    def _chunk_by_paragraphs(self, document: ProcessedDocument) -> List[DocumentChunk]:
        """Split document by paragraph boundaries."""
        chunks = []

        # Split into paragraphs (double newline)
        paragraphs = re.split(r'\n\s*\n', document.content)

        current_chunk_content = []
        current_tokens = 0
        current_start_pos = 0
        chunk_start_pos = 0

        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)

            if current_tokens + para_tokens > self.max_chunk_tokens and current_chunk_content:
                # Save current chunk
                chunk_content = "\n\n".join(current_chunk_content)
                start_page = self._get_page_number(chunk_start_pos, document.page_boundaries)
                end_page = self._get_page_number(current_start_pos, document.page_boundaries)

                chunks.append(self._create_chunk(
                    document=document,
                    content=chunk_content,
                    chunk_index=len(chunks),
                    start_page=start_page,
                    end_page=end_page,
                ))

                # Start new chunk
                current_chunk_content = [para]
                current_tokens = para_tokens
                chunk_start_pos = current_start_pos
            else:
                current_chunk_content.append(para)
                current_tokens += para_tokens

            current_start_pos += len(para) + 2  # +2 for \n\n

        # Add final chunk
        if current_chunk_content:
            chunk_content = "\n\n".join(current_chunk_content)
            start_page = self._get_page_number(chunk_start_pos, document.page_boundaries)
            end_page = document.page_count

            chunks.append(self._create_chunk(
                document=document,
                content=chunk_content,
                chunk_index=len(chunks),
                start_page=start_page,
                end_page=end_page,
            ))

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks

    def _chunk_by_sentences(self, document: ProcessedDocument) -> List[DocumentChunk]:
        """Split document by sentence boundaries."""
        chunks = []

        # Simple sentence splitting (handles common cases)
        sentences = re.split(r'(?<=[.!?])\s+', document.content)

        current_chunk_content = []
        current_tokens = 0
        current_start_pos = 0
        chunk_start_pos = 0

        for sentence in sentences:
            sentence_tokens = self.estimate_tokens(sentence)

            if current_tokens + sentence_tokens > self.max_chunk_tokens and current_chunk_content:
                chunk_content = " ".join(current_chunk_content)
                start_page = self._get_page_number(chunk_start_pos, document.page_boundaries)
                end_page = self._get_page_number(current_start_pos, document.page_boundaries)

                chunks.append(self._create_chunk(
                    document=document,
                    content=chunk_content,
                    chunk_index=len(chunks),
                    start_page=start_page,
                    end_page=end_page,
                ))

                current_chunk_content = [sentence]
                current_tokens = sentence_tokens
                chunk_start_pos = current_start_pos
            else:
                current_chunk_content.append(sentence)
                current_tokens += sentence_tokens

            current_start_pos += len(sentence) + 1

        # Add final chunk
        if current_chunk_content:
            chunk_content = " ".join(current_chunk_content)
            start_page = self._get_page_number(chunk_start_pos, document.page_boundaries)

            chunks.append(self._create_chunk(
                document=document,
                content=chunk_content,
                chunk_index=len(chunks),
                start_page=start_page,
                end_page=document.page_count,
            ))

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks

    def _chunk_by_tokens(self, document: ProcessedDocument) -> List[DocumentChunk]:
        """Split document by fixed token count (may break mid-content)."""
        chunks = []

        words = document.content.split()
        # Approximate words per chunk (tokens / 1.3)
        words_per_chunk = int(self.max_chunk_tokens / 1.3)

        for i in range(0, len(words), words_per_chunk):
            chunk_words = words[i:i + words_per_chunk]
            chunk_content = " ".join(chunk_words)

            # Calculate approximate position for page numbers
            char_pos = len(" ".join(words[:i]))
            start_page = self._get_page_number(char_pos, document.page_boundaries)
            end_char_pos = len(" ".join(words[:i + len(chunk_words)]))
            end_page = self._get_page_number(end_char_pos, document.page_boundaries)

            chunks.append(self._create_chunk(
                document=document,
                content=chunk_content,
                chunk_index=len(chunks),
                start_page=start_page,
                end_page=end_page,
            ))

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks

    def _chunk_semantic(self, document: ProcessedDocument) -> List[DocumentChunk]:
        """
        Smart semantic chunking that respects document structure.

        Prioritizes splitting at:
        1. Page boundaries
        2. Section headers
        3. Paragraph breaks
        4. Sentence endings
        """
        chunks = []

        # Find all potential split points
        split_points = []

        # Page boundaries (highest priority)
        for boundary in document.page_boundaries:
            split_points.append((boundary, 'page', 4))

        # Section headers
        for match in re.finditer(r'^#{1,6}\s+.+$', document.content, re.MULTILINE):
            split_points.append((match.start(), 'header', 3))

        # Paragraph breaks
        for match in re.finditer(r'\n\s*\n', document.content):
            split_points.append((match.start(), 'paragraph', 2))

        # Sort by position
        split_points.sort(key=lambda x: x[0])

        # Build chunks respecting split points
        current_start = 0
        current_content = ""

        for pos, split_type, priority in split_points:
            segment = document.content[current_start:pos]
            test_content = current_content + segment

            if self.estimate_tokens(test_content) > self.max_chunk_tokens:
                # Need to split here
                if current_content:
                    start_page = self._get_page_number(
                        current_start - len(current_content),
                        document.page_boundaries,
                    )
                    end_page = self._get_page_number(current_start, document.page_boundaries)

                    chunks.append(self._create_chunk(
                        document=document,
                        content=current_content.strip(),
                        chunk_index=len(chunks),
                        start_page=start_page,
                        end_page=end_page,
                    ))

                current_content = segment
                current_start = pos
            else:
                current_content = test_content

        # Add remaining content
        remaining = document.content[current_start:]
        final_content = current_content + remaining

        if final_content.strip():
            start_page = self._get_page_number(
                len(document.content) - len(final_content),
                document.page_boundaries,
            )

            chunks.append(self._create_chunk(
                document=document,
                content=final_content.strip(),
                chunk_index=len(chunks),
                start_page=start_page,
                end_page=document.page_count,
            ))

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks

    def _create_chunk(
        self,
        document: ProcessedDocument,
        content: str,
        chunk_index: int,
        start_page: int,
        end_page: int,
    ) -> DocumentChunk:
        """Create a DocumentChunk with computed metadata."""
        return DocumentChunk(
            document_id=document.document_id,
            chunk_index=chunk_index,
            total_chunks=0,  # Will be set later
            content=content,
            start_page=start_page,
            end_page=end_page,
            token_estimate=self.estimate_tokens(content),
            source_path=document.source_path,
            title=document.title,
            section_headers=self._extract_section_headers(content),
        )

    def _get_overlap_content(self, text: str, target_tokens: int) -> str:
        """Get the last portion of text up to target_tokens."""
        words = text.split()
        target_words = int(target_tokens / 1.3)

        if len(words) <= target_words:
            return text

        return " ".join(words[-target_words:])

    async def chunk_multiple(
        self,
        file_paths: List[str],
    ) -> Dict[str, List[DocumentChunk]]:
        """
        Process and chunk multiple documents.

        Args:
            file_paths: List of paths to documents.

        Returns:
            Dictionary mapping document IDs to their chunks.
        """
        results = {}

        for path in file_paths:
            try:
                doc = await self.process_document(path)
                chunks = await self.get_chunks(doc)
                results[doc.document_id] = chunks
                logger.info(
                    f"Processed {path}: {doc.token_estimate} tokens, "
                    f"{len(chunks)} chunks"
                )
            except Exception as e:
                logger.error(f"Failed to process {path}: {e}")

        return results
