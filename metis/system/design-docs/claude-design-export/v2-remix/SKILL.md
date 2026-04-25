---
name: metis-design
description: Use this skill to generate well-branded interfaces and assets for Metis (Research Cortex), either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the README.md file within this skill, and explore the other available files.

Key files:
- `README.md` — brand context, content fundamentals, visual foundations, iconography.
- `colors_and_type.css` — all design tokens (CSS variables) + semantic classes.
- `assets/` — Metis logo SVGs.
- `preview/` — reference card snippets for each token group / component.
- `ui_kits/metis-today/` — React UI kit for the primary "Today" surface (nav, morning brief, runs, inbox, capture, kanban).

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. Always link `colors_and_type.css` and Bootstrap Icons 1.11.3 (CDN). Use IBM Plex Serif + JetBrains Mono from Google Fonts.

If working on production code, copy assets and internalise the rules in README.md — especially the dual macOS/warm palette and the content voice (first-person to Sander, agents named in third person, no emoji).

If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.
