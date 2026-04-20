# Metis PKM — Implementation Plan v7+

**Last updated:** 2026-03-29 (continuation)
**Handoff document:** `01_control-room/handoff-instructions.md` — detailed instructions for any AI to continue
**Status:** Active — pick up from where we left off

---

## Completed (v6-v7)

- [x] Dashboard v6: scrolling fix, 3 new agents (news-aggregator, ux-engineer, epidemiologist), 17 RSS feeds, CSS mobile breakpoints
- [x] Metis routing protocol: 5-step routing, complexity model, recording convention
- [x] Agent invoke templates in dashboard Agents tab (copy-to-clipboard)
- [x] `agent_runs` DB table + `log_agent_run()` function
- [x] Review output directories created for all 17 agents
- [x] Interactive script fix (common.R + all inst/scripts handle both Rscript and interactive R)
- [x] Rename Metis → Metis across all files (CLAUDE.md, agent prompts, R dashboard, CSS)
- [x] Rewrite Metis identity: Senior Researcher / Epidemiologist / Public Health Methodologist
- [x] MCP server built (08_system/mcp-server/, 9 tools, not yet installed/tested)
- [x] Global ~/.claude/CLAUDE.md for Metis access from any folder
- [x] Personal Finance agent archived to 09_archive/
- [x] 13 knowledge reference cards in 06_library/ (methods, concepts, disease-areas, institutions)
- [x] Agent smoke test on HAT Dashboard (10-agent chain review)

---

## In Progress / Next Up

### Priority 1: Crucible (file intake + analysis)
**Status:** DONE (2026-03-29)

The Crucible is a new dashboard tab where you drop any file and Metis analyzes, links, and integrates it into the PKM.

**What it does:**
1. Upload or specify a file (PDF, CSV, TXT, DOCX, markdown)
2. Dashboard asks: analysis type, project link, PhD article link, depth, focus
3. Metis routes to appropriate agent(s) for analysis
4. Structured output written to 07_outputs/reviews/
5. Metadata added to library if it's a paper
6. Ideas extracted → Ideas table
7. Tasks created if action items found

**Files to create/modify:**
- [x] `R/mod_crucible.R` — new module (UI + server)
- [x] `app.R` — add Crucible tab + server call
- [x] `R/data_store.R` — add `crucible_intake` table + `talks` table
- [x] `www/styles.css` — Crucible-specific styles

**DB schema:**
```sql
CREATE TABLE IF NOT EXISTS crucible_intake (
  intake_id TEXT PRIMARY KEY,
  filename TEXT,
  file_type TEXT,          -- pdf, csv, txt, docx, md
  analysis_type TEXT,      -- literature, data, meeting, talk, custom
  project_link TEXT,
  phd_article_link TEXT,
  analysis_depth TEXT,     -- quick, standard, deep
  focus TEXT,              -- methods, results, discussion, all
  status TEXT,             -- pending, analyzing, complete
  output_path TEXT,
  ideas_extracted INTEGER DEFAULT 0,
  tasks_created INTEGER DEFAULT 0,
  created_at TEXT
)
```

---

### Priority 2: News feeds restructured (3 tiers)
**Status:** DONE (2026-03-29)

Expand fetch_news_feeds.R from 17 to ~25 feeds organized in 3 tiers.

**Tier 1 — World context (weekly scan):**
- [ ] The Guardian World (exists)
- [ ] The Economist (needs RSS URL research — may be partial/paywalled)
- [ ] De Standaard (`standaard.be/rss/section/...` — need exact section IDs)
- [ ] Al Jazeera (`aljazeera.com/xml/rss/all.xml`)
- [ ] BBC World (exists)

**Tier 2 — Research & science (daily scan):**
- [ ] Nature (exists)
- [ ] The Lancet (`thelancet.com/rssfeed/lancet_current.xml`)
- [ ] PLOS NTDs (`journals.plos.org/plosntds/feed/atom`)
- [ ] BMJ (`bmj.com/rss`)
- [ ] Eurosurveillance (`eurosurveillance.org/rss` — need to verify)
- [ ] Science (exists)
- [ ] MIT Tech Review (exists)
- [ ] TMIH (need RSS URL)

