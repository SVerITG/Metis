# MLM Course — Software Engineer Context

**Invocation:** `/software-engineer <task title>`
**Repository:** `SVerITG/MLM_course`
**Local path:** `C:\Users\sverschaeve\OneDrive - ITG\Documents\9. Education\1. Multilevel Analysis`

---

## Project overview

A multilevel analysis (MLM) teaching course with two components:
1. **mlm-app** — Node.js/Express interactive Shiny-like web application
2. **Quarto course** — 25+ `.qmd` files forming the written course content

---

## Architecture

### mlm-app (Node.js)
- `server.js` — Express server entry point
- `migrate_db.js` — database migration (SQLite)
- `lessons.json` — lesson definitions (title, content, exercises)
- Launch: `cd mlm-app && node server.js`

### Quarto course
- 25+ modified `.qmd` files (lectures, exercises, solutions)
- Render: `quarto render` from course root
- Likely uses `_quarto.yml` for project config

---

## Known tasks

- **Check mlm-app Shiny app status** — verify `server.js` runs, check if `migrate_db.js` needs running
- **Connect spatial scan statistics** — link spatial stats material (SaTScan) to MLM content
- **Review 25 modified Quarto files** — large diff, prioritise by last-modified date
- **Consider GitHub** — push course scripts for citability

---

## Key considerations

- Course combines education (MLM statistics) + research (HAT clustering/spatial analysis)
- `lessons.json` drives the mlm-app lesson list — any new lessons need entries here
- Quarto files may have hardcoded paths or references to local data files
- The spatial scan module bridges this course with the HAT Risk Mapping project

---

## Useful commands

```bash
# Start Node.js app
cd "C:/Users/sverschaeve/OneDrive - ITG/Documents/9. Education/1. Multilevel Analysis/mlm-app"
node server.js

# Run DB migration (if needed)
node migrate_db.js

# Render Quarto course
cd "C:/Users/sverschaeve/OneDrive - ITG/Documents/9. Education/1. Multilevel Analysis"
quarto render

# Check git status
git -C "C:/Users/sverschaeve/OneDrive - ITG/Documents/9. Education/1. Multilevel Analysis" status
```

---

## Links to other projects

- **HAT Risk Mapping**: spatial scan statistics appear in both projects
- **Methods Coach**: MLM course content should be reviewed against methods coaching materials
- **Monia Library**: course references appear in literature seeded files
