# GitHub Backup Skill for Clawdbot

Automatically backup your Notion Pensieve database to a private GitHub repository. Your memories are converted to clean Markdown files with full metadata preserved, ensuring you never lose your precious thoughts even if Notion experiences downtime.

## Features

- **Automatic Backups**: Weekly scheduled backups (configurable to daily, hourly, or custom)
- **Incremental Updates**: Only backs up new and modified entries, saving time and API calls
- **Clean Markdown**: Notion pages converted to standard Markdown with YAML frontmatter
- **Organized Structure**: Files organized by date for easy navigation
- **Full Metadata**: All Notion properties preserved in frontmatter
- **Resilient**: Handles errors gracefully, never loses existing backups

## Prerequisites

- Python 3.8+
- A Notion integration with access to your Pensieve database
- A GitHub account with a private repository for backups
- A GitHub personal access token with repo permissions

## Setup

### 1. Create a Private GitHub Repository

1. Go to [GitHub](https://github.com/new)
2. Create a new repository:
   - Name: `pensieve-backup` (or your preference)
   - Visibility: **Private** (important for protecting your memories)
   - Initialize with a README (optional)
3. Note the repository name in format `username/repo-name`

### 2. Generate a GitHub Personal Access Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Give it a descriptive name: `Pensieve Backup`
4. Set expiration as needed (or "No expiration" for uninterrupted backups)
5. Select scopes:
   - `repo` (Full control of private repositories)
6. Click "Generate token"
7. **Copy the token immediately** - you won't be able to see it again

### 3. Create a Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Name it `Pensieve Backup`
4. Select your workspace
5. Click "Submit"
6. Copy the "Internal Integration Token"

### 4. Connect Notion Integration to Pensieve

1. Open your Pensieve database in Notion
2. Click the "..." menu in the top right
3. Select "Add connections"
4. Find and select your "Pensieve Backup" integration

### 5. Get Your Pensieve Database ID

1. Open your Pensieve database in Notion
2. Look at the URL: `https://notion.so/workspace/DATABASE_ID?v=...`
3. Copy the `DATABASE_ID` portion (32 characters, no hyphens in URL)

### 6. Configure Environment Variables

Add the following to your environment (e.g., `~/.bashrc`, `~/.zshrc`, or a `.env` file):

```bash
export NOTION_TOKEN="secret_your_notion_integration_token"
export GITHUB_TOKEN="ghp_your_github_personal_access_token"
export GITHUB_BACKUP_REPO="yourusername/pensieve-backup"
export PENSIEVE_DATABASE_ID="your_database_id_here"
```

Reload your shell or source the file:
```bash
source ~/.bashrc
```

### 7. Install Dependencies

```bash
pip install notion-client PyGithub apscheduler
```

## Usage

### Manual Backup

Run an immediate backup:

```bash
python backup.py
```

Run a full backup (re-backup all entries):

```bash
python backup.py --full
```

Check backup status:

```bash
python backup.py --status
```

List recent backups:

```bash
python backup.py --list
```

### Scheduled Backups

Start the scheduler daemon:

```bash
python scheduler.py start
```

View scheduler status:

```bash
python scheduler.py status
```

Change schedule:

```bash
# Weekly backups (default)
python scheduler.py schedule weekly

# Daily backups
python scheduler.py schedule daily

# Custom cron schedule (every day at noon)
python scheduler.py schedule custom --cron "0 12 * * *"
```

View backup history:

```bash
python scheduler.py history --limit 20
```

### Clawdbot Commands

Once installed, you can ask Clawdbot:

- "Backup my Pensieve now"
- "When was my last backup?"
- "Schedule daily backups"
- "Show my backup history"
- "Are my memories safe?"

## Backup Structure

Backups are organized chronologically in your GitHub repository:

```
pensieve/
├── 2026/
│   ├── 01/
│   │   ├── 2026-01-01.md
│   │   ├── 2026-01-05.md
│   │   └── 2026-01-11.md
│   └── 02/
│       └── ...
└── 2025/
    └── ...
```

### Markdown Format

Each backed-up entry includes YAML frontmatter with all Notion properties:

```markdown
---
title: "Morning Reflection"
id: "abc123..."
created_time: "2026-01-11T08:30:00.000Z"
last_edited_time: "2026-01-11T09:15:00.000Z"
url: "https://notion.so/..."
Tags:
  - "reflection"
  - "morning"
Mood: "contemplative"
---

# Morning Reflection

Today I woke up thinking about...
```

## Running as a System Service

### Linux (systemd)

Create `/etc/systemd/system/pensieve-backup.service`:

```ini
[Unit]
Description=Pensieve Backup Scheduler
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/skills/github-backup
Environment="NOTION_TOKEN=secret_..."
Environment="GITHUB_TOKEN=ghp_..."
Environment="GITHUB_BACKUP_REPO=user/repo"
Environment="PENSIEVE_DATABASE_ID=..."
ExecStart=/usr/bin/python3 scheduler.py start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable pensieve-backup
sudo systemctl start pensieve-backup
```

### macOS (launchd)

Create `~/Library/LaunchAgents/com.clawdbot.pensieve-backup.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.clawdbot.pensieve-backup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/skills/github-backup/scheduler.py</string>
        <string>start</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>NOTION_TOKEN</key>
        <string>secret_...</string>
        <key>GITHUB_TOKEN</key>
        <string>ghp_...</string>
        <key>GITHUB_BACKUP_REPO</key>
        <string>user/repo</string>
        <key>PENSIEVE_DATABASE_ID</key>
        <string>...</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.clawdbot.pensieve-backup.plist
```

## Troubleshooting

### "Missing required configuration" error

Ensure all environment variables are set:
```bash
echo $NOTION_TOKEN
echo $GITHUB_TOKEN
echo $GITHUB_BACKUP_REPO
echo $PENSIEVE_DATABASE_ID
```

### "Could not find database" error

1. Verify your database ID is correct
2. Ensure the Notion integration is connected to your Pensieve database
3. Check the integration has permission to access the database

### "Bad credentials" GitHub error

1. Verify your GitHub token is correct
2. Check the token hasn't expired
3. Ensure the token has `repo` scope

### Backups not running on schedule

1. Check scheduler status: `python scheduler.py status`
2. Verify the scheduler daemon is running
3. Check system logs for errors

## Security Notes

- **Keep your tokens secret**: Never commit tokens to version control
- **Use a private repository**: Your Pensieve contains personal memories
- **Rotate tokens periodically**: Update your GitHub token regularly
- **Review access**: Periodically audit what has access to your Notion and GitHub

## Support

If you encounter issues or have questions, ask Clawdbot:
- "Help me set up Pensieve backup"
- "Why did my backup fail?"
- "Check my backup configuration"

---

*Your memories are precious. This skill helps ensure they're always safe.*
