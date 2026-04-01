# Prompt for continuation AI — Phase 2: Content Enrichment

You are continuing work on **Metis**, a research second brain for epidemiologists and public health professionals. Phase 1 (infrastructure, modules, courses, library cards) is complete. You are now doing Phase 2: deep content enrichment, additional courses, and open-source preparation.

## CRITICAL: Read these files first

1. `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/monia-second-brain/01_control-room/implementation-plan-v7.md` — master tracker
2. `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/monia-second-brain/01_control-room/handoff-instructions.md` — technical instructions
3. `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/monia-second-brain/01_control-room/implementation-plan-phase2.md` — THIS PHASE'S TRACKER

## CRITICAL: Update the implementation plan after EVERY task

After completing each task, update `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/monia-second-brain/01_control-room/implementation-plan-phase2.md`:
- Mark the task as `[x]` with the date
- Note what was created/modified
- Note any issues encountered
- This is NON-NEGOTIABLE — if you run out of tokens, the next AI must know exactly where you stopped

---

## Task 1: Deep course content enrichment

**Goal:** Expand all 55 existing lesson files from thin outlines into substantial 30-minute self-study units.

**Location:** `06_library/courses/` — 5 courses, each with a `lessons/` subdirectory.

**For EACH lesson file:**

1. **Search the internet extensively** for the lesson topic. Find:
   - Current best practices and guidelines (WHO, CDC, ECDC)
   - Free online resources (OpenWHO, CDC self-study, Khan Academy)
   - Real published studies that used this method (cite with DOI)
   - Common mistakes and misconceptions

2. **Expand the content** to include:
   - **Detailed explanations** — not just bullet points, but full paragraphs explaining concepts clearly for a beginner
   - **Worked numerical examples** — e.g., for a lesson on odds ratios: present a 2x2 table with real numbers, walk through the calculation step by step, interpret the result
   - **Real-world case studies** — e.g., for cohort studies: describe the Framingham Heart Study briefly, explain why it's a cohort study, what it found
   - **Common pitfalls** — what beginners get wrong, how to avoid it
   - **R code snippets** where relevant — e.g., for logistic regression: show a simple `glm()` example with interpretation

3. **Expand self-check questions** to 5-8 per lesson, with an answer key at the bottom:
   ```markdown
   ## Self-check questions
   1. What is the difference between incidence and prevalence?
   2. A study finds an odds ratio of 2.5 (95% CI: 1.1-5.7). Interpret this.
   ...

   ## Answer key
   1. Incidence measures new cases over time; prevalence measures all existing cases at a point in time...
   2. The exposure is associated with 2.5 times the odds of disease compared to unexposed...
   ```

4. **Add "Further reading" links** — at least 3 free online resources per lesson with URLs

5. **Cross-reference with library cards** — each lesson should link to the relevant `06_library/methods/` or `06_library/concepts/` card

**Courses to expand (in this order):**
1. `epidemiology-foundations/` (12 lessons) — most important, do this first
2. `biostatistics/` (12 lessons)
3. `spatial-epidemiology/` (8 lessons)
4. `surveillance-methods/` (8 lessons)
5. `research-writing/` (10+ lessons)

**Quality standard:** After expansion, each lesson should be 800-1500 words with at least one worked example and 5+ self-check questions.

---

## Task 2: Build 5 additional courses

**Goal:** Create 5 new courses following the exact same structure as the existing 5.

**Structure for each course:**
```
06_library/courses/{course-name}/
├── README.md          # Course description, prerequisites, learning outcomes
├── lessons.json       # Manifest (see existing courses for exact format)
└── lessons/
    ├── 01-{topic}.md
    ├── 02-{topic}.md
    └── ...
```

**lessons.json format** (copy exactly from existing courses):
```json
{
  "lessons": [
    {"id": "lesson-01", "title": "...", "description": "...", "section": "...", "order": 1},
    {"id": "lesson-02", "title": "...", "description": "...", "section": "...", "order": 2}
  ]
}
```

