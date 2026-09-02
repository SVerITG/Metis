# Source ledger — AI in Public Health & Epidemics

**Read this before citing anything from this course.**

This course originally shipped with a single blanket warning — "every citation is an
unverified lead". That is honest and close to useless: it gives a reader no way to tell the
handful of sources that were actually checked from the many that were not, so it prices
everything at the level of the weakest item. This ledger grades them instead, in the same
shape as the genomic-surveillance course.

| Grade | Meaning |
|---|---|
| **CROSSREF-VERIFIED** | The DOI was resolved against Crossref and its first author and year match what the lesson claims. The citation points at the paper it says it does. |
| **MARKED-VERIFIED** | Carried an inline `✓ Verified` marker from the authoring session. The claim was checked then; no DOI is present to re-check mechanically. |
| **SEARCH** | A named reference with no DOI and no verification marker. Almost certainly a real paper; the specific volume, page or finding attributed to it was not confirmed. **Verify before citing in a manuscript.** |
| **FLAGGED** | The author flagged uncertainty inline. Treat as a lead to chase, not a citation. |

Last checked: **2026-08-28** with `tools/check_course_dois.py`.

---

## CROSSREF-VERIFIED — 10 DOIs, all resolving and correctly attributed

Checked mechanically, with a control pair proving the check could tell pass from fail.
**0 unresolvable, 0 misattributed.**

