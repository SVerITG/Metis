# Phase 3 — MCP Server Updates
**Date:** 2026-04-03  
**Built by:** PKM Builder (Opus orchestrator) + Sonnet subagents

---

## Completed

### New tool files created

| File | Tools | Lines |
|------|-------|-------|
| `tools/ideas.py` | `capture_idea`, `get_ideas`, `add_journal_entry`, `get_journal`, `get_contacts`, `update_contact`, `get_glossary`, `add_glossary_term`, `find_connections`, `cross_pollinate`, `assemble_brainstorm_context` | 668 |
| `tools/safety.py` | `check_data_safety` | 136 |
| `tools/files.py` | `scan_tracked_files`, `add_tracked_file`, `remove_tracked_file` | 177 |
| `tools/intelligence.py` | `generate_daily_insight`, `get_daily_insight`, `get_new_publications`, `mark_publications_read`, `get_user_topics`, `add_user_topic` | 370 |
| `tools/library.py` | `archive_library_item`, `remove_library_item`, `search_literature_extended` | ~120 |
| `tools/config_tools.py` | `get_user_profile`, `add_specialist_context`, `toggle_context`, `list_contexts` | ~130 |
| `tools/images.py` | `generate_image`, `list_generated_images` | ~170 |

### Existing files extended

- `tools/projects.py` — added `archive_project`, `unarchive_project`, `remove_project`
- `tools/research.py` — already existed from Phase 1 (`get_research_context`)

### Infrastructure updated

- `server.py` — all 7 new modules imported
- `pyproject.toml` — added dependencies: `pyyaml>=6.0`, `requests>=2.28`, `google-genai>=1.0`

### New SQLite tables (created on first tool call)

| Table | Used by |
|-------|---------|
| `ideas` | `capture_idea`, `get_ideas` |
| `journal_entries` | `add_journal_entry`, `get_journal` |
| `contacts` | `get_contacts`, `update_contact` |
| `glossary` | `get_glossary`, `add_glossary_term` |
| `tracked_files` | `scan_tracked_files`, `add_tracked_file` |
| `daily_insights` | `generate_daily_insight`, `get_daily_insight` |
| `new_publications` | `get_new_publications`, `mark_publications_read` |
| `user_topics` | `get_user_topics`, `add_user_topic` |

---

## Skipped / deferred

- **Phase 3.3 — WhatsApp webhook** (FastAPI endpoint): deferred to Phase 5 alongside scheduling automation — requires a running server process, separate from MCP
- **Phase 3.6 — Thinking profile tools** (`thinking_profile.py`): deferred to Phase 4 — the dashboard Ideas tab needs to be built first to validate what events to record

---

## Issues found / notes

- `uv` not on WSL PATH — runtime import test skipped; all 7 files pass `python3 -m py_compile` (syntax verified)
- `google-genai` is optional at runtime — `images.py` handles `ImportError` gracefully with an install instruction
- `pyyaml` is optional at runtime — `config_tools.py` handles `ImportError` gracefully
- `library_seeded` table may not have a `status` column in existing DBs — `library.py` runs ALTER TABLE migration automatically on first call

---

## Verification

To verify after installing dependencies:

```bash
cd metis/08_system/mcp-server
pip install -e ".[dev]"   # or: uv pip install -e .
python -c "from metis_mcp.tools import ideas, safety, files, intelligence, library, config_tools, images; print('OK')"
```

To re-install with new dependencies:
```bash
pip install pyyaml requests google-genai --break-system-packages
# or via uv: uv add pyyaml requests google-genai
```
