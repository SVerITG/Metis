# Experimental Studies

## Learning objectives
- Distinguish randomized, cluster-randomized, stepped-wedge, and quasi-experimental designs.
- Explain why randomization strengthens causal inference.
- Recognize implementation issues that affect validity in public-health trials.
- Identify when experimental designs are feasible, ethical, and worth the added complexity.

## Prerequisites
- Study designs overview.
- Basic understanding of confounding and temporality.

## Content

### Section 1: What makes a study experimental
An experimental study actively assigns or introduces an intervention rather than only observing existing exposure patterns. The classic example is the randomized controlled trial, in which participants are allocated to intervention or comparison groups and then followed for outcomes.

This is different from observational epidemiology. In observational studies, exposure already exists and investigators try to account for differences between groups. In an experiment, the design itself helps create comparable groups.

That is why experimental studies are often treated as especially strong for causal inference. They do not solve every problem, but they can reduce one of the biggest problems in epidemiology: confounding.

### Section 2: Why randomization matters
Randomization helps distribute known and unknown confounders more evenly between groups. If done properly, it reduces the chance that one group starts out systematically healthier, wealthier, more adherent, or otherwise different in ways that would bias the result.

This does not mean trials are automatically unbiased. Randomization does not fix:

- poor outcome measurement
- contamination between groups
- non-adherence
- missing data
- loss to follow-up
- weak implementation

So the right message is not "randomization makes bias disappear." The right message is that randomization improves the starting comparability of groups, which strengthens internal validity when the rest of the trial is also done well.

### Section 3: Individual randomized controlled trials
In an **individually randomized controlled trial**, each participant is allocated separately to intervention or control. This design works well when the intervention is delivered at the individual level, contamination is limited, and the research team can manage recruitment, allocation, and follow-up reliably.

Examples include:

- a vaccine trial
- a drug efficacy trial
- an individually delivered counseling intervention

These trials are often considered the benchmark for efficacy questions. However, they may be less suitable for system-level public-health interventions such as district screening workflows, school-based programs, or health-facility process changes.

### Section 4: Cluster-randomized trials
In a **cluster-randomized trial**, whole groups are randomized rather than individuals. Clusters might be villages, clinics, schools, districts, or health areas.

This design is useful when:

- the intervention is naturally delivered at group level
- individual randomization is impractical
- contamination between individuals would be likely

For example, if a district wants to compare a new community screening strategy with standard care, randomizing whole health areas may be more realistic than trying to randomize individual residents.

Cluster trials come with statistical and operational consequences. Outcomes within a cluster tend to be correlated, so the effective sample size is smaller than the raw number of participants suggests. That is why cluster trials require attention to intraclass correlation, design effect, and cluster-level implementation fidelity.

### Section 5: Stepped-wedge designs
A **stepped-wedge trial** is a type of cluster trial in which all clusters eventually receive the intervention, but the timing of rollout is randomized or otherwise structured in phases. At any given point, some clusters are still in the control period while others have crossed into the intervention period.

This design is attractive when:

- withholding the intervention permanently is politically or ethically difficult
- rollout must happen gradually because of resources or logistics
- decision-makers want every cluster to receive the programme eventually

The main challenge is time. If disease patterns or service performance are changing anyway, separating intervention effects from secular trends can be difficult. Stepped-wedge designs are often appealing in principle but analytically demanding in practice.

### Section 6: Quasi-experimental designs
Not every intervention can be randomized. Governments may launch a policy nationwide. A programme may already be committed before evaluation begins. In those situations, epidemiologists often use **quasi-experimental** designs.

Examples include:

- interrupted time series
- controlled before-after studies
- difference-in-differences approaches
- natural experiments

These designs do not provide the same protection against confounding as well-run randomized trials, but they can still be powerful when the intervention timing is clear, comparison groups are sensible, and secular trends are handled explicitly.

### Section 7: Worked example - screening intervention in health areas
Imagine a sleeping sickness programme wants to evaluate whether mobile community screening improves confirmed case detection compared with passive detection alone.

