"""
Life OS Skill Package

Personal life management tools including:
- Brain dump processing
- Daily briefings
- Weekly reviews
- Habit tracking
"""

from .brain_dump import BrainDumpProcessor, process_brain_dump
from .daily_briefing import DailyBriefingGenerator, generate_briefing
from .weekly_review import WeeklyReviewGenerator, generate_weekly_review
from .habit_tracker import HabitTracker, log_habit, get_habit_streak, habit_summary

__all__ = [
    # Brain Dump
    "BrainDumpProcessor",
    "process_brain_dump",
    # Daily Briefing
    "DailyBriefingGenerator",
    "generate_briefing",
    # Weekly Review
    "WeeklyReviewGenerator",
    "generate_weekly_review",
    # Habit Tracker
    "HabitTracker",
    "log_habit",
    "get_habit_streak",
    "habit_summary",
]

__version__ = "1.0.0"
