# Deep dive — Two imaging stories: why chest X-ray AI reached scale and dermatology AI did not

**Shape 3** (assign a label, from pixels) · Maturities **🚀⚖️ deployed and endorsed** vs **🔬 research** · Stresses the **deployment & governance** layer

> ⚠ Written from model knowledge to mid-2026. Product names, dates and figures are leads to verify. The comparison is the durable content.

Both stories start the same way: a convolutional network learns to read a medical image and matches specialists on a benchmark. One is now WHO-recommended and screening people in dozens of countries. The other, nine years on, is still mostly a research finding and a consumer app. **Understanding why is the most useful thing in this course**, because the difference is not accuracy.

---

## 1 · The questions someone actually asked

**Chest X-ray / TB.** Tuberculosis kills over a million people a year, and a large share of cases are never diagnosed. Active case-finding works, but chest radiography — the sensitive first step — requires a reader, and **radiologists are the scarcest resource in exactly the places with the most TB.** The question: *can we screen at population scale where there is no radiologist?*

**Dermatology / skin lesions.** Melanoma is curable when caught early and lethal when not, and the decision to biopsy rests on visual inspection by a dermatologist — again scarce, and waiting lists long. The question: *can a phone camera triage skin lesions as well as a dermatologist?*

✱ Read those two questions again. The first asks whether AI can **replace a missing specialist in a defined public-health programme**. The second asks whether it can **match a present specialist in an open-ended clinical judgement**. That difference in framing largely determines the two outcomes.

## 2 · Why each looked tractable

Both became tractable for the same unglamorous reason: **labelled image archives existed.**

- TB: decades of chest radiographs in screening programmes, many with a bacteriological reference standard (culture, later Xpert MTB/RIF) attached. **The label is a lab result.**
- Skin: large dermatology image collections, with the ISIC archive as the public backbone, labels from histopathology on biopsied lesions or from clinical diagnosis otherwise. **The label is often a dermatologist's opinion.**

⚠ That asymmetry in *where the label comes from* is the second structural difference, and it compounds the first.

## 3 · The data, and what it does not represent

| | Chest X-ray / TB | Skin lesions |
|---|---|---|
| **Reference standard** | Bacteriological (culture / Xpert) — independent of the reader | Histopathology on biopsied lesions; clinical diagnosis otherwise |
| **Acquisition** | Standardised: fixed projection, calibrated device, trained radiographer | Uncontrolled: any phone, any light, any distance, any skin |
| **Population captured** | Screening cohorts in high-burden settings — close to the deployment population | Predominantly light-skinned patients in high-income specialist clinics |
| **The gap that matters** | Prior TB leaves permanent scarring that looks like disease | Fitzpatrick V–VI badly under-represented, and often **not measured at all** |

The dermatology gap deserves the sharper statement. The problem is not simply that models perform worse on darker skin — that would be a known limitation. It is that **the evaluation sets did not record skin type**, so for years the failure was *invisible rather than known*. Purpose-built diverse test sets (the Diverse Dermatology Images work, and the Fitzpatrick-annotated collections) were built specifically to make it measurable, and when measured, performance dropped.

## 4 · The methods, explained

Mechanically these are close cousins, and it is worth being clear that **the modelling is not where they differ.**

Both take an image, pass it through a deep convolutional network (later, vision transformers) pretrained on general photographs, and fine-tune on the medical archive. The network learns hierarchical filters — edges, then textures, then configurations — and the final layer outputs a score.

The consequential design choices are not architectural:

- **What the score means.** TB CAD outputs a **continuous abnormality score** with an explicitly configurable threshold. Dermatology models typically output a **class** (melanoma / benign) or a ranked differential. One is designed as a tunable screening instrument; the other imitates a diagnosis.
- **Where it sits in the pathway.** TB CAD is deliberately *upstream*: it decides who gets a molecular test. Dermatology AI has usually been positioned as the decision itself.

