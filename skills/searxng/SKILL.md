---
name: searxng
description: Self-hosted metasearch engine for privacy-respecting web searches
version: 1.0.0
author: Life OS
tags: ["search", "research", "privacy", "web"]
requires:
  - "SearXNG Docker container"
personality_safe: true
---

# SearXNG Search Skill

## Overview

SearXNG is a self-hosted metasearch engine that aggregates results from multiple search engines without tracking. This skill enables Clawdbot to:

- Search the web without API key limitations
- Access multiple search engines (Google, Bing, DuckDuckGo, etc.) in one query
- Perform research tasks with privacy
- Get structured search results in JSON format

## Commands/Capabilities

### `/search`

**Description**: Search the web using SearXNG.

**Usage**:
```
/search [query] [--engines=google,bing] [--category=general]
```

**Examples**:
```
/search "machine learning best practices"
/search "Python async tutorial" --engines=google,stackoverflow
/search "latest AI news" --category=news
/search "neural network architecture" --category=science
```

### `/research`

**Description**: Deep research on a topic with multiple queries.

**Usage**:
```
/research [topic] [--depth=basic|thorough|comprehensive]
```

**Examples**:
```
/research "GraphQL vs REST API comparison"
/research "sustainable packaging trends 2024" --depth=thorough
```

### Automatic Triggers

| Trigger | Action |
|---------|--------|
| "search for..." | Performs web search |
| "look up..." | Performs web search |
| "find information about..." | Research query |
| "what's the latest on..." | News category search |

---

## Available Categories

| Category | Description | Best For |
|----------|-------------|----------|
| `general` | General web search | Broad queries |
| `images` | Image search | Visual content |
| `videos` | Video search | YouTube, Vimeo |
| `news` | News articles | Current events |
| `science` | Academic papers | Research, citations |
| `it` | Tech/programming | Code, docs |
| `files` | File downloads | Documents |

## Available Search Engines

### General Search
- `google` - Google Search
- `bing` - Microsoft Bing
- `duckduckgo` - DuckDuckGo
- `brave` - Brave Search
- `qwant` - Qwant (EU)

### Knowledge
- `wikipedia` - Wikipedia articles
- `wikidata` - Structured knowledge

### Tech/Programming
- `github` - GitHub repositories
- `stackoverflow` - Stack Overflow Q&A
- `hackernews` - Hacker News

### Academic/Science
- `arxiv` - arXiv papers
- `semantic_scholar` - Semantic Scholar
- `google_scholar` - Google Scholar
- `pubmed` - PubMed medical literature

### Social/News
- `reddit` - Reddit posts
- `google_news` - Google News
- `bing_news` - Bing News

### Media
- `youtube` - YouTube videos
- `vimeo` - Vimeo videos
- `google_images` - Google Images
- `bing_images` - Bing Images

---

## Personality Guidelines

> **CRITICAL**: This skill MUST maintain Clawdbot's core personality defined in SOUL.md.

### Response Style

When presenting search results, Clawdbot should:

1. **Acknowledge the search warmly**
   - "Let me look that up for you..."
   - "Great question! Searching now..."

2. **Present results helpfully**
   - Summarize key findings
   - Highlight most relevant results
   - Group by source type when helpful

3. **Offer to dig deeper**
   - "Want me to explore any of these further?"
   - "I can search for more specific information if needed"

### Response Templates

**Search Results**:
```
I found some great results for "[query]":

**Top Results:**
1. [Title] - [brief description]
   Source: [domain]

2. [Title] - [brief description]
   Source: [domain]

Would you like me to look into any of these in more detail?
```

**No Results**:
```
Hmm, I couldn't find much on "[query]". Let me try:
- A different search engine
- Broader search terms
- Related topics

What would you prefer?
```

---

## API Usage

### Direct API Access

SearXNG provides a JSON API at `/search`:

```bash
# Basic search
curl "http://localhost:8888/search?q=python+tutorial&format=json"

# With category
curl "http://localhost:8888/search?q=AI+news&categories=news&format=json"

# Specific engines
curl "http://localhost:8888/search?q=async+await&engines=google,stackoverflow&format=json"
```

### Response Format

