"""
Brain Dump Processor

Transforms unstructured thoughts into organized, actionable items.
Integrates with Notion for persistent storage.
"""

import os
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum
import re


class ItemCategory(Enum):
    """Categories for brain dump items."""

    TASK = "task"
    IDEA = "idea"
    FEELING = "feeling"
    QUESTION = "question"
    REMINDER = "reminder"
    GOAL = "goal"
    WORRY = "worry"
    GRATITUDE = "gratitude"
    OTHER = "other"


class Priority(Enum):
    """Priority levels for items."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass
class ProcessedItem:
    """A single processed item from a brain dump."""

    content: str
    category: ItemCategory
    priority: Priority = Priority.NONE
    context: str = ""
    suggested_action: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "content": self.content,
            "category": self.category.value,
            "priority": self.priority.value,
            "context": self.context,
            "suggested_action": self.suggested_action,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "tags": self.tags,
        }


@dataclass
class BrainDumpResult:
    """Result of processing a brain dump."""

    raw_input: str
    items: list[ProcessedItem]
    summary: str
    mood_detected: Optional[str] = None
    themes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    notion_page_id: Optional[str] = None

    # Warm, encouraging response templates
    RESPONSE_TEMPLATES = {
        "intro": [
            "I've gently sorted through your thoughts. Here's what I found:",
            "Let's bring some clarity to these thoughts together:",
            "Your mind had a lot to process. Here's the organized view:",
            "Thanks for sharing what's on your mind. Let me help organize:",
        ],
        "tasks_found": [
            "I noticed some things that might need action:",
            "Here are some items that seem actionable:",
            "These look like things you could tackle:",
        ],
        "feelings_acknowledged": [
            "I also heard some feelings in there - that's important too.",
            "It sounds like there's some emotional weight here. That's okay.",
            "I noticed some feelings coming through. Thanks for being honest with yourself.",
        ],
        "closing": [
            "Remember: you don't have to do everything at once. One step at a time.",
            "Take what's useful, leave what's not. You've got this.",
            "Now that it's out of your head, you can breathe a little easier.",
            "Your thoughts are valid. Now let's tackle them one by one.",
        ],
    }

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "raw_input": self.raw_input,
            "items": [item.to_dict() for item in self.items],
            "summary": self.summary,
            "mood_detected": self.mood_detected,
            "themes": self.themes,
            "created_at": self.created_at.isoformat(),
            "notion_page_id": self.notion_page_id,
        }

    def format_response(self) -> str:
        """Format a warm, encouraging response."""
        import random

        lines = []

        # Introduction
        lines.append(random.choice(self.RESPONSE_TEMPLATES["intro"]))
        lines.append("")

        # Summary
        if self.summary:
            lines.append(f"**Summary:** {self.summary}")
            lines.append("")

        # Themes
        if self.themes:
            lines.append(f"**Themes:** {', '.join(self.themes)}")
            lines.append("")

        # Group items by category
        tasks = [i for i in self.items if i.category == ItemCategory.TASK]
        feelings = [i for i in self.items if i.category == ItemCategory.FEELING]
        ideas = [i for i in self.items if i.category == ItemCategory.IDEA]
        other = [i for i in self.items if i.category not in
                 [ItemCategory.TASK, ItemCategory.FEELING, ItemCategory.IDEA]]

        # Tasks
        if tasks:
            lines.append(random.choice(self.RESPONSE_TEMPLATES["tasks_found"]))
            for task in tasks:
                priority_icon = {"high": "!", "medium": "-", "low": "~"}.get(
                    task.priority.value, ""
                )
                lines.append(f"  {priority_icon} {task.content}")
                if task.suggested_action:
                    lines.append(f"    -> {task.suggested_action}")
            lines.append("")

        # Ideas
        if ideas:
            lines.append("**Ideas to explore:**")
            for idea in ideas:
                lines.append(f"  - {idea.content}")
            lines.append("")

        # Feelings
        if feelings:
            lines.append(random.choice(self.RESPONSE_TEMPLATES["feelings_acknowledged"]))
            for feeling in feelings:
                lines.append(f"  - {feeling.content}")
            lines.append("")

        # Other items
        if other:
            lines.append("**Other thoughts:**")
            for item in other:
                lines.append(f"  - [{item.category.value}] {item.content}")
            lines.append("")

        # Closing
        lines.append(random.choice(self.RESPONSE_TEMPLATES["closing"]))

        return "\n".join(lines)


class NotionClient:
    """Client for Notion API integration."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        brain_dump_db: Optional[str] = None,
    ):
        """Initialize Notion client."""
        self.api_key = api_key or os.getenv("NOTION_API_KEY")
        self.brain_dump_db = brain_dump_db or os.getenv("NOTION_BRAIN_DUMP_DB")
        self.base_url = "https://api.notion.com/v1"

    async def create_brain_dump_page(
        self,
        result: BrainDumpResult,
    ) -> Optional[str]:
        """
        Create a Notion page for the brain dump.

        Args:
            result: The processed brain dump result

        Returns:
            Notion page ID if successful
        """
        if not self.api_key or not self.brain_dump_db:
            return None

        # TODO: Implement actual Notion API call
        # This is a stub that would create a page with:
        # - Title: "Brain Dump - {date}"
        # - Properties for mood, themes
        # - Content blocks for each item

        # For now, return a placeholder
        return f"notion_page_{result.created_at.strftime('%Y%m%d_%H%M%S')}"


