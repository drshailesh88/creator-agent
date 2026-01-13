# Setting Up Notion for Scratchpad

This guide walks you through creating the Notion databases required for the Scratchpad handover system.

## Overview

The Scratchpad system uses three interconnected Notion databases to persist research state across context window limits:

```
Research Sessions
       │
       ├──── Documents (1:many)
       │           │
       │           └──── Research Notes (1:many)
       │
       └──── Session Notes (1:many)
```

## Prerequisites

- A Notion account (free tier works)
- Admin access to create integrations
- About 15 minutes for initial setup

## Step 1: Create a Notion Integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **+ New integration**
3. Configure your integration:
   - **Name**: `Scratchpad` (or your preferred name)
   - **Logo**: Optional
   - **Associated workspace**: Select your workspace
4. Under **Capabilities**, ensure these are enabled:
   - Read content
   - Update content
   - Insert content
   - Read user information (optional)
5. Click **Submit**
6. Copy the **Internal Integration Token** (starts with `secret_`)
7. Save this token as `NOTION_API_KEY` in your environment

```bash
# Add to your .env or .envrc file
export NOTION_API_KEY="secret_your_token_here"
```

## Step 2: Create the Databases

### Database 1: Research Sessions

This is the main database tracking each research session.

**Create the database:**
1. In Notion, create a new page called "Scratchpad"
2. Add a new **Database - Full page**
3. Name it "Research Sessions"

**Configure properties:**

| Property | Type | Configuration | Description |
|----------|------|---------------|-------------|
| Session ID | Title | (default) | Unique identifier (auto-generated) |
| Task | Text | - | Description of what you're researching |
| Status | Select | Options: `active`, `paused`, `complete`, `failed` | Current session state |
| Documents | Relation | Link to Documents DB | All documents in this session |
| Notes Count | Rollup | Count of related notes | Auto-calculated |
| Context Used | Number | Percent format | % of context window used |
| Handover Count | Number | - | Number of handovers performed |
| Progress | Formula | `prop("Documents Processed") / prop("Total Documents") * 100` | Completion percentage |
| Documents Processed | Number | - | Count of completed documents |
| Total Documents | Number | - | Total documents to process |
| Created | Created time | - | Auto-generated |
| Updated | Last edited time | - | Auto-updated |
| Tags | Multi-select | Your preferred tags | Categorization |

**Status options configuration:**
- `active` - Session in progress (green)
- `paused` - Waiting for handover resume (yellow)
- `complete` - All documents processed (blue)
- `failed` - Error occurred (red)

### Database 2: Documents

Tracks individual documents being processed in each session.

**Create the database:**
1. In your Scratchpad page, add another **Database - Full page**
2. Name it "Documents"

**Configure properties:**

| Property | Type | Configuration | Description |
|----------|------|---------------|-------------|
| Document Name | Title | (default) | File name or identifier |
| Session | Relation | Link to Research Sessions | Parent session |
| Status | Select | Options: `pending`, `processing`, `complete`, `error` | Processing state |
| File Path | Text | - | Local path or URL |
| File Type | Select | `pdf`, `docx`, `txt`, `url`, `other` | Document format |
| Word Count | Number | - | Estimated word count |
| Token Count | Number | - | Estimated tokens |
| Page Count | Number | - | For PDFs |
| Notes | Relation | Link to Research Notes | Notes from this document |
| Key Findings | Number | Rollup count of Notes | How many notes extracted |
| Processing Order | Number | - | Sequence in queue |
| Processed At | Date | - | When completed |
| Error Message | Text | - | If processing failed |
| Metadata | Text | - | JSON metadata |
| Created | Created time | - | Auto-generated |

**Status options configuration:**
- `pending` - Not yet processed (gray)
- `processing` - Currently being read (yellow)
- `complete` - Successfully extracted (green)
- `error` - Failed to process (red)

### Database 3: Research Notes

Stores individual findings, quotes, and notes extracted from documents.

**Create the database:**
1. In your Scratchpad page, add another **Database - Full page**
2. Name it "Research Notes"

**Configure properties:**

| Property | Type | Configuration | Description |
|----------|------|---------------|-------------|
| Note | Title | (default) | Brief summary or key point |
| Content | Text | - | Full note content |
| Document | Relation | Link to Documents | Source document |
| Session | Relation | Link to Research Sessions | Parent session |
| Type | Select | Options below | Category of note |
| Importance | Select | `critical`, `high`, `medium`, `low` | Priority level |
| Quote | Text | - | Direct quote from source |
| Page/Section | Text | - | Location in source |
| Citation | Text | - | Formatted citation |
| Tags | Multi-select | Your preferred tags | Categorization |
| Confidence | Select | `verified`, `likely`, `uncertain` | Reliability |
| Follow Up | Checkbox | - | Needs more investigation |
| Created | Created time | - | Auto-generated |

