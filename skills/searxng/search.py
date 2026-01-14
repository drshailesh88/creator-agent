#!/usr/bin/env python3
"""
SearXNG Search Client for Clawdbot

A Python client for interacting with a self-hosted SearXNG instance.
Provides async search functionality with result parsing and error handling.
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlencode, urljoin

import aiohttp

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("searxng")


@dataclass
class SearchResult:
    """Represents a single search result."""
    title: str
    url: str
    content: str
    engine: str
    score: float = 0.0
    category: str = "general"
    thumbnail: Optional[str] = None
    publishedDate: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "engine": self.engine,
            "score": self.score,
            "category": self.category,
            "thumbnail": self.thumbnail,
            "published_date": self.publishedDate,
        }


@dataclass
class SearchResponse:
    """Represents a complete search response."""
    query: str
    results: list[SearchResult]
    number_of_results: int
    answers: list[str] = field(default_factory=list)
    infoboxes: list[dict] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "number_of_results": self.number_of_results,
            "answers": self.answers,
            "infoboxes": self.infoboxes,
            "suggestions": self.suggestions,
        }


class SearXNGError(Exception):
    """Base exception for SearXNG errors."""
    pass


class SearXNGConnectionError(SearXNGError):
    """Raised when connection to SearXNG fails."""
    pass


class SearXNGTimeoutError(SearXNGError):
    """Raised when request times out."""
    pass


class SearXNGClient:
    """
    Async client for SearXNG metasearch engine.

    Example usage:
        async with SearXNGClient() as client:
            results = await client.search("python tutorial")
            for result in results.results:
                print(f"{result.title}: {result.url}")
    """

    DEFAULT_ENGINES = ["google", "bing", "duckduckgo"]
    DEFAULT_CATEGORIES = ["general"]

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 10,
        max_results: int = 20,
    ):
        """
        Initialize SearXNG client.

        Args:
            base_url: SearXNG instance URL. Defaults to SEARXNG_URL env var or localhost:8888
            timeout: Request timeout in seconds
            max_results: Maximum results to return
        """
        self.base_url = base_url or os.getenv("SEARXNG_URL", "http://localhost:8888")
        self.timeout = timeout
        self.max_results = max_results
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "SearXNGClient":
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def search(
        self,
        query: str,
        categories: Optional[list[str]] = None,
        engines: Optional[list[str]] = None,
        language: str = "en",
        safe_search: int = 0,
        time_range: str = "",
        max_results: Optional[int] = None,
    ) -> SearchResponse:
        """
        Perform a search query.

        Args:
            query: Search query string
            categories: Categories to search (general, images, videos, news, science, it, files)
            engines: Specific engines to use (google, bing, duckduckgo, etc.)
            language: Language code (en, es, fr, etc.)
            safe_search: Safe search level (0=off, 1=moderate, 2=strict)
            time_range: Time range filter (day, week, month, year, or empty)
            max_results: Maximum results to return

        Returns:
            SearchResponse with results

        Raises:
            SearXNGConnectionError: Connection failed
            SearXNGTimeoutError: Request timed out
            SearXNGError: Other errors
        """
        if not query.strip():
            raise SearXNGError("Query cannot be empty")

        # Build query parameters
        params = {
            "q": query,
            "format": "json",
            "language": language,
            "safesearch": safe_search,
        }

        if categories:
            params["categories"] = ",".join(categories)

        if engines:
            params["engines"] = ",".join(engines)

        if time_range:
            params["time_range"] = time_range

        # Build URL
        url = urljoin(self.base_url, "/search")
        full_url = f"{url}?{urlencode(params)}"

        logger.debug(f"Searching: {full_url}")

        try:
            session = self._get_session()
            async with session.get(full_url) as response:
                if response.status != 200:
                    text = await response.text()
                    raise SearXNGError(f"Search failed with status {response.status}: {text}")

                data = await response.json()

        except aiohttp.ClientConnectorError as e:
            raise SearXNGConnectionError(f"Failed to connect to SearXNG at {self.base_url}: {e}")
        except asyncio.TimeoutError:
            raise SearXNGTimeoutError(f"Search request timed out after {self.timeout}s")
        except aiohttp.ClientError as e:
            raise SearXNGError(f"HTTP error: {e}")
        except json.JSONDecodeError as e:
            raise SearXNGError(f"Invalid JSON response: {e}")

        # Parse results
        results = []
        limit = max_results or self.max_results

        for item in data.get("results", [])[:limit]:
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                engine=item.get("engine", ""),
                score=item.get("score", 0.0),
                category=item.get("category", "general"),
                thumbnail=item.get("thumbnail"),
                publishedDate=item.get("publishedDate"),
            ))

        return SearchResponse(
            query=query,
            results=results,
            number_of_results=data.get("number_of_results", len(results)),
            answers=data.get("answers", []),
            infoboxes=data.get("infoboxes", []),
            suggestions=data.get("suggestions", []),
        )

    async def research(
        self,
        topic: str,
        depth: str = "thorough",
        focus_areas: Optional[list[str]] = None,
        include_academic: bool = False,
    ) -> dict[str, Any]:
        """
        Perform deep research on a topic with multiple queries.

        Args:
            topic: Main topic to research
            depth: Research depth (basic, thorough, comprehensive)
            focus_areas: Specific aspects to focus on
            include_academic: Include academic sources

        Returns:
            Dictionary with aggregated research results
        """
        queries = [topic]

        # Generate related queries based on depth
        if depth in ("thorough", "comprehensive"):
            queries.extend([
                f"{topic} overview",
                f"{topic} latest developments",
            ])

        if depth == "comprehensive":
            queries.extend([
                f"{topic} best practices",
                f"{topic} challenges problems",
                f"{topic} future trends",
            ])

        # Add focus area queries
        if focus_areas:
            for area in focus_areas[:3]:  # Limit to 3 focus areas
                queries.append(f"{topic} {area}")

        # Determine categories
        categories = ["general"]
        if include_academic:
            categories.append("science")

        # Execute searches concurrently
        tasks = [
            self.search(q, categories=categories, max_results=10)
            for q in queries
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        all_results = []
        seen_urls = set()
        errors = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"Query '{queries[i]}' failed: {result}")
                continue

            for r in result.results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_results.append(r.to_dict())

        # Sort by score
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        return {
            "topic": topic,
            "depth": depth,
            "queries_executed": len(queries),
            "total_results": len(all_results),
            "results": all_results[:30],  # Top 30 results
            "errors": errors if errors else None,
        }

    async def get_engines(self) -> list[dict]:
        """Get list of available search engines."""
        # SearXNG doesn't have a standard API for this,
        # so we return our configured list
        return [
            {"name": "google", "categories": ["general", "images", "news"]},
            {"name": "bing", "categories": ["general", "images", "news"]},
            {"name": "duckduckgo", "categories": ["general"]},
            {"name": "brave", "categories": ["general"]},
            {"name": "wikipedia", "categories": ["general"]},
            {"name": "github", "categories": ["it"]},
            {"name": "stackoverflow", "categories": ["it"]},
            {"name": "arxiv", "categories": ["science"]},
            {"name": "pubmed", "categories": ["science"]},
            {"name": "reddit", "categories": ["general"]},
            {"name": "youtube", "categories": ["videos"]},
            {"name": "hackernews", "categories": ["it", "news"]},
        ]

    async def get_categories(self) -> list[str]:
        """Get list of available categories."""
        return ["general", "images", "videos", "news", "science", "it", "files"]

    async def health_check(self) -> bool:
        """Check if SearXNG is healthy."""
        try:
            url = urljoin(self.base_url, "/healthz")
            session = self._get_session()
            async with session.get(url) as response:
                return response.status == 200
        except Exception:
            return False


# MCP Server Implementation
async def serve_mcp():
    """Run as MCP server (stdio transport)."""
    import json
    import sys

    client = SearXNGClient()

    async def handle_request(request: dict) -> dict:
        """Handle MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {
                            "name": "searxng-mcp",
                            "version": "1.0.0"
                        },
                        "capabilities": {
                            "tools": {}
                        }
                    }
                }

            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "searxng_search",
                                "description": "Search the web using SearXNG",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string"},
                                        "categories": {"type": "array", "items": {"type": "string"}},
                                        "engines": {"type": "array", "items": {"type": "string"}},
                                        "max_results": {"type": "integer"}
                                    },
                                    "required": ["query"]
                                }
                            },
                            {
                                "name": "searxng_research",
                                "description": "Deep research on a topic",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "topic": {"type": "string"},
                                        "depth": {"type": "string"},
                                        "include_academic": {"type": "boolean"}
                                    },
                                    "required": ["topic"]
                                }
                            }
                        ]
                    }
                }

            elif method == "tools/call":
                tool_name = params.get("name", "")
                args = params.get("arguments", {})

                if tool_name == "searxng_search":
                    result = await client.search(
                        query=args.get("query", ""),
                        categories=args.get("categories"),
                        engines=args.get("engines"),
                        max_results=args.get("max_results", 20)
                    )
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result.to_dict(), indent=2)
                                }
                            ]
                        }
                    }

                elif tool_name == "searxng_research":
                    result = await client.research(
                        topic=args.get("topic", ""),
                        depth=args.get("depth", "thorough"),
                        include_academic=args.get("include_academic", False)
                    )
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result, indent=2)
                                }
                            ]
                        }
                    }

                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown method: {method}"
                    }
                }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }

    # Read from stdin, write to stdout
    logger.info("SearXNG MCP server starting...")

    try:
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            try:
                request = json.loads(line)
                response = await handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON: {line}")

    finally:
        await client.close()


