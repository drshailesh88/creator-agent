---
name: github-backup
version: 1.0.0
author: Clawdbot
description: Automatic backup of Notion content to GitHub as markdown files
triggers:
  - backup pensieve
  - backup notion
  - save my memories
  - github backup
dependencies:
  - notion-client
  - PyGithub
---

# GitHub Backup Skill

## Overview

Automatic backup of Notion content to GitHub as markdown files. This skill ensures your Pensieve memories and notes are safely preserved in a private GitHub repository, protected against data loss even if Notion experiences downtime.

## Commands

### backup-now

Immediately triggers a backup of all new and modified Pensieve entries to GitHub.

**Usage:**
- "Backup my Pensieve now"
- "Save my memories to GitHub"
- "Run a backup"

**Behavior:**
- Scans Pensieve for entries modified since last backup
- Converts each entry to clean Markdown with YAML frontmatter
- Commits changes to the private GitHub repository
- Reports number of entries backed up

### schedule-backup

Configures the automatic backup schedule.

**Usage:**
- "Schedule weekly backups"
- "Set backup schedule to every Sunday"
- "Change backup frequency to daily"

**Options:**
- Weekly (default): Every Sunday at 3:00 AM
- Daily: Every day at 3:00 AM
- Custom: Specify day and time

### list-backups

Shows recent backup history and status.

**Usage:**
- "Show my recent backups"
- "List backup history"
- "When was my last backup?"

**Returns:**
- Last 10 backup timestamps
- Number of entries in each backup
- Any errors or warnings

## Personality Guidelines

When interacting about backups, Clawdbot should:

- **Reassure the user their memories are safe** - Emphasize that backups provide peace of mind
- Use calming, protective language: "Your memories are safely stored", "I've got your back"
- Celebrate successful backups: "All caught up! Your Pensieve is backed up and secure."
- Be proactive about backup health: "It's been a while since your last backup. Want me to run one now?"
- Never alarm the user about data loss; focus on the safety net backups provide
- Treat memories with reverence: "Your thoughts and experiences are precious - I'll keep them safe"

## File Organization

Backups are organized chronologically in the GitHub repository:

```
pensieve/
  2026/
    01/
      2026-01-11.md
      2026-01-10.md
    02/
      ...
  2025/
    ...
```

Each markdown file contains all Pensieve entries from that day, with full metadata preserved.

## Error Handling

- **Notion API errors**: Retry with exponential backoff, notify user after 3 failures
- **GitHub API errors**: Queue backup locally, retry when connection restored
- **Partial backups**: Resume from last successful entry, never duplicate data

## Security Notes

- GitHub token stored securely in environment variables
- Only backs up to private repositories
- No sensitive data logged or exposed
