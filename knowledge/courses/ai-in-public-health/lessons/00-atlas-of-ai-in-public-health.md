# The Atlas — every use of AI in public health and medicine

This is the front door of the course and the only page that is never finished. Everything else in the course exists to make this page readable.

> ⚠ **On accuracy.** Product names, study findings and approval dates below come from knowledge current to mid-2026 and are written from memory, not from a live search. Treat every specific claim as a lead to verify before you cite it. Entries marked **[?]** are ones I am least sure about. The *taxonomy* is the durable part; the examples are the perishable part.

---

## How to read this atlas

There are not hundreds of kinds of health AI. There are **six**, plus two layers that decide whether any of them works. Every row in every table below is one of these six wearing different clothes.

| | Shape | The question it answers | Classical ancestor |
|---|---|---|---|
| **1** | **Detect the unusual** | "Is this different from what I expected?" | Control charts, CUSUM |
| **2** | **Predict what happens next** | "What will this number be in three weeks?" | ARIMA, compartmental models |
| **3** | **Assign a label** | "What is this thing?" | Logistic regression, diagnostic tests |
| **4** | **Find structure without labels** | "What groups are in here?" | Cluster analysis, factor analysis |
| **5** | **Turn language into data** | "What does this text say, as fields?" | Manual chart abstraction, coding |
| **6** | **Choose an action** | "Given all this, what should we do?" | Operations research, decision analysis |

And the two cross-cutting layers:

- **Evaluation** — the layer that decides whether a model is real. Almost every failure in this atlas is an evaluation failure, not a modelling failure.
- **Deployment & governance** — the layer that decides whether a real model helps anyone.

**Maturity key:** 🔬 research only · 🧪 piloted in the field · 🚀 deployed at scale · ⚖️ regulator-cleared · ⚰️ withdrawn, failed, or discredited

**⭑** marks entries with a deep-dive page (or one queued) — the full methodology, how it was evaluated, and what to steal from it.

---

## Shape 1 · Detect the unusual — anomaly detection & early warning

The oldest shape in public health, and the one the NUST course called EEPD. The core tension never changes: **you can have early, or you can have specific, and buying more of one costs you the other.**

| Application | What it does | Maturity | Notes |
|---|---|---|---|
| ⭑ **Farrington / Noufaily aberration detection** | Flags counts above an expected level from historical baselines; the workhorse of European routine surveillance | 🚀 | In the R `surveillance` package. Still the benchmark any ML method must beat |
| **EARS (CDC C1/C2/C3)** | Short-baseline CUSUM variants for settings with no history — designed for mass gatherings and post-disaster | 🚀 | Deliberately crude; useful when you have 7 days of data, not 5 years |
| ⭑ **Syndromic surveillance (ED chief complaints, OTC sales, absenteeism)** | Detects signals before lab confirmation exists | 🚀 | The classic finding: it *is* earlier, and mostly not actionable earlier |
| ⭑ **EIOS (WHO Epidemic Intelligence from Open Sources)** | Machine-assisted scanning of media/web for outbreak signals, triaged by human epidemiologists | 🚀 | The reference implementation of human-in-the-loop event-based surveillance |
| **ProMED-mail / HealthMap** | Curated + automated outbreak event reporting from informal sources | 🚀 | ProMED is human-curated and has had funding crises; HealthMap is the automated cousin |
| **BlueDot, Metabiota** | Commercial epidemic intelligence; flagged unusual Wuhan pneumonia in Dec 2019 | 🧪 | The "AI predicted COVID" story is real but heavily over-told — they flagged a signal, they did not predict a pandemic |
| ⚰️ ⭑ **Google Flu Trends** | Estimated ILI from search volume; drifted badly, over-predicted by ~2× in 2012-13, retired 2015 | ⚰️ | **The single most important teaching case in this atlas.** Big-data hubris, algorithm drift, unstable predictors |
| ⭑ **Wastewater surveillance (SARS-CoV-2, polio)** | Anomaly detection on viral load time series, population-level and pre-symptomatic | 🚀 | Genuinely earlier than clinical signals. Normalisation (flow, PMMoV) is where the methods argument lives |
| **Genomic novelty detection (Nextstrain, Pango, UShER)** | Detects new lineages as they diverge — novelty detection on sequence data | 🚀 | Variant designation is partly automated, partly committee |
| **Pharmacovigilance signal detection (VigiBase, FAERS)** | Disproportionality analysis + ML on spontaneous adverse-event reports | 🚀 | Enormous confounding by reporting behaviour; a masterclass in denominator problems |
| **Health-claims fraud & anomaly detection** | Unusual billing patterns in insurance/financing data | 🚀 | Under-taught in epi but exactly the same maths; relevant to health-financing work |
| **Isolation forests / autoencoders on surveillance series** | Unsupervised multivariate anomaly detection across many signals at once | 🔬 | The main honest advantage over Farrington: *multivariate*. Rarely beats it univariately |
| **Digital participatory surveillance (InfluenzaNet, Flu Near You)** | Self-reported symptoms from volunteer cohorts | 🧪 | Selection bias is the whole story |