```json
{
  "query": "python tutorial",
  "results": [
    {
      "title": "Python Tutorial - W3Schools",
      "url": "https://www.w3schools.com/python/",
      "content": "Well organized and easy to understand...",
      "engine": "google",
      "score": 1.0,
      "category": "general"
    }
  ],
  "number_of_results": 25,
  "answers": [],
  "infoboxes": []
}
```

---

## Configuration

### Environment Variables

```bash
# SearXNG instance URL (default: localhost)
SEARXNG_URL=http://localhost:8888

# Request timeout in seconds
SEARXNG_TIMEOUT=10

# Default number of results
SEARXNG_MAX_RESULTS=20

# Default search engines
SEARXNG_DEFAULT_ENGINES=google,bing,duckduckgo
```

### Skill Options

```python
{
    "base_url": "http://localhost:8888",
    "timeout": 10,
    "max_results": 20,
    "default_engines": ["google", "bing", "duckduckgo"],
    "default_category": "general",
    "safe_search": 0,  # 0=off, 1=moderate, 2=strict

    # Personality preservation
    "preserve_personality": True,
    "soul_md_override": False
}
```

---

## Examples

### Example 1: Basic Search

**User**: Search for best practices for Python async programming

**Clawdbot** (with this skill):
```
Let me search for Python async best practices...

I found some excellent resources:

**Top Results:**

1. **Real Python - Async IO in Python**
   Comprehensive guide covering asyncio fundamentals, event loops, and patterns.
   Source: realpython.com

2. **Python Docs - asyncio**
   Official documentation for Python's asyncio library.
   Source: docs.python.org

3. **Stack Overflow - Async/Await Best Practices**
   Community-curated best practices and common pitfalls.
   Source: stackoverflow.com

The Real Python guide is particularly good for learning the fundamentals.
Would you like me to dig deeper into any specific aspect?
```

### Example 2: Research Query

**User**: Research the current state of quantum computing

**Clawdbot** (with this skill):
```
I'll do a thorough search across multiple sources...

**Quantum Computing - Current State (2024)**

From academic sources (arXiv, Google Scholar):
- IBM announced 1,000+ qubit processor milestone
- Error correction advances showing promise
- Key papers on topological qubits gaining traction

From tech news (Hacker News, Google News):
- Google's quantum supremacy claims debated
- Microsoft investing heavily in topological approach
- Startups receiving significant funding

From general sources:
- Practical applications still 5-10 years out for most use cases
- Cryptography concerns driving government interest
- Cloud-based quantum computing services expanding

Would you like me to focus on any particular aspect -
the technical progress, business landscape, or practical applications?
```

### Example 3: Category-Specific Search

**User**: Find recent news about AI regulation

**Clawdbot** (with this skill):
```
Searching news sources for AI regulation updates...

**Recent AI Regulation News:**

1. **EU AI Act Implementation Timeline Announced**
   The European Union released detailed guidelines...
   Source: reuters.com (2 hours ago)

2. **US Executive Order on AI Safety**
   New requirements for AI companies...
   Source: nytimes.com (1 day ago)

3. **China Updates AI Content Regulations**
   New rules for generative AI services...
   Source: scmp.com (3 days ago)

This is a fast-moving area! Want me to set up a recurring
search to keep you updated?
```

---

## Error Handling

| Error | Response |
|-------|----------|
| SearXNG unavailable | "Search service is temporarily down. Let me try again in a moment..." |
| No results | "I couldn't find results for that specific query. Let me try broader terms..." |
| Timeout | "The search is taking longer than expected. Let me try fewer engines..." |
| Rate limited | "I'm searching a bit too fast. Give me a moment..." |

---

## MCP Server Integration

See `mcporter.json` for MCP tool configuration.

### Required MCP Tools

| Tool | Purpose |
|------|---------|
| `searxng_search` | Execute web searches |
| `searxng_research` | Multi-query research |

---

## Testing

### Verify SearXNG is Running

```bash
curl http://localhost:8888/healthz
```

### Test JSON API

```bash
curl "http://localhost:8888/search?q=test&format=json" | jq .
```

### Test from Python

```python
from skills.searxng.search import SearXNGClient

async def test():
    client = SearXNGClient()
    results = await client.search("python tutorial")
    print(f"Found {len(results)} results")
```

---

## Changelog

### 1.0.0
- Initial release
- Basic search functionality
- Multiple engine support
- Category filtering
- JSON API integration
