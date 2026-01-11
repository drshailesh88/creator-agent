#!/usr/bin/env python3
"""
Pensieve - A Memory Palace MCP Server

Store and retrieve personal thoughts, memories, and reflections via Notion.
Treats every memory with warmth and care - these are precious thoughts.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

# Initialize MCP server
server = Server("pensieve")

# Notion configuration
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID") or os.environ.get("PENSIEVE_DATABASE_ID")
NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

# Mood emoji mapping for warm responses
MOOD_EMOJIS = {
    "happy": "sunshine",
    "contemplative": "thoughtful",
    "grateful": "thankful",
    "curious": "wondering",
    "inspired": "inspired",
    "peaceful": "serene",
    "bittersweet": "tender",
    "determined": "focused",
    "hopeful": "optimistic",
    "reflective": "introspective",
}

# Auto-tag keywords
AUTO_TAG_KEYWORDS = {
    "work": ["project", "meeting", "deadline", "colleague", "office", "job"],
    "personal": ["family", "friend", "home", "weekend", "hobby"],
    "growth": ["learned", "realized", "insight", "discovery", "understand"],
    "gratitude": ["grateful", "thankful", "appreciate", "blessed", "lucky"],
    "creativity": ["idea", "create", "imagine", "design", "art", "write"],
    "wellness": ["health", "exercise", "sleep", "meditation", "rest"],
    "goals": ["goal", "plan", "dream", "future", "aspire", "achieve"],
}


def get_notion_headers() -> dict:
    """Get headers for Notion API requests."""
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }


def auto_generate_tags(content: str) -> list[str]:
    """Automatically generate tags based on content keywords."""
    content_lower = content.lower()
    tags = []

    for tag, keywords in AUTO_TAG_KEYWORDS.items():
        if any(keyword in content_lower for keyword in keywords):
            tags.append(tag)

    return tags[:5]  # Limit to 5 auto-tags


def format_memory_for_display(page: dict) -> dict:
    """Format a Notion page as a readable memory."""
    properties = page.get("properties", {})

    # Extract content
    content_prop = properties.get("Content", {}).get("rich_text", [])
    content = content_prop[0].get("plain_text", "") if content_prop else ""

    # Extract timestamp
    timestamp_prop = properties.get("Timestamp", {}).get("date", {})
    timestamp = timestamp_prop.get("start", "") if timestamp_prop else ""

    # Extract tags
    tags_prop = properties.get("Tags", {}).get("multi_select", [])
    tags = [tag.get("name", "") for tag in tags_prop]

    # Extract mood
    mood_prop = properties.get("Mood", {}).get("select", {})
    mood = mood_prop.get("name", "") if mood_prop else ""

    # Extract source
    source_prop = properties.get("Source", {}).get("select", {})
    source = source_prop.get("name", "") if source_prop else ""

    return {
        "id": page.get("id", ""),
        "content": content,
        "timestamp": timestamp,
        "tags": tags,
        "mood": mood,
        "source": source,
        "url": page.get("url", ""),
    }


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Pensieve tools."""
    return [
        Tool(
            name="save_memory",
            description=(
                "Save a precious memory, thought, or reflection to the Pensieve. "
                "Each memory is stored with care and can include mood and tags for later recall."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The memory, thought, or reflection to save",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags to categorize the memory (auto-generated if not provided)",
                    },
                    "mood": {
                        "type": "string",
                        "enum": [
                            "happy",
                            "contemplative",
                            "grateful",
                            "curious",
                            "inspired",
                            "peaceful",
                            "bittersweet",
                            "determined",
                            "hopeful",
                            "reflective",
                        ],
                        "description": "The emotional tone of this memory",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["chat", "reflection", "journal", "voice", "import"],
                        "default": "chat",
                        "description": "Where this memory originated",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="search_memories",
            description=(
                "Search through your memories using natural language or filters. "
                "Find past thoughts, reflections, and precious moments."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by specific tags",
                    },
                    "mood": {
                        "type": "string",
                        "description": "Filter by mood",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Limit search to memories from the last N days",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of memories to return",
                    },
                },
            },
        ),
        Tool(
            name="get_recent_memories",
            description=(
                "Retrieve your most recent memories from the past few days. "
                "A gentle way to review your recent thoughts and reflections."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "default": 7,
                        "description": "Number of days to look back",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of memories to return",
                    },
                },
            },
        ),
        Tool(
            name="daily_reflection_prompt",
            description=(
                "Generate a thoughtful prompt for daily reflection. "
                "Helps guide introspection and mindful journaling."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "theme": {
                        "type": "string",
                        "description": "Optional theme for the reflection (gratitude, growth, creativity, etc.)",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    """Handle tool calls for Pensieve operations."""

    if not NOTION_API_KEY:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="I'd love to help store your memories, but I need a Notion API key first. "
                    "Please set the NOTION_API_KEY environment variable.",
                )
            ]
        )

    if not NOTION_DATABASE_ID:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Almost there! I need to know which Notion database to use as your Pensieve. "
                    "Please set the NOTION_DATABASE_ID or PENSIEVE_DATABASE_ID environment variable.",
                )
            ]
        )

    try:
        if name == "save_memory":
            return await save_memory(
                content=arguments["content"],
                tags=arguments.get("tags"),
                mood=arguments.get("mood"),
                source=arguments.get("source", "chat"),
            )
        elif name == "search_memories":
            return await search_memories(
                query=arguments.get("query"),
                tags=arguments.get("tags"),
                mood=arguments.get("mood"),
                days=arguments.get("days"),
                limit=arguments.get("limit", 10),
            )
        elif name == "get_recent_memories":
            return await get_recent_memories(
                days=arguments.get("days", 7),
                limit=arguments.get("limit", 10),
            )
        elif name == "daily_reflection_prompt":
            return await daily_reflection_prompt(
                theme=arguments.get("theme"),
            )
        else:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"I don't recognize that tool: {name}",
                    )
                ]
            )
    except Exception as e:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Something went wrong while working with your memories: {str(e)}",
                )
            ],
            isError=True,
        )


