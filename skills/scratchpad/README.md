# Scratchpad MCP Server

A shared infrastructure for managing long-form content creation with multiple documents. Designed for Clawdbot skills that need persistent note-taking across context refreshes.

## Overview

When processing multiple PDFs/documents, AI context windows fill up quickly. The Scratchpad provides:

- **Note-taking that persists** - Notes are saved to disk and survive context refreshes
- **Progress tracking** - Track which documents have been processed and where you left off
- **Handover system** - Seamlessly switch contexts with a summary of what's done and what's next
- **Resume capability** - Pick up paused research sessions right where you left off

## Installation

### Prerequisites

```bash
pip install mcp
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SCRATCHPAD_DIR` | Directory for storing session data | `~/.clawdbot/scratchpad` |
| `LOG_LEVEL` | Logging level (debug, info, warn, error) | `info` |

### Running the Server

```bash
# Direct execution
python mcp_server.py

# Or via the MCP configuration in mcporter.json
```

## Tools

### start_session

Start a new research session with documents.

```json
{
  "task": "Analyze Q4 financial reports",
  "document_paths": ["/path/to/report1.pdf", "/path/to/report2.pdf"],
  "session_name": "Q4 Financial Analysis"
}
```

**Returns:**
```json
{
  "success": true,
  "session_id": "abc123",
  "documents_to_process": 2,
  "message": "Research session started!"
}
```

### save_notes

Save research notes to the scratchpad.

```json
{
  "content": "Key finding: Revenue increased 15% YoY",
  "document_id": "report1",
  "tags": ["revenue", "growth"],
  "section": "key_findings"
}
```

**Returns:**
```json
{
  "success": true,
  "note_id": "note123",
  "message": "Notes saved! They'll be here when you need them."
}
```

### get_notes

Retrieve notes with optional filters.

```json
{
  "document_id": "report1",
  "tags": ["revenue"],
  "section": "key_findings"
}
```

**Returns:**
```json
{
  "success": true,
  "count": 3,
  "notes": [
    {
      "id": "note123",
      "content": "Key finding: Revenue increased 15% YoY",
      "timestamp": "2024-01-15T10:30:00",
      "tags": ["revenue", "growth"],
      "section": "key_findings"
    }
  ]
}
```

### mark_progress

Track reading/processing progress on a document.

```json
{
  "document_id": "report1",
  "status": "in_progress",
  "position": "page 15, Section 3.2",
  "notes": "Need to review the appendix tables"
}
```

**Status options:**
- `not_started` - Document queued but not yet processed
- `in_progress` - Currently being processed
- `completed` - Fully processed
- `needs_review` - Needs another look

### get_progress

Get overall research progress.

```json
{
  "session_id": "abc123"  // optional, defaults to current session
}
```

**Returns:**
```json
{
  "success": true,
  "session_id": "abc123",
  "task": "Analyze Q4 financial reports",
  "documents": {
    "total": 5,
    "completed": 2,
    "in_progress": 1,
    "not_started": 2,
    "progress_percent": 40.0
  },
  "notes_count": 15
}
```

### handover

Prepare for context refresh. Saves all state for seamless continuation.

```json
{
  "summary": "Analyzed 3 of 5 reports. Key theme: cost optimization.",
  "next_steps": [
    "Complete report4.pdf analysis",
    "Cross-reference findings with Q3 data",
    "Draft executive summary"
  ]
}
```

**Returns:**
```json
{
  "success": true,
  "message": "All saved and ready for a fresh start!",
  "handover": {
    "timestamp": "2024-01-15T14:30:00",
    "summary": "Analyzed 3 of 5 reports...",
    "next_steps": ["Complete report4.pdf analysis", ...],
    "context_snapshot": { ... }
  }
}
```

### resume_session

Resume a paused research session.

```json
{
  "session_id": "abc123"
}
```

**Returns:**
```json
{
  "success": true,
  "message": "Welcome back! Resuming: Q4 Financial Analysis",
  "session_id": "abc123",
  "task": "Analyze Q4 financial reports",
  "progress": { ... },
  "last_handover": { ... },
  "notes_count": 15
}
```

### list_sessions

List all research sessions.

```json
{
  "status": "paused",  // "active", "paused", "completed", "all"
  "limit": 10
}
```

**Returns:**
```json
{
  "success": true,
  "count": 3,
  "sessions": [
    {
      "id": "abc123",
      "task": "Analyze Q4 financial reports",
      "name": "Q4 Financial Analysis",
      "status": "paused",
      "created_at": "2024-01-15T09:00:00",
      "document_count": 5,
      "notes_count": 15,
      "is_current": true
    }
  ]
}
```

### get_writing_context

Get all notes formatted for the writing phase.

```json
{
  "session_id": "abc123",
  "format": "detailed"  // "outline", "detailed", "summary"
}
```

**Format options:**
- `outline` - Condensed view with truncated notes
- `detailed` - Full notes organized by section and document
- `summary` - Brief overview with counts and themes

## Usage Examples

### Multi-Document Research Workflow

```python
# 1. Start a research session
await call_tool("start_session", {
    "task": "Literature review on machine learning in healthcare",
    "document_paths": ["paper1.pdf", "paper2.pdf", "paper3.pdf"],
    "session_name": "ML Healthcare Review"
})

# 2. Process documents and save notes
await call_tool("save_notes", {
    "content": "Paper introduces novel approach to medical imaging...",
    "document_id": "paper1.pdf",
    "tags": ["imaging", "methodology"],
    "section": "key_findings"
})

# 3. Mark progress
await call_tool("mark_progress", {
    "document_id": "paper1.pdf",
    "status": "completed"
})

# 4. When context fills up, handover
await call_tool("handover", {
    "summary": "Completed analysis of 2/3 papers. Main themes: imaging, NLP.",
    "next_steps": ["Finish paper3.pdf", "Compare methodologies"]
})

# 5. Later, resume the session
await call_tool("resume_session", {
    "session_id": "abc123"
})

# 6. Get organized notes for writing
await call_tool("get_writing_context", {
    "format": "detailed"
})
```

### Integration with Other Skills

The scratchpad is designed to work with other Clawdbot skills:

```python
# Document Processor skill extracts text
doc_content = await document_processor.process("report.pdf")

# Save extracted insights to scratchpad
await scratchpad.save_notes({
    "content": doc_content["summary"],
    "document_id": "report.pdf",
    "section": "summaries"
})

# Later, Pensieve skill can save important findings as memories
important_finding = scratchpad.get_notes(section="key_findings")[0]
await pensieve.save_memory(important_finding["content"])
```

## Storage Structure

Sessions are stored as JSON files in the configured directory:

```
~/.clawdbot/scratchpad/
  sessions/
    abc123.json
    def456.json
  current_session.json
```

Each session file contains:
- Session metadata (id, task, name, status, timestamps)
- Document progress tracking
- All notes with tags and sections
- Handover history

## Clawdbot Personality

The scratchpad maintains Clawdbot's warm personality in all responses:

- **Starting sessions**: "Research session started! I'm ready to help you with..."
- **Saving notes**: "Notes saved! They'll be here when you need them."
- **Progress updates**: "Nicely done! This one's all wrapped up."
- **Handovers**: "All saved and ready for a fresh start! Here's where we left off..."
- **Resuming**: "Welcome back! Resuming: [session name]"

## Error Handling

All tools return structured responses:

```json
{
  "success": false,
  "error": "No active session. Start a session first.",
  "hint": "Try starting a new session with start_session."
}
```

## License

MIT
