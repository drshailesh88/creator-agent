# Integrating Your Skills with Scratchpad

This guide shows how to use the Scratchpad system from your skills and agents.

## Overview

Any skill can use the Scratchpad to:
- Persist research notes across context resets
- Share findings between skills
- Handle large document sets
- Create lasting records of work

## Quick Start

### For MCP Tool Users (Claude/Agents)

```
Use tool: scratchpad.start_session
Arguments: {"task": "Research topic X"}

Use tool: scratchpad.save_note
Arguments: {"content": "Important finding...", "session_id": "..."}

Use tool: scratchpad.get_notes
Arguments: {"session_id": "..."}
```

### For Python Skills

```python
from shared.scratchpad import Scratchpad

async def my_research_skill():
    pad = Scratchpad()

    # Start session
    session = await pad.start_session(task="Research topic X")

    # Process and save notes
    await pad.save_note("Important finding...")
    await pad.save_note("Another finding...")

    # Complete
    await pad.complete()
```

## Integration Patterns

### Pattern 1: Research and Write

The most common pattern - one skill researches, another writes.

```python
# research_skill.py
from shared.scratchpad import Scratchpad

async def research_documents(documents: list, task: str) -> str:
    """Process documents and save findings to scratchpad."""
    pad = Scratchpad()

    session = await pad.start_session(
        task=task,
        documents=[{"name": d.name, "path": d.path} for d in documents]
    )

    for doc in documents:
        # Check if we need to handover
        if pad.check_context()["should_handover"]:
            await pad.handover()
            # Signal to orchestrator that we need a fresh context
            return f"HANDOVER:{session['session_id']}"

        # Process document
        content = await process_document(doc)
        findings = await extract_findings(content)

        for finding in findings:
            await pad.save_note(
                content=finding.summary,
                document=doc.name,
                note_type=finding.type,
                quote=finding.quote,
                page_section=finding.location
            )

        await pad.update_document(doc.name, status="complete")

    await pad.complete()
    return session["session_id"]
```

```python
# writing_skill.py
from shared.scratchpad import Scratchpad

async def write_article(session_id: str) -> str:
    """Write article using notes from scratchpad."""
    pad = Scratchpad(session_id=session_id)

    # Get all notes
    notes = await pad.get_notes()

    # Group by theme
    themes = group_notes_by_theme(notes)

    # Generate article
    article = await generate_article(themes)

    return article
```

### Pattern 2: Multi-Skill Pipeline

Multiple skills contribute to the same research session.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Document   │────►│  Citation   │────►│  Analysis   │
│  Processor  │     │  Extractor  │     │    Skill    │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────┐
│                    SCRATCHPAD                         │
│                   (Shared Session)                    │
└──────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Writing Skill  │
                  └─────────────────┘
```

```python
# orchestrator.py
async def research_pipeline(documents: list, task: str):
    """Orchestrate multi-skill research pipeline."""

    # Start shared session
    pad = Scratchpad()
    session = await pad.start_session(task=task)
    session_id = session["session_id"]

    # Phase 1: Document processing
    for doc in documents:
        await document_processor.process(doc, session_id)
        await citation_extractor.extract(doc, session_id)
        await analysis_skill.analyze(doc, session_id)

        # Check for handover need
        if pad.check_context()["should_handover"]:
            await pad.handover()
            # Resume in new context
            await pad.resume()

    # Phase 2: Writing
    article = await writing_skill.write(session_id)

    # Complete
    await pad.complete()

    return article
```

### Pattern 3: Incremental Processing

Process documents one at a time, handling handovers gracefully.

```python
from shared.scratchpad import Scratchpad

class IncrementalResearcher:
    def __init__(self):
        self.pad = Scratchpad(auto_handover=True)

    async def start(self, task: str, documents: list):
        """Start or resume research."""

        # Check for existing session
        existing = await self.pad.list_sessions(
            status="paused",
            tags=[self._task_hash(task)]
        )

        if existing:
            # Resume existing session
            await self.pad.resume(existing[0]["session_id"])
        else:
            # Start new session
            await self.pad.start_session(
                task=task,
                documents=documents,
                tags=[self._task_hash(task)]
            )

    async def process_next(self) -> dict:
        """Process next pending document."""
        session = await self.pad.get_session(include_documents=True)

        # Find next pending document
        pending = [d for d in session["documents"] if d["status"] == "pending"]
        if not pending:
            return {"status": "complete"}

        doc = pending[0]

        # Check context before processing
        context = self.pad.check_context(pending_tokens=doc.get("token_count", 10000))
        if context["should_handover"]:
            return {"status": "handover_needed"}

        # Process document
        await self._process_document(doc)

        return {"status": "continue", "processed": doc["name"]}

    async def _process_document(self, doc: dict):
        """Process a single document."""
        await self.pad.update_document(doc["name"], status="processing")

        # Your document processing logic here
        content = await read_document(doc["path"])
        findings = await extract_findings(content)

        for finding in findings:
            await self.pad.save_note(
                content=finding,
                document=doc["name"]
            )

        await self.pad.update_document(doc["name"], status="complete")
