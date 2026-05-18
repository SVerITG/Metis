# Claude Design Session Brief — 2026-04-21

---

## 1. What Was Designed (Summary of v1 + v2-remix)

### v1 — Literary Editorial System
Located at: `claude-design-export/v1/`

v1 is a full React JSX UI kit with 9 surface components (`today.jsx`, `knowledge.jsx`, `work.jsx`, `thinking.jsx`, `planner.jsx`, `meetings.jsx`, `learning.jsx`, `teach.jsx`, `metis.jsx`) plus `app.html` (the single-file wrapper) and `app.css`. The v1 design takes a dramatically different aesthetic direction than the current live app — it uses a warm literary/archival palette with Newsreader/Fraunces display typefaces, hand-written style editorial prose, a subtle parchment background, and no Bootstrap. Key distinguishing elements:

- Today surface rendered as a "morning briefing paragraph" — prose, not a dashboard
- Knowledge surface styled as a slipcase/index-card archive system
- Work surface as a 4-column kanban (Inbox / This week / In progress / Closed)
- Planner surface with weekly day-grid and horizon cards (Today / Week / Quarter)
- Metis surface as settings panel (model picker, memory, keys, billing)
- Custom SVG mark (`metis-mark.svg`, compass-style) with animated reveal
- Logos: `v1/assets/metis-mark.svg`, `v1/assets/metis-mark-ochre.svg`, `v1/assets/metis-wordmark.svg`
- Strong JetBrains Mono use for all metadata, timestamps, section kickers (UPPERCASE + letter-spacing)
- Left-border accent system for active/selected states throughout

### v2-remix — Dual-Layer Design System
Located at: `claude-design-export/v2-remix/`

v2-remix is a production-ready design system with full CSS token foundations, HTML component previews, a React UI kit for the Today surface, and a 3-direction exploration. It formalises the "dual palette" approach:

- **(A) macOS system layer** — `#f5f5f7` background, translucent white surfaces `rgba(255,255,255,0.85)`, `#0071e3` blue, `#1d1d1f` text — used for all chrome
- **(B) Editorial warm layer** — `#faf9f6` cream, `#f6f3ec` parchment, `#174c4f` teal, `#b36a1d` amber — used for morning brief, kanban columns, gallery cards, learning hero

v2-remix designed and exported:
- `colors_and_type.css` — complete dual-layer CSS token sheet (37 color variables, 4 font families, 8 type scale variables, 5 shadow variables, 2 motion variables, 6 radius variables)
- `_source/styles.css` — full component CSS transplanted from the live app (2753 lines), representing the v2-remix reference implementation
- `_source/templates/` — 6 Jinja2 templates: `base.html`, `today.html`, `knowledge.html`, `thinking.html`, `work.html`, `metis_tab.html`
- `_source/partials/` — 11 partials: `today_greeting.html`, `today_overnight.html`, `today_scan.html`, `work_tasks.html`, `capture_modal.html`, `planner_kanban.html`, `metis_agents.html`, `metis_runs.html`, `meetings_list.html`, `learning_courses.html`, `thinking_ideas.html`
- `preview/` — 17 HTML preview cards: buttons, badges, card, forms, kanban, morning-brief, navbar, valuebox, colors-models/system/warm, type-body/display/mono, shape-radii-shadows, brand-iconography, brand-logo
- `ui_kits/metis-today/index.html` — interactive React UI kit with 7 components (TopNav, MorningBrief, ValueBoxStrip, RecentRuns, InboxCard, CaptureBar, ProjectKanban) fully wired up with mock data, interactive kanban card promotion, capture toast notification
- `directions/today-3-directions.html` — 3 named design directions for the Today page
- Logo assets: `v2-remix/assets/metis-mark.svg` (compass-style), `v2-remix/assets/metis-wordmark.svg`, `v2-remix/assets/metis-compass.svg`

### What the 3 Directions Explore (today-3-directions.html)

All 3 directions share the same structural layout (hero section + 2-column grid + footer) and the same full-page React wrapper (`DesignCanvas.jsx`). They differ only in palette, typography, and surface treatment:

- **Direction 1 — MANUSCRIPT**: Cream paper `#f3efe6`, sienna accent `#b56838`, Fraunces display serif. The warmest, most "reading room" feel. Closest to v1.
- **Direction 2 — ARCHIVE**: Bone-white `#f5f2ea`, deep forest green accent `#2d4a3a`, Newsreader serif. The most archival/scholarly. Least personal.
- **Direction 3 — OBSERVATORY**: Warm dark theme `#15130f` background, amber accent `#d99a4c`, Fraunces display. A nocturnal study feel — experimental, stands apart from the current light-mode app.

---

## 2. What Is NOT Finished / Incomplete in the Designs

