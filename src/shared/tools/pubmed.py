"""
PubMed Search Tool

Provides functionality to search PubMed for scientific literature,
retrieve article abstracts, and get citation information.
"""

import os
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class PubMedArticle:
    """Represents a PubMed article."""

    pmid: str
    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    publication_date: Optional[datetime] = None
    doi: Optional[str] = None
    keywords: list[str] = field(default_factory=list)
    mesh_terms: list[str] = field(default_factory=list)
    citation_count: int = 0

    @property
    def url(self) -> str:
        """Get the PubMed URL for this article."""
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "pmid": self.pmid,
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "journal": self.journal,
            "publication_date": (
                self.publication_date.isoformat() if self.publication_date else None
            ),
            "doi": self.doi,
            "keywords": self.keywords,
            "mesh_terms": self.mesh_terms,
            "citation_count": self.citation_count,
            "url": self.url,
        }


@dataclass
class PubMedSearchResult:
    """Represents search results from PubMed."""

    query: str
    total_count: int
    articles: list[PubMedArticle]
    search_time_ms: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "query": self.query,
            "total_count": self.total_count,
            "articles": [a.to_dict() for a in self.articles],
            "search_time_ms": self.search_time_ms,
        }


class PubMedTool:
    """
    Tool for searching PubMed scientific literature database.

    Uses NCBI E-utilities API for searching and retrieving articles.
    """

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize PubMed tool.

        Args:
            api_key: NCBI API key (optional, increases rate limits)
            email: Contact email (required by NCBI for identification)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("NCBI_API_KEY")
        self.email = email or os.getenv("NCBI_EMAIL", "user@example.com")
        self.timeout = timeout

    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> PubMedSearchResult:
        """
        Search PubMed for articles matching the query.

        Args:
            query: Search query (supports PubMed query syntax)
            max_results: Maximum number of results to return
            sort: Sort order ('relevance', 'date', 'citation')
            date_from: Start date filter (YYYY/MM/DD)
            date_to: End date filter (YYYY/MM/DD)

        Returns:
            PubMedSearchResult containing matching articles
        """
        # TODO: Implement actual PubMed API call
        # This is a stub implementation

        start_time = asyncio.get_event_loop().time()

        # Placeholder - would make actual API calls here
        articles = []

        search_time = (asyncio.get_event_loop().time() - start_time) * 1000

        return PubMedSearchResult(
            query=query,
            total_count=len(articles),
            articles=articles,
            search_time_ms=search_time,
        )

    async def get_article(self, pmid: str) -> Optional[PubMedArticle]:
        """
        Get detailed information for a specific article.

        Args:
            pmid: PubMed ID of the article

        Returns:
            PubMedArticle if found, None otherwise
        """
        # TODO: Implement actual article fetch
        # This is a stub implementation
        return None

    async def get_citations(self, pmid: str) -> list[str]:
        """
        Get articles that cite the given article.

        Args:
            pmid: PubMed ID of the article

        Returns:
            List of PMIDs that cite this article
        """
        # TODO: Implement citation lookup
        # This is a stub implementation
        return []

    async def get_related(self, pmid: str, max_results: int = 5) -> list[PubMedArticle]:
        """
        Get related articles for a given article.

        Args:
            pmid: PubMed ID of the article
            max_results: Maximum number of related articles

        Returns:
            List of related PubMedArticle objects
        """
        # TODO: Implement related articles lookup
        # This is a stub implementation
        return []


# Convenience functions for direct use


async def search_pubmed(
    query: str,
    max_results: int = 10,
    **kwargs,
) -> PubMedSearchResult:
    """
    Search PubMed for articles.

    Args:
        query: Search query
        max_results: Maximum results to return
        **kwargs: Additional search parameters

    Returns:
        PubMedSearchResult containing matching articles
    """
    tool = PubMedTool()
    return await tool.search(query, max_results, **kwargs)


async def get_article_details(pmid: str) -> Optional[PubMedArticle]:
    """
    Get details for a specific PubMed article.

    Args:
        pmid: PubMed ID

    Returns:
        PubMedArticle if found, None otherwise
    """
    tool = PubMedTool()
    return await tool.get_article(pmid)


# Synchronous wrappers for non-async contexts


def search_pubmed_sync(query: str, max_results: int = 10, **kwargs) -> PubMedSearchResult:
    """Synchronous wrapper for search_pubmed."""
    return asyncio.run(search_pubmed(query, max_results, **kwargs))


def get_article_details_sync(pmid: str) -> Optional[PubMedArticle]:
    """Synchronous wrapper for get_article_details."""
    return asyncio.run(get_article_details(pmid))
