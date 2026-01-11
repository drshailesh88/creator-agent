"""
Daily Briefing Generator

Creates personalized morning briefings with calendar events,
priorities, and contextual reminders.
"""

import os
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, date, timedelta
from enum import Enum
import random


class EventType(Enum):
    """Types of calendar events."""

    MEETING = "meeting"
    FOCUS_TIME = "focus_time"
    REMINDER = "reminder"
    DEADLINE = "deadline"
    PERSONAL = "personal"
    HEALTH = "health"


class WeatherCondition(Enum):
    """Weather conditions for briefing context."""

    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    SNOWY = "snowy"
    STORMY = "stormy"
    CLEAR = "clear"


@dataclass
class CalendarEvent:
    """Represents a calendar event."""

    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    event_type: EventType = EventType.MEETING
    location: Optional[str] = None
    attendees: list[str] = field(default_factory=list)
    notes: str = ""
    is_all_day: bool = False

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "event_type": self.event_type.value,
            "location": self.location,
            "attendees": self.attendees,
            "notes": self.notes,
            "is_all_day": self.is_all_day,
        }

    def format_time(self) -> str:
        """Format event time for display."""
        if self.is_all_day:
            return "All day"
        return self.start_time.strftime("%I:%M %p")


@dataclass
class Priority:
    """A priority item for the day."""

    title: str
    context: str = ""
    source: str = ""  # Where this priority came from
    energy_level: str = "medium"  # high, medium, low
    estimated_time: Optional[int] = None  # minutes

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "context": self.context,
            "source": self.source,
            "energy_level": self.energy_level,
            "estimated_time": self.estimated_time,
        }


@dataclass
class HabitReminder:
    """A habit to be reminded about."""

    name: str
    current_streak: int
    best_streak: int
    scheduled_time: Optional[str] = None
    encouragement: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "scheduled_time": self.scheduled_time,
            "encouragement": self.encouragement,
        }


