# AI in Public Health & Epidemics

**A living course. Core track COMPLETE 2026-08-21.** Status: active · Slug: `ai-in-public-health` · Opens at `/course/ai-in-public-health`
Started 2026-08-20. Replaces the earlier NTD-specific draft (scope was widened deliberately).

Origin: NUST BMES-826 *Applied AI in Epidemiology*, assessed and declined —
`outputs/reviews/learning-coach/2026-08-20_nust-applied-ai-in-epidemiology.md`.
This course covers everything that syllabus would have taught, minus the filler, plus
the four areas it barely touches: tabular pattern recognition, medical imaging and video,
AI in the consultation, and evaluation done properly.

Built following procedural memory #9, *"Course making — set the curriculum spine before
writing anything"*, and verified against #13, *"verify a course is actually shipped, not
just written"*.

---

## Coverage

Every lesson carries both a quiz and spaced-repetition cards. That was not true until
2026-08-29: `lesson-00`, `lesson-20` and `lesson-21` had empty quiz arrays, and the two
deep dives had no cards, so a learner reaching any of the three got no self-check and the
deep dives contributed nothing to the review queue. All 116 cards are seeded into
`spaced_repetition` — check with:

```sql
SELECT COUNT(*) FROM spaced_repetition WHERE source_table='ai-in-public-health';
```

**Still open: exercises.** This course has none. The graduated A–E ladder specified by
procedural memory #11 is implemented and rendered for `genomic-surveillance` (110
exercises); the lesson reader supports it for every course, so the slot here is wired and
empty. Roughly 80 exercises would fill it.

## Sources — graded, not blanket-warned

`sources/source-ledger.md` grades every citation in the course rather than pricing them all at
the level of the weakest one:

| Grade | Count | Meaning |
|---|---|---|
| **CROSSREF-VERIFIED** | 10 | DOI resolves *and* matches the claimed first author and year |
| **MARKED-VERIFIED** | 16 | Carried an inline `✓ Verified` marker from the authoring session |
| **FLAGGED** | 3 | The author flagged uncertainty inline — a lead, not a citation |
| **SEARCH** | 80 | Named reference, unconfirmed at the level of the specific number attributed to it |

Re-check the DOIs at any time with `python3 ../../../tools/check_course_dois.py ai-in-public-health`.
Checked 2026-08-28: **0 unresolvable, 0 misattributed.**

**What is still not checked** is whether each paper *says* what the lesson says it says. A DOI
matching its author and year proves the citation points at the right paper, not that the finding
attributed to it is the finding it reports.

---

## What this course is for — and how it differs from the statistics course

**The statistics course is drill.** Concepts that must become automatic, learned by heart,
executed. **This course is for understanding.** the researcher wants to discover and understand the
science *and* the application — from research question to conclusion — and to judge what each
AI application could actually be worth. Execution matters least: code appears only where
running it is the fastest route to understanding, never as an exercise for its own sake.

**A second objective, which shapes everything:** afterwards the researcher must be able to *explain*
to other people how AI is used in public health, epidemic and pandemic preparedness, data
science, consultation and health. That is a harder target than understanding, and it changes
three things:

1. **The deep dive, not the core-track lesson, is the heart of the course.** The core track
   teaches the vocabulary needed to read a deep dive; the deep dives are what there is to
   learn. Contract: `DEEP-DIVE-TEMPLATE.md`.
2. **Every deep dive ends with “Explain it in 60 seconds”** — a rehearsed narrative, written
   to be said out loud, not a summary.
3. **Visuals are load-bearing.** Diagrams carry arguments that prose carries badly. In-lesson
   diagrams are single-line inline SVG (the dashboard's `nl2br` extension injects `<br>` into
   multi-line raw HTML, which would corrupt them). Charts use computed geometry from real
   numbers, never eyeballed.
4. **Every deep dive ends with a reading list** — articles and books, with the two or three
   worth starting from marked.

**Companion artifact** — a shareable visual explainer to present from:
<https://claude.ai/code/artifact/9247a225-de03-4f8c-9914-27db205f5824>

## The spine

> **Every AI application in public health is one of six pattern-recognition problems
> wearing different clothes — and what decides whether it works is never the model, it is
> the evaluation.**

Two halves, deliberately. The first half makes the field finite and therefore learnable.
The second half is why the course does not go out of date: methods churn, evaluation
failures repeat.

**How the spine is proved, three times** (procedure step 2 — a spine asserted once is a
slogan):

