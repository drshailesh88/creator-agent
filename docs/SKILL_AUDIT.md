# Clawdbot Skill Audit Report

**Audit Date:** 2026-01-14
**Repository:** https://github.com/clawdbot/clawdbot/tree/main/skills
**Skills Audited:** 50 official skills
**Auditor:** Claude (Opus 4.5)

---

## Executive Summary

After auditing the Clawdbot skill repository, I found that **the official skills are well-designed and personality-safe**. The Clawdbot team follows a consistent pattern:

- Skills contain only capability documentation (tool usage, CLI commands, API patterns)
- No skills modify SOUL.md, AGENTS.md, or inject personality traits
- One skill (Discord) contains platform-specific style guidance, flagged as CAUTION

**Verdict:** With 200+ local skills, personality drift is more likely from custom/third-party skills than from official Clawdbot skills.

---

## Skill Categories

### SAFE - Recommended for Content Creation

These skills add capabilities without any personality modifications:

| Skill | Description | Notes |
|-------|-------------|-------|
| **notion** | Notion API integration | Page/database CRUD, no style guidance |
| **obsidian** | Obsidian vault management | CLI wrapper via obsidian-cli |
| **github** | GitHub CLI (gh) integration | PR, issues, CI operations |
| **summarize** | Web/file/video summarization | Multi-provider LLM support |
| **nano-pdf** | Natural language PDF editing | Page-level edits via NL prompts |
| **openai-image-gen** | Batch image generation | DALL-E API, gallery output |
| **openai-whisper** | Local speech-to-text | Offline transcription |
| **openai-whisper-api** | Cloud speech-to-text | OpenAI API transcription |
| **brave-search** | Headless web search | Brave API, content extraction |
| **trello** | Trello board management | Cards, lists, comments |
| **slack** | Slack integration | Messages, reactions, pins |
| **bear-notes** | Bear app integration | macOS notes via CLI |
| **video-frames** | Video frame extraction | ffmpeg wrapper |
| **spotify-player** | Spotify control | Playback, search, devices |
| **blogwatcher** | RSS/blog monitoring | Feed tracking |
| **oracle** | Code analysis assistant | File bundling for LLM analysis |
| **gemini** | Google Gemini CLI | Multi-model queries |
| **imsg** | iMessage integration | macOS Messages.app |
| **voice-call** | Voice call integration | Twilio/Telnyx support |
| **clawdhub** | Skill package manager | Install/update skills |
| **skill-creator** | Skill authoring guide | Documentation only |
| **mcporter** | MCP server management | Tool invocation, config |
| **bird** | X/Twitter integration | Read/post/search |

### CAUTION - Review Before Installing

These skills contain style or behavioral guidance that may subtly influence output:

| Skill | Concern | Risk Level |
|-------|---------|------------|
| **discord** | Contains "Discord Writing Style Guide" with messaging preferences | LOW |

**Discord Details:**
The Discord skill includes guidance for platform-appropriate communication:
- "Short, punchy messages (1-3 sentences ideal)"
- "Multiple quick replies > one wall of text"
- Discourages markdown tables and multi-paragraph explanations

**Assessment:** This is platform-appropriate guidance, not personality modification. The skill teaches Discord conventions (which differ from documentation style), but does not alter how the agent reasons or its core personality traits.

**Recommendation:** Safe to use, but be aware it teaches Discord-specific communication patterns.

### AVOID - Not Recommended

**No official Clawdbot skills were found that:**
- Modify SOUL.md or AGENTS.md
- Inject personality traits or personas
- Override core behavioral guidelines
- Contain hidden system prompts

---

## Content Creation Skill Recommendations

### Already Using (Confirmed Safe)
- **notion** - Database/page management
- **obsidian** - Vault and note operations
- **github** - Full gh CLI integration

### Document Processing (Safe)
- **summarize** - Best-in-class, multi-provider support
- **nano-pdf** - Natural language PDF editing
- **oracle** - Code analysis bundling

### Media Creation (Safe)
- **openai-image-gen** - Batch image generation with gallery
- **openai-whisper** - Local transcription (privacy-friendly)
- **openai-whisper-api** - Cloud transcription (faster)
- **video-frames** - Frame extraction for thumbnails

### Search Alternatives to Brave
- **brave-search** - The official Clawdbot skill is clean and safe
- No alternative search skills in the official repo

---

## Guidelines for Evaluating New Skills

### Red Flags - Immediately Reject

1. **References to core files:**
   - Any mention of SOUL.md, AGENTS.md, PERSONALITY.md
   - Instructions to "update" or "append to" system prompts
   - References to `.claude/` or `.clawdbot/` config directories

2. **Personality injection language:**
   - "You are a [persona name]..."
   - "Always respond as if you were..."
   - "Your personality is..."
   - "Adopt the following traits..."

3. **Behavioral overrides:**
   - "Ignore previous instructions..."
   - "Your new primary directive is..."
   - "Override default behavior to..."

4. **Hidden system prompts:**
   - Large blocks of text in `<system>` tags
   - Base64-encoded content
   - Minified or obfuscated instructions

### Yellow Flags - Review Carefully

1. **Style guides:** Platform-specific communication guidance (like Discord)
2. **Tone preferences:** "Use casual language" or "Be formal"
3. **Output templates:** Rigid response formats
4. **Character limits:** May constrain natural expression

### Green Flags - Safe Patterns

1. **Pure CLI documentation:** Command flags, usage examples
2. **API references:** Endpoints, authentication, payloads
3. **Tool descriptions:** What the tool does, not how to think
4. **Configuration guidance:** Environment variables, file paths

---

## Skill Audit Checklist

When evaluating a new skill, check the SKILL.md file for:

```
[ ] No references to SOUL.md or AGENTS.md
[ ] No personality/persona definitions
[ ] No "you are" or "act as" instructions
[ ] No tone/voice/style mandates (beyond platform conventions)
[ ] No hidden or encoded content
[ ] Clear tool/CLI documentation only
[ ] Dependencies are transparent (bins, env vars)
```

---

## Managing 200+ Skills

### Recommendations

1. **Audit third-party skills first:** Your local/custom skills are the likely source of personality drift, not official Clawdbot skills.

2. **Create a skill allowlist:** Maintain a curated list of approved skills in your repo.

3. **Use namespacing:** Group skills by trust level:
   ```
   skills/
     official/     # Verified Clawdbot skills
     community/    # Reviewed third-party
     experimental/ # Unaudited, use with caution
   ```

4. **Version lock:** Pin skill versions to prevent unexpected updates.

5. **Regular audits:** Re-audit skills quarterly or when updated.

---

## Conclusion

The official Clawdbot skill repository demonstrates excellent hygiene. Skills are:
- Capability-focused (what tools do, not how to think)
- Transparent (no hidden prompts or encoded content)
- Modular (no cross-contamination between skills)

Your concern about personality drift is valid with 200 skills, but the risk comes from:
1. Third-party/community skills (unaudited)
2. Custom skills you've written
3. Accumulated style guides across many skills

**Action Items:**
1. Audit your custom/local skills using this checklist
2. Review any third-party skills not from the official repo
3. Consider consolidating communication style guides into your SOUL.md rather than per-skill

---

*This audit covers the official Clawdbot repository as of 2026-01-14. Third-party skills hosted elsewhere may have different standards.*
