# Skill: Fuzzy Name Matching for Record Linkage

## When to use this skill
Any project that needs to link records across datasets without a reliable unique identifier,
where names (personal or place names) are the primary linking variable. Examples:
- Linking patient records across screening years
- Deduplicating registries with inconsistent name spelling
- Matching village/location names across data sources
- Any Western or Congolese name matching context

---

## Core principles

1. **Never match on names alone across an entire dataset** — always block first
2. **Compute distances, then classify into zones** — do not use a single hard threshold
3. **Account for missing variables explicitly** — do not silently drop NA pairs
4. **Always validate before applying at scale** — export candidates, label manually, compute precision/recall
5. **Keep the best match per anchor record** — use `slice_min()`, never `slice(1)`

---

## Step 1 — Variable assessment

Before any matching, assess completeness of candidate linking variables:

```r
dat %>%
  select(nom, prenom, postnom, nom_mere, village) %>%
  summarise(across(everything(), list(
    n_present = \(x) sum(!is.na(x) & trimws(x) != ""),
    pct_miss  = \(x) round(100 * (sum(is.na(x)) + sum(!is.na(x) & trimws(x) == "")) / n(), 1)
  ), .names = "{.col}__{.fn}")) %>%
  pivot_longer(everything(), names_to = c("variable", "stat"), names_sep = "__") %>%
  pivot_wider(names_from = stat, values_from = value) %>%
  arrange(pct_miss)
```

Also check co-missingness — when your primary variable is missing, is the fallback variable present?

```r
dat %>%
  mutate(nom_missing  = is.na(nom) | trimws(nom) == "",
         mere_present = !is.na(nom_mere) & trimws(nom_mere) != "") %>%
  group_by(nom_missing) %>%
  summarise(n = n(), mere_present = sum(mere_present), pct = round(100 * mere_present / n, 1))
```

---

## Step 2 — Blocking

Block on geography or another exact variable BEFORE computing string distances.
This reduces comparisons from millions to thousands and prevents false many-to-many matches.

**For DRC/TRYPELIM data**: block on `healthzone + healtharea + village`
(many villages share the same name across provinces — blocking on village alone is insufficient)

**For Western data**: block on postal code, year of birth, or first letter of surname

```r
candidates <- data_yr1 %>%
  inner_join(data_yr2,
             by = c("healthzone", "healtharea", "village"),
             suffix = c("_yr1", "_yr2"))
```

---

## Step 3 — Distance computation

Use **Jaro-Winkler** (`method = "jw"` in `stringdist`) for name variables.
Rationale: handles transpositions, gives higher weight to prefix matches,
performs better than Levenshtein on short strings and African name variants.

```r
library(stringdist)

candidates <- candidates %>%
  mutate(
    dist_nom     = stringdist(nom_yr1,     nom_yr2,     method = "jw"),
    dist_prenom  = stringdist(prenom_yr1,  prenom_yr2,  method = "jw"),
    dist_postnom = stringdist(postnom_yr1, postnom_yr2, method = "jw"),
    dist_mere    = stringdist(mere_yr1,    mere_yr2,    method = "jw")
  )
```

---

## Step 4 — Sequential gate logic with NA handling

Always require the primary variable (highest completeness) to pass Gate 1.
Then select exactly 2 more variables for Gate 2, using fallbacks when variables are missing.

### Gate 1 — primary variable required
```r
candidates <- candidates %>%
  filter(dist_nom < 0.20)   # lenient at gate; zones do the real work
```