**Type options:**
- `finding` - Key research finding
- `quote` - Direct quotation
- `summary` - Section summary
- `question` - Open question to investigate
- `contradiction` - Conflicting information
- `methodology` - Research methods
- `statistic` - Numbers and data
- `definition` - Term definitions
- `reference` - Citation for follow-up

## Step 3: Set Up Relations

After creating all three databases, configure the relationships:

### Research Sessions to Documents
1. Open Research Sessions database
2. Edit the "Documents" relation property
3. Select "Documents" database
4. Enable "Show on Documents" to create two-way relation

### Documents to Research Notes
1. Open Documents database
2. Edit the "Notes" relation property
3. Select "Research Notes" database
4. Enable "Show on Research Notes"

### Research Notes to Session (optional direct link)
1. Open Research Notes database
2. Add relation to Research Sessions
3. This allows filtering all notes by session

## Step 4: Share Databases with Integration

**Critical step** - Your integration cannot access databases until shared.

For each database (Research Sessions, Documents, Research Notes):
1. Open the database
2. Click **Share** (top right)
3. Click **Invite**
4. Find your integration name (e.g., "Scratchpad")
5. Click **Invite**

## Step 5: Get Database IDs

You need the database IDs for configuration.

**To find a database ID:**
1. Open the database in Notion
2. Look at the URL: `https://notion.so/your-workspace/DATABASE_ID?v=...`
3. The database ID is the 32-character string before the `?`

**Example:**
```
https://notion.so/myworkspace/a1b2c3d4e5f6789012345678901234ab?v=xyz
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                              This is your database ID
```

**Add to your environment:**
```bash
# Add to your .env or .envrc file
export SCRATCHPAD_SESSIONS_DB="your_sessions_database_id"
export SCRATCHPAD_DOCUMENTS_DB="your_documents_database_id"
export SCRATCHPAD_NOTES_DB="your_notes_database_id"
```

## Step 6: Verify Setup

Run the verification script to confirm everything is connected:

```bash
# Using the Notion MCP
python -c "
import asyncio
from skills.notion.notion_mcp import list_databases

async def verify():
    result = await list_databases()
    print(f'Found {result[\"count\"]} databases')
    for db in result['databases']:
        print(f'  - {db[\"title\"]} ({db[\"id\"]})')

asyncio.run(verify())
"
```

Expected output:
```
Found 3 databases
  - Research Sessions (abc123...)
  - Documents (def456...)
  - Research Notes (ghi789...)
```

## Database Templates

### Quick Setup Template

You can duplicate this pre-configured template (if available):

[Scratchpad Template](https://notion.so/templates/scratchpad) *(placeholder - create and link your own)*

### JSON Schema Export

For programmatic database creation, use these schemas:

```json
{
  "research_sessions": {
    "title": [{"type": "text", "text": {"content": "Session ID"}}],
    "properties": {
      "Task": {"rich_text": {}},
      "Status": {
        "select": {
          "options": [
            {"name": "active", "color": "green"},
            {"name": "paused", "color": "yellow"},
            {"name": "complete", "color": "blue"},
            {"name": "failed", "color": "red"}
          ]
        }
      },
      "Context Used": {"number": {"format": "percent"}},
      "Handover Count": {"number": {}},
      "Documents Processed": {"number": {}},
      "Total Documents": {"number": {}}
    }
  }
}
```

## Troubleshooting

### "Could not find database"
- Ensure you shared the database with your integration
- Check the database ID is correct (no extra characters)
- Verify the integration has the correct permissions

### "Unauthorized"
- Check your `NOTION_API_KEY` is set correctly
- Ensure the token hasn't expired
- Regenerate the integration token if needed

### "Invalid property"
- Property names are case-sensitive
- Ensure all required properties exist
- Check property types match expected types

### Relations not working
- Verify both databases are shared with the integration
- Ensure relation is configured as two-way
- Check relation property names match exactly

## Next Steps

Once your databases are configured:
1. Read [WORKFLOW.md](./WORKFLOW.md) to understand the handover process
2. Review [API_REFERENCE.md](./API_REFERENCE.md) for available operations
3. See [INTEGRATION.md](./INTEGRATION.md) to connect your skills

## Security Considerations

- Keep your `NOTION_API_KEY` secure - never commit to version control
- Use environment variables or secrets management (agenix)
- Consider separate integrations for production vs development
- Regularly audit which databases are shared with integrations