**Tier 3 — Epi intelligence (real-time):**
- [ ] WHO Disease Outbreak News (`who.int/feeds/entity/don/en/rss.xml`)
- [ ] CDC MMWR (`cdc.gov/mmwr/rss/mmwrweekly.xml`)
- [ ] ReliefWeb (exists)
- [ ] WHO Weekly Epi Record (need RSS URL)
- [ ] DNDi (exists)
- [ ] HealthMap (check if RSS still active)
- [ ] ProMED — RSS killed in 2023, now paid API via samdesk. Alternative: email digest parsing or HealthMap aggregation.

**Questions to ask user:**
- [ ] Do you have access to The Economist digital? (paywall affects RSS)
- [ ] Which De Standaard sections? Binnenland, Buitenland, Wetenschap?
- [ ] Do you want French-language Belgian news too? (Le Soir, La Libre)
- [ ] Any specific PubMed saved searches beyond the existing HAT one?
- [ ] Do you want podcast RSS feeds? (Lancet Voice, BMJ Talk, TWiV)
- [ ] Budget for ProMED samdesk API? Or use free alternatives?

---

### Priority 3: Learning competency domains
**Status:** DONE (2026-03-29)

Seed 12 competency domains in the Learning tab based on ECDC/CDC/FETP/COHFE frameworks.

**Domains to seed:**
- [ ] Epidemiological methods (study design, bias, measures)
- [ ] Biostatistics (regression, MLM, survival, Bayesian)
- [ ] Spatial epidemiology (SaTScan, GIS, mapping)
- [ ] Surveillance systems (design, evaluation, digital)
- [ ] Outbreak investigation (CDC 10-step, rapid assessment)
- [ ] Sampling strategies (probability, LQAS, cluster surveys)
- [ ] Data management (FAIR, reproducibility, R workflows)
- [ ] Diagnostic evaluation (test accuracy, STARD, low-prevalence)
- [ ] Scientific communication (EQUATOR, writing, peer review)
- [ ] Research ethics (Helsinki, IRB, community engagement)
- [ ] Health economics (CEA, DALY, costing)
- [ ] Leadership & management (project mgmt, stakeholder engagement)

**Files to modify:**
- [ ] `R/data_store.R` — seed competencies in `seed_default_data()`
- [ ] `R/mod_learning.R` — link competencies to library cards
- [ ] Link each domain to specific resources (textbooks, courses, library cards)

**Questions to ask user:**
- [ ] What's your current level in each domain? (for initial assessment)
- [ ] Which online courses are you taking or planning? (Coursera, edX, LSHTM short courses?)
- [ ] Do you want the MLM course competencies mapped into this framework?

---

### Priority 4: Library cards (additional)
**Status:** DONE (2026-03-29) — all 25 cards created

8 more methods cards + 4 concepts cards to create in 06_library/.

**Methods:**
- [ ] `methods/sampling-strategies.md`
- [ ] `methods/diagnostic-test-evaluation.md`
- [ ] `methods/outbreak-investigation.md`
- [ ] `methods/mixed-methods-research.md`
- [ ] `methods/health-economics-basics.md`
- [ ] `methods/data-management.md`
- [ ] `methods/gis-for-epidemiology.md`
- [ ] `methods/writing-for-journals.md`

**Concepts:**
- [ ] `concepts/implementation-science.md`
- [ ] `concepts/health-systems-strengthening.md`
- [ ] `concepts/research-ethics.md`
- [ ] `concepts/global-health-governance.md`

### Priority 4A: Library card enrichment with current developments
**Status:** DONE (2026-03-30)

