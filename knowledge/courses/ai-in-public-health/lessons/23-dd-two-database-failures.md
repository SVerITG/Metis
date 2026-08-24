# Deep dive — Two database failures: the model nobody checked, and the model that answered the wrong question

**Shape 3** (assign a label, from tables) · Maturities **⚰️ both effectively withdrawn** ·
Stresses **evaluation** and **deployment & governance**

> ⚠ Written from model knowledge to mid-2026. Figures are leads to verify; several are
> *derived* below rather than quoted, and those are marked. The mechanisms are the durable content.

Tabular prediction on health databases is the least glamorous shape and by far the most
deployed. Its two most consequential failures happened within two years of each other, and
they are **opposite**:

- The **Epic Sepsis Model** was a competent model that **nobody validated externally** before
  running it on millions of patients.
- **Obermeyer et al.'s** algorithm was validated, performed excellently at what it was asked
  to do, and was asked **the wrong question**.

Learn to tell those two apart and you can triage almost any claim in this shape. One is a
governance failure, the other a construct-validity failure, and no amount of the fix for one
addresses the other.

---

## 1 · The questions someone actually asked

**Epic.** Sepsis kills, deteriorates fast, and is treatable if caught early. Hospitals hold
continuous EHR data — vitals, labs, orders, notes. The question: *can we flag deteriorating
patients earlier than the clinical team notices?*

**Obermeyer.** US health systems run care-management programmes: intensive nursing,
coordination, home visits for the patients who need it most. Capacity is far smaller than
need. The question: *which patients should be enrolled?*

✱ Note the second one is shape 3 **serving shape 6**. It assigns a score, but the score
allocates a scarce good. That is why its failure mode is distributional rather than clinical —
and why "the model is accurate" was never a sufficient defence.

## 2 · Why each looked tractable

Both had the same enabling condition: **the data already existed, at enormous scale, for
another purpose.** Epic's EHR covers a very large share of US hospitalisations; insurers hold
claims for tens of millions of people.

⚠ Hold on to *for another purpose*. Neither dataset was collected to answer the question being
asked, and in both cases the mismatch is the failure.

## 3 · The data, and what it does not represent

**Epic.** Routine EHR fields. And here is the first crack: to train a sepsis model you need a
sepsis label, and there is no biological sepsis test. So the outcome was defined
**administratively** — from what clinicians *did*: antibiotics ordered, blood cultures drawn,
billing codes applied.

> The model was therefore trained to predict **clinician recognition of sepsis**, not sepsis.

Those coincide only when clinicians recognise sepsis promptly — which is precisely the
situation where you did not need the model.

**Obermeyer.** Insurance claims: diagnoses, utilisation, and **total healthcare cost**. The
target was next-year cost, used as a stand-in for next-year health need.

What cost does not represent: **need in a population with unequal access.** At equal illness,
less is spent on Black patients — less access, less trust, shorter visits, fewer referrals,
more unmet need. So cost is a *biased* measure of need, and the bias has a direction.

## 4 · The methods, explained

Unremarkable in both cases, which is the point.

**Epic** used a proprietary gradient-boosted-style risk score over EHR features, producing a
0–100 output with a configurable alert threshold (commonly 6). Proprietary matters: the feature
list and weights were not published, so nobody outside could inspect what it used.

**Obermeyer's** algorithm was a straightforward regression predicting next-year cost from prior
claims. The authors' key move was not modelling at all — it was to obtain the model's
**predictions alongside independent measures of actual health** (chronic conditions, biomarkers)
and ask whether patients at the same score were equally sick.

✱ That is the transferable technique: **audit a model by comparing its score against a
construct it was not trained on.** You do not need the weights. You need the predictions and
an independent yardstick.

## 5 · What each found

**Epic**, per the vendor: AUC in the high 0.70s to low 0.80s. Deployed at hundreds of
hospitals on that basis.

**Epic**, on external validation (Wong et al., large US academic health system): **AUC ≈ 0.63**,
poor calibration, and at the deployed threshold **sensitivity ≈ 33%** while alerting on
**≈18% of all hospitalised patients.** It identified only a small fraction of sepsis cases that
clinicians had not already caught.

Those three numbers imply the rest. Taking sepsis at ~7% of admissions — *derived, not quoted*:

| Per 1,000 admissions | Count |
|---|---|
| Alerts fired | **180** |
| Alerts that were real sepsis | **23** |
| False alarms | **157** |
| Sepsis cases missed entirely | **47** |
| Alerts per true case | **≈8** |
| Implied PPV of an alert | **≈13%** |

**Obermeyer**: at any given risk score, Black patients had substantially more active chronic
conditions than White patients — around **26% more**. Among patients automatically flagged for
the programme, **17.7% were Black**; correcting the target raised that to **46.5%** — a
**2.6-fold** change. Retraining on a health-based rather than cost-based label removed roughly
**84%** of the disparity.

⚠ Verify those four figures before citing; they are the ones most often mis-quoted.

## 6 · How each was evaluated

| Question | Epic Sepsis Model | Obermeyer's algorithm |
|---|---|---|
| **Comparator** | Clinician recognition — which was also the *label* | Current practice |
| **Reference standard** | Administrative sepsis definition, i.e. clinician action | Cost (target) vs independent health measures (audit) |
| **External validation** | **None before deployment.** Done years later, by outsiders | Not needed to find the fault — the audit was the finding |
| **Calibration** | Not reported by the vendor; poor when measured | N/A |
| **Subgroups** | Not reported | **The entire finding** |
| **Shape 3's debt paid?** | **No** | Yes on discrimination — and irrelevant, because the target was wrong |

<svg viewBox="0 0 720 300" width="100%" style="max-width:720px" role="img" aria-label="The validation ladder, showing the Epic Sepsis Model stopping at internal validation while being marketed as if impact-evaluated"><text x="8" y="16" font-size="11" font-weight="600" fill="currentColor">The validation ladder — and where each rung actually gets you</text><line x1="42" y1="252" x2="42" y2="34" stroke="currentColor" stroke-width="1.2"/><g font-size="10" fill="currentColor"><text x="56" y="248">1 · Apparent performance — evaluated on training data. Meaningless.</text><text x="56" y="212">2 · Internal validation — cross-validation. Corrects optimism, not transfer.</text><text x="56" y="176">3 · Temporal validation — a later period. Catches drift.</text><text x="56" y="140">4 · External validation — a different site. Catches local practice.</text><text x="56" y="104">5 · Prospective evaluation — deployed, outcomes measured forward.</text><text x="56" y="68">6 · Impact evaluation — a trial. Does using it change outcomes?</text></g><g fill="currentColor"><circle cx="42" cy="245" r="3.5"/><circle cx="42" cy="209" r="3.5"/><circle cx="42" cy="173" r="3.5" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="42" cy="137" r="3.5" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="42" cy="101" r="3.5" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="42" cy="65" r="3.5" fill="none" stroke="currentColor" stroke-width="1.4"/></g><rect x="470" y="198" width="240" height="24" rx="3" fill="currentColor" opacity="0.14"/><rect x="470" y="198" width="240" height="24" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"/><text x="590" y="214" font-size="9.5" text-anchor="middle" fill="currentColor">ESM reached HERE before deployment</text><rect x="470" y="54" width="240" height="24" rx="3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-dasharray="5 3"/><text x="590" y="70" font-size="9.5" text-anchor="middle" fill="currentColor">…and was sold as if it were HERE</text><path d="M590 196 L590 80" stroke="currentColor" stroke-width="1" stroke-dasharray="3 3" opacity="0.6"/><text x="8" y="278" font-size="9.5" fill="currentColor" opacity="0.85">Four rungs of evidence were skipped, and the product was in hundreds of hospitals throughout.</text><text x="8" y="292" font-size="9.5" fill="currentColor" opacity="0.85">External validation was eventually done — by researchers with no commercial relationship to the vendor.</text></svg>

## 7 · What happened next

**Epic.** The external validation was widely covered, the vendor disputed the methodology, and
the model was revised. The durable change was reputational and regulatory: it became the
standard citation for why proprietary clinical AI needs independent validation, and it
sharpened attention on tools that inform clinical decisions without being regulated as devices.

**Obermeyer.** Unusually, the paper came with a **fix**: relabel. Predict a health measure
instead of cost and most of the disparity disappears. The authors worked with the manufacturer
on it. It became the canonical algorithmic-bias case, cited in regulation, and the origin of a
now-standard audit question: *what is the target variable, and what do you actually care about?*