### Missing from v2-remix
1. **Only Today surface has a React UI kit** — v2-remix `ui_kits/metis-today/index.html` covers Today. No equivalent for Knowledge, Work, Planner, Meetings, Learning, Thinking, Teach, or Metis tabs.
2. **Only 6 of 9 tabs have `_source/templates/`** — `base.html`, `today.html`, `knowledge.html`, `thinking.html`, `work.html`, `metis_tab.html`. Missing: `meetings.html`, `learning.html`, `planner.html`, `teach.html`.
3. **Only 11 of 37 partials have `_source/partials/`** — Missing from v2-remix: `capture_modal.html` exists but the live capture modal is richer. Missing entirely: `today_focus.html`, `today_token_footer.html`, `today_news.html`, `knowledge_graph.html`, `knowledge_search.html`, `knowledge_library.html`, `knowledge_literature.html`, `knowledge_domains.html`, `knowledge_stats.html`, `learning_due.html`, `learning_competencies.html`, `learning_completed.html`, `meetings_stats.html`, `metis_stats.html`, `metis_system_info.html`, `metis_consent.html`, `metis_traces.html`, `planner_focus.html`, `planner_timeline.html`, `teach_courses.html`, `teach_lit_alerts.html`, `teach_news_alerts.html`, `thinking_notes.html`, `thinking_questions.html`, `thinking_brainstorm_sessions.html`, `work_projects.html`, `work_stats.html`, `trust_badge.html`.
4. **The 3 directions file is a design canvas wrapper** — `today-3-directions.html` is a Figma-style artboard viewer (drag-to-reorder, fullscreen focus) rather than production-ready HTML. The 3 actual direction previews are rendered inside React artboards at runtime. None of the 3 direction themes have been extracted into actual CSS files or templates.
5. **No dark mode CSS** — v2-remix README explicitly notes "Dark mode is not in the source and isn't here." Direction 3 (Observatory) exists as a theme but is not wired to prefers-color-scheme.
6. **No Knowledge graph redesign** — The D3.js force-directed graph exists in the live app (`knowledge_graph.html` partial) but there is no design-export equivalent with proper styling or the knowledge graph component in any preview file.
7. **No Teach tab design** — v1 has `teach.jsx` but v2-remix has no template or partial for Teach.
8. **No Metis logo SVG applied in the live app** — Three logo SVG files exist in both v1 and v2-remix assets folders but none are linked or referenced anywhere in the live app's `base.html` or `styles.css`.

---

## 3. Gap Analysis: Design vs Current Implementation

### 3a. Token Gaps — Design Variables NOT in the Live App's `styles.css`

The live app's `styles.css` (2931 lines) has an `_source/styles.css`-identical `:root` block but is **missing the full dual-layer warm token set** that `colors_and_type.css` defines:

**Missing CSS custom properties in `/mnt/c/Users/sverschaeve/.../app-py/static/styles.css`:**
```css
/* These 20+ variables exist in v2-remix colors_and_type.css but NOT in the live styles.css */
--metis-surface-2: rgba(255, 255, 255, 0.72);   /* navbar surface */
--metis-blue-hover: #0077ed;
--metis-radius-xs: 6px;
--metis-radius-pill: 999px;
--metis-shadow-focus: 0 0 0 3px rgba(0, 113, 227, 0.15);
--metis-shadow-btn: 0 1px 3px rgba(0, 113, 227, 0.3);
--metis-transition-fast: 150ms ease;
--warm-bg-cream: #faf9f6;
--warm-bg-parchment: #f6f3ec;
--warm-bg-paper: #fefcf8;
--warm-bg-stone: #f5f3ee;
--warm-ink-deep: #1f2a2e;
--warm-ink-slate: #4a5a5e;
--warm-ink-muted: #6d7c74;
--warm-teal: #174c4f;
--warm-teal-2: #2d6073;
--warm-amber: #b36a1d;
--warm-amber-deep: #7a3d00;
--warm-moss: #2e6b4f;
--warm-brick: #c0392b;
--warm-brick-deep: #8b1a11;
--warm-teal-08: rgba(23, 76, 79, 0.08);
--warm-teal-10: rgba(23, 76, 79, 0.10);
--warm-teal-12: rgba(23, 76, 79, 0.12);
--warm-teal-15: rgba(23, 76, 79, 0.15);
--warm-shadow-soft: 0 8px 20px rgba(31, 42, 46, 0.05);
--warm-shadow-hover: 0 12px 28px rgba(23, 76, 79, 0.12);
--font-system: -apple-system, ...;  /* named vars, not raw in body */
--font-display: -apple-system, ...;
--font-serif: "IBM Plex Serif", Georgia, serif;
--font-mono: "JetBrains Mono", "Fira Code", ...;
--type-body-size: 0.9375rem;
--type-body-leading: 1.6;
--type-body-tracking: -0.01em;
--type-h1-size: 1.75rem; --type-h1-weight: 700; --type-h1-tracking: -0.03em;
--type-h2-size: 1.3rem; --type-h2-weight: 600; --type-h2-tracking: -0.02em;
--type-h3-size: 1.15rem; --type-h4-size: 1.05rem;
--type-label-size: 0.78rem; --type-label-weight: 700; --type-label-tracking: 0.05em;
--type-small-size: 0.875rem; --type-meta-size: 0.78rem;
--type-micro-size: 0.72rem; --type-code-size: 0.82rem;
--metis-haiku-bg/fg; --metis-sonnet-bg/fg; --metis-opus-bg/fg;
```