- [x] Enrich `methods/spatial-epidemiology.md` with 2025-2026 software/method updates, practical examples, open references, and learning path
- [x] Enrich `methods/surveillance-systems.md` with WHO PHI framework, pandemic agreement, digital-health updates, practical examples, and learning path
- [x] Enrich `methods/diagnostic-test-evaluation.md` with STARD-AI, regulatory references, practical examples, and learning path
- [x] Enrich `methods/causal-inference.md` with TARGET guidance, target-trial updates, open references, and learning path
- [x] Enrich `methods/systematic-reviews.md` with PROSPERO 2025, current Cochrane guidance, and learning path
- [x] Enrich `methods/study-designs.md` with TARGET/estimands context, practical examples, and learning path
- [x] Enrich `methods/data-management.md` with WHO data principles, digital-health strategy updates, and learning path
- [x] Enrich `methods/writing-for-journals.md` with ICMJE 2026 and AI-reporting updates
- [x] Enrich `concepts/current-challenges-2026.md` with dated 2025-2026 policy, displacement, climate, and AI/digital-governance developments
- [x] Enrich `concepts/digital-health-epi.md` with WHO digital-health strategy extension, AI-governance context, and learning path
- [x] Enrich `disease-areas/hat-sleeping-sickness.md` with 2024 case count, 2025 country validations, 2026 acoziborole milestone, practical examples, and learning path
- [x] Enrich remaining library cards in `06_library/` with the same pattern

---

### Priority 5: Ideas enrichment
**Status:** DONE (2026-03-29)

Add research-specific fields to the ideas system.

**Schema changes needed:**
- [x] Add columns to `ideas` table: `domain`, `linked_papers`, `feasibility`, `phd_relevance`, `novelty_status`
- [x] Update `R/mod_ideas.R` UI to include new fields
- [x] Update idea type options: Research question / Method idea / Analysis approach / Collaboration / Paper concept / Policy implication
- [x] Update domain options: Epidemiology / Biostatistics / Surveillance / Spatial / NTDs / PH systems

### Priority 5A: Learning Hub courses + course browser
**Status:** DONE (2026-03-30)

- [x] Create 5 in-repo courses under `06_library/courses/`
- [x] Add 50 lesson markdown files + 5 `lessons.json` manifests + 5 `README.md` files
- [x] Register 5 new course projects in `metis.sqlite` with `domain = 'education'`
- [x] Restructure `R/mod_learning.R` to show a course browser above competencies
- [x] Add course detail view with lesson progress, completion, and SR actions
- [x] Refresh the Learning tab layout so courses lead the page, competencies sit in the middle, and activity/resources remain in the bottom section

### Priority 5B: Knowledge linking database
**Status:** DONE (2026-03-30)

- [x] Add `knowledge_links` table to `ensure_db_schema()`
- [x] Populate course, competency, library-card, and method links in SQLite
- [x] Insert lesson-to-library-card reference links for all 5 courses
- [x] Add deterministic `sync_knowledge_links(paths)` startup refresh so the graph stays aligned with course/library content

### Priority 5C: Reading lists
**Status:** DONE (2026-03-30)

- [x] Create `06_library/reading-lists/essential-epidemiology-papers.md`
- [x] Create `06_library/reading-lists/spatial-methods-papers.md`
- [x] Create `06_library/reading-lists/surveillance-design-papers.md`
- [x] Create `06_library/reading-lists/public-health-classics.md`
- [x] Create `06_library/reading-lists/open-access-textbooks.md`

---

### Priority 6: Talks & conferences
**Status:** DONE (2026-03-30)

New content type for conference sessions, TED talks, webinars, podcasts.

**DB table:**
```sql
CREATE TABLE IF NOT EXISTS talks (
  talk_id TEXT PRIMARY KEY,
  title TEXT,
  speaker TEXT,
  source TEXT,          -- TED, conference, webinar, podcast
  event_name TEXT,      -- e.g. "ASTMH 2025", "TED Global Health"
  talk_date TEXT,
  url TEXT,
  transcript_path TEXT,
  structured_note_path TEXT,
  domain TEXT,
  project_link TEXT,
  key_takeaways TEXT,
  created_at TEXT
)
```

