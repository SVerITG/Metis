# Metis Today — UI Kit

A pixel-faithful recreation of the main "Today" surface from the Research Cortex / Metis system (originally a FastAPI + htmx single-page app at `system/app-py/`). Built with React 18 + Babel-in-browser, styled with the project's `colors_and_type.css` plus a small kit-local `kit.css`.

## Files

- `index.html` — bootstraps React + Babel, loads `kit.jsx`, renders `<TodayPage />`.
- `kit.jsx` — all components in a single Babel file, each exposed on `window`.
- `kit.css` — layout + component styles layered on the shared tokens.

## Components

| Name | What it is |
|---|---|
| `TopNav` | Glass translucent nav with 8 module tabs, Capture pill, local-first trust chip. |
| `MorningBrief` | Warm editorial briefing block — serif greeting, status chips, "Today's paper". |
| `ValueBoxStrip` | 4-up KPI tiles (runs / tokens / tasks / projects). |
| `RecentRuns` | Glass card listing agent runs with model-tier-colored badges. |
| `InboxCard` | Agent inbox rows with HIGH/MEDIUM/LOW signal boxes + dismiss. |
| `CaptureBar` | Idea/Task/Note/Ask-Metis mode toggle + ⌘↵ submit textarea. |
| `ProjectKanban` | 3-column Someday / Incubating / Active board. Click a card to promote. |

## Interactions (prototype-level)

- Tab switching in `TopNav`.
- Capture → toast notification (no persistence).
- Inbox items dismissable.
- Kanban cards click to promote to the next column.

Anything beyond this (real agent runs, routing, persistence) is intentionally out of scope — this is a UI kit, not a working app.

## Not included

- Knowledge / Thinking / Planner / Meetings / Learning surfaces. Tabs are visual only.
- Metis chat panel.
- Dark mode (the source app is light-only).