### Course 6: Outbreak Investigation (10 lessons)
Based on: CDC Field Epidemiology Manual (free online), WHO rapid risk assessment guidelines
```
lessons/
├── 01-when-is-it-an-outbreak.md          # Defining outbreaks, endemic vs epidemic
├── 02-preparing-for-field-investigation.md # Team, supplies, ethics, safety
├── 03-confirming-the-diagnosis.md         # Clinical vs lab confirmation, case verification
├── 04-defining-and-finding-cases.md       # Case definitions (suspected/probable/confirmed), case finding
├── 05-descriptive-epidemiology.md         # Person-place-time, epidemic curves, attack rates
├── 06-generating-hypotheses.md            # Analytic frameworks, hypothesis generation from descriptive data
├── 07-testing-hypotheses.md               # Case-control studies during outbreaks, cohort studies, 2x2 tables
├── 08-environmental-investigation.md      # Environmental sampling, trace-back, source identification
├── 09-implementing-control-measures.md    # Containment, quarantine, prophylaxis, communication
└── 10-communicating-findings.md           # Epi-Aid reports, situation reports, risk communication
```

### Course 7: Health Economics for Public Health (8 lessons)
Based on: Drummond et al., WHO-CHOICE, Disease Control Priorities (DCP3)
```
lessons/
├── 01-why-economics-in-public-health.md   # Scarcity, opportunity cost, efficiency
├── 02-types-of-economic-evaluation.md     # CEA, CBA, CUA, CMA — when to use which
├── 03-measuring-costs.md                  # Direct/indirect costs, costing methodology, perspective
├── 04-measuring-health-outcomes.md        # DALYs, QALYs, life-years — calculation and interpretation
├── 05-cost-effectiveness-analysis.md      # ICER, CE plane, WTP threshold, dominance
├── 06-budget-impact-analysis.md           # BIA methodology, affordability vs cost-effectiveness
├── 07-economic-evaluation-in-practice.md  # Alongside trials, modelling approaches, sensitivity analysis
└── 08-using-evidence-for-priority-setting.md # DCP3, essential packages, resource allocation
```

### Course 8: Research Ethics in Global Health (8 lessons)
Based on: CIOMS guidelines, Declaration of Helsinki, Nuffield Council on Bioethics
```
lessons/
├── 01-foundations-of-research-ethics.md    # Nuremberg, Helsinki, Belmont — historical context
├── 02-ethical-principles.md               # Respect, beneficence, justice, non-maleficence
├── 03-informed-consent.md                 # Consent process, capacity, voluntariness, low-literacy contexts
├── 04-community-engagement.md             # Participatory research, CABs, benefit sharing
├── 05-ethics-review-process.md            # IRB/ethics committees, protocol submission, amendments
├── 06-vulnerable-populations.md           # Children, prisoners, refugees, emergency contexts
├── 07-data-ethics-and-privacy.md          # GDPR, data sharing, anonymization, secondary use
└── 08-surveillance-vs-research.md         # When does surveillance become research? Ethical gray zones
```

### Course 9: R for Epidemiologists (12 lessons)
Based on: R4Epi (free online), Epi R Handbook (free online), R for Data Science
```
lessons/
├── 01-r-and-rstudio-setup.md             # Installation, RStudio interface, packages
├── 02-data-types-and-structures.md        # Vectors, data frames, factors, dates
├── 03-importing-and-cleaning-data.md      # readr, readxl, janitor, data validation
├── 04-data-manipulation-with-dplyr.md     # filter, mutate, group_by, summarise, joins
├── 05-data-visualization-with-ggplot2.md  # Grammar of graphics, epi-relevant plots
├── 06-descriptive-epidemiology-in-r.md    # Frequency tables, cross-tabs, epi curves with incidence2
├── 07-regression-models-in-r.md           # glm(), logistic, Poisson, interpretation
├── 08-survival-analysis-in-r.md           # survival, survminer, Kaplan-Meier, Cox
├── 09-spatial-data-in-r.md                # sf, tmap, leaflet, mapview — reading shapefiles, making maps
├── 10-reproducible-reports.md             # Quarto/RMarkdown, parameterized reports
├── 11-shiny-basics.md                     # Reactive programming, building a simple dashboard
└── 12-project-workflow.md                 # renv, targets, Git, project organization
```

### Course 10: NTD Elimination Strategies (8 lessons)
Based on: WHO NTD Roadmap 2030, Lancet NTD commissions, country case studies
```
lessons/
├── 01-what-is-elimination.md              # WHO definitions, control-elimination-eradication spectrum
├── 02-elimination-successes.md            # Smallpox, guinea worm, onchocerciasis, LF — what worked
├── 03-hat-elimination-journey.md          # gHAT from millions to <1000, mobile teams, new tools
├── 04-surveillance-for-elimination.md     # Active vs passive, case detection sensitivity, zero-case challenge
├── 05-post-elimination-surveillance.md    # Design principles, how long, integration into PHC
├── 06-diagnostics-in-elimination.md       # Test performance at low prevalence, PPV collapse, confirmatory algorithms
├── 07-integration-into-health-systems.md  # Vertical → horizontal, health system strengthening, PHC
└── 08-who-2030-roadmap.md                 # Targets, indicators, progress tracking, country validation
```

