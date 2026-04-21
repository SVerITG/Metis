# Metis Dashboard — Design Brief for Claude Design

## What this is

**Metis** is a personal research operating system for a senior epidemiologist / PhD researcher. It is a **local-first web dashboard** (FastAPI + HTMX + Bootstrap 5) that runs at `http://127.0.0.1:8000`. It connects to a local SQLite database and 76 AI tools via an MCP server. No cloud. No login screen. This is a productivity tool for one person.

The goal of this session with Claude Design is to **redesign the visual layer** — templates, CSS, and layout — to create a polished, professional interface befitting a research command center. The backend (Python routers, database queries, HTMX wiring) is **not to be changed**. Only `templates/`, `static/styles.css`, and optionally `static/app.js` for minor visual enhancements.

---

## Tech stack & constraints

| Item | Detail |
|------|--------|
| Framework | FastAPI + Jinja2 templates |
| Interactivity | **HTMX 1.9** — no React, no Vue, no SPA |
| CSS base | Bootstrap 5.3.3 (CDN) + custom `styles.css` |
| Icons | Bootstrap Icons 1.11 |
| Typography | System font stack (`-apple-system`, `Inter`, `SF Pro`) |
| CDN dependencies | Bootstrap CSS/JS (CDN), Bootstrap Icons (CDN), HTMX (CDN) |
| Local files | `/static/styles.css`, `/static/app.js` |
| Template engine | Jinja2 — `{% if %}`, `{% for %}`, `{{ variable }}` |
| Tab navigation | HTMX swaps `#tab-content` div on navbar click |
| Partials | Each tab section loads via `hx-get="/api/partial/..."` on page load |
| No build step | Plain CSS and JS — no Webpack, no Tailwind, no PostCSS |

**HTMX pattern used everywhere:**
```html
<div hx-get="/api/partial/tab/section"
     hx-trigger="load"
     hx-swap="innerHTML">
  <!-- Skeleton placeholder shown while loading -->
</div>
```

---

## Current design direction

The current design is **macOS-inspired glassmorphism**:
- Background: `#f5f5f7` (macOS system gray)
- Cards: `rgba(255,255,255,0.85)` with `backdrop-filter: blur(20px)`
- Primary blue: `#0071e3` (macOS blue)
- Accent green: `#30a46c`
- Text: `#1d1d1f` (near-black), muted: `#6e6e73`
- Radius: 12px cards, 8px buttons
- Font: `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", system-ui`

The navbar has a frosted glass effect (`backdrop-filter: saturate(180%) blur(20px)`).

**Current problems:**
1. The design feels inconsistent — some components use the macOS tokens, others still use legacy colors like `#174c4f` (teal) and `#faf9f6` from an older version
2. There are TWO visual identities in conflict: macOS-clean (top of CSS) and the legacy teal/parchment theme (bottom of CSS, ~1500 lines of legacy CSS)
3. The legacy classes (`.kanban-col`, `.gallery-card`, `.morning-brief`, etc.) override Bootstrap correctly but don't match the macOS token system
4. The navbar tab labels disappear on small screens (`.nav-tab-label` has no responsive handling)
5. No dark mode support
6. The capture modal has no animation
7. Stat cards have no visual hierarchy — numbers don't pop

---

## The 9 tabs

### 1. Today (`/today`)
**Purpose:** Daily briefing — what to focus on, what happened overnight, git status.

**Sections (loaded as HTMX partials):**
- **Greeting strip**: Time-based greeting ("Good morning, Stef") + today's date
- **Overnight summary**: 3 counters — news briefs, ideas, meetings captured
- **Focus card**: Top active project + its next step
- **Scan**: Git status button (POST) → shows uncommitted changes
- **Token footer**: Agent calls today + total tokens used

**Design goal:** Should feel like a calm morning newspaper front page. High information density but gentle. The greeting should be large and warm.

---

### 2. Knowledge (`/knowledge`)
**Purpose:** Library of concept notes + research literature.

**Sections:**
- **Stats row**: 4 stat cards — library notes count, domain count, literature count, new this month
- **Library cards grid**: Cards from `knowledge/library/*.md` — title, domain badge, tags, 2-line summary
- **Literature table**: Research papers from `inputs/literature/` — title, authors, year, source
- **Domain breakdown**: Papers grouped by domain (HAT, methods, surveillance, etc.)
- **Search bar**: Live HTMX search across both library and literature
- **Graph view**: D3 force-directed knowledge graph (tab within Knowledge)

**Design goal:** The library cards should look like a card catalog — clean grid, domain color-coded. Literature table should be clean and scannable. The knowledge graph needs a full-height container.

---

### 3. Thinking (`/thinking`)
**Purpose:** Ideas, personal notes, open questions, and brainstorm sessions.

**Sections:**
- **Ideas list**: 30 most recent ideas — content excerpt, tags, date
- **Notes list**: 20 most recent personal notes
- **Questions list**: 15 open research questions
- **Brainstorm panel**: Topic input + 5 steering buttons (Expand/Focus/Challenge/Synthesize/Connect) + "Copy prompt" button. Recent sessions list below.

