"""
Prompt templates for the handover and resume system.

These templates are used to communicate session state to AI assistants
during context handovers and session resumption.

All templates use Python string formatting with named placeholders.
"""

# =============================================================================
# HANDOVER PROMPTS
# =============================================================================

HANDOVER_PROMPT = """
## Context Handover - Resuming Research Task

You are resuming a research task. Here's where we left off:

### Task
{task}

### Documents Processed ({completed}/{total})
{document_status}

### Current Position
{current_position}

### Progress Summary
- Context refreshes: {context_refreshes}
- Citations collected: {citations_count}

### Key Findings So Far
{key_findings}

### Notes Summary
{notes_summary}

### Your Next Action
**{next_action}**

---

Continue from where we left off. Remember to:
1. Save notes frequently to the scratchpad
2. Record citations in proper format
3. Note any important findings
4. Update document progress as you read

If you need another context refresh, prepare a handover state.
"""


CONTEXT_REFRESH_TEMPLATE = """
## Context Refresh #{refresh_count}

The previous context window was exhausted. Here is the compressed state:

**Task**: {task}

**Progress**: {completed}/{total} documents ({progress_percent:.1f}%)

**Where We Left Off**:
- Document: {current_document}
- Position: {current_position}

**Key Information Preserved**:
{preserved_info}

**Immediate Next Steps**:
{next_steps}

Please continue the work from this point.
"""


# =============================================================================
# RESUME PROMPTS
# =============================================================================

RESUME_SYSTEM_PROMPT = """
## Resuming Session

You are continuing a previously started research session.

### Task
{task}

### Progress
{progress}

### Current Document
{current_document} - {position}

### Notes Summary
{notes_summary}

### Key Findings
{key_findings}

### Next Steps
{next_steps}

### Session Info
- Context refreshes so far: {handover_count}

---

Please continue the research from where it was left off.
Remember to save notes and update progress as you work.
"""


PROGRESS_SUMMARY_TEMPLATE = """Documents: {completed}/{total} complete ({pending} pending)
Overall progress: {overall_percent:.1f}%
Notes taken: {notes_count}
Context refreshes: {context_refreshes}"""


# =============================================================================
# NOTE TAKING PROMPTS
# =============================================================================

NOTE_TAKING_PROMPT = """
As you read this document, extract and save notes on:

1. **Key Findings** relevant to: {task}
   - Main conclusions and arguments
   - Supporting evidence
   - Novel insights

2. **Important Data**
   - Statistics and metrics
   - Quantitative results
   - Sample sizes and confidence intervals

3. **Citations** in format:
   - Author(s), Title, Journal/Source, Year
   - DOI or URL if available

4. **Methodology Notes** (if relevant)
   - Study design
   - Methods used
   - Limitations acknowledged

5. **Connections & Contradictions**
   - How this relates to other findings
   - Any debates or disagreements in the literature
   - Areas of consensus

Save notes frequently to the scratchpad. Each note should be self-contained
and useful even without the original document context.
"""


STRUCTURED_NOTE_PROMPT = """
When taking notes, use this structure:

## Finding
[Main point or finding]

## Evidence
[Supporting data or quotes]

## Source
[Citation in format: Author (Year). Title. Journal, Volume(Issue), Pages.]

## Relevance
[How this relates to the research task: {task}]

## Tags
[Relevant categories: methodology, results, theory, etc.]
"""


# =============================================================================
# SUMMARIZATION PROMPTS
# =============================================================================

NOTES_SUMMARIZATION_PROMPT = """
Summarize the following research notes while preserving all key information.

**Research Task**: {task}

**Notes to Summarize**:
{notes}

**Requirements**:
1. Preserve all key findings and data points
2. Keep all citations intact
3. Maintain connections between related points
4. Maximum length: approximately {max_tokens} tokens
5. Organize by theme or document source

**Output**: A condensed summary that captures the essential information
for someone continuing this research task.
"""


KEY_FINDINGS_EXTRACTION_PROMPT = """
Extract the {max_findings} most important findings from these research notes.

**Research Task**: {task}

**Notes**:
{notes}

**Output Format**:
- Finding 1: [Concise statement of key finding]
- Finding 2: [Concise statement of key finding]
...

Focus on:
- Novel or surprising results
- Quantitative data
- Conclusions that directly address the research task
- Points of consensus or debate

Each finding should be self-contained and understandable without context.
"""


CITATION_EXTRACTION_PROMPT = """
Extract all citations from these research notes in standardized format.

**Notes**:
{notes}

**Output Format** (one per line):
Author(s). (Year). Title. Journal/Source, Volume(Issue), Pages. DOI/URL

If information is missing, include what is available.
Deduplicate any repeated citations.
"""


# =============================================================================
# SYNTHESIS PROMPTS
# =============================================================================

SYNTHESIS_PROMPT = """
Based on the research notes collected, synthesize the findings.

**Research Task**: {task}

**Key Findings**:
{key_findings}

**Notes Summary**:
{notes_summary}

**Citations**:
{citations}

**Instructions**:
1. Identify main themes and patterns
2. Note areas of agreement and disagreement
3. Highlight gaps in the literature
4. Draw preliminary conclusions
5. Suggest areas for further investigation

Provide a coherent synthesis that addresses the original research task.
"""


FINAL_REPORT_PROMPT = """
Generate a final report for the research task.

**Task**: {task}

**Summary of Findings**:
{findings_summary}

**Key Conclusions**:
{conclusions}

**Methodology**:
- Documents reviewed: {documents_count}
- Total notes: {notes_count}
- Context refreshes: {refresh_count}

**Report Structure**:
1. Executive Summary
2. Key Findings
3. Methodology
4. Detailed Analysis
5. Conclusions
6. References

Generate a well-structured report suitable for the intended audience.
"""


# =============================================================================
# ERROR & STATUS PROMPTS
# =============================================================================

SESSION_NOT_FOUND_PROMPT = """
The requested session ({session_id}) was not found.

Available actions:
1. Start a new session with the task
2. List existing sessions to find the correct one
3. Check if the session ID is correct
"""


NO_DOCUMENTS_PROMPT = """
No documents are queued for this research session.

Please add documents to process:
1. Provide file paths or URLs
2. Specify document titles for reference
3. Set priority order if needed

Once documents are added, the research can begin.
"""


TASK_COMPLETE_PROMPT = """
## Research Task Complete

**Task**: {task}

**Final Statistics**:
- Documents processed: {documents_count}
- Notes taken: {notes_count}
- Citations collected: {citations_count}
- Context refreshes: {refresh_count}

**Summary**:
{summary}

The session has been marked as complete.
Use the notes and findings to proceed with the next phase of work.
"""