---

## Shape 2 · Predict what happens next — forecasting

| Application | What it does | Maturity | Notes |
|---|---|---|---|
| ⭑ **CDC FluSight / COVID-19 Forecast Hub** | Multi-team probabilistic forecasting with a combined ensemble | 🚀 | **The most important empirical finding in the field: the ensemble beats almost every individual model, almost always.** Humility, formalised |
| **European Covid-19 Forecast Hub** | The European equivalent | 🚀 | Same finding, replicated |
| ⭑ **Dengue forecasting (climate + demography)** | Seasonal-ahead outbreak forecasts from rainfall, temperature, ENSO | 🧪 | NUST's case study. INLA-based Bayesian spatio-temporal models are the credible end; XGBoost is the fashionable end |
| **Malaria seasonal forecasting** | Rainfall/NDVI-driven forecasts for stock and campaign planning | 🧪 | |
| **Cholera risk forecasting** | Climate + water access + conflict predictors | 🧪 | |
| **Hospital / ICU demand forecasting** | Bed, ventilator and staffing surge prediction | 🚀 | Became routine practice in 2020-21 and largely stayed |
| **Vaccine & commodity demand forecasting** | Immunisation logistics, stockpiling, quantification | 🚀 | NUST's supply-chain module. Boring, unglamorous, high-value |
| **Proper scoring rules (WIS, CRPS, log score)** | *How you know* a forecast was good | 🚀 | ✱ Point forecasts evaluated by MAE are how bad forecasters look fine. This is the substance of the forecasting lesson |
| **Nowcasting with reporting delay correction** | Corrects for cases not yet reported | 🚀 | `EpiNow2`, `epinowcast`. Failing to do this makes every recent point look like a decline |

---

## Shape 3 · Assign a label — pattern recognition

This shape splits in two: **labels from tables** and **labels from pixels**. The maths is closer than people think; the failure modes are completely different.

### 3a · From databases (tabular)

| Application | What it does | Maturity | Notes |
|---|---|---|---|
| ⚰️ ⭑ **Epic Sepsis Model** | Predicts sepsis onset from EHR; deployed at hundreds of US hospitals | ⚰️ | Externally validated at AUC ~0.63 vs vendor-claimed 0.76–0.83, poor calibration, missed most sepsis while firing constantly. **The best external-validation case study that exists** |
| ⚰️ ⭑ **Optum / Impact Pro risk score** | Identified patients for care management using healthcare **cost** as a proxy for **need** | ⚰️ | Systematically under-referred Black patients at equal illness. The canonical algorithmic-bias case. Fixed by changing the label, not the model |
| ⭑ **Risk prediction from EHR (deterioration, readmission, mortality)** | Generic tabular classification at scale | 🚀 | Where gradient boosting genuinely wins over logistic regression — and where leakage is endemic |
| ⚰️ ⭑ **COVID-19 diagnostic & prognostic models** | 200+ models published in months | ⚰️ | Living systematic review found nearly all at high risk of bias and none clinically usable. A whole literature that produced nothing |
| **Predictive targeting for social/health programmes** | Who gets a cash transfer, a home visit, a screening invitation | 🧪 | Where the ethics get sharpest — the model allocates a scarce good |
| **Tabular deep learning** | Neural nets on structured data | 🔬 | ✱ Consistently loses to gradient boosting on tabular data. Worth knowing so you can say no |
| **Record linkage / entity resolution** | Matching people across databases without a shared ID | 🚀 | Fuzzy matching; you have a saved procedure on this |

### 3b · From images and video

