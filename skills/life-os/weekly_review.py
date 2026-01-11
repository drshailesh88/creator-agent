"""
Weekly Review Generator

Facilitates weekly reflection and planning with wins,
lessons learned, and next week's focus areas.
"""

import os
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, date, timedelta
from enum import Enum
import random


class ReviewSection(Enum):
    """Sections of a weekly review."""

    WINS = "wins"
    LESSONS = "lessons"
    CHALLENGES = "challenges"
    GRATITUDE = "gratitude"
    ENERGY = "energy"
    FOCUS = "focus"
    INTENTIONS = "intentions"


class EnergyLevel(Enum):
    """Energy level ratings."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VARIABLE = "variable"


@dataclass
class Win:
    """A win or accomplishment from the week."""

    description: str
    category: str = ""  # work, personal, health, etc.
    impact: str = ""  # Why it matters
    date_achieved: Optional[date] = None

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "category": self.category,
            "impact": self.impact,
            "date_achieved": self.date_achieved.isoformat() if self.date_achieved else None,
        }


@dataclass
class Lesson:
    """A lesson learned during the week."""

    insight: str
    context: str = ""  # What happened that led to this
    action: str = ""  # What to do differently
    source: str = ""  # challenge, success, observation

    def to_dict(self) -> dict:
        return {
            "insight": self.insight,
            "context": self.context,
            "action": self.action,
            "source": self.source,
        }


@dataclass
class Challenge:
    """A challenge faced during the week."""

    description: str
    status: str = "ongoing"  # resolved, ongoing, tabled
    learning: str = ""
    support_needed: str = ""

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "status": self.status,
            "learning": self.learning,
            "support_needed": self.support_needed,
        }


@dataclass
class FocusArea:
    """A focus area for the upcoming week."""

    area: str
    why: str = ""
    success_looks_like: str = ""
    first_step: str = ""

    def to_dict(self) -> dict:
        return {
            "area": self.area,
            "why": self.why,
            "success_looks_like": self.success_looks_like,
            "first_step": self.first_step,
        }


@dataclass
class WeeklyReview:
    """A complete weekly review."""

    week_start: date
    week_end: date
    wins: list[Win]
    lessons: list[Lesson]
    challenges: list[Challenge]
    gratitude: list[str]
    energy_rating: EnergyLevel
    energy_notes: str
    next_week_focus: list[FocusArea]
    intentions: list[str]
    highlights: str = ""
    lowlights: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    notion_page_id: Optional[str] = None

    # Encouraging response templates
    CELEBRATION_PHRASES = [
        "What a week! Look at everything you accomplished:",
        "Let's celebrate your wins from this week:",
        "You did some amazing things this week:",
        "Time to acknowledge your hard work:",
        "Here's what you crushed this week:",
    ]

    LESSON_INTROS = [
        "Every week teaches us something. Here's what you learned:",
        "Growth comes from reflection. Your lessons this week:",
        "Wisdom gained this week:",
        "Insights to carry forward:",
    ]

    CHALLENGE_ACKNOWLEDGMENTS = [
        "It wasn't all smooth sailing - and that's okay. Challenges faced:",
        "You faced some tough moments. That takes courage:",
        "Acknowledging what was hard this week:",
    ]

    CLOSING_ENCOURAGEMENTS = [
        "You're doing better than you think. Keep going!",
        "Progress over perfection. You're on the right track.",
        "Another week of growth in the books. Well done!",
        "Remember: small consistent steps lead to big changes.",
        "Be proud of yourself. You showed up this week.",
    ]

    def to_dict(self) -> dict:
        return {
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "wins": [w.to_dict() for w in self.wins],
            "lessons": [l.to_dict() for l in self.lessons],
            "challenges": [c.to_dict() for c in self.challenges],
            "gratitude": self.gratitude,
            "energy_rating": self.energy_rating.value,
            "energy_notes": self.energy_notes,
            "next_week_focus": [f.to_dict() for f in self.next_week_focus],
            "intentions": self.intentions,
            "highlights": self.highlights,
            "lowlights": self.lowlights,
            "created_at": self.created_at.isoformat(),
            "notion_page_id": self.notion_page_id,
        }

    def format_response(self) -> str:
        """Format the review as an encouraging, readable response."""
        lines = []

        # Header
        week_str = f"{self.week_start.strftime('%B %d')} - {self.week_end.strftime('%B %d, %Y')}"
        lines.append(f"# Weekly Review: {week_str}")
        lines.append("")

        # Wins (always lead with wins!)
        lines.append(f"## {random.choice(self.CELEBRATION_PHRASES)}")
        if self.wins:
            for win in self.wins:
                category_tag = f" [{win.category}]" if win.category else ""
                lines.append(f"- **{win.description}**{category_tag}")
                if win.impact:
                    lines.append(f"  _Impact: {win.impact}_")
        else:
            lines.append("_Take a moment to think about what went well..._")
        lines.append("")

        # Highlights summary
        if self.highlights:
            lines.append(f"**Week Highlight:** {self.highlights}")
            lines.append("")

        # Lessons
        if self.lessons:
            lines.append(f"## {random.choice(self.LESSON_INTROS)}")
            for lesson in self.lessons:
                lines.append(f"- {lesson.insight}")
                if lesson.action:
                    lines.append(f"  -> _Action: {lesson.action}_")
            lines.append("")

        # Challenges (approached with compassion)
        if self.challenges:
            lines.append(f"## {random.choice(self.CHALLENGE_ACKNOWLEDGMENTS)}")
            for challenge in self.challenges:
                status_icon = {"resolved": "[Resolved]", "ongoing": "[In Progress]", "tabled": "[Paused]"}.get(
                    challenge.status, ""
                )
                lines.append(f"- {challenge.description} {status_icon}")
                if challenge.learning:
                    lines.append(f"  _Learning: {challenge.learning}_")
            lines.append("")

        # Energy reflection
        lines.append("## Energy & Wellbeing")
        energy_emoji = {
            EnergyLevel.HIGH: "High energy",
            EnergyLevel.MEDIUM: "Balanced",
            EnergyLevel.LOW: "Low energy",
            EnergyLevel.VARIABLE: "Variable",
        }
        lines.append(f"**Overall Energy:** {energy_emoji.get(self.energy_rating, 'Not tracked')}")
        if self.energy_notes:
            lines.append(f"_{self.energy_notes}_")
        lines.append("")

        # Gratitude
        if self.gratitude:
            lines.append("## Gratitude")
            for item in self.gratitude:
                lines.append(f"- {item}")
            lines.append("")

        # Next week focus
        lines.append("## Looking Ahead: Next Week's Focus")
        if self.next_week_focus:
            for i, focus in enumerate(self.next_week_focus[:3], 1):
                lines.append(f"### {i}. {focus.area}")
                if focus.why:
                    lines.append(f"**Why:** {focus.why}")
                if focus.success_looks_like:
                    lines.append(f"**Success looks like:** {focus.success_looks_like}")
                if focus.first_step:
                    lines.append(f"**First step:** {focus.first_step}")
                lines.append("")
        else:
            lines.append("_What do you want to focus on next week?_")
            lines.append("")

        # Intentions
        if self.intentions:
            lines.append("## Intentions for Next Week")
            for intention in self.intentions:
                lines.append(f"- {intention}")
            lines.append("")

        # Closing
        lines.append("---")
        lines.append(f"_{random.choice(self.CLOSING_ENCOURAGEMENTS)}_")

        return "\n".join(lines)


class NotionClient:
    """Client for Notion API integration."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        weekly_review_db: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("NOTION_API_KEY")
        self.weekly_review_db = weekly_review_db or os.getenv("NOTION_WEEKLY_REVIEW_DB")

    async def get_completed_tasks(
        self,
        week_start: date,
        week_end: date,
    ) -> list[Win]:
        """Fetch completed tasks from the week as potential wins."""
        # TODO: Implement actual Notion query
        return []

    async def get_daily_notes(
        self,
        week_start: date,
        week_end: date,
    ) -> list[dict]:
        """Fetch daily notes from the week for context."""
        # TODO: Implement actual Notion query
        return []

    async def get_habit_performance(
        self,
        week_start: date,
        week_end: date,
    ) -> dict:
        """Fetch habit completion data for the week."""
        # TODO: Implement actual Notion query
        return {}

    async def create_review_page(self, review: WeeklyReview) -> Optional[str]:
        """Create a weekly review page in Notion."""
        # TODO: Implement actual Notion page creation
        return f"notion_review_{review.week_start.isoformat()}"


