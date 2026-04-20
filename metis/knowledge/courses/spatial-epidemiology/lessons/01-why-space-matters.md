# Why Space Matters

## Learning objectives
- Explain why health events often cluster geographically.
- Distinguish place as exposure, context, and delivery system.
- Recognize common spatial pitfalls such as ecological fallacy and the modifiable areal unit problem.
- Frame spatial analysis as a substantive epidemiologic question rather than as map-making for its own sake.

## Prerequisites
- Basic epidemiology.

## Content

### Section 1: Why geography belongs in epidemiology
Health outcomes are rarely distributed randomly in space. Vectors, reservoirs, climate, land use, poverty, transport networks, and health services are unevenly distributed, so risk is unevenly distributed as well. Spatial epidemiology studies those geographic patterns and asks whether location is part of the explanation, the intervention pathway, or both.

This matters because "place" is not just a background label. It can influence exposure, care access, surveillance sensitivity, and transmission opportunity. For many diseases, where people live, move, work, or seek care is part of the causal story.

### Section 2: Place can mean different things
In applied epidemiology, space can matter in at least three distinct ways.

First, place can be an **exposure context**. Living near riverine vector habitat, mining areas, or polluted water sources may directly alter risk.

Second, place can represent **social and environmental context**. Neighborhood deprivation, remoteness, conflict, and transportation barriers shape behavior and outcomes even when they are not direct biologic exposures.

Third, place can represent a **delivery system**. District boundaries, facility catchments, and referral routes shape what gets detected, reported, and treated.

These distinctions are important because a map can reflect transmission, service access, reporting intensity, or some mixture of all three.

### Section 3: Why nearby places resemble each other
Neighboring areas often look similar because many drivers are spatially structured. Rainfall, altitude, roads, vector habitat, and program management rarely stop neatly at administrative borders.

This creates **spatial autocorrelation**, meaning nearby observations may be more similar than distant ones. In practical terms, cases in one village may tell you something about nearby villages even before any formal model is fit.

This is one reason ordinary statistical assumptions of independence can break down in spatial data.

### Section 4: Worked example - HAT and focal transmission
Human African trypanosomiasis is a useful example because risk is strongly focal. Transmission depends on tsetse habitat, human movement, contact with riverine or forested areas, and access to detection services.

If cases are mapped only at district level, two problems can arise:

- micro-hotspots may be hidden within large administrative units
- apparent "high-burden" districts may simply reflect larger populations or stronger surveillance

This is why spatial epidemiology is not just about drawing a map. It is about matching spatial scale to the epidemiologic question.

### Section 5: Aggregation and the modifiable areal unit problem
Administrative units are analytic conveniences, not natural truths. A pattern visible at one scale may disappear or reverse at another. This is part of the **modifiable areal unit problem (MAUP)**.

For example, village-level clustering may disappear when data are aggregated to district level. Conversely, a district-level hotspot may be driven by only one small area within the district.

This means that results can depend on how boundaries are drawn and what level of aggregation is chosen. Analysts therefore need to justify spatial scale rather than treating it as fixed or neutral.

### Section 6: Ecological thinking and ecological fallacy
Spatial epidemiology often uses areal data, such as district incidence rates or province-level coverage indicators. These summaries can be useful, especially for planning and surveillance. But they carry a classic risk: the **ecological fallacy**.

An association observed between areas does not automatically hold for individuals within those areas. A district with higher poverty and higher incidence does not prove that the poorest individuals are the ones at highest risk in that dataset.

Ecological summaries are still useful, but they need to be interpreted at the level they were measured.

### Section 7: Why spatial analysis starts with a question
Maps are persuasive, which is why they can also mislead. Before creating a spatial analysis, ask:

- what is the spatial unit that matches the question?
- am I mapping counts, rates, or smoothed estimates?
- am I trying to describe pattern, identify clusters, assess access, or test a hypothesis?
- could the pattern reflect surveillance artifacts rather than true transmission?

Good spatial epidemiology starts with a question about process, not a desire to produce a visually attractive map.

### Section 8: Common beginner mistakes
Several mistakes recur often.

- treating administrative boundaries as natural epidemiologic units
- mapping counts without denominators
- assuming a hotspot map automatically proves local transmission
- ignoring spatial autocorrelation in later analysis
- confusing ecological summaries with individual-level evidence

The practical habit is to keep asking what the map actually represents: exposure, access, population size, reporting intensity, or some mixture of these.

## Key takeaways
- Space matters because exposures, context, and health systems are unevenly distributed geographically.
- Place can act as exposure, context, or delivery structure, and these should not be confused.
- Nearby places often resemble each other, creating spatial dependence.
- Aggregation choices can change what patterns appear, which is why scale matters.
- Spatial analysis should begin with a substantive epidemiologic question, not only a mapping exercise.

## Self-check questions
1. Name two ways in which place can matter in epidemiology besides direct biologic exposure.
2. What is spatial autocorrelation?
3. Why can district-level maps hide important local patterns?
4. What is the modifiable areal unit problem?
5. Why is ecological fallacy a risk in spatial epidemiology?
6. Why should a map of counts usually be interpreted cautiously?

## Answer key
1. Place can matter through social and environmental context, or through health-service and surveillance structure.
2. It is the tendency for nearby observations or areas to be more similar than distant ones.
3. Because aggregation can mask village- or neighborhood-level hotspots and create misleading averages across large areas.
4. It is the problem that results can change depending on how spatial units are defined or aggregated.
5. Because area-level associations do not automatically apply to individuals within those areas.
6. Because raw counts often reflect population size or surveillance intensity rather than underlying risk alone.

## Further reading
- [CRAN sf package](https://cran.r-project.org/package=sf)
- [SaTScan home page](https://www.satscan.org/)
- [OpenIntro Statistics](https://www.openintro.org/book/os/)

## Links to Metis library
- `06_library/methods/spatial-epidemiology.md`
- `06_library/methods/gis-for-epidemiology.md`
- `06_library/methods/surveillance-systems.md`
