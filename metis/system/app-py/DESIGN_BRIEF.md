# Metis Research Cortex — Design Brief
_Last updated: 2026-05-06 · CSS v8.1 · Archive-Observatory design system_

---

## 1. What is Metis?

Metis is a **personal research second-brain dashboard** for a Senior Researcher / Epidemiologist / PhD candidate (senior researcher). It surfaces literature, news signals, tasks, meetings, learning progress, and AI agent activity in a single local-first web app.

**Stack:** Python FastAPI + HTMX + Jinja2 + SQLite. All content loads via HTMX partial swaps — no full page reloads. Runs at `http://127.0.0.1:8000`.

---

## 2. Design System — Archive / Observatory

### Philosophy
An academic archive meets a scientific observatory. Typography-first, high information density, zero decorative noise. Feels like a well-organised research library, works like a control room.

### Two themes
- **Archive** (light): warm parchment — aged paper, ink, forest green accent
- **Observatory** (dark): deep charcoal — night sky, warm parchment text, same accent

### CSS Tokens

```css
:root {
  /* Surfaces */
  --m-bg:            #f5f2ea;   /* warm parchment page */
  --m-surface:       #fbf8f0;   /* panel / card */
  --m-surface-2:     #eee9dd;   /* input backgrounds, secondary */
  --m-surface-3:     #e6e1d2;   /* hover states */

  /* Ink */
  --m-ink:           #1f2a24;   /* primary text */
  --m-text:          #2c3a33;   /* body */
  --m-muted:         #7a8178;   /* captions, labels */
  --m-muted-soft:    #9aa098;

  /* Rules */
  --m-rule:          rgba(31,42,36,0.12);
  --m-rule-soft:     rgba(31,42,36,0.06);
  --m-rule-strong:   rgba(31,42,36,0.28);

  /* Accent — Forest green */
  --m-accent:        #2d4a3a;
  --m-accent-hover:  #223b2e;
  --m-accent-soft:   #4a6a54;
  --m-accent-wash:   rgba(45,74,58,0.08);
  --m-accent-wash-2: rgba(45,74,58,0.14);
  --m-on-accent:     #f5f2ea;

  /* Ochre */
  --m-ochre:         #9a7b3c;
  --m-ochre-deep:    #7a5f25;
  --m-ochre-wash:    rgba(154,123,60,0.12);

  /* Semantic */
  --m-ok:    #5a7a5e;  --m-ok-wash:    rgba(90,122,94,0.14);
  --m-warn:  #9a7b3c;  --m-warn-wash:  rgba(154,123,60,0.14);
  --m-alert: #a84632;  --m-alert-wash: rgba(168,70,50,0.12);
  --m-info:  #3e6178;  --m-info-wash:  rgba(62,97,120,0.12);

  /* Shape */
  --m-radius: 3px;  --m-radius-sm: 2px;

  /* Shadows */
  --m-shadow:    0 1px 0 rgba(31,42,36,0.04), 0 4px 14px rgba(31,42,36,0.05);
  --m-shadow-lg: 0 2px 0 rgba(31,42,36,0.04), 0 12px 36px rgba(31,42,36,0.08);
}
/* Observatory dark overrides (data-theme != "archive"):
   --m-bg:#15130f; --m-surface:#1c1915; --m-ink:#f3ead6; --m-text:#d9cfba; etc. */
```

### Typography
```css
--m-display: 'EB Garamond', Georgia, serif;      /* headings, titles, italic captions */
--m-ui:      'Inter', system-ui, sans-serif;     /* UI chrome, buttons, labels */
--m-mono:    'JetBrains Mono', monospace;        /* metadata, tags, dates, codes */
```

**Scale:** page titles 28–32px display · section labels 10px mono uppercase · body 14px · chips/tags 9–10px mono

---

## 3. App Shell

**Layout:** Fixed sidebar (240px / 56px rail collapsed) + main with topbar + scrollable content area.

```
┌──────────────┬────────────────────────────────────────────────────────┐
│  [icon]      │  TOPBAR                                                │
│  Metis       │  Metis / Library    [search…]  [UPDATE]  ☀  [+Capture]│
│  Research    ├────────────────────────────────────────────────────────┤
│  Cortex      │                                                        │
│  ─────────   │              TAB CONTENT (HTMX partial swap)           │
│  SURFACES IX │                                                        │
│  01 Today    │                                                        │
│  02 Library  │                                                        │
│  03 Reflect  │                                                        │
│  04 Planner  │                                                        │
│  05 Work     │                                                        │
│  06 Meetings │                                                        │
│  07 Learning │                                                        │
│  08 Teach    │                                                        │
│  09 Metis    │                                                        │
│  ─────────   │                                                        │
│  [R] Researcher·RC │                                                        │
└──────────────┴────────────────────────────────────────────────────────┘
```

### Topbar (right side, left-to-right)
1. `Find across the archive…` — ghost search box (not yet wired)
2. **`UPDATE`** button — mono 9px uppercase, 1px border, hover accent. Calls `/api/scan/content`: runs news feed scan + Zotero incremental sync + project staleness check. Shows "UPDATING…" spinner, then toast with summary.
3. Theme toggle (☀ Archive / ☾ Observatory) — flips CSS vars, persists to localStorage
4. `+ Capture` — opens capture modal (slide from right)
5. Trust badge `Local-first`

### Sidebar nav items
Structure: `[icon 16px] [label] [meta count] [tooltip]`
Active: `border-left: 2px solid --m-accent; background: --m-accent-wash`

---