<svg viewBox="0 0 640 250" width="100%" style="max-width:640px" role="img" aria-label="Two pathways: TB CAD as a tunable triage step before a confirmatory molecular test, versus dermatology AI positioned as the diagnosis itself"><text x="8" y="16" font-size="11" font-weight="600" fill="currentColor">TB screening — AI as a tunable gate BEFORE a confirmatory test</text><rect x="8" y="28" width="96" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="56" y="52" font-size="10" text-anchor="middle" fill="currentColor">chest X-ray</text><path d="M104 48 L136 48" stroke="currentColor" stroke-width="1.2"/><path d="M130 44 l6 4 -6 4" fill="currentColor"/><rect x="137" y="28" width="106" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="2"/><text x="190" y="46" font-size="10" text-anchor="middle" fill="currentColor">CAD score</text><text x="190" y="59" font-size="8.5" text-anchor="middle" fill="currentColor" opacity="0.75">threshold set locally</text><path d="M243 48 L275 48" stroke="currentColor" stroke-width="1.2"/><path d="M269 44 l6 4 -6 4" fill="currentColor"/><rect x="276" y="28" width="106" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="329" y="46" font-size="10" text-anchor="middle" fill="currentColor">Xpert MTB/RIF</text><text x="329" y="59" font-size="8.5" text-anchor="middle" fill="currentColor" opacity="0.75">independent truth</text><path d="M382 48 L414 48" stroke="currentColor" stroke-width="1.2"/><path d="M408 44 l6 4 -6 4" fill="currentColor"/><rect x="415" y="28" width="96" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="463" y="52" font-size="10" text-anchor="middle" fill="currentColor">treat</text><text x="527" y="44" font-size="9" fill="currentColor" opacity="0.8">a wrong score</text><text x="527" y="56" font-size="9" fill="currentColor" opacity="0.8">costs a test</text><line x1="8" y1="92" x2="632" y2="92" stroke="currentColor" stroke-width="0.8" opacity="0.35"/><text x="8" y="116" font-size="11" font-weight="600" fill="currentColor">Dermatology — AI positioned AS the decision</text><rect x="8" y="128" width="96" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="56" y="146" font-size="10" text-anchor="middle" fill="currentColor">phone photo</text><text x="56" y="159" font-size="8.5" text-anchor="middle" fill="currentColor" opacity="0.75">any light, any device</text><path d="M104 148 L136 148" stroke="currentColor" stroke-width="1.2"/><path d="M130 144 l6 4 -6 4" fill="currentColor"/><rect x="137" y="128" width="106" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="2"/><text x="190" y="146" font-size="10" text-anchor="middle" fill="currentColor">class label</text><text x="190" y="159" font-size="8.5" text-anchor="middle" fill="currentColor" opacity="0.75">fixed threshold</text><path d="M243 148 L275 148" stroke="currentColor" stroke-width="1.2"/><path d="M269 144 l6 4 -6 4" fill="currentColor"/><rect x="276" y="128" width="106" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3"/><text x="329" y="146" font-size="10" text-anchor="middle" fill="currentColor">reassure /</text><text x="329" y="159" font-size="10" text-anchor="middle" fill="currentColor">or seek care</text><text x="404" y="144" font-size="9" fill="currentColor" opacity="0.8">a wrong label costs</text><text x="404" y="156" font-size="9" fill="currentColor" opacity="0.8">a missed melanoma</text><text x="8" y="196" font-size="10" font-weight="600" fill="currentColor">The structural difference</text><text x="8" y="213" font-size="9.5" fill="currentColor" opacity="0.85">Top: an independent confirmatory test absorbs the model's errors, so the threshold becomes a policy dial.</text><text x="8" y="228" font-size="9.5" fill="currentColor" opacity="0.85">Bottom: nothing downstream catches the error, so the model must be right on its own — a far higher bar.</text><text x="8" y="243" font-size="9.5" fill="currentColor" opacity="0.85">This, not accuracy, is why one reached scale.</text></svg>

## 5 · What each found

**Dermatology, 2017.** Esteva et al., *Nature*: a network trained on roughly **129,000 clinical images** across some **2,000 diseases** matched **21 board-certified dermatologists** on biopsy-proven keratinocyte carcinoma and melanoma classification. A landmark, and correctly celebrated.

**TB CAD, ~2019–2021.** Head-to-head evaluations of several commercial products against human readers, in high-burden settings, using **bacteriological confirmation as the reference standard** — not radiologist agreement. Several products met or exceeded WHO's target performance profile for a TB triage test. In **2021, WHO recommended CAD** as an alternative to human reading of chest radiographs for TB screening and triage in people aged 15 and over.

