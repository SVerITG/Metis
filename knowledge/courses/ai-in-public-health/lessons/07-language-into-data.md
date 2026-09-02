# Lesson 7 — Language into data: clinical NLP, LLMs, and AI in the consultation

> **Concept map**
> **Builds on** — Lesson 1: this is shape 5, whose classical comparator is a human chart abstractor. Lesson 9 supplies the evaluation framing this lesson leans on hardest.
> **Connects to** — Lesson 2, because event-based surveillance (EIOS) is anomaly detection *on text*; and Lesson 8, because a consultation assistant is a decision-support system wearing conversational clothes.
> **Leads to** — the AMIE and ambient-documentation deep dives, and the Atlas' fastest-moving rows.

## Why this matters

This is the shape that changed most between 2023 and 2026, and the one the NUST syllabus gives half a week. It is also the shape where you have the least classical intuition to fall back on, because there is no equivalent of "sensitivity and specificity" that people routinely report for a language system — so the marketing has almost nothing pushing back on it.

Two facts to hold together:

1. **By volume, the most widely deployed clinical AI in the world is a scribe.** Not a diagnostic model. Systems that listen to a consultation and draft the note are in routine use across large health systems.
2. **The best evidence that an AI can conduct a diagnostic consultation comes from a study where the human comparator was also forbidden from examining the patient.**

Neither fact is what the headlines say. Both are more interesting than the headlines.

✱ And a warning specific to this shape: a wrong number looks wrong. A wrong *sentence* looks like prose. Fluency is not a proxy for correctness, and it is the only signal most readers have.

## Learning objectives
By the end of this lesson you will be able to:

- **Explain** why "define correct" is the hard problem in language tasks, and where negation and hedging break extractors.
- **Evaluate** a text-extraction system with the same sensitivity/specificity/PPV framework you use for a diagnostic test.
- **Appraise** claims about AI in consultations by identifying what the comparator was actually allowed to do.
- **Distinguish** retrieval-grounded generation from model recall, and say why the difference is an evaluation question.

## Prerequisites
Lesson 1. Lesson 9 is strongly recommended first — this lesson uses its vocabulary throughout.

---

## Section 1 · The task, and why it is harder than it looks

The generic form of shape 5: **take unstructured text, return fields.** A discharge summary becomes diagnoses, drugs, doses. A media report becomes location, pathogen, case count. A consultation becomes a note.

The classical comparator is a **human chart abstractor**, and this matters more than usual, because humans are not a gold standard here either. Inter-rater agreement on extracting diagnoses from free text is often mediocre. So the first question in any language task is not "how accurate is the model?" but **"accurate against whom, agreeing how well with each other?"**

Where extraction actually breaks:

- **Negation.** "No evidence of tuberculosis" contains the word tuberculosis. A naive extractor records a TB case.
- **Hedging and uncertainty.** "Cannot exclude malaria", "query sepsis", "possible pneumonia". Is that a case? Your answer is a *case definition*, not a technical choice.
- **Temporality.** "History of TB, treated 2019" is not a current case. "Family history of diabetes" is not the patient's diagnosis.
- **Experiencer.** The condition may belong to a relative, not the patient.
- **Abbreviation collision.** In clinical text, short forms are wildly ambiguous and context-dependent, and the same abbreviation means different things by specialty and country.
- **Multilingual and code-switched notes.** Common in your settings, badly served by models trained on English-language records.

⚠ Notice that four of those six are not NLP problems. They are **case-definition problems** wearing NLP clothes. This is the single most useful thing an epidemiologist brings to a language project: the discipline of writing the definition down first.

## Section 2 · The pre-LLM stack, and why it is not obsolete

Clinical NLP existed long before LLMs, and the tools were built precisely around the failure modes above.

- **Dictionary and ontology matching** — map spans of text to UMLS/SNOMED/ICD concepts. Deterministic, auditable, and it will not invent a diagnosis.
- **Negation and context algorithms** (the NegEx / ConText family) — rule-based detection of negation, hedging, experiencer and temporality using trigger terms and scope windows. Simple, transparent, surprisingly strong.
- **Pipelines** — cTAKES, MedCAT, and the shared-task lineage (i2b2/n2c2) that produced the benchmarks the field still quotes.

✱ Why this matters now: a rule-based extractor is **auditable and stable**. You can point at the line that produced a decision, and it produces the same output next month. Neither is true of a generative model. For a statutory notification pipeline or anything that feeds official statistics, that property may matter more than a few points of F1.

**The comparator rule from Lesson 1 applies with unusual force here.** A paper claiming an LLM extracts diagnoses better than "traditional NLP" owes you a comparison against a properly built rule-based extractor with negation handling — not against a keyword search. That comparison is frequently absent, and keyword search is a strawman.

