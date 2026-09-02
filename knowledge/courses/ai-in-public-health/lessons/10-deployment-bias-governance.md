# Lesson 10 — Deployment, bias and governance: what happens when it is wrong, and who finds out

> **Concept map**
> **Builds on** — every lesson. Lesson 9 asks whether a model is real; this one asks whether a real model helps anyone, and what the rules are.
> **Connects to** — the consultation deep dive (regulatory class set by the claim), the imaging deep dive (Beede, and the seven conditions), and the database deep dive (label bias).
> **Leads to** — the Atlas, which you should now be able to read end to end.

## Why this matters

This is the last lesson and the one that decides whether any of the others mattered. A model can be well discriminating, well calibrated, externally validated, and have positive net benefit — and still change nothing, or make things worse, because of what happens between the model and the person.

The governing question is not *"is this model good?"* It is:

> **What happens when it is wrong, and who finds out?**

Ask that of every application in the Atlas and the whole catalogue reorganises itself.

## Learning objectives
By the end of this lesson you will be able to:

- **Explain** the AI chasm and why so little health AI has crossed it.
- **Distinguish** label bias, representation bias, deployment bias and feedback loops, with a case for each.
- **Predict** the human-factors failure modes: automation bias, alert fatigue, workarounds.
- **Place** a health-AI product in the EU regulatory tiers, and say what that classification demands.

## Prerequisites
Lesson 9. The three deep dives, ideally — this lesson is largely their generalisation.

---

## Section 1 · The AI chasm

Thousands of published models. A small number in clinical use. A very small number with any published evidence of patient benefit.

That gap has a name — the **AI chasm** — and it is not caused by conservatism. It is caused by the fact that the published output and the deployed requirement are different objects. A paper needs a dataset and a metric. A deployment needs an integration, a threshold, a workflow, a trained user, a monitoring plan, an escalation route, a maintenance budget, and a way of noticing when it breaks.

✱ Recall the validation ladder from Lesson 9. The chasm sits between **rung 4** (external validation) and **rung 6** (impact evaluation), and almost the entire literature lives below it. When someone says "clinically validated", ask which rung.

## Section 2 · Four kinds of bias, and they need different fixes

Collapsing these into "algorithmic bias" is why the discussion so often goes nowhere. They have different mechanisms and different remedies.

**1 · Label bias — the target is wrong.** Obermeyer: cost stood in for need, and access is unequal. The model was excellent. *Fix:* change the target variable. Nothing else works.

**2 · Representation bias — the data is not the population.** Dermatology trained on lighter skin; genomic reference panels; devices calibrated on one group. *Fix:* collect representative data — and first, **measure the subgroup**, because the dermatology lesson was that skin type was often not recorded at all, making the gap invisible rather than known.

**3 · Deployment bias — right model, wrong context.** The Thailand retinopathy study: the model performed as advertised and the clinic could not use it. Image-quality gating rejected a large share of patients, nurses worked around it, connectivity stalled queues. *Fix:* study the workflow before deploying, not after. This is ethnography, not statistics.

**4 · Feedback loops — the model changes the data that trains it.** Predict where crime or disease will be found, send resources there, find more there, confirm the prediction. ✱ The epidemiological version is exact and it is yours: **a model trained on reported cases sends screening teams to where cases were previously reported, which generates more reported cases there, which confirms the model.** Meanwhile unsurveyed areas stay quiet and therefore stay unsurveyed. *Fix:* deliberate exploration — allocate some effort against the model's advice — and monitor for drift. Hard, because it means knowingly spending resources sub-optimally by the model's own criterion.

⚠ Only the first has a clean technical fix. The others need data collection, fieldwork and institutional will.

## Section 3 · Human factors — the model is not the system

Three failure modes, all measurable, all routinely unmeasured.

**Automation bias.** People defer to a confident machine, including against their own correct judgement, and defer more when tired, junior, or busy — i.e. exactly when the model is meant to help. The effect is strongest for **plausible** wrong answers, which is what modern systems produce.

**Alert fatigue.** Once an alert's PPV falls low enough, people stop investigating. This is not a soft concern: **system sensitivity goes to zero regardless of what the model reports.** Lesson 4 gave the arithmetic — eight alerts per true case is a system that will be ignored within weeks.

**Workarounds.** Users route around friction, and the workaround becomes the real workflow while the official one is what gets audited. Beede's Thai clinics are the documented case.

✱ And the one that recurs across this course: **a human-in-the-loop control fails when the loop is the thing being sold.** If the safety case is "the clinician reviews the output" and the product's value proposition is not having to review, the control is decorative. Ambient documentation is the live example.

## Section 4 · The regulatory picture, and the naming problem

You work in the EU, so this part is not abstract.

