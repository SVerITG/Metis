# Cluster Detection with SaTScan

## Learning objectives
- Explain the logic of the spatial scan statistic used by SaTScan.
- Distinguish most-likely clusters from secondary clusters.
- Choose among common model settings such as Poisson, Bernoulli, and space-time analyses.
- Interpret SaTScan output with attention to parameter choices, denominators, and field context.

## Prerequisites
- Disease mapping and probability basics.

## Content

### Section 1: Why formal cluster detection is useful
Maps can suggest hotspots, but visual impression alone is not enough to tell whether a cluster is unusual relative to the underlying population distribution. Formal cluster-detection tools help answer a sharper question: is the observed concentration of cases more extreme than would be expected under a defined null model?

SaTScan is one of the most widely used tools for this purpose in public health. It is especially common in outbreak detection, cancer epidemiology, and elimination-phase surveillance.

### Section 2: The core logic of the scan statistic
SaTScan moves a scanning window across space, or across space and time. At each location and size, it compares the number of observed cases inside the window with the number expected under the null model.

The software evaluates many possible windows. For each one, it computes a likelihood ratio comparing:

- a null model of no unusual clustering
- an alternative model in which the area inside the window has elevated or reduced risk

The window with the strongest evidence becomes the **most-likely cluster**. Additional non-overlapping clusters may be reported as **secondary clusters**.

### Section 3: Why multiple testing is not ignored
One of the practical strengths of SaTScan is that it accounts for the fact that many candidate windows are being tested. This is usually handled through Monte Carlo simulation.

That matters because without such correction, scanning a large number of possible locations and window sizes would generate many false positives simply by chance.

So SaTScan is not only searching for unusual areas. It is searching while trying to control the problem of repeated testing.

### Section 4: Model choices
Different SaTScan models answer different questions.

The **Poisson model** is common when you have case counts and population denominators by area.

The **Bernoulli model** is common when you have case-control style data with case locations and control locations.

The **space-time permutation model** is useful when denominators are less available but timing and location of cases are known.

Choosing the wrong model can make the output hard to interpret. The model should match the data structure and the epidemiologic question.

### Section 5: Parameter choices matter
SaTScan output is sensitive to analyst choices, especially:

- maximum spatial window size
- maximum temporal window size
- whether circles or ellipses are allowed
- whether high-rate, low-rate, or both cluster types are sought

For example, a very large maximum spatial window may detect broad clusters that are too coarse to be operationally useful. A very small window may miss larger regional patterns.

This is why SaTScan is not a push-button truth machine. Analysts need to justify the parameter settings in relation to the biology, surveillance system, and decision problem.

### Section 6: Worked example - district-level HAT scan
Imagine a programme uses district-level HAT case counts with district population denominators. A Poisson scan statistic is run to identify unusually high-incidence areas.

The analysis identifies one most-likely cluster spanning four neighboring districts with a relative risk above 2 and a Monte Carlo p-value below 0.05.

That result suggests the cluster is unlikely under the null model of spatial randomness adjusted for population. But interpretation still requires caution. The cluster might reflect:

- true focal transmission
- intensified screening in those districts
- better reporting completeness
- referral concentration into a stronger diagnostic center

The software identifies an unusual pattern. It does not explain why the pattern exists.

### Section 7: Field context and validation
This is the most important practical lesson: cluster detection should not be separated from field epidemiology.

SaTScan results are strongest when interpreted alongside:

- disease maps
- denominator quality
- surveillance intensity
- environmental plausibility
- local programme knowledge

A statistically unusual cluster that aligns with riverine vector habitat and poor access patterns may deserve very different interpretation from a cluster that aligns mainly with an area of stronger reporting and a referral hospital.

### Section 8: Common mistakes
Several mistakes recur often.

- interpreting the most-likely cluster as a confirmed outbreak source
- ignoring denominator quality
- using arbitrary maximum window settings without justification
- overreading secondary clusters
- treating statistical significance as if it proves transmission mechanism

The practical habit is to treat cluster detection as one layer of evidence, not the whole evidentiary argument.

## Key takeaways
- SaTScan uses a scanning window and likelihood comparison to identify areas with unusual case concentration.
- Multiple testing is addressed through simulation, which is one reason the method is widely used.
- The Poisson, Bernoulli, and space-time models serve different data structures and questions.
- Parameter choices such as maximum window size strongly influence results.
- Cluster output should always be interpreted alongside maps, denominators, surveillance context, and field knowledge.

## Self-check questions
1. What problem does SaTScan solve that a visual hotspot map alone does not?
2. What is the most-likely cluster?
3. Why is the maximum spatial window important?
4. When is the Poisson model typically appropriate?
5. Why can a statistically unusual cluster still be operationally misleading?
6. Why should SaTScan results be validated with contextual knowledge?

## Answer key
1. It evaluates whether an apparent cluster is unusually concentrated relative to a formal null model while accounting for repeated scanning.
2. It is the candidate scanning window with the strongest evidence against the null model in the analyzed dataset.
3. Because it determines what sizes of clusters the software is allowed to detect and can strongly shape the output.
4. When case counts and population denominators are available for areas or spatial units.
5. Because the cluster may reflect reporting intensity, screening effort, or denominator artifacts rather than true transmission.
6. Because statistical cluster detection identifies unusual patterning, not the causal explanation for that pattern.

## Further reading
- [SaTScan official site](https://www.satscan.org/)
- [SaTScan user guide](https://www.satscan.org/cgi-bin/satscan/register.pl/SaTScan_Users_Guide.pdf)
- [CRAN rsatscan package](https://cran.r-project.org/package=rsatscan)

## Links to Metis library
- `knowledge/library/methods/spatial-epidemiology.md`
- `knowledge/library/methods/surveillance-systems.md`
- `knowledge/library/methods/outbreak-investigation.md`
