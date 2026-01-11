#!/usr/bin/env python3
"""
Notion MCP Server for Clawdbot

This MCP server provides tools for interacting with Notion's API,
allowing Clawdbot to read, write, search, and manage Notion content.
"""

import json
import os
import sys
from typing import Any, Optional
import asyncio
import httpx

# MCP Protocol imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Error: MCP SDK not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)


# Configuration
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DEFAULT_DATABASE_ID = os.environ.get("NOTION_DEFAULT_DATABASE_ID")
NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

# Initialize MCP server
server = Server("notion")


class NotionAPIError(Exception):
    """Custom exception for Notion API errors."""
    def __init__(self, message: str, status_code: int = None, details: str = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


def get_friendly_error(error: NotionAPIError) -> str:
    """Convert API errors to user-friendly messages."""
    if error.status_code == 401:
        return "I couldn't authenticate with Notion. Please check that your API key is valid and hasn't expired."
    elif error.status_code == 403:
        return "I don't have permission to access that resource. Make sure the integration has been shared with the page or database you're trying to access."
    elif error.status_code == 404:
        return "I couldn't find that page or database in Notion. It may have been deleted, or the integration might not have access to it."
    elif error.status_code == 429:
        return "Notion is asking me to slow down. Let's wait a moment and try again."
    elif error.status_code and error.status_code >= 500:
        return "Notion seems to be having some issues right now. Let's try again in a moment."
    else:
        return f"Something went wrong with Notion: {error.message}"


def get_headers() -> dict:
    """Get headers for Notion API requests."""
    if not NOTION_API_KEY:
        raise NotionAPIError("NOTION_API_KEY environment variable is not set", status_code=401)

    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }


async def make_request(
    method: str,
    endpoint: str,
    data: Optional[dict] = None,
    params: Optional[dict] = None
) -> dict:
    """Make an authenticated request to the Notion API."""
    url = f"{NOTION_BASE_URL}/{endpoint}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=get_headers(),
                json=data,
                params=params,
                timeout=30.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                error_body = response.json() if response.text else {}
                error_message = error_body.get("message", "Unknown error")
                raise NotionAPIError(
                    message=error_message,
                    status_code=response.status_code,
                    details=json.dumps(error_body)
                )

        except httpx.TimeoutException:
            raise NotionAPIError("Request to Notion timed out. Please try again.")
        except httpx.RequestError as e:
            raise NotionAPIError(f"Network error connecting to Notion: {str(e)}")


def parse_rich_text(rich_text_array: list) -> str:
    """Extract plain text from Notion rich text array."""
    return "".join(item.get("plain_text", "") for item in rich_text_array)


def create_rich_text(text: str) -> list:
    """Create Notion rich text array from plain text."""
    return [{"type": "text", "text": {"content": text}}]


