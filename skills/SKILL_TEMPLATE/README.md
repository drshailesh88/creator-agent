# Clawdbot Skill Template

This template provides the standard structure for creating personality-safe skills for Clawdbot. All skills in the ClawdHub ecosystem should follow this format to ensure consistent quality and, most importantly, preservation of Clawdbot's core personality.

## Why This Template Exists

Clawdbot has a carefully crafted personality defined in `SOUL.md`. Skills extend Clawdbot's capabilities, but they must NEVER override or conflict with this core personality. This template enforces that principle.

## Quick Start

### 1. Copy the Template

```bash
# Create your new skill directory
cp -r skills/SKILL_TEMPLATE skills/my-new-skill

# Rename and customize
cd skills/my-new-skill
```

### 2. Customize SKILL.md

Edit `SKILL.md` with your skill's details:

```yaml
---
name: "my-awesome-skill"
description: "Does something awesome while keeping Clawdbot friendly"
version: "1.0.0"
author: "Your Name"
tags: ["utility", "productivity"]
personality_safe: true  # Keep this true!
---
```

### 3. Configure MCP Server (if needed)

If your skill requires an MCP server, edit `mcporter.json`:

```json
{
  "name": "my-awesome-skill-mcp",
  "tools": [
    {
      "name": "awesome_action",
      "description": "What it does"
    }
  ]
}
```

### 4. Implement Your Skill

Create your implementation files following the patterns in the template.

## Template Files

### SKILL.md

The main skill definition file in ClawdHub format. Contains:

| Section | Purpose |
|---------|---------|
| **YAML Frontmatter** | Metadata (name, version, author, tags) |
| **Overview** | What the skill does |
| **Commands/Capabilities** | Available commands and triggers |
| **Personality Guidelines** | How to maintain Clawdbot's voice |
| **Examples** | Usage examples showing personality preservation |
| **Configuration** | Environment variables and options |
| **Testing** | How to verify the skill works correctly |

### mcporter.json

MCP (Model Context Protocol) server configuration for skills that need external tool integration:

| Field | Purpose |
|-------|---------|
| `server` | How to start the MCP server |
| `tools` | Available tools with schemas |
| `resources` | Data resources exposed |
| `personality` | Personality preservation settings |
| `clawdbotIntegration` | Trigger configuration |

### Implementation Files (you create these)

```
my-skill/
├── SKILL.md           # From template
├── mcporter.json      # From template (if needed)
├── README.md          # This file (customize for your skill)
├── index.js           # Main skill implementation
├── server.js          # MCP server (if using MCP)
├── handlers/          # Request handlers
├── utils/             # Utility functions
└── tests/             # Test files
```

## Personality Preservation Checklist

Before submitting your skill to ClawdHub, verify:

- [ ] `personality_safe: true` in SKILL.md frontmatter
- [ ] Personality Guidelines section is complete and followed
- [ ] All example responses demonstrate Clawdbot's warmth
- [ ] Error messages are empathetic, not robotic
- [ ] Skill doesn't introduce conflicting personality traits
- [ ] `preserveSoulMd: true` in mcporter.json (if applicable)
- [ ] Tested with personality preservation tests

## The Golden Rule

> **Skills ADD capabilities. Skills do NOT change personality.**

Your skill should make Clawdbot MORE helpful, not DIFFERENT. After installing your skill, Clawdbot should still:

- Sound warm and friendly
- Be authentically helpful
- Show empathy in error situations
- Match the user's energy
- Feel like the same Clawdbot

## Example: Good vs Bad Implementation

### Bad: Skill overrides personality

```javascript
// DON'T DO THIS
async function handleRequest(input) {
  const result = await processData(input);
  return `RESULT: ${result}`; // Cold, robotic response
}
```

### Good: Skill extends while preserving personality

```javascript
// DO THIS
async function handleRequest(input, context) {
  const result = await processData(input);

  // Format with Clawdbot's voice
  return formatResponse({
    data: result,
    personality: context.soulMd,
    style: {
      warm: true,
      helpful: true,
      suggestNextSteps: true
    }
  });
}
```

## Integration with SOUL.md

Your skill should reference Clawdbot's personality from SOUL.md. Key traits to maintain:

1. **Warmth**: Friendly, approachable communication
2. **Helpfulness**: Proactive assistance, relevant suggestions
3. **Authenticity**: Honest about capabilities and limitations
4. **Empathy**: Understanding user frustration, celebrating successes
5. **Adaptability**: Matching user's formality and energy level

## Testing Your Skill

### Personality Tests

```bash
# Run personality preservation tests
npm run test:personality

# Check voice consistency
npm run test:voice

# Verify warmth in responses
npm run test:warmth
```

### Functional Tests

```bash
# Run all tests
npm test

# Test specific capability
npm run test:capability -- --name "my-feature"
```

## Submitting to ClawdHub

1. Ensure all checklist items are complete
2. Run the full test suite
3. Create a pull request with:
   - Completed SKILL.md
   - mcporter.json (if applicable)
   - Implementation files
   - Test results showing personality preservation

## Getting Help

- Review existing skills in `/skills/` for examples
- Check SOUL.md for personality reference
- Ask in the ClawdHub community

## License

MIT - Use this template freely for your Clawdbot skills.

---

*Remember: A great skill makes Clawdbot more capable while keeping Clawdbot... Clawdbot.*
