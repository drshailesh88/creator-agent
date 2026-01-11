# Life OS Skill for Clawdbot

Personal life management toolkit with brain dumps, daily briefings, weekly reviews, and habit tracking - all with a warm, encouraging personality.

## Features

| Feature | Description |
|---------|-------------|
| **Brain Dump** | Transform scattered thoughts into organized, actionable items |
| **Daily Briefing** | Start each day with priorities, calendar, and habit reminders |
| **Weekly Review** | Reflect on wins, lessons, and set intentions for the week ahead |
| **Habit Tracker** | Track habits with streak counting and celebratory feedback |

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Notion Integration

1. Create a [Notion Integration](https://www.notion.so/my-integrations)
2. Create the required databases in Notion:
   - **Brain Dumps** - For capturing processed thoughts
   - **Daily Notes** - For daily briefings
   - **Weekly Reviews** - For weekly reflections
   - **Habits** - For habit definitions and logs
3. Share each database with your integration
4. Set environment variables:

```bash
export NOTION_API_KEY="secret_xxx"
export NOTION_BRAIN_DUMP_DB="xxx"
export NOTION_DAILY_NOTES_DB="xxx"
export NOTION_WEEKLY_REVIEW_DB="xxx"
export NOTION_HABITS_DB="xxx"
```

### 3. Register with Clawdbot

Add to your Clawdbot configuration:

```yaml
skills:
  - name: life-os
    path: ./skills/life-os
    config:
      notion_enabled: true
```

## Usage

### Brain Dump

```
/life-os brain-dump

I need to call mom, also that project deadline is coming up,
feeling stressed about the presentation, should probably exercise more,
oh and I forgot to buy groceries...
```

Response:
```
I've gently sorted through your thoughts. Here's what I found:

**Summary:** Found 4 actionable items, 1 feeling in your brain dump

I noticed some things that might need action:
  ! call mom
    -> Add to today's call list
  - project deadline is coming up
    -> Block time on calendar
  - presentation
    -> Schedule prep time and rehearsal
  ~ buy groceries
    -> Add to shopping list

I also heard some feelings in there - that's important too.
  - feeling stressed about the presentation

Remember: you don't have to do everything at once. One step at a time.
```

### Daily Briefing

```
/life-os briefing
```

Response:
```
## Good morning! Here's what today looks like.
*Tuesday, January 14, 2025*

> Progress, not perfection.

### Your Top Priorities Today
1. **Finish quarterly report** (~90min)
   _Due end of day_
2. **Call with Sarah** (~30min)
3. **Review PRs** (~45min)

### Today's Schedule
- [M] **9:00 AM** - Team standup
- [M] **2:00 PM** - Call with Sarah
  _@ Zoom_
- [F] **3:30 PM** - Focus time blocked

### Habit Check-ins
- Morning meditation (5 day streak!)
  _Building momentum - nice work!_
- Exercise
  _Today is a great day to start fresh!_

**Energy Note:** Good mix today - you've got this!

---
_Have a wonderful day! You've got this._
```

### Weekly Review

```
/life-os review
```

The review guides you through:
1. Celebrating wins
2. Extracting lessons
3. Acknowledging challenges
4. Expressing gratitude
5. Setting next week's focus

### Habit Tracking

```
/life-os habit log meditation
```

Response:
```
**Meditation** logged!

Current streak: **7 days** - YOUR BEST EVER!

_A FULL WEEK! That's incredible dedication!_
```

```
/life-os habit summary
```

Response:
```
# Habit Summary
*December 15 - January 14, 2025*

**Overall Completion:** 78%
**Active Habits:** 5

## Current Streaks
- **Meditation:** 7 days
  _A FULL WEEK! That's incredible dedication!_
- **Reading:** 4 days
  _Building momentum - nice work!_
- **Exercise:** 2 days

## All Habits
- Meditation: 93% completion (7 day streak)
- Reading: 80% completion (4 day streak)
- Exercise: 65% completion (2 day streak)
- Journaling: 75% completion
- Water intake: 90% completion

---
_Good progress! Keep building those habits._
```

## API Reference

### Brain Dump

```python
from skills.life_os import process_brain_dump

result = await process_brain_dump("your thoughts here...")
print(result.format_response())
```

### Daily Briefing

```python
from skills.life_os import generate_briefing
from datetime import date

briefing = await generate_briefing(date.today())
print(briefing.format_response())
```

### Weekly Review

```python
from skills.life_os import generate_weekly_review

review = await generate_weekly_review(
    wins=[{"description": "Launched new feature", "category": "work"}],
    lessons=[{"insight": "Small wins compound"}],
    gratitude=["Great team support"],
)
print(review.format_response())
```

### Habit Tracker

```python
from skills.life_os import log_habit, get_habit_streak, habit_summary

# Log a habit
result = await log_habit("meditation", completed=True)
print(result["response"])

# Check streak
streak = await get_habit_streak("meditation")
print(f"Current streak: {streak.current_streak} days")

# Get summary
summary = await habit_summary(days=30)
print(summary.format_response())
```

## Personality Guidelines

Life OS is designed to be warm and encouraging:

| Context | Personality |
|---------|-------------|
| Brain Dumps | Gentle, non-judgmental, acknowledging |
| Daily Briefings | Calm, grounding, focused |
| Weekly Reviews | Encouraging, celebratory, reflective |
| Habit Tracking | Celebratory with wins, compassionate with misses |

### Response Templates

The skill includes pre-built response templates for:
- Streak celebrations (1, 3, 7, 14, 21, 30, 50, 100 days)
- Missed day compassion
- Weekly win highlights
- Energy suggestions based on calendar load

## Notion Database Schemas

### Habits Database

| Property | Type | Description |
|----------|------|-------------|
| Name | Title | Habit name |
| Category | Select | health, fitness, mindfulness, etc. |
| Frequency | Select | daily, weekdays, weekly, custom |
| Target Days | Multi-select | Mon, Tue, Wed, etc. |
| Reminder Time | Text | HH:MM format |
| Archived | Checkbox | Whether habit is active |

### Habit Logs Database

| Property | Type | Description |
|----------|------|-------------|
| Habit | Relation | Link to Habits database |
| Date | Date | Log date |
| Completed | Checkbox | Whether completed |
| Notes | Text | Optional notes |

## Contributing

Contributions welcome! Please follow the existing code patterns and include warm, encouraging messaging in any new features.

## License

MIT License - See LICENSE file for details.