⚠ Note the different achievements. Dermatology matched *specialists on a benchmark*. TB CAD met *a performance profile defined in advance by the body that would recommend it*, against *an independent reference standard*, in *the population where it would be used*.

## 6 · How each was evaluated

| Question | TB CAD | Dermatology |
|---|---|---|
| **Comparator** | Human readers **and** a defined target product profile | 21 dermatologists on a curated set |
| **Reference standard** | Bacteriological — independent of any reader | Histopathology where biopsied; clinician label otherwise |
| **External validation** | Multi-country, multi-site, in the deployment population | Largely within-archive; diverse external sets came later, and lowered performance |
| **Subgroups reported** | Yes, and consequentially: age, prior TB, HIV status | Initially not at all — skin type frequently unrecorded |
| **Calibration / threshold** | Explicitly a local decision from local prevalence | Usually a fixed vendor threshold |
| **Shape 3's debt paid?** | **Yes** | **Partly, and late** |

✱ The most quietly important row is *subgroups*. WHO's recommendation came with the finding that CAD performs less well in people with **prior TB** — old fibrotic scarring looks like active disease. That is exactly the kind of honest, actionable caveat that lets a programme design around a limitation. Dermatology's equivalent caveat took years to be measurable at all.

## 7 · What happened next

**TB CAD** is in routine use in national programmes, mobile screening vans and prison and mining screening, with products including CAD4TB, qXR and Lunit INSIGHT CXR. It sits inside a **WHO guideline**, which means procurement, thresholds and monitoring have institutional homes. Debate has moved on to the right questions: threshold selection by setting, cost per case detected, performance drift, and vendor dependency.

**Dermatology** went two ways. Clinically, AI entered *dermatologist workflows* as decision support in well-resourced systems, which is a real if modest contribution. Commercially, it went into **consumer apps**, and there the evidence is poor — a systematic review of smartphone skin-cancer apps found the evidence base weak and the risk of missed melanoma real. Meanwhile the confound literature grew uncomfortable: **surgical skin markings** were shown to inflate melanoma scores, and analyses of public archives found **rulers** present disproportionately in malignant images. In both cases the model was right for the wrong reason, because the photograph recorded *what the clinician already suspected*.

## 8 · What each is actually worth

**TB CAD: genuinely valuable, and quantifiably so.**

In the units of the decision: it converts chest radiography from a bottleneck requiring a scarce specialist into a **throughput-limited, tunable triage step**. Its value is *additional TB cases detected per 1,000 screened, per unit cost*, in settings that would otherwise screen nobody. The counterfactual is not a radiologist; it is **no screening at all**.

Its limits are real and known: it degrades where prior TB is common, it needs a local threshold, it needs a confirmatory test downstream to be safe, and it creates dependency on a commercial vendor whose model may change. ✱ The condition under which its value collapses: **remove the confirmatory test.** Then every false positive becomes a course of TB treatment, and PPV at low prevalence makes that intolerable.

**Dermatology: real potential, largely unrealised, and mis-aimed.**

The honest assessment: as **triage in a system that has dermatologists** — ranking a referral queue, flagging urgent lesions — the potential is solid and partly realised. As **autonomous diagnosis on a consumer phone**, it fails on three counts simultaneously: uncontrolled image acquisition, a training population unlike the user, and no downstream check to absorb errors. A missed melanoma has no confirmatory test to catch it, because the patient has been reassured and gone home.

Where the potential is largest and least pursued: **task-shifting in settings with no dermatologist at all**, which is the TB CAD framing applied to skin. That would require diverse training data, a tunable threshold, and a referral pathway to absorb positives — the three things the field mostly did not build.

