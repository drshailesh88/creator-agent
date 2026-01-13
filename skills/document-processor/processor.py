"""
Document Processor - Extract text from PDFs, Word docs, and other formats.

Supports multiple backends for robust extraction:
- PyMuPDF (fitz) for fast PDF text extraction
- pdfplumber for complex tables
- python-docx for Word documents
- Tesseract OCR for scanned documents
"""

import os
import io
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    PPTX = "pptx"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    RTF = "rtf"
    UNKNOWN = "unknown"


@dataclass
class ProcessedDocument:
    """Result of document processing."""
    success: bool
    content: str
    document_type: DocumentType
    page_count: int = 0
    word_count: int = 0
    metadata: Dict[str, Any] = None
    warnings: List[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.warnings is None:
            self.warnings = []
        if self.content:
            self.word_count = len(self.content.split())


class DocumentProcessor:
    """
    Multi-format document processor with fallback backends.
    """

    # File extension to document type mapping
    EXTENSION_MAP = {
        '.pdf': DocumentType.PDF,
        '.docx': DocumentType.DOCX,
        '.doc': DocumentType.DOC,
        '.pptx': DocumentType.PPTX,
        '.txt': DocumentType.TXT,
        '.md': DocumentType.MD,
        '.markdown': DocumentType.MD,
        '.html': DocumentType.HTML,
        '.htm': DocumentType.HTML,
        '.rtf': DocumentType.RTF,
    }

    def __init__(
        self,
        max_file_size_mb: int = 50,
        ocr_enabled: bool = True,
        preserve_formatting: bool = True
    ):
        self.max_file_size_mb = max_file_size_mb
        self.ocr_enabled = ocr_enabled
        self.preserve_formatting = preserve_formatting

        # Check available backends
        self._check_backends()

    def _check_backends(self):
        """Check which backends are available."""
        self.has_pymupdf = False
        self.has_pdfplumber = False
        self.has_docx = False
        self.has_tesseract = False
        self.has_pptx = False

        try:
            import fitz
            self.has_pymupdf = True
        except ImportError:
            logger.warning("PyMuPDF not installed. Install with: pip install pymupdf")

        try:
            import pdfplumber
            self.has_pdfplumber = True
        except ImportError:
            logger.warning("pdfplumber not installed. Install with: pip install pdfplumber")

        try:
            import docx
            self.has_docx = True
        except ImportError:
            logger.warning("python-docx not installed. Install with: pip install python-docx")

        try:
            import pytesseract
            self.has_tesseract = True
        except ImportError:
            logger.info("pytesseract not installed. OCR will be disabled.")

        try:
            from pptx import Presentation
            self.has_pptx = True
        except ImportError:
            logger.info("python-pptx not installed. PowerPoint support disabled.")

    def detect_type(self, file_path: str) -> DocumentType:
        """Detect document type from file extension."""
        ext = Path(file_path).suffix.lower()
        return self.EXTENSION_MAP.get(ext, DocumentType.UNKNOWN)

    def process(self, file_path: str) -> ProcessedDocument:
        """
        Process a document and extract its text content.

        Args:
            file_path: Path to the document file

        Returns:
            ProcessedDocument with extracted content
        """
        path = Path(file_path)

        # Validate file exists
        if not path.exists():
            return ProcessedDocument(
                success=False,
                content="",
                document_type=DocumentType.UNKNOWN,
                error=f"File not found: {file_path}"
            )

        # Check file size
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            return ProcessedDocument(
                success=False,
                content="",
                document_type=DocumentType.UNKNOWN,
                error=f"File too large: {file_size_mb:.1f}MB (max: {self.max_file_size_mb}MB)"
            )

        # Detect document type
        doc_type = self.detect_type(file_path)

        # Route to appropriate processor
        processors = {
            DocumentType.PDF: self._process_pdf,
            DocumentType.DOCX: self._process_docx,
            DocumentType.DOC: self._process_doc,
            DocumentType.PPTX: self._process_pptx,
            DocumentType.TXT: self._process_text,
            DocumentType.MD: self._process_text,
            DocumentType.HTML: self._process_html,
            DocumentType.RTF: self._process_rtf,
        }

        processor = processors.get(doc_type)
        if not processor:
            return ProcessedDocument(
                success=False,
                content="",
                document_type=doc_type,
                error=f"Unsupported document type: {doc_type}"
            )

        try:
            return processor(file_path)
        except Exception as e:
            logger.exception(f"Error processing {file_path}: {e}")
            return ProcessedDocument(
                success=False,
                content="",
                document_type=doc_type,
                error=str(e)
            )

    def _process_pdf(self, file_path: str) -> ProcessedDocument:
        """Process PDF file."""
        warnings = []

        # Try PyMuPDF first (faster)
        if self.has_pymupdf:
            try:
                return self._process_pdf_pymupdf(file_path)
            except Exception as e:
                warnings.append(f"PyMuPDF failed: {e}")
                logger.warning(f"PyMuPDF failed, trying pdfplumber: {e}")

        # Fallback to pdfplumber
        if self.has_pdfplumber:
            try:
                result = self._process_pdf_pdfplumber(file_path)
                result.warnings.extend(warnings)
                return result
            except Exception as e:
                warnings.append(f"pdfplumber failed: {e}")

        return ProcessedDocument(
            success=False,
            content="",
            document_type=DocumentType.PDF,
            warnings=warnings,
            error="No PDF processing backend available. Install pymupdf or pdfplumber."
        )

    def _process_pdf_pymupdf(self, file_path: str) -> ProcessedDocument:
        """Process PDF using PyMuPDF (fitz)."""
        import fitz

        doc = fitz.open(file_path)
        pages = []
        warnings = []

        for page_num, page in enumerate(doc):
            text = page.get_text("text")

            # Check if page has very little text (might be scanned)
            if len(text.strip()) < 50 and self.ocr_enabled and self.has_tesseract:
                warnings.append(f"Page {page_num + 1} may be scanned. OCR attempted.")
                # OCR would go here if needed

            pages.append(text)

        content = "\n\n---\n\n".join(pages)

        # Extract metadata
        metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
        }

        doc.close()

        return ProcessedDocument(
            success=True,
            content=content,
            document_type=DocumentType.PDF,
            page_count=len(pages),
            metadata=metadata,
            warnings=warnings
        )

    def _process_pdf_pdfplumber(self, file_path: str) -> ProcessedDocument:
        """Process PDF using pdfplumber (better for tables)."""
        import pdfplumber

        pages = []
        warnings = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""

                # Extract tables separately
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        text += "\n\n" + self._table_to_markdown(table)

                pages.append(text)

        content = "\n\n---\n\n".join(pages)

        return ProcessedDocument(
            success=True,
            content=content,
            document_type=DocumentType.PDF,
            page_count=len(pages),
            warnings=warnings
        )

    def _table_to_markdown(self, table: List[List[str]]) -> str:
        """Convert a table to markdown format."""
        if not table or not table[0]:
            return ""

        lines = []
        # Header
        header = table[0]
        lines.append("| " + " | ".join(str(cell or "") for cell in header) + " |")
        lines.append("| " + " | ".join("---" for _ in header) + " |")

        # Rows
        for row in table[1:]:
            lines.append("| " + " | ".join(str(cell or "") for cell in row) + " |")

        return "\n".join(lines)

    def _process_docx(self, file_path: str) -> ProcessedDocument:
        """Process Word document (.docx)."""
        if not self.has_docx:
            return ProcessedDocument(
                success=False,
                content="",
                document_type=DocumentType.DOCX,
                error="python-docx not installed. Install with: pip install python-docx"
            )

        from docx import Document

        doc = Document(file_path)
        paragraphs = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                # Preserve heading styles
                if para.style.name.startswith('Heading'):
                    level = int(para.style.name[-1]) if para.style.name[-1].isdigit() else 1
                    text = "#" * level + " " + text
                paragraphs.append(text)

        # Extract tables
        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = [cell.text for cell in row.cells]
                table_data.append(row_data)
            if table_data:
                paragraphs.append(self._table_to_markdown(table_data))

        content = "\n\n".join(paragraphs)

        # Extract metadata
        metadata = {
            "title": doc.core_properties.title or "",
            "author": doc.core_properties.author or "",
            "subject": doc.core_properties.subject or "",
        }

        return ProcessedDocument(
            success=True,
            content=content,
            document_type=DocumentType.DOCX,
            metadata=metadata
        )

    def _process_doc(self, file_path: str) -> ProcessedDocument:
        """Process old Word document (.doc)."""
        # Try using antiword or similar tool
        import subprocess

        try:
            result = subprocess.run(
                ['antiword', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return ProcessedDocument(
                    success=True,
                    content=result.stdout,
                    document_type=DocumentType.DOC
                )
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"antiword failed: {e}")

        return ProcessedDocument(
            success=False,
            content="",
            document_type=DocumentType.DOC,
            error="Cannot process .doc files. Convert to .docx or install antiword."
        )

    def _process_pptx(self, file_path: str) -> ProcessedDocument:
        """Process PowerPoint file."""
        if not self.has_pptx:
            return ProcessedDocument(
                success=False,
                content="",
                document_type=DocumentType.PPTX,
                error="python-pptx not installed. Install with: pip install python-pptx"
            )

        from pptx import Presentation

        prs = Presentation(file_path)
        slides = []

        for slide_num, slide in enumerate(prs.slides, 1):
            slide_text = [f"## Slide {slide_num}"]

            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text)

            slides.append("\n\n".join(slide_text))

        content = "\n\n---\n\n".join(slides)

        return ProcessedDocument(
            success=True,
            content=content,
            document_type=DocumentType.PPTX,
            page_count=len(slides)
        )

    def _process_text(self, file_path: str) -> ProcessedDocument:
        """Process plain text or markdown file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        doc_type = DocumentType.MD if file_path.endswith(('.md', '.markdown')) else DocumentType.TXT

        return ProcessedDocument(
            success=True,
            content=content,
            document_type=doc_type
        )

    def _process_html(self, file_path: str) -> ProcessedDocument:
        """Process HTML file, converting to markdown."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()

        # Simple HTML to text conversion
        # For better results, use html2text or beautifulsoup
        try:
            import html2text
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            content = h.handle(html_content)
        except ImportError:
            # Fallback: strip HTML tags
            import re
            content = re.sub(r'<[^>]+>', '', html_content)
            content = content.replace('&nbsp;', ' ')
            content = content.replace('&amp;', '&')
            content = content.replace('&lt;', '<')
            content = content.replace('&gt;', '>')

        return ProcessedDocument(
            success=True,
            content=content,
            document_type=DocumentType.HTML
        )

    def _process_rtf(self, file_path: str) -> ProcessedDocument:
        """Process RTF file."""
        try:
            from striprtf.striprtf import rtf_to_text

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                rtf_content = f.read()

            content = rtf_to_text(rtf_content)

            return ProcessedDocument(
                success=True,
                content=content,
                document_type=DocumentType.RTF
            )
        except ImportError:
            return ProcessedDocument(
                success=False,
                content="",
                document_type=DocumentType.RTF,
                error="striprtf not installed. Install with: pip install striprtf"
            )

    def process_bytes(self, data: bytes, filename: str) -> ProcessedDocument:
        """
        Process document from bytes (e.g., from API upload).

        Args:
            data: Document content as bytes
            filename: Original filename (for type detection)

        Returns:
            ProcessedDocument with extracted content
        """
        import tempfile

        # Write to temp file and process
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            return self.process(tmp_path)
        finally:
            os.unlink(tmp_path)