## Section 3 · What LLMs actually changed

Three real changes, and it is worth separating them because they carry different risks.

**1 · Zero-shot generalisation.** Pre-LLM extraction required annotated training data for each task. An LLM can extract a schema it has never been trained on from a prompt. For public health this is transformative in one specific way: **rare tasks become feasible.** Nobody was going to annotate 5,000 notes to extract sleeping-sickness staging fields. Now you can attempt it without a corpus.

**2 · Generation, not just labelling.** The system produces new text — a note, a summary, a translation, an answer. This is a genuinely different task with a genuinely different failure mode: there is no confusion matrix for "wrote a plausible sentence that is false".

**3 · Retrieval grounding (RAG).** Instead of answering from model weights, retrieve passages from a fixed corpus and answer from those, with citations. This converts an unfalsifiable claim into a checkable one, because you can look at what it retrieved.

⚠ The most common evaluation error in this shape: testing a RAG system's answers without separately testing its **retrieval**. If the right passage was never retrieved, the model was never given a chance, and no amount of prompt engineering fixes it. Retrieval and generation must be scored separately — retrieval with recall@k, generation with groundedness against the retrieved text.

✱ Metis' own knowledge layer is exactly this architecture, which makes it the honest worked example: the answers are only as good as what the corpus contains and what the retriever surfaces.

## Section 4 · AI in the consultation

You asked about this specifically. It splits into three quite different products.

### 4a · Ambient documentation — the one that is actually deployed
Systems that listen to a consultation and draft the clinical note. This is, by usage volume, the dominant clinical AI in the world today.

What the evidence supports reasonably well: **reduced documentation burden and improved clinician-reported burnout and satisfaction.** Those are real endpoints and they matter — documentation load is a genuine driver of workforce attrition.

What the evidence supports poorly: **note accuracy, and downstream consequences.** A note is not a terminal artefact. It becomes the basis of the next clinician's decision, the billing code, the audit trail, and the research dataset. An error introduced by a scribe propagates silently into all four.

⚠ And there is an evaluation trap here worth naming: because the endpoint measured is clinician satisfaction, a system can score excellently while systematically degrading data quality. The people best placed to notice — the clinicians — are the ones being relieved of the task of checking.

### 4b · Diagnostic dialogue — the research frontier
**AMIE** (Google) is the reference work: an LLM optimised for diagnostic *conversation*, evaluated in a randomised, OSCE-style study against primary-care physicians, where it matched or exceeded them on diagnostic accuracy and on several dimensions of communication quality as rated by specialists and by the simulated patients.

That is a genuinely striking result. Now read the design, because this is the lesson:

- The "patients" were **trained actors**, not patients.
- The interaction was **text chat**.
- Crucially, the **physician comparator was also confined to text chat** — no examination, no gestalt, no continuity, and working in an unfamiliar medium.

So the honest statement is: *in synchronous text-based consultation with simulated patients, an LLM outperformed physicians who were also restricted to synchronous text.* That is a real finding about a real setting — telehealth is a real setting — and it is not "AI is a better doctor".

✱ This is the four-question routine applied to the highest-profile claim in the shape. The comparator was disadvantaged in a specific, documentable way. Finding that took reading the methods, not the abstract, and that is the transferable skill.

### 4c · Patient-facing triage — the cautionary half
Symptom checkers and triage chatbots. The clinical-safety literature is unflattering, and the recurring finding is **under-triage of serious presentations** — the failure direction that matters. Babylon's commercial collapse is a separate lesson about business models, but it usefully punctures the assumption that deployment scale implies validation.

Evaluation note: triage is shape 3 with an ordered outcome, so it owes you a full confusion matrix by acuity level, not an accuracy figure. Under-triage and over-triage have entirely different costs and must be reported separately.

## Section 5 · Language for surveillance

Where this shape meets your actual work.

- **Event-based surveillance.** EIOS, ProMED, HealthMap: text as a signal source. Lesson 2 covers the detection side; the extraction side belongs here. LLMs turning free-text reports into structured event records (location, pathogen, count, confidence) is the current frontier, and it moves the bottleneck from *finding* candidate signals to *verifying* them — which is where the bottleneck already was.
- **Verbal autopsy.** ✱ A lovely and under-appreciated case: probabilistic interpretation of narrative interviews (InterVA, InSilicoVA) produces cause-of-death statistics for populations with no death certification. Language into data, feeding national statistics, for decades, largely without fanfare.
- **Literature screening.** Prioritising abstracts for systematic review. Well studied, measured on recall at a workload reduction — the correct framing, since missing a paper is the asymmetric error.
- **Translation and health communication.** High value, real safety risk. Numbers, doses and negations are exactly where machine translation fails, and exactly where failure hurts.
- **Coding.** ICD assignment from text; the boring backbone of health statistics.

