# Scratchpad Workflow

This document explains how the Scratchpad system enables processing documents that exceed AI context limits.

## The Problem

AI models have limited context windows:

```
AI Context Window:    ~100,000 - 200,000 tokens
Average PDF:          ~10,000 - 50,000 tokens per document
Research Task:        10 PDFs = ~100,000 - 500,000 tokens

Result: AI can only hold 20-40% of research materials at once
```

Traditional approaches fail because:
- Reading all documents fills the context window
- Once full, AI "forgets" earlier documents
- No persistent memory between sessions
- Research insights are lost

## The Solution: Handover System

The Scratchpad creates persistent memory using Notion:

```
┌─────────────────────────────────────────────────────────────────┐
│                     SCRATCHPAD WORKFLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Document 1] ──► Read ──► Extract Notes ──► Save to Notion     │
│                                    │                             │
│  [Document 2] ──► Read ──► Extract Notes ──► Save to Notion     │
│                                    │                             │
│  [Document 3] ──► Read ──► Context 75% Full!                    │
│                                    │                             │
│                              ┌─────▼─────┐                       │
│                              │ HANDOVER  │                       │
│                              │           │                       │
│                              │ • Save    │                       │
│                              │   state   │                       │
│                              │ • Clear   │                       │
│                              │   context │                       │
│                              │ • Resume  │                       │
│                              └─────┬─────┘                       │
│                                    │                             │
│  [Document 4] ──► Read ──► Extract Notes ──► Save to Notion     │
│                                    │                             │
│                                   ...                            │
│                                    │                             │
│  [Document 10] ──► Complete!                                     │
│                                    │                             │
│                              ┌─────▼─────┐                       │
│                              │  COMPILE  │                       │
│                              │           │                       │
│                              │ Retrieve  │                       │
│                              │ all notes │                       │
│                              │ from      │                       │
│                              │ Notion    │                       │
│                              └─────┬─────┘                       │
│                                    │                             │
│                              ┌─────▼─────┐                       │
│                              │  OUTPUT   │                       │
│                              │           │                       │
│                              │ Write     │                       │
│                              │ article,  │                       │
│                              │ report,   │                       │
│                              │ summary   │                       │
│                              └───────────┘                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Session
A research session groups related documents and notes together. Each session has:
- Unique ID (e.g., `statin-research-2024-01-15`)
- Task description
- Status (active/paused/complete)
- Progress tracking

### Handover
When context fills up, a handover:
1. Saves current state to Notion
2. Creates a summary of progress
3. Signals that context should be cleared
4. Provides resume instructions

### Notes
Atomic pieces of information extracted from documents:
- Key findings
- Direct quotes with citations
- Statistics and data points
- Questions for follow-up
- Contradictions between sources

## Example Session

### Starting Research

```
User: Research adverse effects of statins using these 10 PDFs
      [Attaches: Smith_2023.pdf, Jones_2022.pdf, Chen_2021.pdf, ...]

AI: Starting research session...
    Session ID: statin-adverse-effects-2024-01-15
    Documents: 10 PDFs queued for processing

    Processing document 1/10: Smith_2023.pdf
    - Title: "Long-term Statin Safety: A 10-Year Follow-up"
    - Pages: 12
    - Extracting key findings...

    Notes saved:
    ✓ Finding: Muscle pain reported in 15% of patients (Smith 2023, p.3)
    ✓ Finding: Risk increases with age >65 (Smith 2023, p.7)
    ✓ Quote: "The myopathy risk appears dose-dependent" (Smith 2023, p.8)

    Context usage: 25%
```

### Automatic Handover

```
AI: Processing document 4/10: Garcia_2020.pdf
    ...extracting notes...

    ⚠️  Context is 78% full. Initiating handover.

    ═══════════════════════════════════════════════
    HANDOVER SUMMARY
    ═══════════════════════════════════════════════

    Session: statin-adverse-effects-2024-01-15
    Progress: 4/10 documents (40%)
    Notes collected: 23 findings

    Key themes identified so far:
    1. Muscle-related side effects (8 notes)
    2. Hepatic effects (5 notes)
    3. Cognitive concerns (4 notes)
    4. Drug interactions (6 notes)

    State saved to Notion. Ready for fresh context.

    To resume: "Continue research session statin-adverse-effects-2024-01-15"
    ═══════════════════════════════════════════════
```

### Resuming After Handover

```
User: Continue research session statin-adverse-effects-2024-01-15

AI: Resuming research session...

    Loading session state from Notion...
    ✓ Session: statin-adverse-effects-2024-01-15
    ✓ Task: Research adverse effects of statins
    ✓ Progress: 4/10 documents complete
    ✓ Notes: 23 findings collected
    ✓ Summary: Key themes loaded

    Continuing with document 5/10: Williams_2019.pdf
    ...
```

### Completing Research

```
AI: Processing document 10/10: Thompson_2018.pdf
    ...extracting notes...

    ═══════════════════════════════════════════════
    RESEARCH COMPLETE
    ═══════════════════════════════════════════════

    Session: statin-adverse-effects-2024-01-15
    Documents processed: 10/10 (100%)
    Total notes: 47 findings
    Total handovers: 2

    Summary of findings:
    • Muscle effects: 18 notes from 8 sources
    • Hepatic effects: 9 notes from 6 sources
    • Cognitive effects: 8 notes from 4 sources
    • Drug interactions: 12 notes from 7 sources

    Ready to write your article.
    ═══════════════════════════════════════════════

