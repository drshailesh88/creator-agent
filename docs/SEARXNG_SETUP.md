# SearXNG Setup Guide

Self-hosted metasearch engine for privacy-respecting web searches without API key limitations.

## Overview

SearXNG aggregates results from 70+ search engines (Google, Bing, DuckDuckGo, etc.) without tracking. It provides a JSON API that Clawdbot can use for web searches.

**Why SearXNG instead of Brave Search API?**
- No API key required
- No rate limits from external providers
- Complete control over the instance
- Privacy-focused (no tracking)
- Access to multiple search engines simultaneously

## Prerequisites

- Docker and Docker Compose installed
- VPS with at least 512MB RAM available
- Port 8888 available (or modify the configuration)

## Quick Start

### 1. Navigate to the SearXNG directory

```bash
cd /path/to/creator-agent/docker/searxng
```

### 2. Generate a secret key

```bash
# Generate a random secret
export SEARXNG_SECRET=$(openssl rand -hex 32)
echo "SEARXNG_SECRET=$SEARXNG_SECRET" >> .env
```

### 3. Start the containers

```bash
docker-compose up -d
```

### 4. Verify it's running

```bash
# Check container status
docker-compose ps

# Test the health endpoint
curl http://localhost:8888/healthz

# Test a search (JSON API)
curl "http://localhost:8888/search?q=test&format=json" | jq .
```

## Configuration

### Docker Compose Settings

The `docker-compose.yml` configures:

| Setting | Value | Purpose |
|---------|-------|---------|
| Port | 127.0.0.1:8888 | Localhost only (security) |
| Memory limit | 512MB | Prevent runaway usage |
| CPU limit | 1.0 | Fair resource allocation |
| Redis cache | 64MB | Faster repeated queries |

### SearXNG Settings

The `settings.yml` configures:

| Setting | Value | Purpose |
|---------|-------|---------|
| JSON format | Enabled | API access for Clawdbot |
| Safe search | Off (0) | Can be changed per query |
| Image proxy | On | Privacy for image searches |
| Rate limiter | Off | Not needed for localhost |

### Enabled Search Engines

**General Search:**
- Google, Bing, DuckDuckGo, Brave, Qwant

**Knowledge:**
- Wikipedia, Wikidata

**Tech/Programming:**
- GitHub, Stack Overflow, Hacker News

**Academic:**
- arXiv, Semantic Scholar, Google Scholar, PubMed

**Media:**
- YouTube, Vimeo, Google Images, Bing Images

**News:**
- Google News, Bing News, Reddit

## Connecting Clawdbot

### Environment Variables

Add to your Clawdbot environment:

```bash
# SearXNG configuration
SEARXNG_URL=http://localhost:8888
SEARXNG_TIMEOUT=10
SEARXNG_MAX_RESULTS=20
```

### MCP Server Registration

Add to your Claude/Clawdbot MCP configuration:

```json
{
  "mcpServers": {
    "searxng": {
      "command": "python",
      "args": ["/path/to/creator-agent/skills/searxng/search.py", "--serve"],
      "env": {
        "SEARXNG_URL": "http://localhost:8888"
      }
    }
  }
}
```

### Direct Python Usage

```python
from skills.searxng.search import SearXNGClient

async def example():
    async with SearXNGClient() as client:
        # Basic search
        results = await client.search("python async tutorial")
        for r in results.results:
            print(f"{r.title}: {r.url}")

        # Category-specific search
        news = await client.search(
            "AI regulation",
            categories=["news"],
            max_results=10
        )

        # Research mode
        research = await client.research(
            "quantum computing",
            depth="thorough",
            include_academic=True
        )
```

### CLI Usage

```bash
# Basic search
python skills/searxng/search.py "python tutorial"

# Search with specific engines
python skills/searxng/search.py "async programming" -e google,stackoverflow

# Research mode
python skills/searxng/search.py "machine learning" -r --depth thorough

# Check health
python skills/searxng/search.py --health

# List available engines
python skills/searxng/search.py --engines-list
```