### 3b. Component Gaps — Design Components NOT in the Live App

| Component | Design Location | Live App Status |
|-----------|----------------|-----------------|
| **Value box strip** (4-up KPI: Runs today / Tokens / Open tasks / Projects) | `preview/components-valuebox.html`, `ui_kits/metis-today/index.html` → `ValueBoxStrip` | Partially present as `.kpi-strip` + `.bslib-value-box` but uses different markup; today tab shows overnight summary counts but NOT a 4-up value box strip |
| **Agent inbox card** (dismiss-able items from agents with HIGH/MEDIUM/LOW signal) | `ui_kits/metis-today/index.html` → `InboxCard` | Not implemented — no inbox card partial exists |
| **Capture bar** (inline mode-toggle + textarea on Today page) | `ui_kits/metis-today/index.html` → `CaptureBar` | Only exists as the navbar pill button + modal overlay; no inline capture bar on the Today page |
| **Today 2-column layout** (`1.25fr 1fr` grid) | `ui_kits/metis-today/index.html` → `mk-grid` | Today uses Bootstrap rows, not a custom grid; no 2-column layout with the specified ratio |
| **Morning brief serif greeting** (.morning-greeting with IBM Plex Serif applied) | `preview/components-morning-brief.html`, `_source/styles.css` line 731–737 | `.morning-greeting` class exists in styles.css with IBM Plex Serif declared, BUT the live `today_greeting.html` partial wraps greeting in `<h2 class="mb-0 fw-bold">`, NOT `.morning-greeting`. The serif is never activated. |
| **"Today's paper" amber block** (`.todays-paper` with amber left-border) | `preview/components-morning-brief.html`, `_source/styles.css` | CSS class exists, but never used in `today_greeting.html` partial |
| **Overnight item as stat row** (`.overnight-item` with big count number + label) | `_source/styles.css` → `.overnight-count`, `.overnight-item`, `.overnight-item-label`, `.overnight-item-tab` | The live `today_overnight.html` uses `.overnight-count` (outer div) but references `.overnight-count-value` and `.overnight-count-label` (inner divs) which are NOT defined in any CSS — the count numbers get zero styling |
| **`.label-caps` utility** (uppercase label for KPI headers) | `colors_and_type.css` | Not in live `styles.css`; live app uses `text-transform:uppercase` inline or via Bootstrap `.text-uppercase` |
| **`.morning-chip-muted` / `.morning-chip-danger`** | Defined in live styles.css correctly | Present and correct |
| **Model badge colors on agent runs** (`.mk-agent-badge.h/.s/.o`) | `ui_kits/metis-today/index.html` | Live app uses `.model-badge-haiku/sonnet/opus` which are functionally equivalent but not using CSS vars |
| **Navbar pill capture button with box-shadow** | `preview/components-navbar.html` → `.capt` has `box-shadow:0 2px 8px rgba(0,113,227,.35)` | Live `.btn-capture-nav` missing the `box-shadow` |
| **Trust badge with plain white background** | `preview/components-navbar.html` → `.trust` has `background:#fff` | Live `.trust-badge` uses `rgba(48,164,108,0.08)` green tint instead |
| **Kanban column — warm stone background** | `preview/components-kanban.html`, `_source/styles.css` → `#f5f3ee` | The live planner variant of `.kanban-col` uses `var(--metis-gray-light)` = `#f2f2f7` (cool gray), NOT the warm stone `#f5f3ee` from the design. |
| **Kanban column header — warm teal color** | `.hd` in kanban preview → `color:#174c4f` | Live `.kanban-col-header` uses `var(--metis-gray)` = `#6e6e73` — no teal |
| **Gallery card title with optional serif** | `.gallery-card-title--serif` in `colors_and_type.css` | Not applied in live `knowledge_library.html` partial |
| **Section label rule line** (`.mf-seclabel::after` — line extending to right) | `directions/today-3-directions.html` | Not implemented anywhere in live app |
| **Compass logo SVG** | `v2-remix/assets/metis-compass.svg`, `v2-remix/assets/metis-mark.svg` | No SVG logo used anywhere in `base.html` — just `<i class="bi bi-cpu-fill">` text |

### 3c. Structural Inconsistencies — Current App vs Design System

