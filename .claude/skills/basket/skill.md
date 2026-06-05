---
name: Basket Intake
description: "basket, process basket, sort my documents, I dropped files, what's in the basket, file these documents, intake, route my documents, basket intake, organise dropped files, promote basket, tell metis what these are, sort documents into folders"
effort: normal
complexity: standard
---

## Purpose

The **basket** is a flat drop-zone (`basket/`) where you toss any document — papers, reports, scripts, meeting notes, datasets, course material — without filing it. This skill processes the basket: it works out *what each file is*, asks you to confirm with a short questionnaire, and **promotes each file to the right input folder** so the rest of Metis (Librarian, knowledge layer, Data Analyst…) can use it.

You drop; Metis sorts. Nothing leaves your machine.

## Hard rule

**Never read, list, or touch `basket/private/`.** It holds personal/patient data that AI tools must not access. `list_basket()` already excludes it — keep it that way.

## What to do when invoked

**Step 1 — List the basket.** Call `list_basket()` to get the items (private/ is auto-excluded). If empty, say so and stop. Optionally `scan_folder_for_intent(folder_path="basket")` for a quick read of the collection.

**Step 2 — Classify each item.** For each file, infer its type from name + a short `read_file()` peek (first ~40 lines; skip binary). Propose a classification and a destination:

| Looks like | Type | Destination |
|---|---|---|
| Journal article / report (`.pdf`) | literature | `inputs/literature/<topic>/` (or a background layer `knowledge/domains/<layer>/`) |
| Script / analysis (`.R`, `.py`, `.qmd`, `.do`) | code | `inputs/code/` |
| Meeting note / transcript | meeting | `inputs/meetings/` |
| Course / teaching material | course | `knowledge/courses/<course>/` |
| **Dataset** (`.csv`, `.xlsx`, `.sav`, `.dta`) | **data — check first** | run `check_data_safety` on a header peek; if CONFIDENTIAL/SENSITIVE → **route to `basket/private/`**, never an indexed folder; else a data folder |
| Personal / identifiable | private | `basket/private/` (you move it; never index) |

**Step 3 — One short questionnaire, then confirm.** Don't ask per-file if you can batch. Present the proposed routing as a table and ask **only what you can't infer**, e.g.:
- *"3 PDFs look like HAT papers — file under `inputs/literature/sleeping-sickness/`? (y / different topic)"*
- *"`screening_2024.csv` is a dataset — it scanned as CONFIDENTIAL. Move to `basket/private/` (kept off the AI)? (y/n)"*
- *"`model.R` → `inputs/code/`? (y/n)"*
Keep it to 1–3 questions. Default to the inferred destination on "y".

**Step 4 — Promote.** For each confirmed item: `promote_basket_item(source_path="<abs path in basket>", target_path="<destination>/<filename>")`. Create the destination subfolder implicitly via the target path. Report what moved where.

**Step 5 — Offer the obvious next step.** After promoting:
- PDFs → "Index these into your library/knowledge layer? (`/librarian` or `build_pdf_knowledge_db`)"
- Dataset (non-sensitive) → "Profile it? (`/data-analyst`)"; sensitive → "Use `/safe-analysis` — it never sends the data."
- Meeting note → "Structure it? (`/meeting-memory`)"

## Output format
```
── BASKET PROCESSED ──────────────────────────────
Moved 5 of 6 items:
  → inputs/literature/sleeping-sickness/   3 papers
  → inputs/code/                           model.R
  → basket/private/                        screening_2024.csv  (CONFIDENTIAL — kept off the AI)
Left in basket: notes.txt  (unclear — tell me what it is)

Next: index the 3 papers with /librarian?
```

## Principles
- **Infer, then confirm — don't interrogate.** Batch by type; ask only the ambiguous bits.
- **Sensitive data is sacred.** Any dataset gets a `check_data_safety` peek before it lands anywhere indexable; CONFIDENTIAL/SENSITIVE → `basket/private/`.
- **Reversible.** Promotion moves files; if a target is wrong, it can be moved again. Never delete.
- **`basket/` is removable.** No DB rows. Don't create dependencies on it.

## Collaboration
Data Guardian (classify datasets) · Librarian (index promoted papers) · Data Analyst (profile datasets) · Meeting Memory (structure notes) · Content Harvester (extract from odd formats).