| Application | What it does | Maturity | Notes |
|---|---|---|---|
| ⭑ **TB screening from chest X-ray (CAD4TB, qXR, Lunit)** | Reads CXR for TB-suggestive abnormality; **WHO-recommended since 2021** for screening in people 15+ | 🚀⚖️ | **The strongest public-health AI-at-scale story in LMICs.** Note what WHO endorsed: a *triage/screening* tool with a tunable threshold, not a diagnosis |
| ⭑ **Diabetic retinopathy screening (IDx-DR, EyeArt, ARDA)** | Grades fundus photographs for referable retinopathy | 🚀⚖️ | IDx-DR was the first FDA-cleared *autonomous* diagnostic AI (2018). Landmark accuracy paper: Gulshan et al., JAMA 2016 |
| ⭑ **The Thailand DR deployment study (Beede et al. 2020)** | Ethnographic study of the same model failing in real clinics | 🧪 | Image-quality gating rejected a fifth of patients; nurses worked around it; internet dropouts stalled queues. **Read this before believing any accuracy figure** |
| ⭑ **Skin lesion classification (Esteva et al. 2017 onward)** | CNN matched dermatologists on melanoma/keratinocyte carcinoma from photographs | 🔬🧪 | You asked specifically about this — deep-dive queued. Two famous confounds: **surgical rulers** appearing in malignant images, and training sets dominated by light skin (Fitzpatrick I–III), so performance on dark skin is far weaker and often unmeasured |
| **Cervical cancer — automated visual evaluation** | Classifies cervix images for precancer | 🔬 | **[?]** Early results were strong, then reproducibility problems on external data. A cautionary replication story |
| **Malaria parasite detection on blood smears** | Counts parasites from digitised microscopy | 🧪⚖️ | **[?]** Several devices with WHO/regulatory engagement. Removes microscopist scarcity, adds device dependency |
| **Cervical/oral cancer screening on smartphones** | Point-of-care image capture + classification | 🔬 | |
| ⭑ **AI-guided obstetric ultrasound for gestational age** | Lets a *novice* with no sonography training sweep a probe and get a reliable estimate | 🧪 | Trialled in Zambia and the US. ✱ The most important design idea here: AI used to **move a skill down the cadre ladder**, not to replace a specialist |
| **Digital pathology** | Tumour detection, grading, mitosis counting on whole-slide images | 🚀⚖️ | Well-regulated, well-evidenced, mostly high-income |
| **ECG interpretation** | Arrhythmia detection, and "hidden" labels like low ejection fraction or age | 🚀⚖️ | ✱ The interesting result is models reading things off ECGs no cardiologist can see |
| **Retinal images as a systemic biomarker** | Cardiovascular risk, anaemia, kidney disease from fundus photos | 🔬 | Same idea as above: the image knows more than the clinical use case |
| **Cough and voice classifiers (TB, COVID)** | Audio classification for screening | 🔬 | ⚠ Heavily hyped, weakly evidenced. Repeated failures to generalise across recording devices and sites |
| **Video — surgical workflow, gait, infant motor development** | Temporal models on video streams | 🔬 | |
| **Video — insect/vector identification** | Species ID from trap images or in-flight video | 🔬🧪 | Directly relevant to entomological surveillance |
| **Video — behavioural/compliance surveillance** | Mask wearing, crowd density, distancing | ⚰️ | ⚠ Deployed during COVID, ethically corrosive, largely abandoned. Worth studying as a governance failure |
| **Satellite & street-view imagery** | Building footprints, population, housing quality, water bodies, road access | 🚀 | ✱ Quietly one of the highest-value uses in global health: it builds *denominators* where no census exists |

---

## Shape 4 · Find structure without labels — clustering & representation

| Application | What it does | Maturity | Notes |
|---|---|---|---|
| **Spatial cluster detection (SaTScan, DBSCAN, Getis-Ord)** | Finds hotspots without being told where to look | 🚀 | Your home ground. The scan statistic is anomaly detection *and* clustering at once |
| ⭑ **Sepsis phenotypes (Seymour et al. JAMA 2019;321:2003–2017)** | Latent-class analysis found four clinical subtypes with different treatment responses | 🔬 | The best "clustering that meant something" paper. ⚠ Also a reminder that clusters replicate poorly |
| **Genomic transmission clustering (TB, HIV)** | Groups sequences into probable transmission clusters | 🚀 | ⚠ HIV molecular surveillance is a live ethics controversy — clusters identify people, not just viruses |
| **Patient phenotyping from EHR** | Unsupervised subtypes of diabetes, asthma, long COVID | 🔬 | |
| **Embeddings for retrieval** | Turns any object into a vector so similar things sit near each other | 🚀 | The engine under RAG, deduplication, record linkage and image search |
| **Dimension reduction (UMAP, t-SNE)** | Visualising high-dimensional data | 🚀 | ⚠ Distances and cluster sizes in a UMAP plot are not interpretable. Misread constantly |

