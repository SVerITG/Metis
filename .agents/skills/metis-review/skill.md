---
name: metis-review
description: "metis review, is metis still pointed at the right things, health of my second brain, check my interests, are my feeds working, what has metis learned, monthly review, is my news still relevant, drift check, tune metis"
---

# Metis Review — is your second brain still pointed at the right things?

A periodic tuning pass. Not a health check of whether Metis *works* (that is
`/metis-doctor`) — this asks whether it is still aimed at what the researcher actually cares
about now. Both drift silently, and silent drift is the failure mode: nothing
breaks, the briefings just quietly get less useful.

**Run monthly, or whenever a briefing has felt off for a while.**

---

## Why each check exists

Every item here was a real failure found on 2026-08-19, not a hypothetical:

| Check | The failure it catches |
|---|---|
| Feed health | **24 of 52 feeds were dead**, some for years. `feedparser` returns zero entries rather than raising on a 404, so a dead source is indistinguishable from a quiet news day. |
| Scan recency | A **five-week gap** (13 Jul → 18 Aug) because news only scans while the dashboard runs. |
| Interest coverage | **59% of news items matched no subject**, so most of the feed could not be grouped or filtered. |
| Undeclared interests | Recurring subjects in the researcher's own work that were never declared. |
| Briefing rotation | Whether cooldowns are actually engaging, or every brief still leads with the same story. |
| Learned lessons | Whether corrections the researcher made are on record, or were only remembered as having happened. |

---

## Step 1 — Run the checks

In parallel where possible:

- `check_news_feeds(kind="news")` and `check_news_feeds(kind="paper")` — which sources
  are alive. **Sequential and spaced internally**, so it takes a minute; do not
  parallelise it further or publishers rate-limit and healthy feeds report as 403.
- `get_briefing_coverage(days=14)` — which story threads led, which are held back,
  which angles are spent.
- `get_missed_news(days=14)` — stories that never reached a briefing he read.
- `suggest_interests_from_work()` — subjects recurring in his work but undeclared.
- `get_user_profile()` — the two declared lists, and `has_declared_*` flags.
- `get_persona_learnings()` — what Metis has learned about how to behave.
- `get_continuity_context(topic="metis review")` — when this was last done.

Also check **scan recency** directly: if the newest news item is more than a few
days old, the scanner has not been running, and every other finding here is
distorted by that. Say so first — a review of a stale corpus is a review of nothing.

---

## Step 2 — Report

Follow `metis-response-contract.md`. Lead with the one thing that matters most, then:

```
FEEDS      N/M working  · <the dead ones, named>
LAST SCAN  <date> — <"current" | "N days stale, nothing has been collected">
COVERAGE   <N> threads · <N> held back · <N> never delivered
INTERESTS  news: <N> · library: <N> · <N> suggested from your work
LEARNED    <N> lessons on record · <newest>
```

Then, only where there is something to act on:

- 🟡 **Needs your call** — a dead feed needing a replacement URL, or suggested
  interests to accept or reject. **One 🟡 at a time**; if several things need
  deciding, name the most consequential and hold the rest.
- 🟢 **Fine** — say plainly what is healthy. A review that only lists problems
  reads as alarming when the system is mostly working.
- ⚠ **Caveat** — anything unverifiable, e.g. relevance scoring being degraded
  because the embedding model is unavailable.

---

## Step 3 — Act, but only where it is safe to

**Do without asking** (reversible, and inaction is the worse outcome):
- Run `scan_news_feeds()` / `scan_library_feeds()` if the corpus is stale.
- Record any lesson the researcher confirms during the review with `record_persona_learning()`.

**Ask first** (changes what Metis pays attention to):
- Adding suggested interests — `suggest_interests_from_work(apply=True)` writes to
  the **library** list only. News interests must be asked about separately; what
  someone wants to hear about is often outside their work and cannot be mined
  from it.
- Removing or replacing a feed URL.
- Anything that would drop existing declared interests.

---

## Step 4 — Record

- `save_session_summary()` with what was found and changed.
- `update_project_memory(project_id="metis-dashboard", ...)` if anything was changed.
- Note the date so the next review can say how long it has been.

---

## Judgement notes

- **A small true number beats a large false one.** If a count looks implausibly
  large, it is probably matching noise — say so rather than reporting it.
- **Do not manufacture work.** If feeds are healthy, interests are current and
  rotation is working, the correct output is three lines saying so. A review that
  invents findings to look thorough trains the researcher to stop running it.
- **Suggested interests are proposals.** the researcher's own words: people find it hard to
  articulate interests, which is why they are mined — but mined terms are evidence,
  not conclusions. Show what supports each one.