## API Reference

### Search Endpoint

```
GET http://localhost:8888/search
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| q | string | Search query (required) |
| format | string | Output format: `json`, `html`, `csv`, `rss` |
| categories | string | Comma-separated: `general`, `images`, `news`, etc. |
| engines | string | Comma-separated: `google`, `bing`, etc. |
| language | string | Language code: `en`, `es`, `fr`, etc. |
| safesearch | int | 0=off, 1=moderate, 2=strict |
| time_range | string | `day`, `week`, `month`, `year` |

**Example:**

```bash
curl "http://localhost:8888/search?q=python+async&format=json&categories=general,it&engines=google,stackoverflow"
```

**Response:**

```json
{
  "query": "python async",
  "results": [
    {
      "title": "Async IO in Python: A Complete Walkthrough",
      "url": "https://realpython.com/async-io-python/",
      "content": "Async IO is a concurrent programming design...",
      "engine": "google",
      "score": 1.0,
      "category": "general"
    }
  ],
  "number_of_results": 25,
  "answers": [],
  "infoboxes": [],
  "suggestions": ["python asyncio", "python async await"]
}
```

## Production Deployment

### Security Considerations

1. **Keep localhost-only binding** - The default config binds to `127.0.0.1:8888`. Do not expose to the internet.

2. **Use a reverse proxy** (if external access needed):
   ```nginx
   # Nginx example - add authentication!
   location /searxng/ {
       auth_basic "Restricted";
       auth_basic_user_file /etc/nginx/.htpasswd;
       proxy_pass http://127.0.0.1:8888/;
   }
   ```

3. **Set a strong secret key**:
   ```bash
   export SEARXNG_SECRET=$(openssl rand -hex 32)
   ```

### Resource Tuning

For high-volume usage, adjust `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # More CPU
      memory: 1024M    # More memory
```

### Monitoring

Check container logs:
```bash
docker-compose logs -f searxng
```

Check resource usage:
```bash
docker stats searxng searxng-redis
```

## Troubleshooting

### SearXNG not starting

```bash
# Check logs
docker-compose logs searxng

# Verify settings.yml syntax
python -c "import yaml; yaml.safe_load(open('settings.yml'))"
```

### No search results

1. Check if engines are working:
   ```bash
   curl "http://localhost:8888/search?q=test&format=json&engines=duckduckgo"
   ```

2. Some engines may be rate-limited. Try different engines.

3. Check for network issues:
   ```bash
   docker exec searxng ping google.com
   ```

### Slow searches

1. Enable Redis caching (already configured)
2. Reduce number of engines per query
3. Increase timeout in settings

### JSON API not working

Verify `formats` section in `settings.yml` includes `json`:
```yaml
formats:
  - html
  - json  # Must be present
```

## Maintenance

### Update SearXNG

```bash
cd /path/to/creator-agent/docker/searxng
docker-compose pull
docker-compose up -d
```

### Backup configuration

```bash
cp settings.yml settings.yml.backup
cp docker-compose.yml docker-compose.yml.backup
```

### View metrics

If metrics are enabled:
```bash
curl http://localhost:8888/stats
```

## Integration with Life OS

SearXNG integrates with the Life OS content creation workflow:

1. **Research Phase**: Use `/research` command for comprehensive topic research
2. **Content Creation**: Search results feed into content briefs
3. **Fact Checking**: Verify claims with multi-engine searches
4. **Trend Monitoring**: Track topics with news category searches

Example workflow:
```
User: Research sustainable packaging trends for a blog post

Clawdbot:
1. Runs searxng_research("sustainable packaging trends", depth="comprehensive")
2. Aggregates results from Google, Bing, news sources, and academic papers
3. Creates structured research summary
4. Generates content brief with sources
```

## Support

- SearXNG Documentation: https://docs.searxng.org/
- SearXNG GitHub: https://github.com/searxng/searxng
- Instance List (public): https://searx.space/
