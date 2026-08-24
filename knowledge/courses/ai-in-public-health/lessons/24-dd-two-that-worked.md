# Deep dive — Two that worked: forecast hubs and wastewater surveillance

**Shape 2** (predict what happens next) and **Shape 1** (detect the unusual) ·
Maturities **🚀 both at scale** · Stresses **evaluation** — favourably, for once

> ⚠ Written from model knowledge to mid-2026. Figures are leads to verify. The mechanisms are the
> durable content.

Every other deep dive in this course is a failure. That is not editorial pessimism — the failures
are simply where the mechanisms are clearest. But it leaves a false impression, so this one is
about two things that worked, and about *why* they worked, which turns out to have almost nothing
to do with method.

- **Forecast hubs** solved a problem nobody could solve individually, by changing the
  institution rather than the model.
- **Wastewater surveillance** achieved what a decade of digital early-warning promises did not:
  a signal that is genuinely, reliably earlier — by changing the sample rather than the algorithm.

---

## 1 · The questions someone actually asked

**Forecast hubs.** By the mid-2010s, influenza forecasting had many teams, many methods, and no
way to compare them. Everyone reported favourable results on their own data with their own metric.
So the question was not *"what is the best model?"* but the harder, more embarrassing one:
**"how would we ever know?"**

**Wastewater.** Clinical surveillance sees people who present. That excludes the asymptomatic, the
mildly ill, and anyone who cannot or will not attend — and it arrives only after a delay. The
question: *is there a sample that includes everybody and arrives sooner?*

✱ Note that neither is a modelling question. One is about evaluation infrastructure; the other is
about sampling. Both are the kind of question that gets asked when a field stops trying to win and
starts trying to know.

## 2 · Why each looked tractable

**Hubs** needed nothing new: a common target, a common format, a fixed submission deadline, and a
proper scoring rule. All of it existed. What was missing was the *agreement*.

**Wastewater** rested on a fact known for decades from polio: infected people shed virus in
faeces, so sewage integrates a whole catchment's infection status into one sample. Two things made
it newly practical — cheap quantitative PCR, and a pandemic urgent enough to fund the plumbing.

## 3 · The data, and what it does not represent

**Hubs.** Forecasts submitted as **quantiles**, weekly, before the truth is known — the crucial
design point — against a pre-specified target (cases, hospitalisations, deaths) with a
pre-specified truth source.

⚠ What it does not represent: teams that dropped out. A hub only scores what is submitted, and
teams tend to stop submitting when they do badly. Any hub evaluation therefore has a survivorship
problem, and the good hubs handle it by reporting who submitted when.

**Wastewater.** Viral RNA concentration in influent, by sampling site and date.

What it does *not* represent, and this is where the methods argument lives:

- **The catchment is not a population.** Sewer networks do not match administrative boundaries,
  and connection rates vary enormously. ⚠ In much of the world, including the settings you work
  in, most people are not connected to a sewer at all — which bounds where this method can go.
- **Dilution changes constantly.** Rain, industrial discharge, groundwater infiltration. So raw
  concentration is not comparable across days, which is why normalisation matters (flow rate, or
  a faecal marker such as PMMoV).
- **Shedding is not infection.** It varies by person, by day of illness, by variant, and by
  immune status. So the relationship between concentration and case count is not fixed — it
  drifts.
- **No individual data at all.** Which is simultaneously its greatest strength (nobody can be
  identified, no consent problem, no care-seeking bias) and its hard ceiling (you cannot follow up
  a signal to a person).

## 4 · The methods, explained

**The hub method is administrative, and that is the point.**

1. Fix the target, the truth source, the horizons and the submission format.
2. Everyone submits quantiles by a deadline, **before** the outcome is observed.
3. Score everything with the same proper rule — **WIS**, from Lesson 3.
4. Publish all scores, all teams, all weeks.
5. Build an **ensemble** — often just the median across submissions.

That is the entire innovation. There is no algorithm in it.

**Wastewater method:**

1. Composite sample from the influent stream — usually 24-hour, to average diurnal variation.
2. Concentrate and extract nucleic acid.
3. Quantify by RT-qPCR or digital PCR; increasingly sequence for variant composition.
4. **Normalise** for dilution.
5. Smooth, and apply aberration detection — Lesson 2's machinery, unchanged.

