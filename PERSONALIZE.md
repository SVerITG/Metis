# Personalising Metis

Metis ships as a clean template. Everything personal — your research domain, your projects, your literature, your notes — is added by you after installation and stored locally. None of it goes to GitHub.

This document explains what to personalise and how.

---

## Quick personalisation (10–15 minutes)

Run the configuration wizard from Claude Code (inside the metis/ folder):

```
/metis_config
```

This walks you through 13 sections:
1. Your name and contact email
2. Your research domain and field
3. Your active projects
4. Your PhD or main research arc (optional)
5. Your literature sources (PubMed topics, journal watchlists)
6. Your news topics and RSS feeds
7. Your writing style preferences
8. Your data protection settings
9. Which agents to activate
10. Your preferred AI models (Haiku / Sonnet / Opus)
11. Your working hours and morning briefing time
12. Your Zotero or Mendeley connection
13. Your notification preferences

After the wizard, restart Claude Desktop and Claude Code.

---

## Connecting your literature library

```
/metis-library-setup
```

Guided 3-step flow. Works with Zotero (API key), Mendeley (BibTeX export), or any BibTeX file.

---

## What stays personal (never pushed to GitHub)

| What | Where |
|------|-------|
| Your journal and session notes | `journal/` |
| Your ideas and captured thoughts | Database only |
| Your research outputs and reviews | `outputs/reviews/` |
| Your project cards | `projects/active/` |
| Your literature library | `knowledge/library/disease-areas/` |
| Your API keys (Zotero, etc.) | `system/.env` |
| Your user preferences | `system/config/user-preferences.json` |
| Your personalised agent context files | `agents/**/*-context.md` |

All of these are excluded from git in `.gitignore`. They stay on your machine and in OneDrive, but never appear on GitHub.

---

## Adding personal context to agents

After setup, you can add personal context to any agent. For example, if you work in infectious disease epidemiology and want the Epidemiologist agent to know your specific focus:

1. Open `agents/epidemiologist/`
2. Create a file `my-domain-context.md` (ends in `-context.md` → gitignored)
3. Write your domain context: your disease focus, your standard methods, your study designs

The agent will load this file automatically on its next run.

---

## Keeping your personal version in sync with GitHub

The public GitHub repository receives system improvements (dashboard code, MCP server, new agents, bug fixes). Your personal version stays in sync automatically because:

- Your personal data is in gitignored directories
- System files are not gitignored
- Pulling from GitHub updates the system without touching your personal data

To pull updates:

```bash
cd /path/to/your/metis/
git pull origin main
```

Your personal files are untouched. The system code is updated.

---

## Contributing improvements back

If you build a useful agent, improve the dashboard, or fix a bug:

1. Make sure your personal data files are gitignored (check `.gitignore`)
2. Commit only the system files
3. Open a pull request on GitHub

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.
