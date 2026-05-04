# Contributing to Metis

Metis is built for the research community, and contributions from researchers are the best contributions.

---

## What to contribute

- **New agents** — Is there a specialist your field needs that isn't in the agent team? Epidemiology, ecology, economics, genomics, qualitative methods — every discipline has its own methodological standards that a specialist agent could enforce.
- **New MCP tools** — New capabilities for the 76-tool server.
- **Dashboard improvements** — The dashboard runs FastAPI + HTMX. Any researcher who knows Python and basic HTML can contribute.
- **Bug reports** — Open an issue with as much detail as possible: what you expected, what happened, and what version you're running.
- **Workflow descriptions** — Share how you use Metis. The best features come from actual research workflows.
- **Documentation** — Clearer explanations, translated documentation, better examples.

---

## Personal ↔ Public sync strategy

The repo is designed so that your personal research data never touches GitHub, and system improvements flow freely between your personal version and the public repo.

### How it works

```
GitHub (public)          Your machine (personal)
───────────────          ──────────────────────
system code         ←→   system code (same files)
agents (generic)    ←→   agents (generic + personal *-context.md)
README, docs        ←→   README, docs
                         journal/          (gitignored)
                         projects/active/  (gitignored)
                         outputs/reviews/  (gitignored)
                         system/.env       (gitignored)
                         agents/**/*-context.md (gitignored)
```

- **System improvements** you make (fixing a bug in `routers/work.py`, adding a new MCP tool, improving an agent's generic skill file) — commit and push. They go to GitHub.
- **Personal files** (your journal, your project cards, your domain context files, your `.env`) — these are gitignored and never pushed.
- **Pulling updates from GitHub** — `git pull origin main` updates system files without touching personal data.

### Before submitting a PR

1. Check that no personal files are staged: `git status`
2. Verify that `*-context.md` files are not staged (they match the gitignore pattern)
3. Make sure no API keys, email addresses, or personal names are in your diff
4. Run the dashboard locally and confirm the tab you changed still works

### Agent contributions

Each agent lives in `agents/<agent-slug>/`. The minimum for a new agent:

```
agents/my-agent/
├── system-prompt.md   # Full role definition, scope, output format
├── README.md          # What this agent does and when to use it
└── contract.md        # Scope, authority, coordination rules (optional)
```

See any existing agent for the structure. The system-prompt.md is what gets loaded when the agent is invoked — write it the way you would brief a specialist colleague.

---

## Development setup

```bash
# Clone
git clone https://github.com/SVerITG/metis.git
cd metis

# Install MCP server (auto-registers with Claude Code)
bash system/mcp-server/setup-mcp.sh

# Run dashboard
bash system/app-py/run.sh
# → http://127.0.0.1:8000

# Run MCP server standalone
~/.local/share/metis-mcp/run.sh
```

---

## Questions?

Open a GitHub Discussion, not an issue — discussions are better for questions, ideas, and feedback.
