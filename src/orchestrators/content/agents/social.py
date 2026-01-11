"""Social Media Agent - Handles platform-specific content optimization."""

from typing import Any, Dict, List, Optional
import logging
import re
from datetime import datetime

from ...base.agent import BaseAgent, AgentTool, ResponseFormat


logger = logging.getLogger(__name__)


class SocialAgent(BaseAgent):
    """
    Social Media Agent for platform-specific content optimization.

    Capabilities:
    - Platform-specific formatting
    - Hashtag generation and optimization
    - Engagement optimization
    - Posting schedule recommendations
    - A/B testing suggestions
    """

    SYSTEM_PROMPT = """You are an expert social media strategist specializing in content optimization across platforms.

Your capabilities include:
1. Formatting content for specific platforms (Twitter, LinkedIn, Instagram, TikTok, Facebook)
2. Generating effective hashtags based on trends and relevance
3. Optimizing content for maximum engagement
4. Recommending posting schedules
5. Creating A/B test variations

Platform expertise:
- Twitter/X: Thread creation, hooks, character optimization, trending topics
- LinkedIn: Professional tone, thought leadership, B2B engagement
- Instagram: Visual-first content, Reels scripts, Story sequences, hashtag strategy
- TikTok: Hook-driven scripts, trends, audio suggestions
- Facebook: Community building, longer form content, group engagement

Optimization principles:
- Platform-native content performs best
- First 3 seconds/lines are crucial for retention
- CTAs should be clear and actionable
- Hashtags should balance reach and relevance
- Timing matters for engagement"""

    # Platform specifications
    PLATFORMS = {
        "twitter": {
            "max_chars": 280,
            "max_hashtags": 3,
            "supports_threads": True,
            "media_types": ["image", "video", "gif", "poll"]
        },
        "linkedin": {
            "max_chars": 3000,
            "max_hashtags": 5,
            "supports_threads": False,
            "media_types": ["image", "video", "document", "poll"]
        },
        "instagram": {
            "max_chars": 2200,
            "max_hashtags": 30,
            "supports_threads": False,
            "media_types": ["image", "video", "reel", "story", "carousel"]
        },
        "tiktok": {
            "max_chars": 2200,
            "max_hashtags": 5,
            "supports_threads": False,
            "media_types": ["video"]
        },
        "facebook": {
            "max_chars": 63206,
            "max_hashtags": 3,
            "supports_threads": False,
            "media_types": ["image", "video", "link", "poll", "event"]
        }
    }

    def __init__(
        self,
        model: str = "glm-4",
        model_config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            model=model,
            model_config=model_config,
            response_format=ResponseFormat.JSON
        )
        self._last_tools_used: List[str] = []

    def _initialize_tools(self) -> None:
        """Initialize social media tools."""

        # Platform Formatter
        self.register_tool(AgentTool(
            name="format_for_platform",
            description="Format content for a specific social media platform",
            func=self._format_for_platform,
            parameters={
                "content": {
                    "type": "string",
                    "description": "Content to format"
                },
                "platform": {
                    "type": "string",
                    "description": "Target platform: twitter, linkedin, instagram, tiktok, facebook"
                },
                "options": {
                    "type": "object",
                    "description": "Platform-specific options"
                }
            },
            required_params=["content", "platform"]
        ))

        # Hashtag Generator
        self.register_tool(AgentTool(
            name="generate_hashtags",
            description="Generate relevant hashtags for content",
            func=self._generate_hashtags,
            parameters={
                "content": {
                    "type": "string",
                    "description": "Content to generate hashtags for"
                },
                "platform": {
                    "type": "string",
                    "description": "Target platform"
                },
                "max_hashtags": {
                    "type": "integer",
                    "description": "Maximum number of hashtags",
                    "default": 10
                },
                "include_trending": {
                    "type": "boolean",
                    "description": "Include trending hashtags",
                    "default": True
                }
            },
            required_params=["content"]
        ))

        # Engagement Optimizer
        self.register_tool(AgentTool(
            name="optimize_engagement",
            description="Optimize content for maximum engagement",
            func=self._optimize_engagement,
            parameters={
                "content": {
                    "type": "string",
                    "description": "Content to optimize"
                },
                "platform": {
                    "type": "string",
                    "description": "Target platform"
                },
                "goal": {
                    "type": "string",
                    "description": "Primary goal: awareness, engagement, conversion",
                    "default": "engagement"
                }
            },
            required_params=["content", "platform"]
        ))

        # Schedule Recommender
        self.register_tool(AgentTool(
            name="recommend_schedule",
            description="Recommend optimal posting schedule",
            func=self._recommend_schedule,
            parameters={
                "platform": {
                    "type": "string",
                    "description": "Target platform"
                },
                "content_type": {
                    "type": "string",
                    "description": "Type of content"
                },
                "timezone": {
                    "type": "string",
                    "description": "User's timezone",
                    "default": "UTC"
                },
                "audience": {
                    "type": "string",
                    "description": "Target audience type: b2b, b2c, general",
                    "default": "general"
                }
            },
            required_params=["platform"]
        ))

        # A/B Variation Generator
        self.register_tool(AgentTool(
            name="generate_ab_variations",
            description="Generate A/B test variations of content",
            func=self._generate_ab_variations,
            parameters={
                "content": {
                    "type": "string",
                    "description": "Original content"
                },
                "num_variations": {
                    "type": "integer",
                    "description": "Number of variations to generate",
                    "default": 3
                },
                "vary_elements": {
                    "type": "array",
                    "description": "Elements to vary: hook, cta, tone, length",
                    "default": ["hook", "cta"]
                }
            },
            required_params=["content"]
        ))

        # Cross-Platform Adapter
        self.register_tool(AgentTool(
            name="adapt_cross_platform",
            description="Adapt content for multiple platforms",
            func=self._adapt_cross_platform,
            parameters={
                "content": {
                    "type": "string",
                    "description": "Source content"
                },
                "source_platform": {
                    "type": "string",
                    "description": "Original platform"
                },
                "target_platforms": {
                    "type": "array",
                    "description": "Platforms to adapt for"
                }
            },
            required_params=["content", "target_platforms"]
        ))

    def _initialize_prompts(self) -> None:
        """Initialize prompt templates."""

        self.register_prompt_template(
            "twitter_optimization",
            """Optimize this content for Twitter/X:

Original Content: {content}

Requirements:
- Under 280 characters per tweet
- Create a thread if needed ({max_tweets} tweets max)
- Start with an attention-grabbing hook
- Include relevant hashtags (max 3)
- End with engagement prompt

Goal: {goal}
Tone: {tone}"""
        )

        self.register_prompt_template(
            "linkedin_optimization",
            """Optimize this content for LinkedIn:

Original Content: {content}

Requirements:
- Professional tone
- Strong opening line (visible before "see more")
- Use line breaks for readability
- Include a question or CTA for engagement
- Add 3-5 relevant hashtags

Goal: {goal}
Industry: {industry}"""
        )

        self.register_prompt_template(
            "instagram_optimization",
            """Optimize this content for Instagram:

Original Content: {content}

Requirements:
- Compelling first line (hook)
- Use emojis appropriately
- Include call-to-action
- Suggest relevant hashtags (up to 30)
- Consider carousel or reel format

Content Type: {content_type}
Goal: {goal}"""
        )

        self.register_prompt_template(
            "hashtag_strategy",
            """Generate a hashtag strategy for:

Content: {content}
Platform: {platform}
Niche: {niche}

Provide:
1. High-volume hashtags (broad reach)
2. Medium-volume hashtags (balanced)
3. Niche hashtags (targeted)
4. Branded hashtags (if applicable)

Max hashtags: {max_hashtags}"""
        )

    async def _format_for_platform(
        self,
        content: str,
        platform: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format content for a specific platform."""
        logger.info(f"Formatting content for {platform}")

        options = options or {}
        platform_spec = self.PLATFORMS.get(platform, self.PLATFORMS["twitter"])

        formatters = {
            "twitter": self._format_twitter,
            "linkedin": self._format_linkedin,
            "instagram": self._format_instagram,
            "tiktok": self._format_tiktok,
            "facebook": self._format_facebook
        }

        formatter = formatters.get(platform, self._format_twitter)
        return await formatter(content, platform_spec, options)

    async def _format_twitter(
        self,
        content: str,
        spec: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format content for Twitter."""
        max_chars = spec["max_chars"]

        # Check if thread is needed
        if len(content) > max_chars:
            # Split into thread
            tweets = self._split_into_tweets(content, max_chars)
            return {
                "platform": "twitter",
                "format": "thread",
                "tweets": tweets,
                "tweet_count": len(tweets),
                "total_characters": sum(len(t) for t in tweets),
                "has_hook": True,
                "suggested_media": "Consider adding images or GIFs for better engagement"
            }

        return {
            "platform": "twitter",
            "format": "single",
            "content": content,
            "character_count": len(content),
            "within_limit": len(content) <= max_chars,
            "remaining_chars": max_chars - len(content)
        }

    def _split_into_tweets(self, content: str, max_chars: int = 280) -> List[str]:
        """Split content into tweet-sized chunks."""
        words = content.split()
        tweets = []
        current_tweet = ""

        # Reserve space for numbering (e.g., "1/10 ")
        effective_max = max_chars - 6

        for word in words:
            if len(current_tweet) + len(word) + 1 <= effective_max:
                current_tweet += (" " if current_tweet else "") + word
            else:
                if current_tweet:
                    tweets.append(current_tweet)
                current_tweet = word

        if current_tweet:
            tweets.append(current_tweet)

        # Add numbering
        total = len(tweets)
        numbered_tweets = [
            f"{i+1}/{total} {tweet}" for i, tweet in enumerate(tweets)
        ]

        return numbered_tweets

    async def _format_linkedin(
        self,
        content: str,
        spec: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format content for LinkedIn."""
        # LinkedIn shows ~210 chars before "see more"
        hook_length = 210

        # Add line breaks for readability
        paragraphs = content.split(". ")
        formatted_content = "\n\n".join(
            ". ".join(paragraphs[i:i+2]) for i in range(0, len(paragraphs), 2)
        )

        return {
            "platform": "linkedin",
            "content": formatted_content,
            "character_count": len(formatted_content),
            "within_limit": len(formatted_content) <= spec["max_chars"],
            "hook": content[:hook_length] if len(content) > hook_length else content,
            "hook_quality": "strong" if content[:50].endswith(("?", "!", ":")) else "moderate",
            "formatting_tips": [
                "Use line breaks between paragraphs",
                "Start with a bold statement or question",
                "Add a question at the end for engagement",
                "Include 3-5 hashtags at the bottom"
            ]
        }

    async def _format_instagram(
        self,
        content: str,
        spec: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format content for Instagram."""
        content_type = options.get("content_type", "post")

        return {
            "platform": "instagram",
            "content_type": content_type,
            "caption": content,
            "character_count": len(content),
            "within_limit": len(content) <= spec["max_chars"],
            "suggested_format": "carousel" if len(content) > 500 else "single_image",
            "formatting_tips": [
                "Use emojis to break up text",
                "Put most important info first",
                "Use line breaks for readability",
                "End with a question or CTA",
                "Save hashtags for first comment or end"
            ]
        }

    async def _format_tiktok(
        self,
        content: str,
        spec: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format content for TikTok."""
        return {
            "platform": "tiktok",
            "caption": content[:spec["max_chars"]],
            "character_count": len(content),
            "video_script_suggestion": {
                "hook": "First 3 seconds are crucial - lead with the most interesting point",
                "body": "Keep energy high, use jump cuts, maintain fast pace",
                "cta": "End with a clear call-to-action"
            },
            "trending_audio_tip": "Check trending sounds in your niche for better reach",
            "hashtag_limit": spec["max_hashtags"]
        }

    async def _format_facebook(
        self,
        content: str,
        spec: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format content for Facebook."""
        return {
            "platform": "facebook",
            "content": content,
            "character_count": len(content),
            "within_limit": True,  # Facebook has high limit
            "suggested_format": "text_with_image",
            "engagement_tips": [
                "Ask a question to encourage comments",
                "Tag relevant pages or people",
                "Consider Facebook Groups for niche audiences",
                "Use 1-3 hashtags maximum"
            ]
        }

    async def _generate_hashtags(
        self,
        content: str,
        platform: str = "instagram",
        max_hashtags: int = 10,
        include_trending: bool = True
    ) -> Dict[str, Any]:
        """Generate hashtags for content."""
        logger.info(f"Generating hashtags for {platform}")

        # Extract key topics from content
        words = re.findall(r'\b\w+\b', content.lower())
        # Filter common words
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'to',
                     'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
                     'into', 'through', 'during', 'before', 'after', 'above',
                     'below', 'between', 'under', 'again', 'further', 'then',
                     'once', 'here', 'there', 'when', 'where', 'why', 'how',
                     'all', 'each', 'few', 'more', 'most', 'other', 'some',
                     'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
                     'than', 'too', 'very', 'just', 'and', 'but', 'or', 'if',
                     'because', 'until', 'while', 'this', 'that', 'these',
                     'those', 'what', 'which', 'who', 'whom', 'whose', 'i',
                     'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
                     'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their'}

        keywords = [w for w in words if w not in stopwords and len(w) > 3]

        # Generate hashtag categories
        hashtags = {
            "high_volume": [],
            "medium_volume": [],
            "niche": [],
            "trending": []
        }

        # Create hashtags from keywords
        for keyword in keywords[:5]:
            hashtags["niche"].append(f"#{keyword}")
            hashtags["medium_volume"].append(f"#{keyword}tips")

        # Add generic high-volume hashtags based on platform
        if platform == "instagram":
            hashtags["high_volume"] = ["#instagood", "#photooftheday", "#instadaily"]
        elif platform == "linkedin":
            hashtags["high_volume"] = ["#leadership", "#innovation", "#growth"]
        elif platform == "twitter":
            hashtags["high_volume"] = ["#trending", "#viral"]
        elif platform == "tiktok":
            hashtags["high_volume"] = ["#fyp", "#foryou", "#viral"]

        # Flatten and limit
        all_hashtags = (
            hashtags["high_volume"][:3] +
            hashtags["medium_volume"][:4] +
            hashtags["niche"][:3]
        )[:max_hashtags]

        return {
            "platform": platform,
            "hashtags": all_hashtags,
            "hashtag_count": len(all_hashtags),
            "categories": hashtags,
            "strategy": {
                "high_volume": "Broad reach, high competition",
                "medium_volume": "Balanced reach and relevance",
                "niche": "Targeted audience, lower competition"
            },
            "recommendations": [
                f"Use {self.PLATFORMS[platform]['max_hashtags']} hashtags max for {platform}",
                "Mix high-volume and niche hashtags",
                "Track which hashtags perform best",
                "Update hashtags regularly based on trends"
            ],
            "status": "generated"
        }

    async def _optimize_engagement(
        self,
        content: str,
        platform: str,
        goal: str = "engagement"
    ) -> Dict[str, Any]:
        """Optimize content for maximum engagement."""
        logger.info(f"Optimizing for {goal} on {platform}")

        # Analyze current content
        has_question = "?" in content
        has_cta = any(cta in content.lower() for cta in
                      ["click", "tap", "comment", "share", "follow", "subscribe",
                       "learn more", "check out", "link in bio"])
        has_emoji = bool(re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]', content))

        word_count = len(content.split())

        # Generate recommendations
        recommendations = []
        if not has_question:
            recommendations.append("Add a question to encourage comments")
        if not has_cta:
            recommendations.append("Include a clear call-to-action")
        if platform == "instagram" and not has_emoji:
            recommendations.append("Add emojis to increase visual appeal")
        if word_count > 100 and platform == "twitter":
            recommendations.append("Consider creating a thread for longer content")

        # Goal-specific optimizations
        goal_tips = {
            "awareness": [
                "Use broad, trending hashtags",
                "Create shareable content",
                "Tag relevant accounts",
                "Post during peak hours"
            ],
            "engagement": [
                "Ask open-ended questions",
                "Create polls or quizzes",
                "Respond to comments quickly",
                "Use controversial or thought-provoking hooks"
            ],
            "conversion": [
                "Include clear CTA",
                "Add urgency (limited time, exclusive)",
                "Highlight benefits over features",
                "Use social proof"
            ]
        }

        return {
            "platform": platform,
            "goal": goal,
            "analysis": {
                "has_question": has_question,
                "has_cta": has_cta,
                "has_emoji": has_emoji,
                "word_count": word_count
            },
            "engagement_score": self._calculate_engagement_score(
                has_question, has_cta, has_emoji, word_count, platform
            ),
            "recommendations": recommendations,
            "goal_specific_tips": goal_tips.get(goal, goal_tips["engagement"]),
            "optimized_hooks": [
                f"Here's what nobody tells you about {content[:50]}...",
                f"I tested this for 30 days. Here's what happened:",
                f"Stop scrolling. This will change how you think about {content[:30]}..."
            ],
            "cta_suggestions": [
                "Drop a if you agree",
                "Save this for later",
                "Tag someone who needs to see this",
                "What's your take? Comment below"
            ]
        }

    def _calculate_engagement_score(
        self,
        has_question: bool,
        has_cta: bool,
        has_emoji: bool,
        word_count: int,
        platform: str
    ) -> int:
        """Calculate estimated engagement score (0-100)."""
        score = 50  # Base score

        if has_question:
            score += 15
        if has_cta:
            score += 15
        if has_emoji and platform in ["instagram", "tiktok"]:
            score += 10

        # Optimal length bonus
        optimal_lengths = {
            "twitter": (100, 200),
            "linkedin": (150, 300),
            "instagram": (150, 400),
            "tiktok": (100, 200),
            "facebook": (100, 250)
        }

        min_len, max_len = optimal_lengths.get(platform, (100, 300))
        if min_len <= word_count <= max_len:
            score += 10

        return min(100, score)

    async def _recommend_schedule(
        self,
        platform: str,
        content_type: str = "post",
        timezone: str = "UTC",
        audience: str = "general"
    ) -> Dict[str, Any]:
        """Recommend optimal posting schedule."""
        logger.info(f"Recommending schedule for {platform}")

        # Best times by platform and audience
        schedules = {
            "twitter": {
                "b2b": ["9:00 AM", "12:00 PM", "5:00 PM"],
                "b2c": ["12:00 PM", "3:00 PM", "6:00 PM"],
                "general": ["9:00 AM", "12:00 PM", "3:00 PM", "6:00 PM"]
            },
            "linkedin": {
                "b2b": ["7:30 AM", "12:00 PM", "5:00 PM"],
                "b2c": ["12:00 PM", "5:00 PM"],
                "general": ["8:00 AM", "12:00 PM", "5:00 PM"]
            },
            "instagram": {
                "b2b": ["11:00 AM", "1:00 PM"],
                "b2c": ["11:00 AM", "2:00 PM", "7:00 PM"],
                "general": ["11:00 AM", "1:00 PM", "7:00 PM"]
            },
            "tiktok": {
                "b2b": ["9:00 AM", "12:00 PM"],
                "b2c": ["7:00 PM", "9:00 PM"],
                "general": ["12:00 PM", "7:00 PM", "9:00 PM"]
            },
            "facebook": {
                "b2b": ["9:00 AM", "1:00 PM"],
                "b2c": ["1:00 PM", "4:00 PM", "8:00 PM"],
                "general": ["9:00 AM", "1:00 PM", "4:00 PM"]
            }
        }

        best_days = {
            "twitter": ["Tuesday", "Wednesday", "Thursday"],
            "linkedin": ["Tuesday", "Wednesday", "Thursday"],
            "instagram": ["Monday", "Wednesday", "Friday"],
            "tiktok": ["Tuesday", "Thursday", "Friday"],
            "facebook": ["Wednesday", "Thursday", "Friday"]
        }

        platform_schedule = schedules.get(platform, schedules["twitter"])
        times = platform_schedule.get(audience, platform_schedule["general"])
        days = best_days.get(platform, ["Tuesday", "Wednesday", "Thursday"])

        return {
            "platform": platform,
            "audience": audience,
            "timezone": timezone,
            "best_times": times,
            "best_days": days,
            "optimal_frequency": {
                "twitter": "3-5 times per day",
                "linkedin": "1-2 times per day",
                "instagram": "1-2 times per day",
                "tiktok": "1-3 times per day",
                "facebook": "1-2 times per day"
            }.get(platform, "1-2 times per day"),
            "recommendations": [
                f"Post during {times[0]} for highest engagement",
                f"Focus on {', '.join(days[:2])} for best reach",
                "Test different times and track results",
                "Consider your audience's timezone"
            ],
            "avoid": {
                "times": ["Late night (11PM-6AM)", "Early morning weekends"],
                "days": ["Sunday" if platform == "linkedin" else "Saturday"]
            }
        }

    async def _generate_ab_variations(
        self,
        content: str,
        num_variations: int = 3,
        vary_elements: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate A/B test variations of content."""
        logger.info(f"Generating {num_variations} A/B variations")

        vary_elements = vary_elements or ["hook", "cta"]

        variations = []

        # Hook variations
        hook_templates = [
            "Here's something most people don't know: {}",
            "I've been thinking about this a lot: {}",
            "Unpopular opinion: {}",
            "The truth about {}: ",
            "What if I told you {}?"
        ]

        # CTA variations
        cta_templates = [
            "What do you think? Let me know in the comments.",
            "Agree or disagree? Drop your thoughts below.",
            "Save this for later.",
            "Share this with someone who needs to hear it.",
            "Follow for more insights like this."
        ]

        for i in range(num_variations):
            variation = {"id": chr(65 + i), "content": content}

            if "hook" in vary_elements:
                hook = hook_templates[i % len(hook_templates)]
                # Extract first sentence for hook modification
                first_sentence = content.split(".")[0] if "." in content else content[:100]
                variation["hook"] = hook.format(first_sentence.lower())

            if "cta" in vary_elements:
                variation["cta"] = cta_templates[i % len(cta_templates)]

            if "tone" in vary_elements:
                tones = ["professional", "casual", "enthusiastic"]
                variation["tone"] = tones[i % len(tones)]

            variations.append(variation)

        return {
            "original": content,
            "variations": variations,
            "num_variations": len(variations),
            "elements_varied": vary_elements,
            "testing_tips": [
                "Test one element at a time for clear results",
                "Run each variation for at least 24-48 hours",
                "Ensure similar posting times for fair comparison",
                "Track engagement rate, not just total engagement"
            ],
            "metrics_to_track": [
                "Engagement rate",
                "Click-through rate",
                "Share/retweet rate",
                "Comment quality",
                "Follower growth"
            ]
        }

    async def _adapt_cross_platform(
        self,
        content: str,
        source_platform: str = None,
        target_platforms: List[str] = None
    ) -> Dict[str, Any]:
        """Adapt content for multiple platforms."""
        target_platforms = target_platforms or ["twitter", "linkedin", "instagram"]
        logger.info(f"Adapting content for {target_platforms}")

        adaptations = {}

        for platform in target_platforms:
            formatted = await self._format_for_platform(content, platform)
            hashtags = await self._generate_hashtags(content, platform, max_hashtags=5)

            adaptations[platform] = {
                "formatted_content": formatted,
                "hashtags": hashtags["hashtags"],
                "posting_tips": formatted.get("formatting_tips", [])
            }

        return {
            "source_content": content,
            "source_platform": source_platform,
            "adaptations": adaptations,
            "platforms_covered": list(adaptations.keys()),
            "cross_posting_tips": [
                "Stagger posts by 1-2 hours across platforms",
                "Customize content for each platform's audience",
                "Use platform-native features when possible",
                "Track which platform performs best for this content type"
            ]
        }

    async def _process(
        self,
        task: str,
        content: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process social media task."""
        self._last_tools_used = []

        platform = context.get("platform", "twitter")
        goal = context.get("goal", "engagement")

        result = {
            "task": task,
            "platform": platform,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Format for platform
        self._last_tools_used.append("format_for_platform")
        formatted = await self._format_for_platform(content, platform, context)
        result["formatted"] = formatted

        # Generate hashtags
        self._last_tools_used.append("generate_hashtags")
        hashtags = await self._generate_hashtags(content, platform)
        result["hashtags"] = hashtags

        # Optimize for engagement
        self._last_tools_used.append("optimize_engagement")
        optimization = await self._optimize_engagement(content, platform, goal)
        result["optimization"] = optimization

        # Get schedule recommendations
        self._last_tools_used.append("recommend_schedule")
        schedule = await self._recommend_schedule(
            platform,
            audience=context.get("audience", "general")
        )
        result["schedule"] = schedule

        # Generate A/B variations if requested
        if context.get("generate_variations", False):
            self._last_tools_used.append("generate_ab_variations")
            variations = await self._generate_ab_variations(content)
            result["variations"] = variations

        # Cross-platform adaptation if requested
        if context.get("cross_platform"):
            self._last_tools_used.append("adapt_cross_platform")
            adaptations = await self._adapt_cross_platform(
                content,
                platform,
                context.get("target_platforms", ["twitter", "linkedin", "instagram"])
            )
            result["cross_platform"] = adaptations

        return result