<svg viewBox="0 0 640 210" width="100%" style="max-width:640px" role="img" aria-label="Comparison of five conditions that let TB CAD reach scale and that dermatology AI mostly lacks"><text x="200" y="14" font-size="10" font-weight="600" text-anchor="middle" fill="currentColor">condition for reaching practice</text><text x="452" y="14" font-size="10" font-weight="600" text-anchor="middle" fill="currentColor">TB CAD</text><text x="560" y="14" font-size="10" font-weight="600" text-anchor="middle" fill="currentColor">derm AI</text><line x1="8" y1="22" x2="632" y2="22" stroke="currentColor" stroke-width="0.8" opacity="0.4"/><text x="8" y="44" font-size="10" fill="currentColor">Label independent of the reader</text><text x="452" y="44" font-size="12" text-anchor="middle" fill="currentColor">●</text><text x="560" y="44" font-size="12" text-anchor="middle" fill="currentColor" opacity="0.3">○</text><text x="8" y="68" font-size="10" fill="currentColor">Standardised image acquisition</text><text x="452" y="68" font-size="12" text-anchor="middle" fill="currentColor">●</text><text x="560" y="68" font-size="12" text-anchor="middle" fill="currentColor" opacity="0.3">○</text><text x="8" y="92" font-size="10" fill="currentColor">Training population = deployment population</text><text x="452" y="92" font-size="12" text-anchor="middle" fill="currentColor">●</text><text x="560" y="92" font-size="12" text-anchor="middle" fill="currentColor" opacity="0.3">○</text><text x="8" y="116" font-size="10" fill="currentColor">Tunable threshold, set from local prevalence</text><text x="452" y="116" font-size="12" text-anchor="middle" fill="currentColor">●</text><text x="560" y="116" font-size="12" text-anchor="middle" fill="currentColor" opacity="0.3">○</text><text x="8" y="140" font-size="10" fill="currentColor">Confirmatory test downstream absorbs errors</text><text x="452" y="140" font-size="12" text-anchor="middle" fill="currentColor">●</text><text x="560" y="140" font-size="12" text-anchor="middle" fill="currentColor" opacity="0.3">○</text><text x="8" y="164" font-size="10" fill="currentColor">Guideline home for procurement and monitoring</text><text x="452" y="164" font-size="12" text-anchor="middle" fill="currentColor">●</text><text x="560" y="164" font-size="12" text-anchor="middle" fill="currentColor" opacity="0.3">○</text><line x1="8" y1="176" x2="632" y2="176" stroke="currentColor" stroke-width="0.8" opacity="0.4"/><text x="8" y="196" font-size="9.5" fill="currentColor" opacity="0.85">Not one of these six rows is about model accuracy. Both models matched specialists on a benchmark.</text><text x="8" y="207" font-size="9.5" fill="currentColor" opacity="0.85">Only one was built into a pathway that could carry it.</text></svg>

## 9 · Transferable lessons

1. **The pathway matters more than the model.** An AI step with an independent confirmatory test downstream can be imperfect and still safe. One that is the final decision cannot.
2. **A continuous score with a locally set threshold beats a fixed class label.** It turns a technical property into a policy dial, which is what lets different settings use the same product.
3. **Prefer a label that does not come from the person you are replacing.** A bacteriological reference standard makes a stronger claim than agreement with clinicians.
4. **Ask "replace a missing specialist" rather than "match a present one".** The first is a health-systems question with a measurable benefit; the second is a benchmark contest.
5. **Unmeasured subgroups are worse than known-poor subgroups.** Measure skin type, prior disease, age, site — or your limitation is invisible instead of manageable.
6. **A target product profile defined before development, by the body that will recommend it, is a huge accelerator.** WHO's TPP told developers what "good enough" meant.
7. **Suspect the image records the clinician's suspicion.** Rulers, markings, portable equipment, drains. If it correlates with the label, the model will find it.

## 10 · Explain it in 60 seconds

> In 2017 an AI matched 21 dermatologists at spotting skin cancer from photographs. Around the same time, AI learned to read chest X-rays for TB. Today the TB one is recommended by WHO and screening people in dozens of countries; the skin one is mostly still a research result and some phone apps of doubtful value.
>
> The difference isn't accuracy — both matched specialists. It's that the TB system was built as a **triage step with a lab test behind it**. It gives a score, each country sets its own cut-off, and anyone it flags gets a molecular test. So when it's wrong, it costs a test. The skin apps were built to be the answer itself — one fixed threshold, no lab behind it — so when they're wrong, someone with a melanoma is told not to worry and goes home.
>
> Add that TB models were trained on the same populations they'd be used in and validated against a lab result, while dermatology models were trained mostly on light skin and validated against dermatologists' opinions — often without even recording skin type, so nobody could see the problem.
>
> The lesson: whether medical AI helps anyone depends far more on the pathway you put it in than on how good the model is.

