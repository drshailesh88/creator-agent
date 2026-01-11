"""Writer Agent - Handles content creation in multiple formats."""

from typing import Any, Dict, List, Optional
import logging
from datetime import datetime

from ...base.agent import BaseAgent, AgentTool, ResponseFormat


logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """
    Writer Agent for content creation.

    Supports multiple formats:
    - Blog posts with SEO optimization
    - Twitter threads
    - LinkedIn posts
    - Newsletter content
    - Academic writing

    Features:
    - Tone adjustment
    - SEO optimization for blogs
    - Thread creation for Twitter
    - Platform-specific formatting
    """

    SYSTEM_PROMPT = """You are an expert content writer with mastery across multiple formats and platforms.

Your capabilities include:
1. Writing engaging blog posts optimized for SEO
2. Creating compelling Twitter threads that drive engagement
3. Crafting professional LinkedIn content
4. Developing newsletter content that builds audience
5. Producing academic writing with proper citations

Writing principles:
- Adapt tone and style to the target audience
- Use clear, concise language
- Structure content for readability
- Include relevant hooks and calls-to-action
- Optimize for the specific platform's best practices

For each format, consider:
- Blog: SEO keywords, headers, meta descriptions, readability
- Twitter: Thread hooks, character limits, engagement tactics
- LinkedIn: Professional tone, industry relevance, networking value
- Newsletter: Personal voice, value delivery, subscriber retention
- Academic: Formal tone, citations, methodology, objectivity"""

    # Supported content formats
    FORMATS = ["blog", "twitter", "linkedin", "newsletter", "academic"]

    # Tone options
    TONES = [
        "professional", "casual", "friendly", "authoritative",
        "conversational", "formal", "humorous", "inspirational"
    ]

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
        """Initialize writing tools."""

        # Format Content Tool
        self.register_tool(AgentTool(
            name="format_content",
            description="Format content for a specific platform",
            func=self._format_content,
            parameters={
                "content": {
                    "type": "string",
                    "description": "Raw content to format"
                },
                "format": {
                    "type": "string",
                    "description": "Target format: blog, twitter, linkedin, newsletter, academic"
                },
                "options": {
                    "type": "object",
                    "description": "Format-specific options"
                }
            },
            required_params=["content", "format"]
        ))

        # Adjust Tone Tool
        self.register_tool(AgentTool(
            name="adjust_tone",
            description="Adjust the tone of content",
            func=self._adjust_tone,
            parameters={
                "content": {
                    "type": "string",
                    "description": "Content to adjust"
                },
                "target_tone": {
                    "type": "string",
                    "description": "Target tone: professional, casual, friendly, etc."
                }
            },
            required_params=["content", "target_tone"]
        ))

        # SEO Optimize Tool
        self.register_tool(AgentTool(
            name="seo_optimize",
            description="Optimize content for SEO",
            func=self._seo_optimize,
            parameters={
                "content": {
                    "type": "string",
                    "description": "Content to optimize"
                },
                "keywords": {
                    "type": "array",
                    "description": "Target keywords"
                },
                "meta_description": {
                    "type": "boolean",
                    "description": "Generate meta description",
                    "default": True
                }
            },
            required_params=["content"]
        ))

        # Create Thread Tool
        self.register_tool(AgentTool(
            name="create_thread",
            description="Create a Twitter thread from content",
            func=self._create_thread,
            parameters={
                "content": {
                    "type": "string",
                    "description": "Content to convert to thread"
                },
                "max_tweets": {
                    "type": "integer",
                    "description": "Maximum number of tweets",
                    "default": 10
                },
                "include_hook": {
                    "type": "boolean",
                    "description": "Include an engaging first tweet",
                    "default": True
                }
            },
            required_params=["content"]
        ))

        # Generate Outline Tool
        self.register_tool(AgentTool(
            name="generate_outline",
            description="Generate an outline for long-form content",
            func=self._generate_outline,
            parameters={
                "topic": {
                    "type": "string",
                    "description": "Topic for the outline"
                },
                "format": {
                    "type": "string",
                    "description": "Content format"
                },
                "depth": {
                    "type": "integer",
                    "description": "Outline depth (levels)",
                    "default": 3
                }
            },
            required_params=["topic"]
        ))

    def _initialize_prompts(self) -> None:
        """Initialize prompt templates."""

        self.register_prompt_template(
            "blog_post",
            """Write a comprehensive blog post on the following topic:

Topic: {topic}
Target Keywords: {keywords}
Tone: {tone}
Target Length: {length} words

Structure the post with:
1. An engaging headline
2. A compelling introduction with a hook
3. Well-organized body sections with H2/H3 headers
4. Practical examples or case studies
5. A conclusion with a call-to-action

Additional context:
{context}"""
        )

        self.register_prompt_template(
            "twitter_thread",
            """Create an engaging Twitter thread on:

Topic: {topic}
Tone: {tone}
Max Tweets: {max_tweets}

Requirements:
1. First tweet should be a hook that stops scrolling
2. Each tweet should be under 280 characters
3. Include relevant data points or insights
4. End with a call-to-action or question
5. Consider adding numbered tweets (1/, 2/, etc.)

Context:
{context}"""
        )

        self.register_prompt_template(
            "linkedin_post",
            """Write a LinkedIn post about:

Topic: {topic}
Tone: {tone}
Purpose: {purpose}

Guidelines:
1. Start with an attention-grabbing first line
2. Use short paragraphs and line breaks for readability
3. Include a professional insight or lesson
4. Add a question to encourage engagement
5. Keep under 1300 characters for optimal engagement

Context:
{context}"""
        )

        self.register_prompt_template(
            "newsletter",
            """Write a newsletter segment about:

Topic: {topic}
Audience: {audience}
Tone: {tone}

Include:
1. A compelling subject line hook
2. Personal greeting
3. Main content with clear value
4. Relevant links or resources
5. Sign-off with personality

Context:
{context}"""
        )

        self.register_prompt_template(
            "academic",
            """Write an academic piece on:

Topic: {topic}
Type: {type}
Citation Style: {citation_style}

Requirements:
1. Formal academic tone
2. Clear thesis statement
3. Evidence-based arguments
4. Proper structure (intro, body, conclusion)
5. Placeholder for citations [Author, Year]

Context:
{context}"""
        )

    async def _format_content(
        self,
        content: str,
        format: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format content for a specific platform."""
        options = options or {}

        formatters = {
            "blog": self._format_blog,
            "twitter": self._format_twitter,
            "linkedin": self._format_linkedin,
            "newsletter": self._format_newsletter,
            "academic": self._format_academic
        }

        formatter = formatters.get(format, self._format_blog)
        return await formatter(content, options)

    async def _format_blog(
        self,
        content: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format content as a blog post."""
        return {
            "format": "blog",
            "content": content,
            "word_count": len(content.split()),
            "suggested_headers": [],
            "seo_ready": False,
            "status": "formatted"
        }

    async def _format_twitter(
        self,
        content: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format content as Twitter thread."""
        # Split into tweet-sized chunks
        max_length = 280
        words = content.split()
        tweets = []
        current_tweet = ""

        for word in words:
            if len(current_tweet) + len(word) + 1 <= max_length:
                current_tweet += (" " if current_tweet else "") + word
            else:
                if current_tweet:
                    tweets.append(current_tweet)
                current_tweet = word

        if current_tweet:
            tweets.append(current_tweet)

        return {
            "format": "twitter",
            "thread": tweets,
            "tweet_count": len(tweets),
            "status": "formatted"
        }

    async def _format_linkedin(
        self,
        content: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format content for LinkedIn."""
        # LinkedIn optimal length is under 1300 chars
        formatted = content[:1300] if len(content) > 1300 else content

        return {
            "format": "linkedin",
            "content": formatted,
            "character_count": len(formatted),
            "truncated": len(content) > 1300,
            "status": "formatted"
        }

    async def _format_newsletter(
        self,
        content: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format content for newsletter."""
        return {
            "format": "newsletter",
            "content": content,
            "sections": [],
            "status": "formatted"
        }

    async def _format_academic(
        self,
        content: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format content for academic writing."""
        citation_style = options.get("citation_style", "APA")

        return {
            "format": "academic",
            "content": content,
            "citation_style": citation_style,
            "citations_needed": [],
            "status": "formatted"
        }

    async def _adjust_tone(
        self,
        content: str,
        target_tone: str
    ) -> Dict[str, Any]:
        """Adjust the tone of content."""
        logger.info(f"Adjusting tone to: {target_tone}")

        # In production, this would use LLM to rewrite
        return {
            "original_content": content,
            "adjusted_content": content,  # Would be modified by LLM
            "target_tone": target_tone,
            "status": "mock_response",
            "message": "Tone adjustment would be done by LLM in production."
        }

    async def _seo_optimize(
        self,
        content: str,
        keywords: Optional[List[str]] = None,
        meta_description: bool = True
    ) -> Dict[str, Any]:
        """Optimize content for SEO."""
        keywords = keywords or []
        logger.info(f"SEO optimizing for keywords: {keywords}")

        word_count = len(content.split())

        return {
            "original_content": content,
            "optimized_content": content,  # Would be modified by LLM
            "keywords": keywords,
            "keyword_density": {},
            "meta_description": "" if meta_description else None,
            "seo_score": 0,
            "recommendations": [
                "Add target keywords to headers",
                "Include keywords in first paragraph",
                "Add internal and external links",
                "Optimize images with alt text",
                "Ensure proper header hierarchy"
            ],
            "word_count": word_count,
            "status": "mock_response"
        }

    async def _create_thread(
        self,
        content: str,
        max_tweets: int = 10,
        include_hook: bool = True
    ) -> Dict[str, Any]:
        """Create a Twitter thread from content."""
        logger.info(f"Creating thread with max {max_tweets} tweets")

        # Basic thread creation
        formatted = await self._format_twitter(content, {})
        tweets = formatted["thread"][:max_tweets]

        if include_hook and tweets:
            tweets[0] = f"THREAD: {tweets[0]}" if not tweets[0].startswith("THREAD") else tweets[0]

        # Number the tweets
        numbered_tweets = [
            f"{i+1}/{len(tweets)} {tweet}" if i > 0 else tweet
            for i, tweet in enumerate(tweets)
        ]

        return {
            "thread": numbered_tweets,
            "tweet_count": len(numbered_tweets),
            "has_hook": include_hook,
            "engagement_tips": [
                "Post during peak hours (9-11am, 7-9pm)",
                "Reply to your own thread to boost visibility",
                "Add relevant images or media",
                "End with a question to encourage replies"
            ],
            "status": "created"
        }

    async def _generate_outline(
        self,
        topic: str,
        format: str = "blog",
        depth: int = 3
    ) -> Dict[str, Any]:
        """Generate an outline for content."""
        logger.info(f"Generating {format} outline for: {topic}")

        # Generic outline structure
        outline = {
            "topic": topic,
            "format": format,
            "structure": [
                {
                    "level": 1,
                    "title": "Introduction",
                    "subsections": [
                        {"level": 2, "title": "Hook/Opening"},
                        {"level": 2, "title": "Context/Background"},
                        {"level": 2, "title": "Thesis/Main Point"}
                    ]
                },
                {
                    "level": 1,
                    "title": "Main Body",
                    "subsections": [
                        {"level": 2, "title": "Point 1"},
                        {"level": 2, "title": "Point 2"},
                        {"level": 2, "title": "Point 3"}
                    ]
                },
                {
                    "level": 1,
                    "title": "Conclusion",
                    "subsections": [
                        {"level": 2, "title": "Summary"},
                        {"level": 2, "title": "Call to Action"}
                    ]
                }
            ],
            "status": "generated"
        }

        return outline

    async def _process(
        self,
        task: str,
        content: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process writing task."""
        self._last_tools_used = []

        # Get parameters
        format_type = context.get("format", "blog")
        tone = context.get("tone", "professional")
        keywords = context.get("keywords", [])

        result = {
            "task": task,
            "format": format_type,
            "tone": tone,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Generate content based on format
        if format_type == "blog":
            self._last_tools_used.extend(["generate_outline", "format_content", "seo_optimize"])
            result["content"] = await self._generate_blog_content(content, tone, keywords, context)

        elif format_type == "twitter":
            self._last_tools_used.extend(["create_thread"])
            thread_result = await self._create_thread(content)
            result["content"] = thread_result

        elif format_type == "linkedin":
            self._last_tools_used.extend(["format_content", "adjust_tone"])
            result["content"] = await self._generate_linkedin_content(content, tone, context)

        elif format_type == "newsletter":
            self._last_tools_used.extend(["format_content"])
            result["content"] = await self._generate_newsletter_content(content, tone, context)

        elif format_type == "academic":
            self._last_tools_used.extend(["generate_outline", "format_content"])
            result["content"] = await self._generate_academic_content(content, context)

        else:
            result["content"] = await self._format_content(content, format_type)

        return result

    async def _generate_blog_content(
        self,
        topic: str,
        tone: str,
        keywords: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate blog content with SEO optimization."""
        outline = await self._generate_outline(topic, "blog")

        return {
            "type": "blog",
            "topic": topic,
            "tone": tone,
            "outline": outline,
            "suggested_title": f"Complete Guide to {topic}",
            "meta_description": f"Discover everything you need to know about {topic}. Expert insights, tips, and actionable advice.",
            "keywords": keywords,
            "estimated_read_time": "5-7 minutes",
            "body": "",  # Would be generated by LLM
            "status": "outline_ready",
            "message": "Full content would be generated by LLM in production."
        }

    async def _generate_linkedin_content(
        self,
        topic: str,
        tone: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate LinkedIn post content."""
        return {
            "type": "linkedin",
            "topic": topic,
            "tone": tone,
            "hook": f"Here's something I've learned about {topic}...",
            "body": "",  # Would be generated by LLM
            "cta": "What's your experience with this? Drop a comment below.",
            "hashtag_suggestions": ["#leadership", "#growth", "#learning"],
            "optimal_posting_times": ["Tuesday 10am", "Wednesday 9am", "Thursday 2pm"],
            "status": "template_ready"
        }

    async def _generate_newsletter_content(
        self,
        topic: str,
        tone: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate newsletter content."""
        return {
            "type": "newsletter",
            "topic": topic,
            "tone": tone,
            "subject_line_options": [
                f"The truth about {topic}",
                f"What I wish I knew about {topic}",
                f"3 insights on {topic} you can't ignore"
            ],
            "preview_text": f"This week, we're diving deep into {topic}...",
            "sections": [
                {"name": "Main Story", "content": ""},
                {"name": "Quick Tips", "content": ""},
                {"name": "Resource of the Week", "content": ""}
            ],
            "status": "template_ready"
        }

    async def _generate_academic_content(
        self,
        topic: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate academic content."""
        citation_style = context.get("citation_style", "APA")

        return {
            "type": "academic",
            "topic": topic,
            "citation_style": citation_style,
            "outline": await self._generate_outline(topic, "academic"),
            "abstract": "",  # Would be generated
            "sections": [
                "Introduction",
                "Literature Review",
                "Methodology",
                "Results",
                "Discussion",
                "Conclusion",
                "References"
            ],
            "status": "outline_ready"
        }
