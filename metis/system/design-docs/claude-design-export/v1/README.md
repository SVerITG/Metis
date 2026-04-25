# Metis Design System

_Archive edition — v1.0_

A design system for **Metis**, a personal knowledge-work companion for Stan. The product is a single web app with nine connected surfaces: Today, Knowledge, Thinking, Planner, Work, Meetings, Learning, Teach, and Metis (settings & model).

This system is the canonical source of truth. Read the relevant sections before designing anything in this project — do not guess.

---

## 1. What Metis is (context)

**Metis** is Stan's second brain and daily operating surface. It is not a chatbot and not a notes app — it is a **workbench for thinking**, organized like a working archive: shelves, index cards, slipcases, and a marginal hand (the assistant) that reads alongside you, proposes moves, and never interrupts.

### Product anatomy — the nine surfaces

| # | Surface | One-line purpose |
|---|---------|------------------|
| 1 | **Today** | The morning briefing. Agenda, open threads, one focus. |
| 2 | **Knowledge** | Personal library. Notes, clippings, sources, concept links. |
| 3 | **Thinking** | Active reasoning spaces — long-form dialogues with Metis. |
| 4 | **Planner** | Horizons. Quarters → weeks → today, with intentions. |
| 5 | **Work** | Projects, tasks, kanban. The doing surface. |
| 6 | **Meetings** | Prep, transcripts, follow-ups, one-pagers. |
| 7 | **Learning** | Courses, study plans, spaced-repetition queues. |
| 8 | **Teach** | Drafts outward — essays, lessons, talks Stan is producing. |
| 9 | **Metis** | Settings, model, memory, keys, billing. |

### Voice & tone — how Metis speaks

Metis sounds like **a literate, patient assistant working in the same room.** It is not chipper, not corporate, not mystical.

- Prefers **the short declarative sentence.** One clause. Then another.
- Uses **proper em-dashes, semicolons, and italics.** Honors typography.
- Offers rather than asks. _"Three threads from yesterday are still warm."_ Not _"Would you like me to..."_
- Uses **lowercase freely in chrome** (`inbox`, `today`, `thinking`) and **sentence-case in prose.**
- Names things. `Thursday's notes on Kripke.` Not `Your recent note.`
- Never uses exclamation marks. Rarely uses emoji. Never gamifies.
- Calls the user by name (**Stan**) sparingly, at thresholds — morning greeting, end-of-day, first use of a new surface.

**Never:**
- "Let me help you with that!" / "Great question!" / "I'd be happy to…"
- Celebration language, streak language, "well done" language.
- Tech jargon leaking into user copy (no "embedding", "tokens", "vector").

---

## 2. Design direction — Archive

The chosen direction is **Archive**: an editorial, research-journal aesthetic. Paper, rules, and typographic hierarchy do almost all the work; color and shadow are restrained.

### Foundational moves

1. **Paper over panels.** Bone-white surfaces (`--m-surface: #fbf8f0`) on warm off-white ground (`--m-bg: #f5f2ea`). No pure white.
2. **Serif for voice, sans for chrome, mono for labels.** Newsreader (Stan) for greetings, titles, editorial body. Inter for UI. JetBrains Mono, UPPERCASE, wide-tracked, for section labels and meta.
3. **Forest-green ink + muted ochre.** Green is primary. Ochre is the single warm accent — used for highlights, annotations, warnings. Alert-red is brick, never fire-truck.
4. **Rules over shadows.** Prefer 1px dividers to drop shadows. Shadows exist but are `rgba(31, 42, 36, 0.05)` subtle.
5. **Near-square radii.** `--m-radius: 3px`. Paper has edges.
6. **Italic `s` in the wordmark.** The one typographic flourish that signals "this is a crafted tool, not a SaaS product."

### The dark twin — Observatory

Dark mode is **Observatory**: the same archive, lit by a brass lamp at night. Warm near-black (`#15130f`), cream ink, single amber accent (`#d99a4c`). Opt-in via `data-theme="observatory"` or `.theme-observatory` on any ancestor. OS dark-mode is also honored unless `data-theme="archive"` is set explicitly.

