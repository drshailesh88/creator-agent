# Scratchpad API Reference

Complete reference for the Scratchpad MCP tools and Python API.

## Overview

The Scratchpad provides two interfaces:
1. **MCP Tools** - For use by Claude and other AI agents
2. **Python API** - For direct integration in skills and scripts

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NOTION_API_KEY` | Yes | Notion integration token |
| `SCRATCHPAD_SESSIONS_DB` | Yes | Research Sessions database ID |
| `SCRATCHPAD_DOCUMENTS_DB` | Yes | Documents database ID |
| `SCRATCHPAD_NOTES_DB` | Yes | Research Notes database ID |
| `SCRATCHPAD_MAX_CONTEXT_PERCENT` | No | Handover threshold (default: 75) |

## MCP Tools

### scratchpad.start_session

Create a new research session.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "task": {
      "type": "string",
      "description": "Description of the research task"
    },
    "session_id": {
      "type": "string",
      "description": "Optional custom session ID (auto-generated if not provided)"
    },
    "documents": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "path": {"type": "string"},
          "type": {"type": "string", "enum": ["pdf", "docx", "txt", "url"]}
        }
      },
      "description": "List of documents to process"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Tags for categorizing this session"
    }
  },
  "required": ["task"]
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "statin-research-2024-01-15-abc123",
  "page_id": "notion-page-id",
  "page_url": "https://notion.so/...",
  "documents_queued": 10,
  "message": "Research session started"
}
```

**Example:**
```
Use tool: scratchpad.start_session
Arguments: {
  "task": "Research adverse effects of statin medications",
  "documents": [
    {"name": "Smith_2023.pdf", "path": "/docs/Smith_2023.pdf", "type": "pdf"},
    {"name": "Jones_2022.pdf", "path": "/docs/Jones_2022.pdf", "type": "pdf"}
  ],
  "tags": ["medical", "statins", "side-effects"]
}
```

---

### scratchpad.save_note

Save a research note to the current session.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Session to save note to"
    },
    "content": {
      "type": "string",
      "description": "The note content"
    },
    "document_id": {
      "type": "string",
      "description": "Source document (Notion page ID or name)"
    },
    "type": {
      "type": "string",
      "enum": ["finding", "quote", "summary", "question", "contradiction", "methodology", "statistic", "definition", "reference"],
      "description": "Type of note"
    },
    "importance": {
      "type": "string",
      "enum": ["critical", "high", "medium", "low"],
      "description": "Importance level"
    },
    "quote": {
      "type": "string",
      "description": "Direct quote from source"
    },
    "page_section": {
      "type": "string",
      "description": "Location in source (e.g., 'p. 15' or 'Methods section')"
    },
    "citation": {
      "type": "string",
      "description": "Formatted citation"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Tags for this note"
    }
  },
  "required": ["session_id", "content"]
}
```

**Response:**
```json
{
  "success": true,
  "note_id": "notion-note-page-id",
  "session_id": "statin-research-2024-01-15-abc123",
  "notes_count": 15,
  "message": "Note saved"
}
```

**Example:**
```
Use tool: scratchpad.save_note
Arguments: {
  "session_id": "statin-research-2024-01-15-abc123",
  "content": "Muscle pain reported in 15% of patients during long-term follow-up",
  "document_id": "Smith_2023.pdf",
  "type": "statistic",
  "importance": "high",
  "quote": "Our analysis revealed that 15.3% of patients reported myalgia symptoms",
  "page_section": "Results, p. 8",
  "citation": "Smith et al., 2023",
  "tags": ["muscle-effects", "myalgia", "prevalence"]
}
```

---

### scratchpad.get_session

Retrieve session state and summary.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Session ID to retrieve"
    },
    "include_notes": {
      "type": "boolean",
      "default": false,
      "description": "Include all notes in response"
    },
    "include_documents": {
      "type": "boolean",
      "default": true,
      "description": "Include document list and status"
    }
  },
  "required": ["session_id"]
}
```

**Response:**
```json
{
  "success": true,
  "session": {
    "id": "statin-research-2024-01-15-abc123",
    "task": "Research adverse effects of statin medications",
    "status": "active",
    "progress": {
      "documents_processed": 4,
      "total_documents": 10,
      "percent": 40
    },
    "notes_count": 23,
    "handover_count": 1,
    "context_used": 65,
    "created": "2024-01-15T10:30:00Z",
    "updated": "2024-01-15T11:45:00Z"
  },
  "documents": [
    {"name": "Smith_2023.pdf", "status": "complete", "notes": 6},
    {"name": "Jones_2022.pdf", "status": "complete", "notes": 5},
    {"name": "Chen_2021.pdf", "status": "complete", "notes": 7},
    {"name": "Garcia_2020.pdf", "status": "complete", "notes": 5},
    {"name": "Williams_2019.pdf", "status": "pending", "notes": 0}
  ]
}
```

