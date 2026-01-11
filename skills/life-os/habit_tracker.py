"""
Habit Tracker

Track daily habits with streak counting, celebrations,
and compassionate handling of missed days.
"""

import os
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, date, timedelta
from enum import Enum
import random


class HabitFrequency(Enum):
    """How often a habit should be performed."""

    DAILY = "daily"
    WEEKDAYS = "weekdays"
    WEEKENDS = "weekends"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class HabitCategory(Enum):
    """Categories for habits."""

    HEALTH = "health"
    FITNESS = "fitness"
    MINDFULNESS = "mindfulness"
    LEARNING = "learning"
    PRODUCTIVITY = "productivity"
    SOCIAL = "social"
    CREATIVE = "creative"
    SELF_CARE = "self_care"
    OTHER = "other"


@dataclass
class Habit:
    """A habit being tracked."""

    id: str
    name: str
    description: str = ""
    category: HabitCategory = HabitCategory.OTHER
    frequency: HabitFrequency = HabitFrequency.DAILY
    target_days: list[int] = field(default_factory=list)  # 0=Mon, 6=Sun
    reminder_time: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    archived: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "frequency": self.frequency.value,
            "target_days": self.target_days,
            "reminder_time": self.reminder_time,
            "created_at": self.created_at.isoformat(),
            "archived": self.archived,
        }

    def is_scheduled_for(self, target_date: date) -> bool:
        """Check if habit is scheduled for a specific date."""
        weekday = target_date.weekday()

        if self.frequency == HabitFrequency.DAILY:
            return True
        elif self.frequency == HabitFrequency.WEEKDAYS:
            return weekday < 5
        elif self.frequency == HabitFrequency.WEEKENDS:
            return weekday >= 5
        elif self.frequency == HabitFrequency.WEEKLY:
            return weekday in self.target_days
        elif self.frequency == HabitFrequency.CUSTOM:
            return weekday in self.target_days

        return True


@dataclass
class HabitLog:
    """A single habit completion log entry."""

    habit_id: str
    date: date
    completed: bool
    notes: str = ""
    logged_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "habit_id": self.habit_id,
            "date": self.date.isoformat(),
            "completed": self.completed,
            "notes": self.notes,
            "logged_at": self.logged_at.isoformat(),
        }


@dataclass
class StreakInfo:
    """Information about a habit streak."""

    habit_name: str
    current_streak: int
    best_streak: int
    total_completions: int
    completion_rate: float  # 0-1
    last_completed: Optional[date] = None

    def to_dict(self) -> dict:
        return {
            "habit_name": self.habit_name,
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "total_completions": self.total_completions,
            "completion_rate": self.completion_rate,
            "last_completed": self.last_completed.isoformat() if self.last_completed else None,
        }