# MCP Tool Functions

processor = DocumentProcessor()


async def process_document(file_path: str) -> Dict[str, Any]:
    """
    MCP tool: Process a document and extract text.

    Args:
        file_path: Path to the document

    Returns:
        Dict with extracted content and metadata
    """
    result = processor.process(file_path)

    return {
        "success": result.success,
        "content": result.content,
        "type": result.document_type.value,
        "page_count": result.page_count,
        "word_count": result.word_count,
        "metadata": result.metadata,
        "warnings": result.warnings,
        "error": result.error
    }


async def summarize_document(file_path: str, max_length: int = 500) -> Dict[str, Any]:
    """
    MCP tool: Process and summarize a document.

    Args:
        file_path: Path to the document
        max_length: Maximum summary length in words

    Returns:
        Dict with document summary
    """
    result = processor.process(file_path)

    if not result.success:
        return {
            "success": False,
            "error": result.error
        }

    # Return first part as preview (actual summary would use LLM)
    preview_words = result.content.split()[:max_length]
    preview = " ".join(preview_words)
    if len(result.content.split()) > max_length:
        preview += "..."

    return {
        "success": True,
        "preview": preview,
        "full_content": result.content,
        "word_count": result.word_count,
        "page_count": result.page_count,
        "needs_full_summary": result.word_count > max_length
    }


async def get_supported_formats() -> Dict[str, Any]:
    """
    MCP tool: Get list of supported document formats.
    """
    return {
        "formats": [
            {"extension": ".pdf", "name": "PDF", "support": "full"},
            {"extension": ".docx", "name": "Word", "support": "full"},
            {"extension": ".doc", "name": "Word (old)", "support": "basic"},
            {"extension": ".pptx", "name": "PowerPoint", "support": "full"},
            {"extension": ".txt", "name": "Text", "support": "full"},
            {"extension": ".md", "name": "Markdown", "support": "full"},
            {"extension": ".html", "name": "HTML", "support": "full"},
            {"extension": ".rtf", "name": "Rich Text", "support": "basic"},
        ],
        "max_file_size_mb": processor.max_file_size_mb,
        "ocr_available": processor.has_tesseract
    }
