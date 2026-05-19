# Introduction to Multilevel Models

## Learning objectives
- Explain why clustering violates ordinary independence assumptions.
- Distinguish fixed effects from random effects at an introductory level.
- Interpret the intuition behind random-intercept models.
- Recognize when multilevel models improve epidemiologic and health-systems analyses.

## Prerequisites
- Multiple regression.

## Content

### Section 1: Why multilevel thinking is needed
Many epidemiologic datasets are hierarchical. People are nested within households, households within villages, villages within districts, or patients within facilities. Observations from the same cluster often resemble each other more than observations from different clusters.

This matters because ordinary regression methods often assume independence of observations. If clustering is ignored, uncertainty may be underestimated and important contextual variation may be hidden.

Multilevel models, also called hierarchical or mixed models, are designed for this structure.

### Section 2: What clustering means in practice
Clustering can arise for many substantive reasons:

- people in the same village share ecology and services
- patients in the same facility share clinical practices
- repeated measurements on the same person share biology and history
- districts share programme management and reporting systems

These are not statistical nuisances added after the fact. They are features of how health data are generated. The model should reflect that structure.

### Section 3: Fixed effects and random effects
At an introductory level, a useful distinction is:

- **fixed effects** describe average associations across the dataset
- **random effects** allow certain quantities, such as baseline outcome levels, to vary across clusters

A common starting model is the **random-intercept model**. It allows each cluster to have its own baseline level of the outcome while still estimating average predictor effects across clusters.

This is often more realistic than assuming that all villages, facilities, or districts begin at exactly the same baseline risk.

### Section 4: Random-intercept intuition
Imagine modelling hemoglobin level in individuals nested within villages. Even after accounting for infection status, age, and sex, some villages may have systematically higher or lower average hemoglobin because of diet, malaria ecology, socioeconomic conditions, or health-service access.

A random-intercept model lets the baseline expected hemoglobin vary by village.

That is the key intuition: the model acknowledges that clusters differ, rather than forcing all between-cluster variation into the residual error.

### Section 5: Worked example — disease risk factors by village
Suppose a study examines disease risk factors among individuals living in 40 villages. Predictors include age, sex, occupation, and distance to river.

If a standard logistic regression ignores village clustering, it may treat all individuals as fully independent. But villagers often share exposure environments, vector ecology, and care access.

A multilevel model with a village random intercept allows baseline disease risk to differ across villages. This usually gives a more realistic estimate of uncertainty and a better account of contextual variation.

The model may reveal that some of what looked like individual-level effect is actually structured by village context.

### Section 6: Why multilevel models are useful
Multilevel models are useful because they can:

- account for clustering explicitly
- separate within-cluster from between-cluster variation
- improve standard errors and confidence intervals
- allow cluster-level predictors and individual-level predictors in one framework
- support more realistic health-systems and geographic analyses

They are especially common in education, health-services research, implementation science, and spatially structured public-health datasets.

### Section 7: When simpler approaches may be enough
Not every clustered dataset requires a full multilevel model. In some cases, cluster-robust standard errors or fixed-effects approaches may be reasonable alternatives depending on the question.

But when cluster structure is scientifically meaningful and between-cluster variation is itself important, multilevel modeling often provides a clearer representation of the data-generating process.

The choice should follow the question. Are you only trying to correct standard errors, or do you also want to understand variation across clusters?

### Section 8: Common mistakes
Several mistakes recur often.

- ignoring clustering entirely
- using a multilevel model without being clear about the cluster structure
- interpreting random effects as if they were ordinary fixed coefficients
- assuming that more levels always mean a better model
- forgetting that cluster-level and individual-level effects can answer different questions

The practical lesson is that multilevel modeling is not just a more advanced regression. It is a way of respecting the structure of real epidemiologic data.

## Key takeaways
- Multilevel models are used when data are hierarchical or clustered.
- Clustering violates simple independence assumptions and can distort uncertainty if ignored.
- Fixed effects summarize average associations, while random effects allow cluster-level variation.
- Random-intercept models are a useful starting point for understanding between-cluster heterogeneity.
- Multilevel models are especially valuable for village-, facility-, district-, and repeated-measure data common in public health.

## Self-check questions
1. What problem arises if clustering is ignored in an ordinary regression?
2. What does a random intercept allow?
3. Why might people in the same village have correlated outcomes?
4. What is the difference between fixed effects and random effects in simple terms?
5. Why might a multilevel model be preferable to a pooled model in health-systems data?
6. Why is multilevel modeling not just a technical upgrade but also a substantive one?

## Answer key
1. Standard errors may be underestimated and contextual variation may be hidden because the model assumes too much independence.
2. It allows the baseline level of the outcome to vary across clusters such as villages or facilities.
3. Because they share environment, services, programme implementation, and social context.
4. Fixed effects describe average associations across the dataset, while random effects allow certain quantities to vary across clusters.
5. Because health-systems data are often nested within facilities, districts, or regions, and that structure affects both estimates and uncertainty.
6. Because clustering reflects real epidemiologic and organizational processes, not merely a statistical inconvenience.

## Further reading
- [Gelman and Hill book page](https://www.cambridge.org/core/books/data-analysis-using-regression-and-multilevelhierarchical-models)
- [CRAN lme4 package](https://cran.r-project.org/package=lme4)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)