```

### Pattern 4: Handover-Aware Agent

Agent that handles handovers automatically.

```python
from shared.scratchpad import Scratchpad

class ResearchAgent:
    """Agent that manages its own handovers."""

    def __init__(self, max_context_percent: float = 0.75):
        self.pad = Scratchpad(handover_threshold=max_context_percent)
        self.session_id = None

    async def run(self, task: str, documents: list) -> str:
        """Run research with automatic handover handling."""

        # Start session
        session = await self.pad.start_session(task=task, documents=documents)
        self.session_id = session["session_id"]

        while True:
            result = await self._process_batch()

            if result["status"] == "complete":
                break
            elif result["status"] == "handover":
                # Return handover signal
                return self._format_handover_response(result)

        return await self._complete_research()

    async def resume(self, session_id: str) -> str:
        """Resume from handover."""
        context = await self.pad.resume(session_id)
        self.session_id = session_id

        return await self.run_from_current_state()

    async def _process_batch(self) -> dict:
        """Process documents until handover needed or complete."""
        session = await self.pad.get_session(include_documents=True)

        for doc in session["documents"]:
            if doc["status"] != "pending":
                continue

            # Check context
            context = self.pad.check_context()
            if context["should_handover"]:
                handover_result = await self.pad.handover(
                    summary=self._generate_summary(),
                    themes=self._identify_themes()
                )
                return {"status": "handover", "result": handover_result}

            # Process document
            await self._process_document(doc)

        return {"status": "complete"}

    def _format_handover_response(self, result: dict) -> str:
        """Format response for handover."""
        return f"""
HANDOVER REQUIRED

Session: {self.session_id}
Progress: {result['result']['progress']['percent']}%
Notes collected: {result['result']['notes_saved']}

To resume: "Resume research session {self.session_id}"
"""
```

## Skill-Specific Integration

### Document Processor Integration

```python
from skills.document_processor import DocumentProcessor
from shared.scratchpad import Scratchpad

async def process_with_scratchpad(file_path: str, session_id: str):
    """Process document and save to scratchpad."""

    processor = DocumentProcessor()
    pad = Scratchpad(session_id=session_id)

    # Process document
    result = processor.process(file_path)

    if not result.success:
        await pad.update_document(file_path, status="error", error_message=result.error)
        return

    # Save summary as note
    await pad.save_note(
        content=f"Document processed: {result.word_count} words, {result.page_count} pages",
        document=file_path,
        note_type="summary",
        metadata={
            "word_count": result.word_count,
            "page_count": result.page_count,
            "document_type": result.document_type.value
        }
    )

    # Update document status
    await pad.update_document(
        file_path,
        status="complete",
        token_count=result.word_count * 1.3  # Rough estimate
    )
```

### Notion MCP Integration

```python
from skills.notion import notion_mcp
from shared.scratchpad import Scratchpad

async def sync_notes_to_notion_page(session_id: str, target_page_id: str):
    """Sync scratchpad notes to a Notion page."""

    pad = Scratchpad(session_id=session_id)
    notes = await pad.get_notes()

    # Format notes for Notion
    content = format_notes_as_markdown(notes)

    # Append to Notion page
    await notion_mcp.append_to_page(
        page_id=target_page_id,
        content=content
    )
```

### Pensieve Integration

```python
from skills.pensieve import pensieve
from shared.scratchpad import Scratchpad

async def save_research_to_pensieve(session_id: str):
    """Save key research findings to Pensieve for long-term memory."""

    pad = Scratchpad(session_id=session_id)
    session = await pad.get_session()
    notes = await pad.get_notes(importance="critical")

    # Save to Pensieve
    for note in notes:
        await pensieve.save_memory(
            content=f"Research finding: {note['content']}",
            tags=["research"] + note.get("tags", []),
            mood="curious",
            source="research"
        )