1. **Morning brief using wrong gradient direction**: Live `.morning-brief` overridden at line 2832–2835 of styles.css to `border-left-color: var(--metis-blue)` and `background: linear-gradient(135deg, rgba(0,113,227,0.04) 0%, var(--metis-gray-light) 100%)`. Design system specifies `border-left: 4px solid #174c4f` (warm teal) and `background: linear-gradient(135deg, #f6f3ec 0%, #faf9f6 100%)` (cream/parchment). The live override destroys the warm editorial character of the morning brief.

2. **Greeting not using serif font**: The design specifies `.morning-greeting` with `font-family: "IBM Plex Serif"`. Live `today_greeting.html` uses `<h2 class="mb-0 fw-bold">` — no `.morning-greeting` class applied, so the IBM Plex Serif never renders in the greeting.

3. **Overnight count values unstyled**: Live `today_overnight.html` references `.overnight-count-value` and `.overnight-count-label` as inner div classes, but no CSS defines these. The big count numbers (`1.8rem font-size`) have zero styling. Design specifies `.overnight-count` = 1.8rem blue font-size, which IS in styles.css (line 2462) but applied to the wrong element.

4. **Warm token overrides use hardcoded hex instead of CSS vars**: The live styles.css is full of hardcoded colors like `#174c4f`, `#faf9f6`, `#b36a1d`, `#6d7c74` instead of the declared warm token vars (`var(--warm-teal)`, `var(--warm-bg-cream)`, `var(--warm-amber)`, `var(--warm-ink-muted)`). Since the warm vars are not in the live `:root`, they can't be used — but the consequence is zero maintainability.

5. **`.kanban-col` redefined twice**: Lines 795 and 2332 both define `.kanban-col` with different values (stone `#f5f3ee` vs system gray `var(--metis-gray-light)`). The late override (line 2332) wins and cools the kanban columns, losing the warm editorial character.

6. **Today page uses Bootstrap rows instead of the design grid**: The design specifies a `1.25fr 1fr` two-column grid (`mk-grid`). Live `today.html` uses Bootstrap's `row g-3` with `col-12 col-md-6` splits — a 50/50 split, not the intended 1.25/1 ratio.

7. **`.morning-chip` base class has wrong background**: Line 2774 sets `.morning-chip { background: var(--metis-gray-light); color: var(--metis-text); }` — design specifies no base background (chips should only render via modifier classes `.morning-chip-ok/warn/alert`). The base class makes unchipped text appear gray-boxed.

8. **No `overnight-count` stat rendering in the live partial**: The live `today_overnight.html` counts are wrapped in `<div class="overnight-count">` (outer container) with inner `overnight-count-value` / `overnight-count-label` divs. The CSS at line 2462 styles `.overnight-count` as if it is the value div (`font-size: 1.8rem; font-weight: 700; color: var(--metis-blue)`). This produces a large-text outer container with small inner text — the exact opposite of the design intent.

---

## 4. Priority Surfaces to Complete Tomorrow

### Today Page — Recommended Direction

**Recommendation: Synthesise the v2-remix design with the ARCHIVE direction theme.**

The v2-remix `_source/styles.css` is the production-ready implementation spec and should be the primary reference. Of the 3 directions:

- Direction 1 (MANUSCRIPT) is too warm/sienna — the current app already has IBM Plex Serif and teal; pulling toward sienna brown would require a palette shift.
- Direction 3 (OBSERVATORY) is a dark mode that the README explicitly marks as out of scope.
- **Direction 2 (ARCHIVE)** best matches the existing dual-palette spirit: bone-white backgrounds, forest green as accent (maps directly to warm-teal `#174c4f`), Newsreader/display serif for greeting, JetBrains Mono for metadata. This is the closest to what the v2-remix design system already describes — the fonts and colors align with tokens already declared.

**Specific changes to make Tomorrow for the Today page:**

1. Fix `today_greeting.html` — add `.morning-brief` wrapper + `.morning-greeting` + `.morning-date` classes (serif font will then apply)
2. Add "Today's paper" block below chips using `.todays-paper` + `.todays-paper-label`
3. Replace the Bootstrap 50/50 grid in `today.html` with a custom CSS grid using `grid-template-columns: 1.25fr 1fr`
4. Add a 4-up value box strip (`.mk-vbs` / `.mk-vb`) above the 2-column section showing: Runs today / Tokens today / Open tasks / Active projects
5. Fix `.overnight-count` CSS bug — the outer div needs `display:flex; gap:1.5rem; flex-wrap:wrap` and the inner `.overnight-count-value` needs `font-size:1.8rem; font-weight:700; color:var(--metis-blue)`

### Knowledge Page
The v2-remix `_source/templates/knowledge.html` exists. Priority: apply the gallery card warm tokens (restore `#fff` card background with `rgba(23,76,79,.1)` border instead of macOS surface override), apply `.gallery-card-title--serif` to library card titles, and ensure the knowledge graph container has its warm paper background (`#fefcf8`).