**After creating each course:**
1. Register it in the SQLite database as a project with `domain = 'education'`:
   ```sql
   INSERT INTO projects (project_id, title, domain, status, priority, external_path, created_at)
   VALUES ('{course-id}', '{Course Title}', 'education', 'active', 'medium',
           '{absolute path to course dir}', datetime('now'));
   ```
2. Add knowledge links connecting course lessons to library cards and competencies

---

## Task 3: Expand reading lists into annotated bibliographies

**Location:** `06_library/reading-lists/` — 5 files exist

**For each reading list:**

1. Add a **"If you only read 5 papers"** section at the very top — curated picks for someone short on time

2. **Add 2-3 sentence annotations** per paper explaining:
   - What the paper changed or contributed
   - Why it's still relevant today
   - What method/concept it demonstrates

3. **Organize by sub-topic** within each list (currently flat lists)

4. **Search the internet for papers published 2024-2026** and add 5-10 recent additions per list, especially:
   - New systematic reviews or meta-analyses
   - Updated WHO/CDC guidelines
   - Methodological advances (new R packages, new SaTScan features, etc.)

5. **Verify all DOI links are correct** — broken links are useless

---

## Task 4: Create epidemiology glossary

**Create:** `06_library/glossary.md`

**Format:**
```markdown
# Epidemiology & Public Health Glossary

## A

**Absolute risk** — The probability of an event occurring in a defined population over a specified time period. Also called cumulative incidence. See: [measures of disease frequency](methods/study-designs.md)

**Attack rate** — The cumulative incidence of disease in a defined population during a specific time period, typically used during outbreak investigations. Calculated as: (number of cases / population at risk) × 100.

**Attributable risk** — The difference in risk between exposed and unexposed groups. Also called risk difference (RD). Measures the excess risk due to exposure.

## B
...
```

**Requirements:**
- **200+ terms** covering: epidemiological measures, study designs, bias types, statistical terms, surveillance terminology, public health concepts, diagnostic test terms, spatial epi terms
- Each definition: 1-3 concise sentences
- Where relevant: link to the Metis library card that covers the concept in depth
- Include formulas for quantitative terms (OR, RR, NNT, sensitivity, specificity, etc.)
- Alphabetically organized with letter headers

**Search the internet** for existing epidemiology glossaries to ensure completeness:
- CDC Principles of Epidemiology glossary
- Last JM "A Dictionary of Epidemiology" terms
- BMJ Clinical Evidence glossary
- WHO health topics glossary

---

## Task 5: Create news synthesis templates

**Location:** `08_system/templates/`

Create 3 markdown templates:

### Template 1: `daily-synthesis.md`
```markdown
# Metis Daily Synthesis — {{DATE}}

## World context
- {{bullet 1}}
- {{bullet 2}}
- {{bullet 3}}

## Research & science
- {{New papers or findings}}
- {{Method developments}}

## Epi intelligence
- {{Outbreak alerts}}
- {{WHO/CDC updates}}
- {{Surveillance reports}}

## Relevance to current projects
- {{How today's news connects to active projects}}

## Action items
- [ ] {{Any papers to read}}
- [ ] {{Any feeds to follow up}}

---
*Generated by Metis News Radar — {{TIMESTAMP}}*
```

### Template 2: `weekly-digest.md`
```markdown
# Metis Weekly Research Digest — Week {{WEEK_NUM}}, {{YEAR}}

## Top signals this week
1. {{Most important development}}
2. {{Second}}
3. {{Third}}

## New publications
| Paper | Journal | Relevance | Signal |
|-------|---------|-----------|--------|
| {{title}} | {{journal}} | {{high/med/low}} | {{brief note}} |

## Guidelines & policy updates
- {{WHO, CDC, ECDC updates}}

## Outbreak & surveillance watch
- {{Active outbreaks, case counts, trends}}

## Methods & tools
- {{New R packages, software updates, methodological papers}}

## PhD relevance
- {{How this week's developments connect to the thesis}}

## Recommended reading (pick 3)
1. {{Paper + why}}
2. {{Paper + why}}
3. {{Paper + why}}

---
*Generated by Metis — covers {{START_DATE}} to {{END_DATE}}*
```