- `10.1001/jama.2019.5791` — Seymour 2019 — Derivation, Validation, and Potential Treatment Implications of Novel Clinical Phenotypes for Sepsis (JAMA)
- `10.1001/jamainternmed.2021.2626` — Wong 2021 — External Validation of a Widely Implemented Proprietary Sepsis Prediction Model (JAMA Intern Med)
- `10.1038/s41586-025-08866-7` — Tu 2025 — Towards conversational diagnostic artificial intelligence (Nature)
- `10.1038/s42256-021-00307-0` — Roberts 2021 — Common pitfalls and recommendations for using machine learning ... COVID-19 (Nature Machine Intelligence)
- `10.1056/EVIDoa2100058` — Pokaprakarn 2022 — AI Estimation of Gestational Age from Blind Ultrasound Sweeps (NEJM Evidence)
- `10.1073/pnas.1812594116` — Reich 2019 — A collaborative multiyear, multimodel assessment of seasonal influenza forecasting (PNAS)
- `10.1126/science.1248506` — Lazer 2014 — The Parable of Google Flu: Traps in Big Data Analysis (Science)
- `10.1126/science.aax2342` — Obermeyer 2019 — Dissecting racial bias in an algorithm used to manage the health of populations (Science)
- `10.1145/3313831.3376718` — Beede 2020 — A Human-Centered Evaluation of a Deep Learning System Deployed in Clinics (CHI '20)
- `10.1371/journal.pcbi.1008618` — Bracher 2021 — Evaluating epidemic forecasts in an interval format (PLOS Comp Biol)

> An earlier run of this check reported all ten as unresolvable. That was the checker
> failing silently on content negotiation, not ten fabricated citations. `check_course_dois.py`
> now runs a known-good and a known-bad DOI first and refuses to judge anything unless those
> two come back different.


## MARKED-VERIFIED — 16 sources checked during authoring

- *[02-detect-the-unusual.md]* Salmon, Schumacher & Höhle, *Monitoring count time series in R: aberration detection in public health surveillance.* **Journal of Statistical Software** 2016;70(10):1–35.**
- *[03-predict-what-happens-next.md]* **Bracher J, Ray EL, Gneiting T, Reich NG.** *Evaluating epidemic forecasts in an interval format.* **PLOS Computational Biology** 2021;17(2):e1008618; doi:10.1371/journal.pcbi.1008618. Where WIS is defined for exactly this use.
- *[05-labels-from-pixels.md]* Daneshjou R et al. *Disparities in dermatology AI performance on a diverse, curated clinical image set.* **Science Advances** 2022;8:eabq6147.
- *[05-labels-from-pixels.md]* **Pokaprakarn T, et al.** *AI estimation of gestational age from blind ultrasound sweeps in low-resource settings.* **NEJM Evidence** 2022; doi:10.1056/EVIDoa2100058. A 2024 JAMA diagnostic-accuracy study follows it.
- *[06-finding-structure.md]* **Seymour CW, Kennedy JN, Wang S, et al.** *Derivation, validation, and potential treatment implications of novel clinical phenotypes for sepsis.* **JAMA** 2019;321:2003–2017; doi:10.1001/jama.2019.5791.** Then read the replication literature that followed it.
- *[10-deployment-bias-governance.md]* **Beede E, Baylor E, Hersch F, Iurchenko A, Wilcox L, Ruamviboonsuk P, Vardoulakis LM.** *A human-centered evaluation of a deep learning system deployed in clinics for the detection of diabetic retinopathy.* **CHI '20**; doi:10.1145/3313831.3376718. The single best account of deployment reality.
- *[20-dd-google-flu-trends.md]* Lazer D, Kennedy R, King G, Vespignani A. *The parable of Google Flu: traps in big data analysis.* **Science** 2014;343(6176):1203–1205. doi:10.1126/science.1248506 The definitive critique. Two pages. If you read one thing in this course, read this.
- *[21-dd-two-imaging-stories.md]* **Qin ZZ, et al.** *Tuberculosis detection from chest x-rays for triaging in a high tuberculosis-burden setting: an evaluation of five artificial intelligence algorithms.* **Lancet Digital Health** 2021.** See also the prospective triage-accuracy study against culture-confirmed disease (Lancet Digit Health 2021) and the South African prevalence-survey external validation with modelled impacts (Lancet Digit Health 2024;6:e605–13, plus its correction).
- *[21-dd-two-imaging-stories.md]* Winkler JK et al. *Association between surgical skin markings in dermoscopic images and diagnostic performance of a deep learning convolutional neural network for melanoma recognition.* **JAMA Dermatology** 2019;155(10):1135–1141. The confound, demonstrated cleanly: markings raised melanoma probability scores and increased the false-positive rate on benign nevi by roughly **40%**.
- *[21-dd-two-imaging-stories.md]* Freeman K et al. *Algorithm based smartphone apps to assess risk of skin cancer in adults: systematic review of diagnostic accuracy studies.* **BMJ** 2020;368:m127. The consumer-app evidence, and it is not good.
- *[21-dd-two-imaging-stories.md]* Roberts M et al. *Common pitfalls and recommendations for using machine learning to detect and prognosticate for COVID-19 using chest radiographs and CT scans.* **Nature Machine Intelligence** 2021;3(3):199–217; doi:10.1038/s42256-021-00307-0.** Reviewed hundreds of models; found none fit for clinical use. The best single demonstration that imaging AI's problem is method, not architecture.
- *[21-dd-two-imaging-stories.md]* **Beede E, Baylor E, Hersch F, Iurchenko A, Wilcox L, Ruamviboonsuk P, Vardoulakis LM.** *A human-centered evaluation of a deep learning system deployed in clinics for the detection of diabetic retinopathy.* **CHI '20**; doi:10.1145/3313831.3376718. The best account of deployment reality there is.
- *[22-dd-the-consultation.md]* **Tu T, Schaekermann M, Palepu A, et al.** *Towards conversational diagnostic artificial intelligence.* **Nature** 2025;642(8067):442–450. doi:10.1038/s41586-025-08866-7 (arXiv preprint 2401.05654, 2024). **The paper.** Read the methods and the limitations, not the abstract — the limitations are unusually honest and are where the learning is.
- *[23-dd-two-database-failures.md]* **Wong A, Otles E, Donnelly JP, et al.** *External validation of a widely implemented proprietary sepsis prediction model in hospitalized patients.* **JAMA Internal Medicine** 2021;181(8):1065–1070. doi:10.1001/jamainternmed.2021.2626
- *[23-dd-two-database-failures.md]* **Obermeyer Z, Powers B, Vogeli C, Mullainathan S.** *Dissecting racial bias in an algorithm used to manage the health of populations.* **Science** 2019;366(6464):447–453. doi:10.1126/science.aax2342 **If you read one paper on health-AI fairness, this is it** — the mechanism is stated plainly and the fix is in the paper.
- *[24-dd-two-that-worked.md]* **Reich NG, Brooks LC, Fox SJ, Kandula S, McGowan CJ, Moore E, et al.** *A collaborative multiyear, multimodel assessment of seasonal influenza forecasting in the United States.* **PNAS** 2019;116(8):3146–3154; doi:10.1073/pnas.1812594116. Start here** — the paper that established the ensemble finding.

## FLAGGED — 3 the author was explicitly unsure about

- *[07-language-into-data.md]* Tu, Palepu, McDuff, Schaekermann et al., *Towards conversational diagnostic AI* (AMIE) — Nature, 2025. ⚠ Author list and year worth checking.
- *[22-dd-the-consultation.md]* Follow-on AMIE work on **multimodal inputs** and on **management reasoning** (rather than diagnosis alone), 2025. ⚠ I am not confident of the exact titles; worth a librarian pass.
- *[22-dd-the-consultation.md]* **EU AI Act** (Regulation 2024/1689) and **EU MDR** — how a clinical-decision-support claim triggers the high-risk tier. ⚠ Obligations phase in through 2026–27; check current dates.

## SEARCH — 80 named references, not individually confirmed

Real papers in almost every case. What is *not* confirmed is the specific volume, page,
figure or number attributed to each one in the lesson text. Chase the ones you intend to
cite or quote.


**01-the-six-shapes.md**

- Topol, *Deep Medicine* (2019) — the clinical framing; read critically, it is optimistic.
- Lazer et al., *The Parable of Google Flu* — Science, 2014.
- Obermeyer et al., *Dissecting racial bias in an algorithm…* — Science, 2019.
- Wong et al., *External validation of a widely implemented proprietary sepsis prediction model* — JAMA Internal Medicine, 2021.
- Wynants et al., *Prediction models for COVID-19: systematic review and critical appraisal* — BMJ, 2020 (living review).
- Beede et al., *A human-centered evaluation of a deep learning system deployed in clinics* — CHI, 2020.

**02-detect-the-unusual.md**

- Farrington et al., *A statistical algorithm for the early detection of outbreaks of infectious disease* — JRSS-A, 1996.
- Noufaily et al., *An improved algorithm for outbreak detection in multiple surveillance systems* — Statistics in Medicine, 2013.
- Lazer et al., *The parable of Google Flu: traps in big data analysis* — Science, 2014.

**03-predict-what-happens-next.md**

- **Gneiting T, Raftery AE.** *Strictly proper scoring rules, prediction, and estimation.* **JASA** 2007. The foundation. Dense but decisive.
- **Cori A, Ferguson NM, Fraser C, Cauchemez S.** *A new framework and software to estimate time-varying reproduction numbers.* **AJE** 2013 (`EpiEstim`).
- **Keeling MJ, Rohani P.** *Modeling Infectious Diseases in Humans and Animals* (2008). The textbook, if you want compartmental models properly.

**04-labels-from-databases.md**

- **Grinsztajn L, Oyallon E, Varoquaux G.** *Why do tree-based models still outperform deep learning on typical tabular data?* **NeurIPS** 2022. The evidence for the claim in Section 0.
- **Kaufman S, Rosset S, Perlich C.** *Leakage in data mining.* **ACM TKDD** 2012. The original taxonomy; still the clearest.
- **Sterne JAC, White IR, Carlin JB, et al.** *Multiple imputation for missing data.* **BMJ** 2009 — and read it *against* this lesson: the assumptions it requires are frequently violated in EHR data precisely because missingness is a decision.
- **Collins GS et al.** *TRIPOD+AI.* **BMJ** 2024.
- **Wolff RF, Moons KGM, Riley RD, et al.** *PROBAST.* **Annals of Internal Medicine** 2019.
- **Vickers AJ, Elkin EB.** *Decision curve analysis.* 2006.

**05-labels-from-pixels.md**

- Esteva A et al. *Dermatologist-level classification of skin cancer with deep neural networks.* **Nature** 2017.
- Winkler JK et al. *Association between surgical skin markings in dermoscopic images and diagnostic performance of a deep learning CNN for melanoma recognition.* **JAMA Dermatology** 2019. The confound, demonstrated.
- Zech JR et al. *Variable generalization performance of a deep learning model to detect pneumonia in chest radiographs: a cross-sectional study.* **PLOS Medicine** 2018. Site as a confound, cleanly shown.
- Roberts M et al. *Common pitfalls and recommendations for using machine learning to detect and prognosticate for COVID-19 using chest radiographs and CT scans.* **Nature Machine Intelligence** 2021.
- WHO consolidated guidelines on tuberculosis, Module 2: Screening (2021) — CAD for CXR.

**06-finding-structure.md**

- **Kulldorff M.** *A spatial scan statistic.* **Communications in Statistics** 1997 — and the SaTScan documentation, which is unusually good on the Monte Carlo null.
- **Tibshirani R, Walther G, Hastie T.** *Estimating the number of clusters in a data set via the gap statistic.* **JRSS-B** 2001. The gap statistic *is* the null comparison, formalised — and it is much less used than the elbow it should have replaced.
- **von Luxburg U, Williamson RC, Guyon I.** *Clustering: science or art?* 2012. Short and clarifying on why this shape resists evaluation.
- **Wattenberg M, Viégas F, Johnson I.** *How to use t-SNE effectively.* **Distill** 2016. The clearest demonstration that these plots mislead, with interactive examples.
- **Chari T, Pachter L.** *The specious art of single-cell genomics.* ~2023. Blunt, and the argument generalises well beyond genomics.

**07-language-into-data.md**

- **Temporality.** "History of TB, treated 2019" is not a current case. "Family history of diabetes" is not the patient's diagnosis.
- Chapman et al., *A simple algorithm for identifying negated findings and diseases in discharge summaries* (NegEx) — Journal of Biomedical Informatics, 2001.
- Singhal et al., *Large language models encode clinical knowledge* (Med-PaLM) — Nature, 2023.

**08-choosing-an-action.md**

- **Vickers AJ, Elkin EB.** *Decision curve analysis: a novel method for evaluating prediction models.* **Medical Decision Making** 2006. Short, and it changes how you read every risk model.
- **Vickers AJ, van Calster B, Steyerberg EW.** *Net benefit approaches to the evaluation of prediction models.* **BMJ** 2016. The practical version.
- **Komorowski M, Celi LA, Badawi O, Gordon AC, Faisal AA.** *The Artificial Intelligence Clinician learns optimal treatment strategies for sepsis in intensive care.* **Nature Medicine** 2018. Read it, then read the critiques.
- **Gottesman O, Johansson F, Komorowski M, et al.** *Guidelines for reinforcement learning in healthcare.* **Nature Medicine** 2019. Written partly in response, and unusually candid about what offline RL cannot support.
- The literature on **vaccine allocation modelling** from 2020–21, and on **risk-based active case finding** in TB and HAT.

**09-evaluation.md**

- Collins et al., *TRIPOD+AI statement* — BMJ, 2024.
- Wong et al., *External validation of a widely implemented proprietary sepsis prediction model in hospitalized patients* — JAMA Internal Medicine, 2021.
- Obermeyer et al., *Dissecting racial bias in an algorithm used to manage the health of populations* — Science, 2019.
- Wynants et al., *Prediction models for diagnosis and prognosis of covid-19* — BMJ, 2020.
- Vickers & Elkin, *Decision curve analysis* — Medical Decision Making, 2006.
- Gneiting & Raftery, *Strictly proper scoring rules, prediction, and estimation* — JASA, 2007.

**10-deployment-bias-governance.md**

- **WHO.** *Ethics and governance of artificial intelligence for health* (2021), and the later guidance on large multi-modal models. Free, and the right global-health reference.
- **Obermeyer Z, et al.** **Science** 2019 — label bias, with its fix.
- **EU AI Act** (Regulation 2024/1689) — the high-risk tier and its obligations.
- **EU MDR** (2017/745) — when software becomes a device.
- **TRIPOD+AI** (Collins et al., BMJ 2024) · **PROBAST+AI** · **DECIDE-AI** (Vasey et al., BMJ
- **Topol EJ.** *High-performance medicine: the convergence of human and artificial intelligence.* **Nature Medicine** 2019 — for the optimistic framing, read against Beede.
- **Wiens J, Saria S, Sendak M, et al.** *Do no harm: a roadmap for responsible machine learning for health care.* **Nature Medicine** 2019.
- **Wachter R.** *The Digital Doctor* (2015). How clinical software reshapes clinical work in ways nobody intended. Pre-LLM and still the most useful book here.
- **O'Neil C.** *Weapons of Math Destruction* (2016) — feedback loops, non-technically.
- **Kearns M, Roth A.** *The Ethical Algorithm* (2019).

**20-dd-google-flu-trends.md**

- **Outcome:** CDC's published ILI proportion, by region, for roughly 2003–2008.
- **Detect a novel event.** A model fitted on historical relationships is definitionally blind to a change in those relationships. 2009 was not bad luck; it was the design.
- Ginsberg J, Mohebbi MH, Patel RS, Brammer L, Smolinski MS, Brilliant L. *Detecting influenza epidemics using search engine query data.* **Nature** 2009;457:1012–1014. The original. Short, readable, and the method is fully described.
- Cook S, Conrad C, Fowlkes AL, Mohebbi MH. *Assessing Google Flu Trends performance in the United States during the 2009 influenza virus A (H1N1) pandemic.* **PLoS ONE** 2011. The under-estimation, quantified.
- Butler D. *When Google got flu wrong.* **Nature** news feature, 2013. The 2012–13 over-estimation as it was being noticed.
- Olson DR, Konty KJ, Paladini M, Viboud C, Simonsen L. *Reassessing Google Flu Trends data for detection of seasonal and pandemic influenza.* **PLoS Computational Biology** 2013.
- Yang S, Santillana M, Kou SC. *Accurate estimation of influenza epidemics using Google search data via ARGO.* **PNAS** 2015. The credible successor: recalibrated continuously against ground truth.
- Salganik MJ. *Bit by Bit: Social Research in the Digital Age* (2018; free online). Chapter 2 on observing behaviour is the best available treatment of why found data behaves differently from designed data. Directly generalises this case.

**21-dd-two-imaging-stories.md**

- **WHO consolidated guidelines on tuberculosis. Module 2: Screening — systematic screening for tuberculosis disease** (2021), and the accompanying operational handbook. **Start here** — this is the document that made CAD official, and it states the caveats plainly. Free.
- Esteva A, Kuprel B, Novoa RA, Ko J, Swetter SM, Blau HM, Thrun S. *Dermatologist-level classification of skin cancer with deep neural networks.* **Nature** 2017;542:115–118. The landmark. Read it, then read the two below.
- Daneshjou R et al. *Disparities in dermatology AI performance on a diverse, curated clinical image set* (Diverse Dermatology Images). **Science Advances** 2022. The skin-tone gap, made measurable.
- Groh M et al. *Evaluating deep neural networks trained on clinical images in dermatology with the Fitzpatrick 17k dataset.* CVPR workshops, 2021.
- Adamson AS, Smith A. *Machine learning and health care disparities in dermatology.* **JAMA Dermatology** 2018. Two pages, and it predicted the problem.
- Topol E. *Deep Medicine* (2019). The optimistic case, well told. Read it against Roberts and Freeman above and you have the whole argument.

**22-dd-the-consultation.md**

- **Singhal K et al.** *Large language models encode clinical knowledge* (Med-PaLM), **Nature** 2023, and the Med-PaLM 2 follow-up. The benchmark lineage AMIE grew out of, and a good illustration of why exam performance is not clinical performance.
- **WHO.** *Ethics and governance of artificial intelligence for health* (2021) and the later guidance on **large multi-modal models** for health. The global-health framing, free.
- **Wachter R.** *The Digital Doctor* (2015). Pre-LLM, and still the best account of how clinical software reshapes clinical work in ways nobody intended. Read it and the ambient scribe story becomes predictable.
- **Topol E.** *Deep Medicine* (2019) — chapters on the clinician-patient relationship. The optimistic case for exactly this technology.

**23-dd-two-database-failures.md**

- Habib AR, Lin AL, Grant RW, on the ESM affair and what it implies for governance of proprietary clinical AI. **JAMA** viewpoints, 2021.
- Chen IY, Pierson E, Rose S, Joshi S, Ferryman K, Ghassemi M. *Ethical machine learning in health care.* **Annual Review of Biomedical Data Science** 2021. Good survey; picks up the label-choice problem directly.
- Jacobs AZ, Wallach H. *Measurement and fairness.* **FAccT** 2021. The formal account of what goes wrong when you substitute a measurable proxy for the construct you care about.
- Passi S, Barocas S. *Problem formulation and fairness.* **FAccT** 2019.
- O'Neil C. *Weapons of Math Destruction* (2016). Obermeyer is the rigorous version of this book's argument.
- Kearns M, Roth A. *The Ethical Algorithm* (2019). For what "fix the label" means technically.

**24-dd-two-that-worked.md**

- **Cramer EY, Ray EL, Lopez VK, et al.** *Evaluation of individual and ensemble probabilistic forecasts of COVID-19 mortality in the United States.* **PNAS** 2022.
- **Bracher J, Ray EL, Gneiting T, Reich NG.** *Evaluating epidemic forecasts in an interval format.* **PLOS Comp Biol** 2021 — the scoring rule the hubs use.
- **Peccia J, Zulli A, Brackney DE, et al.** *Measurement of SARS-CoV-2 RNA in wastewater tracks community infection dynamics.* **Nature Biotechnology** 2020. One of the early lead-time papers.
- **Medema G, Heijnen L, Elsinga G, Italiaander R, Brouwer A.** *Presence of SARS-Coronavirus-2 RNA in sewage.* **Environmental Science & Technology Letters** 2020.


## STANDING — verify before citing

Field knowledge stated in the lesson prose without a source: Farrington/Noufaily aberration
detection as the European routine-surveillance workhorse; the claim that tabular deep learning
reliably loses to gradient boosting; PPV collapse at low prevalence; proper scoring rules (WIS,
CRPS, log score) as the debt owed by probabilistic forecasts; EARS C1/C2/C3 provenance and
design intent. All are standard and none was re-verified while writing.

## What this ledger does not do

It does not check that a paper *says* what the lesson claims it says. A DOI matching its author
and year proves the citation points at the right paper, not that the finding attributed to it is
the finding it reports. That is the second verification layer — `evidence.py` in the MCP server —
and it has not been run over this course.