@dataclass
class HabitSummary:
    """Summary of all habits."""

    date_range_start: date
    date_range_end: date
    habits: list[StreakInfo]
    total_habits: int
    active_habits: int
    overall_completion_rate: float
    top_streaks: list[StreakInfo]
    needs_attention: list[str]  # Habits with low completion

    # Celebratory messages for different streak milestones
    STREAK_CELEBRATIONS = {
        1: [
            "You showed up today! That's what matters.",
            "Day 1 - every streak starts here!",
            "The beginning of something great!",
        ],
        3: [
            "3 days in a row! You're building momentum.",
            "Three-peat! Keep that energy going.",
            "Hat trick! Consistency is forming.",
        ],
        7: [
            "A FULL WEEK! That's incredible dedication!",
            "7 days strong! You should be proud.",
            "One week down - you've proven you can do this!",
        ],
        14: [
            "TWO WEEKS! This is becoming part of who you are.",
            "14 days of showing up. That's real commitment.",
            "Half a month! You're unstoppable.",
        ],
        21: [
            "21 DAYS - they say that's how habits form!",
            "Three weeks! This is officially a habit now.",
            "21 days of dedication. You're amazing!",
        ],
        30: [
            "A FULL MONTH! You're a habit master!",
            "30 days! This is who you are now.",
            "One month strong - celebrate this victory!",
        ],
        50: [
            "50 DAYS! That's exceptional commitment!",
            "Half a hundred! You're in elite company.",
            "50 days of showing up. Incredible!",
        ],
        100: [
            "100 DAYS! You're a legend!",
            "TRIPLE DIGITS! This is extraordinary!",
            "A hundred days! Take a moment to appreciate this.",
        ],
    }

    MISSED_DAY_COMPASSION = [
        "Yesterday was a rest day. That's okay - what matters is showing up today.",
        "Missing a day doesn't erase your progress. Ready to continue?",
        "Life happens. Your streak may reset, but your growth doesn't.",
        "One day off won't undo all your hard work. Let's keep going!",
        "Rest is part of the journey too. Back at it today?",
    ]

    def to_dict(self) -> dict:
        return {
            "date_range_start": self.date_range_start.isoformat(),
            "date_range_end": self.date_range_end.isoformat(),
            "habits": [h.to_dict() for h in self.habits],
            "total_habits": self.total_habits,
            "active_habits": self.active_habits,
            "overall_completion_rate": self.overall_completion_rate,
            "top_streaks": [s.to_dict() for s in self.top_streaks],
            "needs_attention": self.needs_attention,
        }

    def format_response(self) -> str:
        """Format the summary as an encouraging response."""
        lines = []

        # Header
        lines.append("# Habit Summary")
        lines.append(
            f"*{self.date_range_start.strftime('%B %d')} - "
            f"{self.date_range_end.strftime('%B %d, %Y')}*"
        )
        lines.append("")

        # Overall stats
        completion_pct = int(self.overall_completion_rate * 100)
        lines.append(f"**Overall Completion:** {completion_pct}%")
        lines.append(f"**Active Habits:** {self.active_habits}")
        lines.append("")

        # Top streaks
        if self.top_streaks:
            lines.append("## Current Streaks")
            for streak in sorted(self.top_streaks, key=lambda s: -s.current_streak)[:5]:
                streak_msg = self._get_streak_message(streak.current_streak)
                lines.append(f"- **{streak.habit_name}:** {streak.current_streak} days")
                if streak_msg:
                    lines.append(f"  _{streak_msg}_")
            lines.append("")

        # All habits
        lines.append("## All Habits")
        for habit in self.habits:
            rate_pct = int(habit.completion_rate * 100)
            streak_indicator = f" ({habit.current_streak} day streak)" if habit.current_streak > 0 else ""
            lines.append(f"- {habit.habit_name}: {rate_pct}% completion{streak_indicator}")
        lines.append("")

        # Needs attention
        if self.needs_attention:
            lines.append("## Needs Some Love")
            lines.append("_These habits could use more attention:_")
            for habit_name in self.needs_attention:
                lines.append(f"- {habit_name}")
            lines.append("")
            lines.append(
                "_Remember: it's okay to adjust or pause habits that aren't "
                "serving you right now._"
            )
            lines.append("")

        # Encouragement
        if completion_pct >= 80:
            lines.append("---")
            lines.append("_Outstanding work! You're crushing it!_")
        elif completion_pct >= 60:
            lines.append("---")
            lines.append("_Good progress! Keep building those habits._")
        else:
            lines.append("---")
            lines.append("_Every day is a new chance to show up. You've got this!_")

        return "\n".join(lines)

    def _get_streak_message(self, streak: int) -> str:
        """Get a celebration message for a streak."""
        # Find the highest milestone reached
        for milestone in sorted(self.STREAK_CELEBRATIONS.keys(), reverse=True):
            if streak >= milestone:
                return random.choice(self.STREAK_CELEBRATIONS[milestone])
        return ""


