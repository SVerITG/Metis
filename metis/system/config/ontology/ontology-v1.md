# Ontology V1

This is the first practical ontology for the Metis second-brain system.

It is designed around your real use case:

- gambiense HAT in the DRC
- elimination and post-elimination surveillance
- PhD article program
- literature intelligence
- meetings and operational decisions
- dashboards and analytical work

## Design principle

Do not rely on folders alone.

Folders are useful for browsing and storage, but the actual intelligence layer should come from entities, metadata, and relationships.

## Core entity types

### Scientific domain

- `Disease`
- `Pathogen`
- `Vector`
- `Intervention`
- `SurveillanceMode`
- `EliminationPhase`
- `DiagnosticTest`
- `Treatment`
- `Method`
- `Model`
- `StatisticalConcept`
- `ComputeEnvironment`
- `Indicator`
- `Geography`
- `Focus`
- `Facility`
- `Village`
- `Population`

### Knowledge objects

- `Source`
- `Paper`
- `Report`
- `Guideline`
- `Dataset`
- `Codebase`
- `Script`
- `Figure`
- `Protocol`
- `Meeting`
- `Transcript`
- `Idea`
- `Question`
- `Decision`

### Work objects

- `Domain`
- `Project`
- `Article`
- `ThesisSection`
- `Task`
- `Workflow`
- `Dashboard`
- `App`

### Actors

- `Person`
- `Organization`
- `Program`
- `Team`

## Required metadata by entity

### Paper

- title
- authors
- year
- publication
- DOI or PMID
- local file path
- Zotero key if available
- source type
- access status
- language
- abstract or summary
- disease tags
- method tags
- geography tags
- surveillance tags
- article relevance
- PhD relevance
- status

### Article

- title
- working status
- target journal
- lead question
- linked datasets
- linked methods
- linked papers
- linked decisions
- linked figures

### Meeting

- date
- participants
- organization
- related project
- related article
- recording path
- transcript path
- decisions
- actions
- unresolved questions

### Geography

- country
- province
- health zone
- village
- coordinates where relevant
- historical risk status
- current surveillance status

## Relationships

### Scientific relationships

- `caused_by`
- `transmitted_by`
- `targets`
- `diagnosed_by`
- `treated_by`
- `measured_by`
- `modeled_by`
- `located_in`
- `part_of_focus`
- `belongs_to_elimination_phase`

### Knowledge relationships

- `describes`
- `evaluates`
- `supports`
- `contradicts`
- `extends`
- `summarizes`
- `derived_from`
- `attached_to`
- `mentions`

### Workflow relationships

- `belongs_to_domain`
- `belongs_to_project`
- `runs_on`
- `supports_article`
- `supports_thesis_section`
- `requires_decision`
- `produced_in_meeting`
- `implemented_by`
- `tracked_in_dashboard`

## High-priority controlled vocabularies

The first controlled vocabularies should be:

- disease subtype
- geography hierarchy
- surveillance mode
- elimination phase
- diagnostic test
- intervention type
- methodology
- compute environment
- article status
- evidence type

Priority methodology terms should include at least:

- multilevel analysis
- spatial scan statistics
- risk mapping
- spatial epidemiology
- HPC-supported workflow

## PhD-centered ontology view

The PhD program appears to organize around this spine:

- historical and contemporary risk structure
- performance and limitations of the current surveillance system
- building blocks for a passive-dominant post-elimination surveillance architecture
- sampling and revisit logic for resurgence detection

This suggests a central chain:

`Historic risk and foci`
-> `Current surveillance quality and coverage`
-> `Passive system redesign`
-> `Facility targeting strategy`
-> `Sampling interval strategy`
-> `Operational post-elimination framework`

## Why this matters

This ontology lets one paper belong simultaneously to:

- `Diagnostics`
- `Passive surveillance`
- `DRC`
- `Post-elimination relevance`
- `Article 3`
- `Quality assurance`

That is exactly why the ontology must sit above the folder tree.