**TED talk intake:**
- User provides URL
- Scrape transcript from ted.com or YouTube
- Run through Crucible as type "talk"
- Extract: thesis, evidence, methods, implications
- Store in 05_sources/talks/

**Questions to ask user:**
- [ ] Which conferences do you attend regularly? (ASTMH, ECTMIH, ISNTD?)
- [ ] Do you watch TED talks on specific topics? Health, science, data?
- [ ] Any webinar series you follow? (WHO EPI-WIN, LSHTM events, ITM seminars?)
- [ ] Do you listen to health/science podcasts?

**Completed implementation:**
- [x] Add `R/mod_talks.R` dashboard module for logging talks, webinars, podcasts, and conference sessions
- [x] Add CRUD helpers for `talks` in `R/data_store.R`
- [x] Add `Talks` panel under `More` in the dashboard navigation
- [x] Support transcript file intake to `05_sources/talks/transcripts/`
- [x] Add Claude Code handoff prompt generation for transcript or note analysis

---

### Priority 7: MCP server installation + testing
**Status:** Built, not installed

- [ ] `pip install -e 08_system/mcp-server/`
- [ ] Configure in Claude Code settings.json
- [ ] Configure in Claude Desktop config (if user has Desktop)
- [ ] Test each of the 9 tools
- [ ] Fix any path/permission issues on WSL2

---

### Priority 8: Dashboard rename cleanup
**Status:** Mostly done, minor leftovers

- [ ] Rename `07_outputs/apps/metis-dashboard/` folder to `metis-dashboard/` (or keep as-is to avoid breaking paths)
- [ ] Update Windows Task Scheduler task names (if user wants)
- [ ] Update curl user-agent string
- [ ] Decision: keep `metis.sqlite` filename? (yes, changing would lose data)

---

## Questions bank — things to ask the user in future sessions

### Content & sources
- [ ] What textbooks do you own/have access to? (Gordis, Rothman, Kirkwood?)
- [ ] Which journal subscriptions do you have? (ITM institutional access?)
- [ ] Do you use Zotero, Mendeley, or another reference manager?
- [ ] What PubMed saved searches do you have beyond HAT?
- [ ] Do you have access to WHO institutional repository (IRIS)?
- [ ] What R packages do you use most frequently in your analysis work?
- [ ] Are there specific datasets you regularly work with beyond TRYPELIM/WHO Atlas?

### Learning & career
- [ ] What's your current stats/methods comfort level? (self-assessment per domain)
- [ ] Which online platforms do you use? (Coursera, edX, DataCamp?)
- [ ] Any upcoming courses planned?
- [ ] Timeline for PhD defense?

### Workflow
- [ ] Do you use Claude Desktop? If so, on which machines?
- [ ] Do you use Claude Cowork? For which projects?
- [ ] How many meetings per week on average?
- [ ] Do you take notes during conferences digitally or on paper?
- [ ] Do you already have a reference management system with papers in it?

### News & monitoring
- [ ] Languages: English, French, Dutch — all three for news?
- [ ] Budget for paid APIs? (ProMED samdesk, Economist)
- [ ] Which WHO regional offices are relevant? (AFRO primarily?)
- [ ] Do you follow specific researchers on social media? (for signal detection)

### Technical
- [ ] Python version on WSL2?
- [ ] Node.js available? (for potential future MCP alternatives)
- [ ] Claude Desktop installed? Version?
- [ ] Available disk space for cached feeds/transcripts?

---

## Long-term vision: Open-source Metis

**Goal:** Metis becomes a generic, configurable, open-source research PKM for public health / epidemiology professionals.

**Core principle:** Everything built now should be configurable, not hardcoded to one user.

