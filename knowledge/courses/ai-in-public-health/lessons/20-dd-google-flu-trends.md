# Deep dive — Google Flu Trends

**Shape 1** (detect the unusual) straddling **shape 2** (predict what happens next) · Maturity **⚰️ withdrawn** · Stresses the **evaluation** layer

> ⚠ Written from model knowledge to mid-2026. Specific figures are leads to verify, not citations to reuse. The mechanism is the durable content.

---

## 1 · The question someone actually asked

In 2008, US influenza surveillance worked like this: sentinel clinicians reported the proportion of visits for influenza-like illness (ILI) to CDC, which aggregated, cleaned and published it — with a **lag of one to two weeks**.

That lag is not a bureaucratic failing; it is the time it takes for a person to fall ill, decide to attend, be seen, be recorded, and for the record to travel. But it means that in a fast-moving season, public health is always steering by a rear-view mirror.

The question: **can we estimate current ILI activity faster than the surveillance system can report it?**

Note what this question is and is not. It is *nowcasting* — estimating the present. It is not forecasting the future, and it is not detecting a novel pathogen. That distinction is the whole story.

## 2 · Why it looked tractable

People with flu search the web. They search before they attend a clinic, and certainly before a sentinel report is aggregated. Google held the search logs. If search volume for the right terms tracked ILI, you would have a real-time proxy for free.

✱ This is the classic shape of a data-availability opportunity rather than a methods advance. Nothing in the statistics was new. What was new was that somebody had the data.

## 3 · The data

- **Predictors:** aggregated, anonymised counts of Google search queries by week and US region, drawn from a candidate pool on the order of **50 million** distinct queries.
- **Outcome:** CDC's published ILI proportion, by region, for roughly 2003–2008.
- **Unit:** region-weeks. About 128 weeks of training data across 9 US regions.

**What it represents:** the searching behaviour of American internet users in the mid-2000s.

**What it does not represent** — and this is where the failure is already visible:

- It is not *illness*. It is *searching about illness*, which mixes the sick, the worried, the caregivers and the merely curious in unknown and changing proportions.
- The denominator is unstable. Who uses Google, and how they phrase things, changes continuously.
- The predictors are **not under the researchers' control**. Google changes its own product. That has no analogue in classical surveillance, where the case definition is yours.

## 4 · The method, explained

Deliberately simple, which is important — nobody can blame a neural network here.

1. **Candidate generation.** For each of ~50 million queries, compute the correlation between its weekly regional volume and the CDC ILI series.
2. **Selection.** Add queries greedily, keeping those that improve fit, arriving at a set of roughly **45 queries**.
3. **Model.** A linear model on the logit scale: log-odds of ILI regressed on the log-odds of the aggregated volume of the selected query set.
4. **Deployment.** Feed live search volume into the fitted model each week, publish the estimate immediately.

The reported in-sample fit was extraordinary — correlation around **0.97** with CDC ILI.

⚠ Pause on step 2. Queries were selected **because they correlated**, from a pool of 50 million, with no requirement that they be causally or even plausibly related to influenza. With 50 million candidates and ~128 observations, a great many things will correlate at 0.9+ by chance alone. The reported example of the pathology: terms related to **high-school basketball**, whose season coincides with flu season.

<svg viewBox="0 0 640 110" width="100%" style="max-width:640px" role="img" aria-label="Pipeline: 50 million candidate queries narrowed to 45, fitted to CDC ILI, published live"><rect x="1" y="30" width="120" height="44" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="61" y="49" font-size="11" text-anchor="middle" fill="currentColor">50,000,000</text><text x="61" y="63" font-size="9" text-anchor="middle" fill="currentColor" opacity="0.7">candidate queries</text><path d="M121 52 L156 52" stroke="currentColor" stroke-width="1.2"/><path d="M150 48 l6 4 -6 4" fill="currentColor"/><rect x="157" y="30" width="112" height="44" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="213" y="49" font-size="11" text-anchor="middle" fill="currentColor">45 queries</text><text x="213" y="63" font-size="9" text-anchor="middle" fill="currentColor" opacity="0.7">kept if correlated</text><path d="M269 52 L304 52" stroke="currentColor" stroke-width="1.2"/><path d="M298 48 l6 4 -6 4" fill="currentColor"/><rect x="305" y="30" width="120" height="44" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="365" y="49" font-size="11" text-anchor="middle" fill="currentColor">linear model</text><text x="365" y="63" font-size="9" text-anchor="middle" fill="currentColor" opacity="0.7">128 region-weeks</text><path d="M425 52 L460 52" stroke="currentColor" stroke-width="1.2"/><path d="M454 48 l6 4 -6 4" fill="currentColor"/><rect x="461" y="30" width="120" height="44" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="521" y="49" font-size="11" text-anchor="middle" fill="currentColor">live estimate</text><text x="521" y="63" font-size="9" text-anchor="middle" fill="currentColor" opacity="0.7">r = 0.97 in-sample</text><text x="213" y="97" font-size="9.5" text-anchor="middle" fill="currentColor" opacity="0.75">50M candidates / 128 observations</text><text x="213" y="20" font-size="9.5" text-anchor="middle" fill="currentColor" opacity="0.75">the step that decided everything</text><path d="M213 24 L213 30" stroke="currentColor" stroke-width="1" opacity="0.6"/><path d="M213 74 L213 88" stroke="currentColor" stroke-width="1" opacity="0.6"/></svg>

