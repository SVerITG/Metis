# Initial Strategy

## First-pass architecture

The second brain should have five connected layers:

1. Capture
   - Inbox notes
   - Meeting notes and transcripts
   - PDFs and literature metadata
   - R scripts and project code
   - Web clips and news items

2. Triage and enrichment
   - Metis routes new material
   - The librarian extracts metadata, tags, and summaries
   - Specialist agents create links to projects, diseases, methods, and people

3. Knowledge layer
   - Concepts
   - Disease areas
   - Methods and statistics
   - People and organizations
   - Bridge notes connecting fields

4. Execution layer
   - PhD article pipeline
   - Epidemiology and surveillance projects
   - Risk mapping work
   - App and dashboard development
   - Presentation preparation

5. Review and control layer
   - Daily brief
   - Weekly review
   - Open decisions
   - Weak signals and trend radar
   - Recommended next actions

## Confirmed operating principles

- Local-first by default
- Permissioned internet access for general searches
- Built-in internet access for literature surveillance and news discovery
- Rich ontology and structured metadata from the start
- Scan-for-new-material should be a deliberate button in the dashboard
- New ideas should trigger a choice between capture only, deep search, or brainstorm mode

## Agent map

- `Metis`
  - General manager and orchestrator
  - Routes information, highlights priorities, and maintains system coherence

- `Librarian`
  - Manages literature, disease surveillance sources, elimination references, and topic coverage
  - Tracks what is new, what is missing, and what is relevant
  - If direct access to an article is blocked, returns the link and why it matters

- `PhD Architect`
  - Maintains the central research question, article map, and unifying thesis spine

- `R Reviewer`
  - Reviews scripts, reproducibility, style, package use, and analytical logic

- `Methods Coach`
  - Focuses on statistics, sampling, outbreak methods, causal inference, and study design

- `Risk Mapping Analyst`
  - Specializes in spatial workflows, mapping logic, and geospatial evidence organization

- `Writing Partner`
  - Supports article drafting, revision planning, argument structure, and journal targeting

- `Meeting Memory`
  - Summarizes meetings, extracts actions, and prepares briefing notes before follow-up meetings

- `News Radar`
  - Produces daily and weekly briefs across AI, science, geopolitics, humanitarian work, markets, and sleeping sickness

- `Builder`
  - Designs dashboards, apps, interfaces, and data products

- `Presentation Maker`
  - Transforms structured knowledge into slide outlines and decks

- `Learning Guide`
  - Tracks Arabic, coding, methods, and other skill-building plans

## Design choices to validate

- Keep one master knowledge system, with privacy controls inside it.
- Use domains and projects as the main structural split, not life versus work.
- Keep raw sources separate from cleaned library notes.
- Make the PhD a central domain, not just another project.
- Use one central dashboard with focused tabs rather than many disconnected tools.
- Treat the dashboard as a control room plus specialized pages, not as a single overloaded screen.

## Control-room structure

The dashboard should be one application with multiple pages or tabs:

1. `Control Room`
   - New research
   - New global developments relevant to your work
   - Project to-do overview
   - Open decisions
   - Recommended actions from Metis
   - Weak signals and unexpected items worth attention

2. `Library`
   - New papers
   - Coverage gaps
   - Search by disease, method, geography, intervention, surveillance phase, and article status
   - Manual `Scan for new material` trigger

3. `PhD`
   - Thesis spine
   - Current papers
   - Candidate paper ideas
   - Methods to learn
   - Unresolved conceptual questions

4. `Projects`
   - Active projects, deadlines, next actions, and linked sources

5. `Meetings`
   - Meeting memory
   - Briefing notes
   - Follow-up actions

6. `Ideas`
   - Inbox
   - Explore now
   - Deep search
   - Brainstorm mode

7. `Builder`
   - Dashboards
   - Apps
   - Visualizations
   - Technical backlog

8. `Learning`
   - Arabic
   - Coding
   - Statistics and outbreak methods
   - Other skills

## Rich ontology direction

The ontology should likely include at least these entity types:

- Disease
- Pathogen
- Geography
- Intervention
- Surveillance mode
- Elimination phase
- Study
- Dataset
- Method
- Statistical concept
- Script
- Project
- Article
- Meeting
- Person
- Organization
- Tool
- Idea
- Question

Relationships should include:

- `informs`
- `uses_method`
- `uses_dataset`
- `belongs_to_project`
- `supports_article`
- `relates_to_disease`
- `relates_to_geography`
- `precedes`
- `contradicts`
- `extends`
- `mentions`
- `requires_decision`

## Meaning of day one

