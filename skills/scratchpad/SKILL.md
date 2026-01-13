---
name: scratchpad
description: Shared scratchpad for multi-document research and long-form content
version: 1.0.0
author: Clawdbot
tags:
  - research
  - notes
  - documents
  - persistence
  - handover
mcp_server: mcp_server.py
---

# Scratchpad Skill

A shared infrastructure for managing long-form content creation with multiple documents.

## Overview

When processing multiple PDFs/documents, AI context windows fill up. This skill provides:
- Note-taking that persists across context refreshes
- Progress tracking across multiple documents
- Handover system for seamless context switches
- Resume capability for paused research

## Commands

- "Start research session with these PDFs"
- "Save notes about [topic]"
- "What's my research progress?"
- "Resume my research on [topic]"
- "Handover" (when context is full)

## Personality Guidelines

Maintain Clawdbot's warmth when:
- Acknowledging note saves
- Reporting progress
- Performing handovers ("I've saved everything, ready to continue fresh!")

## Use Cases

### Multi-Document Research
When analyzing multiple PDFs or documents for a research project, the scratchpad:
1. Tracks which documents have been processed
2. Stores extracted insights and notes
3. Maintains a summary of findings across context refreshes

### Long-Form Content Creation
When writing lengthy content that spans multiple sessions:
1. Stores outline and draft sections
2. Tracks writing progress
3. Preserves context between sessions

### Context Handover
When the context window fills up during a long task:
1. Captures current state and progress
2. Summarizes what's been done
3. Notes what still needs to be completed
4. Enables seamless continuation in a fresh context

## Integration

The scratchpad integrates with:
- **Document Processor** - Store notes from processed documents
- **Pensieve** - Optionally save important insights as memories
- **Any Clawdbot skill** - Shared note-taking infrastructure
