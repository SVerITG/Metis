# Causation

## Learning objectives
- Explain why association alone is not enough to justify a causal claim.
- Use Bradford Hill viewpoints and modern causal models as aids to judgment rather than mechanical checklists.
- Describe how counterfactual thinking, DAGs, and target-trial framing sharpen causal questions.
- Recognize how epidemiologists support action under uncertainty without pretending certainty where it does not exist.

## Prerequisites
- Bias and confounding.
- Basic familiarity with study designs and measures of association.

## Content

### Section 1: From association to causal claims
Epidemiology often begins with an observed association: exposure and outcome occur together more or less often than expected. But causal inference asks a stronger question: what would happen to the outcome if the exposure or intervention were different?

That is the key move from description to causation. A causal claim is not simply "these variables are related." It is "changing this exposure would change this outcome, all else equal."

This is difficult because we never observe the same person both exposed and unexposed at the same moment. Causal inference therefore depends on comparison groups, assumptions, and design quality. Strong causal reasoning requires more than statistical significance. It requires a credible account of why the observed comparison approximates the contrast we actually care about.

### Section 2: Why association is not causation
Associations can arise for many reasons besides causation.

- the exposure may truly cause the outcome
- the outcome may influence the exposure
- a third variable may confound the relationship
- selection processes may distort the comparison
- measurement error may create a spurious association
- chance may produce an unstable result

This is why epidemiologists do not ask only, "Is there an association?" They also ask, "Could this association be explained another way?"

The quality of a causal claim depends on how well those alternative explanations have been addressed.

### Section 3: Bradford Hill viewpoints
The Bradford Hill viewpoints remain useful because they structure judgment. They are not a checklist that mechanically proves causation, but they help organize evidence from multiple angles.

The viewpoints include:

- strength of association
- consistency across studies and settings
- temporality
- biological gradient
- plausibility
- coherence
- experimental evidence
- analogy
- specificity

Of these, **temporality** is the only necessary one in the strict sense: the cause must precede the outcome.

The smoking and lung cancer evidence is still a classic teaching example because several Hill viewpoints aligned. Associations were strong, replicated, temporally sensible, dose-responsive, biologically plausible, and supported by later experimental and policy evidence. No single viewpoint proved causation on its own; together they built a compelling causal case.

### Section 4: Counterfactual thinking
Modern causal inference often uses the **counterfactual** or **potential outcomes** framework. The central idea is simple: the causal effect is the difference between what would happen to the same unit under one exposure state and what would happen under another exposure state.

That ideal comparison is impossible to observe directly for one individual, so epidemiologists estimate average effects by comparing groups under assumptions such as:

- **exchangeability:** comparison groups are comparable, at least conditional on measured variables
- **positivity:** each relevant covariate pattern has a chance of receiving each exposure or intervention
- **consistency:** the exposure being studied is well defined

These assumptions make causal inference more explicit. They also remind us that a model cannot rescue a vague causal question.

### Section 5: DAGs and explicit assumptions
Directed acyclic graphs, or DAGs, help turn causal assumptions into visual structure. They are useful because they force analysts to say what causes what, what is a confounder, what is a mediator, and what should not be adjusted for.

DAGs help answer practical questions such as:

- which variables block backdoor paths?
- which variables are mediators and should not be adjusted away?
- where might collider bias appear?

This matters because adjustment is not automatically beneficial. A badly chosen adjustment set can introduce bias instead of removing it. DAG thinking helps epidemiologists move from "adjust for everything available" to "adjust for what the causal structure requires."

### Section 6: Target-trial thinking
One of the most useful modern ideas is to frame an observational causal study as the emulation of a hypothetical trial. This is often called **target-trial emulation**.

The idea is practical: before fitting a model, specify the trial you wish you could run.

That means being explicit about:

- eligibility criteria
- time zero
- intervention strategies
- follow-up
- outcomes
- causal estimand

This approach is valuable because many observational analyses fail before modeling begins. If eligibility, time zero, or treatment strategies are vague, bias can enter through immortal time, selection, or inconsistent definitions. Target-trial thinking improves causal clarity even when randomization is impossible.

### Section 7: Worked example - smoking and lung cancer
The link between smoking and lung cancer is one of the most influential causal arguments in epidemiology. The case was not built from one perfect study. It emerged from converging evidence:

- strong associations in observational studies
- consistent findings across settings
- clear temporality
- dose-response patterns
- biological plausibility
- reductions in risk after cessation

This is a good teaching example because it shows how causal judgment often accumulates across study designs, subject-matter knowledge, and intervention relevance. It also shows that public-health action sometimes becomes justified well before perfect certainty exists.

### Section 8: Worked example - causal thinking in programme evaluation
Imagine a post-elimination surveillance programme introduces community alerts plus rapid investigation of suspect cases. Routine data show fewer delayed diagnoses after implementation.

Is the intervention causal? Maybe, but not automatically.

An epidemiologist would ask:

- did time zero align with the implementation date?
- were case definitions stable before and after?
- were there concurrent changes in diagnostics or staffing?
- what comparison group or trend information is available?
- what exactly is the causal effect of interest?

This is why causal inference is a design problem before it is a modeling problem. The strongest question is not "What regression should I run?" It is "What comparison would make this estimate interpretable as an effect?"

### Section 9: Causation and public-health decision making
Public health rarely gets to wait for perfect evidence. Action is often needed under uncertainty. The task is therefore not to eliminate uncertainty completely, but to judge whether the causal case is strong enough for the decision at hand.

That threshold depends on context. A low-cost, low-harm intervention may justify action with moderate evidence. A costly or potentially harmful intervention demands more certainty. Epidemiologic reasoning therefore combines effect size, bias assessment, plausibility, equity implications, feasibility, and consequences of delay.

Good causal reasoning is disciplined, but it is also decision-aware.

## Key takeaways
- A causal claim asks what would happen under a different exposure or intervention, not just whether two variables are associated.
- Bradford Hill viewpoints help structure causal judgment but do not function as a proof checklist.
- Counterfactual thinking, DAGs, and target-trial framing make causal assumptions more explicit.
- Causal inference depends on design quality, comparability, and clear definition of the intervention and estimand.
- Public-health action often requires reasoned causal judgment under uncertainty rather than impossible certainty.

## Self-check questions
1. Why is association alone insufficient for a causal claim?
2. Which Bradford Hill viewpoint is generally considered necessary?
3. What does counterfactual thinking add to epidemiologic reasoning?
4. Why can adjusting for more variables sometimes worsen causal inference?
5. What does target-trial thinking force researchers to clarify before analysis?
6. Why might a public-health programme act on imperfect causal evidence?

## Answer key
1. Because associations may also be produced by confounding, bias, reverse causation, or chance rather than by a true causal effect.
2. Temporality, because the cause must precede the outcome.
3. It reframes causation as a comparison between potential outcomes under different exposure states, making assumptions about comparability and intervention clearer.
4. Because some variables are mediators or colliders, and adjusting for them can block causal pathways or introduce bias.
5. Eligibility criteria, time zero, intervention strategies, follow-up, outcomes, and the exact causal estimand.
6. Because waiting for perfect certainty may cause preventable harm, especially when the intervention is plausible, low-risk, and the cost of inaction is high.

## Further reading
- [Causal Inference: What If](https://miguelhernan.org/whatifbook)
- [BMJ TARGET statement](https://www.bmj.com/content/390/bmj-2025-087179)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)
- [DAGitty](https://dagitty.net/)

## Links to Metis library
- `06_library/methods/causal-inference.md`
- `06_library/methods/study-designs.md`
- `06_library/concepts/research-ethics.md`