### Template 3: `monthly-epi-report.md`
```markdown
# Metis Monthly Epidemiological Intelligence Report — {{MONTH}} {{YEAR}}

## Executive summary
{{3-5 sentence overview of the month's key developments}}

## Global health landscape
### Outbreak trends
{{Active outbreaks, new declarations, resolved events}}

### Policy & governance
{{WHO decisions, IHR events, funding changes}}

### NTD & elimination progress
{{Country validations, case milestones, new tool approvals}}

## Research landscape
### Key publications
{{5-10 most important papers of the month}}

### Methodological advances
{{New approaches, software, guidelines}}

## Implications for current work
### PhD
{{How the month's events affect thesis work}}

### Projects
{{Implications for active projects}}

## Knowledge gaps identified
- {{Questions raised by this month's events that need investigation}}

## Next month outlook
- {{Upcoming conferences, expected publications, policy decisions}}

---
*Generated by Metis — {{MONTH}} {{YEAR}} report*
```

---

## Task 6: Agent system prompt audit for open-source readiness

**Location:** `02_agents/` — 17 agent directories, each with `system-prompt.md` and `contract.md`

**For EACH agent:**

1. **Read** the current system-prompt.md and contract.md

2. **Replace HAT-specific language** with generic phrasing:
   - "sleeping sickness" → "the user's disease focus" or "the target disease"
   - "DRC" → "the user's study area"
   - "T.b. gambiense" → remove or generalize
   - "TRYPELIM" → "the user's surveillance data system"
   - Keep HAT as ONE EXAMPLE among many, not the only focus

3. **Add a "Configurable context" section** to each system prompt:
   ```markdown
   ## Configurable context
   This agent adapts to the user's research focus. The current configuration is:
   - Disease focus: [loaded from metis-config]
   - Study area: [loaded from metis-config]
   - Institution: [loaded from metis-config]
   - Career stage: [loaded from metis-config]
   ```

4. **Ensure consistent recording convention** across all agents:
   ```markdown
   ## Recording convention
   All substantive work must be recorded:
   - Output files → `07_outputs/reviews/{agent-slug}/{YYYY-MM-DD}_{task-slug}.md`
   - Database log → `log_agent_run(paths, "{slug}", "summary", "input", "output")`
   - Ideas extracted → Ideas table with domain and feasibility
   - Tasks created → Tasks table with agent as owner
   ```

5. **Add 3-5 example interactions** to each system prompt showing how a user would invoke the agent and what it would do. Format:
   ```markdown
   ## Example interactions

   **User:** Review my study design for passive case detection analysis
   **Agent:** [asks clarifying questions about: study type, denominator, case definition, time period, geographic scope, potential biases]

   **User:** Is my sample size adequate?
   **Agent:** [asks about: expected prevalence, desired precision, design effect, available resources]
   ```

6. **Ensure all agents reference Metis** (not Monia) and describe themselves as part of "the Metis research team"

**Agents to audit (in this order — most used first):**
1. monia/ (Metis herself)
2. epidemiologist/
3. methods-coach/
4. librarian/
5. writing-partner/
6. phd-architect/
7. software-engineer/
8. meeting-memory/
9. news-radar/
10. news-aggregator/
11. ux-engineer/
12. dashboard-engineer/
13. builder/
14. presentation-maker/
15. learning-coach/
16. career-coach/

---

## REMINDER: Update the tracker after EVERY task

After completing each task (or even sub-task), update:
`/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/monia-second-brain/01_control-room/implementation-plan-phase2.md`

Mark items as done with dates. If you run out of tokens mid-task, note EXACTLY where you stopped (e.g., "Expanded 7/12 epidemiology-foundations lessons, stopped at lesson 08").

---

## Context about the user

- Epidemiologist at ITM Antwerp working on sleeping sickness (HAT)
- PhD in progress on elimination/post-elimination surveillance
- All skill domains at beginner level — the courses need to be genuinely educational
- Uses R, Zotero, Claude Desktop, WSL2
- Languages: English, Dutch
- Wants Metis to become open-source for any epi/PH researcher
- Does NOT want emoji in any files
- Prefers concise, scannable content over walls of text
