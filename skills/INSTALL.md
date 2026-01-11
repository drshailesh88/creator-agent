# Installing Skills in Clawdbot

This guide explains how to install the Life OS skills into your Clawdbot.

## Prerequisites

- Clawdbot running on your VPS
- Notion API key (for Pensieve, Notion skills)
- GitHub token (for backup skill)

## Quick Install (All Skills)

```bash
# On your VPS, clone this repo
cd ~/.clawdbot/skills
git clone https://github.com/drshailesh88/creator-agent life-os-suite

# Create symlinks for each skill
ln -s life-os-suite/skills/pensieve pensieve
ln -s life-os-suite/skills/notion notion
ln -s life-os-suite/skills/life-os life-os
ln -s life-os-suite/skills/github-backup github-backup

# Reload Clawdbot
clawd reload
```

## Individual Skill Installation

### Pensieve (Memory Palace)
```bash
cp -r skills/pensieve ~/.clawdbot/skills/
```
**Requires**: `NOTION_API_KEY` in environment

### Notion Integration
```bash
cp -r skills/notion ~/.clawdbot/skills/
```
**Requires**: `NOTION_API_KEY` in environment

### Life OS (Brain Dump, Reviews, Habits)
```bash
cp -r skills/life-os ~/.clawdbot/skills/
```
**Requires**: `NOTION_API_KEY` for data storage

### GitHub Backup
```bash
cp -r skills/github-backup ~/.clawdbot/skills/
```
**Requires**: `GITHUB_TOKEN`, `GITHUB_BACKUP_REPO` in environment

## Environment Variables

Add these to your `.env` or environment:

```bash
# Notion
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxx

# GitHub Backup
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
GITHUB_BACKUP_REPO=your-username/pensieve-backup

# LLM Keys (for content creation)
ZHIPU_API_KEY=xxxxxxxxxxxxx        # GLM 4.7 (primary)
MOONSHOT_API_KEY=xxxxxxxxxxxxx     # Kimi K2 (fallback 1)
OPENAI_API_KEY=xxxxxxxxxxxxx       # GPT-4o mini (fallback 2)
```

## Personality Safety

All skills in this repo follow the **personality-safe template**. They:

1. NEVER modify SOUL.md or AGENTS.md
2. ADD capabilities without changing Clawdbot's warmth
3. Reference the core personality, don't override it

If Clawdbot's personality changes after installing a skill, the skill is broken - not Clawdbot.

## Verifying Installation

After installation, test each skill:

```
You: "Save this to my Pensieve: Today I realized..."
Clawdbot: [Should respond warmly, save to Notion]

You: "Brain dump: I've been thinking about..."
Clawdbot: [Should process thoughts, maintain friendly tone]

You: "Backup my Pensieve now"
Clawdbot: [Should backup to GitHub, confirm warmly]
```

## Troubleshooting

### Skill not loading
- Check `~/.clawdbot/skills/[skill-name]/SKILL.md` exists
- Run `clawd reload`

### Notion connection failing
- Verify `NOTION_API_KEY` is set
- Ensure Notion integration has access to your databases

### GitHub backup failing
- Verify `GITHUB_TOKEN` has repo write permissions
- Check `GITHUB_BACKUP_REPO` is correct (username/repo-name)

## Skill Structure Reference

```
skill-name/
├── SKILL.md          # Required: Skill definition
├── mcporter.json     # Optional: MCP server config
├── *.py              # Optional: Python implementation
└── README.md         # Optional: Detailed docs
```

## Creating New Skills

Use the template:
```bash
cp -r skills/SKILL_TEMPLATE ~/.clawdbot/skills/my-new-skill
# Edit SKILL.md with your skill's details
```

See `skills/SKILL_TEMPLATE/README.md` for detailed instructions.