def create_paragraph_block(text: str) -> dict:
    """Create a paragraph block for Notion."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": create_rich_text(text)
        }
    }


def create_heading_block(text: str, level: int = 1) -> dict:
    """Create a heading block for Notion."""
    heading_type = f"heading_{min(max(level, 1), 3)}"
    return {
        "object": "block",
        "type": heading_type,
        heading_type: {
            "rich_text": create_rich_text(text)
        }
    }


def parse_content_to_blocks(content: str) -> list:
    """Parse text content into Notion blocks."""
    blocks = []
    lines = content.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Handle markdown-style headings
        if line.startswith("### "):
            blocks.append(create_heading_block(line[4:], 3))
        elif line.startswith("## "):
            blocks.append(create_heading_block(line[3:], 2))
        elif line.startswith("# "):
            blocks.append(create_heading_block(line[2:], 1))
        else:
            blocks.append(create_paragraph_block(line))

    return blocks


def extract_page_content(blocks: list) -> str:
    """Extract readable content from Notion blocks."""
    content_parts = []

    for block in blocks:
        block_type = block.get("type", "")

        if block_type == "paragraph":
            text = parse_rich_text(block.get("paragraph", {}).get("rich_text", []))
            if text:
                content_parts.append(text)

        elif block_type.startswith("heading_"):
            level = int(block_type[-1])
            text = parse_rich_text(block.get(block_type, {}).get("rich_text", []))
            if text:
                prefix = "#" * level
                content_parts.append(f"{prefix} {text}")

        elif block_type == "bulleted_list_item":
            text = parse_rich_text(block.get("bulleted_list_item", {}).get("rich_text", []))
            if text:
                content_parts.append(f"- {text}")

        elif block_type == "numbered_list_item":
            text = parse_rich_text(block.get("numbered_list_item", {}).get("rich_text", []))
            if text:
                content_parts.append(f"1. {text}")

        elif block_type == "to_do":
            checked = block.get("to_do", {}).get("checked", False)
            text = parse_rich_text(block.get("to_do", {}).get("rich_text", []))
            if text:
                checkbox = "[x]" if checked else "[ ]"
                content_parts.append(f"- {checkbox} {text}")

        elif block_type == "code":
            text = parse_rich_text(block.get("code", {}).get("rich_text", []))
            language = block.get("code", {}).get("language", "")
            if text:
                content_parts.append(f"```{language}\n{text}\n```")

        elif block_type == "quote":
            text = parse_rich_text(block.get("quote", {}).get("rich_text", []))
            if text:
                content_parts.append(f"> {text}")

        elif block_type == "divider":
            content_parts.append("---")

    return "\n\n".join(content_parts)


# Tool implementations

async def create_page(
    database_id: str,
    title: str,
    content: str = "",
    properties: Optional[dict] = None
) -> dict:
    """
    Create a new page in a Notion database.

    Args:
        database_id: The ID of the database to create the page in
        title: The title of the new page
        content: The content to add to the page body
        properties: Additional properties to set on the page

    Returns:
        dict with page_id and url of the created page
    """
    # Build page properties with title
    page_properties = {
        "title": {
            "title": create_rich_text(title)
        }
    }

    # Merge additional properties if provided
    if properties:
        page_properties.update(properties)

    # Build request data
    request_data = {
        "parent": {"database_id": database_id},
        "properties": page_properties,
    }

    # Add content as children blocks if provided
    if content:
        request_data["children"] = parse_content_to_blocks(content)

    result = await make_request("POST", "pages", data=request_data)

    return {
        "success": True,
        "page_id": result.get("id"),
        "url": result.get("url"),
        "title": title,
        "message": f"Successfully created page '{title}' in the database!"
    }


async def update_page(page_id: str, content: str) -> dict:
    """
    Update an existing Notion page by appending new content.

    Args:
        page_id: The ID of the page to update
        content: The content to append to the page

    Returns:
        dict with success status and message
    """
    # First, get current page to verify it exists and get title
    page_info = await make_request("GET", f"pages/{page_id}")

    # Get the page title for the response message
    title_prop = page_info.get("properties", {}).get("title", {})
    title_array = title_prop.get("title", [])
    page_title = parse_rich_text(title_array) if title_array else "Untitled"

    # Clear existing content and add new content
    blocks = parse_content_to_blocks(content)

    # Append blocks to the page
    await make_request(
        "PATCH",
        f"blocks/{page_id}/children",
        data={"children": blocks}
    )

    return {
        "success": True,
        "page_id": page_id,
        "title": page_title,
        "message": f"Successfully updated page '{page_title}'!"
    }


async def search_pages(query: str, database_id: Optional[str] = None) -> dict:
    """
    Search for pages in Notion.

    Args:
        query: The search query
        database_id: Optional database ID to limit search scope

    Returns:
        dict with list of matching pages
    """
    request_data = {
        "query": query,
        "sort": {
            "direction": "descending",
            "timestamp": "last_edited_time"
        },
        "page_size": 20
    }

    # If database_id is provided, filter to that database
    if database_id:
        request_data["filter"] = {
            "property": "object",
            "value": "page"
        }

    result = await make_request("POST", "search", data=request_data)

    pages = []
    for item in result.get("results", []):
        if item.get("object") == "page":
            # Extract title
            properties = item.get("properties", {})
            title = "Untitled"

            for prop_name, prop_value in properties.items():
                if prop_value.get("type") == "title":
                    title_array = prop_value.get("title", [])
                    title = parse_rich_text(title_array) if title_array else "Untitled"
                    break

            # Get parent info
            parent = item.get("parent", {})
            parent_type = parent.get("type", "unknown")

            pages.append({
                "id": item.get("id"),
                "title": title,
                "url": item.get("url"),
                "last_edited": item.get("last_edited_time"),
                "parent_type": parent_type,
            })

    return {
        "success": True,
        "query": query,
        "count": len(pages),
        "pages": pages,
        "message": f"Found {len(pages)} pages matching '{query}'"
    }


async def get_page(page_id: str) -> dict:
    """
    Get the content of a Notion page.

    Args:
        page_id: The ID of the page to retrieve

    Returns:
        dict with page title, content, and metadata
    """
    # Get page metadata
    page_info = await make_request("GET", f"pages/{page_id}")

    # Get page title
    properties = page_info.get("properties", {})
    title = "Untitled"

    for prop_name, prop_value in properties.items():
        if prop_value.get("type") == "title":
            title_array = prop_value.get("title", [])
            title = parse_rich_text(title_array) if title_array else "Untitled"
            break

    # Get page content (blocks)
    blocks_result = await make_request("GET", f"blocks/{page_id}/children")
    blocks = blocks_result.get("results", [])

    content = extract_page_content(blocks)

    return {
        "success": True,
        "page_id": page_id,
        "title": title,
        "content": content,
        "url": page_info.get("url"),
        "created_time": page_info.get("created_time"),
        "last_edited_time": page_info.get("last_edited_time"),
        "message": f"Retrieved page '{title}'"
    }


async def append_to_page(page_id: str, content: str) -> dict:
    """
    Append content to an existing Notion page without replacing existing content.

    Args:
        page_id: The ID of the page to append to
        content: The content to append

    Returns:
        dict with success status and message
    """
    # Get page info for the response
    page_info = await make_request("GET", f"pages/{page_id}")

    # Get the page title
    properties = page_info.get("properties", {})
    title = "Untitled"

    for prop_name, prop_value in properties.items():
        if prop_value.get("type") == "title":
            title_array = prop_value.get("title", [])
            title = parse_rich_text(title_array) if title_array else "Untitled"
            break

    # Convert content to blocks
    blocks = parse_content_to_blocks(content)

    # Append blocks to the page
    await make_request(
        "PATCH",
        f"blocks/{page_id}/children",
        data={"children": blocks}
    )

    return {
        "success": True,
        "page_id": page_id,
        "title": title,
        "message": f"Successfully appended content to '{title}'!"
    }


async def list_databases() -> dict:
    """
    List all databases accessible to the integration.

    Returns:
        dict with list of databases
    """
    request_data = {
        "filter": {
            "property": "object",
            "value": "database"
        },
        "page_size": 100
    }

    result = await make_request("POST", "search", data=request_data)

    databases = []
    for item in result.get("results", []):
        if item.get("object") == "database":
            # Extract title
            title_array = item.get("title", [])
            title = parse_rich_text(title_array) if title_array else "Untitled Database"

            databases.append({
                "id": item.get("id"),
                "title": title,
                "url": item.get("url"),
                "created_time": item.get("created_time"),
            })

    return {
        "success": True,
        "count": len(databases),
        "databases": databases,
        "message": f"Found {len(databases)} accessible databases"
    }


# MCP Tool definitions

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Notion tools."""
    return [
        Tool(
            name="create_page",
            description="Create a new page in a Notion database with a title and optional content",
            inputSchema={
                "type": "object",
                "properties": {
                    "database_id": {
                        "type": "string",
                        "description": "The ID of the Notion database to create the page in"
                    },
                    "title": {
                        "type": "string",
                        "description": "The title for the new page"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to add to the page body (supports markdown headings)"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Additional Notion properties to set on the page"
                    }
                },
                "required": ["database_id", "title"]
            }
        ),
        Tool(
            name="update_page",
            description="Update an existing Notion page with new content (replaces existing content)",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "The ID of the Notion page to update"
                    },
                    "content": {
                        "type": "string",
                        "description": "The new content for the page"
                    }
                },
                "required": ["page_id", "content"]
            }
        ),
        Tool(
            name="search_pages",
            description="Search for pages in Notion matching a query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "database_id": {
                        "type": "string",
                        "description": "Optional: Limit search to a specific database"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_page",
            description="Get the full content of a Notion page",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "The ID of the Notion page to retrieve"
                    }
                },
                "required": ["page_id"]
            }
        ),
        Tool(
            name="append_to_page",
            description="Append content to an existing Notion page without replacing existing content",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "The ID of the Notion page to append to"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to append to the page"
                    }
                },
                "required": ["page_id", "content"]
            }
        ),
        Tool(
            name="list_databases",
            description="List all Notion databases accessible to the integration",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "create_page":
            result = await create_page(
                database_id=arguments["database_id"],
                title=arguments["title"],
                content=arguments.get("content", ""),
                properties=arguments.get("properties")
            )
        elif name == "update_page":
            result = await update_page(
                page_id=arguments["page_id"],
                content=arguments["content"]
            )
        elif name == "search_pages":
            result = await search_pages(
                query=arguments["query"],
                database_id=arguments.get("database_id")
            )
        elif name == "get_page":
            result = await get_page(page_id=arguments["page_id"])
        elif name == "append_to_page":
            result = await append_to_page(
                page_id=arguments["page_id"],
                content=arguments["content"]
            )
        elif name == "list_databases":
            result = await list_databases()
        else:
            result = {"success": False, "error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except NotionAPIError as e:
        error_response = {
            "success": False,
            "error": get_friendly_error(e),
            "details": e.details if e.details else None
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    except Exception as e:
        error_response = {
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


async def main():
    """Run the MCP server."""
    if not NOTION_API_KEY:
        print("Warning: NOTION_API_KEY environment variable is not set", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
