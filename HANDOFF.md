# Handoff — dashboard design work

**Written 2026-08-27, end of session. Branch `feat/briefing-rotation-news-surface-interests`.**

Start here next session. This replaces "what were we doing?" — it says what was
found, what was fixed, and what is still open, in the order worth doing.

---

## The question that reframed the session

the researcher asked, mid-session: *"Is it me or did nothing change to the design?"*

He was right, and the answer turned out to be measurable rather than a matter of
taste. **The design system is not the problem. Its adoption is.**

Counted across all 199 templates:

| | count |
|---|---|
| Uses of a semantic chip (`.chip--ok/--warn/--alert/--info`) | **12** |
| Hand-rolled inline `background:` on a span or div | **333** |
| Hand-rolled inline uppercase-mono labels | **91** |
| Elements still carrying a `style=` attribute | **2,483** |

`styles.css` already defines a full semantic palette, a button hierarchy, chips,
elevation and washes — all of it careful, all of it documented. Twelve places use
the semantic part of it. That is why every badge on the dashboard is the same
olive, why nothing reads as urgent or new or resolved, and why the surfaces look
flat no matter how many individual defects get fixed.

**So the remaining work is not "design more". It is "wire what already exists".**
That is also why it will look like a real change when it happens — this is a
system-level swap, not fifty spot fixes.

---

## Landed this session

### Committed as `bbbcff60` — the five worst defects from the screenshot sweep
Word-boundary truncation, the mindmap layout, project launch rows, the Library
control stack, run-on empty states. Full detail in the commit message.

### Uncommitted at time of writing (see "First thing to do" below)

**A state/category vocabulary** — `styles.css`, new block above `.btn`.
The rule the dashboard was missing, in two axes that never mix:

- **Shape encodes kind.** A pill is a STATE (true now, false later). Plain small
  text is a CATEGORY (a permanent fact). Categories are most of the labels on
  screen, so they get the quietest form — `.tag`, no box, no colour.
- **Colour encodes urgency**, on a strict ladder: `.is-quiet` (the default, and
  the important one) → `.is-info` → `.is-good` → `.is-warn` → `.is-urgent`
  (solid fill, should be rare).

**The badge-earns-its-place rule, applied to News.** Counted on the rendered
page: `high` was on **100%** of the 24 threads and `not briefed` on **92%**. A
mark on nearly every row cannot distinguish rows — it is ink, not information.
Both are gone; `briefed` (4%) and `changed` (12%) stay. Worth applying to every
other surface: **show a state only when its absence is the common case.**

**Triage icons dim again.** `.ov-item .tri > .tri-btn { opacity: 0 }` had been
written to hide the five per-row action icons until hover. My own earlier
refactor renamed the wrapper to `.acts`, so every selector silently stopped
matching and 300+ glyphs went to full strength on a 60-item News tab. Selectors
now match the markup; icons sit at `opacity: .25` and come up on hover or focus.

**News threading — three genuine bugs in `news_threads.classify()`:**
1. `_match_vocab` required a word boundary on the **left only**, so the alias
   `mali` matched "**mali**gnant" and a pancreatic-cancer story was filed under
   Mali. Now bounded both sides via `_alias_re()` (plurals and possessives still
   match; "chadwick" no longer matches "chad").
2. **A verb could name a thread.** One FDA drug approval appeared as three
   separate running stories — "Approves treatment", "Agency approves",
   "Approves · Mali" — because each headline was named from its own leftover
   verbs. New `_NON_SUBJECT` stoplist; all three now collapse into one thread
   called **"Pancreatic cancer"**.
3. `_distinctive_tokens` took tokens in **headline order**, so filler in front of
   the noun won. Now ranked by length (a crude but effective specificity proxy),
   returned in original order.

**A one-item thread is no longer called a running story.** 93% of threads held
exactly one item — a single link wearing a story's clothes, under an invented
name. Running stories now require ≥2 items; the rest are listed plainly beneath
as "Single reports". This is what removed the four bogus FDA rows.

**Series folded inside a thread.** Ebola · DR Congo opened with Situation Report
13, 14 and 15 — one weekly bulletin, three instalments. `freshness.collapse()` is
now applied per thread: newest instalment shown, `+2 earlier editions` inline,
nothing discarded. This was the researcher's original "I keep seeing Ebola" complaint, and
it was never a clustering bug — the clustering was right; showing every
instalment as news was wrong.