### Work Page
The v2-remix `_source/templates/work.html` and `_source/partials/work_tasks.html` exist. Priority: the task list needs priority left-borders rendered correctly (the CSS `:has()` selector is too fragile — use explicit class-based approach), and the projects section needs the `.project-board-card` warm cream background.

### Planner/Kanban
Highest visual regression. Priority:
1. Restore kanban column background to warm stone `#f5f3ee` (currently overridden to cool `#f2f2f7`)
2. Restore kanban column header color to `#174c4f` warm teal (currently `var(--metis-gray)`)
3. Restore kanban count chip to `rgba(23,76,79,.15)` teal (currently `rgba(0,0,0,0.08)` gray)
4. The v2-remix `_source/partials/planner_kanban.html` exists and is the reference

### Metis/Agents Tab
The v2-remix `_source/templates/metis_tab.html` and `_source/partials/metis_agents.html` + `metis_runs.html` exist. The agent run rows in `ui_kits/metis-today/index.html` show the ideal layout: `56px time | 120px agent-badge | 1fr text | 48px tokens`. The live implementation uses Bootstrap table rows instead. Priority: convert metis_runs to use the `.mk-run` row pattern with monospaced time/tokens columns.

---

## 5. Component Library Gaps

The following components appear in the design exports but have no live implementation in the app:

| Component | Design Reference | CSS Class(es) |
|-----------|-----------------|---------------|
| **4-up Value Box Strip** | `preview/components-valuebox.html`, `ui_kits/metis-today` → `ValueBoxStrip` | `.mk-vbs`, `.mk-vb`, `.mk-vb-lab`, `.mk-vb-val`, `.mk-vb-sub` |
| **Agent Inbox Card** | `ui_kits/metis-today` → `InboxCard` | `.mk-inbox-row`, `.mk-inbox-from`, `.mk-inbox-text`, `.sig-high/med/low` |
| **Inline Capture Bar** (on Today page) | `ui_kits/metis-today` → `CaptureBar`, `preview/components-forms.html` → `.mk-capture-bar` | `.mk-capture-bar`, `.mk-capture-modes`, `.mk-mode`, `.mk-capture-input`, `.mk-capture-foot` |
| **Section label with rule-line** | `directions/today-3-directions.html` → `.mf-seclabel::after` | `.mf-seclabel` with `::after { flex:1; height:1px; background:var(--m-rule); }` |
| **Horizon card** (Today / Week / Quarter) | `v1/surfaces/planner.jsx` → `HorizonCard` | none — lives only in v1 JSX |
| **Day-at-a-glance row** (time / label / title / duration) | `v1/surfaces/today.jsx` → `DayRow` | none — lives only in v1 JSX |
| **Thread card** (active knowledge thread) | `v1/surfaces/today.jsx` → `ThreadCard` | none — lives only in v1 JSX |
| **Margin note** (Metis agent annotation) | `v1/surfaces/today.jsx` → `MarginNote` | none — lives only in v1 JSX |
| **Weekly day-grid** (7-column planner) | `v1/surfaces/planner.jsx` → 7-column grid | none — not in live planner tab |
| **Knowledge slipcase list** (left-sidebar with `2px accent border-left` on active item) | `v1/surfaces/knowledge.jsx` | none |
| **Source row** (table-style source list in Knowledge) | `v1/surfaces/knowledge.jsx` → `SOURCES` grid | Partially replicated by `knowledge_literature.html` table, but with different structure |
| **Model selector cards** (Haiku / Sonnet / Opus pick) | `v1/surfaces/metis.jsx` → model picker | No model picker in live Metis tab |
| **Toggle component** (macOS-style pill toggle) | `v1/surfaces/metis.jsx` → `Toggle` | Not in live app at all |
| **Compass mark SVG + animated reveal** | `directions/today-3-directions.html` CSS keyframes `m-draw`/`m-fade` | No animated logo in live app |
| **`label-caps` utility class** | `colors_and_type.css` | Not in live `styles.css` |
| **`.serif` utility class** | `colors_and_type.css` | Not in live `styles.css` |
| **`.mono` utility class** | `colors_and_type.css` | Not in live `styles.css` (`.brainstorm-context-output` uses JetBrains Mono inline) |

---

## 6. Design Tokens to Apply Immediately

The following CSS changes should be made to `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex/metis/system/app-py/static/styles.css` at the start of the session to unify the token system:

### Step 1: Add missing variables to `:root` (insert after existing `:root` block, ~line 28)

