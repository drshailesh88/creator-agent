# Pensieve - Memory Palace for Clawdbot

A warm, thoughtful skill for storing and retrieving personal memories, thoughts, and reflections via Notion.

## Overview

Pensieve is an MCP (Model Context Protocol) server that allows Clawdbot to:
- Save memories with automatic tagging and mood tracking
- Search through past thoughts using natural language
- Retrieve recent memories for reflection
- Generate daily reflection prompts

## Installation

### Prerequisites

1. **Python 3.10+** with the following packages:
   ```bash
   pip install mcp httpx
   ```

2. **Notion Integration** - Create a Notion integration:
   - Go to [Notion Integrations](https://www.notion.so/my-integrations)
   - Click "New integration"
   - Name it "Pensieve Memory Palace"
   - Select your workspace
   - Copy the "Internal Integration Token"

3. **Notion Database** - Create a database for memories:
   - Create a new page in Notion
   - Add a database with the following properties:
     - `Content` (Text) - The memory content
     - `Timestamp` (Date) - When captured
     - `Tags` (Multi-select) - Categories
     - `Mood` (Select) - Emotional tone
       - Options: happy, contemplative, grateful, curious, inspired, peaceful, bittersweet, determined, hopeful, reflective
     - `Source` (Select) - Origin
       - Options: chat, reflection, journal, voice, import
   - Share the database with your integration (click "..." > "Connections" > add your integration)
   - Copy the database ID from the URL (it's the 32-character string after your workspace name)

### Environment Variables

Set these environment variables:

```bash
export NOTION_API_KEY="your-notion-integration-token"
export PENSIEVE_DATABASE_ID="your-notion-database-id"
```

Or add them to your `.env` file:

```env
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PENSIEVE_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Running the Server

#### Standalone
```bash
python pensieve.py
```

#### With Claude Code / MCP
Add to your MCP configuration:

```json
{
  "mcpServers": {
    "pensieve": {
      "command": "python",
      "args": ["/path/to/skills/pensieve/pensieve.py"],
      "env": {
        "NOTION_API_KEY": "${NOTION_API_KEY}",
        "PENSIEVE_DATABASE_ID": "${PENSIEVE_DATABASE_ID}"
      }
    }
  }
}
```

## Usage

### Saving Memories

```
User: I just realized that taking morning walks completely changes my day

Clawdbot: What a lovely insight! I've saved this to your Pensieve, tagged with
#wellness and #growth. These moments of self-discovery are precious.
```

### Searching Memories

```
User: What have I been thinking about work lately?

Clawdbot: Looking through your recent reflections about work, I found...
[displays relevant memories with dates and moods]
```

### Daily Reflection

```
User: Help me reflect on today

Clawdbot: Here's a gentle prompt for your reflection:

*What moment today surprised you - either a challenge you handled better
than expected, or a simple joy you almost missed?*

Take your time. When you're ready, I'll keep your thoughts safe.
```

## Tools

| Tool | Description |
|------|-------------|
| `save_memory` | Store a new memory with optional tags and mood |
| `search_memories` | Find memories by query, tags, mood, or date range |
| `get_recent_memories` | Retrieve memories from the last N days |
| `daily_reflection_prompt` | Generate a thoughtful reflection prompt |

## Personality Integration

Pensieve is designed to maintain Clawdbot's warm, caring personality. When handling memories:

- Acknowledge the significance of what's being shared
- Use gentle, supportive language
- Present recalled memories thoughtfully, not as cold data
- Celebrate insights and growth patterns
- Respect the vulnerability in personal reflections

## File Structure

```
skills/pensieve/
├── SKILL.md          # Skill definition and documentation
├── mcporter.json     # MCP server configuration
├── pensieve.py       # Python MCP server implementation
└── README.md         # This file
```

## Troubleshooting

### "I need a Notion API key"
Ensure `NOTION_API_KEY` is set in your environment.

### "I need to know which database to use"
Ensure `PENSIEVE_DATABASE_ID` or `NOTION_DATABASE_ID` is set.

### "Permission denied" from Notion
Make sure your Notion integration has been shared with the database:
1. Open your Pensieve database in Notion
2. Click "..." in the top right
3. Click "Connections"
4. Add your "Pensieve Memory Palace" integration

### Database property errors
Ensure your Notion database has all required properties with the correct types as listed in the Installation section.

## Privacy

Your memories are stored in your personal Notion workspace. The Pensieve server only accesses what you've explicitly shared with the integration. Treat your Notion API key as a secret - never commit it to version control.

## License

Part of the Clawdbot Life OS project.
