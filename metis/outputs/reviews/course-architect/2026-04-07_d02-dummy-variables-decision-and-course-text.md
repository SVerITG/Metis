# D02 — Dummy Variables: Decision Log + Course Text Draft

**Date**: 2026-04-07  
**Status**: Resolved  
**Decision**: Option C — seed in Variables & Measurement, full worked example in regression lesson

## Disease chosen for worked example
Visceral leishmaniasis (kala-azar)  
- Three-arm treatment trial: SSG monotherapy vs. AmBisome vs. miltefosine combination  
- Endemic in Bihar (India), Nepal, East Africa — all relevant ITM contexts  
- Realistic trial structure, naturally produces k−1 = 2 dummy variables  

## Connection to D01
The categorical treatment group variable in the VL trial is a dummy variable — this is exactly the ANCOVA group variable from D01. The two explanations should cross-reference each other.

## Implementation locations
1. Variables & Measurement: one-sentence seed  
2. Multiple linear regression lesson: full subsection with worked example  
3. Cross-reference in the ANCOVA bridge callout (D01 text) to mention dummy coding  

## Course text drafted
See content below.

---

# Course Text

## 1. Seed — Variables & Measurement lesson
*(Insert as a short callout or italicised note after the section on nominal/categorical variables)*

> **Looking ahead — categorical variables in regression**  
> Nominal variables cannot enter a regression model as raw category labels. When we reach the regression module, you will see how each category is converted into a numeric 0/1 variable — called a **dummy variable** (or indicator variable). For now, just note that the type of variable you are working with determines how it will be coded later in the analysis.

---

## 2. Full subsection — Multiple linear regression lesson

### Dummy variables: including categorical predictors in regression

Regression works with numbers. But many of the predictors you care about are categorical — treatment group, sex, district, disease stage. To include them in a model, you convert each category into a 0/1 numeric variable. These are called **dummy variables** (also known as indicator variables).

#### The rule: k − 1 dummies for k categories

For a variable with k categories, you create k − 1 dummy variables. One category is left out — this becomes the **reference category**. All other categories are compared to it.

**Why k − 1 and not k?** If you created a dummy for every category, the dummies would sum to 1 for every row, which causes perfect multicollinearity and breaks the model. Leaving one out avoids this.

---

#### Worked example: treatment trial in visceral leishmaniasis

Visceral leishmaniasis (VL, also called kala-azar) is a fatal NTD caused by *Leishmania donovani*, endemic in Bihar (India), Nepal, and East Africa. A randomised trial compares three treatment regimens:

- **SSG monotherapy** (sodium stibogluconate) — the traditional first-line treatment
- **AmBisome** (liposomal amphotericin B) — a single-dose alternative
- **Miltefosine combination** — an oral combination regimen

The outcome is **parasite clearance at day 30** (continuous score, 0–100).

**Step 1 — the raw data looks like this:**

| Patient | Treatment | Clearance score |
|---------|-----------|----------------|
| 1 | SSG | 61 |
| 2 | AmBisome | 84 |
| 3 | Miltefosine combination | 79 |
| 4 | SSG | 58 |
| 5 | AmBisome | 88 |

**Step 2 — convert to dummy variables (reference = SSG):**

| Patient | Treatment | dummy_ambisome | dummy_miltefosine |
|---------|-----------|----------------|-------------------|
| 1 | SSG | 0 | 0 |
| 2 | AmBisome | 1 | 0 |
| 3 | Miltefosine combination | 0 | 1 |
| 4 | SSG | 0 | 0 |
| 5 | AmBisome | 1 | 0 |

SSG is the reference: both dummies = 0. The model is:

**Clearance = β₀ + β₁ · dummy_ambisome + β₂ · dummy_miltefosine + ε**

**Interpreting the coefficients:**

| Coefficient | Meaning |
|-------------|---------|
| β₀ | Predicted clearance score for SSG (reference group) |
| β₁ | Difference in clearance: AmBisome vs. SSG |
| β₂ | Difference in clearance: Miltefosine combination vs. SSG |

If β₁ = 24, this means AmBisome patients have on average 24 points higher clearance than SSG patients, holding other variables constant.

**Step 3 — what R does automatically:**

In R, you never need to create dummies by hand. When you include a `factor` variable in a regression formula, R creates k − 1 dummies silently and chooses the first level alphabetically as the reference.

```r
library(tidyverse)
library(broom)

# Load data
vl_trial <- read_csv("vl_trial.csv") |>
  mutate(treatment = factor(treatment,
                            levels = c("SSG", "AmBisome", "Miltefosine combination")))

# Fit model — R creates dummies automatically
model <- lm(clearance_score ~ treatment + age + baseline_spleen_size, data = vl_trial)

# Tidy output
tidy(model, conf.int = TRUE)
```

**Output:**

```
term                                    estimate  std.error  statistic  p.value  conf.low  conf.high
(Intercept)                               61.2      3.1        19.7      <0.001    55.1      67.3
treatmentAmBisome                         24.1      2.8         8.6      <0.001    18.6      29.6
treatmentMiltefosine combination          18.3      2.9         6.3      <0.001    12.6      24.0
age                                       -0.3      0.1        -3.0       0.003    -0.5      -0.1
baseline_spleen_size                      -0.8      0.2        -4.1      <0.001    -1.2      -0.4
```

Key points to read from this output:
- The intercept (61.2) is the predicted clearance for an SSG patient with age = 0 and spleen size = 0 — not directly interpretable, but needed for the model
- `treatmentAmBisome` (24.1) — AmBisome patients have 24.1 points higher clearance than SSG patients on average, after adjusting for age and baseline spleen size (95% CI: 18.6 to 29.6)
- `treatmentMiltefosine combination` (18.3) — Miltefosine patients have 18.3 points higher clearance than SSG
- There is no row for SSG — it is the reference, absorbed into the intercept
- To change the reference category: `relevel(treatment, ref = "AmBisome")`

---

#### Connecting back to ANCOVA

If you have used ANCOVA before, this is exactly what it does. The treatment group is the dummy variable; age and baseline spleen size are the covariates. The mathematics is identical — only the framing differs.

---

## 3. Tie-in (end of regression lesson, under "Tie-ins")

- **Dummy variables and multilevel models**: In MLM, level-2 grouping variables (country, district, health facility type) are often categorical. They enter the model as dummy variables at level 2, just as treatment group entered here. Cross-level interactions — a key concept in Module [X] — almost always involve a dummy-coded level-2 variable interacting with a continuous level-1 predictor. The logic you learned here carries forward directly.

---

## Implementation notes for the implementing AI

- Seed callout in Variables & Measurement: visually distinct but lightweight — a small italicised note or a "looking ahead" box, not a full subsection
- Full subsection in regression lesson: give it a clear H2 or H3 heading "Dummy variables: including categorical predictors in regression"
- The worked example table and R output must be rendered properly (not as raw markdown table in a code block)
- R output: annotate the important lines with inline comments explaining what to look at
- The ANCOVA bridge callout (D01 text) should include a one-line cross-reference: "The treatment group variable in this example is a dummy variable — explained in full in the section below"
- Do not add the full dummy variable explanation to the Introduction module
- VL context: visceral leishmaniasis / kala-azar, *Leishmania donovani*, Bihar/Nepal/East Africa settings
