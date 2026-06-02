# How to add a new project to the Metis system

Follow these steps every time you start a new research, software, or education project.

---

## Step 1 — Create a project card

Copy this template to `04_projects/active/[project-name].md`:

```markdown
---
project_id: your-project-id        # lowercase, hyphens, no spaces
title: Your Project Title
domain: your-domain                 # or: education, software, phd, personal
status: active                      # active | planned | blocked | done
priority: high                      # high | medium | low
external_path: C:\full\windows\path\to\project
github_url: pending                 # fill in after GitHub repo is created
---

# Your Project Title

One paragraph description.

## What it does
- ...

## Key scripts / files
- ...

## Open todos
- [ ] First thing to do
- [ ] Second thing to do

## Notes
- ...
```

---

## Step 2 — Set up git in the project folder

Open a terminal (Git Bash, WSL, or RStudio terminal):

```bash
cd "C:\path\to\your\project"

# If not already a git repo:
git init
git branch -m main

# Create a .gitignore — ALWAYS exclude data files
# Copy from an existing project or use the template below
```

### Standard .gitignore for R/epidemiology projects

```gitignore
# R session artifacts
.Rhistory
.RData
.Rproj.user/
*.Rproj

# Data files — keep local
*.csv
*.rds
*.xlsx
*.sav
*.dta
data/
1. Data/

# Shapefiles
*.shp
*.shx
*.dbf
*.prj

# OS
.DS_Store
Thumbs.db
~$*
```

```bash
git add README.md .gitignore
git add *.R          # or specific scripts
git commit -m "Initial commit: scripts and configuration"
```

---

## Step 3 — Create the GitHub repository

1. Go to https://github.com/<your-github-username>
2. Click **New repository**
3. Name it (e.g. `My_Research_Project`)
4. Set to **Private** (for research data projects) or Public (for teaching)
5. Do NOT initialise with README (you already have one)
6. Click **Create repository**
7. Copy the SSH URL: `git@github.com:<your-github-username>/My_Research_Project.git`

```bash
git remote add origin git@github.com:<your-github-username>/My_Research_Project.git
git push -u origin main
```

---

## Step 4 — Register the project with Metis

Use the MCP tool (in Claude) — no manual file editing:

```
create_project_full(
  name="Your Project Title",
  category="Article",          # Article | Grant | Teaching | Software | Review | …
  folder="C:/full/path",       # optional — local project folder to track
  next_step="First thing to do"
)
```

`create_project_full` writes the project record, links the folder (so the
Planning tab tracks it), and — if a folder is given — drops a `CLAUDE.md` into it.
Add tasks with `create_task(...)`. You can also do all of this from the dashboard
**Work** tab or the setup wizard at `http://localhost:8080/setup`.

---

## Step 5 — Daily git workflow

```bash
# End of every work session:
git add .
git commit -m "Brief description of what you did"
git push

# Start of session (if working from multiple machines):
git pull
```

The Metis dashboard Control Room will show a **red dot** when commits or pushes are pending. Click **Refresh** to update the status.

---

## Existing projects

Update this table with your own projects as you add them.

| Project | GitHub | Branch |
|---|---|---|
| My Research Project | https://github.com/<your-github-username>/my-research-project | `main` |