class NotionClient:
    """Client for Notion API integration."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        habits_db: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("NOTION_API_KEY")
        self.habits_db = habits_db or os.getenv("NOTION_HABITS_DB")

    async def get_habits(self, include_archived: bool = False) -> list[Habit]:
        """Fetch all habits from Notion."""
        # TODO: Implement actual Notion query
        return []

    async def get_habit_by_name(self, name: str) -> Optional[Habit]:
        """Find a habit by name."""
        # TODO: Implement actual Notion query
        return None

    async def get_habit_logs(
        self,
        habit_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[HabitLog]:
        """Fetch habit logs for a specific habit."""
        # TODO: Implement actual Notion query
        return []

    async def log_habit(
        self,
        habit_id: str,
        target_date: date,
        completed: bool,
        notes: str = "",
    ) -> HabitLog:
        """Log a habit completion."""
        # TODO: Implement actual Notion page creation
        return HabitLog(
            habit_id=habit_id,
            date=target_date,
            completed=completed,
            notes=notes,
        )

    async def create_habit(self, habit: Habit) -> str:
        """Create a new habit in Notion."""
        # TODO: Implement actual Notion page creation
        return habit.id


class HabitTracker:
    """
    Tracks habits with streak counting and encouragement.

    Handles daily logging, streak calculation, and provides
    warm, encouraging feedback for both successes and misses.
    """

    def __init__(
        self,
        notion_api_key: Optional[str] = None,
        notion_db_id: Optional[str] = None,
    ):
        self.notion = NotionClient(
            api_key=notion_api_key,
            habits_db=notion_db_id,
        )
        # In-memory cache for demo (would use Notion in production)
        self._habits: dict[str, Habit] = {}
        self._logs: list[HabitLog] = []

    def _calculate_streak(
        self,
        habit: Habit,
        logs: list[HabitLog],
        as_of: date,
    ) -> int:
        """Calculate current streak for a habit."""
        if not logs:
            return 0

        # Sort logs by date descending
        sorted_logs = sorted(
            [l for l in logs if l.completed],
            key=lambda l: l.date,
            reverse=True,
        )

        if not sorted_logs:
            return 0

        streak = 0
        check_date = as_of

        # Count backwards from today
        for _ in range(365):  # Max 1 year of checking
            # Skip days the habit isn't scheduled
            if not habit.is_scheduled_for(check_date):
                check_date -= timedelta(days=1)
                continue

            # Check if we have a completion for this date
            completed_on_date = any(
                log.date == check_date and log.completed
                for log in sorted_logs
            )

            if completed_on_date:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        return streak

    def _calculate_best_streak(
        self,
        habit: Habit,
        logs: list[HabitLog],
    ) -> int:
        """Calculate the best streak ever for a habit."""
        if not logs:
            return 0

        completed_logs = sorted(
            [l for l in logs if l.completed],
            key=lambda l: l.date,
        )

        if not completed_logs:
            return 0

        best_streak = 0
        current_streak = 0
        last_date = None

        for log in completed_logs:
            if not habit.is_scheduled_for(log.date):
                continue

            if last_date is None:
                current_streak = 1
            else:
                # Check for consecutive scheduled days
                expected_date = last_date + timedelta(days=1)
                while expected_date < log.date:
                    if habit.is_scheduled_for(expected_date):
                        # Missed a scheduled day
                        current_streak = 1
                        break
                    expected_date += timedelta(days=1)
                else:
                    current_streak += 1

            last_date = log.date
            best_streak = max(best_streak, current_streak)

        return best_streak

    def _generate_log_response(
        self,
        habit: Habit,
        completed: bool,
        streak: int,
        best_streak: int,
    ) -> str:
        """Generate an encouraging response for a habit log."""
        if completed:
            streak_msg = ""
            for milestone in sorted(HabitSummary.STREAK_CELEBRATIONS.keys(), reverse=True):
                if streak >= milestone:
                    streak_msg = random.choice(HabitSummary.STREAK_CELEBRATIONS[milestone])
                    break

            if streak == best_streak and streak > 1:
                return (
                    f"**{habit.name}** logged!\n\n"
                    f"Current streak: **{streak} days** - YOUR BEST EVER!\n\n"
                    f"_{streak_msg}_"
                )
            else:
                return (
                    f"**{habit.name}** logged!\n\n"
                    f"Current streak: **{streak} days**\n\n"
                    f"_{streak_msg}_"
                )
        else:
            compassion = random.choice(HabitSummary.MISSED_DAY_COMPASSION)
            return (
                f"**{habit.name}** marked as missed.\n\n"
                f"_{compassion}_"
            )

    async def log(
        self,
        habit_name: str,
        completed: bool = True,
        target_date: Optional[date] = None,
        notes: str = "",
    ) -> dict:
        """
        Log a habit completion or miss.

        Args:
            habit_name: Name of the habit
            completed: Whether the habit was completed
            target_date: Date to log for (default: today)
            notes: Optional notes about the log

        Returns:
            Dict with log info and encouraging response
        """
        if target_date is None:
            target_date = date.today()

        # Find or create habit
        habit = await self.notion.get_habit_by_name(habit_name)
        if habit is None:
            # Create a new habit
            import uuid
            habit = Habit(
                id=str(uuid.uuid4()),
                name=habit_name,
            )
            self._habits[habit.id] = habit
            await self.notion.create_habit(habit)

        # Log the habit
        log_entry = await self.notion.log_habit(
            habit_id=habit.id,
            target_date=target_date,
            completed=completed,
            notes=notes,
        )
        self._logs.append(log_entry)

        # Calculate streak
        all_logs = await self.notion.get_habit_logs(habit.id)
        all_logs = all_logs + [log_entry]  # Include new log

        streak = self._calculate_streak(habit, all_logs, target_date)
        best_streak = max(self._calculate_best_streak(habit, all_logs), streak)

        # Generate response
        response = self._generate_log_response(habit, completed, streak, best_streak)

        return {
            "success": True,
            "habit": habit.to_dict(),
            "log": log_entry.to_dict(),
            "current_streak": streak,
            "best_streak": best_streak,
            "response": response,
        }

    async def get_streak(self, habit_name: str) -> StreakInfo:
        """
        Get streak information for a habit.

        Args:
            habit_name: Name of the habit

        Returns:
            StreakInfo with current and best streak
        """
        habit = await self.notion.get_habit_by_name(habit_name)
        if habit is None:
            return StreakInfo(
                habit_name=habit_name,
                current_streak=0,
                best_streak=0,
                total_completions=0,
                completion_rate=0.0,
            )

        logs = await self.notion.get_habit_logs(habit.id)
        today = date.today()

        current_streak = self._calculate_streak(habit, logs, today)
        best_streak = self._calculate_best_streak(habit, logs)
        completed_logs = [l for l in logs if l.completed]
        total = len(completed_logs)

        # Calculate completion rate (last 30 days)
        thirty_days_ago = today - timedelta(days=30)
        scheduled_days = sum(
            1 for i in range(30)
            if habit.is_scheduled_for(thirty_days_ago + timedelta(days=i))
        )
        recent_completions = sum(
            1 for l in completed_logs
            if l.date >= thirty_days_ago
        )
        rate = recent_completions / scheduled_days if scheduled_days > 0 else 0.0

        last_completed = max((l.date for l in completed_logs), default=None)

        return StreakInfo(
            habit_name=habit_name,
            current_streak=current_streak,
            best_streak=best_streak,
            total_completions=total,
            completion_rate=rate,
            last_completed=last_completed,
        )

    async def get_summary(
        self,
        days: int = 30,
    ) -> HabitSummary:
        """
        Get a summary of all habits.

        Args:
            days: Number of days to include in summary

        Returns:
            HabitSummary with all habit stats
        """
        today = date.today()
        start_date = today - timedelta(days=days)

        habits = await self.notion.get_habits()
        habit_streaks = []
        total_scheduled = 0
        total_completed = 0
        needs_attention = []

        for habit in habits:
            logs = await self.notion.get_habit_logs(
                habit.id,
                start_date=start_date,
                end_date=today,
            )

            streak_info = StreakInfo(
                habit_name=habit.name,
                current_streak=self._calculate_streak(habit, logs, today),
                best_streak=self._calculate_best_streak(habit, logs),
                total_completions=len([l for l in logs if l.completed]),
                completion_rate=0.0,
            )

            # Calculate rate
            scheduled_days = sum(
                1 for i in range(days)
                if habit.is_scheduled_for(start_date + timedelta(days=i))
            )
            if scheduled_days > 0:
                streak_info.completion_rate = streak_info.total_completions / scheduled_days
                total_scheduled += scheduled_days
                total_completed += streak_info.total_completions

            habit_streaks.append(streak_info)

            # Check if needs attention
            if streak_info.completion_rate < 0.5:
                needs_attention.append(habit.name)

        # Overall rate
        overall_rate = total_completed / total_scheduled if total_scheduled > 0 else 0.0

        # Top streaks
        top_streaks = sorted(
            habit_streaks,
            key=lambda s: s.current_streak,
            reverse=True,
        )[:5]

        return HabitSummary(
            date_range_start=start_date,
            date_range_end=today,
            habits=habit_streaks,
            total_habits=len(habits),
            active_habits=len([h for h in habits if not h.archived]),
            overall_completion_rate=overall_rate,
            top_streaks=top_streaks,
            needs_attention=needs_attention,
        )


# Convenience functions for direct use


async def log_habit(
    habit: str,
    completed: bool = True,
    date: Optional[date] = None,
    notes: str = "",
    notion_api_key: Optional[str] = None,
    notion_db_id: Optional[str] = None,
) -> dict:
    """
    Log a habit completion.

    Args:
        habit: Name of the habit
        completed: Whether it was completed
        date: Date to log (default: today)
        notes: Optional notes

    Returns:
        Dict with log info and encouraging response
    """
    tracker = HabitTracker(
        notion_api_key=notion_api_key,
        notion_db_id=notion_db_id,
    )
    return await tracker.log(habit, completed, date, notes)


async def get_habit_streak(
    habit: str,
    notion_api_key: Optional[str] = None,
    notion_db_id: Optional[str] = None,
) -> StreakInfo:
    """
    Get streak info for a habit.

    Args:
        habit: Name of the habit

    Returns:
        StreakInfo with streak data
    """
    tracker = HabitTracker(
        notion_api_key=notion_api_key,
        notion_db_id=notion_db_id,
    )
    return await tracker.get_streak(habit)


async def habit_summary(
    days: int = 30,
    notion_api_key: Optional[str] = None,
    notion_db_id: Optional[str] = None,
) -> HabitSummary:
    """
    Get summary of all habits.

    Args:
        days: Number of days to summarize

    Returns:
        HabitSummary with all stats
    """
    tracker = HabitTracker(
        notion_api_key=notion_api_key,
        notion_db_id=notion_db_id,
    )
    return await tracker.get_summary(days)


# Synchronous wrappers


def log_habit_sync(habit: str, completed: bool = True, **kwargs) -> dict:
    """Synchronous wrapper for log_habit."""
    return asyncio.run(log_habit(habit, completed, **kwargs))


def get_habit_streak_sync(habit: str, **kwargs) -> StreakInfo:
    """Synchronous wrapper for get_habit_streak."""
    return asyncio.run(get_habit_streak(habit, **kwargs))


def habit_summary_sync(days: int = 30, **kwargs) -> HabitSummary:
    """Synchronous wrapper for habit_summary."""
    return asyncio.run(habit_summary(days, **kwargs))