### Gate 2 — select 2 secondary variables, handle NA
```r
candidates <- candidates %>%
  mutate(
    prenom_avail  = !is.na(prenom_yr1)  & trimws(prenom_yr1)  != "" &
                    !is.na(prenom_yr2)  & trimws(prenom_yr2)  != "",
    postnom_avail = !is.na(postnom_yr1) & trimws(postnom_yr1) != "" &
                    !is.na(postnom_yr2) & trimws(postnom_yr2) != "",
    mere_avail    = !is.na(mere_yr1)    & trimws(mere_yr1)    != "" &
                    !is.na(mere_yr2)    & trimws(mere_yr2)    != "",

    vars_used = case_when(
      prenom_avail & postnom_avail  ~ "prenom + postnom",
      prenom_avail & !postnom_avail ~ "prenom + mere",
      !prenom_avail & postnom_avail ~ "postnom + mere",
      TRUE                          ~ "mere only"           # low confidence
    ),

    avg_dist_used = case_when(
      vars_used == "prenom + postnom" ~ rowMeans(cbind(dist_nom, dist_prenom, dist_postnom), na.rm = TRUE),
      vars_used == "prenom + mere"    ~ rowMeans(cbind(dist_nom, dist_prenom, dist_mere),    na.rm = TRUE),
      vars_used == "postnom + mere"   ~ rowMeans(cbind(dist_nom, dist_postnom, dist_mere),   na.rm = TRUE),
      vars_used == "mere only"        ~ rowMeans(cbind(dist_nom, dist_mere),                 na.rm = TRUE)
    ),

    low_confidence = vars_used == "mere only"
  )
```

---

## Step 5 — Three-zone classification

| Zone | avg_dist_used | Action |
|---|---|---|
| auto_match | < 0.10 | Accept automatically |
| review | 0.10 – 0.20 | Export for manual review |
| reject | > 0.20 | Discard |

```r
candidates <- candidates %>%
  mutate(
    zone = case_when(
      avg_dist_used <  0.10 ~ "auto_match",
      avg_dist_used <= 0.20 ~ "review",
      TRUE                  ~ "reject"
    )
  ) %>%
  filter(zone != "reject")
```

---

## Step 6 — Tie-breaking

Keep the best match per anchor record using lowest average distance.
Never use `slice(1)` — that is row-order dependent and not reproducible.

```r
candidates_best <- candidates %>%
  group_by(identifier_yr1) %>%
  slice_min(avg_dist_used, n = 1, with_ties = FALSE) %>%
  ungroup()
```

---

## Step 7 — Export and validation

Export two files:
- **Auto-matches**: no review needed, spot-check a sample for quality control
- **Review zone**: label `correct_match` TRUE/FALSE in Excel, then compute precision/recall

```r
# Review zone export
candidates_best %>%
  filter(zone == "review") %>%
  mutate(correct_match = NA_character_) %>%
  arrange(avg_dist_used) %>%
  write.csv("fuzzy_review.csv", row.names = FALSE, fileEncoding = "UTF-8")
```

After labelling, compute precision by distance band:

```r
val <- read.csv("fuzzy_review.csv") %>%
  mutate(correct_match = as.logical(correct_match))

val %>%
  mutate(dist_band = cut(avg_dist_used,
                         breaks = c(0.10, 0.12, 0.14, 0.16, 0.18, 0.20),
                         include.lowest = TRUE)) %>%
  group_by(dist_band) %>%
  summarise(
    n         = n(),
    precision = round(sum(correct_match, na.rm = TRUE) / n(), 3),
    .groups = "drop"
  )
```

---

## Notes on name types

### Congolese names (DRC context)
- Three-part naming: Nom (family) + Postnom + Prénom — order varies by data entry operator
- Common variation sources: French vs Lingala/Kikongo/Swahili spelling, vowel doubling (Mbaya/Mbaaya), truncation, prefix omission (Nk- vs K-)
- Nom de la mère is a strong fallback — independent of the patient's own name encoding errors
- Postnom completeness is often low (30–40%) — do not rely on it as a required variable
- Village names: many duplicates across provinces — always block on healthzone + healtharea + village

### Western names
- Two-part naming typical: family name + given name (+ optional middle)
- Common variation: hyphenated names, accents stripped (García → Garcia), nickname vs legal name
- Date of birth is a strong additional blocking/matching variable when available
- Soundex can supplement Jaro-Winkler for phonetic matching of anglophone names

---

## Scale considerations

| Dataset size | Recommended approach |
|---|---|
| Single village / small cohort (< 5,000) | Custom sequential JW in tidyverse (transparent, controllable) |
| Regional / national (> 100,000) | `fastLink` package — parallel computing, EM-estimated weights, no manual threshold calibration |

For `fastLink`, the labelled validation CSV from the small-scale approach serves as training data for threshold calibration.

Reference: ASTHO Record Linkage Using R (Parrish, 2024)
- Deterministic exact match: ~68% linkage rate
- Probabilistic with manual review: ~96% linkage rate
