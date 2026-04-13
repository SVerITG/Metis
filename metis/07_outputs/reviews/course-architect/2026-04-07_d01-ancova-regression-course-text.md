# D01 — Course Text Draft: ANCOVA as Bridge to Regression

**Location in course**: Module 1 / Multiple Linear Regression lesson — early theory section  
**Format**: "If you've seen this before" bridge callout box  
**Status**: Draft — ready for review

---

## Bridge callout box (insert near top of regression theory section)

> **If you've done ANCOVA, you've already done regression**
>
> Many researchers in clinical and experimental settings learn ANCOVA — Analysis of Covariance — before they encounter regression. If that's you, here's the good news: they are the same model.
>
> ANCOVA takes a group variable (say, treatment vs. control) and one or more continuous covariates (say, age or baseline score) and fits a linear model that controls for the covariate while comparing groups. That is exactly what multiple linear regression does — the group variable becomes a dummy variable (0/1), the covariates become predictors, and the output is a set of β coefficients.
>
> The difference is not in the mathematics. It is in the tradition: ANCOVA comes from the world of experiments and ANOVA; regression comes from epidemiology and observational research. Same engine, different dashboard.
>
> **So if ANCOVA feels familiar — good. You already understand the core logic. This lesson will show you how to read the regression dashboard.**

---

## Short in-line version (if a full callout box is too much)

> ANCOVA and multiple linear regression are the same model. If you have used ANCOVA before, you have already fitted a regression — the group variable was simply coded as a dummy variable (0 = control, 1 = treatment). This course uses regression language throughout, but the underlying mathematics is identical.

---

## Tie-in at end of regression lesson (linking to MLM)

**Tie-ins**

- **From ANCOVA to regression to multilevel models**: ANCOVA controls for a covariate while comparing groups. Multiple regression generalises this to any number of predictors. Multilevel models take the next step: instead of treating group membership as a dummy variable, they model the group structure explicitly — allowing effects to vary across groups. The conceptual spine of this course is ANOVA → ANCOVA → regression → multilevel models. Each step adds one layer of realism.

---

## Implementation notes for the implementing AI

- Insert the bridge callout box as a visually distinct block (e.g. teal left-border callout, or a "Connecting the dots" styled box) near the top of the regression theory section, before the formal model specification
- The short in-line version is an alternative if page length is a concern — choose one, not both
- The Tie-in belongs under the "Tie-ins" heading at the end of the lesson, per global standard (§ of implementation plan)
- Do NOT add this content to the Introduction module — regression has not been taught yet at that point
- Connected concept: dummy variables (D02) — consider whether a brief mention of dummy variable coding belongs in the same callout