```css
/* v2-remix additions — warm editorial layer + extended system tokens */
--metis-surface-2:    rgba(255, 255, 255, 0.72);
--metis-blue-hover:   #0077ed;
--metis-radius-xs:    6px;
--metis-radius-pill:  999px;
--metis-shadow-focus: 0 0 0 3px rgba(0, 113, 227, 0.15);
--metis-shadow-btn:   0 1px 3px rgba(0, 113, 227, 0.3);
--metis-transition-fast: 150ms ease;

--warm-bg-cream:      #faf9f6;
--warm-bg-parchment:  #f6f3ec;
--warm-bg-paper:      #fefcf8;
--warm-bg-stone:      #f5f3ee;
--warm-ink-deep:      #1f2a2e;
--warm-ink-slate:     #4a5a5e;
--warm-ink-muted:     #6d7c74;
--warm-teal:          #174c4f;
--warm-teal-2:        #2d6073;
--warm-amber:         #b36a1d;
--warm-amber-deep:    #7a3d00;
--warm-moss:          #2e6b4f;
--warm-brick:         #c0392b;
--warm-brick-deep:    #8b1a11;
--warm-teal-08:       rgba(23, 76, 79, 0.08);
--warm-teal-10:       rgba(23, 76, 79, 0.10);
--warm-teal-12:       rgba(23, 76, 79, 0.12);
--warm-teal-15:       rgba(23, 76, 79, 0.15);
--warm-shadow-soft:   0 8px 20px rgba(31, 42, 46, 0.05);
--warm-shadow-hover:  0 12px 28px rgba(23, 76, 79, 0.12);

--font-system:  -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", system-ui, sans-serif;
--font-display: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", system-ui, sans-serif;
--font-serif:   "IBM Plex Serif", Georgia, serif;
--font-mono:    "JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;

--type-label-size:    0.78rem;
--type-label-weight:  700;
--type-label-tracking: 0.05em;
--type-micro-size:    0.72rem;
--type-meta-size:     0.78rem;
--type-code-size:     0.82rem;

--metis-haiku-bg:  #d4f7e7; --metis-haiku-fg:  #1a6641;
--metis-sonnet-bg: #dbeafe; --metis-sonnet-fg: #1e40af;
--metis-opus-bg:   #ede9fe; --metis-opus-fg:   #5b21b6;
```

### Step 2: Add missing utility classes (add near top of stylesheet)

```css
.label-caps {
  text-transform: uppercase;
  letter-spacing: var(--type-label-tracking);
  font-weight: var(--type-label-weight);
  font-size: var(--type-label-size);
}
.serif { font-family: var(--font-serif); }
.mono  { font-family: var(--font-mono); font-size: var(--type-code-size); }
```

### Step 3: Fix the morning brief warm character (override the "Phase 9" macOS override at ~line 2832)

```css
/* Replace lines 2832–2836 with: */
.morning-brief {
  border-left: 4px solid var(--warm-teal) !important;
  background: linear-gradient(135deg, var(--warm-bg-parchment) 0%, var(--warm-bg-cream) 100%) !important;
}
.morning-greeting {
  font-family: var(--font-serif);
  color: var(--warm-teal) !important;
}
```

### Step 4: Fix kanban warm tokens (replace lines 2332-2355 planner kanban variant)

```css
/* Planner kanban columns — restore warm stone, not cool gray */
.kanban-wrapper .kanban-col {
  background: var(--warm-bg-stone);  /* #f5f3ee, not #f2f2f7 */
}
.kanban-wrapper .kanban-col-header {
  color: var(--warm-teal);  /* #174c4f, not var(--metis-gray) */
}
.kanban-wrapper .kanban-count {
  background: var(--warm-teal-15);
  color: var(--warm-teal);
}
```

### Step 5: Fix overnight count CSS (replace `.overnight-count` block at ~line 2462)

```css
.overnight-items {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}
.overnight-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.overnight-count-value {
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--metis-blue);
  line-height: 1;
}
.overnight-count-label {
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--metis-text);
}
```

### Step 6: Add value box strip component (new section)

```css
/* 4-up value box strip — Today page */
.value-box-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.value-box-item {
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid var(--metis-border);
  border-radius: var(--metis-radius);
  padding: 0.95rem 1rem;
  box-shadow: var(--metis-shadow);
}
.value-box-label {
  font-size: var(--type-label-size, 0.78rem);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--metis-text-muted);
  font-weight: 700;
}
.value-box-value {
  font-size: 1.8rem;
  font-weight: 600;
  color: var(--metis-text);
  line-height: 1.15;
  margin-top: 2px;
}
.value-box-sub {
  font-size: var(--type-micro-size, 0.72rem);
  color: var(--metis-text-muted);
  margin-top: 2px;
}
```

### Step 7: Fix capture button box-shadow (update `.btn-capture-nav` at ~line 2663)

```css
.btn-capture-nav {
  /* add: */
  box-shadow: 0 2px 8px rgba(0, 113, 227, 0.35) !important;
}
```

### Step 8: Fix trust badge to white background (update `.trust-badge` at ~line 2643)