## 5 · What they found

Published in *Nature* in 2009 (Ginsberg et al.): search data could estimate current ILI with high accuracy, one to two weeks ahead of CDC reporting. It was celebrated as a demonstration that large-scale behavioural data could outrun conventional surveillance — and it became the standard example of "big data for public health".

## 6 · How it was evaluated

The four questions:

| Question | Answer |
|---|---|
| **Which shape?** | Ambiguous — evaluated as shape 2 (does it track ILI?), sold as shape 1 (does it warn earlier?) |
| **What comparator?** | CDC ILI was the *target*, not a comparator. **A seasonal-naive baseline was never reported** |
| **How evaluated?** | In-sample fit and short-run holdout. No prospective evaluation against a changing platform |
| **Maturity claimed** | Deployed at scale, publicly, immediately |

✱ The missing comparator is the sharpest omission. Influenza is strongly seasonal, so a model that knows only the week of the year predicts ILI well. **How much of that 0.97 was influenza signal and how much was calendar?** The question was not asked, and the answer matters entirely: a calendar-driven model cannot detect anything unusual, which is precisely what an early-warning system must do.

## 7 · What happened next

Two failures, in opposite directions, which together are more instructive than either.

**2009 — it missed the real event.** The H1N1 pandemic arrived out of season, in spring. GFT substantially *underestimated* it. The model had learned the relationship between search behaviour and ILI *during normal winter seasons*; a novel pathogen in April changed both the epidemiology and the searching, and the fitted relationship no longer held. ⚠ **The one event the system existed to catch was the one it was structurally unable to catch.**

**2012–13 — it wildly overestimated.** GFT reported ILI at roughly **double** the true peak. Reported causes:

- **Overfitting to seasonal confounders.** Predictors selected for correlation, not causation, drift apart from the outcome when a season behaves unusually.
- **Algorithm dynamics.** Google changed its own product — autocomplete, related searches, the news panel. Heavy media coverage of a severe flu season prompted more searching by well people. The predictor was **contaminated by the model's own context.** No classical surveillance system has this failure mode.
- **No recalibration path.** The model was fitted once. There was no mechanism to notice that its inputs had changed meaning.

<svg viewBox="0 0 640 200" width="100%" style="max-width:640px" role="img" aria-label="Schematic: GFT tracks CDC ILI in normal seasons, underestimates the 2009 out-of-season H1N1 wave, then roughly doubles the 2012-13 peak"><line x1="46" y1="160" x2="616" y2="160" stroke="currentColor" stroke-width="1"/><line x1="46" y1="20" x2="46" y2="160" stroke="currentColor" stroke-width="1"/><text x="20" y="26" font-size="9" fill="currentColor" opacity="0.7">ILI</text><text x="24" y="164" font-size="9" fill="currentColor" opacity="0.7">0</text><path d="M46 150 L96 120 L146 152 L196 118 L246 150 L296 100 L346 152 L396 116 L446 150 L496 60 L546 148 L596 128" fill="none" stroke="currentColor" stroke-width="2"/><path d="M46 152 L96 122 L146 154 L196 120 L246 152 L296 138 L346 154 L396 118 L446 152 L496 24 L546 150 L596 130" fill="none" stroke="currentColor" stroke-width="1.6" stroke-dasharray="5 3" opacity="0.85"/><circle cx="296" cy="100" r="3.5" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="296" cy="138" r="3.5" fill="currentColor" opacity="0.5"/><text x="296" y="182" font-size="9.5" text-anchor="middle" fill="currentColor">2009 H1N1</text><text x="296" y="193" font-size="8.5" text-anchor="middle" fill="currentColor" opacity="0.7">out of season: UNDER-estimated</text><circle cx="496" cy="24" r="3.5" fill="currentColor" opacity="0.5"/><circle cx="496" cy="60" r="3.5" fill="none" stroke="currentColor" stroke-width="1.4"/><text x="510" y="20" font-size="9.5" fill="currentColor">2012-13</text><text x="510" y="31" font-size="8.5" fill="currentColor" opacity="0.7">~2x the true peak</text><text x="470" y="176" font-size="9" fill="currentColor" opacity="0.85">— CDC ILI (truth)</text><text x="470" y="190" font-size="9" fill="currentColor" opacity="0.85">- - GFT estimate</text><text x="330" y="12" font-size="8.5" text-anchor="middle" fill="currentColor" opacity="0.6">schematic — shows the two failure directions, not exact values</text></svg>

Google stopped publishing estimates in 2015, moving to providing data to research groups instead. Lazer et al.'s 2014 *Science* paper, **"The Parable of Google Flu"**, named the underlying error **big data hubris**: treating volume as a substitute for, rather than a supplement to, measurement and theory.