---

## 3. Content fundamentals

Rules for **what Metis says and how it says it**, applied system-wide.

### Dates & time
- Today's date in the morning briefing: **"Thursday, November 14"** (serif, full month).
- In lists and meta: **"Nov 14"** or **"Thu · 14 Nov"** (mono, abbreviated).
- Times are 24h by default in UI meta (`14:30`), 12h in prose (`at 2:30`).
- Relative times are allowed in prose ("twenty minutes ago") but rendered in mono with absolute fallback in UI (`20m · 14:10`).

### Numbers & units
- Tabular numerals everywhere for counts (`.tabular` utility).
- Counts ≥ 1000 use thin-space grouping: `1 240`, not `1,240`.
- Durations: `45m`, `2h 10m`, `3d` — mono, no spaces before unit.

### Labels (UPPERCASE mono)
The Archive rhythm-keeper. Use sparingly but deliberately:
- Section headers (`SHELVES`, `ACTIVE THREADS`, `FOLLOW-UPS`).
- Metadata rows (`SOURCE · HIGHLIGHTED · 14 NOV`).
- Model tiers and system states (`HAIKU`, `THINKING`, `DRAFT`).
- Never mix with icons in the same cell — the label _is_ the signifier.

### Titles
- Serif, sentence-case, 500 weight.
- Prefer specific nouns over abstractions: **"Kripke's rigid designators"** not **"Philosophy note"**.
- No title-case. No clickbait.

### Empty states
Always written as a quiet observation, never a prompt:
- ✅ _"No meetings today. The calendar is clear through Friday."_
- ❌ _"Add your first meeting!"_

### Assistant turns (Metis speaking)
- Open with the observation, not the offer. _"Two of these threads are converging."_
- Offer next moves as **a short list of verbs**, one per line, each linkable.
- When unsure, say so plainly. _"I can't tell which you mean. The 2019 paper, or the lecture?"_

### Error language
- Brick-red, sentence-case, no exclamation. _"That couldn't be saved. The connection dropped; nothing was lost."_
- Always include what the user should do next.

---

## 4. Visual foundations

### Color system
See `colors_and_type.css` for the full token set. Semantic roles:

| Role | Archive | Observatory |
|------|---------|-------------|
| Page ground | `#f5f2ea` | `#15130f` |
| Paper / card | `#fbf8f0` | `#1c1915` |
| Primary ink | `#1f2a24` | `#f3ead6` |
| Body text | `#2c3a33` | `#d9cfba` |
| Meta / muted | `#7a8178` | `#8a8075` |
| Primary accent | `#2d4a3a` forest | `#d99a4c` amber |
| Secondary accent | `#9a7b3c` ochre | `#e0b07a` amber-soft |
| Positive | `#5a7a5e` moss | `#a9c89a` |
| Warning | `#9a7b3c` ochre | `#e0b07a` |
| Destructive | `#a84632` brick | `#e28570` |
| Info | `#3e6178` blue-slate | `#92b3c5` |

Model-tier tints (for `Haiku` / `Sonnet` / `Opus` badges) are warm, low-saturation — they sit in the archive, they don't compete.

### Type scale
| Token | Size | Use |
|-------|------|-----|
| `--t-display` | 42 / 1.08 | Hero greetings ("Good morning, Stan.") |
| `--t-h1` | 30 / 1.2 | Page titles (serif) |
| `--t-h2` | 24 / 1.25 | Section titles (serif) |
| `--t-h3` | 20 / 1.3 | Card titles (serif) |
| `--t-h4` | 17 / 1.35 | Subsection (serif or sans) |
| `--t-body-lg` | 16 / 1.6 | Editorial prose |
| `--t-body` | 15 / 1.55 | UI body |
| `--t-small` | 13 / 1.45 | Dense UI, controls |
| `--t-meta` | 12 / 1.4 | Metadata rows |
| `--t-micro` | 11 / 1.4 | UPPERCASE mono labels |