# CLI Interface
async def cli_search(args):
    """CLI search command."""
    async with SearXNGClient() as client:
        if args.health:
            healthy = await client.health_check()
            print(f"SearXNG status: {'healthy' if healthy else 'unhealthy'}")
            return

        if args.engines_list:
            engines = await client.get_engines()
            print("Available engines:")
            for e in engines:
                print(f"  - {e['name']}: {', '.join(e['categories'])}")
            return

        if not args.query:
            print("Error: query is required")
            return

        query = " ".join(args.query)

        if args.research:
            result = await client.research(
                topic=query,
                depth=args.depth or "thorough",
                include_academic=args.academic,
            )
            print(json.dumps(result, indent=2))
        else:
            result = await client.search(
                query=query,
                categories=args.categories.split(",") if args.categories else None,
                engines=args.engines.split(",") if args.engines else None,
                max_results=args.max_results,
            )
            print(json.dumps(result.to_dict(), indent=2))


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SearXNG Search Client")
    parser.add_argument("query", nargs="*", help="Search query")
    parser.add_argument("--serve", action="store_true", help="Run as MCP server")
    parser.add_argument("--url", help="SearXNG base URL")
    parser.add_argument("--categories", "-c", help="Categories (comma-separated)")
    parser.add_argument("--engines", "-e", help="Engines (comma-separated)")
    parser.add_argument("--max-results", "-n", type=int, default=20, help="Max results")
    parser.add_argument("--research", "-r", action="store_true", help="Research mode")
    parser.add_argument("--depth", choices=["basic", "thorough", "comprehensive"])
    parser.add_argument("--academic", action="store_true", help="Include academic sources")
    parser.add_argument("--health", action="store_true", help="Check health")
    parser.add_argument("--engines-list", action="store_true", help="List engines")

    args = parser.parse_args()

    if args.url:
        os.environ["SEARXNG_URL"] = args.url

    if args.serve:
        asyncio.run(serve_mcp())
    else:
        asyncio.run(cli_search(args))


if __name__ == "__main__":
    main()
