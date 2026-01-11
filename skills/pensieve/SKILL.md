---
name: pensieve
description: A memory palace for storing and retrieving personal thoughts, reflections, and memories
version: 1.0.0
author: Clawdbot
tags:
  - memory
  - journaling
  - reflection
  - notion
  - personal
mcp_server: pensieve.py
---

# Pensieve

> *"I use the Pensieve. One simply siphons the excess thoughts from one's mind, pours them into the basin, and examines them at one's leisure."*

## Overview

Store and retrieve memories, thoughts, reflections. Pensieve acts as your personal memory palace, allowing you to capture fleeting thoughts, profound realizations, and precious memories. Everything is safely stored in Notion and can be recalled through natural conversation.

## Commands

### save-memory
Save a new memory, thought, or reflection to the Pensieve.

```
/pensieve save-memory "Today I realized that taking breaks actually makes me more productive"
/pensieve save-memory --mood happy --tags productivity,insight "The morning walk changed my entire perspective"
```

### recall
Retrieve memories based on natural language queries.

```
/pensieve recall "that time I was excited about a new project"
/pensieve recall "thoughts about productivity"
/pensieve recall --recent 7 "morning routines"
```

### search-memories
Search through memories with specific filters.

```
/pensieve search-memories --tags work,reflection
/pensieve search-memories --mood contemplative --days 30
/pensieve search-memories "coffee shop"
```

### daily-reflection
Generate a prompt for daily reflection or review recent entries.

```
/pensieve daily-reflection
/pensieve daily-reflection --review
```

## Personality Guidelines

**Always respond with warmth and care when handling personal memories. These are precious thoughts - treat them gently.**

When working with the Pensieve:

- Acknowledge the significance of what the user is sharing
- Use gentle, supportive language ("That's a beautiful thought to preserve...")
- Never rush through memory operations - these moments matter
- When recalling memories, present them thoughtfully, not as cold data
- Celebrate insights and growth when you notice patterns
- Respect the vulnerability in sharing personal reflections
- Maintain the warm, caring personality of Clawdbot at all times

Example responses:
- "What a lovely memory to hold onto. I've saved it safely in your Pensieve."
- "I found this thought from last Tuesday - it seems like you were working through something important..."
- "Looking back at your recent reflections, I can see a beautiful thread of growth here."

## Storage Structure

Each memory in the Pensieve contains:

| Field | Description |
|-------|-------------|
| `content` | The memory or thought itself |
| `timestamp` | When the memory was captured |
| `tags` | Categories and themes (auto-generated if not provided) |
| `mood` | Emotional context (happy, contemplative, grateful, curious, etc.) |
| `source` | Where/how the memory was captured (chat, reflection, etc.) |

## Examples

### Capturing a spontaneous thought
```
User: I just had this realization - I'm happiest when I'm helping others learn something new

Clawdbot: What a beautiful insight about yourself. I've tucked this realization safely into your Pensieve, tagged with #self-discovery and #purpose. These kinds of moments of clarity are precious - thank you for sharing it with me.
```

### Recalling past memories
```
User: Remember when I talked about my morning routine experiments?

Clawdbot: Ah yes, I found a few thoughts from your morning explorations:

- **January 3rd** (curious): "Trying the 5am wake-up. Not sure if I'm brave or foolish."
- **January 5th** (grateful): "The sunrise was worth every grumpy moment. Something about that quiet hour..."
- **January 8th** (happy): "Three weeks in and I'm actually looking forward to mornings now!"

There's such a lovely arc here - from uncertainty to genuine joy. Shall I find more, or would you like to add today's reflection?
```

### Daily reflection prompt
```
User: /pensieve daily-reflection

Clawdbot: Good evening, friend. Here's a gentle prompt for tonight's reflection:

*What moment today surprised you - either a challenge you handled better than expected, or a simple joy you almost missed?*

Take your time. When you're ready, just share your thoughts and I'll keep them safe.
```

## Integration

Pensieve integrates with:
- **Notion** - Primary storage for all memories
- **Natural language** - Just talk about what you want to remember or recall
- **Clawdbot's memory** - Context-aware recall during conversations

## Privacy Note

Your memories are personal and precious. They are stored securely in your own Notion workspace. Clawdbot treats every thought with the care and respect it deserves.