Tracking: `-0.025em` on hero, `-0.015em` on body, `+0.14em` on caps-labels, `+0.18em` on wider section dividers.

### Spacing
4px base: `--m-s-1` (4) through `--m-s-20` (80). Favor generous vertical whitespace — editorial density, not dashboard density. A typical card has `24px` internal padding; sections separate by `48px` or a rule.

### Radii & borders
- `--m-radius: 3px` — cards, modals.
- `--m-radius-sm: 2px` — buttons, inputs.
- `--m-radius-pill: 999px` — chips, pills, avatars.
- `1px solid rgba(31, 42, 36, 0.12)` — default rule.

### Shadows
Barely there. Default card shadow is `0 1px 0 rgba(31, 42, 36, 0.04), 0 4px 14px rgba(31, 42, 36, 0.05)`. Modal shadow is `0 2px 0 rgba(0,0,0,0.04), 0 12px 36px rgba(31,42,36,0.08)`. Never use colored shadows.

---

## 5. Iconography

**Prefer labels over icons.** Archive relies on UPPERCASE mono labels where most products reach for icons. When an icon is needed, draw it in the same hand as the mark:

- 1.5px stroke, round caps, round joins
- 20px or 24px bounding box
- No fills (except a single 2px pivot dot where useful — matches the mark)
- Color: `currentColor` — icons inherit from their text context

Do not use off-the-shelf icon sets (Feather, Lucide, Material). When the design calls for an icon and one doesn't exist, use a **UPPERCASE mono label in brackets** as a placeholder — `[TASK]`, `[NOTE]`, `[THREAD]` — and flag it in comments. Do not auto-draw "AI slop" icons.

The Metis mark itself (`assets/metis-mark.svg`) is the prototype: concentric index rings, compass axes, a central pivot point. Any bespoke iconography should feel drawn by the same hand.

---

## 6. Components

Built in `preview/` as review cards. The kit is intentionally small:

- **Button** — primary (forest), secondary (outlined), ghost, destructive (brick). Mono caps label treatment on small buttons; sentence-case on large.
- **Input / Textarea** — paper field, 1px rule, forest focus ring.
- **Badge / Chip** — pill, mono caps, semantic washes.
- **Card** — paper surface, 1px rule, `24px` pad, optional seclabel header.
- **Seclabel** — section label with trailing rule (`.seclabel` utility).
- **Menu / List row** — 1px separator, hover wash `--m-accent-wash`, left-rule indicator for selected.
- **Toast / Banner** — flat, semantic wash, no icon by default.
- **Avatar** — 32/40/56px, pill, cream background, serif initial.
- **Modal / Drawer** — paper, rule-framed, no drop shadow on mobile.
- **Command bar** — mono input, fixed-width results, forest cursor.
- **Thread / Message** — two-column editorial; Metis left-margin annotation, Stan right-hand prose.

---

## 7. Files in this project

```
colors_and_type.css        ← foundational tokens + utilities (import this globally)
assets/
  metis-mark.svg           ← primary mark (forest)
  metis-mark-ochre.svg     ← dark-mode mark (amber)
  metis-wordmark.svg       ← wordmark with italic s
preview/
  *.html                   ← design system review cards (Type, Colors, Spacing, Components, Brand)
ui_kits/metis/
  app.html                 ← the nine-surface product mock
SKILL.md                   ← short instructions for using this system
README.md                  ← this file
```

---

## 8. Caveats

- **Newsreader & Inter load from Google Fonts.** If offline, fall back to Iowan Old Style / Palatino and system sans respectively.
- **Archive is the primary direction.** Observatory is a complete dark twin but all design decisions were made in Archive first.
- **The nine-surface UI kit is a mock.** It demonstrates applied design — it is not a working product. Placeholders are drawn in with ochre `[placeholder]` notation.
- **Icons are sparse and bespoke.** There is no icon library. When composing new screens, lean on mono labels before reaching for a glyph.
