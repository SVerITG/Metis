# Prompt for continuation AI

You are continuing work on **Metis**, a research second brain for epidemiologists and public health professionals. It is an R Shiny dashboard + PKM (Personal Knowledge Management) system built by a previous Claude Code session. You are picking up where that session left off.

## Before you do ANYTHING

Read these two files completely:

1. `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/monia-second-brain/01_control-room/implementation-plan-v7.md` — tracks what's done and what's next
2. `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/monia-second-brain/01_control-room/handoff-instructions.md` — detailed technical instructions, coding standards, project structure, and content creation mandate

Also read:
3. `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/monia-second-brain/CLAUDE.md` — system configuration and agent routing

These three documents are your complete briefing. Do not skip them.

## What is Metis

Metis is named after the Greek Titaness of wisdom. It is a **Senior Researcher / Epidemiologist / Public Health Methodologist** second brain. It has:
- An R Shiny dashboard with 10 tabs (Control Room, Library, PhD, Projects, Meetings, News, Learning, Ideas, Crucible, More)
- 17 specialist AI agents with system prompts
- SQLite database (25+ tables)
- 25 knowledge reference cards in `06_library/`
- A Python MCP server (built, not installed)
- 23 RSS news feeds across 3 tiers

The long-term goal is to make Metis **open source** — any epidemiologist or public health researcher can configure it for themselves. Everything you build must be generic and configurable, not hardcoded to one user.

## Your tasks (in priority order)

### Task 1: Create educational courses for the Learning Hub

This is the **biggest and most important task**. You need to create 5 complete courses.

**How courses work:** Read `07_outputs/apps/metis-dashboard/R/mod_library.R` lines 340-500 to understand the course rendering system. Each course needs:
- A `lessons.json` file (see format in handoff-instructions.md section 6B)
- Markdown content files for each lesson (see template in section 6C)
- Registration as a project in the SQLite database with `domain = 'education'`

**Courses to create at `06_library/courses/`:**

1. **Epidemiology Foundations** (12 lessons) — Based on CDC SS1000, Gordis chapters 1-8. Covers: what is epi, disease frequency measures, measures of association, study designs (cohort, case-control, cross-sectional, experimental), bias/confounding, screening, causation, outbreak investigation.

2. **Biostatistics for Epidemiologists** (12 lessons) — Based on Kirkwood & Sterne, OpenIntro Statistics. Covers: descriptive stats, probability, distributions, CIs, hypothesis testing, chi-square/t-tests, regression (simple, multiple, logistic), survival analysis, Poisson regression, intro to MLM.

3. **Spatial Epidemiology** (8 lessons) — Based on Lawson handbook, Kulldorff methods. Covers: why space matters, GIS basics, disease mapping, SaTScan cluster detection, spatial autocorrelation, spatial regression, R packages, practical workflow.

4. **Surveillance System Design** (8 lessons) — Based on WHO PHI framework, CDC guidelines. Covers: what is surveillance, types, indicator vs event-based, case definitions, data flow, evaluation attributes, digital surveillance, post-elimination.

5. **Research Methods & Scientific Writing** (10 lessons) — Based on EQUATOR network, Cochrane handbook. Covers: research questions, lit review, protocol development, reporting guidelines, writing each IMRaD section, peer review, systematic reviews.

**For each lesson, search the internet extensively for:**
- Current best practices and guidelines
- Free online resources (OpenWHO, CDC, WHO guidelines)
- Practical examples from real epidemiological studies
- Self-check questions the learner can use
- Links to the existing library reference cards in `06_library/methods/` and `06_library/concepts/`

**Lesson content format:** Each lesson must have: Learning objectives, Prerequisites, Content sections with practical examples, Key takeaways, Self-check questions, Further reading (with URLs), Links to Metis library cards.

**After creating the files**, register each course in the SQLite database. Connect to `07_outputs/apps/metis-dashboard/data/metis.sqlite` and run:
```sql
INSERT INTO projects (project_id, title, domain, status, priority, external_path, created_at)
VALUES ('course-epi-foundations', 'Epidemiology Foundations', 'education', 'active', 'medium',
        '[absolute path to 06_library/courses/epidemiology-foundations]', datetime('now'));
```
Do this for all 5 courses.

### Task 2: Enrich library cards with deep web research

