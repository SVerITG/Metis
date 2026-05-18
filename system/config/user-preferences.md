# User behavioural preferences

Companion to `user-preferences.json` (which holds app-level settings: display name, active model). This file holds **how the user wants to be worked with** — read at session start by `/metis` and inherited by all entry-point skills.

Update this file when the user signals a preference; never invent entries from a single ambiguous comment. When in doubt, ask before writing.

---

## Cadence

- *(empty — fill from observed signals)*

## Topics that get full attention

- *(e.g., PhD article alignment, surveillance methodology, MLM teaching)*

## Topics to keep short

- *(e.g., status checks, news scans, routine literature pulls)*

## Things to skip

- *(e.g., "don't summarize what you just did", "no closers")*

## Things to keep doing

- *(approaches the user has explicitly validated)*

## Format defaults

- Terseness: high. No closers, no recap, no enthusiasm filler.
- Routing announcements: narrative form per `metis-persona.md`.
- Code: minimal comments. No docstring paragraphs.

---

## How Metis updates this file

- Append, don't rewrite, unless explicitly asked.
- Each entry: one line. If a "why" matters, add a parenthetical.
- Date entries that are likely to expire (e.g., "merge freeze 2026-05-12").
- Remove entries that the user contradicts.
