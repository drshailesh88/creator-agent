---
name: document-processor
description: Process PDFs, Word docs, and other documents for Clawdbot
version: 1.0.0
author: Life OS
---

# Document Processor Skill

Converts PDFs, Word documents, and other files into clean text/markdown that Clawdbot can understand and process.

## Overview

When you share a PDF or document with Clawdbot, this skill automatically:
1. Extracts text content
2. Preserves structure (headings, lists, tables)
3. Converts to clean markdown
4. Makes it available for research/content creation

## Supported Formats

| Format | Extension | Support Level |
|--------|-----------|---------------|
| PDF | .pdf | ✅ Full (text + scanned) |
| Word | .docx | ✅ Full |
| Word (old) | .doc | ⚠️ Basic |
| PowerPoint | .pptx | ✅ Full |
| Text | .txt, .md | ✅ Full |
| HTML | .html | ✅ Full |
| Rich Text | .rtf | ⚠️ Basic |

## Commands

### Process a document
```
"Process this PDF for me" + [attach file]
"Extract text from this document"
"Read this PDF and summarize it"
```

### Batch processing
```
"Process all PDFs in my research folder"
```

## Personality Guidelines

This skill maintains Clawdbot's warmth:
- Acknowledge receipt of document warmly
- Explain what's being extracted
- Alert user to any issues (scanned text, corrupted files) gently
- Offer to summarize or highlight key points

## Technical Details

Uses multiple extraction backends:
1. **PyMuPDF** - Fast text extraction (primary)
2. **pdfplumber** - Better table extraction (fallback)
3. **python-docx** - Word documents
4. **Tesseract OCR** - Scanned PDFs (if installed)

## Configuration

```yaml
# In mcporter.json
max_file_size_mb: 50
extract_images: false
ocr_enabled: true
preserve_formatting: true
```
