# Spatial Regression

## Learning objectives
- Explain when ordinary regression is insufficient for spatial data.
- Distinguish the basic intuition of spatial lag, spatial error, and areal smoothing models.
- Recognize the difference between modeling dependence and modeling mechanism.
- Choose spatial models based on the substantive question rather than software convenience.

## Prerequisites
- Spatial autocorrelation and multiple regression.

## Content

### Section 1: Why standard regression can fail in spatial data
Ordinary regression assumes that, after accounting for predictors, residuals are independent. In spatial epidemiology that assumption often fails because nearby areas share unmeasured environment, services, reporting structures, or transmission processes.

If spatial dependence remains in the residuals, standard errors may be too optimistic and coefficients may absorb pattern that actually belongs to unmodeled spatial structure. This is one reason spatial regression exists.

### Section 2: What spatial regression is trying to do
Spatial regression is not one model. It is a family of approaches for situations where:

- the outcome depends partly on neighboring outcomes
- residuals are spatially correlated
- small-area rates need spatial smoothing
- relationships vary over space

Different models answer different questions. The analyst's task is to match the model to the likely process rather than treating "spatial regression" as a single generic upgrade.

### Section 3: Spatial lag models
A **spatial lag model** includes the influence of neighboring outcome values directly. Conceptually, it says that what happens in one area may depend partly on what is happening nearby.

This can be plausible when there is true spatial spillover, such as:

- transmission across neighboring areas
- intervention effects that diffuse geographically
- service access that crosses boundaries

The main intuition is contagion or spatial interaction in the outcome itself.

### Section 4: Spatial error models
A **spatial error model** is different. It assumes that the spatial dependence lies mostly in the unexplained component of the model rather than in direct spillover of the outcome.

This may be appropriate when neighboring areas share omitted drivers, such as:

- environmental suitability
- reporting quality
- socioeconomic context
- unmeasured programme strength

The core idea is that the model is missing spatially patterned information, and the error structure reflects that.

### Section 5: Areal smoothing and CAR-type models
In small-area disease mapping, analysts often use models based on conditional autoregressive structure, such as CAR or BYM-style approaches. These models borrow strength across neighboring areas and are often especially useful when raw rates are unstable.

Their role is often partly descriptive and partly inferential. They help stabilize area-level estimates while accounting for spatial dependence. This is different from simply running a standard regression on noisy crude rates and hoping for the best.

### Section 6: Worked example - neighboring transmission context
Imagine a village-level model of disease risk includes distance to river, occupation, and facility access. After fitting an ordinary model, residuals still cluster geographically.

This may suggest that:

- neighboring villages share transmission context not captured by measured variables
- spatial spillover or unmeasured ecology remains important
- the current model underrepresents structured dependence

A spatial lag or spatial error model may be more appropriate depending on whether the analyst believes the key mechanism is direct neighboring influence or omitted spatially structured causes.

### Section 7: Explanation versus prediction
Spatial models can be used for both explanation and prediction, but those goals are not identical.

If the main goal is **explanation**, you may care most about whether coefficients represent plausible mechanisms and whether adjustment aligns with the causal structure.

If the goal is **prediction**, you may care more about accurate risk surfaces, stable fitted values, and out-of-sample performance.

This distinction matters because a strong predictive spatial model is not automatically a strong causal model.

### Section 8: Common mistakes
Several mistakes recur often.

- fitting a spatial model without first diagnosing whether spatial dependence is present
- choosing a lag or error model by habit rather than mechanism
- interpreting smoothed surfaces as if they were direct observations
- assuming a spatial model automatically fixes confounding
- using spatial regression when a data-quality problem is the real issue

Spatial models are powerful, but they still depend on measurement quality, denominators, and epidemiologic reasoning.

## Key takeaways
- Spatial regression is needed when dependence or smoothing needs cannot be handled well by ordinary regression.
- Spatial lag models represent neighboring influence in the outcome; spatial error models represent spatial structure in the unexplained component.
- CAR/BYM-type models are especially useful for areal disease mapping and small-area smoothing.
- Model choice should follow the likely spatial mechanism and the analytic goal.
- Spatial modeling improves analysis only when it is tied to a credible epidemiologic question and good data handling.

## Self-check questions
1. Why might ordinary regression be inadequate for spatial data?
2. What is the core intuition of a spatial lag model?
3. How is a spatial error model different?
4. Why are CAR-type models common in disease mapping?
5. Why should model choice follow mechanism rather than software availability?
6. Why is a strong predictive spatial model not automatically a causal model?

## Answer key
1. Because nearby observations may remain dependent after ordinary adjustment, violating independence assumptions and distorting inference.
2. That the outcome in one area is influenced partly by neighboring outcomes.
3. It assumes the spatial dependence is mainly in the residual or unmeasured component rather than direct spillover of the observed outcome.
4. Because they stabilize small-area estimates by borrowing strength across neighboring areas while accounting for spatial structure.
5. Because different spatial models represent different underlying processes, and the wrong model may answer the wrong question.
6. Because prediction can work well without identifying the true causal mechanism behind the spatial pattern.

## Further reading
- [CRAN spatialreg package](https://cran.r-project.org/package=spatialreg)
- [Simple Features for R](https://r-spatial.github.io/sf/)
- [OpenIntro Statistics](https://www.openintro.org/book/os/)

## Links to Metis library
- `knowledge/library/methods/spatial-epidemiology.md`
- `knowledge/library/methods/causal-inference.md`
- `knowledge/library/methods/biostatistics-essentials.md`
