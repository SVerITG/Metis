# Handoff — Metis design work

**Updated 2026-09-01, end of session. Branch `feat/briefing-rotation-news-surface-interests`.**
**Everything is committed AND pushed to `origin` and `metis-ph` (HEAD `20055719`).**

---

## What the last stretch changed (2026-09-01)

**Today reads top to bottom again.** The Dispatch — the full news file — used to
sit sixth of eleven sections and was the longest thing on the page, so the
boards, the memory zone and the health footer all lived below a screen of news.
It is now the last thing on the surface, closed, and capped at `60vh` when open.
A fold that expands without a limit only moves the problem to the second click.

**Folded is not hidden.** `GET /api/partial/today/news-rail?folded=1` suppresses
the rail's own `<h2>` (it would have printed "Dispatch" one line under the
summary that already says it) and sends the counts back **out-of-band** into
`#dispatch-counts` in the summary. The closed line therefore reads
*"DISPATCH · 482 signals · updated 3h ago"*. `mark_seen` carries `folded` through
so the redraw keeps the right shape. Mark-all-seen deliberately sits **inside**
the body, never in the `<summary>`: a button in a summary is a keyboard trap,
because activating it also toggles the disclosure.

**Cross-pollination now lives on Reflection.** Naming its seed project was not
enough to make it legible on Today — Today's panels each answer a question you
are asking at nine in the morning, and *"here are five things resembling a
project you touched"* is not one of them. Same endpoint, mounted in
`templates/thinking.html` beside the marginalia. Its heading also moved the
"why this project" clause into a sentence below the label, because in a narrow
rail that clause wrapped to four lines.

**Two panels had one name and opposite answers.** *"New in your field · 98 new"*
sat two inches above *"New in your field · Nothing new this week"*. They count
different things — unread library items against this week's feed scan — so the
second is now the **Publication scan**. The pair of windows carry the two names
directly (`What changed in your field yesterday` / `New in your field`) instead
of one heading above both, which had forced each panel to be labelled by its
*source* rather than by what its number meant.

**An empty state is not automatically an achievement.** "That's your day" and
"Nothing is pinned for today" were the same large centred card, so the screen
showed a task that *was* due and, directly under it, a panel announcing no work.
Finishing earns the panel; nothing pinned earns one quiet line (`.focus-none`).

Verification: 460 passing · 4 skipped · 47 HTMX swap sites clean ·
`migrate_inline_styles.py --check` settles at 0.

**Note on running the tools:** pytest and Playwright both live in
`~/.local/share/metis-mcp/.venv/bin/python`, not in the system `python3`.
Running `python3 -m pytest` reports *no module named pytest*, which is easy to
misread as a passing run when it is piped through `tail`.

---

## Read this first

**Screenshots work again, and they run inside Linux now.**

```bash
~/.local/share/metis-mcp/.venv/bin/python tools/shoot.py /work out.png 2200 1600
```

The old `tools/shoot.sh` drove `chrome.exe` across the WSL boundary. That bridge
dropped mid-session and stayed down for a whole day — so the one tool that
catches layout defects was unavailable for exactly the stretch that accumulated
the most unverified visual change, and the documented fix (`wsl --shutdown`)
would have killed the session doing the work.

`tools/shoot.py` uses a browser Playwright keeps in `~/.cache`. It needs
`libasound.so.2` (installed system-wide, and also copied into
`~/.local/lib/metis-shoot` as a fallback).

**The lesson, again:** every layout defect this week was found by a picture and
none by a test. Shoot the surface before believing it.

---

## What the styling now is — decided, not inherited

the researcher chose ten of them from a live studio on 31 August:
**1D · 2C · 3D · 4C · 5A · 6C · 7C · 8C · 9A · 10D**

| | |
|---|---|
| 1D | a row steps aside on hover, accent edge behind it |
| 2C | a new item is a **tinted band**, not a mark on a row |
| 3D | panels lift — border and shadow |
| 4C | 6px corners (badges stay fully round) |
| 5A | headings unchanged — mono caps, hairline |
| 6C | haloed focus ring: page colour, then accent |
| 7C | waiting says "reading the archive…" |
| 8C | a number carries an accent rule under it |
| 9A | list density unchanged |
| 10D | spring easing |

**All ten live in ONE block at the end of `styles.css`.** They cut across ~4,800
lines — the focus ring alone was declared in ten places — so they are kept
together as one dated decision record. That block is the single place to change
the product's feel.

Two picks compound: 1D moves the row, 10D overshoots it. If it ever reads as
restless the fix is `--m-ease-row` and `--m-dur-row`. Two numbers.

