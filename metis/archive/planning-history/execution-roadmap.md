# Execution Roadmap

This roadmap defines how to continue the PhD workstream and how to build the agent ecosystem around Metis.

The guiding principle is:

- do not try to build every agent at once
- first build the minimum infrastructure that lets later agents share context
- prioritize agents that improve retrieval, triage, and decision support

## Part I: PhD continuation plan

### Phase 1: Define the PhD spine

Goal:

- turn the existing framework note into a stable central research spine

Steps:

1. Convert the current central PhD document into a structured anchor note.
2. Define the working thesis title and central research question.
3. Separate current papers from future candidate papers.
4. Confirm the six-paper logic:
   - Article 1: historical risk mapping and foci
   - Article 2: current surveillance system quality or operational limitations
   - Article 3: diagnostic test performance and quality assurance
   - Article 4: passive screening system pilot and feasibility
   - Article 5: targeting health facilities for post-elimination surveillance
   - Article 6: sampling interval and modelling logic
5. Mark which papers are already active, which are conceptual, and which still need methodological definition.

Deliverables:

- stable central PhD anchor file
- article map
- open questions list

### Phase 2: Build the PhD evidence map

Goal:

- connect literature, datasets, methods, and unresolved questions to each paper

Steps:

1. Refine the seeded PhD literature subset.
2. Tighten the split between Article 2 and Article 4.
3. Build a dedicated shortlist for Article 5.
4. Link key papers to the central anchor note.
5. Identify missing literature or methods per article.
6. Create a `needed next` list for each article.

Deliverables:

- article-specific paper lists
- methods gap list
- missing-source list

### Phase 3: Build the methods plan

Goal:

- define which analytical and methodological skills are needed to finish the current paper program

Steps:

1. List the methods already mastered.
2. List the methods still needed.
3. Prioritize them by immediate usefulness.
4. Link each method to one or more papers.
5. Create a small learning backlog for statistics, sampling, and modelling where needed.

The methods layer should explicitly include:

- multilevel analysis
- spatial scan statistics
- risk mapping
- spatial epidemiology
- HPC-supported analysis workflows

Deliverables:

- PhD methods roadmap
- methods-to-article dependency map

### Phase 4: Build the writing and supervision workflow

Goal:

- make the PhD progress operational rather than conceptual only

Steps:

1. Create article status boards.
2. Create a supervision meeting workflow.
3. Store meeting decisions and convert them into article tasks.
4. Add versioned outlines and revision plans.
5. Add a `next writing move` field for each paper.

Deliverables:

- article progress board
- supervision memory workflow
- revision backlog

### Phase 5: Build the post-elimination framework note

Goal:

- let the thesis grow into a reusable framework beyond the current papers

Steps:

1. Maintain one evolving framework note for post-elimination surveillance.
2. Record competing operational models.
3. Track unresolved uncertainties:
   - future screen-and-treat evidence
   - funding constraints
   - health-system capacity
   - surveillance interval assumptions
4. Add cross-disease analogies from other elimination programs.

Deliverables:

- reusable framework note
- broader research agenda

## Part II: Agent build plan

### Build philosophy

Agents should be built in layers:

1. Orchestration
2. Intake and retrieval
3. Domain intelligence
4. Execution support
5. Presentation and interface support

This avoids building specialist agents before they have structured context to work with.

## Layer 1: Core infrastructure agents

### 1. Metis

Role:

- general manager
- intake router
- dashboard owner
- coordinator of all other agents

Why first:

- without Metis, the rest stay disconnected

Minimum viable responsibilities:

- receive new input
- ask whether to capture, deep-search, or brainstorm
- route items to the right domain
- surface daily recommendations

Dependencies:

- folder structure
- metadata layer
- dashboard shell

### 2. Librarian

Role:

- manages literature, updates, metadata, and relevance

Why second:

- your system depends on external scientific awareness
- many later agents need structured literature

Minimum viable responsibilities:

- scan for new papers on demand
- produce relevance notes
- maintain the paper catalogue
- link papers to PhD articles and projects

Dependencies:

- inventory and metadata tables
- source watchlists

### 3. Meeting Memory

Role:

- transcribes, summarizes, extracts decisions, and prepares next-meeting briefs

Why third:

- meetings are a major recurring source of operational knowledge

Minimum viable responsibilities:

- store recordings and transcripts
- extract decisions and actions
- generate briefings for follow-up meetings

Dependencies:

- local transcription workflow
- meeting template

## Layer 2: PhD and research agents

### 4. PhD Architect

Role:

- maintains the thesis spine and article map

Why now:

- once Metis, Librarian, and Meeting Memory exist, the PhD agent can reason over actual structured context

Minimum viable responsibilities:

- maintain central thesis note
- identify missing methodological or conceptual links
- propose future paper directions

### 5. Writing Partner

Role:

- supports article drafting, restructuring, and journal-targeted revision

Minimum viable responsibilities:

- rewrite outlines
- build argument structures
- identify weak sections

Dependencies:

- PhD Architect
- paper-level metadata

### 6. Methods Coach

Role:

- supports statistics, sampling, modelling, and outbreak-relevant methods

Minimum viable responsibilities:

- explain and compare methods
- suggest methodological next steps
- map methods to article needs

Priority methods for your case should explicitly include:

- multilevel analysis
- spatial scan statistics
- HPC workflow support for heavier analyses

Dependencies:

- PhD methods backlog

## Layer 3: Epidemiology and technical agents

### 7. Risk Mapping Analyst

Role:

- supports spatial epidemiology, mapping logic, and focus delineation

Why after Methods Coach:

- risk mapping is a specialized execution layer built on top of the general methods layer

### 8. R Reviewer

Role:

- reviews R scripts, analytical logic, reproducibility, and code structure

Why later:

- you explicitly deprioritized code review relative to literature and research structure

### 9. Builder

Role:

- creates dashboards, apps, visualizations, and interfaces

Why here:

- once Metis and the knowledge model are stable, the Builder can create useful interfaces instead of speculative ones

### 10. Presentation Maker

Role:

- turns structured work into slide outlines and presentation assets

Why later:

- depends on structured project and article data

## Layer 4: Strategic awareness agents

### 11. News Radar

Role:

- monitors world developments relevant to your projects and interests

Why after core research agents:

- it needs a mature control room to avoid becoming noise

Minimum viable responsibilities:

- daily brief
- weekly brief
- project-relevance tagging
- weak-signal highlighting

### 12. Learning Guide

Role:

- tracks Arabic, coding, methods, and other learning paths

Why later:

- useful, but less foundational than the research and control layers

## Part III: Recommended build order

### Stage A: Foundation

1. Metis
2. Librarian
3. Meeting Memory

### Stage B: PhD intelligence

4. PhD Architect
5. Writing Partner
6. Methods Coach

### Stage C: Specialist execution

7. Risk Mapping Analyst
8. R Reviewer
9. Builder
10. Presentation Maker

### Stage D: Strategic overlay

11. News Radar
12. Learning Guide

## Part IV: Immediate next actions

If we continue in the best order, the next concrete tasks should be:

1. Define Metis's operating contract.
2. Build the Librarian workflow around the seeded literature catalogue.
3. Design the meeting transcription and extraction pipeline.
4. Refine the central PhD anchor note using the current framework document.
5. Start building the dashboard shell with:
   - Control Room
   - Library
   - PhD
   - Meetings
   - Ideas

## Part V: What not to build yet

- full autonomous action-taking
- R code review automation
- presentation generation
- broad learning tracker
- too many separate interfaces

These should wait until the knowledge layer and control room are stable.