## 4. The 9 Surfaces

### 01 TODAY
Morning briefing, focus, and quick capture.
- Header: greeting + date
- Overnight AI summary
- Focus block (what matters today)
- **News scan rail** — signals from `news_briefs` grouped by domain/strength
- Token footer — session turn counter + usage bar

### 02 LIBRARY _(tab key: `knowledge`)_
The entire research literature in one place.

**Left sidebar — Collections (240px):**
List of Zotero collection names with counts. Click to filter the main browser. Styled like a filing cabinet index — each row has collection name + count, active row has accent left-border.

Your collections: Thesis (52) · Diagnostics (30) · Screening & Surveillance (21) · Methodology (17) · Elimination (11) · Statistics & Modelling (9) · Sero-surveillance (9) · WHO (8) · Epidemiology (8) · Passive (8) · and ~13 more.

**Main area:**
- Stats meta: `222 CARDS · N COLLECTIONS · N ADDED THIS WEEK`
- Index cards grid (from `library_cards` — domain knowledge notes)
- **Sync status bar:** `197 ZOTERO PAPERS · SYNCED 2026-05-06 00:59 · v1393` + `SYNC NOW` button
- **Library browser panel:**
  - Row 1: Search bar + "Search in: All / Title / Authors / Abstract" + Sort select + "Clear N filters" button
  - Row 2: Author field · Year from · Year to · Journal (autocomplete datalist)
  - Row 3: Type pills — All · Article · Book · Chapter · Report · Preprint · Web
  - Row 4: Collection chips — All + all Zotero collections
  - **Table:** Type badge · Title (DOI-linked) / Authors (italic) / Abstract (expandable) · Year · Journal · Collection tags · [ABS] [DOI ↗]
- Memory search (semantic across episodic memory)

**Data:** `literature_metadata` (222 rows: 197 Zotero + 25 manual) · `library_cards` (31 rows) · `zotero_sync_state`

### 03 REFLECTION
Ideas, notes, open questions, brainstorm launcher. Capture modal feeds here.

### 04 PLANNER
Work planning across time horizons.
- Kanban: Someday → Incubating → Active (drag-and-drop columns)
- PhD focus board
- Timeline view
- **Each card needs:** inline text editing, done checkmark, user-set priority (H/M/L)

### 05 WORK
Task list (priority left-border coloring) + active project cards + launcher buttons.
Project card actions: `Code` (VS Code) · `Data` (Explorer) · `📊 Dashboard` (launches Shiny on 4321) · `Folder` · `Docs`.

### 06 MEETINGS
Structured meeting log — transcription, decisions, action items.

### 07 LEARNING
Spaced repetition queue + course progress bars + competency radar.

### 08 TEACH
Course cards with AI actions: Chat · Co-work · Slides · Assessment · Q-bank · Gap analysis.

### 09 METIS
Agent run history table · token stats · agent registry · self-improvement proposals.

---

## 5. Component Reference

### Panel
```html
<div class="panel">…</div>
```
Surface background, 1px `--m-rule` border, 3px radius, subtle shadow.

### Section Label
```html
<div class="sec-label">
  <span>Title</span>
  <span class="tail">META · COUNTS</span>
</div>
```
10px mono, uppercase, muted. `.tail` floats right.

### Library filter chips
```css
.lib-chip       { 9px mono; padding:3px 10px; 1px border; radius:2px; bg:surface-2 }
.lib-chip.active{ bg:--m-accent; color:#fff; border:accent }
.lib-type-btn.active { bg:--m-ink; color:surface }
```

### Toast
Bottom-right, 3s auto-dismiss. Accent background, parchment text.

### Inputs
```css
.lib-input { font:12px --m-ui; padding:7px 10px; bg:surface-2; border:1px rule; radius:3px }
.lib-input:focus { border-color:--m-accent }
.lib-select { font:10px mono; same bg/border/radius }
```

---

## 6. HTMX Patterns (do not break)

Every section loads independently:
```html
<div hx-get="/api/partial/knowledge/library-browser"
     hx-trigger="load"
     hx-swap="outerHTML">…skeleton…</div>
```

Live filter (debounced):
```html
<input hx-get="/api/partial/knowledge/library-table"
       hx-trigger="keyup changed delay:350ms"
       hx-target="#lib-table-area"
       hx-include="#lib-hidden-fields">
```

All filter state lives in `#lib-hidden-fields` (hidden inputs). JS function `_refreshLibTable()` reads all values and fires one HTMX request.

---

## 7. File Locations

```
system/app-py/
├── static/
│   ├── styles.css          (1289 lines — full design system)
│   ├── app.js              (1200+ lines — all interactivity)
│   └── metis-icon.png      (dark blue AI brain, sidebar favicon)
├── templates/
│   ├── base.html           (shell: sidebar, topbar, theme toggle)
│   ├── knowledge.html      (Library surface)
│   └── partials/           (80 partials)
└── routers/
    ├── knowledge.py        (Library + filter + sync endpoints)
    ├── today.py            (Today + /api/scan/content Update endpoint)
    └── work.py             (Work + project launcher)
```

---

## 8. Open Design Work

| Item | Notes |
|---|---|
| Planner cards inline editing | Click-to-edit, checkmark done, priority selector |
| Planner drag-and-drop | Columns: Someday / Incubating / Active |
| Library PDF column | `file_path` column needed, PDF icon + open button |
| News as separate Today section | Signals stay on Today scan rail, not in Library |
| Responsive navbar | Labels hide below 900px (already CSS-supported) |