---

### scratchpad.get_notes

Retrieve notes from a session with optional filtering.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Session to retrieve notes from"
    },
    "document_id": {
      "type": "string",
      "description": "Filter to specific document"
    },
    "type": {
      "type": "string",
      "description": "Filter by note type"
    },
    "importance": {
      "type": "string",
      "description": "Filter by importance level"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Filter by tags (any match)"
    },
    "limit": {
      "type": "integer",
      "default": 100,
      "description": "Maximum notes to return"
    }
  },
  "required": ["session_id"]
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "statin-research-2024-01-15-abc123",
  "count": 23,
  "notes": [
    {
      "id": "note-page-id-1",
      "content": "Muscle pain reported in 15% of patients",
      "type": "statistic",
      "importance": "high",
      "document": "Smith_2023.pdf",
      "page_section": "p. 8",
      "quote": "Our analysis revealed that 15.3% of patients...",
      "citation": "Smith et al., 2023",
      "tags": ["muscle-effects", "prevalence"],
      "created": "2024-01-15T10:45:00Z"
    }
  ]
}
```

---

### scratchpad.handover

Initiate a handover to save state and prepare for context reset.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Session to handover"
    },
    "reason": {
      "type": "string",
      "enum": ["context_full", "user_requested", "error", "pause"],
      "description": "Reason for handover"
    },
    "summary": {
      "type": "string",
      "description": "Summary of work completed so far"
    },
    "themes": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Key themes identified"
    },
    "pending_notes": {
      "type": "array",
      "items": {"type": "object"},
      "description": "Any unsaved notes to persist"
    }
  },
  "required": ["session_id"]
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "statin-research-2024-01-15-abc123",
  "handover_number": 2,
  "status": "paused",
  "progress": {
    "documents_processed": 4,
    "total_documents": 10,
    "percent": 40
  },
  "notes_saved": 23,
  "resume_context": {
    "summary": "Processed 4/10 documents on statin adverse effects...",
    "themes": ["muscle effects", "hepatic effects", "cognitive concerns"],
    "next_document": "Williams_2019.pdf",
    "resume_command": "Resume session statin-research-2024-01-15-abc123"
  },
  "message": "Handover complete. Session paused."
}
```

---

### scratchpad.resume

Resume a paused session after handover.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Session to resume"
    }
  },
  "required": ["session_id"]
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "statin-research-2024-01-15-abc123",
  "status": "active",
  "context": {
    "task": "Research adverse effects of statin medications",
    "progress": "4/10 documents (40%)",
    "notes_count": 23,
    "themes": ["muscle effects", "hepatic effects", "cognitive concerns"],
    "summary": "Processed Smith_2023, Jones_2022, Chen_2021, Garcia_2020. Key findings include 15% myalgia prevalence...",
    "next_document": {
      "name": "Williams_2019.pdf",
      "path": "/docs/Williams_2019.pdf",
      "position": 5
    }
  },
  "message": "Session resumed. Ready to continue with Williams_2019.pdf"
}
```

---

### scratchpad.update_document

Update document processing status.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Session containing the document"
    },
    "document_id": {
      "type": "string",
      "description": "Document page ID or name"
    },
    "status": {
      "type": "string",
      "enum": ["pending", "processing", "complete", "error"],
      "description": "New status"
    },
    "token_count": {
      "type": "integer",
      "description": "Estimated tokens in document"
    },
    "error_message": {
      "type": "string",
      "description": "Error details if status is 'error'"
    }
  },
  "required": ["session_id", "document_id", "status"]
}
```

---

### scratchpad.complete_session

Mark a session as complete and generate final summary.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Session to complete"
    },
    "final_summary": {
      "type": "string",
      "description": "Final summary of research findings"
    }
  },
  "required": ["session_id"]
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "statin-research-2024-01-15-abc123",
  "status": "complete",
  "final_stats": {
    "documents_processed": 10,
    "total_notes": 47,
    "handovers": 2,
    "duration_minutes": 45,
    "themes": ["muscle effects", "hepatic effects", "cognitive concerns", "drug interactions"]
  },
  "notes_by_theme": {
    "muscle effects": 18,
    "hepatic effects": 9,
    "cognitive concerns": 8,
    "drug interactions": 12
  },
  "message": "Session complete. 47 notes available for synthesis."
}
```

---

### scratchpad.list_sessions

List all research sessions.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["active", "paused", "complete", "failed", "all"],
      "default": "all",
      "description": "Filter by status"
    },
    "limit": {
      "type": "integer",
      "default": 20,
      "description": "Maximum sessions to return"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Filter by tags"
    }
  }
}
```

---

### scratchpad.check_context