1. **Lesson 1** — eight real claims, stripped of branding, classified into shapes in
   under ten seconds each. The Google Flu Trends item straddles two shapes, and that
   straddle *is* why it failed.
2. **Lesson 9 (Evaluation)** — one model, one dataset, two evaluations. AUC says deploy;
   calibration and PPV at real prevalence say don't. The Epic Sepsis Model is the
   real-world instance of exactly this.
3. **Every deep-dive page** ends with the same four questions. Forty repetitions of the
   spine is what makes it a reflex rather than a slogan.

## Why this design and not 16 weeks

The atlas comes *first*, not last. A conventional course teaches methods then shows
applications; this one shows the whole landscape on day one, because the actual skill
the researcher needs is not "implement an autoencoder" — it is **reading a claim a week for the
next decade and knowing instantly what kind of thing it is and whether to believe it.**

The core track then teaches only what is needed to read the atlas properly.

## Structure

| Section | Content | State |
|---|---|---|
| **Start here** | Lesson 0 — the Atlas: ~95 applications across six shapes, plus evaluation and governance layers, plus the cautionary canon | ✅ written |
| **Core track** | Lessons 1–10, one per shape plus two cross-cutting | **10 of 10 written** |
| **Deep dives** | The heart of the course: 11-section arc from research question to conclusion, plus a 60-second explanation and a reading list | **5 written**: Google Flu Trends · Two imaging stories · The consultation · Two database failures · Two that worked |
| **Cards** | Authored spaced-repetition cards in `qbank.json` | **106 seeded** |
| **Quizzes** | 4-option MCQs in the manifest, mlm-course schema | **97, audit-clean** |
| **Checkpoints** | Phase self-checks in `exams.json`, drawing from lesson quizzes | 3 |

Planned core track and the deep-dive queue are declared in `course.json`. `lessons.json`
lists **only what exists** — never stub a lesson into the manifest, or the reader shows a
course that cannot be read.

## The six shapes

1. **Detect the unusual** — anomaly detection, early warning · *ancestor:* CUSUM, Farrington
2. **Predict what happens next** — forecasting · *ancestor:* ARIMA, compartmental models
3. **Assign a label** — classification, from tables and from pixels · *ancestor:* logistic regression
4. **Find structure without labels** — clustering, embeddings · *ancestor:* latent class, scan statistics
5. **Turn language into data** — clinical NLP, LLMs · *ancestor:* manual chart abstraction
6. **Choose an action** — decision support, optimisation · *ancestor:* operations research

Plus two cross-cutting layers: **evaluation** and **deployment & governance**.

## Structure borrowed from the multilevel course

The multilevel statistics course is the working model, and it is a **two-layer**
architecture worth copying deliberately:

- **Content layer** — a Quarto site holding the prose (`mlm-app/public/course/`).
- **Learning layer** — an Express app (`mlm-app/server.js` + `lessons.json`) holding the
  pedagogy: 661 MCQs across 55 lessons, per-lesson `practical` tasks, `key_terms` feeding a
  glossary, `day`/`phase` pacing, an `optional` flag for the advanced strand, `emoji` for
  visual identity in a list, phase checkpoint exams, plus XP, streaks and a leaderboard for
  a cohort of colleagues on the local network. And `r-runner.js`, which executes real R in
  the browser.

What this course adopts now: the **manifest schema** (`topics`, `key_terms`, `emoji`, `day`,
`phase`, `time`, `optional`, `quiz`, `practical`), the **MCQ format** with distractors and an
explanation that says why the tempting wrong answer is wrong, and **phase checkpoints**. The
manifest is a superset, so these lessons are drop-in compatible with the mlm learning layer
if the gamified/cohort experience is ever wanted here.

What it does not adopt yet: XP/streaks/leaderboard (the dashboard already has spaced
repetition and a streak), and live R execution — see the open questions.

## Design rules

- **Peer register.** No explaining p-values, case definitions or study design.
- **Every method names the classical comparator it must beat.** No comparator, no claim.
- **Epidemiological metrics.** Sensitivity/specificity/PPV at real prevalence, calibration,
  proper scoring rules — never AUC alone.
- **Not disease-specific.** General public health and medicine. HAT/NTD examples are
  allowed as illustrations, never as the frame.
- **Honest maturity labels.** Research · piloted · at scale · regulator-cleared ·
  withdrawn. The withdrawn ones teach most.
