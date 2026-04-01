# Metis PKM — Detailed Handoff Instructions for Continuation

**Purpose:** This document provides complete instructions for any AI assistant (Claude, Gemini, ChatGPT, etc.) to continue building the Metis PKM. Read this ENTIRE document before making any changes.

**Last updated:** 2026-03-29
**Implementation plan:** `01_control-room/implementation-plan-v7.md` (tracks what's done and what's next)

---

## 1. What is Metis?

Metis is a **research second brain** for epidemiologists and public health professionals. Named after the Greek Titaness of wisdom, good counsel, and deep thought.

### Current state
- R Shiny dashboard with 10 tabs (Control Room, Library, PhD, Projects, Meetings, News, Learning, Ideas, Crucible, More)
- 17 specialist AI agents with system prompts and contracts
- SQLite database with 25+ tables
- 25 knowledge reference cards in `06_library/`
- Python MCP server (built, not yet installed) for access from Claude Desktop/Code
- 23 RSS feeds across 3 tiers (world, research, epi intelligence)
- 12 learning competency domains seeded

### Identity
Metis is a **Senior Researcher / Epidemiologist / Public Health Methodologist**. She is NOT:
- A general-purpose assistant
- A personal life manager
- A todo app

She IS:
- A rigorous research colleague who challenges methodology
- A knowledge router who knows which specialist to invoke
- A record-keeper who ensures all work is captured in the PKM
- A learning companion who tracks skill development

