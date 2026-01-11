"""Research Agent - Handles research, data gathering, and summarization."""

from typing import Any, Dict, List, Optional
import logging
import asyncio
from datetime import datetime

from ...base.agent import BaseAgent, AgentTool, ResponseFormat


logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """
    Research Agent for data gathering and summarization.

    Tools:
    - PubMed search: Search medical/scientific literature
    - Web search: General web search
    - RAG query: Query vector database for relevant documents
    - Summarize: Summarize long texts or multiple sources
    """

    SYSTEM_PROMPT = """You are an expert research assistant specializing in gathering, analyzing, and summarizing information from multiple sources.

Your capabilities include:
1. Searching PubMed for medical and scientific literature
2. Performing web searches for general information
3. Querying document databases using RAG
4. Synthesizing information from multiple sources into clear summaries

Guidelines:
- Always cite your sources when presenting findings
- Distinguish between peer-reviewed and non-peer-reviewed sources
- Highlight key findings and statistics
- Note any limitations or conflicting information
- Present information in a structured, easy-to-understand format

When researching, prioritize:
1. Accuracy and reliability of sources
2. Recency of information
3. Relevance to the query
4. Comprehensiveness of coverage"""

    def __init__(
        self,
        model: str = "glm-4",
        model_config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            model=model,
            model_config=model_config,
            response_format=ResponseFormat.MARKDOWN
        )
        self._last_tools_used: List[str] = []

    def _initialize_tools(self) -> None:
        """Initialize research tools."""

        # PubMed Search Tool
        self.register_tool(AgentTool(
            name="pubmed_search",
            description="Search PubMed database for medical and scientific articles",
            func=self._pubmed_search,
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query for PubMed"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 10
                },
                "date_range": {
                    "type": "string",
                    "description": "Date range filter (e.g., '5y' for 5 years)",
                    "default": "5y"
                }
            },
            required_params=["query"]
        ))

        # Web Search Tool
        self.register_tool(AgentTool(
            name="web_search",
            description="Search the web for general information",
            func=self._web_search,
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 10
                },
                "site_filter": {
                    "type": "string",
                    "description": "Limit search to specific domain",
                    "default": None
                }
            },
            required_params=["query"]
        ))

        # RAG Query Tool
        self.register_tool(AgentTool(
            name="rag_query",
            description="Query the vector database for relevant documents",
            func=self._rag_query,
            parameters={
                "query": {
                    "type": "string",
                    "description": "Query to search for relevant documents"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of top results to return",
                    "default": 5
                },
                "collection": {
                    "type": "string",
                    "description": "Specific collection to search",
                    "default": "default"
                }
            },
            required_params=["query"]
        ))

        # Summarize Tool
        self.register_tool(AgentTool(
            name="summarize",
            description="Summarize text or multiple sources",
            func=self._summarize,
            parameters={
                "texts": {
                    "type": "array",
                    "description": "List of texts to summarize"
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum length of summary in words",
                    "default": 500
                },
                "style": {
                    "type": "string",
                    "description": "Summary style: 'brief', 'detailed', 'bullet_points'",
                    "default": "detailed"
                }
            },
            required_params=["texts"]
        ))

    def _initialize_prompts(self) -> None:
        """Initialize prompt templates."""

        self.register_prompt_template(
            "research_query",
            """Research the following topic thoroughly:

Topic: {topic}

Focus areas:
{focus_areas}

Please provide:
1. Key findings from reliable sources
2. Statistics and data points
3. Expert opinions or consensus
4. Any controversies or debates
5. Recent developments

Sources to prioritize: {sources}"""
        )

        self.register_prompt_template(
            "summarize_sources",
            """Summarize the following sources on the topic of "{topic}":

Sources:
{sources_text}

Provide a comprehensive summary that:
1. Highlights the main points
2. Notes any agreements/disagreements between sources
3. Identifies gaps in the information
4. Suggests areas for further research"""
        )

        self.register_prompt_template(
            "fact_check",
            """Fact-check the following claim:

Claim: {claim}

Using the available tools, verify this claim and provide:
1. Verification status (True/False/Partially True/Unverifiable)
2. Supporting evidence
3. Contradicting evidence
4. Source reliability assessment"""
        )

    async def _pubmed_search(
        self,
        query: str,
        max_results: int = 10,
        date_range: str = "5y"
    ) -> Dict[str, Any]:
        """
        Search PubMed for scientific articles.

        In production, this would integrate with NCBI E-utilities API.
        """
        logger.info(f"PubMed search: {query}")

        # Simulated response structure
        # In production: Use Bio.Entrez or direct API calls
        return {
            "query": query,
            "total_results": 0,
            "results": [],
            "search_params": {
                "max_results": max_results,
                "date_range": date_range
            },
            "status": "mock_response",
            "message": "PubMed integration pending. Connect to NCBI E-utilities API."
        }

    async def _web_search(
        self,
        query: str,
        num_results: int = 10,
        site_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform web search.

        In production, integrate with search API (SerpAPI, Brave, etc.)
        """
        logger.info(f"Web search: {query}")

        search_query = query
        if site_filter:
            search_query = f"site:{site_filter} {query}"

        return {
            "query": search_query,
            "num_results": 0,
            "results": [],
            "status": "mock_response",
            "message": "Web search integration pending. Connect to search API."
        }

    async def _rag_query(
        self,
        query: str,
        top_k: int = 5,
        collection: str = "default"
    ) -> Dict[str, Any]:
        """
        Query vector database for relevant documents.

        In production, integrate with vector DB (Chroma, Pinecone, etc.)
        """
        logger.info(f"RAG query: {query}")

        return {
            "query": query,
            "collection": collection,
            "results": [],
            "status": "mock_response",
            "message": "RAG integration pending. Connect to vector database."
        }

    async def _summarize(
        self,
        texts: List[str],
        max_length: int = 500,
        style: str = "detailed"
    ) -> Dict[str, Any]:
        """
        Summarize multiple texts.

        Uses the LLM to generate a coherent summary.
        """
        logger.info(f"Summarizing {len(texts)} texts")

        combined_length = sum(len(t) for t in texts)

        return {
            "input_texts": len(texts),
            "total_input_length": combined_length,
            "style": style,
            "max_length": max_length,
            "summary": "",
            "status": "mock_response",
            "message": "Summary would be generated by LLM in production."
        }

    async def _process(
        self,
        task: str,
        content: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process research task."""
        self._last_tools_used = []

        # Determine which tools to use based on content
        sources = context.get("sources", ["pubmed", "web"])
        results = {
            "query": content,
            "timestamp": datetime.utcnow().isoformat(),
            "sources_searched": [],
            "findings": []
        }

        # Execute searches based on requested sources
        if "pubmed" in sources:
            self._last_tools_used.append("pubmed_search")
            pubmed_results = await self._pubmed_search(content)
            results["pubmed"] = pubmed_results
            results["sources_searched"].append("pubmed")

        if "web" in sources:
            self._last_tools_used.append("web_search")
            web_results = await self._web_search(content)
            results["web"] = web_results
            results["sources_searched"].append("web")

        if "rag" in sources or context.get("use_rag"):
            self._last_tools_used.append("rag_query")
            rag_results = await self._rag_query(content)
            results["rag"] = rag_results
            results["sources_searched"].append("rag")

        # Generate research summary
        results["summary"] = await self._generate_research_summary(content, results)

        return results

    async def _generate_research_summary(
        self,
        query: str,
        results: Dict[str, Any]
    ) -> str:
        """Generate a summary of research findings."""
        # In production, this would use the LLM to synthesize findings

        summary_parts = [
            f"## Research Summary: {query}",
            "",
            f"**Sources Searched:** {', '.join(results['sources_searched'])}",
            "",
            "### Key Findings",
            "",
            "*Research results pending integration with actual search APIs.*",
            "",
            "### Methodology",
            f"- Searched {len(results['sources_searched'])} source(s)",
            f"- Query: \"{query}\"",
            "",
            "### Next Steps",
            "- Connect PubMed via NCBI E-utilities",
            "- Integrate web search API",
            "- Set up vector database for RAG queries"
        ]

        return "\n".join(summary_parts)