## 8 · What it is actually worth

This is the section the course exists for, and the honest answer is **not zero** — which is what most retellings imply.

**What the approach can genuinely do:**

- **Fill gaps where no surveillance exists.** In settings with no sentinel network, a noisy real-time proxy beats nothing. The comparator is not CDC ILI; it is silence.
- **Add days of lead time as one input among several.** Combined with clinical data, corrected continuously against it, digital signals contribute. This is what the field actually became: search and social data as *components* of ensemble nowcasts, never as standalone systems.
- **Track behaviour and attention**, which is a legitimate object in its own right — vaccine hesitancy, health-information seeking, infodemic dynamics.

**What it cannot do, ever, in this design:**

- **Detect a novel event.** A model fitted on historical relationships is definitionally blind to a change in those relationships. 2009 was not bad luck; it was the design.
- **Stand alone.** Without a ground-truth series to recalibrate against, drift is undetectable. ✱ And the deep irony: **the system needed the surveillance it was meant to replace.**

**The condition under which the answer flips:** continuous recalibration against a ground-truth series, causally plausible predictors rather than correlation-mined ones, and honest uncertainty. Modern digital-epidemiology work that does these things performs respectably. The 2009 design did none of them.

**Quantified in the units of the decision:** roughly **1–2 weeks** of lead time on a regional ILI estimate — real, and worth having if and only if something is done differently in those two weeks, and if the estimate is trustworthy enough to act on. GFT failed the second condition precisely when the first mattered most.

## 9 · Transferable lessons

1. **Selecting predictors by correlation from a huge pool is not feature selection, it is fishing.** Demand causal plausibility, or expect drift.
2. **Always report the boring baseline.** For a seasonal outcome, that is a seasonal-naive model. Unreported means it probably won.
3. **If you do not control your predictors, you do not control your model.** A vendor's product changes; your case definition does not.
4. **In-sample r = 0.97 is a warning sign**, not a result.
5. **A nowcast and an early-warning system are different products** with different evidence requirements. Do not let one be marketed as the other.
6. **Nothing replaces the ground truth**, because you need it to know your proxy still works.

## 10 · Explain it in 60 seconds

> Google noticed that people search about flu before they see a doctor, so in 2009 they built a model that estimated current flu levels from search volume — about two weeks faster than the official surveillance system. It fitted beautifully, and it became the poster child for big data in public health.
>
> Then it failed twice, in opposite directions. It **underestimated** the 2009 swine flu pandemic, because it was out of season and the model had only ever learned normal winters — so the one event it existed to catch was the one it couldn't. And in 2012–13 it **overestimated** the peak by about double, partly because its predictors had been picked for correlation rather than for making sense, and partly because Google kept changing what people saw when they searched, so the inputs quietly changed meaning underneath a model nobody was recalibrating.
>
> The lesson isn't "big data doesn't work". It's that a proxy needs the real measurement to stay honest — so it can supplement surveillance, but it can never replace it.

## 11 · Read more

**Start here (the two papers that bracket the story)**

- Ginsberg J, Mohebbi MH, Patel RS, Brammer L, Smolinski MS, Brilliant L. *Detecting influenza epidemics using search engine query data.* **Nature** 2009;457:1012–1014. The original. Short, readable, and the method is fully described.
- Lazer D, Kennedy R, King G, Vespignani A. *The parable of Google Flu: traps in big data analysis.* **Science** 2014;343(6176):1203–1205. doi:10.1126/science.1248506 ✓ Verified. The definitive critique. Two pages. If you read one thing in this course, read this.

**The failures in detail**

- Cook S, Conrad C, Fowlkes AL, Mohebbi MH. *Assessing Google Flu Trends performance in the United States during the 2009 influenza virus A (H1N1) pandemic.* **PLoS ONE** 2011. The under-estimation, quantified.
- Butler D. *When Google got flu wrong.* **Nature** news feature, 2013. The 2012–13 over-estimation as it was being noticed.
- Olson DR, Konty KJ, Paladini M, Viboud C, Simonsen L. *Reassessing Google Flu Trends data for detection of seasonal and pandemic influenza.* **PLoS Computational Biology** 2013.

**Where the field went next**

- Santillana M et al., on combining search data *with* clinical surveillance rather than instead of it — the ensemble approach that actually works.
- Yang S, Santillana M, Kou SC. *Accurate estimation of influenza epidemics using Google search data via ARGO.* **PNAS** 2015. The credible successor: recalibrated continuously against ground truth.

**Books**

- Salganik MJ. *Bit by Bit: Social Research in the Digital Age* (2018; free online). Chapter 2 on observing behaviour is the best available treatment of why found data behaves differently from designed data. Directly generalises this case.
- Meng XL's writing on data quality vs data quantity — the "big data paradox": a small random sample can beat a huge biased one, and the bigger the biased sample the more confidently wrong it is.

⚠ Author lists and volume numbers above are from memory. Verify before citing; the Ginsberg and Lazer references are the two I am most confident about.
