# Claude Design Handoff — Metis v7.1 → next iteration

## What Claude Design already has in the project
- `nifty-stargazing-sifakis.md` — full visual spec (Part 1: palette, typography, layout)
- `Metis_Design.png` — editorial screenshot reference

## What's currently live (v7.1)
- `styles.css` v7.1 with macOS-inspired editorial tokens
- Today page: dateline → hero → 3-col canvas (focus | activity | news rail) → actions → question prompt
- Hero greeting: Georgia 3.1rem, italic narrative 2.05rem
- Knowledge graph (D3 force-directed)
- Span waterfall (Metis tab)
- News rail with category chips
- Launcher cards that open Windows programs

## What Claude Design should explore next (in order)

1. **Dark mode** — token palette for night work sessions. Preserve editorial feel. No glassmorphism. The existing palette lives in `styles.css` as CSS custom properties on `:root` — dark mode should override those on `[data-theme="dark"]` or `@media (prefers-color-scheme: dark)`.

2. **Micro-interactions** — hover states on launcher cards, news item transitions, toast animations. The feel should reinforce a "quiet desk lamp" quality: nothing bounces, nothing flashes. Subtle opacity/translate transitions at 150–200ms.

3. **Learning tab visual** — currently utilitarian. Needs editorial treatment: course cards as a reading list, progress as understated progress bars, spaced repetition as "tomorrow's desk". See `templates/partials/` for learning_* partial templates.

4. **Mobile/tablet responsive** — desktop-first currently. The 3-col canvas (`.today-canvas`) needs a single-column fallback at < 900px that preserves hero-first-then-focus reading order.

5. **Empty states** — when there are no news items, no courses, no tasks — each needs an editorial "clean slate" message rather than a blank box. Tone should be calm and purposeful, not chirpy.

## What to NOT touch
- The 9-tab nav structure (Today, Knowledge, Meetings, Learning, Work, Thinking, Planner, Teach, Metis) — locked.
- The editorial type scale (Georgia serif for voice, Inter for UI chrome).
- The "no glassmorphism, no backdrop-filter" rule.
- The macOS-inspired token naming convention in `styles.css`.

## How to hand back to Claude Code (Opus/Sonnet)
When Claude Design produces updates:
1. Save new CSS as `styles.css` (version it: `/* v7.2 */` at top)
2. Save any new partials to `metis/system/app-py/templates/partials/`
3. Write a short `CHANGES.md` at the top of the delivery: what changed, which tokens were added/removed, which files are new
4. Place everything in `metis/system/design-docs/deliveries/YYYY-MM-DD/`
5. Tell Claude Code "Resume post-Claude-Design" — it will read `CHANGES.md` and integrate without re-scanning

## Budget
- One Claude Design session per visual pillar (dark mode = 1, micro-interactions = 1, etc.)
- If something needs back-and-forth, note it in `CHANGES.md` — Opus can review and respond in a single Claude Code turn