**Two overlapping regimes.** Software that informs a clinical decision is generally a **medical device** under **MDR**, needing conformity assessment, clinical evaluation and post-market surveillance. Separately, the **EU AI Act** classifies AI systems by risk, and medical AI largely lands in the **high-risk** tier: risk management, data governance, technical documentation, logging, human oversight, accuracy and robustness requirements, post-market monitoring. ⚠ Obligations phase in across 2025–2027; verify current dates before relying on them.

The FDA route is analogous — software as a medical device, with **predetermined change control plans** as the mechanism for models that update.

**And now the problem that runs through this whole course:**

> **The regulatory class is set by the *claim*, not by what the thing can break.**

Call a product "documentation" and it is generally not a device, needing no clinical validation before sale. Call it "diagnosis" and it is high-risk, with an enormous evidence bar. The consultation deep dive is the case: ambient scribes are in hundreds of thousands of consulting rooms while AMIE, with a randomised blinded trial behind it, is deployed nowhere. **The product carrying less oversight is the one in the room with patients.**

✱ So the reviewer's question is never "how is this classified?" but **"what can it break, and does its classification match that?"**

**WHO guidance** is the global-health frame: the 2021 *Ethics and governance of artificial intelligence for health*, and later guidance on large multi-modal models. Non-binding, free, and the right reference when the setting is not the EU.

## Section 5 · What good actually looks like

It is worth ending on the positive case, because the course has spent a lot of time on failures.

**TB chest X-ray CAD** is the one health-AI application to reach a WHO recommendation, and it did so by satisfying, roughly in order:

1. A **target product profile published first**, by the body that would recommend it.
2. A **label independent of the reader being replaced** — bacteriological confirmation.
3. **Multi-site external validation in the deployment population.**
4. **Subgroup performance reported**, including the awkward finding that it does worse where prior TB is common.
5. A **tunable threshold**, set locally from local prevalence.
6. A **confirmatory test downstream** to absorb its errors.
7. A **guideline home**, giving procurement, thresholds and monitoring an institutional owner.

⚠ Note what is absent from that list: any claim about the architecture. None of the seven is about the model.

## Section 6 · What to do — as a researcher, reviewer, or the person asked

**Reviewing a claim.** The four questions from Lesson 1, then: which rung of the validation ladder; what happens when it is wrong; who finds out; and does the classification match the risk.

**Advising a programme.** Ask for the threshold and who set it; the alert burden; the monitoring plan; the escalation route; and who owns it in three years when the vendor has moved on.

**Doing the work yourself.** Report against **TRIPOD+AI**; appraise against **PROBAST+AI**; if it reaches live use, **DECIDE-AI**; if you trial it, **CONSORT-AI**. And write down the objective function.

**Explaining it to others** — the course's actual objective. The most useful thing you can say to a colleague is not that AI is over- or under-hyped. It is: *tell me what happens when it is wrong, and who finds out.* If they cannot answer, the conversation about accuracy is premature.

---

## Key insight

**Nearly every failure in this course is a failure of the surrounding system, not the model** — the label, the acquisition, the threshold, the workflow, the classification, the monitoring. That is why the durable skill is not modelling but the ability to ask where a number came from and what will be done with it.

Which is also why the course does not go out of date. The methods in the Atlas will be replaced. The chasm, the four biases, automation bias, alert fatigue, and the naming problem will not.

---

## Worked example — the feedback loop, in twenty lines

Dataset: 200 villages with a fixed true prevalence, a model that allocates screening to where cases were previously found, and no exploration. Watch what the surveillance data become.

### In R

```r
library(tidyverse)

set.seed(19)
n_villages <- 200

# True, FIXED prevalence. Nothing about the disease changes during this loop.
villages <- tibble(
  id    = 1:n_villages,
  truth = rgamma(n_villages, shape = 1.2, scale = 0.8)   # cases per 1000, latent
)

# Start with one round of uniform screening, so every village has a record.
state <- villages |> mutate(screened = 1, observed = rpois(n(), truth * 1))

# ---- The loop: allocate next round's effort to where cases were found ------
# This is the obvious, defensible, locally rational policy. Follow it for
# fifteen rounds with NO exploration and watch the data drift away from truth.
for (round in 1:15) {
  state <- state |>
    mutate(rate_seen = observed / screened,
           # top 40 villages by observed rate get screened; the rest get nothing
           effort    = if_else(rank(-rate_seen, ties.method = "first") <= 40, 1, 0)) |>
    mutate(screened = screened + effort,
           observed = observed + rpois(n(), truth * effort))
}

# ---- What the surveillance system now believes ----------------------------
state |>
  mutate(never_rescreened = screened == 1,
         apparent_rate    = observed / screened) |>
  summarise(
    villages_abandoned      = sum(never_rescreened),
    mean_truth_abandoned    = mean(truth[never_rescreened]),
    mean_truth_screened     = mean(truth[!never_rescreened]),
    corr_apparent_vs_truth  = cor(apparent_rate, truth)
  )
# Expect: a large block of villages screened once and never again, whose TRUE
# prevalence is not zero -- it was just never observed again. The apparent rate
# and the truth decouple, and the model's own data confirm the model.

# ---- The fix, and its cost ------------------------------------------------
# Reserve some effort for villages the model does not favour. Rerun with, say,
# 30 model-chosen and 10 randomly chosen villages per round and compare
# corr_apparent_vs_truth. It improves -- and you screened fewer of the
# villages the model considered highest-yield. That trade is the whole
# governance problem in one line.
```

