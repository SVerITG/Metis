# Software Engineer Workflows

## Workflow 1: R script review (single file)

```
INPUT: path to R script
1. Read file fully
2. Run security checklist (system-prompt)
3. Check for: hardcoded paths, missing seeds, base-R anti-patterns
4. If Shiny module: check reactive correctness
5. Return: Critical / Warning / Suggestion list
6. Append to patterns.md if any non-obvious finding
OUTPUT: structured findings, optionally patched file
```

## Workflow 2: R Shiny dashboard bug fix (user projects)

> Note: this applies to a **user's own R Shiny project**. The **Metis dashboard
> itself is FastAPI + HTMX** (`system/app-py/`) — for that, route to Dashboard Engineer.

```
INPUT: bug description + affected module name
1. Read app.R and the named module
2. Reproduce the logic path in your head
3. Identify minimal change
4. Implement fix
5. Describe how to verify
OUTPUT: patched file + verification steps
```

## Workflow 3: New dashboard feature

```
INPUT: feature description
1. Complexity check — is this trivial / medium / complex?
2. If complex: write scope doc, wait for user confirmation
3. Implement: data layer (data_store.R or SQLite) first
4. Then: server logic in module
5. Then: UI in module
6. Update app.R only if new tab/module is needed
OUTPUT: new or modified module files
```

## Workflow 4: Python script or MCP server review

```
INPUT: path to .py file or MCP server directory
1. Read all relevant files
2. Run security checklist with Python focus
3. Check virtual environment usage
4. If MCP server: validate all tool input boundaries
OUTPUT: findings document
```

## Workflow 5: Batch R audit

```
INPUT: folder path containing R scripts
1. List and categorise all scripts
2. Apply single-file review to each (or group similar ones)
3. Aggregate findings by severity
4. Produce prioritised report at outputs/reviews/[date]-r-audit.md
OUTPUT: prioritised audit report
```

## Workflow 6: Escalate to ruflo swarm

```
TRIGGER: 10+ files, greenfield app, externally deployed security audit
1. Confirm with user before activating
2. Run:
   npx ruflo@latest swarm init --topology hierarchical --max-agents 5
   npx ruflo@latest agent spawn --type reviewer --name lead
   npx ruflo@latest agent spawn --type coder --name implementer
   npx ruflo@latest swarm start --objective "[stated objective]"
3. Collect ruflo output, summarise for user
OUTPUT: ruflo swarm report + summary
```