### What "configurable" means in practice:
- **Reference manager:** Support Zotero AND Mendeley (detect which is installed)
- **Library:** User imports their own papers, not pre-seeded with HAT-specific content
- **Learning hub:** Self-assessment on first run sets initial skill levels; competency domains are the same for all epi/PH professionals
- **Projects:** User defines their own projects, articles, thesis structure
- **Ideas:** Generic research idea types, not locked to one disease
- **News feeds:** Default set of epi/PH feeds, but user can add/remove
- **Agents:** Core agents (Epidemiologist, Methods Coach, Librarian, Writing Partner) are universal; disease-specific agents are optional modules
- **Crucible:** Analysis templates work for any health research, not just HAT
- **Dashboard:** First-run wizard that asks: your name, your disease focus, your institution, your reference manager, your skill levels
- **MCP server:** Works from any Claude interface, configurable PKM root path

### What to build eventually:
- [ ] First-run setup wizard (name, focus area, institution, reference manager choice)
- [ ] Config file (`metis-config.yaml`) for user-specific settings instead of hardcoded values
- [ ] Zotero integration (Better BibTeX export → library sync)
- [ ] Mendeley integration (API or export sync)
- [ ] Skill self-assessment flow in Learning tab
- [ ] Article quality assessment tool (user drops their draft, agents assess readiness)
- [ ] R script analysis in Crucible (import user's analysis scripts, review methodology)
- [ ] GitHub repo setup with proper README, LICENSE, CONTRIBUTING.md
- [ ] Docker container for easy deployment
- [ ] Documentation site (what it is, how to set up, how to configure)

### Design rules (apply to all current implementation):
1. No hardcoded user paths — always use config/env vars
2. No hardcoded disease names in generic components — HAT-specific content goes in user config
3. Seed data should be "example" data, not production data
4. Agent system prompts should reference "the user's research focus" not "HAT"
5. Reference manager integration should be pluggable (Zotero adapter, Mendeley adapter)

---

## User answers (2026-03-29)

### News
- De Standaard: all sections
- Languages: English + Dutch
- No Economist/FT/NYT subscription — use free alternatives, focus on awareness + synthesis
- No ProMED API budget — use WHO DON + HealthMap + CDC MMWR
- Podcasts: recommendations welcome but not played in dashboard
- Key need: **daily/weekly synthesis** of what's happening, with links to articles

### Learning
- All domains: **beginner** (starting fresh with structured learning)
- MLM course in progress
- No other courses planned yet

### Workflow
- Uses **Zotero** for reference management
- Uses **Claude Desktop** often — MCP server config needed
- Future: grammar/writing correction in Claude Desktop
- Conference notes: none yet, but wants recording + transcription capability
- No conferences yet, but infrastructure must exist

### Open source vision
- Metis should be generic and configurable
- Support both Zotero and Mendeley
- Someone else should be able to set it up for their own research
- First-run configuration instead of hardcoded content
- Skill assessment, article import, project setup all user-configurable

---

## Architecture decisions log

| # | Decision | Rationale | Date |
|---|---|---|---|
| 1 | Keep `metis.sqlite` filename | Renaming would lose existing data | 2026-03-29 |
| 2 | Keep `02_agents/metis/` directory name | Other agents reference it; content says "Metis" | 2026-03-29 |
| 3 | Keep `metis-dashboard` folder name | Renaming breaks launch scripts and Task Scheduler | 2026-03-29 |
| 4 | MCP server in `08_system/mcp-server/` | Co-located with PKM, not a separate repo | 2026-03-29 |
| 5 | Personal Finance → archive, not delete | May become a separate personal PKM later | 2026-03-29 |
| 6 | Crucible as dashboard tab, not standalone | Integrates with existing Ideas/Library/Tasks UI | 2026-03-29 |
| 7 | Three-tier news (world/research/epi intel) | Different scan frequencies and signal priorities | 2026-03-29 |
| 8 | ProMED via HealthMap, not paid API | Free alternative available; reassess later | 2026-03-29 |
| 9 | TED transcripts via web scrape | No official API; transcripts publicly available | 2026-03-29 |