class WeeklyReviewGenerator:
    """
    Generates weekly reviews with reflection prompts
    and celebration of accomplishments.
    """

    # Reflection prompts to guide the review
    REFLECTION_PROMPTS = {
        "wins": [
            "What accomplishment are you most proud of?",
            "What small win deserves recognition?",
            "Where did you show up for yourself this week?",
        ],
        "lessons": [
            "What would you do differently if you could?",
            "What surprised you this week?",
            "What did a challenge teach you?",
        ],
        "gratitude": [
            "What are you thankful for this week?",
            "Who helped you or made your week better?",
            "What simple pleasure did you enjoy?",
        ],
        "focus": [
            "What one thing would make next week great?",
            "Where do you want to direct your energy?",
            "What's been waiting for your attention?",
        ],
    }

    def __init__(
        self,
        notion_api_key: Optional[str] = None,
        notion_db_id: Optional[str] = None,
    ):
        self.notion = NotionClient(
            api_key=notion_api_key,
            weekly_review_db=notion_db_id,
        )

    def _get_week_bounds(
        self,
        target_date: Optional[date] = None,
    ) -> tuple[date, date]:
        """Get the start and end dates for a week."""
        if target_date is None:
            target_date = date.today()

        # Find Monday of the week
        days_since_monday = target_date.weekday()
        week_start = target_date - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)

        return week_start, week_end

    def _analyze_energy_patterns(
        self,
        daily_notes: list[dict],
    ) -> tuple[EnergyLevel, str]:
        """Analyze energy patterns from daily notes."""
        # TODO: Implement actual energy analysis
        # This would look at mood/energy ratings in daily notes
        return EnergyLevel.MEDIUM, "Consistent energy throughout the week."

    def _extract_wins_from_data(
        self,
        completed_tasks: list[Win],
        daily_notes: list[dict],
    ) -> list[Win]:
        """Extract wins from completed tasks and daily notes."""
        wins = list(completed_tasks)

        # TODO: Also parse daily notes for accomplishments
        # Look for keywords like "finished", "completed", "achieved"

        return wins

    def _generate_reflection_prompts(
        self,
        section: str,
    ) -> list[str]:
        """Get reflection prompts for a section."""
        return self.REFLECTION_PROMPTS.get(section, [])

    async def generate(
        self,
        week: Optional[date] = None,
        wins: Optional[list[Win]] = None,
        lessons: Optional[list[Lesson]] = None,
        challenges: Optional[list[Challenge]] = None,
        gratitude: Optional[list[str]] = None,
        next_week_focus: Optional[list[FocusArea]] = None,
        intentions: Optional[list[str]] = None,
    ) -> WeeklyReview:
        """
        Generate a weekly review.

        Can be called with pre-filled data or will gather from Notion.

        Args:
            week: Any date within the target week
            wins: Pre-filled wins (optional)
            lessons: Pre-filled lessons (optional)
            challenges: Pre-filled challenges (optional)
            gratitude: Pre-filled gratitude items (optional)
            next_week_focus: Pre-filled focus areas (optional)
            intentions: Pre-filled intentions (optional)

        Returns:
            Complete WeeklyReview
        """
        week_start, week_end = self._get_week_bounds(week)

        # Gather data from Notion if not provided
        if wins is None:
            completed_tasks = await self.notion.get_completed_tasks(
                week_start, week_end
            )
            daily_notes = await self.notion.get_daily_notes(week_start, week_end)
            wins = self._extract_wins_from_data(completed_tasks, daily_notes)
        else:
            daily_notes = []

        # Analyze energy
        energy_rating, energy_notes = self._analyze_energy_patterns(daily_notes)

        # Create review
        review = WeeklyReview(
            week_start=week_start,
            week_end=week_end,
            wins=wins or [],
            lessons=lessons or [],
            challenges=challenges or [],
            gratitude=gratitude or [],
            energy_rating=energy_rating,
            energy_notes=energy_notes,
            next_week_focus=next_week_focus or [],
            intentions=intentions or [],
        )

        # Store in Notion
        page_id = await self.notion.create_review_page(review)
        review.notion_page_id = page_id

        return review

    async def interactive_review(
        self,
        week: Optional[date] = None,
    ) -> dict:
        """
        Generate an interactive review with prompts.

        Returns prompts for each section to guide user input.
        """
        week_start, week_end = self._get_week_bounds(week)

        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "sections": {
                "wins": {
                    "title": "Celebrate Your Wins",
                    "prompts": self._generate_reflection_prompts("wins"),
                    "items": [],
                },
                "lessons": {
                    "title": "Lessons Learned",
                    "prompts": self._generate_reflection_prompts("lessons"),
                    "items": [],
                },
                "gratitude": {
                    "title": "Gratitude",
                    "prompts": self._generate_reflection_prompts("gratitude"),
                    "items": [],
                },
                "focus": {
                    "title": "Next Week's Focus",
                    "prompts": self._generate_reflection_prompts("focus"),
                    "items": [],
                },
            },
        }


