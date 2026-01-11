"""
Shared Tools Package

This package provides common tools used across Life OS orchestrators:
- PubMed search for scientific literature
- Web search for general research
- RAG (Retrieval Augmented Generation) for knowledge base queries
"""

from .pubmed import PubMedTool, search_pubmed, get_article_details
from .web_search import WebSearchTool, search_web, search_news
from .rag import RAGTool, query_knowledge_base, add_to_knowledge_base

__all__ = [
    # PubMed
    "PubMedTool",
    "search_pubmed",
    "get_article_details",
    # Web Search
    "WebSearchTool",
    "search_web",
    "search_news",
    # RAG
    "RAGTool",
    "query_knowledge_base",
    "add_to_knowledge_base",
]

__version__ = "1.0.0"
