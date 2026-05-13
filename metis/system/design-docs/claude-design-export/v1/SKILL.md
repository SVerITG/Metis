# Metis Design System · Skill

This project is the canonical design system for **Metis** — a personal knowledge-work companion for one researcher. Nine connected surfaces: Today, Knowledge, Thinking, Planner, Work, Meetings, Learning, Teach, Metis.

## Before you design anything

1. Read `README.md` — product context, voice, visual foundations, iconography.
2. Import `colors_and_type.css` globally. It defines every token and utility.
3. Look at `preview/*.html` for applied type, color, spacing, components, brand.
4. Look at `ui_kits/metis/app.html` for the nine-surface application in situ.

## Direction — Archive (primary)

Editorial, research-journal. Bone-white paper on warm off-white. Forest-green ink. Muted ochre as the single warm accent. Newsreader serif for voice; Inter for chrome; JetBrains Mono, UPPERCASE, for labels. Near-square radii (3px). Rules over shadows.

**Dark twin:** Observatory — warm near-black, cream ink, amber accent. Opt in via `[data-theme="observatory"]` or `.theme-observatory`.

## Voice

Metis observes before offering. Short declaratives. Proper em-dashes and italics. No exclamation marks. No celebration. UPPERCASE mono labels (`SHELVES`, `ACTIVE THREADS`) where other apps use icons. Never "Let me help" — instead: "Three threads from yesterday are still warm."

## When composing new screens

- Reach for a **label** (`.label-caps`) before reaching for an icon.
- Titles in serif (Newsreader), sentence-case, with specific nouns.
- Meta (dates, counts, status) in mono UPPERCASE, `+0.14em` tracking.
- Paper surfaces (`--m-surface`) on the ground (`--m-bg`). No pure white.
- Forest accent for primary, ochre for warm/warning, brick for destructive.
- Drop shadows are barely-there; prefer 1px rules.
- Spacing generous — editorial, not dashboard.
- Placeholders stay as visible `[PLACEHOLDER]` mono tags until real content exists.

## File map

```
colors_and_type.css   · foundational tokens + utilities
assets/               · mark, ochre mark, wordmark
preview/              · design-system review cards (Type, Colors, Spacing, Components, Brand)
ui_kits/metis/
  app.html            · the full application shell
  app.css             · app-specific styles
  shell.jsx           · Sidebar, Topbar, icons, chips, mark
  surfaces/*.jsx      · one file per surface
README.md
SKILL.md  (this file)
```

Do not invent tokens — extend `colors_and_type.css`.
Do not reach for off-the-shelf icon sets — the hand is bespoke.
Do not use pure white, drop shadows over 0.1 opacity, or emoji.