**Row alignment.** Item rows are a two-column grid (`.ov-item-text` | `.acts`),
and `.ov-thread-meta` has a fixed `min-width`, so the action icons sit at the
same x on every row of every thread instead of following the length of the
headline.

**`tools/rethread_news.py`** — new. Re-clusters every news item under the current
rules, because `assign_threads()` only ever touches unthreaded items. Backs both
tables up to `_bak_<stamp>` and carries `news_thread_mentions` (the "briefed"
history, keyed by thread id) across the id change by majority vote. Already run:
`--undo 20260827T1738` reverses it.

---

## First thing to do next session

1. `~/.local/share/metis-mcp/.venv/bin/pytest tests/ -q` — a full run was in
   flight when the session ended. **Check it before committing.**
2. Commit the working tree (see "Landed / uncommitted" above).
3. Nothing is pushed. Branch is local.

---

## What is still open, most valuable first

### 1. Wire the rest of the surfaces to the semantic vocabulary
The single highest-leverage remaining job, and the one that will finally make the
answer to "did anything change?" be yes. The vocabulary now exists and is proven
on News. Apply the same two rules to:

- **Today** — the focus cards build their badge colour inline from a
  `badge_color` string set in `routers/today.py:2010-2036`. Map those five states
  onto `.stat.is-*` instead. `OVERDUE` is the one genuine `.is-urgent` on the
  whole dashboard.
- **Work** — `MEDIUM` priority, and the category tags (`SOFTWARE`,
  `PHD FRAMEWORK`, `SLEEPING-SICKNES` — note it is **truncated mid-word** in the
  card header, which is a separate small bug) should become `.tag`, not pills.
- **Library** — `ARTICLE` / `PREPRINT` kind labels are categories, not states.

Before doing it, run the badge census again the same way: render the page, count
each badge, and drop or invert anything appearing on more than about half the
rows. It is a two-minute check and it decided every good call this session.

### 2. Dead space
- The morning-brief panel on Today holds one collapsed line inside a full-height
  box (~100px of nothing).
- Work project cards: the grid row is sized by the tallest sibling, so a card
  with two tasks carries ~150px of blank below it. `align-items: start` on the
  grid is most of the fix.

### 3. The unexplained block at the top of Work
Five rows — Personal, Seroconversion, Angola HAT Analysis, HPC Clustering,
Detection Coverage — each with a long underline bar and `MEDIUM` on the right.
There is no header and no legend. I could not tell from the screenshot what it
is meant to convey; the bar is the same length on all five, so it is not a
progress meter. **Ask the researcher what he expects this to show before changing it.**

### 4. News, remaining
- `changed` is on 12% — fine — but confirm it means something to the researcher.
- The threading still leaves 95% of items as singletons. That is honestly
  presented now, but if better clustering is wanted the next step is title
  similarity within a time window, not more vocabulary.
- Category tabs (Outbreaks, World news, …) have not been looked at at all.

### 5. The long tail
- ~2,480 inline `style=` attributes remain. `tools/migrate_inline_styles.py`
  handles the mechanical ones; the test asserting it is idempotent will catch
  new ones.
- The 33 agent prompts have never been reviewed.
- `system/config/feature-backlog.md` — 84 open items.

---

## Two things worth not forgetting

**Screenshots find what tests cannot.** `bash tools/shoot.sh /news out.png` takes
one second. Across two sweeps it found: raw HTML printed on every page, an
illegible mindmap, mid-word truncation, ragged launch rows, and the dimming
regression above — every one of them invisible to 456 tests, a byte-count audit
and a rendered-text snapshot, because the text was all present and correct. It is
the layout that was wrong, and only a picture shows layout.

**Count before deciding.** Three of this session's better calls came from
counting rather than judging: the badge census (100% / 92%), the semantic-chip
adoption number (12), and the singleton share (93%). The one place I guessed
instead — assuming better thread ids would reduce fragmentation — was wrong: the
rethread produced *more* singletons, not fewer, and the dry run caught it before
anything was written.