class BrainDumpProcessor:
    """
    Processes unstructured thoughts into organized items.

    Uses pattern matching and NLP to categorize, prioritize,
    and suggest actions for stream-of-consciousness input.
    """

    # Patterns for detecting item types
    TASK_PATTERNS = [
        r"\bneed to\b",
        r"\bhave to\b",
        r"\bshould\b",
        r"\bmust\b",
        r"\bremember to\b",
        r"\bdon't forget\b",
        r"\bTODO\b",
        r"\bcall\b",
        r"\bemail\b",
        r"\bbuy\b",
        r"\bfinish\b",
        r"\bcomplete\b",
    ]

    FEELING_PATTERNS = [
        r"\bfeeling\b",
        r"\bfeel\b",
        r"\bstressed\b",
        r"\banxious\b",
        r"\bhappy\b",
        r"\bsad\b",
        r"\bworried\b",
        r"\bexcited\b",
        r"\bfrustrated\b",
        r"\boverwhelmed\b",
    ]

    IDEA_PATTERNS = [
        r"\bmaybe\b",
        r"\bwhat if\b",
        r"\bcould\b",
        r"\bidea\b",
        r"\bperhaps\b",
        r"\bwonder\b",
    ]

    URGENCY_PATTERNS = [
        r"\burgent\b",
        r"\bASAP\b",
        r"\bimmediately\b",
        r"\btoday\b",
        r"\bdeadline\b",
        r"\bdue\b",
    ]

    def __init__(
        self,
        notion_api_key: Optional[str] = None,
        notion_db_id: Optional[str] = None,
    ):
        """
        Initialize the brain dump processor.

        Args:
            notion_api_key: Notion API key for storage
            notion_db_id: Notion database ID for brain dumps
        """
        self.notion = NotionClient(
            api_key=notion_api_key,
            brain_dump_db=notion_db_id,
        )

    def _detect_category(self, text: str) -> ItemCategory:
        """Detect the category of a text segment."""
        text_lower = text.lower()

        # Check patterns in order of specificity
        for pattern in self.TASK_PATTERNS:
            if re.search(pattern, text_lower):
                return ItemCategory.TASK

        for pattern in self.FEELING_PATTERNS:
            if re.search(pattern, text_lower):
                return ItemCategory.FEELING

        for pattern in self.IDEA_PATTERNS:
            if re.search(pattern, text_lower):
                return ItemCategory.IDEA

        # Default categorization based on punctuation
        if text.strip().endswith("?"):
            return ItemCategory.QUESTION

        return ItemCategory.OTHER

    def _detect_priority(self, text: str) -> Priority:
        """Detect the priority level of a text segment."""
        text_lower = text.lower()

        for pattern in self.URGENCY_PATTERNS:
            if re.search(pattern, text_lower):
                return Priority.HIGH

        # Medium priority indicators
        if any(word in text_lower for word in ["soon", "this week", "important"]):
            return Priority.MEDIUM

        return Priority.NONE

    def _extract_themes(self, text: str) -> list[str]:
        """Extract main themes from the brain dump."""
        themes = []
        text_lower = text.lower()

        theme_keywords = {
            "work": ["work", "project", "meeting", "deadline", "boss", "colleague"],
            "health": ["exercise", "gym", "health", "doctor", "sleep", "tired"],
            "relationships": ["family", "friend", "mom", "dad", "partner", "call"],
            "finances": ["money", "pay", "bill", "budget", "save", "buy"],
            "personal growth": ["learn", "read", "improve", "goal", "habit"],
            "home": ["home", "house", "clean", "groceries", "cook"],
        }

        for theme, keywords in theme_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                themes.append(theme)

        return themes

    def _detect_mood(self, text: str) -> Optional[str]:
        """Detect overall mood from the brain dump."""
        text_lower = text.lower()

        mood_indicators = {
            "stressed": ["stressed", "overwhelmed", "anxious", "worried", "pressure"],
            "positive": ["happy", "excited", "grateful", "good", "great"],
            "reflective": ["thinking", "wondering", "considering", "processing"],
            "tired": ["tired", "exhausted", "drained", "need rest"],
            "motivated": ["motivated", "ready", "energized", "pumped"],
        }

        for mood, indicators in mood_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                return mood

        return None

    def _split_into_segments(self, text: str) -> list[str]:
        """Split raw text into processable segments."""
        # Split on common separators
        segments = re.split(r'[,\n;]|(?:\.\s+)|(?:also\s+)|(?:and\s+)', text)

        # Clean up segments
        cleaned = []
        for segment in segments:
            segment = segment.strip()
            if segment and len(segment) > 3:  # Skip very short fragments
                cleaned.append(segment)

        return cleaned

    def _suggest_action(self, item: ProcessedItem) -> Optional[str]:
        """Suggest a next action for an item."""
        if item.category != ItemCategory.TASK:
            return None

        content_lower = item.content.lower()

        # Suggest based on keywords
        if "call" in content_lower:
            return "Add to today's call list"
        if "email" in content_lower:
            return "Draft email now or schedule for focus time"
        if "buy" in content_lower or "groceries" in content_lower:
            return "Add to shopping list"
        if "deadline" in content_lower:
            return "Block time on calendar"
        if "presentation" in content_lower:
            return "Schedule prep time and rehearsal"

        return "Add to task list with due date"

    async def process(self, raw_thoughts: str) -> BrainDumpResult:
        """
        Process raw thoughts into organized items.

        Args:
            raw_thoughts: Unstructured text input

        Returns:
            BrainDumpResult with organized items
        """
        segments = self._split_into_segments(raw_thoughts)
        items = []

        for segment in segments:
            category = self._detect_category(segment)
            priority = self._detect_priority(segment)

            item = ProcessedItem(
                content=segment,
                category=category,
                priority=priority,
            )

            # Add suggested action for tasks
            item.suggested_action = self._suggest_action(item)

            items.append(item)

        # Create result
        result = BrainDumpResult(
            raw_input=raw_thoughts,
            items=items,
            summary=self._generate_summary(items),
            mood_detected=self._detect_mood(raw_thoughts),
            themes=self._extract_themes(raw_thoughts),
        )

        # Store in Notion
        page_id = await self.notion.create_brain_dump_page(result)
        result.notion_page_id = page_id

        return result

    def _generate_summary(self, items: list[ProcessedItem]) -> str:
        """Generate a brief summary of the brain dump."""
        task_count = sum(1 for i in items if i.category == ItemCategory.TASK)
        idea_count = sum(1 for i in items if i.category == ItemCategory.IDEA)
        feeling_count = sum(1 for i in items if i.category == ItemCategory.FEELING)

        parts = []
        if task_count:
            parts.append(f"{task_count} actionable item{'s' if task_count > 1 else ''}")
        if idea_count:
            parts.append(f"{idea_count} idea{'s' if idea_count > 1 else ''}")
        if feeling_count:
            parts.append(f"{feeling_count} feeling{'s' if feeling_count > 1 else ''}")

        if not parts:
            return "Processed your thoughts"

        return f"Found {', '.join(parts)} in your brain dump"


# Convenience function for direct use


async def process_brain_dump(
    raw_thoughts: str,
    notion_api_key: Optional[str] = None,
    notion_db_id: Optional[str] = None,
) -> BrainDumpResult:
    """
    Process unstructured thoughts into organized items.

    Args:
        raw_thoughts: Stream of consciousness text
        notion_api_key: Optional Notion API key
        notion_db_id: Optional Notion database ID

    Returns:
        BrainDumpResult with organized items and warm response
    """
    processor = BrainDumpProcessor(
        notion_api_key=notion_api_key,
        notion_db_id=notion_db_id,
    )
    return await processor.process(raw_thoughts)


# Synchronous wrapper for non-async contexts


def process_brain_dump_sync(
    raw_thoughts: str,
    **kwargs,
) -> BrainDumpResult:
    """Synchronous wrapper for process_brain_dump."""
    return asyncio.run(process_brain_dump(raw_thoughts, **kwargs))