async def save_memory(
    content: str,
    tags: Optional[list[str]] = None,
    mood: Optional[str] = None,
    source: str = "chat",
) -> CallToolResult:
    """Save a memory to the Notion Pensieve database."""

    # Auto-generate tags if not provided
    if not tags:
        tags = auto_generate_tags(content)

    # Build the Notion page properties
    properties = {
        "Content": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": content},
                }
            ]
        },
        "Timestamp": {
            "date": {
                "start": datetime.now().isoformat(),
            }
        },
        "Source": {
            "select": {"name": source},
        },
    }

    if tags:
        properties["Tags"] = {
            "multi_select": [{"name": tag} for tag in tags[:10]]  # Notion limit
        }

    if mood:
        properties["Mood"] = {
            "select": {"name": mood},
        }

    # Create the page in Notion
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{NOTION_BASE_URL}/pages",
            headers=get_notion_headers(),
            json={
                "parent": {"database_id": NOTION_DATABASE_ID},
                "properties": properties,
            },
        )
        response.raise_for_status()
        page = response.json()

    # Craft a warm response
    mood_desc = MOOD_EMOJIS.get(mood, "") if mood else ""
    tags_str = ", ".join(f"#{tag}" for tag in tags) if tags else ""

    response_parts = [
        f"Memory saved to your Pensieve.",
        f"",
        f"Content: \"{content[:100]}{'...' if len(content) > 100 else ''}\"",
    ]

    if mood_desc:
        response_parts.append(f"Mood: {mood} ({mood_desc})")

    if tags_str:
        response_parts.append(f"Tags: {tags_str}")

    response_parts.append(f"Timestamp: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text="\n".join(response_parts),
            )
        ]
    )