<svg viewBox="0 0 720 250" width="100%" style="max-width:720px" role="img" aria-label="Diagram showing healthcare need being substituted by healthcare cost, with unequal access as the wedge that makes cost a biased proxy"><text x="8" y="16" font-size="11" font-weight="600" fill="currentColor">The label substitution — and the wedge that makes it biased</text><rect x="8" y="32" width="150" height="44" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"/><text x="83" y="52" font-size="10.5" text-anchor="middle" fill="currentColor">what you CARE about</text><text x="83" y="66" font-size="10" text-anchor="middle" fill="currentColor" font-weight="600">health need</text><path d="M158 54 L206 54" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3"/><path d="M200 50 l6 4 -6 4" fill="currentColor"/><rect x="207" y="32" width="150" height="44" rx="3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-dasharray="4 3"/><text x="282" y="52" font-size="10.5" text-anchor="middle" fill="currentColor">what you MEASURE</text><text x="282" y="66" font-size="10" text-anchor="middle" fill="currentColor" font-weight="600">healthcare cost</text><path d="M357 54 L405 54" stroke="currentColor" stroke-width="1.2"/><path d="M399 50 l6 4 -6 4" fill="currentColor"/><rect x="406" y="32" width="150" height="44" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="481" y="52" font-size="10.5" text-anchor="middle" fill="currentColor">model predicts it</text><text x="481" y="66" font-size="10" text-anchor="middle" fill="currentColor">accurately</text><path d="M556 54 L604 54" stroke="currentColor" stroke-width="1.2"/><path d="M598 50 l6 4 -6 4" fill="currentColor"/><rect x="605" y="32" width="107" height="44" rx="3" fill="currentColor" opacity="0.14"/><rect x="605" y="32" width="107" height="44" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"/><text x="658" y="52" font-size="10" text-anchor="middle" fill="currentColor">allocates</text><text x="658" y="66" font-size="10" text-anchor="middle" fill="currentColor">the programme</text><path d="M282 82 L282 106" stroke="currentColor" stroke-width="1.2"/><path d="M278 100 l4 6 4 -6" fill="currentColor"/><rect x="150" y="108" width="264" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.4"/><text x="282" y="124" font-size="10" text-anchor="middle" fill="currentColor" font-weight="600">THE WEDGE: unequal access</text><text x="282" y="139" font-size="9.5" text-anchor="middle" fill="currentColor">at equal illness, less is spent on Black patients</text><text x="8" y="178" font-size="10" font-weight="600" fill="currentColor">The result, at the same risk score</text><text x="8" y="196" font-size="9.5" fill="currentColor" opacity="0.9">Black patients had ~26% more active chronic conditions — equally scored, measurably sicker.</text><text x="8" y="212" font-size="9.5" fill="currentColor" opacity="0.9">Auto-enrolment: 17.7% Black → 46.5% once the target is corrected. A 2.6× change from the LABEL, not the model.</text><text x="8" y="234" font-size="9.5" fill="currentColor" opacity="0.9">The model was never broken. It answered the question it was given, and the question encoded the inequity.</text></svg>

## 8 · What each is actually worth

**Epic Sepsis: the idea is sound, the execution was not, and the distinction matters.**

Early-warning scores for deterioration *do* work — NEWS and MEWS are unglamorous, transparent,
and useful. So the lesson is not "don't predict sepsis". It is that at 8 alerts per true case
and two-thirds of sepsis missed, the tool has **negative** value: it consumes attention,
trains staff to ignore alerts, and the missed cases are invisible in the alert log. ✱ Alert
fatigue is not a soft cost. Once clinicians disregard alerts, system sensitivity goes to zero
regardless of what the model reports.

**The condition under which it becomes worth having:** an outcome definition not derived from
clinician behaviour, external validation before deployment, a locally set threshold from local
sepsis incidence, and a measured alert burden. All four are achievable. None was done.

**Obermeyer: the most valuable failure in the field, because it came with its fix.**

The algorithm's potential was real — targeting scarce care management by predicted need is
sensible. Correct the label and it does that. Its worth is that it turned a vague worry about
"algorithmic bias" into a concrete, checkable, fixable mechanism: **look at the target
variable.**

✱ And the mechanism generalises beyond race and beyond the US. Any proxy target inherits the
inequities of the process that generated it. Cost proxies need. Diagnosis proxies disease —
but only where people can reach a diagnosis. Reported cases proxy incidence — but only where
surveillance reaches. **That last one is your daily working life.**

## 9 · Transferable lessons