**Design goal:** The brainstorm panel should feel like a creative workspace — slightly warmer background, less clinical than other tabs.

---

### 4. Planner (`/planner`)
**Purpose:** Project management — Kanban board, PhD focus, timeline.

**Sections:**
- **Kanban**: 3 columns — Someday / Incubating / Active (projects, not tasks)
- **Focus board**: PhD-specific active projects + tasks mentioning article/Article
- **Timeline**: Active + incubating projects ordered by priority (no actual dates in DB yet)

**Design goal:** Kanban columns should feel spacious. Active column should be visually distinguished (blue border or badge). The focus board should feel urgent.

---

### 5. Work (`/work`)
**Purpose:** Task list + active project overview.

**Sections:**
- **Stats row**: Open tasks, overdue tasks, done this week, active projects
- **Task list**: Filterable (open/all/done) — title, project/category, status badge, due date
- **Active projects**: Cards with title, domain, priority, next step

**Design goal:** The task list is the most-used section. It needs to be highly scannable. Overdue items should pop red. Priority colors matter.

---

### 6. Meetings (`/meetings`)
**Purpose:** Meeting history and structured notes.

**Sections:**
- Stats: total meetings, decisions, action items this month
- Filterable meeting table: title, date, type, attendees, decisions/actions badge

---

### 7. Learning (`/learning`)
**Purpose:** Self-directed learning tracker.

**Sections:**
- **Due today**: Spaced repetition items due for review (cards in DB)
- **Active courses**: Progress bars — title, category, % complete
- **Completed courses**: List of finished courses
- **Competencies**: Skill grid — topic, domain, level badge (beginner/intermediate/advanced/expert)

**Design goal:** Course progress bars should be prominent. Competency cards could use color by level.

---

### 8. Teach (`/teach`)
**Purpose:** Teaching support — course management, content tools.

**Sections:**
- **Course cards**: For each course (title, code, semester, student count)
  - Literature alerts panel (lazy-loaded by intersection)
  - News alerts panel (lazy-loaded by intersection)
  - Action buttons: Chat / Co-work / Slides / Assessment / Q-bank / Gap analysis

**Design goal:** Course cards should feel professional and distinct. Buttons copy Claude Code prompts to clipboard.

---

### 9. Metis (`/metis`)
**Purpose:** System monitoring — agent activity, trust, observability.

**Sections:**
- **Stats row**: Runs today, tokens today, total runs, active agents
- **Agent run history**: Table of recent agent runs — slug, task summary, timestamp, token count, status
- **Agent registry**: Grid of all 28 registered agents — slug, name, trust tier badge, description
- **Span waterfall**: Observability view of agent execution traces (Phase 5.9)
- **Consent ledger**: Log of data processing decisions
- **Network policy badge**: Current policy (strict/offline/normal)
- **System info**: RC root path, DB path, DB size

---

## Navigation bar

```
[Metis logo] [Today] [Knowledge] [Thinking] [Planner] [Work] [Meetings] [Learning] [Teach] [Metis]    [+Capture] [🛡 Local-first]
```

- 9 nav tab buttons: icon + label
- Active tab: highlighted in blue
- Right side: blue pill "Capture" button (Ctrl+K) + green trust badge
- Sticky on scroll, frosted glass background

---

## Capture modal (Ctrl+K)

A full-screen overlay with a centered card:
- Large textarea
- Prefix detection: `i:` = Idea (blue), `n:` = Note (green), `t:` = Task (yellow), `q:` = Question (purple)
- Live badge update as user types
- Submit → POST to `/api/capture`
- Close on backdrop click or Escape

---

## Design requests for Claude Design

### Priority 1 — Unify the design system
Remove the legacy `#174c4f` teal and `#faf9f6` parchment colors throughout. Replace all components with the macOS token system (defined in `:root`). The current CSS is ~2700 lines — many selectors are dead code or duplicates.

### Priority 2 — Stat cards
The stat cards (4-column rows on Work, Knowledge, Metis) need a clear visual treatment. Numbers should be large (2rem+), labels small. Currently they're plain Bootstrap cards with no visual hierarchy.

### Priority 3 — Task list
Make the task list more scannable. Overdue dates in red. Priority indicator (left border or dot). Status badge colors: open = blue, done = green, cancelled = gray.

### Priority 4 — Kanban board
Active column should be visually distinct (blue left border on cards, or column header in blue). Project cards should show a small priority pip.

### Priority 5 — Capture modal animation
Add a smooth slide-in/fade-in animation when the capture overlay opens. Currently appears instantaneously.

### Priority 6 — Knowledge graph container
The D3 graph needs a fixed-height container (`min-height: 600px`) and should fill the full tab width. Currently it's constrained by Bootstrap grid.

### Priority 7 — Responsive navbar
On narrow screens, hide the text labels on nav buttons (show only icons). The current `.nav-tab-label` class exists but has no responsive logic.

### Priority 8 — Dark mode (optional, low priority)
Prefers-color-scheme support. Dark: `#1c1c1e` background, `#2c2c2e` cards.