# Convenience function for direct use


async def generate_weekly_review(
    week: Optional[date] = None,
    wins: Optional[list[dict]] = None,
    lessons: Optional[list[dict]] = None,
    challenges: Optional[list[dict]] = None,
    gratitude: Optional[list[str]] = None,
    next_week_focus: Optional[list[dict]] = None,
    intentions: Optional[list[str]] = None,
    notion_api_key: Optional[str] = None,
    notion_db_id: Optional[str] = None,
) -> WeeklyReview:
    """
    Generate a weekly review.

    Args:
        week: Any date within the target week
        wins: List of win dicts with description, category, impact
        lessons: List of lesson dicts with insight, context, action
        challenges: List of challenge dicts
        gratitude: List of gratitude strings
        next_week_focus: List of focus area dicts
        intentions: List of intention strings
        notion_api_key: Optional Notion API key
        notion_db_id: Optional Notion database ID

    Returns:
        WeeklyReview with formatted response
    """
    # Convert dicts to dataclasses if provided
    win_objects = [Win(**w) for w in wins] if wins else None
    lesson_objects = [Lesson(**l) for l in lessons] if lessons else None
    challenge_objects = [Challenge(**c) for c in challenges] if challenges else None
    focus_objects = [FocusArea(**f) for f in next_week_focus] if next_week_focus else None

    generator = WeeklyReviewGenerator(
        notion_api_key=notion_api_key,
        notion_db_id=notion_db_id,
    )

    return await generator.generate(
        week=week,
        wins=win_objects,
        lessons=lesson_objects,
        challenges=challenge_objects,
        gratitude=gratitude,
        next_week_focus=focus_objects,
        intentions=intentions,
    )


# Synchronous wrapper


def generate_weekly_review_sync(
    week: Optional[date] = None,
    **kwargs,
) -> WeeklyReview:
    """Synchronous wrapper for generate_weekly_review."""
    return asyncio.run(generate_weekly_review(week, **kwargs))