1. **Two distinct failure modes.** *Never checked* (Epic) is a governance problem, fixed by
   requiring external validation. *Checked, wrong question* (Obermeyer) is a construct problem,
   fixed by interrogating the target. A rule that catches one will not catch the other.
2. **Ask what the label actually is** — not what it is called. "Sepsis" meant clinician action.
   "Need" meant cost.
3. **If the label is derived from the behaviour you want to improve, the model can only learn
   to imitate it.** It cannot beat clinicians at recognising sepsis if the definition of sepsis
   is that clinicians recognised it.
4. **Audit by comparing the score against a construct the model was not trained on.** You do
   not need the weights.
5. **Report alert burden, always** — alerts per true case, and share of all patients alerted.
   AUC hides both.
6. **Proprietary is not a defence, it is a risk factor.** An uninspectable model in hundreds of
   hospitals is a systemic exposure.
7. **A proxy inherits the inequities of the process that produced it.** Including your own
   reported case counts.

## 10 · Explain it in 60 seconds

> Two famous health-AI failures, and they broke in opposite ways.
>
> The first, Epic's sepsis alert, was running in hundreds of American hospitals on the vendor's
> own accuracy claims. When outsiders finally tested it properly, it caught about a third of
> sepsis cases while alerting on nearly a fifth of *everyone admitted* — roughly eight false
> alarms per real case. And the deeper problem: because there's no lab test for sepsis, they
> had to define it by what doctors did — the antibiotics they ordered. So the model was trained
> to predict *doctors noticing sepsis*, which is exactly what you don't need a model for.
>
> The second was an algorithm choosing who gets extra nursing care. It worked beautifully — at
> predicting what it was asked to predict, which was **healthcare cost**, used as a stand-in
> for how sick someone was. But at equal illness, less money is spent on Black patients,
> because of unequal access. So the model systematically under-referred them: patients with the
> same score had about a quarter more chronic conditions if they were Black. Fix the target
> instead of the model and Black enrolment goes from 18% to 47%.
>
> So: one was never checked, the other was checked and answered the wrong question. And the
> second lesson generalises everywhere — any proxy inherits the unfairness of whatever produced
> it. Reported case counts proxy disease, but only where surveillance reaches.

## 11 · Read more

**The two papers — read both, they are short**
- **Wong A, Otles E, Donnelly JP, et al.** *External validation of a widely implemented
  proprietary sepsis prediction model in hospitalized patients.* **JAMA Internal Medicine**
  2021;181(8):1065–1070. doi:10.1001/jamainternmed.2021.2626 ✓ Verified.
- **Obermeyer Z, Powers B, Vogeli C, Mullainathan S.** *Dissecting racial bias in an algorithm
  used to manage the health of populations.* **Science** 2019;366(6464):447–453.
  doi:10.1126/science.aax2342 ✓ Verified. **If you read one
  paper on health-AI fairness, this is it** — the mechanism is stated plainly and the fix is in
  the paper.

**Context and follow-ups**
- Habib AR, Lin AL, Grant RW, on the ESM affair and what it implies for governance of
  proprietary clinical AI. **JAMA** viewpoints, 2021.
- Ghassemi M, and colleagues — critiques of EHR-based deterioration prediction and of
  explainability as a substitute for validation.
- Chen IY, Pierson E, Rose S, Joshi S, Ferryman K, Ghassemi M. *Ethical machine learning in
  health care.* **Annual Review of Biomedical Data Science** 2021. Good survey; picks up the
  label-choice problem directly.
- Obermeyer Z, Mullainathan S, and colleagues — the **Algorithmic Bias Playbook** (Chicago
  Booth, free). Practical, checklist-shaped, built from this case.

**On labels and construct validity — the deeper reading**
- Jacobs AZ, Wallach H. *Measurement and fairness.* **FAccT** 2021. The formal account of what
  goes wrong when you substitute a measurable proxy for the construct you care about.
- Passi S, Barocas S. *Problem formulation and fairness.* **FAccT** 2019.

**On alert burden and clinical deployment**
- Any of the clinical-decision-support alert-fatigue literature; the concept matters more than
  the specific citation.
- **DECIDE-AI** — the reporting guideline for early live clinical evaluation, i.e. exactly the
  rung ESM skipped.

**Books**
- O'Neil C. *Weapons of Math Destruction* (2016). Obermeyer is the rigorous version of this
  book's argument.
- Kearns M, Roth A. *The Ethical Algorithm* (2019). For what "fix the label" means technically.