### Long-term vision: OPEN SOURCE
Everything built must be **configurable, not hardcoded to one user**. Metis will become an open-source tool that any epidemiologist/public health researcher can adopt. This means:
- No hardcoded paths — use environment variables and config files
- No hardcoded disease names in generic components (HAT-specific content is the current user's config)
- Support both Zotero AND Mendeley
- First-run wizard for user configuration (future)
- Courses and learning resources should be useful to any epi/PH professional

---

## 2. Project structure

```
monia-second-brain/                    # Root (name kept for backward compat)
├── 00_inbox/                          # Drop zone for new files
│   └── crucible/                      # Crucible intake storage
├── 01_control-room/                   # Strategy, roadmaps, THIS FILE
│   ├── implementation-plan-v7.md      # Master tracking document
│   └── handoff-instructions.md        # THIS FILE
├── 02_agents/                         # 17 AI agent personas
│   ├── monia/                         # Metis (directory kept as "monia")
│   ├── epidemiologist/
│   ├── librarian/
│   ├── methods-coach/
│   ├── writing-partner/
│   ├── phd-architect/
│   ├── software-engineer/
│   └── ... (17 total)
├── 03_domains/                        # Knowledge by subject area
│   └── phd/                           # PhD spine, articles, methods
├── 04_projects/active/                # Project cards (YAML frontmatter)
├── 05_sources/                        # Raw materials (papers, meetings, data)
│   └── literature/sleeping-sickness/  # 2500+ papers with metadata
├── 06_library/                        # Knowledge reference cards
│   ├── methods/                       # 14 methodology cards
│   ├── concepts/                      # 9 concept cards
│   ├── disease-areas/                 # 2 disease cards
│   └── people-organizations/          # 1 institutions card
├── 07_outputs/
│   ├── apps/metis-dashboard/          # R Shiny dashboard
│   │   ├── app.R
│   │   ├── R/                         # All modules (mod_*.R)
│   │   ├── data/metis.sqlite          # SQLite database
│   │   ├── www/styles.css             # Stylesheet
│   │   └── inst/scripts/              # Worker scripts
│   └── reviews/                       # Agent output files (17 dirs)
├── 08_system/
│   └── mcp-server/                    # Python MCP server
└── 09_archive/                        # Archived agents
```

---

## 3. Technology stack

- **R Shiny + bslib** — Dashboard UI (Bootstrap 5)
- **SQLite** — Database at `07_outputs/apps/metis-dashboard/data/metis.sqlite`
- **Python** — MCP server at `08_system/mcp-server/`
- **CSS** — Custom styles at `www/styles.css`
- Palette: deep teal #174c4f, rust/amber #b36a1d, cream #f4f1ea, dark slate #1f2a2e
- Fonts: IBM Plex Serif (headings), Source Sans 3 (body), JetBrains Mono (code)

---

## 4. PRIORITY TASKS (in order)

### Priority 2: News feeds — DONE (2026-03-29)
23 feeds in 3 tiers. See `inst/scripts/fetch_news_feeds.R`.

### Priority 3: Learning competencies — DONE (2026-03-29)
12 domains seeded. See `data_store.R` `seed_default_data()`.

### Priority 4: Library cards — DONE (2026-03-29)
25 cards across methods/, concepts/, disease-areas/, people-organizations/.

### Priority 5: Ideas enrichment — TODO
See implementation-plan-v7.md for schema changes.

### Priority 6: Talks & conferences — TODO
`talks` table already created in DB schema. Need UI module.

### Priority 7: MCP server — TODO (install + test)

### Priority 8: Dashboard folder rename — DEFERRED (keep as-is)

---

## 5. CONTENT CREATION — DETAILED INSTRUCTIONS

This is the most important section. The other AI should spend significant time on this.

### 5A. What content to create and why

The `06_library/` directory is the knowledge backbone. Current cards are reference summaries. What's needed is **deep, course-quality educational content** that:

1. Teaches the user (and future open-source users) epidemiology and public health
2. Links to real courses, textbooks, and online resources
3. Provides practical examples and exercises
4. Connects to the Learning Hub for skill tracking
5. Can be used as the basis for spaced repetition cards

### 5B. Research mandate

**Search the internet extensively for:**

1. **University curricula:**
   - MSc Epidemiology programs: LSHTM, Johns Hopkins Bloomberg SPH, Karolinska, ITM Antwerp, Swiss TPH
   - MPH programs: Harvard, Columbia, UNC Chapel Hill, Emory
   - FETP (Field Epidemiology Training Programs): CDC FETP, EPIET/EUPHEM (ECDC)
   - Extract: course lists, learning objectives, recommended readings

2. **Open educational resources:**
   - CDC self-study courses (SS1000 Principles of Epi, SS1978, etc.)
   - OpenWHO courses (especially epi, surveillance, outbreak)
   - Coursera/edX epidemiology courses (free audit versions)
   - Khan Academy statistics/probability
   - MIT OpenCourseWare biostatistics

3. **Textbooks** (extract chapter structures and key concepts):
   - Gordis Epidemiology (7th ed, 2024)
   - Rothman's Modern Epidemiology (4th ed)
   - Kirkwood & Sterne: Essential Medical Statistics
   - Gelman & Hill: Data Analysis Using Regression and MLM
   - Lawson: Handbook of Spatial Epidemiology
   - Hernán & Robins: Causal Inference (What If) — FREE online
   - Cochrane Handbook for Systematic Reviews — FREE online
   - CDC Field Epidemiology Manual — FREE online

4. **Current debates and hot topics:**
   - Lancet commissions (search for recent ones on surveillance, UHC, NTDs)
   - WHO technical guidelines updates
   - ECDC technical reports
   - Global health funding crisis (USAID cuts 2025-2026)
   - AI in epidemiology debates

5. **Key papers and landmark studies:**
   - For each method card, find the 3-5 most cited methodological papers
   - For each concept, find the foundational framework paper
   - For disease areas, find the latest WHO status reports

### 5C. Where to put the content

```
06_library/
├── methods/          # Methodology reference cards (already have 14)
├── concepts/         # Cross-cutting PH concepts (already have 9)
├── disease-areas/    # Disease-specific knowledge (already have 2)
├── people-organizations/  # Key institutions (already have 1)
├── courses/          # NEW — Course content (see section 6)
│   ├── epidemiology-foundations/
│   ├── biostatistics/
│   ├── spatial-epidemiology/
│   ├── surveillance-methods/
│   ├── outbreak-investigation/
│   └── ...
└── reading-lists/    # NEW — Curated reading lists per topic
    ├── essential-epi-papers.md
    ├── spatial-methods-papers.md
    ├── surveillance-design-papers.md
    └── ...
```

### 5D. Content quality standards

Every piece of content must:
- Be **accurate** (cite sources, use correct terminology)
- Be **scannable** (bullet points, tables, headers — not walls of text)
- Include **practical examples** where possible
- End with a **Key references** section
- Include **links** to freely available online resources
- Be written for a **beginner-to-intermediate** audience
- Not assume access to paid journals (prefer open access alternatives)

---

## 6. LEARNING HUB COURSES — DETAILED INSTRUCTIONS

### 6A. How the current course system works

The existing MLM (Multilevel Modelling) course demonstrates the pattern. Here's how it works:

**Architecture:**
1. Each course is a project in the `projects` table with `domain = 'education'`
2. Course content is stored as a `lessons.json` file in the course directory
3. The `course_progress` table tracks which lessons are completed
4. Completed lessons can be added to spaced repetition for review
5. The Library tab's courses section renders cards for each education project

**lessons.json format:**
```json
{
  "lessons": [
    {
      "id": "lesson-01",
      "title": "Introduction to Multilevel Models",
      "description": "Why observations are nested and what that means for analysis",
      "section": "Foundations",
      "order": 1
    },
    {
      "id": "lesson-02",
      "title": "Random Intercepts Model",
      ...
    }
  ]
}
```

**Course rendering in mod_library.R:**
- Reads `lessons.json` from the course's `external_path`
- Shows progress bar (completed / total lessons)
- Lists lessons with "Mark complete" and "Add to SR" buttons
- Completed lessons are greyed out with a checkmark

### 6B. Courses to create

Create course directories inside the PKM at `06_library/courses/`. Each course needs:

1. A `lessons.json` file following the format above
2. For each lesson: a markdown file with the actual content
3. A `README.md` explaining the course

**Course 1: Foundations of Epidemiology**
Based on: CDC SS1000, Gordis chapters 1-8, LSHTM intro epi module
```
06_library/courses/epidemiology-foundations/
├── README.md
├── lessons.json
├── lessons/
│   ├── 01-what-is-epidemiology.md
│   ├── 02-measures-of-disease-frequency.md
│   ├── 03-measures-of-association.md
│   ├── 04-study-designs-overview.md
│   ├── 05-cohort-studies.md
│   ├── 06-case-control-studies.md
│   ├── 07-cross-sectional-studies.md
│   ├── 08-experimental-studies.md
│   ├── 09-bias-confounding-effect-modification.md
│   ├── 10-screening-and-surveillance.md
│   ├── 11-causation.md
│   └── 12-outbreak-investigation.md
```

**Course 2: Biostatistics for Epidemiologists**
Based on: Kirkwood & Sterne, OpenIntro Statistics, Khan Academy
```
06_library/courses/biostatistics/
├── lessons/
│   ├── 01-descriptive-statistics.md
│   ├── 02-probability-basics.md
│   ├── 03-probability-distributions.md
│   ├── 04-confidence-intervals.md
│   ├── 05-hypothesis-testing.md
│   ├── 06-chi-square-and-t-tests.md
│   ├── 07-correlation-simple-regression.md
│   ├── 08-multiple-regression.md
│   ├── 09-logistic-regression.md
│   ├── 10-survival-analysis.md
│   ├── 11-poisson-regression.md
│   └── 12-intro-multilevel-models.md
```

**Course 3: Spatial Epidemiology**
Based on: Lawson handbook, Bivand et al., Kulldorff methods
```
06_library/courses/spatial-epidemiology/
├── lessons/
│   ├── 01-why-space-matters.md
│   ├── 02-gis-basics-coordinate-systems.md
│   ├── 03-disease-mapping.md
│   ├── 04-cluster-detection-satscan.md
│   ├── 05-spatial-autocorrelation.md
│   ├── 06-spatial-regression.md
│   ├── 07-r-packages-for-spatial-epi.md
│   └── 08-practical-workflow.md
```

**Course 4: Surveillance System Design**
Based on: WHO PHI framework, CDC guidelines, IDSR
```
06_library/courses/surveillance-methods/
├── lessons/
│   ├── 01-what-is-surveillance.md
│   ├── 02-types-of-surveillance.md
│   ├── 03-indicator-vs-event-based.md
│   ├── 04-case-definitions.md
│   ├── 05-data-collection-and-flow.md
│   ├── 06-evaluation-cdc-attributes.md
│   ├── 07-digital-surveillance.md
│   ├── 08-post-elimination-surveillance.md
```

**Course 5: Research Methods & Scientific Writing**
Based on: EQUATOR network, Cochrane handbook
```
06_library/courses/research-writing/
├── lessons/
│   ├── 01-formulating-research-questions.md
│   ├── 02-literature-review-strategy.md
│   ├── 03-study-protocol-development.md
│   ├── 04-reporting-guidelines-equator.md
│   ├── 05-writing-introduction.md
│   ├── 06-writing-methods.md
│   ├── 07-writing-results.md
│   ├── 08-writing-discussion.md
│   ├── 09-peer-review-process.md
│   └── 10-systematic-reviews-prisma.md
```

### 6C. Lesson content format

Each lesson markdown file should follow this structure:

```markdown
# Lesson Title

## Learning objectives
- Objective 1
- Objective 2
- Objective 3

## Prerequisites
- What the learner should know before this lesson

## Content

### Section 1: [Topic]
[Explanation with examples]

### Section 2: [Topic]
[Explanation with examples]

### Practical example
[A worked example using real or realistic epidemiological data]

## Key takeaways
- Bullet 1
- Bullet 2
- Bullet 3

## Self-check questions
1. Question 1?
2. Question 2?
3. Question 3?

## Further reading
- [Resource 1](url)
- [Resource 2](url)

## Links to Metis library
- Related method card: `06_library/methods/[card].md`
- Related concept: `06_library/concepts/[card].md`
```

### 6D. Registering courses in the dashboard

For each course created, add a project to the database:
```sql
INSERT INTO projects (project_id, title, domain, status, priority, external_path, created_at)
VALUES ('course-epi-foundations', 'Epidemiology Foundations', 'education', 'active', 'medium',
        '/path/to/06_library/courses/epidemiology-foundations', datetime('now'));
```

The `external_path` should point to the course directory where `lessons.json` lives.

### 6E. Learning hub UI changes needed

The Learning tab (`mod_learning.R`) needs to be restructured:

**Current:** One page with competency grid + activity logger + resources
**Target:** Two-level structure:

1. **Top level: Course browser**
   - Grid of course cards (like the Library gallery view)
   - Each card shows: title, progress %, number of lessons, linked competency
   - Clicking opens the course detail view

2. **Course detail view:**
   - Lesson list with completion status (current behavior)
   - Progress bar
   - Spaced repetition integration
   - Link back to course browser

3. **Competency dashboard** (keep current, move below courses)
   - Competency cards with levels
   - Now linked to courses: "Take the Epidemiology Foundations course to improve this competency"

---

## 7. LINKING EVERYTHING TOGETHER

This is the critical integration work. The PKM's value comes from connections between pieces:

### Links to build:
1. **Library card → Learning competency:** Each method/concept card links to a competency domain
2. **Learning competency → Course:** Each competency links to relevant courses
3. **Course lesson → Library card:** Each lesson references relevant library cards
4. **Course lesson → Spaced repetition:** Completed lessons generate SR cards
5. **Ideas → Library cards:** Research ideas reference which methods/concepts apply
6. **Crucible intake → Library:** Analyzed papers get linked to relevant library cards
7. **News briefs → Concepts:** News items tagged with relevant concept domains
8. **Projects → Competencies:** Which competencies does each project exercise?

### How to implement links:
The SQLite database should store these relationships. Create a generic `knowledge_links` table:
```sql
CREATE TABLE IF NOT EXISTS knowledge_links (
  link_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT,    -- 'library_card', 'competency', 'course_lesson', 'idea', 'news_brief'
  source_id TEXT,      -- e.g. 'methods/spatial-epidemiology.md', 'comp-spatial-epi'
  target_type TEXT,
  target_id TEXT,
  link_label TEXT,     -- e.g. 'teaches', 'requires', 'references', 'exercises'
  created_at TEXT
)
```

---

## 8. DATABASE SCHEMA REFERENCE

The SQLite database at `data/metis.sqlite` has these tables:

**Core:** library_inventory, library_duplicates, library_seeded
**Projects:** projects, tasks
**Meetings:** meetings, meeting_persons, meeting_attendance
**News:** news_briefs, news_topics, news_brief_topics
**Ideas:** ideas, idea_links
**Learning:** learning_competencies, learning_activities, learning_resources, spaced_repetition, course_progress
**PhD:** phd_milestones
**Finance:** finance_watchlist, finance_snapshots
**System:** jobs_log, agent_runs, crucible_intake, talks

All insert/query functions are in `R/data_store.R`. The `ensure_db_schema()` function creates all tables.

---

## 9. CODING STANDARDS

When modifying R Shiny code:

1. **Module pattern:** Every tab is a module with `*_ui(id)` and `*_server(id, paths)` functions
2. **SQL safety:** Always use parameterized queries (`DBI::dbExecute(con, "... ?", params = list(...))`)
3. **Error handling:** Wrap DB queries in `tryCatch(..., error = function(...) data.frame())`
4. **CSS classes:** Follow existing naming: `.metis-brand`, `.crucible-*`, `.news-*`, etc.
5. **Icons:** Use `icon("name")` from Font Awesome, NEVER emoji
6. **Responsive:** All grids must stack at 768px breakpoint
7. **Accessibility:** Support `prefers-reduced-motion`, maintain WCAG AA contrast

---

## 10. WHAT NOT TO CHANGE

- `metis.sqlite` filename (would lose all data)
- `02_agents/metis/` directory name (other files reference it)
- `metis-dashboard` folder name (scripts and Task Scheduler reference it)
- Any existing working functionality — add to it, don't replace it
- The 3-tier news feed structure
- Agent system prompts (unless specifically asked)

---

## 11. TESTING

After making changes, verify:
1. Dashboard launches: `shiny::runApp()` from the dashboard directory
2. All tabs load without errors
3. New database tables are created on first run
4. Existing data is preserved (seed functions check count before inserting)
5. CSS renders correctly at desktop and 768px widths
