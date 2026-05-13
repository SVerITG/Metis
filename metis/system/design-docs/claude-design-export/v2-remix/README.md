# Metis Design System

A design system distilled from **Research Cortex / Metis** — a personal AI ops platform for a field epidemiologist (NTD surveillance, multilevel models). Local-first FastAPI + htmx app with a consolidated `styles.css` (≈3.5k lines) plus Quarto notebooks and a Typst academic template.

## Sources

- Codebase: `_source/Research Cortex/` (read-only mount). Core design tokens live in `system/app-py/static/styles.css`; templates in `system/app-py/templates/`; Typst article style in `articles/article-1/style.typ`; Quarto `_quarto.yml` + `custom.scss` in `knowledge/`.
- No Figma. No slide decks attached.

## Index (this folder)

- `README.md` — this file (context, content fundamentals, visual foundations, iconography)
- `colors_and_type.css` — CSS variables: colors, fonts, and semantic classes (`.h1`, `.body`, `.meta`, `.mono`, `.launch-cmd-block`, …)
- `SKILL.md` — agent-invocable skill manifest
- `assets/` — logo SVGs (`metis-wordmark.svg`, `metis-mark.svg`)
- `preview/` — small HTML cards populating the Design System tab
- `ui_kits/metis-today/` — React UI kit for the main "Today" surface

## Products represented

1. **Metis Today** (primary) — the unified morning-brief + agent-runs + capture + kanban surface.
2. *Quarto knowledge base* and *Typst academic articles* — acknowledged in tokens (IBM Plex Serif, warm teal) but no separate UI kit this pass.

## Content fundamentals

- **Voice.** First-person, directed at the owner ("Good morning, Sander."). Tools speak as named agents ("Librarian tagged 3 papers"). System never says "I" as Metis-the-assistant.
- **Tone.** Warm-editorial for reflective surfaces (morning brief, journal, learning); neutral-utilitarian for operational chrome (nav, cards, KPIs). Never marketing-y.
- **Casing.** Title Case for module names and tab labels (Today, Knowledge, Thinking). Sentence case for body and button labels ("Scan now", "Capture"). UPPERCASE + .05em tracking only for small labels (KPI caps, signal chips: `HIGH` / `MEDIUM` / `LOW`).
- **Dates.** Long form in briefs ("Tuesday 21 April 2026"); ISO-ish compact in metadata rows ("2026-04-21 · librarian · 12k").
- **Numbers.** Rounded, humanised: `412k` tokens, `€2.71`, `14 GB`. No trailing zeros.
- **Emoji.** Not used in product chrome. Icons come from Bootstrap Icons.
- **Microcopy.** Short and concrete. Agent outputs are past-tense statements of fact ("Reviewed Article 1 design, suggested sensitivity analysis"), not promises.

## Visual foundations