- **Sources flagged, not faked.** Entries written from model knowledge are marked as
  needing verification. No invented citations, ever.

## The update loop — how this course stays current

The point of the course. Every AI-in-public-health item arriving via news, a paper, or a
colleague goes through **four questions**:

1. **Which of the six shapes is it?** If it doesn't fit, that's a finding — amend the taxonomy.
2. **What classical method must it beat?** No comparator, no claim.
3. **How was it evaluated?** Internal only? Calibration? Subgroups? External?
4. **Maturity, honestly?**

The answers route it:

- Thin answers → a new **row in the Atlas**.
- Rich answers, or a case that teaches something → a new **deep-dive page**.
- Contradicts something already in the atlas → an **update**, with the old claim kept
  visible and struck through. A living course that quietly rewrites history teaches nothing.

Cadence: fold in during the monthly `/metis-review`, or on demand whenever something
worth keeping comes through the news surface.

## Sources

- `sources/NUST_BMES-826_Applied-AI-in-Epidemiology_outline.pdf` — the brochure that
  started this (gitignored).
- `sources/NUST_BMES-826_outline.txt` — extracted text, tracked.

## Completion state, 2026-08-21

**16 lessons · 115 MCQs · 116 cards · 8 SVG diagrams · 5 deep dives.** Every lesson verified
openable; the course launches from the Learning surface and can be scheduled into the Work
calendar via the Schedule button on its card.

Route: Atlas → the six shapes (L1) → one lesson per shape (L2–L8) → evaluation (L9) → deployment
and governance (L10) → five deep dives, each following the eleven-section arc and ending in an
"Explain it in 60 seconds" narrative and a reading list.

**Quiz audit** (`tools/audit_quiz.py`): positions 25/24/24/24 · longest-is-correct 33.0% against
25% chance · median length ratio 1.08 · no wide spreads · no duplicate stems.
⚠ 33% was left deliberately. A mechanical rebalance drove it to 0.0% but made every padded option
a distractor — a *perfect* syntactic tell — and produced nonsense prose. Reverted, and procedural
memory #12 now forbids mechanical rebalancing: **a weak length tell beats a perfect one.**

## Open questions

- ✓ **Librarian pass done 2026-08-21** for the load-bearing references —
  `outputs/reviews/librarian/2026-08-21_citation-verification.md`. **18 verified, 9 corrected**,
  including two figures that were wrong (AMIE: **28 of 32** and **24 of 26** axes, not ~30 of 32)
  and the AMIE author order. The Epic Sepsis figures I had *derived* were confirmed by the paper
  to a decimal (specificity 83%, PPV 12%) and are now quoted rather than derived.
- ✓ **Second tranche done the same day: 10 more verified**, all confirmed — Qin et al. TB CAD,
  the WHO TB screening module (CAD for ages 15+), Beede CHI '20, Roberts Nat Mach Intell
  2021;3(3):199–217, Wynants BMJ 2020;369:m1328, Reich PNAS 2019;116(8):3146–3154, Bracher PLOS
  Comput Biol 2021;17(2):e1008618, Seymour JAMA 2019;321:2003–2017, Salmon J Stat Softw
  2016;70(10):1–35, Pokaprakarn NEJM Evidence 2022. **28 verified in total.**
- ⚠ **Still unverified** — textbook and framework material where the risk is page detail rather
  than existence: Vickers & Elkin, Gneiting & Raftery, TRIPOD+AI, PROBAST, Kulldorff, Farrington,
  Noufaily, NegEx, Zech, Komorowski, Grinsztajn, Cramer, the gap statistic, t-SNE, SHERLOCK 2017,
  Hamers-Casterman, and the EU AI Act article numbers.
  ✱ The pass found **two invented references in ~40 checked**, both in the diagnostics course, and
  none in the second tranche. Verify before a manuscript, not before a reading.
- 🟡 Do the labs run code? Lessons 2 and 9 both carry substantial R that has **not been
  executed** (no Rscript in WSL). `mlm-app/r-runner.js` already solves in-browser Windows
  Rscript execution and would turn these blocks from listings into labs. Not wired yet.
- ⚠ Lesson 9's `ppv_at` arithmetic is verified exact. Its simulation block and lesson 2's
  `surveillance` code are traced by hand only — object names in `surveillance` drift across
  versions and must be checked against the installed one.
- ⚠ Does this double as ITG teaching material? If so, the peer register has to be relaxed
  in lessons 1, 9 and 10.
