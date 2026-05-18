# Version 6.0 — 2026-03-28

## Overview

**Theme: Agents, News Data, UX Fix, Epidemiologist**

Four parallel work streams in one session. The agent ecosystem grows from 15 to 18 with three new specialists occupying previously uncovered roles: automated news aggregation (with unique internet permission), design system enforcement, and epidemiological peer review. News feed coverage scales from 3 sources to 17 across all 8 tracked domains. A viewport scrolling bug that silently clipped content on the News and Library tabs is fixed at the root level in app.R. CSS gains its first formal accessibility and mobile pass.

## New Features

- **Agent: news-aggregator** — automated RSS feed collection and curation across all 8 domains; the only agent in the ecosystem with explicit internet access permission (ADR-017)
  Files affected: agents/news-aggregator/ (3 files), agents/metis/security-policy.md, R/mod_agents.R, R/mod_projects.R, R/data_store.R, CLAUDE.md

- **Agent: ux-engineer** — design system and UI/UX specialist; encodes hard rules (no emoji icons as nav elements, WCAG AA contrast minimums, responsive breakpoints) to enforce design consistency across all future dashboard work
  Files affected: agents/ux-engineer/ (3 files), R/mod_agents.R, R/mod_projects.R, R/data_store.R, CLAUDE.md

- **Agent: epidemiologist** — senior specialist reviewer with a Socratic questioning persona; HAT/NTD field expertise; intended for study design critique, methodology challenge, and surveillance gap identification during PhD work
  Files affected: agents/epidemiologist/ (3 files), R/mod_agents.R, R/mod_projects.R, R/data_store.R, CLAUDE.md

- **News feed expansion** — 14 new RSS feed URLs added to `inst/scripts/fetch_news_feeds.R`; all 8 tracked domains now have at least one feed source; full feed list: WHO NTD, DNDi, Anthropic, MIT Tech Review, Nature, Reuters, BBC, The Conversation, ReliefWeb, MSF, CNBC, Bloomberg, NPR, The Guardian
  Files affected: inst/scripts/fetch_news_feeds.R

- **CSS: accessibility and mobile** — first formal accessibility pass on `www/styles.css`: `min-height: 100vh` prevents layout collapse on short pages; button hover transitions (150ms) give click feedback; `cursor: pointer` on all interactive elements; `@media (prefers-reduced-motion)` removes transitions for users who need it; mobile breakpoints at 768px produce stacked grids, columnar kanban, and 2-column KPI strip on small screens
  Files affected: www/styles.css

## Bug Fixes

- **Viewport-constrained scrolling** (app.R): `fillable = FALSE` added to `page_navbar()`
  Root cause: `bslib::page_navbar()` defaults to `fillable = TRUE`, which constrains every panel to the viewport height. Content below the fold was silently inaccessible — no scroll indicator, no error, content simply absent.
  Impact: News timeline and Library article grids were the most affected; any content past approximately 900px of page height was unreachable.
  Fix: Single-line change in app.R. All panels now scroll as standard document pages. See ADR-016.

## Breaking Changes

None.

## Security and Policy Updates

- **Security policy** (agents/metis/security-policy.md): per-agent security table updated with entries for all 6 agents that were missing (3 from v5.0: learning-coach, career-coach, personal-finance; 3 from v6.0: news-aggregator, ux-engineer, epidemiologist)
- **news-aggregator internet exception** recorded as ADR-017 — only agent in the ecosystem with an explicit internet access grant
- KI-007 (v5.0 agents missing from security table) resolved — see KI-R04

## Known Limitations

- KI-010: 17 news feed URLs have not been validated against live internet sources — automated ingestion is still not confirmed working
- KI-008: pre-meeting briefing generation still requires manual agent invocation (no in-app end-to-end trigger)
- KI-009: competency auto-leveling thresholds not yet tuned per competency

## Upgrade Notes

No schema migrations required. No new R packages added.

Recommended steps after deploying v6.0:
1. Restart the dashboard to pick up the `fillable = FALSE` fix in app.R
2. Validate news feeds: run `inst/scripts/fetch_news_feeds.R` with internet access to confirm all 17 feed URLs return content
3. Verify new agents appear correctly in the Agents tab (mod_agents.R reads from filesystem — the 9 new files should appear automatically)
