"""
Web Search Tool

Provides web search functionality using Serper API or similar services.
Supports general web search, news search, and image search.
"""

import os
import asyncio
import json
from dataclasses import dataclass, field
from typing import Optional, Literal
from datetime import datetime
from urllib.parse import urlencode


@dataclass
class SearchResult:
    """Represents a single search result."""

    title: str
    url: str
    snippet: str
    position: int = 0
    domain: str = ""
    date: Optional[datetime] = None
    thumbnail: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "position": self.position,
            "domain": self.domain,
            "date": self.date.isoformat() if self.date else None,
            "thumbnail": self.thumbnail,
        }


@dataclass
class WebSearchResponse:
    """Represents a web search response."""

    query: str
    results: list[SearchResult]
    total_results: int = 0
    search_time_ms: float = 0.0
    knowledge_graph: Optional[dict] = None
    related_searches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_results": self.total_results,
            "search_time_ms": self.search_time_ms,
            "knowledge_graph": self.knowledge_graph,
            "related_searches": self.related_searches,
        }


SearchType = Literal["search", "news", "images", "places"]


class WebSearchTool:
    """
    Tool for performing web searches using Serper API.

    Supports multiple search types including web, news, images, and places.
    """

    SERPER_BASE_URL = "https://google.serper.dev"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        default_country: str = "us",
        default_language: str = "en",
    ):
        """
        Initialize web search tool.

        Args:
            api_key: Serper API key
            timeout: Request timeout in seconds
            default_country: Default country code for results
            default_language: Default language for results
        """
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.timeout = timeout
        self.default_country = default_country
        self.default_language = default_language

        if not self.api_key:
            raise ValueError(
                "Serper API key required. Set SERPER_API_KEY environment variable."
            )

    async def search(
        self,
        query: str,
        search_type: SearchType = "search",
        num_results: int = 10,
        country: Optional[str] = None,
        language: Optional[str] = None,
        time_range: Optional[str] = None,
    ) -> WebSearchResponse:
        """
        Perform a web search.

        Args:
            query: Search query
            search_type: Type of search ('search', 'news', 'images', 'places')
            num_results: Number of results to return
            country: Country code for results
            language: Language for results
            time_range: Time range filter ('d' for day, 'w' for week, 'm' for month, 'y' for year)

        Returns:
            WebSearchResponse containing search results
        """
        # TODO: Implement actual Serper API call
        # This is a stub implementation

        start_time = asyncio.get_event_loop().time()

        # Placeholder - would make actual API call here
        # url = f"{self.SERPER_BASE_URL}/{search_type}"
        # headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        # payload = {
        #     "q": query,
        #     "num": num_results,
        #     "gl": country or self.default_country,
        #     "hl": language or self.default_language,
        # }
        # if time_range:
        #     payload["tbs"] = f"qdr:{time_range}"

        results = []
        search_time = (asyncio.get_event_loop().time() - start_time) * 1000

        return WebSearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            search_time_ms=search_time,
        )

    async def search_news(
        self,
        query: str,
        num_results: int = 10,
        time_range: Optional[str] = None,
    ) -> WebSearchResponse:
        """
        Search for news articles.

        Args:
            query: Search query
            num_results: Number of results
            time_range: Time range filter

        Returns:
            WebSearchResponse with news results
        """
        return await self.search(
            query=query,
            search_type="news",
            num_results=num_results,
            time_range=time_range,
        )

    async def search_images(
        self,
        query: str,
        num_results: int = 10,
    ) -> WebSearchResponse:
        """
        Search for images.

        Args:
            query: Search query
            num_results: Number of results

        Returns:
            WebSearchResponse with image results
        """
        return await self.search(
            query=query,
            search_type="images",
            num_results=num_results,
        )

    async def get_answer_box(self, query: str) -> Optional[dict]:
        """
        Get the answer box/featured snippet for a query.

        Args:
            query: Search query

        Returns:
            Answer box data if available, None otherwise
        """
        # TODO: Implement answer box extraction
        # This is a stub implementation
        return None


# Convenience functions for direct use


async def search_web(
    query: str,
    num_results: int = 10,
    **kwargs,
) -> WebSearchResponse:
    """
    Perform a web search.

    Args:
        query: Search query
        num_results: Number of results
        **kwargs: Additional search parameters

    Returns:
        WebSearchResponse with results
    """
    try:
        tool = WebSearchTool()
        return await tool.search(query, num_results=num_results, **kwargs)
    except ValueError:
        # Return empty result if API key not configured
        return WebSearchResponse(query=query, results=[], total_results=0)


async def search_news(
    query: str,
    num_results: int = 10,
    time_range: Optional[str] = None,
) -> WebSearchResponse:
    """
    Search for news articles.

    Args:
        query: Search query
        num_results: Number of results
        time_range: Time range filter

    Returns:
        WebSearchResponse with news results
    """
    try:
        tool = WebSearchTool()
        return await tool.search_news(query, num_results, time_range)
    except ValueError:
        return WebSearchResponse(query=query, results=[], total_results=0)


# Synchronous wrappers for non-async contexts


def search_web_sync(query: str, num_results: int = 10, **kwargs) -> WebSearchResponse:
    """Synchronous wrapper for search_web."""
    return asyncio.run(search_web(query, num_results, **kwargs))


def search_news_sync(
    query: str,
    num_results: int = 10,
    time_range: Optional[str] = None,
) -> WebSearchResponse:
    """Synchronous wrapper for search_news."""
    return asyncio.run(search_news(query, num_results, time_range))