---

## File structure

```
metis/system/app-py/
├── main.py                    # FastAPI app — do not modify
├── db.py                      # SQLite helpers — do not modify
├── routers/                   # Route handlers — do not modify
│   ├── today.py
│   ├── knowledge.py
│   ├── work.py
│   ├── planner.py
│   ├── meetings.py
│   ├── learning.py
│   ├── thinking.py
│   ├── teach.py
│   ├── metis_tab.py
│   └── capture.py
├── templates/
│   ├── base.html              # Nav + layout shell ← can modify
│   ├── today.html             # Today tab template ← can modify
│   ├── knowledge.html         ← can modify
│   ├── work.html              ← can modify
│   ├── planner.html           ← can modify
│   ├── meetings.html          ← can modify
│   ├── learning.html          ← can modify
│   ├── thinking.html          ← can modify
│   ├── teach.html             ← can modify
│   ├── metis_tab.html         ← can modify
│   └── partials/              # HTMX fragment templates ← can modify
│       ├── today_greeting.html
│       ├── today_overnight.html
│       ├── today_focus.html
│       ├── today_scan.html
│       ├── today_token_footer.html
│       ├── knowledge_stats.html
│       ├── knowledge_library.html
│       ├── knowledge_literature.html
│       ├── knowledge_domains.html
│       ├── knowledge_search.html
│       ├── knowledge_graph.html
│       ├── work_stats.html
│       ├── work_tasks.html
│       ├── work_projects.html
│       ├── planner_kanban.html
│       ├── planner_focus.html
│       ├── planner_timeline.html
│       ├── meetings_stats.html
│       ├── meetings_table.html
│       ├── learning_due.html
│       ├── learning_courses.html
│       ├── learning_completed.html
│       ├── learning_competencies.html
│       ├── thinking_ideas.html
│       ├── thinking_notes.html
│       ├── thinking_questions.html
│       ├── thinking_brainstorm_sessions.html
│       ├── teach_courses.html
│       ├── teach_lit_alerts.html
│       ├── teach_news_alerts.html
│       ├── metis_stats.html
│       ├── metis_runs.html
│       ├── metis_agents.html
│       ├── metis_traces.html
│       ├── metis_consent.html
│       ├── metis_system_info.html
│       └── capture_modal.html
├── static/
│   ├── styles.css             ← primary target for redesign
│   └── app.js                 ← minor JS enhancements only
└── run.sh                     # launcher — do not modify
```

---

## Running the dashboard

```bash
# Start the dashboard
bash metis/system/app-py/run.sh
# Opens at http://127.0.0.1:8000
```

The dashboard hot-reloads (`--reload` flag). Changes to templates and static files are reflected immediately on browser refresh.

---

## Key Jinja2 context variables

Each partial template receives data from its router:

| Partial | Key variables |
|---------|--------------|
| `today_greeting.html` | `greeting`, `today_label`, `open_tasks`, `overdue`, `morning_runs` |
| `today_overnight.html` | `news`, `ideas`, `meetings` |
| `today_focus.html` | `project` (dict: title, domain, priority, next_step) |
| `work_stats.html` | `open_tasks`, `overdue`, `done_week`, `active_projects` |
| `work_tasks.html` | `tasks` (list: id, title, project, priority, status, due_date) |
| `work_projects.html` | `projects` (list: id, title, domain, priority, next_step, status) |
| `knowledge_library.html` | `cards` (list: id, title, domain, tags, summary, created_at) |
| `knowledge_literature.html` | `items` (list: id, title, authors, year, source, tags) |
| `planner_kanban.html` | `someday`, `incubating`, `active` (lists of projects) |
| `learning_courses.html` | `courses` (list: id, title, category, progress_pct, total_modules, completed_modules) |
| `learning_competencies.html` | `skills` (list: name, level, domain) |
| `teach_courses.html` | `courses` (list: id, title, code, semester, description, student_count) |
| `metis_stats.html` | `runs_today`, `tokens_today`, `total_runs`, `active_agents` |
| `metis_agents.html` | `agents` (list from agent-registry.json: slug, name, trust_tier, description) |

---

## Skeleton / loading states

All lazy-loaded partials show skeleton placeholders while loading:

```html
<div hx-get="/api/partial/work/tasks"
     hx-trigger="load"
     hx-swap="innerHTML">
  <div class="placeholder-glow">
    <span class="placeholder col-8 mb-2"></span>
    <span class="placeholder col-6 mb-2"></span>
    <span class="placeholder col-7"></span>
  </div>
</div>
```

These should look good in both the base state and the loaded state.

---

## Design inspiration references

- **Raycast** — minimal launcher aesthetic, high keyboard usability, monochrome with accent colors
- **Linear** — task management density and color system
- **Notion** — clean content hierarchy
- **macOS System Preferences / Settings** — sidebar + content pane pattern
- **GitHub's Primer design system** — status badges and diff views

The final result should feel like a **professional research cockpit**: dense but not cluttered, calm but not boring, capable of showing a lot of data without overwhelming.
