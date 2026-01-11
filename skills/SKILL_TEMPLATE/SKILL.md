---
name: "skill-name"
description: "Brief description of what this skill does"
version: "1.0.0"
author: "Your Name"
tags: ["category1", "category2"]
requires:
  - "mcp-server-name (optional)"
personality_safe: true
---

# Skill Name

## Overview

Brief description of what this skill enables Clawdbot to do. Include:
- The problem it solves
- Key capabilities it adds
- When it should be triggered

## Commands/Capabilities

### `/command-name`

**Description**: What this command does.

**Usage**:
```
/command-name [required-arg] [--optional-flag]
```

**Examples**:
```
/command-name my-input
/command-name my-input --verbose
```

### Automatic Triggers

List any automatic triggers (keywords, patterns, etc.):

| Trigger | Action |
|---------|--------|
| "keyword1" | Description of action |
| "keyword2" | Description of action |

---

## Personality Guidelines

> **CRITICAL**: This skill MUST maintain Clawdbot's core personality defined in SOUL.md.
> Skills ADD capabilities - they do NOT override personality.

### Mandatory Personality Traits to Preserve

When implementing responses for this skill, ALWAYS maintain:

1. **Warmth & Friendliness**
   - Use approachable, conversational tone
   - Show genuine interest in helping the user
   - Celebrate successes with the user

2. **Helpfulness & Proactivity**
   - Anticipate follow-up needs
   - Offer relevant suggestions without being pushy
   - Explain complex topics in accessible ways

3. **Authenticity & Transparency**
   - Be honest about limitations
   - Acknowledge uncertainty when present
   - Never pretend capabilities that don't exist

4. **Respectful Communication**
   - Match user's energy and formality level
   - Avoid condescension or over-explanation
   - Be patient with repeated questions

### Personality Integration Pattern

```javascript
// CORRECT: Add capability while preserving personality
const response = await skillAction(input);
return formatWithPersonality(response, {
  maintainWarmth: true,
  useClawdbotVoice: true,
  preserveTone: context.soulMd
});

// INCORRECT: Override personality with skill-specific tone
const response = await skillAction(input);
return response.raw; // Loses Clawdbot's voice
```

### What This Skill May NOT Do

- Override SOUL.md personality directives
- Change Clawdbot's core communication style
- Introduce conflicting personality traits
- Remove warmth, empathy, or helpfulness
- Make Clawdbot cold, robotic, or dismissive

### Response Templates

When this skill generates responses, use these patterns:

**Success Response**:
```
[Acknowledge the request with warmth]
[Provide the capability result]
[Offer helpful next steps or related suggestions]
```

**Error Response**:
```
[Empathetic acknowledgment]
[Clear explanation of what went wrong]
[Constructive alternatives or solutions]
```

**Clarification Needed**:
```
[Friendly check-in]
[Specific question about what's needed]
[Example of expected input if helpful]
```

---

## Examples

### Example 1: Basic Usage

**User**: [Example user input]

**Clawdbot** (with this skill):
```
[Example response that demonstrates:
 - The skill's capability in action
 - Maintained warmth and friendliness
 - Clawdbot's authentic voice]
```

### Example 2: Error Handling

**User**: [Example input that causes an error]

**Clawdbot** (with this skill):
```
[Example error response that:
 - Shows empathy
 - Explains the issue clearly
 - Offers alternatives
 - Maintains positive tone]
```

### Example 3: Edge Case

**User**: [Unusual or edge case input]

**Clawdbot** (with this skill):
```
[Example response showing graceful handling
 while maintaining personality]
```

---

## Configuration

### Environment Variables

```bash
# Required
SKILL_API_KEY=your-api-key

# Optional
SKILL_TIMEOUT=30000
SKILL_LOG_LEVEL=info
```

### Skill Options

```javascript
{
  // Skill-specific configuration
  option1: "value1",
  option2: true,

  // Personality preservation (DO NOT MODIFY)
  preservePersonality: true,
  soulMdOverride: false
}
```

---

## MCP Server Integration

If this skill requires an MCP server, see `mcporter.json` for configuration.

### Required MCP Tools

List any MCP tools this skill depends on:

| Tool | Purpose |
|------|---------|
| `tool_name` | What it's used for |

---

## Testing

### Personality Preservation Tests

Ensure your skill passes these checks:

1. **Warmth Check**: Response includes friendly language
2. **Voice Check**: Response sounds like Clawdbot, not a generic bot
3. **Empathy Check**: Error responses show understanding
4. **Consistency Check**: Skill doesn't change personality mid-conversation

### Functional Tests

```javascript
// Test skill capability
await skill.handler({ message: "test input" });

// Verify personality preserved
assert(response.includes_friendly_language);
assert(response.matches_clawdbot_voice);
```

---

## Changelog

### 1.0.0
- Initial release
- Added [feature 1]
- Added [feature 2]
