# Version 5.0 — 2026-03-28

## Overview

**Theme: Intelligence Layer — News Synthesis, Meeting Intelligence, Learning, Finance**

v5.0 is the largest single-session expansion of the Metis Dashboard to date. Four modules were added or substantially rewritten, the database grew by 10 tables and 10 new columns across 2 existing tables, three new agents joined the ecosystem, and the CSS layer grew by ~300 lines. The version's unifying theme is intelligence: the app now actively synthesizes information across domains (news), tracks competency growth over time (learning), surfaces financial awareness (finance), and generates context-aware meeting briefings (meetings). Where v4.0 connected the dashboard to the agent ecosystem, v5.0 deepens the content each panel can hold and reason about.

---

## New Features

### mod_news.R — Complete Rewrite
The News tab was rebuilt from scratch as a multi-domain daily intelligence briefing system.

- **Top signals section**: high-priority items surfaced across all domains in a scannable card grid
- **Domain synthesis grid**: seven tracked domains — geopolitics, science, academia, sleeping sickness, humanitarian, markets, AI — each rendered as a summary card with latest briefs
- **"Surprise me" section**: items flagged outside the user's usual domains, for serendipitous discovery
- **Finance sub-section**: short-term market headlines and long-term trend views embedded within the News tab (mirrored from mod_finance.R)
- **Full timeline**: chronological log of all briefs with domain color coding for at-a-glance orientation
- **Collapsible add-brief form**: captures title, domain, signal strength, source URL, tags, and surprise flag
- **Domain filter chips**: single-domain focus mode — click a chip to filter the entire view to one domain

Files affected: R/mod_news.R, R/data_store.R (new CRUD functions), www/styles.css

### mod_learning.R — New Module
Statistics and epidemiology competency tracker.

- **8 seeded competencies**: sampling methods, multilevel modelling (MLM), spatial statistics, outbreak investigation, diagnostic test evaluation, survival analysis, Bayesian analysis, generalised estimating equations (GEE)
- **Auto-leveling**: activity count drives level progression — 0-4 activities = beginner, 5-14 = intermediate, 15+ = advanced. No manual level assignment required.
- **Activity logger**: log type (course_lesson, paper_read, exercise, sr_review, tutorial, practice), competency, and notes per session
- **SR integration**: learning-specific spaced repetition items surfaced within the Learning tab
- **Learning path view**: linked resources per competency (papers, courses, tutorials)
- **MLM Course integration**: the MLM Course project (education domain) connects to the MLM competency

Files affected: R/mod_learning.R (new), R/data_store.R, app.R (new nav_panel + server call), www/styles.css

### mod_finance.R — New Module
Financial awareness tab for market orientation and trend tracking.

- **Short-term headlines**: today's market-relevant news from domain='markets' news briefs
- **Long-term trends**: grouped by label with directional trend arrows (up, down, sideways)
- **Snapshot capture form**: category (macro, sector, asset, theme), label, headline, trend, optional project link
- **Watchlist management**: tracked assets or themes with add/remove interface
- **Project connections panel**: finance snapshots that are linked to active projects

Files affected: R/mod_finance.R (new), R/data_store.R, app.R (nav_panel under "More" + server call), www/styles.css

### mod_meetings.R — Major Expansion
The Meetings module was substantially extended with intelligence generation and person tracking.

- **Pre-meeting briefing generator**: pulls context from past meetings (same person or project) and linked library articles to produce a structured preparation brief; brief path stored in meetings.pre_briefing_path
- **Meeting intelligence panel**: structured capture of decisions made, action items, and follow-ups per meeting; stored in dedicated columns on the meetings table
- **Person directory**: add people by name, role, and affiliation; track total meeting count and last-meeting date automatically from the meeting_attendance join table
- **Meeting timeline with type badges**: color-coded badges per meeting type (general, project_review, phd_supervision, strategy, seminar, one_on_one)
- **Attendee tracking**: comma-separated entry parses into individual person records in meeting_attendance
- **Decision/action indicators**: timeline cards show a badge count for how many decisions and actions were captured per meeting

Files affected: R/mod_meetings.R, R/data_store.R (new tables + ALTER TABLE), www/styles.css