---

## The vocabulary that decides everything else

A pill (`.stat`) is a **state**. Plain text (`.tag`) is a **category**. A
bordered button (`.chip-btn`) is a **control**. These never mix, and colour
rides a strict ladder with `.is-quiet` as the default.

**The rule that settled most calls: the most common state must be the quietest.**
Applied by counting, never by taste. And it CUTS BOTH WAYS — when the Library
was marked read, "read" became universal and "unread" became the rare,
informative one, so the emphasis flipped within a session.

**One row anatomy** (`.mrow`, see `_row.html`): `state · title · meta · actions`.
The fixed-width state slot keeps its width even when empty — that is what makes
titles start at the same x down a list.

---

## Built this week

**Today** — reordered around the questions asked at 9am. Brief folded to its
first paragraph. "What needs you today" is ONE section (dated → due strip,
starred → cards). "Where you left off" is folded inside it and every row can pin
its next task straight into the focus. "Connects to" names its seed project.
News-new and Library-new sit side by side. It can reach zero and say so.

**News** — filters sorted by what they do: period out in the open, detail and
density folded behind "Display", the stack link quiet at the end. Keyboard
triage: `j`/`k`, `Enter`, then `l` later, `s` save, `r` read, `x` decline, `?`.

**Library** — 3,083 items marked read with a `read_at` date, so "new" finally
means something. Reading is a tab here now, not a surface. Header figures carry
denominators and are links.

**Work** — categories quietened, "Quiet for 81 days" instead of a raw date,
`active` marked on the rare recent ones.

**The corpus — 48,624 → 40,747 chunks, 657 → 484 documents.** 16% was the same
text stored twice. Merged under aliases rather than deleted: 96 names preserved,
12 flagged. `tools/merge_corpus_aliases.py --undo` lists them.

**New tools:** `check_htmx_swaps.py`, `merge_corpus_aliases.py`,
`dedupe_corpus.py`, `migrate_hover.py`, `shoot.py`.

---

## Open, most valuable first

### 1. The Library relevance scorer is broken
The score saturates at **0.90** and 1,302 of 1,889 sit at **0.0**. The default
"close to my work" view was showing phenomenology and school-nursing papers, all
scored 0.90, to an NTD researcher. **The number is now hidden when it is at the
ceiling** — but that hides a symptom. The scorer needs rebuilding, and the most
promising direction is ResearchRabbit's: rank against a CHOSEN COLLECTION rather
than the whole corpus.

### 2. Twelve flagged corpus aliases
`python3 tools/merge_corpus_aliases.py --undo`. The one that matters: a thesis
by **Mpanya** and a paper by **Kabeya** share a fingerprint — different authors,
identical text, so one file is mislabelled. Both names are kept; open the two
PDFs to settle it.

### 3. Personal detail is in the published git history
`Metis_PH` is published and the release coordinator keeps it current. The last
40 commit messages carried 42 name mentions and 210 HAT references. A rule is
now in `CLAUDE.md` to stop it growing. **Rewriting 503 commits is a separate and
risky decision** — see the redactor's silent partial failure on exactly that job.

### 4. The long tail
- 88 hand-written empty states remain in templates that never import `_empty.html`
  (mostly search/filter empties that do not need the three-part treatment).
- ~2,460 inline `style=` attributes; `migrate_inline_styles.py` is exhausted
  under its current rules.
- 22 inline hover handlers the codemod could not match (transforms, Jinja colours).
- The 33 agent prompts have never been reviewed.

---

## Three things worth not forgetting

**Count before deciding — then check what you are counting.** Every good call
came from counting. But three first-pass counts were wrong: a heading-destruction
check claimed 41 and the real number was 5; a swap audit reported 38 defects of
which 27 were false positives; and a "redundant passage" metric counted a long
page split across two chunks as duplication. A count is a hypothesis until you
look at what it is measuring.

**An element authored in two places will drift.** The library read control, the
Meetings heading, and the morning brief's collapse were each written twice — and
in the brief's case the two collapses hid each other and rendered a BLANK panel.
`tools/check_htmx_swaps.py` catches the HTMX half; it caught two defects within
a minute of my writing them.

**When a fix looks like it needs a threshold, check whether the data is telling
you something.** A "dormant" mark at 60 days landed on 11 of 16 projects. The
instinct was to raise the threshold until the page looked calm. But most of
those projects ARE asleep, and saying so is the most useful fact on the surface —
so the mark inverted instead: activity is rare, and activity is what is marked.
