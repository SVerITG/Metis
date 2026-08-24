---
name: Code Intake
description: "code intake, scan scripts, analyze R scripts, register code, data dictionary from scripts, code to metadata, extract variables from code, scan my scripts, parse my R code, index my code, register my scripts"
effort: normal
complexity: standard
---

## Purpose

Extract metadata from R and Python scripts without ever seeing the data. This is the "send code, not data" pipeline for projects: Metis reads the code (safe) to learn file paths, variables, and packages, generates tailored profiling scripts the user runs locally, and builds a per-project data dictionary — all without the AI ever touching any data.

The end goal: Metis can scaffold new scripts (dashboards, analyses, Table 1) using exact variable names, paths, and coding conventions from the project.

## The workflow (5 steps)

### Step 1 — Locate scripts

Ask the user where their scripts are. Default: `inputs/code/`. Accept any folder path.

```
scan_project_scripts(folder_path="<path>", project_id="<project>")
```

If the user hasn't specified a project, ask which project this belongs to (check `get_project_status()` for active projects).

### Step 2 — Present findings

Show the summary table from `scan_project_scripts`:
- Scripts found and analyzed
- Packages used
- Datasets detected (file reads)
- Variables extracted

Highlight anything interesting: missing packages, inconsistent naming, unusually large/small scripts. If `source()` dependencies are found, mention the dependency chain.

### Step 3 — Generate profiling scripts

For each detected dataset, offer to generate a safe profiling script:

```
generate_profiling_script(
  dataset_name="<name>",
  project_id="<project>",
  language="r",           # or "python"
  dataset_path="<path>"   # from the scan results
)
```

Explain clearly:
- The script runs on their machine
- Only aggregates are computed (no row-level data)
- Output is structured JSON ready for Metis to ingest

### Step 4 — Receive profiling output

When the user shares the JSON path after running the profiling script:

```
ingest_profiling_output(
  json_path="<path>",
  dataset_name="<name>",
  project_id="<project>"
)
```

Confirm: how many variables were registered, any anomalies (high missingness, inconsistent coding, unexpected types).

### Step 5 — Ready to scaffold

Confirm the data dictionary is registered. Offer next steps:
- `scaffold_script(goal="...", project_id="...", language="r")` — for new analyses
- `search_code_repository(query="...")` — to find existing patterns
- Suggest specific things they could build: "Table 1", "dashboard", "analysis pipeline"

## Safety contract

- **Never ask the user to paste data.** All data insight comes from running profiling scripts locally.
- **If the user shares raw data, stop.** Redirect them to `generate_profiling_script()`.
- **Only aggregates are acceptable:** variable names, types, unique counts, ranges, missingness percentages, value frequencies (capped at 30 levels).

## Collaboration

Software Engineer (code analysis) + Data Guardian (safety gate) + Data Analyst (profiling) + Methods Coach (if variables suggest a statistical context).

## Recording

After the workflow:
```
log_agent_run(agent_slug="software-engineer", task_summary="Code intake: scanned N scripts, registered M variables for project X")
write_reflexion(session_id="...", agent_slug="software-engineer", went_well="...", could_improve="...", missing_context="...", tool_wishes="...")
```