@dataclass
class DailyBriefing:
    """A complete daily briefing."""

    date: date
    greeting: str
    calendar_events: list[CalendarEvent]
    top_priorities: list[Priority]
    habit_reminders: list[HabitReminder]
    quote_of_day: str = ""
    weather_summary: str = ""
    energy_suggestion: str = ""
    notes_from_yesterday: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    notion_page_id: Optional[str] = None

    # Warm greeting templates
    GREETINGS = {
        "monday": [
            "Good morning! Fresh week, fresh start.",
            "Happy Monday! Let's make this week count.",
            "Rise and shine! A new week of possibilities awaits.",
        ],
        "friday": [
            "Happy Friday! You're almost there.",
            "TGIF! One more day to finish strong.",
            "Friday vibes! Let's wrap up the week well.",
        ],
        "weekend": [
            "Good morning! Hope you're taking it easy today.",
            "Weekend energy! Balance rest with what matters.",
            "Hello! Remember: weekends are for recharging too.",
        ],
        "default": [
            "Good morning! Here's what today looks like.",
            "Rise and shine! Let's make today great.",
            "Hello! Ready to tackle the day?",
            "Good morning! I've got your day organized.",
        ],
    }

    ENERGY_SUGGESTIONS = {
        "high_load": [
            "Today looks busy - remember to take breaks.",
            "Lots on the plate today. Prioritize and pace yourself.",
            "Full day ahead - protect your focus time.",
        ],
        "light_load": [
            "Light calendar today - great for deep work!",
            "Some breathing room today. What will you create?",
            "Flexible day ahead - use it wisely!",
        ],
        "balanced": [
            "Nice balance of meetings and focus time today.",
            "Good mix today - you've got this!",
            "Balanced day ahead. Stay present in each moment.",
        ],
    }

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "greeting": self.greeting,
            "calendar_events": [e.to_dict() for e in self.calendar_events],
            "top_priorities": [p.to_dict() for p in self.top_priorities],
            "habit_reminders": [h.to_dict() for h in self.habit_reminders],
            "quote_of_day": self.quote_of_day,
            "weather_summary": self.weather_summary,
            "energy_suggestion": self.energy_suggestion,
            "notes_from_yesterday": self.notes_from_yesterday,
            "created_at": self.created_at.isoformat(),
            "notion_page_id": self.notion_page_id,
        }

    def format_response(self) -> str:
        """Format the briefing as a warm, readable response."""
        lines = []

        # Greeting
        lines.append(f"## {self.greeting}")
        lines.append(f"*{self.date.strftime('%A, %B %d, %Y')}*")
        lines.append("")

        # Quote of the day
        if self.quote_of_day:
            lines.append(f"> {self.quote_of_day}")
            lines.append("")

        # Weather
        if self.weather_summary:
            lines.append(f"**Weather:** {self.weather_summary}")
            lines.append("")

        # Top Priorities
        lines.append("### Your Top Priorities Today")
        if self.top_priorities:
            for i, priority in enumerate(self.top_priorities[:3], 1):
                time_est = f" (~{priority.estimated_time}min)" if priority.estimated_time else ""
                lines.append(f"{i}. **{priority.title}**{time_est}")
                if priority.context:
                    lines.append(f"   _{priority.context}_")
        else:
            lines.append("_No specific priorities set - what matters most to you today?_")
        lines.append("")

        # Calendar
        lines.append("### Today's Schedule")
        if self.calendar_events:
            for event in self.calendar_events:
                time_str = event.format_time()
                icon = self._get_event_icon(event.event_type)
                lines.append(f"- {icon} **{time_str}** - {event.title}")
                if event.location:
                    lines.append(f"  _@ {event.location}_")
        else:
            lines.append("_Clear calendar today!_")
        lines.append("")

        # Habits
        if self.habit_reminders:
            lines.append("### Habit Check-ins")
            for habit in self.habit_reminders:
                streak_msg = f" ({habit.current_streak} day streak!)" if habit.current_streak > 0 else ""
                lines.append(f"- {habit.name}{streak_msg}")
                if habit.encouragement:
                    lines.append(f"  _{habit.encouragement}_")
            lines.append("")

        # Energy suggestion
        if self.energy_suggestion:
            lines.append(f"**Energy Note:** {self.energy_suggestion}")
            lines.append("")

        # Notes from yesterday
        if self.notes_from_yesterday:
            lines.append("### Carried Over")
            lines.append(self.notes_from_yesterday)
            lines.append("")

        # Closing
        lines.append("---")
        lines.append("_Have a wonderful day! You've got this._")

        return "\n".join(lines)

    def _get_event_icon(self, event_type: EventType) -> str:
        """Get an icon for event type."""
        icons = {
            EventType.MEETING: "[M]",
            EventType.FOCUS_TIME: "[F]",
            EventType.REMINDER: "[R]",
            EventType.DEADLINE: "[!]",
            EventType.PERSONAL: "[P]",
            EventType.HEALTH: "[H]",
        }
        return icons.get(event_type, "[-]")


class NotionClient:
    """Client for Notion API integration."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        daily_notes_db: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("NOTION_API_KEY")
        self.daily_notes_db = daily_notes_db or os.getenv("NOTION_DAILY_NOTES_DB")

    async def get_calendar_events(self, target_date: date) -> list[CalendarEvent]:
        """Fetch calendar events from Notion."""
        # TODO: Implement actual Notion calendar query
        # This would query a calendar database filtered by date
        return []

    async def get_priorities(self, target_date: date) -> list[Priority]:
        """Fetch priorities from Notion tasks database."""
        # TODO: Implement actual Notion query for high-priority tasks
        return []

    async def get_habits(self) -> list[HabitReminder]:
        """Fetch active habits from Notion."""
        # TODO: Implement actual Notion query for habits
        return []

    async def get_yesterday_notes(self, target_date: date) -> str:
        """Get notes/carryover from yesterday's daily note."""
        # TODO: Implement actual Notion query
        return ""

    async def create_daily_note(self, briefing: DailyBriefing) -> Optional[str]:
        """Create a daily note page in Notion."""
        # TODO: Implement actual Notion page creation
        return f"notion_daily_{briefing.date.isoformat()}"


