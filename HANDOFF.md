# Handoff — dashboard design work

**Updated 2026-08-28. Branch `feat/briefing-rotation-news-surface-interests`.**
**Last commit `13fbd59e`. Nothing is pushed — the branch is still local.**

---

## The finding that still governs this work

*"Is it me or did nothing change to the design?"* — the answer was measurable.
**The design system was never the problem. Its adoption was.**

Count the *rendered* pages, not the templates: a Metis surface's first-paint HTML
is an empty shell and everything that carries a badge arrives later over HTMX, so
counting source files undercounts what actually ships. On seven surfaces:

| | before | now |
|---|---|---|
| semantic state classes in use | 4 | **46** |
| quiet category labels | 175 | **252** |
| inline `style=` attributes | 9,142 | 8,940 |
| inline backgrounds | 2,232 | 2,112 |

`tools/` has no census script — the one used here lives in the session
scratchpad. If you want it permanently, it is twenty lines: fetch each surface,
follow its `hx-get`s one level, count.

---

## The vocabulary, in one paragraph

**Shape encodes kind.** A pill (`.stat`) is a STATE — true now, false later. Plain
small text (`.tag`) is a CATEGORY — a permanent fact. A bordered button
(`.chip-btn`) is a CONTROL you press. These never mix.
**Colour encodes urgency**, on a strict ladder: `.is-quiet` (the default, and the
important one) → `.is-info` → `.is-good` → `.is-warn` → `.is-urgent`.
The rule that decides most calls: **the most common state must be the quietest**,
or the loud treatment stops carrying information at all.

Now applied on: Today focus, Work cards + filter strip + Due Today, Library
catalogue and new-literature rows, Learning reviews, Reflection threads and
marginalia, Meetings connections.

---

## Landed in `13fbd59e`

Full detail is in the commit message — it is long on purpose. The short version:

- **Categories quietened everywhere.** 24 identical olive pills on Work became
  quiet text; `OVERDUE` is now the only coloured badge on that page.
- **Labels removed because they were on every row**, each with a count behind it:
  `ARTICLE` 60% · `UNREAD` 25/26 · `OVERDUE` 10/10 · `OPEN` 11/11 · `NOTE` 3/3 ·
  `medium` 5/5 · a memory badge printing `0` on 4 of 6 cards.
- **`OVERDUE` on spaced repetition became *how late*** — 45d, 44d, 8d, due today.
  A constant label cannot rank; a number can, and ranking is the only question
  that list has to answer.
- **The Learning sparkline** had `width:100%` and no `height`, so a 276×62
  viewBox scaled to ~258px tall across a wide panel — that was the giant empty
  box, and the same scaling blew `font-size="8"` axis labels up to ~33px.
- **`/work` scrolled sideways** — grid items default to `min-width:auto`.
- **The Intentions bar** was priority drawn as a length beside the word that
  already said it; five medium projects drew five identical 55% bars. It now
  shows tasks actually closed (HAT Metric: 4/5) and is omitted when there is
  nothing to measure.
- **Five headings were deleted by HTMX on load** (they sat inside an
  `innerHTML` swap target). Three needed fixing; two already emitted their own.
- **`/meetings` "Next meetingNONE SCHEDULED"** — the route returned two bare
  spans into an `outerHTML` swap on an `<h2 class="sec-label">`.
- **`#news-briefings` was destroyed on load**, and the two refresh buttons
  inside the partial target that id — so they did nothing after first paint.
- **`--m-muted-soft`** had drifted back into 6 CSS rules and 13 templates as
  real type, despite the stylesheet documenting it as retired for text.

### New tool — `tools/check_htmx_swaps.py`
Asserts an `outerHTML` swap returns the tag and classes it replaces, that no
heading sits inside an `innerHTML` target, and that a swapped-in element does not
re-trigger itself. Found 11 real defects. Currently green — run it after any
template or partial-route change.

```bash
python3 tools/check_htmx_swaps.py     # needs the dashboard running on 8080
```

### The test suite was not running at all
`bs4` was missing from the venv, so collection aborted and the "456 tests"
everyone was trusting had not executed. Installed. **456 pass, 4 skipped.**

---

## Open, most valuable first

### 1. The relevance score saturates — a scorer bug, not a display one
`new_publications.relevance` maxes at exactly **0.90 and 41 items sit on it**,
while **1,302 of 1,889 are exactly 0.0**. The default view sorts by relevance, so
the first screen is a tie at the ceiling in date order, every row printing the
same number. The tooltip now discloses the tie; the scoring itself is untouched
because that is an algorithm decision, not a design one. **Ask the researcher whether the
0.90 cap is intended before changing it.**

### 2. Surfaces still at zero semantic adoption
`/meetings` and `/teach` have had only spot fixes. `/thinking` is at 1.
Run the census, then apply the same two rules.

### 3. Remaining dead space
- Meetings: four stat boxes stacked full-width for four numbers; the whole
  lower two-thirds of the page is empty when there are no meetings.
- The morning-brief panel on Today draws a full-width bordered box around text
  capped at 78ch, leaving ~440px of nothing inside the border on a wide screen.
  Either cap the panel or use the right column.

### 4. The long tail
- ~2,464 inline `style=` attributes. `tools/migrate_inline_styles.py` is
  **exhausted** — 0 substitutions left under its current rules. Getting further
  means adding rules for the next most common declaration sets.
- Duplicate section headings on Meetings (`LIVE ASSIST`, `VOICE PROFILES` each
  render twice — once as `sec_label`, once inside the partial).
- The 33 agent prompts have never been reviewed.
- `system/config/feature-backlog.md` — 84 open items.

---

## Three things worth not forgetting

**Screenshots find what tests cannot.** `bash tools/shoot.sh /news out.png` takes
one second and found every layout bug in this commit. 456 tests found none of
them, because in each case the *text* was correct and only its wrapper or its
scale was wrong.

⚠ **Screenshots are currently unavailable**: WSL's `WSLInterop` binfmt
registration dropped mid-session, so `chrome.exe` fails with *"Exec format
error"*. Re-registering needs root. Fix: `wsl --shutdown` from Windows, then
reopen. Nothing else is affected.

**Count before deciding — then verify the count.** Every good call here came from
counting. But *two* first-pass counts were badly wrong: a heading-destruction
check claimed 41 sites and the real number was 5, and the first HTMX swap audit
reported 38 defects of which 27 were false positives (it ignored `hx-target`,
did not send the `HX-Request` header, and took a leading `<style>` as the root
element). A count is a hypothesis until you check what it is actually counting.

**An element authored in two places will drift.** Both the library read/unread
control and the Meetings heading were written once in a template and once in a
route, and the copies diverged. The bug is invisible on load and only appears
after the first interaction. That is what `check_htmx_swaps.py` exists to catch.
