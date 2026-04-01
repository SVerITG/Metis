# Monia Review: Agent Smoke Test — HAT Dashboard & Clustering

**Date:** 2026-03-29
**Agent:** monia (chain — 10 agents)
**Request:** Test all agents on the HAT Dashboard, let them analyse something small
**Input:** HAT Dashboard (7. Dashboard/), HAT Clustering (4. Clustering/)
**Complexity:** Chain

---

## Smoke test results

Each agent was given one focused micro-task on real HAT project files. Results below.

---

### 1. Software Engineer — `02d_derived_datasets.R` quick review

**File:** `02d_derived_datasets.R` (derived datasets for 9M+ records)

**Finding:** `case_flag_any(dplyr::cur_data())` on line 27 uses `cur_data()` which was deprecated in dplyr 1.1.0 and may break in future versions. Replace with `pick(everything())` or pass columns explicitly.

**Finding:** The function creates `dm_cases_summary` by binding ITM and WHO data, then does a left join with `village_coords` to fill missing coordinates. This join on `c("village", "healthzone")` could produce duplicates if village names are not unique within health zones. Consider adding `dplyr::distinct()` before the join or using `multiple = "first"`.

**Verdict:** Functional but has two deprecation/correctness risks.

---

### 2. Epidemiologist — SaTScan parameter challenge

**File:** `DRC_24-25_5%POP_90%SP_9MC_250h/results.txt` and `DRC_24-25_50%POP_50%SP_800h/results.txt`

**Questions I would ask before accepting these results:**

1. **Population denominator:** 2.3M locations with 117M population — is this village-level GPS points? How was population assigned to each point? Interpolation from health zone census? This matters for the Poisson model assumptions.

2. **Two runs with very different parameters:** One uses 5% max population / 90% spatial penalty, the other 50%/50%. What was the rationale for each? The 50% population cap is unusual for a rare disease — at 0.02-0.2 cases/100,000, a 50% population cluster would be meaningless epidemiologically.

3. **Study period mismatch:** One run covers 2000-2025 (full history), the other 2024-2025 only. These answer fundamentally different questions (historical hotspots vs current risk). Are you clear on which question you need for the PhD article?

4. **Only 532 cases across 117M population:** At this prevalence (0.02/100,000), SaTScan's power to detect clusters is very low. Have you calculated the minimum detectable relative risk given your spatial resolution?

5. **250 vs 800 health zones in the max spatial window:** What geographic reasoning drove these choices? The 250hz limit seems like it could artificially truncate clusters that span coordination boundaries.

**Verdict:** Parameters need explicit justification. The 50% population cap run should probably be discarded.

---

### 3. Methods Coach — statistical approach check

**Observation:** You're running retrospective space-time Poisson with SaTScan v10.3.3. This is appropriate for rare disease cluster detection.

**Flag:** With 2.3M locations and 532 cases, most locations will have 0 cases. SaTScan handles this, but the Monte Carlo simulations (9 or 99?) may not be enough for stable p-values at this sparsity. Check: did you use 999 or 9999 Monte Carlo replications? The "9MC" in the folder name suggests only 9, which is too few for publication-quality results.

**Suggestion:** For the PhD article, use at minimum 999 replications (ideally 9999). The computation time is higher but results will be reproducible.

---

### 4. Writing Partner — config documentation review

**File:** `00_config.R`

**Grammar/clarity:** The code comments are clean and professional. The header "YEAR BOUNDARIES (CRITICAL)" in `app.R` is well-marked. However, the version numbering is inconsistent: `app.R` says "v38 (pre-1.0)", `02d_derived_datasets.R` says "v38", `03_css_styles.R` says "v40", `04_helpers.R` says "v38". Pick one version scheme and apply consistently.

**Suggestion:** Since you've declared V1.0 in the navbar badge, update all file headers to "v1.0".

---

### 5. UX Engineer — CSS audit snippet

**File:** `03_css_styles.R`

**Good:** Uses CSS custom properties (`:root` variables), has glassmorphism navbar, proper font loading.

**Issues found:**
- `body { padding-top: 85px !important; }` — hardcoded padding to compensate for fixed navbar. Fragile; if navbar height changes, content is hidden.
- Uses `@keyframes fadeInUp` but no `@media (prefers-reduced-motion)` — accessibility gap.
- Fonts loaded via `@import url(...)` in CSS — this blocks rendering. Move to `<link rel="preload">` in the HTML head for better performance.

**Verdict:** Visually polished but has accessibility and performance gaps.

---

### 6. Dashboard Engineer — architecture observation

**File:** `app.R`

**Structure:** 8 UI modules + 10 server modules, all sourced via `source()`. This is a classic monolithic Shiny pattern — works fine until the file count grows further.

**Observation:** `server_core()` on line 59 is defined but appears empty (`{}`). Is this used? Dead code should be removed.

**Suggestion:** For future growth, consider migrating to Shiny modules (`moduleServer()` + namespaced UI/server pairs) to avoid global namespace pollution. Not urgent.

---

### 7. PhD Architect — project alignment check

**Observation:** The HAT Dashboard serves Article 1 (surveillance data analysis) and provides data visualization for Articles 2-3 (clustering, passive detection). It is a tool, not a thesis chapter — but its derived datasets (`dm_cases_summary`, screening summaries) are the analytical backbone.

**Question:** Is the dashboard's case classification logic (confirmed/probable/stroghat) consistent with the definitions you'll use in the PhD articles? If the dashboard classifies differently from your article, reviewers will catch the discrepancy.

---

### 8. Librarian — data source note

**Observation from config:** Data sources are TRYPELIM (ITM individual records, 2019+) and WHO HAT Atlas (aggregated, 2000-2018). The year boundary is critical: WHO data stops at 2018, ITM starts at 2019.

**Flag:** The WHO extraction file is dated `240402` (April 2024). Has there been a more recent WHO data release? If so, the 2019-2022 gap between WHO and ITM data might be fillable.

---

### 9. Learning Coach — skill observation

**Based on code reviewed:** Your R/dplyr skills are solid (grouped summaries, joins, coalesce). SaTScan usage shows spatial epi competency. The gap is in **reproducibility practices** — no unit tests, version inconsistencies, parameter choices not documented in code.

**Suggested next skill:** Learn `testthat` for R to write simple unit tests for the derived dataset functions. This directly serves the PhD (reviewers may ask about data validation).

---

### 10. Career Coach — quick note

**Observation:** A working R Shiny surveillance dashboard processing 9M records is a strong portfolio piece for WHO/ECDC/GOARN-type positions. Make sure the GitHub repo (`SVerITG/HAT_Dashboard_1.0`) is pushed and has a clean README before any job applications.

---

## Follow-up actions

- [ ] **Software Engineer:** Fix `cur_data()` deprecation in `02d_derived_datasets.R`
- [ ] **Epidemiologist:** Document SaTScan parameter rationale in a methods note
- [ ] **Methods Coach:** Re-run SaTScan with 999+ Monte Carlo replications
- [ ] **Writing Partner:** Standardize version headers across all .R files to v1.0
- [ ] **UX Engineer:** Add `prefers-reduced-motion` to `03_css_styles.R`
- [ ] **PhD Architect:** Verify case classification consistency between dashboard and articles
- [ ] **Librarian:** Check for updated WHO HAT Atlas data post-April 2024
- [ ] **Learning Coach:** Start `testthat` for derived dataset validation
