# Deep-dive contract

**This course is for understanding, not memorising.** The statistics course is drill —
concepts that must be automatic, learned by heart, executed. This one is different: the researcher
wants to *discover and understand* — the science and the application, **from research
question to conclusion** — and to judge what each AI application could actually be worth.

So the deep dive, not the core-track lesson, is the heart of this course. The core track
teaches the vocabulary needed to read a deep dive. The deep dives are what there is to
learn.

Execution matters least. Code appears only when running it is the fastest way to
understand something, never as an exercise for its own sake.

---

## The arc every deep-dive page follows

Ten sections, always in this order, because the order *is* the argument — you cannot judge
a result before you know what question it answered and what data it had.

1. **The question someone actually asked.** Stated as a research question, in the context
   of the person asking. Not "can AI detect X" but the real operational or scientific need.
2. **Why it looked tractable.** What made this a plausible AI problem at that moment —
   which is often about data availability rather than about method.
3. **The data.** Where it came from, what it actually represents, and — the part that
   usually explains everything later — what it does not represent.
4. **The method, explained.** Enough that you understand the mechanism, not just its name.
   If the method cannot be explained in plain prose, that is itself a finding.
5. **What they found.** The headline result, stated as its authors stated it.
6. **How it was evaluated.** The four questions, and whether the shape's debt was paid.
7. **What happened next.** Deployment, replication, regulation, collapse. This section is
   where most of the learning is, and where most published accounts stop.
8. **What it is actually worth.** The honest assessment of potential: what this application
   can change, what it cannot, and the conditions under which the answer flips. **The
   section this course exists for.**
9. **Transferable lessons.** What to steal, and what to avoid, in your own work.
10. **Atlas placement.** Shape, maturity, and which cross-cutting layer it stresses most.

## Style rules

- **Explain, don't assert.** Every claim carries its mechanism. "It failed because of
  algorithm drift" is an assertion; explaining that Google's own autocomplete changed what
  people searched for, which changed the predictors under a fixed model, is an explanation.
- **Name the counterfactual.** What would have happened without the AI? Usually the honest
  comparator is a person doing the task adequately.
- **Distinguish "did not work" from "was not tried properly".** These have opposite
  implications for potential.
- **Quantify potential in the units of the decision** — cases found per 1,000 screened,
  clinician-hours saved, days of lead time — not in AUC.
- **Flag every unverified specific.** Written from model knowledge; marked as leads.