---

## New Agents (3)

| Agent slug | Purpose | Key capabilities |
|------------|---------|-----------------|
| learning-coach | Skill progression, learning paths, statistics focus | Competency gap analysis, resource recommendations, spaced repetition curation, MLM course guidance |
| career-coach | EU academic/research job preparation | CV support, interview prep, job market orientation, application strategy |
| personal-finance | Market awareness, financial trend tracking | Short-term market headlines, long-term thematic trends, financial literacy nudges |

Agent invocations added to CLAUDE.md: `/learning-coach`, `/career-coach`, `/personal-finance`

Agent count: 11 (v4.0) -> 14 (v5.0)

---

## Database Changes

### New tables (10)
| Table | Description |
|-------|------------|
| news_topics | Controlled vocabulary for news domains |
| news_brief_topics | Many-to-many: news_briefs <-> news_topics |
| meeting_persons | Person directory |
| meeting_attendance | Many-to-many: meetings <-> meeting_persons |
| learning_competencies | Tracked skill areas with level and activity count |
| learning_activities | Per-event activity log |
| learning_resources | Resources linked to competencies |
| finance_watchlist | Tracked assets and themes |
| finance_snapshots | Point-in-time market/trend captures |

Total tables: 13 (v4.0) -> 23 (v5.0)

### ALTER TABLE
| Table | New columns |
|-------|------------|
| news_briefs | source_url TEXT, tags TEXT, surprise_flag INTEGER |
| meetings | attendees TEXT, meeting_type TEXT, decisions TEXT, action_items TEXT, follow_ups TEXT, linked_meetings TEXT, pre_briefing_path TEXT |

### New indexes
- idx_briefs_date
- idx_briefs_domain

### New CRUD functions (20+)
news_domain_summary, news_by_domain, news_surprise_items, news_top_signals, insert_news_brief_v5, insert_meeting_person, get_meeting_persons, get_meeting_context, update_meeting_intelligence, seed_default_competencies, get_competencies, insert_learning_activity, get_learning_activities, insert_finance_snapshot, get_finance_today, get_finance_trends, insert_finance_watchlist, get_finance_watchlist

---

## CSS Additions (~300 lines)

| Domain | New classes |
|--------|------------|
| News | .news-header-row, .news-domain-chip, .news-top-signals-grid, .news-signal-card, .news-domain-grid, .news-domain-card, .news-surprise-*, .news-timeline-*, .signal-dot-*, .finance-list |
| Meetings | .meeting-person-chip, .meeting-timeline-*, .meeting-type-badge, .meeting-badge-* |
| Learning | .competency-grid, .competency-card, .competency-level-badge, .competency-bar-*, .learning-activity-*, .learning-path-* |
| Finance | .finance-card, .finance-category-badge, .finance-trend-*, .finance-list-stack |

---

## Breaking Changes

None. All schema changes used ALTER TABLE with safe defaults (NULL or 0). Existing rows in news_briefs and meetings are unaffected. The meeting_persons / meeting_attendance tables coexist with the legacy free-text attendees column — no migration required.

---

## Known Limitations

- Pre-meeting briefing generator produces a path reference (pre_briefing_path) but the actual brief generation logic depends on the meeting-memory agent; full automation is not yet wired end-to-end.
- The 3 new agents (learning-coach, career-coach, personal-finance) are not yet in the per-agent security table in 02_agents/metis/security-policy.md — this must be updated manually.
- Finance tab is informational only at this stage — no live data feed integration. All snapshots are manually entered.
- KI-001 (Whisper not installed) remains open; Granola was evaluated as a potential alternative during this session.

---

## Verification

- 14 R modules, 0 parse errors
- 23 SQLite tables after schema migration
- 3 agent directories confirmed created with system-prompt.md, contract.md, README.md

---

## Upgrade Notes

No action required beyond the normal schema migration run (data_store.R initialises new tables on first load). If upgrading from v4.0 with an existing metis.sqlite, the ALTER TABLE statements will add new columns on startup. No data will be lost. Cache rebuild is not applicable (SQLite, not RDS cache).
