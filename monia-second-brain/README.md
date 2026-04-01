# Monia Second Brain

This is the root folder for a local-first personal knowledge management system.

The current design assumes:

- One unified system, not a hard split between life and work.
- Cross-linking is a core feature, so domains stay connected.
- Sensitive material can still be isolated by folder, permissions, or agent rules.
- Local-first is the default operating mode.
- Internet use should be permissioned, except for explicitly external functions such as literature surveillance and news monitoring.
- Literature, code, meetings, ideas, writing, and dashboards all feed the same knowledge layer.
- The system should evolve toward a rich ontology, not just folders and tags.

## Folder logic

- `00_inbox`: fast capture for notes, ideas, clips, transcripts, and unsorted material.
- `01_control-room`: dashboard material, daily briefs, weekly reviews, and Monia summaries.
- `02_agents`: agent definitions, prompts, runbooks, and operating policies.
- `03_domains`: long-lived areas of responsibility and identity.
- `04_projects`: active and time-bounded work.
- `05_sources`: raw inputs such as papers, meetings, web clips, datasets, code, and news.
- `06_library`: cleaned and structured knowledge extracted from sources.
- `07_outputs`: articles, slides, dashboards, apps, and other deliverables.
- `08_system`: templates, ontology, workflows, and system operations.
- `09_archive`: inactive material kept for retrieval.

## Why this structure

This system is intentionally not organized as `life/` and `work/` at the top level.
That split looks simple but becomes brittle for your use case:

- PhD, epidemiology, AI, methods, and personal learning overlap heavily.
- You want cross-pollination across diseases, tools, and ideas.
- You want one dashboard and one manager agent to reason across everything.

Instead, the system separates:

- `domains`: what stays true over time
- `projects`: what changes and finishes
- `sources`: what comes in
- `library`: what has been understood
- `outputs`: what leaves the system

This makes retrieval and automation cleaner.

## Internet and privacy rule

The baseline rule is:

- Work locally first.
- Ask permission before general internet use.
- Allow controlled internet access for the library, literature surveillance, and news radar functions because those depend on external sources.
- If a source cannot be directly accessed, provide the link and context so the user can retrieve it manually.

## First domains

- `phd`
- `sleeping-sickness`
- `ai-and-development`
- `personal-learning`
- `career-and-eu`

These are placeholders and will be refined after the next planning round.