`Day one` means the first usable version of the system.
It answers the question: what must work first before the system becomes useful enough to use daily?

For your case, the likely day-one priorities are:

- Literature and PDF intake
- Structured sleeping-sickness and PhD knowledge capture
- Project overview
- Idea inbox with exploration options
- Manual scan button for new material
- Control-room summary

## Updated decisions from planning

- PDFs are a core source and must be preserved as data sources, not just summarized.
- The library is centered on sleeping sickness, adjacent research, elimination, post-elimination surveillance, and methods relevant to your work.
- Zotero should be integrated if possible, but the system should not be limited by Zotero's model.
- The Librarian should actively surface related new papers and provide acquisition links when access is blocked.
- New-material scanning should be user-triggered from the dashboard.
- The Control Room should prioritize new research, new developments affecting projects, and project to-dos.
- Idea intake should branch into `explore now`, `deep internet search`, or `brainstorm mode`.
- R code review is lower priority and can be implemented after the literature, dashboard, and meeting workflows.

## Literature source watchlist

The Librarian should scan a layered watchlist rather than a single database:

### Core bibliographic sources

- PubMed
- Europe PMC
- Crossref
- Google Scholar

### Domain and programmatic sources

- WHO HAT and NTD pages
- WHO reports and guidance related to HAT, elimination, and surveillance
- Institutional and program reports connected to HAT in DRC
- African Union and related trypanosomiasis networks where relevant

### Journal and article sources

- PLOS Neglected Tropical Diseases
- The Lancet and Lancet Infectious Diseases
- Tropical Medicine and International Health
- Clinical Infectious Diseases
- Transactions of the Royal Society of Tropical Medicine and Hygiene
- Infectious Disease and epidemiology journals that regularly publish HAT, surveillance, or diagnostic work

### Preprints and grey literature

- medRxiv
- bioRxiv
- Research Square
- WHO IRIS and similar repositories when accessible
- NGO, donor, and ministry reports

### Related-topic expansion

The Librarian should also watch:

- elimination and post-elimination surveillance
- passive case detection
- screening-test performance
- quality assurance for diagnostics
- spatial epidemiology and risk mapping
- sampling, multilevel models, and implementation research
- adjacent NTD elimination programs for cross-pollination

## Literature organization recommendation

When you provide the full literature base, I should first inspect it and then propose a migration plan before creating a final folder structure.

My likely recommendation will be:

- keep Zotero for reference management and citation workflows
- keep a local article store for files and controlled naming
- create a richer metadata layer outside Zotero for ontology, relationships, and research relevance

This means Zotero remains part of the system, but not the only source of truth for knowledge structure.

## Meeting transcription workflow

Recommended baseline workflow:

1. Record audio in a dedicated meeting app or device.
2. Save the audio file locally into the system.
3. Run local transcription.
4. Store:
   - raw audio
   - raw transcript
   - cleaned transcript
   - structured meeting note
   - extracted decisions and actions
5. Link the meeting to:
   - people
   - project
   - article
   - dataset
   - next meeting

### Local-first transcription recommendation

Preferred default:

- local Whisper-based transcription

Why:

- fits your privacy rule
- keeps sensitive meetings off cloud services
- works well as a backend step in an automated workflow

Suggested output objects per meeting:

- summary
- decisions
- action items
- deadlines
- open questions
- entities mentioned
- linked projects and articles
- follow-up briefing note for the next meeting

### Capture options

- Phone voice memo or recorder app if simple and reliable is the priority
- Desktop meeting recorder if you often work from a computer
- Dedicated hardware recorder if audio quality is critical

The best implementation choice depends on whether most meetings are:

- in person
- hybrid
- online calls
- field discussions

### Confirmed meeting requirement

Your system needs support for all three meeting modes:

- in-person
- online
- mixed or hybrid

So the eventual implementation should support:

- mobile capture for in-person meetings
- desktop capture for online calls
- a consistent post-processing pipeline that treats all recordings the same after capture

## Literature storage decision

When you provide the full literature library, the system may copy it locally into the second-brain structure and reorganize it for long-term maintenance.

That means the literature layer should be designed to:

- hold a full local copy
- accept new documents over time
- preserve provenance
- avoid losing the relationship to Zotero entries

## Librarian behavior for new papers

When the Librarian finds a new relevant paper, it should:

- produce a short relevance note
- explain why it matters to your work
- offer a download or acquisition option
- link it to the relevant disease, method, project, and article where possible

## PhD center

The center of the PhD page should be a unifying document that:

- connects the three current papers
- frames the broader research program
- stores candidate future papers and directions
- helps refine the final thesis topic over time