- **Dual palette.** (A) **macOS system layer** (primary chrome) — `#f5f5f7` bg, translucent white surfaces, `#1d1d1f` text, `#0071e3` accent. (B) **Warm editorial layer** (reflective content) — `#faf9f6` cream, `#f6f3ec` parchment, `#174c4f` teal, `#b36a1d` amber, `#1f2a2e` ink. The two coexist: macOS chrome hosts warm editorial content, like a native shell hosting a journal.
- **Type.** System stack (`-apple-system`) for UI. **IBM Plex Serif** 400/500/600/700 for reflective text (morning greetings, course titles, article heads). **JetBrains Mono** for launch commands, metadata, and context blocks. Display h1 is 1.75–2rem, 700, `-0.03em` tracking. Body is `.9375rem / 1.6`, `-0.01em`.
- **Spacing.** Bootstrap-style scale (`.25rem` … `3rem`). Cards pad `1rem`; card headers pad `.875rem 1rem`. Section labels sit on `.375rem` vertical whitespace with `.05em` tracking.
- **Corners.** `12px` for cards/modals, `8–10px` for inputs/buttons, `6px` for badges, `5px` for tight tiles, `999px` for the Capture pill and trust chip, `3–5px` for kanban cards and paper blocks.
- **Shadows.** Three levels: card `0 2 12 rgba(0,0,0,.08)`; modal `0 8 32 rgba(0,0,0,.12)`; warm-hover `0 12 28 rgba(23,76,79,.12)`. Focus ring `0 0 0 3 rgba(0,113,227,.15)` plus blue border.
- **Backgrounds.** Flat colors + translucent-white glass. **No gradients** except the warm `linear-gradient(135deg, #f6f3ec → #faf9f6)` for morning briefs. No photography, no illustrations, no patterns. No full-bleed imagery.
- **Borders.** `1px solid rgba(0,0,0,.1)` on system surfaces. Warm surfaces use `rgba(23,76,79,.1)`. Left-border accents carry semantic weight: teal 4px = morning brief; amber 3px = paper callout; red 3px = blocked task.
- **Blur.** `backdrop-filter: saturate(180%) blur(20px)` on nav; `blur(20px)` on cards. Used sparingly — only where the layer needs to feel "above".
- **Animation.** Subtle. 150ms ease on hovers; kanban cards lift `translateY(-1px)` + warm-hover shadow. No bounces, no springs, no page transitions.
- **Hover.** System: pale-blue tint (`#e8f0fe`) for tabs; darker-blue (`#005bbf`) for primary buttons; `rgba(0,0,0,.04)` wash for ghost buttons. Warm: teal shadow lift for cards.
- **Press.** Implicit — no active-state shrink or color flash. Rely on hover + focus ring.
- **Imagery vibe.** No real imagery in product. When added downstream, prefer warm desaturated photography, never cool/tech stock.
- **Layout rules.** Fixed top nav; 2-column primary grid (`1.25fr 1fr`) on Today; 3-column kanban; KPI strips are 4-up. Max content width is viewport — the app fills the window.

## Iconography

- **Primary set: Bootstrap Icons 1.11.3** — pulled from the source app's `<link>` to jsdelivr. This is a non-negotiable match. Common glyphs: `bi-cpu-fill` (Metis mark/brand), `bi-sun` (Today), `bi-book` (Knowledge), `bi-lightbulb` (Thinking/Idea), `bi-calendar3` (Planner), `bi-briefcase` (Work), `bi-camera-video` (Meetings), `bi-mortarboard` (Learning), `bi-robot` (Metis agent / Ask), `bi-plus-lg` (Capture), `bi-shield-check` (Local-first / safety), `bi-check-circle` (done), `bi-exclamation-circle` (warn), `bi-inbox`, `bi-clock-history`, `bi-arrow-clockwise`, `bi-check2-square`, `bi-journal-text`, `bi-moon-stars`, `bi-hourglass-split`, `bi-lightning-charge`.
- **Size / weight.** Inline with surrounding text (no fixed px). Color inherits from parent unless it's the brand mark (`#0071e3`) or trust chip (`#30a46c`).
- **Emoji.** Not used.
- **Unicode as icon.** Used only for inline typographic glyphs: `⌘`, `↵`, `→`, `·`, `…`.
- **Custom SVG.** Only the Metis logo (`assets/metis-wordmark.svg`, `assets/metis-mark.svg`). Simplified from the `bi-cpu-fill` mark + "Metis" wordmark, designed to be substitutable back to the icon+text combo used in the nav.
- **Substitutions.** None — Bootstrap Icons is directly CDN-linked in the source.

## Font substitution flag

- `colors_and_type.css` loads **IBM Plex Serif** and **JetBrains Mono** from Google Fonts (source uses the same CDN). No local font files in this system. If you want these vendored, drop the `.woff2` into `fonts/` and the CSS `@import` line can be replaced with `@font-face`.

## Caveats

- No slide template exists in the source — `slides/` was intentionally omitted.
- No Knowledge/Planner/Thinking/Meetings/Learning UI kit this pass; tabs are visual only.
- Dark mode is not in the source and isn't here.
- Metis logo is a stylized recreation of the `bi-cpu-fill` + "Metis" pairing used in the nav — swap it if a real wordmark ever exists.

## Bold ask

**Review the Today UI kit and the preview cards.** Tell me which tokens, badges, or components feel off versus your memory of the real Metis app — especially the **Capture**, **Morning brief**, and **agent-badge colors**. Then tell me which *second* surface to build next: Knowledge (library/graph), Planner (kanban+timeline+strategy), or Metis (agent chat).