```css
.trust-badge {
  background: #fff !important;  /* was rgba(48,164,108,0.08) */
  color: var(--metis-text-muted) !important;
  border-color: var(--metis-border) !important;
}
.trust-badge .bi-shield-check { color: var(--metis-green); }
```

---

## 7. Logo Assets Found

### v2-remix Assets (`claude-design-export/v2-remix/assets/`)
- `metis-wordmark.svg` — Full "Metis" wordmark SVG (200px wide in preview)
- `metis-mark.svg` — Standalone compass mark SVG (56px in preview)
- `metis-compass.svg` — Variant compass mark

### v1 Assets (`claude-design-export/v1/assets/`)
- `metis-mark.svg` — Same compass mark style
- `metis-mark-ochre.svg` — Ochre/amber colored variant of the mark
- `metis-wordmark.svg` — Full wordmark

### Animated Compass Mark CSS
The `directions/today-3-directions.html` file contains a fully-specified SVG animation system for the compass mark:
- `@keyframes m-draw` — stroke-dasharray path draw animation (outer ring 1.1s, inner ring 0.9s)
- `@keyframes m-fade` — scale-up fade for the center triangle/dot
- Hover state: outer ring rotates 12 degrees with 0.9s ease spring
- Classes: `.metis-mark.reveal` triggers the animation on load

### Where the Logo Should Go
1. **Navbar brand** (`base.html` line 38-40): Replace `<i class="bi bi-cpu-fill me-1 text-primary"></i>Metis` with the `metis-mark.svg` inline SVG or `<img src="/static/metis-mark.svg">` + "Metis" wordmark text.
2. **Static files**: Copy `v2-remix/assets/metis-mark.svg`, `metis-wordmark.svg`, `metis-compass.svg` to `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex/metis/system/app-py/static/`.
3. The animated reveal variant would work well on a loading screen or first-visit. For daily use, the static mark is more appropriate.

---

## 8. Exact Prompts for Tomorrow's Claude Design Session

### Prompt 1 — Token Foundation Fix
```
You are building the Metis Research Cortex dashboard design system.
Context: The live app is at metis/system/app-py/ (FastAPI + HTMX).
The design system is at metis/system/design-docs/claude-design-export/v2-remix/.

Task: Apply the full v2-remix token system to the live styles.css.

1. Read the v2-remix colors_and_type.css (full dual-layer token sheet).
2. Read the current live styles.css :root block (lines 1-28).
3. Add ALL missing CSS custom properties from colors_and_type.css to the live styles.css :root block — specifically the warm-* layer (20+ warm color vars), the font-* named vars (font-system, font-display, font-serif, font-mono), all type-* scale vars, the extended radius/shadow/transition vars, and the model badge bg/fg pairs.
4. Then replace all hardcoded hex values in the live styles.css that have a corresponding CSS variable (e.g. #174c4f → var(--warm-teal), #f5f3ee → var(--warm-bg-stone), #6d7c74 → var(--warm-ink-muted), #b36a1d → var(--warm-amber)) — only where they appear inside warm-layer component rules (morning-brief, kanban-col, gallery-card, course-card, etc.).
5. Add the missing utility classes: .label-caps, .serif, .mono.

Do NOT change any visual output — only consolidate hardcoded values to use the CSS vars. The result should look identical.
```

### Prompt 2 — Today Page Redesign
```
You are redesigning the Today tab of the Metis Research Cortex dashboard.

Reference files:
- Design spec: metis/system/design-docs/claude-design-export/v2-remix/ui_kits/metis-today/index.html (the React UI kit — study MorningBrief, ValueBoxStrip, RecentRuns, CaptureBar components)
- Design spec: metis/system/design-docs/claude-design-export/v2-remix/preview/components-morning-brief.html
- Current template: metis/system/app-py/templates/today.html
- Current partials: today_greeting.html, today_overnight.html, today_news.html, today_focus.html, today_scan.html, today_token_footer.html

Changes to make:
1. today.html: Replace the Bootstrap row/col layout with a CSS custom grid (.today-grid { display:grid; grid-template-columns: 1.25fr 1fr; gap:14px; }) for the main content area. Add a 4-up value-box-strip above it.
2. today_greeting.html: Wrap the greeting content in <div class="morning-brief"> and apply <div class="morning-greeting"> to the greeting text (so IBM Plex Serif renders). Add <div class="morning-date"> for the date. Add a "Today's paper" block below chips using .todays-paper + .todays-paper-label if a highlighted_paper context variable is available.
3. today_overnight.html: Fix the overnight count HTML structure — the .overnight-count-value and .overnight-count-label divs need to match the CSS that styles them (see CLAUDE_DESIGN_BRIEF_TOMORROW.md Section 6 Step 5 for the corrected CSS).
4. Add a new today_valuebox.html partial that renders a 4-up .value-box-strip fetching run_count, token_count, open_task_count, active_project_count from the backend.

Keep all HTMX hx-get / hx-trigger / hx-swap attributes intact.
```