## Section 6 · Evaluating a language system

The framing that makes this tractable: **for extraction, it is a diagnostic test.** Treat each field as a test for a condition and everything from Lesson 9 transfers unchanged — sensitivity, specificity, PPV at the prevalence of that field, and subgroup performance.

For generation, the additional measures:

| Measure | Question |
|---|---|
| **Groundedness / faithfulness** | Is every claim supported by the retrieved source? |
| **Retrieval recall@k** | Was the right passage even retrieved? Score separately |
| **Omission rate** | What did it leave out? ⚠ Far harder to notice than what it added, and usually unreported |
| **Consistency** | Same input twice, same output? Non-determinism is a validation problem |
| **Calibration of stated confidence** | When it says "likely", is it? Usually not |
| **Human review burden** | If every output must be checked, what was saved? |

⚠ Two things to distrust on sight. **Automated text-similarity scores** (ROUGE, BLEU and relatives) measure overlap with a reference, not correctness — a clinically dangerous omission barely moves them. And **LLM-as-judge** evaluation, where a model grades model output: convenient, increasingly standard, and it inherits the grader's blind spots. It is evidence, but it is not measurement.

---

## Key insight

**In every other shape, the hard part is the model. In this shape, the hard part is the label.** Negation, hedging, temporality and experiencer are case-definition problems, not engineering problems — which means the epidemiologist's contribution is not to check the model but to write down what "correct" means before anyone builds anything.

And the corollary: a language system's fluency is uncorrelated with its correctness, while being the only quality signal most reviewers actually perceive.

---

## Worked example — negation is a case definition

Dataset: twelve clinical-style sentences, hand-labelled, constructed to contain the six failure modes from Section 1. Small and self-contained on purpose — the point is the labelling logic, not the scale.

The exercise: build the "obvious" keyword extractor, score it as a diagnostic test, then watch each failure mode cost you.

### In R

```r
library(tidyverse)

# ---- A tiny gold standard --------------------------------------------------
# `tb_case` is what a human abstractor decided, applying an explicit case
# definition: a CURRENT, AFFIRMED TB diagnosis IN THIS PATIENT.
# Writing that sentence down is the actual work of this lesson.
notes <- tribble(
  ~text,                                                        ~tb_case, ~trap,
  "Sputum positive for acid-fast bacilli. Starting RHZE.",            TRUE,  "plain positive",
  "No evidence of tuberculosis on chest radiograph.",                 FALSE, "negation",
  "Cannot exclude pulmonary tuberculosis; await GeneXpert.",          FALSE, "hedging",
  "History of tuberculosis, completed treatment 2019.",               FALSE, "temporality",
  "Family history of TB in the household.",                           FALSE, "experiencer",
  "TB treatment ongoing, month 3 of 6.",                              TRUE,  "plain positive",
  "Screened for TB, result pending.",                                 FALSE, "hedging",
  "Patient denies TB contact. Cough 3 weeks.",                        FALSE, "negation",
  "GeneXpert MTB detected, rifampicin resistance not detected.",       TRUE,  "abbreviation",
  "Ruled out TB; treating community-acquired pneumonia.",             FALSE, "negation",
  "Tuberculose pulmonaire confirmee, sous traitement.",                TRUE,  "multilingual",
  "No improvement on TB therapy after 8 weeks.",                       TRUE,  "negation decoy"
)

# ---- The extractor everyone builds first -----------------------------------
# Any mention of TB counts as a case. This is the strawman that LLM papers
# are often compared against -- and note it is not stupid, it is just
# missing the case definition.
notes <- notes |>
  mutate(keyword = str_detect(text, regex("tubercul|\\bTB\\b|\\bMTB\\b", ignore_case = TRUE)))

# ---- Score it exactly like a diagnostic test -------------------------------
# This function is deliberately identical in spirit to Lesson 9's `operating()`.
# A text extractor IS a diagnostic test; nothing new is needed to judge it.
score <- function(pred, truth, label) {
  tp <- sum(pred & truth); fp <- sum(pred & !truth)
  fn <- sum(!pred & truth); tn <- sum(!pred & !truth)
  tibble(extractor = label, tp, fp, fn, tn,
         sensitivity = tp / (tp + fn),
         specificity = tn / (tn + fp),
         ppv         = tp / max(tp + fp, 1))
}

score(notes$keyword, notes$tb_case, "keyword")
# Sensitivity is perfect and PPV is poor: it finds every case and also
# everything that merely mentions the word. Familiar shape -- this is a
# sensitive screening test with no confirmation step.

# ---- Add negation handling: the NegEx idea in four lines -------------------
# Look for a negation trigger BEFORE the mention, within a short scope window.
# Crude, transparent, and it recovers most of the specificity.
neg_triggers <- "no evidence of|ruled out|denies|cannot exclude|negative for|without"
notes <- notes |>
  mutate(negated = str_detect(str_to_lower(text), neg_triggers),
         rule    = keyword & !negated)

score(notes$rule, notes$tb_case, "keyword + negation")

# ---- Where it still fails, and why that is not the algorithm's fault ------
notes |>
  filter(rule != tb_case) |>
  select(trap, text, gold = tb_case, predicted = rule)
# Expect the temporality, experiencer and "negation decoy" rows to survive.
# "No improvement on TB therapy" contains a negation trigger but the patient
# HAS tuberculosis -- the trigger negates the improvement, not the diagnosis.
# No amount of trigger-list tuning fixes that; it needs scope, and scope needs
# the case definition to say what is being negated.

# ---- The comparison an LLM paper owes you ---------------------------------
# Whatever you would put here -- an LLM prompted with the case definition,
# a fine-tuned classifier, a commercial pipeline -- it must be scored with
# the SAME `score()` call on the SAME gold standard, and reported against
# `keyword + negation`, not against `keyword`.
# Comparing to the strawman is how this shape's literature flatters itself.
```