⚠ Not executed here. The mechanism is forced by the construction: villages that stop being screened cannot generate observations, so their apparent rate freezes while the truth is unchanged.

---

## Exercises

**Recall.** Name the four kinds of bias and the distinct fix each requires.

**Application.** Take an AI application from the Atlas and answer the governing question in two sentences: what happens when it is wrong, and who finds out?

**Application.** Run the feedback-loop example, then add the exploration arm. Quantify what you gave up and what you gained, and decide which you would defend to a programme manager.

**Conceptual.** Argue that ambient documentation should be regulated as a medical device. Then argue the opposite. Which argument would you actually make, and to whom?

**Challenge.** Write the seven-condition checklist from Section 5 as a one-page appraisal form, and apply it to a health-AI product being offered to your institution. Note which conditions you cannot assess from the material the vendor supplied — that absence is itself the finding.

---

## Connection to the course spine

The spine says that what decides whether an AI application works is never the model, it is the evaluation. This lesson extends the claim by one step: **beyond evaluation lies the system**, and most of what determines benefit lives there — in the threshold, the workflow, the classification and the monitoring.

And it closes the first half too. Six shapes, six evaluation debts, and now one governing question that applies to all six identically. That is the whole course, and it is short enough to carry into any meeting.

---

## Sources

⚠ Written from model knowledge to mid-2026, not verified. Leads, not citations. Regulatory dates in particular must be checked.

**Start here**

- **WHO.** *Ethics and governance of artificial intelligence for health* (2021), and the later guidance on large multi-modal models. Free, and the right global-health reference.
- **Beede E, Baylor E, Hersch F, Iurchenko A, Wilcox L, Ruamviboonsuk P, Vardoulakis LM.** *A human-centered evaluation of a deep learning system deployed in clinics for the detection of diabetic retinopathy.* **CHI '20**; doi:10.1145/3313831.3376718. ✓ Verified — 11 clinics in Pathum Thani and Chiang Mai. The single best account of deployment reality.
- **Obermeyer Z, et al.** **Science** 2019 — label bias, with its fix.

**Regulation**

- **EU AI Act** (Regulation 2024/1689) — the high-risk tier and its obligations.
- **EU MDR** (2017/745) — when software becomes a device.
- **FDA** guidance on clinical decision support and on predetermined change control plans.
- **Gilbert S, Harvey H**, and colleagues on regulating adaptive medical AI in the EU and UK.

**Reporting and appraisal frameworks**

- **TRIPOD+AI** (Collins et al., BMJ 2024) · **PROBAST+AI** · **DECIDE-AI** (Vasey et al., BMJ
2022) · **CONSORT-AI / SPIRIT-AI** (Liu, Cruz Rivera, Moher, Calvert, Denniston, Nature Medicine 2020).

**Human factors and the chasm**

- **Coiera E** on automation bias and clinical decision support.
- **Topol EJ.** *High-performance medicine: the convergence of human and artificial intelligence.* **Nature Medicine** 2019 — for the optimistic framing, read against Beede.
- **Wiens J, Saria S, Sendak M, et al.** *Do no harm: a roadmap for responsible machine learning for health care.* **Nature Medicine** 2019.

**Books**

- **Wachter R.** *The Digital Doctor* (2015). How clinical software reshapes clinical work in ways nobody intended. Pre-LLM and still the most useful book here.
- **O'Neil C.** *Weapons of Math Destruction* (2016) — feedback loops, non-technically.
- **Kearns M, Roth A.** *The Ethical Algorithm* (2019).

---

## Retain long-term

- The governing question: what happens when it is wrong, and who finds out?
- The AI chasm sits between external validation and impact evaluation, and almost the whole literature is below it. Ask which rung.
- Four biases, four fixes: label bias → change the target; representation bias → measure then collect; deployment bias → study the workflow first; feedback loops → deliberate exploration.
- A model trained on reported cases sends teams where cases were reported, generating more reports there, confirming itself.
- Automation bias is strongest for plausible wrong answers, and worst when users are tired or junior.
- Once alert PPV falls far enough, system sensitivity goes to zero regardless of the model.
- A human-in-the-loop control fails when the loop is the thing being sold.
- The regulatory class is set by the claim, not by what the thing can break — so ask whether the classification matches the risk.
- TB CAD reached a WHO recommendation on seven conditions, none of which is about the architecture.
- Nearly every failure in this course is a failure of the surrounding system, not the model.