async def search_memories(
    query: Optional[str] = None,
    tags: Optional[list[str]] = None,
    mood: Optional[str] = None,
    days: Optional[int] = None,
    limit: int = 10,
) -> CallToolResult:
    """Search through memories in the Pensieve."""

    # Build the filter
    filters = []

    if query:
        filters.append({
            "property": "Content",
            "rich_text": {"contains": query},
        })

    if tags:
        for tag in tags:
            filters.append({
                "property": "Tags",
                "multi_select": {"contains": tag},
            })

    if mood:
        filters.append({
            "property": "Mood",
            "select": {"equals": mood},
        })

    if days:
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        filters.append({
            "property": "Timestamp",
            "date": {"on_or_after": start_date},
        })

    # Build the query
    query_body = {
        "page_size": min(limit, 100),
        "sorts": [
            {
                "property": "Timestamp",
                "direction": "descending",
            }
        ],
    }

    if filters:
        if len(filters) == 1:
            query_body["filter"] = filters[0]
        else:
            query_body["filter"] = {"and": filters}

    # Query Notion
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{NOTION_BASE_URL}/databases/{NOTION_DATABASE_ID}/query",
            headers=get_notion_headers(),
            json=query_body,
        )
        response.raise_for_status()
        data = response.json()

    results = data.get("results", [])

    if not results:
        search_desc = []
        if query:
            search_desc.append(f'"{query}"')
        if tags:
            search_desc.append(f"tags: {', '.join(tags)}")
        if mood:
            search_desc.append(f"mood: {mood}")
        if days:
            search_desc.append(f"last {days} days")

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"No memories found matching {' '.join(search_desc) or 'your search'}. "
                    "Perhaps it's time to create some new ones?",
                )
            ]
        )

    # Format memories for display
    memories = [format_memory_for_display(page) for page in results]

    response_parts = [f"Found {len(memories)} {'memory' if len(memories) == 1 else 'memories'}:", ""]

    for i, memory in enumerate(memories, 1):
        date_str = ""
        if memory["timestamp"]:
            try:
                dt = datetime.fromisoformat(memory["timestamp"].replace("Z", "+00:00"))
                date_str = dt.strftime("%B %d, %Y")
            except (ValueError, AttributeError):
                date_str = memory["timestamp"]

        mood_str = f" ({memory['mood']})" if memory["mood"] else ""
        tags_str = " " + " ".join(f"#{t}" for t in memory["tags"]) if memory["tags"] else ""

        response_parts.append(f"{i}. **{date_str}**{mood_str}: \"{memory['content'][:150]}{'...' if len(memory['content']) > 150 else ''}\"{tags_str}")
        response_parts.append("")

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text="\n".join(response_parts),
            )
        ]
    )


async def get_recent_memories(days: int = 7, limit: int = 10) -> CallToolResult:
    """Get recent memories from the Pensieve."""
    return await search_memories(days=days, limit=limit)


async def daily_reflection_prompt(theme: Optional[str] = None) -> CallToolResult:
    """Generate a thoughtful daily reflection prompt."""

    prompts = {
        "gratitude": [
            "What small moment today brought you unexpected joy?",
            "Who made a difference in your day, even in a tiny way?",
            "What about today are you grateful for that you might usually overlook?",
        ],
        "growth": [
            "What did you learn today that surprised you?",
            "Where did you step outside your comfort zone, even slightly?",
            "What would you do differently if you could replay today?",
        ],
        "creativity": [
            "What sparked your imagination today?",
            "If today were a color, what would it be and why?",
            "What connection did you make between two seemingly unrelated things?",
        ],
        "connection": [
            "What conversation stayed with you today?",
            "How did you show up for someone else?",
            "What moment of genuine connection did you experience?",
        ],
        "presence": [
            "What moment today did you feel truly present?",
            "What did you notice today that you've never noticed before?",
            "When did time seem to slow down for you?",
        ],
        "general": [
            "What moment today surprised you - either a challenge you handled better than expected, or a simple joy you almost missed?",
            "What's one thing you'd like to remember about today?",
            "How are you different tonight than you were this morning?",
            "What's sitting on your heart right now?",
            "If today had a lesson to teach you, what might it be?",
        ],
    }

    import random

    theme_key = theme.lower() if theme and theme.lower() in prompts else "general"
    prompt = random.choice(prompts[theme_key])

    theme_intro = f" focused on {theme}" if theme else ""

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=f"Here's a gentle prompt for your reflection{theme_intro}:\n\n"
                f"*{prompt}*\n\n"
                "Take your time with this. When you're ready to share, I'll keep your thoughts safe in the Pensieve.",
            )
        ]
    )


async def main():
    """Run the Pensieve MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