⚠ Not executed here (no Rscript in WSL). The `score()` arithmetic is elementary and the regexes are simple, but verify the `negation decoy` row behaves as described before using this in teaching — it is the row that carries the lesson.

---

## Exercises

**Recall.** Name the six failure modes of clinical text extraction, and say which four are really case-definition problems.

**Application.** Write the case definition you would hand to an annotator for "confirmed gambiense HAT case" from free-text clinic notes. Then list the sentences you expect to be ambiguous under your own definition. If there are none, the definition is too vague.

**Application.** Take a RAG system you have used — Metis included. Design an evaluation that scores retrieval and generation separately, and say what recall@k you would require before you would trust an answer you could not check.

**Conceptual.** The AMIE study restricted physicians to text chat. Argue that this makes the comparison *fair* rather than unfair. Then say what additional study would settle it.

**Challenge.** Ambient scribes are evaluated on clinician burnout, which they improve. Design a study that would detect a scribe that reduces burnout while degrading the accuracy of the record. Explain why nobody has strong incentives to run it.

---

## Connection to the course spine

Shape 5's debt, from Lesson 9, is **a definition of correct** — and this lesson is why that debt is the one it owes. In every other shape "correct" is given: the patient had sepsis or did not, the outbreak happened or did not. Here the label is constructed, contested, and often not written down at all.

The second half of the spine holds with unusual force. The methods in this shape changed almost completely between 2023 and 2026, and every evaluation failure listed here — strawman comparators, unscored retrieval, unmeasured omissions, similarity metrics standing in for correctness — long predates LLMs and will outlive them.

---

## Sources

⚠ Written from model knowledge to mid-2026, not verified against the literature. Leads to confirm, not citations to reuse.

**Books**

- Jurafsky & Martin, *Speech and Language Processing* (open draft) — chapters on information extraction and on evaluation.

**Online**

- The n2c2 / i2b2 shared-task descriptions — the benchmark lineage for clinical extraction.
- MedCAT and cTAKES documentation — what an auditable production pipeline looks like.
- WHO EIOS — event-based surveillance in practice.

**Key papers**

- Chapman et al., *A simple algorithm for identifying negated findings and diseases in discharge summaries* (NegEx) — Journal of Biomedical Informatics, 2001.
- Tu, Palepu, McDuff, Schaekermann et al., *Towards conversational diagnostic AI* (AMIE) — Nature, 2025. ⚠ Author list and year worth checking.
- Singhal et al., *Large language models encode clinical knowledge* (Med-PaLM) — Nature, 2023.
- Byambasuren et al. and the verbal-autopsy methods literature (InterVA, InSilicoVA) — **[?]** I am unsure of the best single citation here; ask the librarian.

---

## Retain long-term

- The generic task is: unstructured text in, fields out. The comparator is a human abstractor — who is also imperfect.
- Six failure modes: negation, hedging, temporality, experiencer, abbreviation collision, multilingual text.
- Four of the six are case-definition problems, not NLP problems.
- Rule-based extractors are auditable and stable; generative ones are neither. For statutory pipelines that can outweigh accuracy.
- RAG must be scored twice: retrieval recall@k, then groundedness of generation.
- Ambient scribes are the most-deployed clinical AI; the evidence is on burnout, not on note accuracy.
- AMIE beat physicians who were also restricted to text chat. Read the comparator, not the abstract.
- Triage chatbots' characteristic failure is under-triage — report by acuity, never as accuracy.
- Text-similarity scores measure overlap, not correctness. LLM-as-judge is evidence, not measurement.
- A wrong number looks wrong; a wrong sentence looks like prose.