An individually randomized trial would be awkward because screening is delivered through local teams and community outreach, not as a private intervention to isolated individuals.

A more realistic design would be a **cluster-randomized trial** in which health areas are randomized to:

- standard passive detection
- passive detection plus periodic mobile screening

Outcomes might include:

- confirmed cases detected
- time from symptoms to diagnosis
- proportion completing confirmatory referral

If all areas are expected to receive mobile screening eventually, a **stepped-wedge** design could be considered instead. That may be operationally attractive, but only if the team can manage the timing and analysis carefully.

The lesson is practical: experimental design should fit how the intervention is actually delivered.

### Section 8: Implementation issues that shape validity
Trials succeed or fail on implementation details as much as on allocation.

Important concepts include:

- **allocation concealment:** preventing foreknowledge of assignment during enrollment
- **blinding:** reducing biased outcome measurement or differential behavior when feasible
- **adherence:** whether participants or clusters actually receive the intervention as intended
- **contamination:** whether control participants are exposed to the intervention
- **fidelity:** whether the intervention was implemented in the planned way

In pragmatic public-health trials, blinding is often difficult or impossible. That makes objective outcomes, strong protocols, and transparent reporting even more important.

### Section 9: Ethics and generalizability
Experimental studies also raise ethical questions. Randomization is not always acceptable when an intervention is already known to be beneficial, when equipoise is absent, or when communities are not meaningfully involved in design decisions.

Even when trials are internally strong, generalizability can still be limited. A tightly controlled efficacy trial may not reflect the messier conditions of routine service delivery. That is why public-health researchers often distinguish **efficacy** from **effectiveness** and value pragmatic designs that resemble real implementation settings.

### Section 10: How to read an experimental study critically
When reading a trial or quasi-experiment, ask:

1. Was the intervention assigned in a credible way?
2. Were groups comparable at baseline?
3. Could contamination or non-adherence dilute the effect?
4. Were outcomes measured consistently and objectively?
5. Does the reported effect reflect efficacy under ideal conditions or effectiveness in real-world settings?
6. Are the conclusions consistent with the design's actual strengths and limits?

These questions help separate the prestige of a "trial" label from the actual quality of the evidence.

## Key takeaways
- Experimental studies assign interventions rather than only observing exposures.
- Randomization improves group comparability and strengthens causal inference, but does not eliminate all sources of bias.
- Cluster-randomized and stepped-wedge designs are often more realistic than individual randomization for public-health delivery interventions.
- Quasi-experimental designs are valuable when randomization is impossible, but they require careful handling of trends and comparison groups.
- Validity depends on implementation details such as adherence, contamination, fidelity, and outcome measurement.

## Self-check questions
1. What distinguishes an experimental study from an observational study?
2. Why does randomization strengthen causal inference?
3. Why might a cluster-randomized design be better than individual randomization for a district-level intervention?
4. What is the main attraction of a stepped-wedge design?
5. Why can a randomized trial still produce biased results?
6. What is one major difference between efficacy and effectiveness?

## Answer key
1. An experimental study actively assigns an intervention, whereas an observational study measures exposures that already exist.
2. Because it helps balance confounding factors between groups at baseline, improving comparability.
3. Because the intervention may be delivered through clinics, schools, or health areas, and individual randomization could be impractical or prone to contamination.
4. All clusters eventually receive the intervention, which can make phased implementation more acceptable operationally or ethically.
5. Because problems such as poor measurement, contamination, non-adherence, attrition, or weak implementation can still distort the result.
6. Efficacy refers to performance under controlled conditions, while effectiveness refers to performance in real-world practice.

## Further reading
- [CONSORT Statement](https://www.consort-statement.org/)
- [Cochrane Handbook](https://training.cochrane.org/handbook/current)
- [BMJ overview of stepped-wedge trials](https://www.bmj.com/content/350/bmj.h391)

## Links to Metis library
- `06_library/methods/study-designs.md`
- `06_library/concepts/research-ethics.md`
- `06_library/methods/causal-inference.md`