User: Write the article now

AI: Retrieving all 47 notes from Notion...

    Loading notes by theme:
    ✓ Muscle effects (18 notes)
    ✓ Hepatic effects (9 notes)
    ✓ Cognitive effects (8 notes)
    ✓ Drug interactions (12 notes)

    Writing article...

    # Adverse Effects of Statins: A Comprehensive Review

    ## Introduction
    This review synthesizes findings from 10 peer-reviewed studies...

    ## Muscle-Related Side Effects
    Muscle symptoms represent the most commonly reported adverse effect
    of statin therapy. Smith et al. (2023) found that 15% of patients
    experienced muscle pain during long-term follow-up...

    [Continues with properly cited article...]
```

## Workflow States

### Session States

```
┌────────┐     start      ┌────────┐
│ (none) │ ─────────────► │ active │
└────────┘                └────┬───┘
                               │
                    ┌──────────┼──────────┐
                    │          │          │
                handover    complete    error
                    │          │          │
                    ▼          ▼          ▼
              ┌────────┐ ┌──────────┐ ┌────────┐
              │ paused │ │ complete │ │ failed │
              └────┬───┘ └──────────┘ └────────┘
                   │
                 resume
                   │
                   ▼
              ┌────────┐
              │ active │
              └────────┘
```

### Document States

```
pending ──► processing ──► complete
                │
                └──► error
```

## Context Management

### Monitoring Context Usage

The system tracks estimated context usage:

```python
# Approximate token counts
TOKENS_PER_PAGE_PDF = 500
TOKENS_PER_NOTE = 100
TOKENS_SYSTEM_PROMPT = 2000
TOKENS_BUFFER = 5000

# Calculate usage
current_tokens = (
    TOKENS_SYSTEM_PROMPT +
    sum(doc.token_count for doc in current_docs) +
    sum(note.token_count for note in pending_notes) +
    TOKENS_BUFFER
)

usage_percent = current_tokens / MAX_CONTEXT_TOKENS * 100
```

### Handover Thresholds

| Threshold | Action |
|-----------|--------|
| 60% | Warning logged, continue processing |
| 75% | Prepare handover, finish current document |
| 85% | Initiate handover immediately |
| 95% | Emergency save, potential data loss warning |

### What Gets Saved in Handover

1. **Session State**
   - Current progress (documents processed/total)
   - Accumulated themes and patterns
   - Open questions

2. **All Notes**
   - Every finding already saved to Notion
   - Notes from current document saved before handover

3. **Resume Context**
   - Summary of work completed
   - Key patterns identified
   - Next document in queue

## Multi-Skill Collaboration

Different skills can contribute to the same session:

```
┌──────────────────────────────────────────────────────────────┐
│                    RESEARCH SESSION                           │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │  Document   │    │  Citation   │    │  Analysis   │       │
│  │  Processor  │    │  Extractor  │    │    Skill    │       │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘       │
│         │                  │                  │               │
│         ▼                  ▼                  ▼               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                    SCRATCHPAD                           │  │
│  │                                                         │  │
│  │  • Document Processor saves content summaries          │  │
│  │  • Citation Extractor saves formatted references       │  │
│  │  • Analysis Skill saves themes and patterns            │  │
│  │                                                         │  │
│  └────────────────────────────────────────────────────────┘  │
│                              │                                │
│                              ▼                                │
│                    ┌─────────────────┐                       │
│                    │  Writing Skill  │                       │
│                    │                 │                       │
│                    │  Retrieves all  │                       │
│                    │  notes, writes  │                       │
│                    │  final output   │                       │
│                    └─────────────────┘                       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Best Practices

### For Users

1. **Be specific about the task**
   ```
   Good: "Research statin side effects, focusing on muscle symptoms"
   Less good: "Tell me about statins"
   ```

2. **Let the system manage handovers**
   - Don't interrupt mid-document
   - Wait for handover completion before changing topics

3. **Review notes periodically**
   - Check Notion to see what's been captured
   - Add manual notes if needed

### For Skill Developers

1. **Always use session IDs**
   - Enables proper note grouping
   - Allows resume after handover

2. **Save notes incrementally**
   - Don't batch all notes at the end
   - Save as you extract

3. **Include source information**
   - Document name, page/section
   - Direct quotes when relevant

4. **Categorize notes by type**
   - Helps with later retrieval
   - Enables themed summaries

## Limitations

1. **Token estimation is approximate**
   - Different content has varying token density
   - Buffer helps but isn't perfect

2. **Handover has overhead**
   - Takes time to save state and resume
   - 2-3 handovers is normal for 10 documents

3. **Notion API rate limits**
   - 3 requests per second limit
   - Batched operations help

4. **No real-time collaboration**
   - One agent per session at a time
   - Multi-agent requires coordination

## Related Documentation

- [NOTION_SETUP.md](./NOTION_SETUP.md) - Database configuration
- [API_REFERENCE.md](./API_REFERENCE.md) - Available operations
- [INTEGRATION.md](./INTEGRATION.md) - Skill integration guide