---

## Shape 5 · Turn language into data — NLP & LLMs

This is the shape that changed most between 2023 and 2026, and the one where the NUST syllabus is thinnest (half of one week).

| Application | What it does | Maturity | Notes |
|---|---|---|---|
| ⭑ **Clinical note → structured fields (cTAKES, MedCAT, n2c2 tasks)** | Extracts diagnoses, drugs, negation from free text | 🚀 | Pre-LLM clinical NLP. Negation and hedging detection is the hard part and always was |
| ⭑ **Ambient clinical documentation (DAX Copilot, Abridge, Nabla)** | Listens to the consultation, drafts the note | 🚀 | ✱ **By volume, the most widely deployed clinical AI in the world right now.** Good evidence on clinician burnout; thin evidence on note accuracy and on what happens when a wrong note propagates |
| ⭑ **AMIE (Google, diagnostic dialogue)** | An LLM conducting a diagnostic *conversation*; in a randomised OSCE-style study it matched or exceeded primary-care physicians on diagnostic accuracy and several communication measures | 🔬 | You asked about AI in consultations — **this is the reference paper**. ⚠ Read the design carefully: text-chat, actors not patients, and the comparator physicians were also confined to text chat |
| **LLMs on medical exams (USMLE, MedQA)** | Benchmark performance, now saturated | 🔬 | ✱ Exam performance measures the exam, not the clinic. Useful mainly as a rhetorical warning |
| ⚰️ ⭑ **Symptom checkers / triage chatbots (Babylon, Ada, K Health, NHS 111 online)** | Patient-facing triage | 🧪⚰️ | Babylon's collapse is the business-model lesson; the clinical-safety literature on triage apps is unflattering. Under-triage of serious presentations is the recurring finding |
| **Outbreak signal extraction from text** | LLMs reading news, ProMED, social media into structured event records | 🧪 | Where EIOS is heading |
| **Literature screening & living reviews (ASReview, Rayyan, Elicit)** | Prioritises abstracts, drafts extractions | 🚀 | Immediately useful to you. Well-studied for screening recall |
| **Coding and classification (ICD, cause of death)** | Auto-assigns codes; verbal autopsy interpretation (InterVA, InSilicoVA) | 🚀 | ✱ Verbal autopsy is a lovely example — a probabilistic model producing national mortality statistics where no death certification exists |
| **Translation & health communication** | Multilingual health messaging, consent, instructions | 🚀 | High value, low glamour, real safety risk on numbers and dosages |
| **RAG over a document corpus** | Answers grounded in a fixed, cited corpus rather than model memory | 🚀 | Metis' own knowledge layer. The deep dive writes itself from your own system |
| **Misinformation detection & infodemiology** | Classifying and tracking health misinformation | 🔬🧪 | |
| **Synthetic clinical text / data** | Shareable stand-ins for records that cannot be shared | 🔬 | ⚠ Privacy guarantees are much weaker than the marketing implies unless formally bounded |

---

## Shape 6 · Choose an action — optimisation & decision support

| Application | What it does | Maturity | Notes |
|---|---|---|---|
| **Targeted active case finding** | Where to send screening teams next | 🧪 | The decision layer on top of shapes 1 and 4 |
| **Vaccine allocation optimisation** | Who gets doses first, given scarcity and transmission structure | 🧪 | Heavily modelled in 2020-21 |
| **Contact tracing prioritisation** | Ranking contacts by expected yield | 🧪 | |
| **Screening interval optimisation** | How often to re-screen, by risk | 🔬 | |
| **Tsetse / vector control siting** | Where to place targets or traps | 🧪 | |
| ⚰️ ⭑ **"AI Clinician" for sepsis (Komorowski et al. 2018)** | Reinforcement learning recommending vasopressor/fluid policy | 🔬⚰️ | Nature Medicine, then substantial methodological criticism. ✱ Off-policy evaluation from observational data is the trap: the model can look brilliant while never having been tested |
| **Supply chain & routing optimisation** | Cold chain, drone delivery, last-mile | 🚀 | Zipline-style delivery is a real, working, unglamorous success |
| **Health workforce scheduling** | Rostering and task-shifting under constraints | 🚀 | |

---