### Prompt 3 — Kanban & Planner Warm Tokens
```
You are fixing the Planner/Kanban tab of the Metis Research Cortex dashboard to use the warm editorial design system.

Reference: metis/system/design-docs/claude-design-export/v2-remix/preview/components-kanban.html
Reference: metis/system/design-docs/claude-design-export/v2-remix/_source/partials/planner_kanban.html
Current partial: metis/system/app-py/templates/partials/planner_kanban.html
Current styles: metis/system/app-py/static/styles.css (look at .kanban-col definitions around lines 786-868 and 2332-2408)

The kanban has two competing `.kanban-col` definitions in styles.css:
- Line 795: correct warm stone background #f5f3ee, warm teal header #174c4f
- Line 2332: incorrect cool override using var(--metis-gray-light) and var(--metis-gray)

Fix:
1. Remove the duplicate `.kanban-col`, `.kanban-col-header`, `.kanban-count` definitions at lines 2332-2355 (the planner "variant").
2. The original warm-teal kanban definition should apply to all kanban instances.
3. In planner_kanban.html, verify the column headers use the correct icon glyphs: bi-moon-stars (Someday), bi-hourglass-split (Incubating), bi-lightning-charge (Active), bi-check2-square (Done).
4. Add .kanban-col-active class (top border accent) only to the "Active" column, using var(--warm-teal) as the border color instead of var(--metis-blue).
```

### Prompt 4 — Component Library: Value Boxes + Agent Runs
```
You are implementing two missing components for the Metis Today tab:

1. VALUE BOX STRIP — A 4-up KPI strip showing: Runs today | Tokens today | Open tasks | Active projects
   - Reference: metis/system/design-docs/claude-design-export/v2-remix/preview/components-valuebox.html
   - CSS to add to styles.css (see CLAUDE_DESIGN_BRIEF_TOMORROW.md Section 6 Step 6)
   - Create: metis/system/app-py/templates/partials/today_valuebox.html
   - Create: metis/system/app-py/routers/today.py addition — a new /api/partial/today/valuebox endpoint returning run_count (today), token_sum (today), open_task_count, active_project_count
   - Register in today.html with hx-get="/api/partial/today/valuebox" hx-trigger="load"

2. AGENT RUN ROWS — The existing metis_runs partial should use the design system's run-row layout
   - Reference: metis/system/design-docs/claude-design-export/v2-remix/ui_kits/metis-today/index.html → RecentRuns component, .mk-run grid layout
   - The row grid should be: 56px time | named-agent-badge | 1fr text | 48px tokens (monospace)
   - Current: metis/system/app-py/templates/partials/metis_runs.html
   - Update metis_runs.html to use .run-row class with the 4-column grid layout
   - Add .run-row, .run-time, .run-tokens CSS classes using var(--font-mono) and var(--metis-text-muted)
   - Agent badge should use existing .model-badge-haiku/sonnet/opus but converted to use CSS vars: --metis-haiku-bg/fg etc.
```

### Prompt 5 — Logo SVG Integration + Navbar Polish
```
You are integrating the Metis compass logo SVG and polishing the navbar for the dashboard.

Assets available:
- metis/system/design-docs/claude-design-export/v2-remix/assets/metis-mark.svg
- metis/system/design-docs/claude-design-export/v2-remix/assets/metis-wordmark.svg

Task:
1. Copy metis-mark.svg and metis-wordmark.svg to metis/system/app-py/static/
2. In base.html, replace the current navbar brand:
   <span class="navbar-brand fw-bold me-3" style="font-size:1.1rem; letter-spacing:.04em;">
     <i class="bi bi-cpu-fill me-1 text-primary"></i>Metis
   </span>
   with:
   <a class="navbar-brand metis-brand me-3 d-flex align-items-center gap-2" href="/">
     <img src="/static/metis-mark.svg" width="22" height="22" alt="Metis">
     <span class="metis-wordmark">Metis</span>
   </a>

3. Add .metis-brand and .metis-wordmark to styles.css:
   .metis-brand { font-weight: 700; font-size: 1.05rem; letter-spacing: -0.02em; color: var(--metis-text); text-decoration: none; }
   .metis-wordmark { font-weight: 700; font-size: 1.05rem; letter-spacing: -0.02em; }
   .metis-brand:hover { color: var(--metis-text); }

4. Fix navbar capture button — add box-shadow: 0 2px 8px rgba(0,113,227,0.35) to .btn-capture-nav
5. Fix trust badge — set background:#fff, color:var(--metis-text-muted), border:1px solid var(--metis-border), and color var(--metis-green) only for the shield icon

Reference: metis/system/design-docs/claude-design-export/v2-remix/preview/components-navbar.html for exact design spec.
Keep all hx-get attributes and onclick handlers intact.
```
