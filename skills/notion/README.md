# Notion Integration Skill for Clawdbot

This skill enables Clawdbot to interact with Notion workspaces through the official Notion API.

## Features

- **Create Pages**: Add new pages to any Notion database
- **Read Pages**: Retrieve and display page content
- **Search**: Find pages and databases across your workspace
- **Update Pages**: Modify existing page content
- **Append Content**: Add content to existing pages without replacing
- **List Databases**: Discover all accessible databases

## Setup

### 1. Create a Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click **"+ New integration"**
3. Fill in the details:
   - **Name**: "Clawdbot" (or your preferred name)
   - **Associated workspace**: Select your workspace
   - **Type**: Internal integration
4. Click **"Submit"**
5. Copy the **Internal Integration Token** (starts with `secret_`)

### 2. Share Databases with Your Integration

For Clawdbot to access your Notion content, you must explicitly share each database:

1. Open the database page in Notion
2. Click the **"..."** menu in the top-right corner
3. Scroll down and click **"+ Add connections"**
4. Search for and select your integration ("Clawdbot")
5. Click **"Confirm"**

> **Important**: The integration can only access pages and databases that have been explicitly shared with it. This is a security feature of the Notion API.

### 3. Configure Environment Variables

Add the following to your environment or `.env` file:

```bash
# Required: Your Notion integration token
NOTION_API_KEY=secret_your_integration_token_here

# Optional: Default database for quick saves
NOTION_DEFAULT_DATABASE_ID=your_default_database_id_here
```

### 4. Install Dependencies

The MCP server requires Python 3.10+ and the following packages:

```bash
pip install mcp httpx
```

Or using a requirements file:

```bash
# Create requirements.txt
echo "mcp>=0.9.0" > requirements.txt
echo "httpx>=0.25.0" >> requirements.txt

# Install
pip install -r requirements.txt
```

### 5. Register the Skill

Add the skill to your Clawdbot configuration. The `mcporter.json` file in this directory contains the MCP server configuration.

## Finding Database and Page IDs

### Database ID

1. Open the database in Notion
2. Look at the URL: `https://notion.so/workspace/[DATABASE_ID]?v=...`
3. The database ID is the 32-character string before the `?`

Example URL:
```
https://notion.so/myworkspace/a1b2c3d4e5f6789012345678901234567?v=...
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                              This is the database ID
```

### Page ID

1. Open the page in Notion
2. Look at the URL: `https://notion.so/workspace/Page-Title-[PAGE_ID]`
3. The page ID is the 32-character string at the end

Example URL:
```
https://notion.so/myworkspace/My-Page-Title-a1b2c3d4e5f6789012345678901234567
                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                            This is the page ID
```

## Usage Examples

### Creating a Page

```
User: Save this to my Blog Ideas database: "10 Tips for Productivity - a guide to getting more done"

Clawdbot: Done! I've created a new page "10 Tips for Productivity" in your Blog Ideas database.
```

### Searching

```
User: Search notion for anything about project planning

Clawdbot: I found 3 pages:
1. Q4 Project Planning (in Projects)
2. Planning Template (in Templates)
3. Project Planning Guide (in Resources)
```

### Reading a Page

```
User: Read the Q4 Project Planning page

Clawdbot: Here's the content from "Q4 Project Planning":

# Goals
- Launch new feature by October
- Complete security audit
...
```

### Updating a Page

```
User: Update the Q4 Project Planning page with: "Update: Security audit completed on Jan 5"

Clawdbot: Done! I've updated "Q4 Project Planning" with your new content.
```

## API Reference

### Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_page` | Create a new page in a database | `database_id`, `title`, `content?`, `properties?` |
| `update_page` | Replace page content | `page_id`, `content` |
| `append_to_page` | Add content to a page | `page_id`, `content` |
| `get_page` | Retrieve page content | `page_id` |
| `search_pages` | Search for pages | `query`, `database_id?` |
| `list_databases` | List accessible databases | none |

### Supported Content Formats

The MCP server supports basic markdown-style formatting:

- `# Heading 1`, `## Heading 2`, `### Heading 3`
- Regular paragraphs
- Multiple paragraphs (separated by blank lines)

## Troubleshooting

### "I don't have permission to access that resource"

**Cause**: The database or page hasn't been shared with the integration.

**Solution**: Share the database/page with your integration (see Step 2 above).

### "I couldn't authenticate with Notion"

**Cause**: The API key is invalid, expired, or not set.

**Solution**:
1. Verify `NOTION_API_KEY` is set correctly
2. Check the key hasn't been revoked in Notion settings
3. Generate a new key if needed

### "I couldn't find that page or database"

**Cause**: The page was deleted, or the ID is incorrect.

**Solution**:
1. Verify the page/database still exists in Notion
2. Double-check the ID from the URL
3. Ensure the integration has access

### "Request timed out"

**Cause**: Network issues or Notion API slowness.

**Solution**: Wait a moment and try again. Check your internet connection.

## Security Considerations

1. **API Key Protection**: Never commit your `NOTION_API_KEY` to version control
2. **Minimal Permissions**: Only share databases that Clawdbot needs to access
3. **Audit Access**: Regularly review which pages/databases are shared with the integration
4. **Key Rotation**: Rotate your API key periodically via Notion settings

## Rate Limits

The Notion API has rate limits:
- **3 requests per second** for most endpoints
- The MCP server handles rate limit errors gracefully

## License

MIT