✱ Step 4 is where the science is, and step 5 is where the shape-1 discipline from Lesson 2
applies exactly: the detector is easy, the baseline is hard, and here the baseline has to absorb
rainfall.

## 5 · What each found

**Hubs.** The finding is the one from Lesson 3, and it deserves restating because it was so
unexpected: **a simple median ensemble outperformed almost every individual model, almost always,
and was dramatically more consistent.** Individual teams had excellent months; the ensemble almost
never had a bad one.

A second finding, less celebrated and more useful: **most models are worse than they claimed, and
many are worse than a seasonal-naive baseline at longer horizons.** That could only be discovered
by scoring everyone the same way, prospectively, in public.

**Wastewater.** Consistent lead times over clinical indicators — typically **days to a couple of
weeks**, varying by site and indicator, with hospitalisations lagging further than cases. It
detected variant emergence, tracked trends when clinical testing collapsed after free testing
ended, and is now routine in many national systems. Polio environmental surveillance had shown the
principle for decades; SARS-CoV-2 scaled it.

## 6 · How each was evaluated

| Question | Forecast hubs | Wastewater |
|---|---|---|
| **Shape** | 2 | 1, feeding 2 |
| **Comparator** | Every other submitted model **and** a naive baseline | Clinical case and admission series |
| **Evaluation** | **Prospective, pre-registered, public, proper scoring rule** | Lead time against clinical indicators, at matched alarm rates |
| **Debt paid?** | **Yes — this is what paying it looks like** | Yes, and honestly: lead times are reported as ranges, not best cases |
| **Weakness** | Survivorship among submitting teams | Catchment ≠ population; shedding-to-cases relationship drifts |

✱ The hub column is the best answer in this entire course to "what would convincing evidence look
like?" Nothing else here has been evaluated that well, and the reason is that the evaluation was
designed **before** the results existed.

## 7 · What happened next

**Hubs** spread — from influenza to COVID-19 to RSV, from the US to Europe, and into other
outbreak-prone diseases. They became infrastructure, and the hub *is* the deliverable, not any
model in it. ⚠ With a fragility worth naming: hubs depend on sustained coordination funding, and
the incentive to submit weakens once the emergency ends.

**Wastewater** became a permanent surveillance stream in many high-income countries and expanded
beyond SARS-CoV-2 to influenza, RSV, mpox, polio and antimicrobial-resistance genes. ✱ The
interesting frontier is not the pathogen list but the **settings question**: how to do this where
sewerage is partial or absent — pit-latrine and open-drain sampling, and sampling at
institutional level rather than city level.

## 8 · What each is actually worth

**Forecast hubs: the most transferable idea in this course.**

The value is not the forecasts. It is that the hub **made a field honest**, and it did so by
changing the rules rather than persuading anyone. Once scores are public and pre-registered,
nobody has to be convinced to stop over-claiming; over-claiming simply stops working.

In the units of the decision: a reliable multi-week-ahead probabilistic forecast with honest
intervals, which supports staffing and capacity planning. Modest, real, and — ✱ crucially —
**bounded honesty about horizons**. The hubs established where forecasting stops being useful,
which is itself a public good. Very little else in health AI can tell you where it stops working.

⚠ **And it generalises directly to your world.** Any question where many groups produce competing
estimates — HAT elimination timelines, risk maps, burden estimates — could be run as a hub. There
is no methodological barrier. The barrier is that somebody has to convene it and everybody has to
agree to be scored.

**Wastewater: genuinely earlier, genuinely limited, and honest about both.**

Its worth is **days to weeks of lead time on a population signal that includes people clinical
surveillance never sees**, with no consent problem and no care-seeking bias. That is a real and
rare combination.

Its limits are structural rather than fixable: no individual follow-up, catchment boundaries that
are not epidemiological units, a drifting relationship between concentration and cases, and — the
one that matters for your settings — **a requirement for sewerage that much of the world does not
have.**

**The condition under which its value collapses:** if nothing is done differently in the lead
time. Lesson 2's rule holds. Wastewater's advantage over the digital early-warning systems in the
Atlas is not that it is earlier — several of those were earlier too. It is that it is **earlier and
trustworthy enough to act on**, because it measures a physical quantity rather than a proxy for
attention.