## Cross-cutting layer A · Evaluation — where nearly everything dies

If you take one page from this course, take this one.

| Concept | Why it decides everything |
|---|---|
| **PPV depends on prevalence** | A test at 95% sensitivity and 95% specificity is nearly useless at 1/10,000. AUC hides this completely |
| **Discrimination vs calibration** | AUC says "ranks people correctly". Calibration says "the number 0.7 means 70%". Only the second supports a decision. Most papers report only the first |
| **External validation** | Internal cross-validation measures the dataset. Epic Sepsis passed internally and failed everywhere |
| **Dataset shift** | Site, scanner, season, coding practice, population. The model has no idea any of these changed |
| **Leakage** | The single most common cause of fake performance. Post-outcome variables, patient overlap across folds, timestamps |
| **Confounded features** | Rulers in melanoma images. Chest drains signalling pneumothorax. The model is right for the wrong reason |
| **Proper scoring rules** | For forecasts: WIS, CRPS, log score. MAE on a point forecast rewards over-confidence |
| **Subgroup performance** | Aggregate accuracy is a weighted average that hides who the model fails |
| **Clinical utility ≠ accuracy** | Decision curves, net benefit, and the question "what would change?" |
| **TRIPOD+AI · PROBAST+AI · CONSORT-AI · DECIDE-AI · STARD-AI** | The reporting and risk-of-bias frameworks. Reading a paper against PROBAST takes 20 minutes and settles most arguments |

---

## Cross-cutting layer B · Deployment, bias & governance

| Topic | Notes |
|---|---|
| **The AI chasm** | The gap between published accuracy and any measurable patient benefit. Very few systems have crossed it |
| **Label bias** | Obermeyer: the model was excellent at predicting what it was asked to predict. The *label* was wrong |
| **Representation bias** | Skin tone in dermatology sets; genomic reference panels; who is in the training data at all |
| **Automation bias & alarm fatigue** | Clinicians defer to a confident wrong model, and ignore a model that cries wolf. Both are measurable |
| **Human factors** | Beede et al.: the model worked; the clinic did not |
| **WHO guidance** | 2021 *Ethics and governance of AI for health*; later guidance on large multi-modal models. The reference documents for global health |
| **EU AI Act** | Medical AI largely lands in the high-risk tier: risk management, data governance, human oversight, post-market monitoring. Obligations phasing in through 2026-27 — ⚠ directly relevant to you, verify current dates |
| **EU MDR / FDA SaMD** | A model that informs a clinical decision is a regulated device. Continuous learning is handled through predetermined change control |
| **Data protection** | GDPR, secondary use, federated learning as an alternative to pooling |
| **Environmental and dependency cost** | Compute footprint; and what happens when the vendor, the API, or the funding stops |

---

## The cautionary canon

Six cases that, read together, teach more than any methods textbook:

1. ⭑ **Google Flu Trends** — big data does not fix unstable predictors.
2. ⭑ **Epic Sepsis Model** — internal validation is not validation.
3. ⭑ **Obermeyer et al. 2019** — the label carries the bias.
4. ⭑ **Wynants et al. COVID prognostic review** — a whole literature, no usable output.
5. ⭑ **Beede et al. 2020 (Thailand)** — accuracy is not deployment.
6. ⭑ **The AI Clinician** — off-policy evaluation is not evidence.

---

## What this atlas is still missing

Kept deliberately visible, because this list is the course's to-do queue:

- Federated learning in practice (rather than in principle)
- Foundation models for medical imaging, and whether they change the LMIC calculus
- Agentic systems in clinical workflows — brand new, thin evidence, moving fast
- Multi-modal models combining image + text + tabular
- Causal inference vs prediction, done properly rather than gestured at
- Digital twins for health systems — currently more brochure than science
- Antimicrobial resistance prediction from genomes
- Climate–health attribution modelling
- Africa CDC / AFENET regional capacity programmes
- Economic evaluation of AI interventions — almost absent from the literature

---

## How a new entry enters this atlas

Every AI-in-public-health item that reaches you through news, a paper, or a colleague goes through four questions:

1. **Which of the six shapes is it?** If it doesn't fit, that is a finding — say so.
2. **What is the classical method it must beat?** No comparator, no claim.
3. **How was it evaluated?** Internal only? Calibration reported? Subgroups?
4. **Maturity, honestly** — research, piloted, at scale, or withdrawn.

Answer those four and it becomes a row. Answer them in depth and it becomes a deep-dive page.
