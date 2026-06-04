---
name: Safe Analysis
description: "sensitive data, patient data, analyze without sharing, safe analysis, don't send my data, confidential dataset, analyze locally, keep data local, work with patient data, GDPR-safe analysis, de-identify, metadata only, send code not data, analyse my data safely, dashboard from sensitive data"
effort: normal
complexity: standard
---

## Purpose

The safe way to use Metis on sensitive data — patient records, identifiable surveillance data, embargoed or unpublished datasets. **The raw data never enters a prompt.** Metis writes the analysis code, *you* run it on your own machine, and only derived, non-identifiable outputs (column names, value counts, summary tables, model results) come back. Claude reasons over the **shape** of your data, never the records.

This is the generalised, repeatable form of the "send code, not data" pattern (see the README Data Protection section). It is how a full dashboard or analysis can be built without any identifiable data ever leaving the researcher's computer.

## The contract (non-negotiable)

1. **Never ask the user to paste raw data, individual records, or a data file's contents.** If you need to understand the data, ask about its *structure*, or generate code that reports that structure.
2. **If the user pastes something that looks like raw or sensitive data, STOP.** Do not use it. Call `check_data_safety` on it; if the classification is `CONFIDENTIAL` or `SENSITIVE`, tell them plainly, discard it from your working answer, and hand them a script that emits only aggregates instead.
3. **Only ever request or accept aggregates:** column names, data types, value counts / frequency tables, ranges, missingness, summary statistics, model coefficients and diagnostics, and the like.
4. **All raw-data computation happens on the user's machine.** Metis's job is to produce code and to reason over the metadata that comes back.

## What to do when invoked

**Usage:** `/safe-analysis [what you want to do]`
e.g. *"build a dashboard for my screening dataset"*, *"interpret my logistic model"*, *"make Table 1"*, *"profile and clean this CSV"*.

**Step 1 — Clarify the goal, not the data.**
Ask only what you need and nothing identifiable: What's the task? What format is the data (CSV / Excel / SPSS / Stata / SQLite)? Roughly what *domains* of variables does it hold (e.g. "demographics, test results, dates") — never the values? R or Python?

**Step 2 — State the plan in plain language.**
> "Here's a script you'll run on your own machine. It prints only [the schema / value counts / a summary table / the model output]. Nothing identifiable leaves your computer. Paste me back only that output."

**Step 3 — Generate the local script.**
Emit a self-contained script (Step-templates below) that: reads their file path (placeholder), computes the needed metadata, and **prints only safe aggregate output** — never row-level data. Cap or omit any example values. Where useful, also have it write the metadata to a small `*_metadata.txt`/`.json` they can review before sharing.

**Step 4 — Receive metadata → sanity-check → do the work.**
When they paste the output: glance for anything identifiable (when unsure, call `check_data_safety`). Then perform the actual task using only that metadata, routing to the right specialist — **Dashboard Engineer** (dashboards), **Biostatistician** (models/power), **Methods Coach** (method choice), **Data Analyst** (profiling/cleaning), **Writing Partner** (Table 1 / results prose).

**Step 5 — Record.**
`log_agent_run(agent_slug="data-guardian", task_summary=..., session_id=...)` and a brief `write_reflexion`. Offer to capture the analysis as a project/idea.

## Script templates

### A. Profile / codebook — for dashboards, cleaning, understanding structure
```r
# R — prints schema + value summaries ONLY. No raw rows leave your machine.
df <- read.csv("PATH/TO/your_data.csv", stringsAsFactors = FALSE)  # or readxl/haven
cat("Rows:", nrow(df), " Cols:", ncol(df), "\n\n")
for (v in names(df)) {
  x <- df[[v]]
  cat(sprintf("%-24s %-10s  missing=%d  unique=%d\n",
              v, class(x)[1], sum(is.na(x)), length(unique(x))))
  if (is.numeric(x)) {
    cat("   range:", paste(round(range(x, na.rm = TRUE), 3), collapse = " – "),
        " mean:", round(mean(x, na.rm = TRUE), 3), "\n")
  } else if (length(unique(x)) <= 20) {           # only low-cardinality categoricals
    print(table(x, useNA = "ifany"))
  } else {
    cat("   (high-cardinality — value list withheld)\n")  # e.g. names/IDs: never printed
  }
}
```
```python
# Python equivalent
import pandas as pd
df = pd.read_csv("PATH/TO/your_data.csv")            # or read_excel / read_stata / read_spss
print("Rows:", len(df), "Cols:", df.shape[1])
for v in df.columns:
    s = df[v]
    print(f"{v:24} {str(s.dtype):10} missing={s.isna().sum()} unique={s.nunique()}")
    if pd.api.types.is_numeric_dtype(s):
        print("   range:", round(s.min(),3), "-", round(s.max(),3), " mean:", round(s.mean(),3))
    elif s.nunique() <= 20:
        print(s.value_counts(dropna=False).to_string())
    else:
        print("   (high-cardinality — values withheld)")
```

### B. Table 1 — descriptive stats by group
```r
# Counts/means/proportions only — never individual rows.
library(dplyr)
df %>% group_by(GROUP_VAR) %>% summarise(
  n = n(),
  age_mean = round(mean(AGE, na.rm = TRUE), 1),
  positive_pct = round(100 * mean(RESULT == "positive", na.rm = TRUE), 1)
) %>% print()
```

### C. Model interpretation — fit locally, share only the summary
```r
m <- glm(outcome ~ age + sex + zone, data = df, family = binomial)
print(summary(m))            # coefficients, SEs, p-values — no data
print(exp(cbind(OR = coef(m), confint(m))))   # odds ratios + 95% CI
# (paste this output; Metis interprets it and drafts the methods/results)
```

### D. De-identification — make a dataset shareable (output stays local too)
```r
# Hash IDs, shift dates per-subject, coarsen geography, check k-anonymity.
library(digest)
df$id_hash <- vapply(df$patient_id, function(z) digest(paste0(z, "SALT")), character(1))
df$patient_id <- NULL
df$zone <- df$health_zone            # keep zone, drop village/GPS
# k-anonymity check on the quasi-identifiers you keep:
ka <- df %>% count(sex, age_band, zone) %>% summarise(min_k = min(n))
cat("min k =", ka$min_k, "(want >= 5)\n")
saveRDS(df, "deidentified_local_only.rds")   # stays on your machine
```

## Safety net (not the first line of defence)

The pipeline's Data Guardian (`scan_content`, Stage 3) classifies every request, and `check_data_safety` can scan any pasted text on demand. But the whole point of this workflow is that the Guardian rarely has to fire — because only metadata is ever shared in the first place.

## Collaboration

Data Guardian (classification) · Data Analyst (profiling/cleaning) · Biostatistician (models, power) · Methods Coach (method choice) · Dashboard Engineer (dashboards) · Writing Partner (Table 1 / results prose).
