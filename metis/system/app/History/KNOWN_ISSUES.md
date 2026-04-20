# Metis Dashboard — Known Issues

---

## Open

### KI-010: 17 news feed URLs not yet validated against live sources
**Status**: Open — deferred
**Severity**: Low
**First noted**: v6.0 (2026-03-28)
**Description**: `inst/scripts/fetch_news_feeds.R` now contains 17 feed URLs across 8 domains. The URLs were added based on publicly known RSS endpoints for each source (WHO NTD, DNDi, Anthropic, MIT Tech Review, Nature, Reuters, BBC, The Conversation, ReliefWeb, MSF, CNBC, Bloomberg, NPR, The Guardian). None have been tested against live internet to confirm the RSS URLs are valid, accessible, and return parseable feed content.
**Impact**: Automated news ingestion will not flow until feeds are validated. Manual brief capture still works.
**Next step**: Run `inst/scripts/fetch_news_feeds.R` with approved internet access (news-aggregator agent scope). Confirm each feed parses correctly and returns expected content. Replace or remove any dead URLs. Note: this supersedes KI-002 (which tracked the same problem when only 3 feeds existed).
**Supersedes**: KI-002

### KI-008: Pre-meeting briefing generation not fully automated
**Status**: Open — accepted limitation
**Severity**: Low
**First noted**: v5.0 (2026-03-28)
**Description**: The mod_meetings.R pre-meeting briefing panel stores a `pre_briefing_path` value in the meetings table, pointing to where a brief should or will be saved. The actual brief generation (pulling past meeting context, linked library articles, and synthesizing a structured preparation document) requires the meeting-memory agent to be invoked manually. There is no in-app button that triggers briefing generation end-to-end.
**Impact**: Low — the user must invoke the meeting-memory agent externally, copy the output to the expected path, and the app will then surface it. This is consistent with the worker-script pattern (ADR-005). However, users may expect the [Generate Brief] button to produce the brief immediately.
**Next step**: Consider adding a `system2()` call or a modal with copy-to-clipboard agent invocation command (following the pattern of the [Invoke] button in mod_projects.R) to make the handoff explicit.

### KI-009: Activity auto-leveling thresholds not yet tuned per competency
**Status**: Open — accepted at launch
**Severity**: Low
**First noted**: v5.0 (2026-03-28)
**Description**: The auto-leveling thresholds (5 activities = intermediate, 15 = advanced) are uniform across all 8 competencies. In practice, some competencies (e.g., Bayesian analysis) may require more investment before an intermediate label is appropriate, while others (e.g., outbreak investigation, where the user has field experience) may warrant a head-start.
**Impact**: Low — the competency level is a personal tracking tool, not an external credential. The primary value is the progression signal, not the exact label.
**Next step**: After ~2 months of active use, review whether the thresholds match felt competency. Add per-competency threshold overrides to the `seed_default_competencies` function if needed.

### KI-004: lessons.json format not yet documented
**Status**: Open — deferred
**Severity**: Low
**First noted**: v4.0 (2026-03-27)
**Description**: The Courses section reads lesson structure from `lessons.json` in each education project's local path. The required JSON schema (fields, lesson ID format) has not been formally documented. Any course added without a valid `lessons.json` will silently fall back to showing the course card with no lesson detail.
**Impact**: Low — fallback is graceful. A course maintainer adding a new course without guidance may produce a mismatched file structure and see no lessons.
**Next step**: Add `lessons.json` schema documentation to `02_agents/software-engineer/` or a `docs/` folder.

### KI-005: Orphaned course_progress records if lesson IDs change
**Status**: Open — accepted risk
**Severity**: Low
**First noted**: v4.0 (2026-03-27)
**Description**: Completion records in the `course_progress` table reference lessons by ID from `lessons.json`. If a course is restructured and lesson IDs change, existing completion records become orphaned and completion state is lost.
**Impact**: Low — affects learning tracking only; no data loss to primary knowledge management functions.
**Next step**: Consider a migration helper or ID stability convention in the `lessons.json` schema when KI-004 is resolved.

### KI-001: Local Whisper installation incomplete
**Status**: Open — deferred
**Severity**: Medium
**First noted**: v1.0 (2026-03-26)
**Description**: The `transcribe_meeting.R` worker script exists and is wired into the Meetings tab import flow, but the local Whisper engine has not been successfully installed. The meeting transcription path currently stops at `pending_whisper_install`.
**Impact**: Automatic audio-to-transcript conversion does not work. Manual transcript import still works.
**Next step**: Inspect `.venv` in the dashboard folder. Decide whether to continue with `openai-whisper` or switch to a lighter CPU-friendly transcription stack.
**Root cause**: Python environment setup for Whisper was not completed before the session ended.