## 11 · Read more

**TB / chest X-ray CAD**

- **WHO consolidated guidelines on tuberculosis. Module 2: Screening — systematic screening for tuberculosis disease** (2021), and the accompanying operational handbook. **Start here** — this is the document that made CAD official, and it states the caveats plainly. Free.
- WHO. *Target product profile for a TB triage test.* The prior specification of "good enough". A model of how to make evaluation tractable before development starts.
- **Qin ZZ, et al.** *Tuberculosis detection from chest x-rays for triaging in a high tuberculosis-burden setting: an evaluation of five artificial intelligence algorithms.* **Lancet Digital Health** 2021. ✓ **Verified 2026-08-21 — the head-to-head evaluation.** See also the prospective triage-accuracy study against culture-confirmed disease (Lancet Digit Health 2021) and the South African prevalence-survey external validation with modelled impacts (Lancet Digit Health 2024;6:e605–13, plus its correction).
- Kik SV, Denkinger CM et al., on threshold selection and cost per case detected.

**Dermatology**

- Esteva A, Kuprel B, Novoa RA, Ko J, Swetter SM, Blau HM, Thrun S. *Dermatologist-level classification of skin cancer with deep neural networks.* **Nature** 2017;542:115–118. The landmark. Read it, then read the two below.
- Winkler JK et al. *Association between surgical skin markings in dermoscopic images and diagnostic performance of a deep learning convolutional neural network for melanoma recognition.* **JAMA Dermatology** 2019;155(10):1135–1141. ✓ Verified. The confound, demonstrated cleanly: markings raised melanoma probability scores and increased the false-positive rate on benign nevi by roughly **40%**.
- Daneshjou R et al. *Disparities in dermatology AI performance on a diverse, curated clinical image set* (Diverse Dermatology Images). **Science Advances** 2022. The skin-tone gap, made measurable.
- Groh M et al. *Evaluating deep neural networks trained on clinical images in dermatology with the Fitzpatrick 17k dataset.* CVPR workshops, 2021.
- Freeman K et al. *Algorithm based smartphone apps to assess risk of skin cancer in adults: systematic review of diagnostic accuracy studies.* **BMJ** 2020;368:m127. ✓ Verified. The consumer-app evidence, and it is not good.
- Adamson AS, Smith A. *Machine learning and health care disparities in dermatology.* **JAMA Dermatology** 2018. Two pages, and it predicted the problem.

**Cross-cutting on medical imaging AI**

- Roberts M et al. *Common pitfalls and recommendations for using machine learning to detect and prognosticate for COVID-19 using chest radiographs and CT scans.* **Nature Machine Intelligence** 2021;3(3):199–217; doi:10.1038/s42256-021-00307-0. ✓ **Verified 2026-08-21.** Reviewed hundreds of models; found none fit for clinical use. The best single demonstration that imaging AI's problem is method, not architecture.
- **Beede E, Baylor E, Hersch F, Iurchenko A, Wilcox L, Ruamviboonsuk P, Vardoulakis LM.** *A human-centered evaluation of a deep learning system deployed in clinics for the detection of diabetic retinopathy.* **CHI '20**; doi:10.1145/3313831.3376718. ✓ **Verified 2026-08-21** — fieldwork in 11 clinics in Pathum Thani and Chiang Mai, Thailand. The best account of deployment reality there is.
- Oakden-Rayner L. Blog and papers on hidden stratification and dataset flaws in medical imaging. Unusually clear-eyed, and readable.

**Books**

- Topol E. *Deep Medicine* (2019). The optimistic case, well told. Read it against Roberts and Freeman above and you have the whole argument.
- Kelleher JD, Tierney B. *Data Science* (MIT Press Essential Knowledge). Short, non-technical, good on what these methods actually do.

⚠ Every citation above is from memory. The Esteva, Winkler, Freeman, Roberts and Beede references I am most confident about; the TB CAD evaluation papers least. A librarian pass should resolve them before any of this is taught or cited.