Check current context usage and get handover recommendation.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Current session"
    },
    "pending_tokens": {
      "type": "integer",
      "description": "Additional tokens about to be added"
    }
  },
  "required": ["session_id"]
}
```

**Response:**
```json
{
  "success": true,
  "context_usage": {
    "current_percent": 72,
    "pending_percent": 8,
    "projected_percent": 80,
    "tokens_remaining": 20000
  },
  "recommendation": "warning",
  "message": "Context at 72%. Consider handover after current document.",
  "should_handover": false
}
```

---

## Python API

### Installation

```python
from shared.scratchpad import Scratchpad
```

### Class: Scratchpad

#### Constructor

```python
scratchpad = Scratchpad(
    session_id: Optional[str] = None,
    auto_handover: bool = True,
    handover_threshold: float = 0.75
)
```

**Parameters:**
- `session_id` - Existing session to connect to
- `auto_handover` - Automatically trigger handover when threshold reached
- `handover_threshold` - Context usage percentage to trigger handover

#### Methods

##### start_session

```python
async def start_session(
    task: str,
    documents: List[Dict] = None,
    tags: List[str] = None,
    session_id: str = None
) -> Dict:
```

Start a new research session.

```python
result = await scratchpad.start_session(
    task="Research statin adverse effects",
    documents=[
        {"name": "Smith_2023.pdf", "path": "/docs/Smith_2023.pdf"}
    ],
    tags=["medical", "research"]
)
```

##### save_note

```python
async def save_note(
    content: str,
    document: str = None,
    note_type: str = "finding",
    importance: str = "medium",
    quote: str = None,
    page_section: str = None,
    citation: str = None,
    tags: List[str] = None
) -> Dict:
```

Save a note to the current session.

```python
await scratchpad.save_note(
    content="Muscle pain reported in 15% of patients",
    document="Smith_2023.pdf",
    note_type="statistic",
    importance="high",
    quote="Our analysis revealed that 15.3% of patients...",
    page_section="p. 8",
    citation="Smith et al., 2023"
)
```

##### get_notes

```python
async def get_notes(
    document: str = None,
    note_type: str = None,
    importance: str = None,
    tags: List[str] = None,
    limit: int = 100
) -> List[Dict]:
```

Retrieve notes with optional filtering.

```python
notes = await scratchpad.get_notes(
    importance="high",
    tags=["muscle-effects"]
)
```

##### handover

```python
async def handover(
    reason: str = "context_full",
    summary: str = None,
    themes: List[str] = None
) -> Dict:
```

Perform a handover.

```python
result = await scratchpad.handover(
    reason="context_full",
    summary="Processed 4/10 documents...",
    themes=["muscle effects", "hepatic effects"]
)
```

##### resume

```python
async def resume(session_id: str = None) -> Dict:
```

Resume a paused session.

```python
context = await scratchpad.resume("statin-research-2024-01-15")
```

##### check_context

```python
def check_context(pending_tokens: int = 0) -> Dict:
```

Check context usage.

```python
status = scratchpad.check_context(pending_tokens=5000)
if status["should_handover"]:
    await scratchpad.handover()
```

##### complete

```python
async def complete(final_summary: str = None) -> Dict:
```

Complete the session.

```python
result = await scratchpad.complete(
    final_summary="Comprehensive review of statin adverse effects..."
)
```

### Context Manager

```python
async with Scratchpad.session(task="My research") as pad:
    await pad.save_note("Finding 1...")
    await pad.save_note("Finding 2...")
# Session auto-completes on exit
```

### Events

```python
scratchpad.on_handover_needed(callback)
scratchpad.on_session_complete(callback)
scratchpad.on_error(callback)
```

## Error Handling

### Error Codes

| Code | Name | Description |
|------|------|-------------|
| `SESSION_NOT_FOUND` | Session not found | Invalid session ID |
| `SESSION_LOCKED` | Session locked | Another process is using session |
| `DOCUMENT_NOT_FOUND` | Document not found | Invalid document reference |
| `NOTION_ERROR` | Notion API error | Notion API call failed |
| `RATE_LIMITED` | Rate limited | Notion rate limit hit |
| `CONTEXT_OVERFLOW` | Context overflow | Context limit exceeded |

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "No session found with ID 'invalid-id'",
    "details": {
      "session_id": "invalid-id"
    }
  }
}
```

### Retry Logic

```python
from shared.scratchpad import Scratchpad, RetryPolicy

scratchpad = Scratchpad(
    retry_policy=RetryPolicy(
        max_retries=3,
        backoff_factor=2,
        retry_on=["RATE_LIMITED", "NOTION_ERROR"]
    )
)
```

## Rate Limits

Notion API limits: 3 requests per second

The Scratchpad handles this automatically with:
- Request queuing
- Automatic backoff
- Batch operations where possible

## Related Documentation

- [NOTION_SETUP.md](./NOTION_SETUP.md) - Database configuration
- [WORKFLOW.md](./WORKFLOW.md) - Understanding the handover process
- [INTEGRATION.md](./INTEGRATION.md) - Skill integration guide
