# Session Log — 2026-03-28

## Summary

v5.0 was implemented in a single session. Four modules were added or substantially rewritten: News (complete rewrite), Learning (new), Finance (new), and Meetings (major expansion). The database grew from 13 tables to 23 tables via 10 new tables and multiple ALTER TABLE additions to existing tables. Three new agent directories were created (learning-coach, career-coach, personal-finance). The CLAUDE.md agent routing table was updated to reflect the three new agents. All 14 R modules pass syntax check with 0 parse errors. The version label for this release is v5.0.

---

## Changes Made

| File | Type | Description |
|------|------|-------------|
| R/mod_news.R | REWRITE | Complete rewrite — multi-domain daily intelligence briefing with top signals, domain synthesis grid, surprise items, finance sub-section, full timeline, collapsible add-brief form, domain filter chips |
| R/mod_learning.R | ADDED | New competency tracker module — 8 seeded competencies, auto-leveling, activity logger, SR integration, learning path view, MLM Course integration |
| R/mod_finance.R | ADDED | New financial awareness module — short-term headlines, long-term trends with arrows, snapshot capture form, watchlist, project connections panel |
| R/mod_meetings.R | MODIFIED | Major expansion — pre-meeting briefing generator, meeting intelligence panel (decisions/actions/follow-ups), person directory, meeting timeline with type badges, attendee tracking, meeting type selector |
| R/data_store.R | MODIFIED | 10 new tables, 2 altered tables (news_briefs and meetings), 2 new indexes, 20+ new CRUD functions |
| app.R | MODIFIED | Added nav_panel("Learning") to main nav, nav_panel("Finance") under "More", learning_server and finance_server calls |
| www/styles.css | MODIFIED | ~300 new lines — News, Meetings, Learning, and Finance CSS classes |
| 02_agents/CLAUDE.md | MODIFIED | 3 new agent invocations added: /learning-coach, /career-coach, /personal-finance |
| 02_agents/learning-coach/ | ADDED | New agent directory — system-prompt.md, contract.md, README.md |
| 02_agents/career-coach/ | ADDED | New agent directory — system-prompt.md, contract.md, README.md |
| 02_agents/personal-finance/ | ADDED | New agent directory — system-prompt.md, contract.md, README.md |

---

## Database Changes Detail

### New tables (10)
| Table | Purpose |
|-------|---------|
| news_topics | Controlled vocabulary for news domain tagging |
| news_brief_topics | Many-to-many join: news_briefs <-> news_topics |
| meeting_persons | Person directory — name, role, affiliation |
| meeting_attendance | Many-to-many join: meetings <-> meeting_persons |
| learning_competencies | Tracked skill areas with current level and activity count |
| learning_activities | Log of each learning event (course_lesson, paper_read, exercise, sr_review, tutorial, practice) |
| learning_resources | Linked resources per competency (URL, title, type) |
| finance_watchlist | Tracked financial assets or themes |
| finance_snapshots | Point-in-time market/trend captures with category, label, headline, trend, project link |
| (course_progress) | Note: this table was added at v4.0, not v5.0 — listed here for completeness |

### ALTER TABLE additions
| Table | New columns |
|-------|------------|
| news_briefs | source_url TEXT, tags TEXT, surprise_flag INTEGER (0/1) |
| meetings | attendees TEXT, meeting_type TEXT, decisions TEXT, action_items TEXT, follow_ups TEXT, linked_meetings TEXT, pre_briefing_path TEXT |

### New indexes
- idx_briefs_date on news_briefs(date)
- idx_briefs_domain on news_briefs(domain)

---

## Decisions Made

- Decision: Auto-leveling competencies by activity count (5 activities -> intermediate, 15 -> advanced) rather than requiring manual level assignment.
  Rationale: Reduces friction — the user logs activities and the level emerges automatically. Avoids subjective self-rating at entry time. Thresholds can be adjusted per competency in a future pass.
  Alternatives considered: Manual level selector (rejected — requires conscious judgment each time, likely to be neglected); external assessment integration (overkill at this stage).