```

## Error Handling

### Handling Notion Errors

```python
from shared.scratchpad import Scratchpad, NotionError, RateLimitError

async def safe_save_note(pad: Scratchpad, content: str, **kwargs):
    """Save note with error handling."""
    try:
        return await pad.save_note(content, **kwargs)
    except RateLimitError:
        # Wait and retry
        await asyncio.sleep(1)
        return await pad.save_note(content, **kwargs)
    except NotionError as e:
        # Log and continue
        logger.error(f"Failed to save note: {e}")
        # Optionally queue for retry
        return None
```

### Handling Handover Failures

```python
async def robust_handover(pad: Scratchpad):
    """Perform handover with fallback."""
    try:
        return await pad.handover()
    except Exception as e:
        # Emergency local save
        notes = pad._pending_notes  # Access pending notes
        save_locally(notes, f"emergency_{pad.session_id}.json")
        raise HandoverError(f"Handover failed, notes saved locally: {e}")
```

## Testing

### Unit Testing with Mock

```python
import pytest
from unittest.mock import AsyncMock, patch
from shared.scratchpad import Scratchpad

@pytest.fixture
def mock_scratchpad():
    with patch.object(Scratchpad, '_notion_client') as mock:
        mock.create_page = AsyncMock(return_value={"id": "test-id"})
        mock.query_database = AsyncMock(return_value={"results": []})
        yield Scratchpad()

async def test_start_session(mock_scratchpad):
    result = await mock_scratchpad.start_session(task="Test task")
    assert result["success"] is True
    assert "session_id" in result
```

### Integration Testing

```python
import pytest
from shared.scratchpad import Scratchpad

@pytest.mark.integration
async def test_full_workflow():
    """Test complete scratchpad workflow."""
    pad = Scratchpad()

    # Start session
    session = await pad.start_session(task="Integration test")
    assert session["success"]

    # Save notes
    for i in range(5):
        await pad.save_note(f"Test finding {i}")

    # Get notes
    notes = await pad.get_notes()
    assert len(notes) == 5

    # Complete
    result = await pad.complete()
    assert result["status"] == "complete"
```

## Best Practices

### 1. Always Use Session IDs

```python
# Good
await pad.save_note("Finding...", session_id="my-session")

# Avoid (relies on implicit state)
await pad.save_note("Finding...")
```

### 2. Save Notes Incrementally

```python
# Good - save as you go
for doc in documents:
    findings = process(doc)
    for f in findings:
        await pad.save_note(f)

# Avoid - batching risks losing work
all_findings = []
for doc in documents:
    all_findings.extend(process(doc))
await pad.save_notes_batch(all_findings)
```

### 3. Include Source Information

```python
# Good - traceable
await pad.save_note(
    content="15% of patients experienced side effects",
    document="Smith_2023.pdf",
    page_section="Results, p. 8",
    citation="Smith et al., 2023"
)

# Avoid - no provenance
await pad.save_note("15% of patients experienced side effects")
```

### 4. Use Appropriate Note Types

```python
# Good - categorized
await pad.save_note(content="...", note_type="statistic")
await pad.save_note(content="...", note_type="quote")
await pad.save_note(content="...", note_type="question")

# Avoid - everything as generic finding
await pad.save_note(content="...", note_type="finding")
await pad.save_note(content="...", note_type="finding")
```

### 5. Handle Handovers Gracefully

```python
# Good - check before heavy operations
if pad.check_context()["projected_percent"] > 80:
    await pad.handover()

# Avoid - hitting the limit unexpectedly
process_large_document(doc)  # Might overflow
```

## Debugging

### Enable Debug Logging

```python
import logging
logging.getLogger("scratchpad").setLevel(logging.DEBUG)
```

### Inspect Session State

```python
session = await pad.get_session(include_notes=True, include_documents=True)
print(json.dumps(session, indent=2))
```

### Check Notion Directly

```python
# List all sessions in Notion
from skills.notion.notion_mcp import list_databases, search_pages

databases = await list_databases()
sessions = await search_pages("session")
```

## Related Documentation

- [NOTION_SETUP.md](./NOTION_SETUP.md) - Database configuration
- [WORKFLOW.md](./WORKFLOW.md) - Understanding the handover process
- [API_REFERENCE.md](./API_REFERENCE.md) - Complete API documentation
