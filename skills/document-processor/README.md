# Document Processor Skill

Process PDFs, Word documents, and other files so Clawdbot can read and work with them.

## Why You Need This

LLMs can't read raw PDF/binary files directly. This skill converts documents to text/markdown that Clawdbot can understand.

## Installation

### 1. Install dependencies

```bash
# Core dependencies (handles most documents)
pip install pymupdf python-docx python-pptx html2text

# Full installation (all formats)
pip install pymupdf pdfplumber python-docx python-pptx html2text striprtf
```

### 2. Optional: OCR for scanned PDFs

```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr
pip install pytesseract Pillow

# macOS
brew install tesseract
pip install pytesseract Pillow
```

### 3. Install the skill

```bash
cp -r skills/document-processor ~/.clawdbot/skills/
clawd reload
```

## Usage

### Basic usage
```
You: [attach a PDF] "Read this research paper"
Clawdbot: "I've processed your PDF! It's a 15-page document about...
         Here's a summary of the key points..."
```

### Research workflow
```
You: "Process this PDF and use it for my blog post about AI"
Clawdbot:
1. Extracts text from PDF
2. Identifies key points
3. Uses content for your blog post
```

### Batch processing
```
You: "Process all the PDFs in /path/to/research/"
```

## Supported Formats

| Format | Extension | Quality |
|--------|-----------|---------|
| PDF | .pdf | ⭐⭐⭐⭐⭐ |
| Word | .docx | ⭐⭐⭐⭐⭐ |
| Word (old) | .doc | ⭐⭐⭐ |
| PowerPoint | .pptx | ⭐⭐⭐⭐⭐ |
| Plain Text | .txt | ⭐⭐⭐⭐⭐ |
| Markdown | .md | ⭐⭐⭐⭐⭐ |
| HTML | .html | ⭐⭐⭐⭐ |
| Rich Text | .rtf | ⭐⭐⭐ |

## How It Works

```
Your PDF
    │
    ▼
┌─────────────────────────────────────┐
│       Document Processor            │
│                                     │
│  1. Detect format                   │
│  2. Extract text                    │
│  3. Preserve structure              │
│  4. Convert to markdown             │
└─────────────────────────────────────┘
    │
    ▼
Clean text/markdown
    │
    ▼
Clawdbot can now read it!
```

## Configuration

Edit `mcporter.json` to customize:

```json
{
  "config": {
    "max_file_size_mb": 50,    // Max file size to process
    "ocr_enabled": true,       // OCR for scanned PDFs
    "preserve_formatting": true // Keep headings, lists, etc.
  }
}
```

## Troubleshooting

### "PDF has very little text"
- The PDF might be scanned images
- Install Tesseract OCR (see above)
- Or use a different PDF that has actual text

### "File too large"
- Default limit is 50MB
- Increase `max_file_size_mb` in config
- Or split large documents

### "Unsupported format"
- Check the supported formats table above
- Convert to a supported format first

## API Reference

### process_document(file_path)
Extract text from a document.

**Returns:**
```python
{
    "success": True,
    "content": "Full extracted text...",
    "type": "pdf",
    "page_count": 15,
    "word_count": 5420,
    "metadata": {"title": "...", "author": "..."},
    "warnings": [],
    "error": None
}
```

### summarize_document(file_path, max_length=500)
Extract and preview a document.

### get_supported_formats()
List all supported formats and their status.