### KI-002: News feed ingestion not validated against live sources
**Status**: Open — deferred
**Severity**: Low
**First noted**: v1.0 (2026-03-26)
**Description**: `inst/scripts/fetch_news_feeds.R` exists and the News page stores briefs manually. Automated feed ingestion has not been tested against live internet sources.
**Impact**: News Radar automated briefs are not flowing into the dashboard automatically.
**Next step**: Verify `fetch_news_feeds.R` with approved live internet access.

### KI-003: PhD evidence-map editing not implemented
**Status**: Partially resolved in v3.0 — milestone timeline added; full evidence-map table still pending
**Severity**: Low
**First noted**: v1.0 (2026-03-26)
**Updated**: v3.0 (2026-03-27) — `phd_milestones` table and CSS timeline UI added to PhD tab. Article-level evidence-map table with filters is not yet implemented.
**Updated**: v4.0 (2026-03-27) — no further progress this version. Still pending.
**Impact**: PhD milestone tracking now works inside the app. Article-level evidence mapping still requires external tools.
**Next step**: Add PhD evidence-map table view and page-level filters in a future pass.

### KI-006: Security policy excerpts in agent system prompts require manual sync when master policy changes
**Status**: Open — accepted risk
**Severity**: Low
**First noted**: 2026-03-27 (agent audit session)
**Description**: The master security policy lives at `02_agents/metis/security-policy.md`. Four agent system prompts (dashboard-engineer, meeting-memory, librarian, news-radar) contain relevant excerpts. If the master policy is updated, those excerpts must be manually reviewed and updated. There is no automated sync or validation step.
**Impact**: Low in normal usage — the policy is expected to be stable. Risk increases if the agent count grows significantly or if a policy update is applied to the master but not propagated to the excerpts.
**Next step**: Consider adding a "policy version" comment at the top of each agent system prompt excerpt so a diff between the excerpt date and the master policy date signals a review is needed.

---

## Resolved

### KI-R03: Viewport-constrained scrolling on News and Library tabs
**Status**: Resolved in v6.0 (2026-03-28)
**Severity**: Medium
**Root cause**: `bslib::page_navbar()` defaults to `fillable = TRUE`, which constrains all panels to the viewport height and suppresses document-level scrolling. Content below the fold was silently inaccessible.
**Fix**: `fillable = FALSE` added to `page_navbar()` call in `app.R`. Panels now determine their own height and scroll naturally.
**Files changed**: app.R
**Decision recorded**: ADR-016

### KI-R04: v5.0 agents (learning-coach, career-coach, personal-finance) missing from security policy table
**Status**: Resolved in v6.0 (2026-03-28)
**Severity**: Low (was KI-007)
**Root cause**: Agents were created without a corresponding row being added to the per-agent security table in `02_agents/metis/security-policy.md`.
**Fix**: All three v5.0 agents plus all three v6.0 agents (news-aggregator, ux-engineer, epidemiologist) added to the per-agent security table in v6.0. news-aggregator granted internet access; all others assigned appropriate INTERNAL or PUBLIC tiers without internet.
**Files changed**: 02_agents/metis/security-policy.md

### KI-R02: News feed ingestion not validated against live sources (superseded)
**Status**: Superseded by KI-010 (v6.0, 2026-03-28)
**Note**: The feed list has grown from 3 to 17 URLs. Validation is still pending. Tracking moved to KI-010 to reflect the expanded scope.

### KI-R01: Value boxes causing persistent vertical scroll
**Status**: Resolved in v2.0 (2026-03-27)
**Severity**: High
**Root cause**: Default shinydashboard `.small-box` height (~10rem) caused every page to overflow vertically even with only a few value boxes in a row.
**Fix**: Constrained `.small-box` to 5.5rem height in `www/styles.css`. Reduced internal padding proportionally.
**Files changed**: www/styles.css

### KI-R02: Meeting tab showing raw strings "AUD", "TXT", "PREP" instead of icons
**Status**: Resolved in v2.0 (2026-03-27)
**Severity**: Medium
**Root cause**: `shinydashboard::valueBox()` `icon` parameter received string literals ("AUD") instead of `icon()` function calls.
**Fix**: Replaced all three string literals with proper `icon("microphone")`, `icon("file-text")`, `icon("tasks")` calls.
**Files changed**: R/mod_meetings.R