The 25 existing library cards in `06_library/` are good reference summaries but need enrichment. For EACH card:

1. **Search the internet** for the latest developments, guidelines, and debates in that topic area
2. **Add a "Current developments (2025-2026)" section** with recent news, guideline updates, or methodological advances
3. **Add more practical examples** — real studies that used the method, with citations
4. **Expand the "Key references" section** with URLs to freely available resources
5. **Add a "Learning path" section** that links to relevant courses and competencies

Focus especially on:
- `methods/spatial-epidemiology.md` — add latest SaTScan developments, new R packages
- `methods/surveillance-systems.md` — add WHO PHI framework details (launched Dec 2025)
- `concepts/current-challenges-2026.md` — update with latest developments
- `disease-areas/hat-sleeping-sickness.md` — latest case numbers, treatment advances

### Task 3: Create reading lists

Create curated reading lists at `06_library/reading-lists/`:

1. `essential-epidemiology-papers.md` — 20-30 landmark papers every epidemiologist should know
2. `spatial-methods-papers.md` — key papers on cluster detection, disease mapping, SaTScan methodology
3. `surveillance-design-papers.md` — foundational papers on surveillance system design and evaluation
4. `public-health-classics.md` — John Snow, Semmelweis, Framingham, Doll & Hill, etc.
5. `open-access-textbooks.md` — list of FREE online textbooks and courses with URLs

For each paper, include: authors, year, title, journal, DOI or URL, and a 1-2 sentence note on why it matters.

### Task 4: Build the knowledge linking database

Create and populate a `knowledge_links` table in the SQLite database:

```sql
CREATE TABLE IF NOT EXISTS knowledge_links (
  link_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT,
  source_id TEXT,
  target_type TEXT,
  target_id TEXT,
  link_label TEXT,
  created_at TEXT
);
```

Then insert links between:
- Each library card → its relevant competency domain
- Each competency → relevant courses
- Each course lesson → relevant library cards
- Each method → related methods (e.g., spatial-epi → biostatistics, surveillance → sampling)

### Task 5: Restructure the Learning tab UI

Modify `R/mod_learning.R` to show courses prominently:

1. **Top section:** Course browser — grid of course cards showing title, progress %, lesson count
2. **Middle section:** Competency dashboard (keep current grid)
3. **Bottom section:** Activity logger and resources (keep current)

Each course card in the browser should link to its detail view (the existing lesson list rendering already works).

### Task 6: Ideas enrichment

Modify the Ideas system to support research-specific metadata:

1. Add columns to `ideas` table in `ensure_db_schema()`:
   - `domain TEXT` — Epidemiology, Biostatistics, Surveillance, Spatial, NTDs, PH systems
   - `linked_papers TEXT` — comma-separated references
   - `feasibility TEXT` — high/medium/low
   - `phd_relevance TEXT` — Article 1/2/3/Future/None
   - `novelty_status TEXT` — novel/partial/exists

2. Update `R/mod_ideas.R`:
   - Add domain dropdown
   - Change idea_type choices to: Research question, Method idea, Analysis approach, Collaboration, Paper concept, Policy implication
   - Add PhD relevance selector
   - Add feasibility assessment

## Critical rules

1. **Read the handoff-instructions.md FIRST** — it has coding standards, what not to change, and testing instructions
2. **Do NOT rename** `metis.sqlite`, `02_agents/metis/`, or the `metis-dashboard` folder
3. **Do NOT break existing functionality** — always check `ensure_db_schema()` pattern (CREATE TABLE IF NOT EXISTS)
4. **Use parameterized SQL** — never concatenate user input into SQL strings
5. **Test that the dashboard still launches** after your changes: `shiny::runApp()` from the dashboard directory
6. **Update the implementation plan** (`01_control-room/implementation-plan-v7.md`) as you complete tasks — mark items as done with dates

## The user's profile

- Epidemiologist working on sleeping sickness (HAT) at ITM Antwerp
- PhD in progress on elimination/post-elimination surveillance
- All competency domains currently at beginner level
- Uses Zotero for references
- Uses Claude Desktop
- Works on WSL2 (Linux on Windows)
- Languages: English, Dutch
- Wants this to eventually be open source for any epi/PH researcher

Start with Task 1 (courses) as it's the largest and most impactful. Work systematically — create one complete course before moving to the next.