## 9 · Transferable lessons

1. **Design the evaluation before the results exist.** Everything the hubs achieved follows from
   this one decision.
2. **Score everyone the same way, publicly.** It removes the need to win an argument about
   over-claiming.
3. **Combine rather than select.** The ensemble beats picking a winner — and it needs diversity,
   not more members.
4. **Sometimes the answer is a better sample, not a better model.** Wastewater beat a decade of
   algorithmic early-warning effort by changing what was measured.
5. **Prefer measuring a physical quantity over a proxy for attention.** Viral RNA does not change
   its meaning because a search engine updated its autocomplete.
6. **Report the limits as specifically as the findings.** Both cases do; it is why they are
   trusted.
7. **A field can be fixed by institutions rather than methods** — and that option is usually
   available and usually ignored.

## 10 · Explain it in 60 seconds

> Two cases where public health AI actually worked, and neither is really about the AI.
>
> The first: flu forecasting was full of teams all claiming their model was best on their own
> data. So instead of arguing, they built a **hub** — everyone submits a forecast in the same
> format, by a deadline, before the answer is known, and everyone gets scored the same way in
> public. Two things fell out. Most models were worse than they'd claimed, some worse than just
> guessing "same as last year". And the **average of everybody's forecasts** beat almost every
> individual model, almost always. They fixed the field by changing the rules, not the maths.
>
> The second: everyone spent a decade trying to detect outbreaks earlier from search data and
> social media, and it mostly didn't work. Then it turned out you could just **test the sewage.**
> Infected people shed virus in their faeces, so one sample from a treatment plant covers a whole
> city — including everyone who never sees a doctor. It's reliably days to weeks ahead of hospital
> admissions.
>
> The lesson from both: the win didn't come from a cleverer algorithm. One came from a better
> **institution**, the other from a better **sample**. That's usually where the win is.

## 11 · Read more

**Forecast hubs**
- **Reich NG, Brooks LC, Fox SJ, et al.** **Reich NG, Brooks LC, Fox SJ, Kandula S, McGowan CJ, Moore E, et al.** *A collaborative
  multiyear, multimodel assessment of seasonal influenza forecasting in the United States.*
  **PNAS** 2019;116(8):3146–3154; doi:10.1073/pnas.1812594116. ✓ **Verified 2026-08-21. Start
  here** — the paper that established the ensemble finding.
- **Cramer EY, Ray EL, Lopez VK, et al.** *Evaluation of individual and ensemble probabilistic
  forecasts of COVID-19 mortality in the United States.* **PNAS** 2022.
- **Sherratt K, Gruson H, Grah R, et al.** On the **European COVID-19 Forecast Hub** — the
  replication, and unusually frank about what did not work.
- **Bracher J, Ray EL, Gneiting T, Reich NG.** *Evaluating epidemic forecasts in an interval
  format.* **PLOS Comp Biol** 2021 — the scoring rule the hubs use.
- The **CDC FluSight** and **COVID-19 Forecast Hub** repositories. All submissions and all scores
  are public; browsing them teaches more than any paper.

**Wastewater surveillance**
- **Peccia J, Zulli A, Brackney DE, et al.** *Measurement of SARS-CoV-2 RNA in wastewater tracks
  community infection dynamics.* **Nature Biotechnology** 2020. One of the early lead-time papers.
- **Medema G, Heijnen L, Elsinga G, Italiaander R, Brouwer A.** *Presence of SARS-Coronavirus-2
  RNA in sewage.* **Environmental Science & Technology Letters** 2020.
- **Wolfe MK, Boehm AB**, and colleagues on normalisation and on multi-pathogen panels.
- **WHO** guidance on **environmental surveillance for poliovirus** — the decades-older precedent,
  and the best source on doing this where sewerage is partial.
- Reviews on wastewater surveillance in **low- and middle-income settings** — the open problem,
  and the one that matters for your work. ⚠ I do not have a specific citation I trust here;
  worth a librarian pass.

**Books**
- **Hyndman RJ, Athanasopoulos G.** *Forecasting: Principles and Practice* (free online) — for
  the combination and scoring material, done properly.
