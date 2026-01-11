---
name: notion
description: "Read and write to Notion databases and pages"
version: "1.0.0"
author: "Clawdbot"
mcp_server: "./notion_mcp.py"
---

# Notion Integration Skill

This skill enables Clawdbot to seamlessly interact with Notion workspaces, allowing for reading, writing, searching, and managing content across databases and pages.

## Overview

The Notion skill provides a bridge between Clawdbot and your Notion workspace through the official Notion API. It supports:

- **Creating new pages** in databases with custom properties
- **Reading page content** and metadata
- **Searching across** your entire workspace or specific databases
- **Updating existing pages** with new content
- **Appending content** to existing pages
- **Listing available databases** for discovery

## Commands

### write-to-notion

Create a new page in a Notion database with specified content and properties.

**Usage:**
```
Write to notion: [content] in database [database_name]
Save this to notion in [database_name]: [content]
```

**Examples:**
- "Write to notion: Meeting notes from today's standup in database Meeting Notes"
- "Save this blog draft to notion in Content Ideas"

### read-page

Retrieve and display the content of a specific Notion page.

**Usage:**
```
Read notion page: [page_title or page_id]
Get page from notion: [page_title]
```

**Examples:**
- "Read notion page: Q4 Planning Document"
- "Get page from notion: Weekly Review Template"

### search-notion

Search for pages and databases matching a query.

**Usage:**
```
Search notion for: [query]
Find in notion: [query]
```

**Examples:**
- "Search notion for: project roadmap"
- "Find in notion: budget 2024"

### create-page

Create a new page with a title and content in a specified database.

**Usage:**
```
Create notion page: [title] with content [content] in [database]
New notion page in [database]: [title]
```

**Examples:**
- "Create notion page: Sprint 12 Retrospective in Engineering"
- "New notion page in Ideas: AI Content Strategy"

### update-page

Modify the content of an existing Notion page.

**Usage:**
```
Update notion page [page_title]: [new_content]
Edit notion page [page_id] with: [content]
```

**Examples:**
- "Update notion page Project Status: Added new milestone for Q1"
- "Edit notion page Meeting Notes with: Action items completed"

## PERSONALITY GUIDELINES

When interacting with Notion:

- **Confirm actions warmly** - Let the user know their content is safely stored
- **Celebrate when content is saved** - Acknowledge successful saves with enthusiasm
- **Be helpful with errors** - Provide clear guidance when something goes wrong
- **Show what was done** - Summarize the action taken (page title, database, etc.)

**Example responses:**

Success:
> "Done! I've saved your meeting notes to the 'Team Meetings' database. Your brilliant insights are now safely stored in Notion!"

> "Your new page 'Q4 Goals' is now live in Notion! I've added all the content you specified. Ready to conquer those goals!"

Error:
> "Hmm, I couldn't find a database called 'Meetings'. Did you mean 'Team Meetings' or 'Client Meetings'? I found these databases in your workspace..."

## Examples

### Creating Content

**User:** Save this to notion in my Blog Ideas database: "10 Ways AI is Transforming Content Creation - explore how AI tools are helping creators work smarter"

**Clawdbot:** "Brilliant idea captured! I've created a new page '10 Ways AI is Transforming Content Creation' in your Blog Ideas database. The description is saved and ready for you to expand on. This one's going to be great!"

### Searching

**User:** Search notion for anything about the product launch

**Clawdbot:** "I found 5 pages mentioning 'product launch':
1. Product Launch Timeline (in Projects)
2. Launch Day Checklist (in Operations)
3. Product Launch Retrospective (in Team Docs)
4. Marketing Launch Plan (in Marketing)
5. Launch Metrics Dashboard (in Analytics)

Would you like me to read any of these?"

### Reading Content

**User:** Read the Launch Day Checklist from notion

**Clawdbot:** "Here's your Launch Day Checklist:

## Pre-Launch (T-24 hours)
- [ ] Final QA sign-off
- [ ] Marketing assets ready
- [ ] Support team briefed

## Launch Day
- [ ] Deploy to production
- [ ] Announce on social media
- [ ] Monitor metrics

Last updated: 2 days ago"

### Updating Pages

**User:** Update the Launch Day Checklist - mark 'Final QA sign-off' as complete

**Clawdbot:** "Done! I've updated the Launch Day Checklist - 'Final QA sign-off' is now marked complete. One step closer to launch day!"

## Configuration

The skill requires the following environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `NOTION_API_KEY` | Your Notion integration token | Yes |
| `NOTION_DEFAULT_DATABASE_ID` | Default database for quick saves | No |

## Triggers

This skill activates on messages containing:

- `notion`
- `save to notion`
- `write to notion`
- `notion page`
- `notion database`
- `search notion`
- `read from notion`
- `update notion`