- Decision: Finance tab placed under "More" nav menu alongside Search, Graph, and Agents.
  Rationale: Finance is accessed on-demand rather than as part of the daily loop. Keeping the primary nav to the core daily tabs (Control Room, Projects, Library, PhD, Meetings, News, Ideas) maintains scan speed for daily use. See ADR-006 (established principle).
  Alternatives considered: Top-level tab (rejected — primary nav already wide at 7 items).

- Decision: Meeting persons stored in a normalized person directory table (meeting_persons) with a join table (meeting_attendance), rather than as a free-text column.
  Rationale: Enables tracking meeting count and last-meeting date per person, powers the person directory view, and allows future meeting-to-person analytics. The v4.0 free-text `attendees` column is retained for backward compatibility and as a quick-entry fallback.
  Alternatives considered: Free-text attendees field only (retained as fallback but insufficient for person analytics), JSON blob in a single column (queryable only with JSON functions, harder to aggregate).

- Decision: Three specialized agents created (learning-coach, career-coach, personal-finance) rather than expanding existing agents.
  Rationale: Each domain has a meaningfully different task profile and tone. The learning-coach is pedagogical (skill progression, spaced repetition, curriculum), the career-coach is strategic and aspirational (EU job market, CV positioning), and the personal-finance agent is informational and domain-scoped. Mixing these into an existing agent (e.g., methods-coach for learning) would dilute both agents. 11 -> 14 agents.
  Alternatives considered: Extend methods-coach with learning-coach duties (rejected — career and finance are out of scope for a methods-focused agent); a single "life management" agent (rejected — too broad to give focused guidance in any domain).

---

## Issues Encountered

- Issue: The meetings table already had an `attendees TEXT` column as a free-text field from earlier versions. The v5.0 expansion adds the normalized meeting_persons / meeting_attendance tables alongside it.
  Resolution: Both coexist. Free-text attendees is retained for backward compatibility. The person directory uses the normalized tables. No data migration required — existing meeting records simply have empty attendance join records.

- Issue: news_briefs schema needed extension (source_url, tags, surprise_flag) without breaking existing brief records.
  Resolution: ALTER TABLE with default values — surprise_flag defaults to 0, source_url and tags default to NULL. Existing records unaffected.

---

## Data Rules Validated

- [x] CATT and RDT calculated separately (not applicable — no HAT data in this module)
- [x] Year boundaries respected (not applicable — no HAT pipeline data)
- [x] PS_Cases checked before test-based classification (not applicable)
- [x] Positivity only from active screening (not applicable)
- [x] HAT case records classified as SENSITIVE — finance/learning/news modules do not touch patient-level data

---

## Research Documented

Tool evaluations conducted during this session:
- **NotebookLM** (Google): source-grounded AI synthesis, mind map export, audio overview generation — recommended for literature synthesis and podcast-style briefings
- **Granola**: no-bot meeting transcription via system audio capture, AI-enhanced structured notes, meeting templates — evaluated for KI-001 (Whisper alternative)
- **PKM tools surveyed**: Obsidian (graph view, plugin ecosystem), Tana (supertags, structured data), Mem.ai (semantic search), Logseq (daily notes, open-source), Roam Research (backlinks, block references)

---

## Next Steps

- [ ] Validate finance_snapshots capture form end-to-end in the running app
- [ ] Test learning activity logger and confirm auto-level advancement triggers
- [ ] Test pre-meeting briefing generator with a real meeting record
- [ ] Consider Granola as a resolution path for KI-001 (Whisper not installed)
- [ ] Seed initial finance watchlist entries to populate the Finance tab
- [ ] Seed learning competency baseline levels based on current skill self-assessment
- [ ] Update security policy (02_agents/metis/security-policy.md) to include the 3 new agents in the per-agent security table
