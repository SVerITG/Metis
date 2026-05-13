# Metis Edition Variants — K4

Defines what is included/excluded per edition for packaging and the installer course selector.

---

## Edition matrix

| Component | Full | Standard | MCP-only | Custom |
|---|---|---|---|---|
| MCP server (76 tools) | ✓ | ✓ | ✓ | configurable |
| FastAPI dashboard (9 tabs) | ✓ | ✓ | — | configurable |
| Claude Code hooks | ✓ | ✓ | — | configurable |
| Biostatistics course (~12 lessons) | ✓ | optional | — | configurable |
| Other placeholder courses (×14) | ✓ | ✓ | — | configurable |
| R / RStudio integration | ✓ | optional | — | configurable |
| Windows Task Scheduler jobs | ✓ | optional | — | configurable |
| NSSM background service | ✓ | — | — | configurable |
| Docker image | ✓ | — | — | configurable |
| PaperQA2 semantic library search | ✓ | ✓ | ✓ (library tools) | configurable |
| Spaced repetition seeding | ✓ | ✓ | — | configurable |

---

## Metis_PH editions

| Edition label | Base | What's different | install-state `profile` |
|---|---|---|---|
| **Full** | Standard + biostatistics course | +R/RStudio, +biostatistics course | `full` |
| **Standard** | Dashboard + MCP + hooks | Default install for most researchers | `standard` |
| **MCP-only** | MCP server only | For Claude Desktop integration, no dashboard | `mcp-only` |
| **Full without R** | Full minus R/RStudio | For non-R users who still want all content | `full-no-r` |

---

## Course inclusion logic

Installer asks: `"Include the Biostatistics for Epidemiologists course? (~50 MB, 12 lessons)"`

- If **yes** → copy `knowledge/courses/biostatistics/` to install path, seed `learning_courses` row
- If **no** → skip. User can run `/course-builder` anytime to generate a course later.

Placeholder courses (14 rows in `learning_courses`) are always included — they are DB records only, no file content.

---

## install-state.json profile values

```json
{
  "profile": "standard",          // full | standard | mcp-only | full-no-r | custom
  "courses_included": ["biostatistics"],  // list of course slugs included at install time
  "r_integration": false,          // true = RStudio launcher active
  "task_scheduler": false,         // true = Windows Task Scheduler jobs registered
  "dashboard": true                // false = MCP-only install
}
```

---

## File size reference (approximate, 2026-05-13)

| Component | Size |
|---|---|
| MCP server + venv | ~180 MB |
| FastAPI dashboard + static | ~8 MB |
| Biostatistics course (lessons only) | ~0.5 MB |
| SQLite DB (empty seed) | ~2 MB |
| Python venv (shared) | ~180 MB (same venv) |
| Library PDFs (user-provided) | varies |
| **Total installer (no PDFs)** | **~200 MB** |