class DailyBriefingGenerator:
    """
    Generates personalized daily briefings.

    Combines calendar data, priorities, habits, and context
    into a warm, actionable morning briefing.
    """

    QUOTES = [
        "The secret of getting ahead is getting started. - Mark Twain",
        "What you do today can improve all your tomorrows. - Ralph Marston",
        "Every day is a new beginning. Take a deep breath and start again.",
        "Progress, not perfection. - Unknown",
        "Small steps every day lead to big changes over time.",
        "Your only limit is your mind. - Unknown",
        "Be present. Make today count.",
        "Focus on what matters. Let go of what doesn't.",
    ]

    def __init__(
        self,
        notion_api_key: Optional[str] = None,
        notion_db_id: Optional[str] = None,
    ):
        self.notion = NotionClient(
            api_key=notion_api_key,
            daily_notes_db=notion_db_id,
        )

    def _get_greeting(self, target_date: date) -> str:
        """Get appropriate greeting for the day."""
        weekday = target_date.weekday()

        if weekday == 0:  # Monday
            templates = DailyBriefing.GREETINGS["monday"]
        elif weekday == 4:  # Friday
            templates = DailyBriefing.GREETINGS["friday"]
        elif weekday >= 5:  # Weekend
            templates = DailyBriefing.GREETINGS["weekend"]
        else:
            templates = DailyBriefing.GREETINGS["default"]

        return random.choice(templates)

    def _get_energy_suggestion(self, events: list[CalendarEvent]) -> str:
        """Suggest energy management based on calendar load."""
        meeting_count = sum(
            1 for e in events
            if e.event_type == EventType.MEETING
        )

        if meeting_count >= 5:
            return random.choice(DailyBriefing.ENERGY_SUGGESTIONS["high_load"])
        elif meeting_count <= 1:
            return random.choice(DailyBriefing.ENERGY_SUGGESTIONS["light_load"])
        else:
            return random.choice(DailyBriefing.ENERGY_SUGGESTIONS["balanced"])

    def _generate_habit_encouragement(self, habit: HabitReminder) -> str:
        """Generate encouraging message for habit."""
        if habit.current_streak == 0:
            return "Today is a great day to start fresh!"
        elif habit.current_streak == habit.best_streak:
            return f"You're at your best streak! Keep it going!"
        elif habit.current_streak >= 7:
            return f"A full week! That's dedication!"
        elif habit.current_streak >= 3:
            return "Building momentum - nice work!"
        else:
            return "Every day counts. You're doing great!"

    async def generate(
        self,
        target_date: Optional[date] = None,
    ) -> DailyBriefing:
        """
        Generate a daily briefing for the specified date.

        Args:
            target_date: Date to generate briefing for (default: today)

        Returns:
            Complete DailyBriefing with all components
        """
        if target_date is None:
            target_date = date.today()

        # Gather data from Notion (parallel where possible)
        events = await self.notion.get_calendar_events(target_date)
        priorities = await self.notion.get_priorities(target_date)
        habits = await self.notion.get_habits()
        yesterday_notes = await self.notion.get_yesterday_notes(target_date)

        # Add encouragement to habits
        for habit in habits:
            habit.encouragement = self._generate_habit_encouragement(habit)

        # Create briefing
        briefing = DailyBriefing(
            date=target_date,
            greeting=self._get_greeting(target_date),
            calendar_events=sorted(events, key=lambda e: e.start_time),
            top_priorities=priorities[:3],  # Limit to top 3
            habit_reminders=habits,
            quote_of_day=random.choice(self.QUOTES),
            energy_suggestion=self._get_energy_suggestion(events),
            notes_from_yesterday=yesterday_notes,
        )

        # Store in Notion
        page_id = await self.notion.create_daily_note(briefing)
        briefing.notion_page_id = page_id

        return briefing


# Convenience function for direct use


async def generate_briefing(
    target_date: Optional[date] = None,
    notion_api_key: Optional[str] = None,
    notion_db_id: Optional[str] = None,
) -> DailyBriefing:
    """
    Generate a daily briefing.

    Args:
        target_date: Date for briefing (default: today)
        notion_api_key: Optional Notion API key
        notion_db_id: Optional Notion database ID

    Returns:
        DailyBriefing with calendar, priorities, and habits
    """
    generator = DailyBriefingGenerator(
        notion_api_key=notion_api_key,
        notion_db_id=notion_db_id,
    )
    return await generator.generate(target_date)


# Synchronous wrapper


def generate_briefing_sync(
    target_date: Optional[date] = None,
    **kwargs,
) -> DailyBriefing:
    """Synchronous wrapper for generate_briefing."""
    return asyncio.run(generate_briefing(target_date, **kwargs))
