# Genomic Surveillance — From DNA to Decisions

A four-day short course, plus a fifth day of recent applications, for a senior
epidemiologist with no molecular biology or bioinformatics background.

**22 lessons · ~24 hours · 109 quiz questions · 110 exercises · 110 spaced-repetition cards · ~49,000 words**

---

## The spine

> A pathogen genome is a clock and a family tree at the same time. Every claim in genomic
> surveillance answers one of four questions — **is this the same outbreak, where did it come
> from, how fast is it spreading, has the pathogen changed**. And what decides whether the
> answer is trustworthy is almost never the sequencer; it is the **sampling and the metadata**.

The first half makes the field learnable. The second half is why the course does not go out of
date: the chemistry turned over twice while it was being written, and none of the failure modes
moved.

## The shape

The course is the chain, walked once.

```
 THE MOLECULE      THE MACHINE      THE DATA        THE TREE        THE DECISION
 L1–L2             L3–L4            L5–L6           L7–L12          L13–L15
 why a genome      sample →         reads →         alignment →     sampling · sharing
 carries epi       library →        consensus →     tree → time →   → what changes
 information       sequencer        a name          dynamics        on Monday
```

| | Section | Lessons |
|---|---|---|
| **Day 0** | Orientation | 0 — the atlas: the four questions, the chain, ~60 applications |
| **Day 1** | Molecule and machine | 1 two clocks · 2 mutation/signal/artefact · 3 sample to library · 4 the machines |
| **Day 2** | Data and trees | 5 reads to genome · 6 naming things · 7 what a tree is · 8 building the tree |
| **Day 3** | Time and dynamics | 9 time on the tree · 10 coalescent and growth · 11 where it came from · 12 clusters and transmission |
| **Day 4** | The system | 13 sampling and metadata · 14 sharing, governance, equity · 15 genome to decision |
| **Day 5** | Recent applications | 20 Bundibugyo DRC 2026 · 21 mpox clade Ib · 22 H5N1 in cattle · 23 resistance markers · 24 wastewater and agnostic · **25 *T. b. gambiense*** |

## The flagship

The brief was that the course should explain **everything appearing in** the virological.org
post on the [2026 Bundibugyo virus outbreak in Ituri, DRC](https://virological.org/t/phylodynamics-and-evolution-of-the-2026-bundibugyo-virus-circulating-in-the-democratic-republic-of-the-congo-insights-from-a-100-day-window-of-genomic-sequencing/1046)
(INRB Kinshasa with Edinburgh, Oxford, Birmingham, ITM Antwerp, WHO, Africa CDC, US CDC).

**Deep Dive 1 walks it phrase by phrase**, and every method phrase in it is decoded in a
numbered core lesson:

| Phrase in the post | Lesson |
|---|---|
| all PCR-positive samples with Ct < 31 | 3 |
| `amplicon-nf` v2 from ARTIC Network | 5 |
| MAFFT; trimmed to 18,900 bp | 5, 7 |
| 32 genomes excluded for ADAR editing signatures | 2 |
| IQ-TREE 3, ModelFinder, `GTR+F+R3` | 8 |
| small branches collapsed to zero | 7 |
| tree rooted to minimise residuals | 8 |
| iterative root-to-tip outlier removal, ±2 SD | 2, 9 |
| BEAST X v10.6.0-beta2, 100M steps, 10% burn-in | 9 |
| exponential growth; doubling time 21.0 days | 10 |
| SkyGrid, 31 one-week transition points, 32-week cutoff | 10 |
| tMRCA 22 February 2026 (95% HPDI) | 9 |
| Mongbwalu "could have been a starting point" | 11 |
| iterative cutoff approach across four datasets | 10 |
| Pathoplexus, restricted licence, named contacts | 14 |
| PearTree | 7 |

## The counter-example

Five of the six deep dives show genomic surveillance working. **Deep Dive 6 (*T. b. gambiense*)
is the one where it mostly does not**, and it is there deliberately — a course that only shows
successes teaches the tools but not the judgement.

Tbg1 is clonal and monophyletic, which rules out linkage (Q1) and phylodynamics (Q3) at any
sequencing depth. Parasitaemia is too low for whole-genome work, so the field went after a
high-copy target and turned sequencing into a field PCR. Human sampling outnumbers animal
sampling so heavily that the animal-reservoir question can only honestly return a bound. And
the reservoir is partly in the **skin**, which the standard blood specimen misses in exactly
the untreated group that matters.

Its conclusion is the one operational recommendation in the whole course: **archive before
elimination.** Once a focus reaches zero, import-versus-residual becomes the only question that
matters, and it is answerable only against a baseline that had to be collected beforehand.

## Exercises

Five rungs per lesson, following procedural memory #11 rather than inventing a format:

| Rung | Type | Why it is there |
|---|---|---|
| **A** | Conceptual, no tools | Answerable straight after reading, with nothing open |
| **B** | **Read the output** | Real tool output — a Tracer table, an IQ-TREE log, a Freyja demix, a SNP matrix — with three questions. **The most important rung**: in real work you meet somebody else's output long before you produce any of your own |
| **C** | Three of six | Six statements, exactly three correct, +1 / &minus;1 / 0 scoring. The negative marking forces careful reading instead of guessing |
| **D** | Scaffolded | Most of the work given; complete one specific thing and interpret it |
| **E** | Connect to your work | Open-ended, always last, on data you actually have |

Rung D is adapted from the recorded ladder's "guided R, scaffolded" — this course does not
teach execution, so D is a scaffolded *reading or arithmetic* task on the same material.

They are validated at build time. `_build_manifest.py` refuses to write a manifest where a C
rung has other than exactly three correct statements of six, where guidance concedes its own
exercise is broken, or where a literal escape survived into the text. All three were real
defects in the first build, and none was visible by reading the source.

## Files

```
course.json      course-level metadata: spine, phases, pedagogy, quiz audit, what is NOT covered
lessons.json     GENERATED — superset manifest (dashboard + learning layer). Never hand-edit.
qbank.json       103 authored spaced-repetition cards, one entry per lesson
lessons/         the 21 lesson markdown files (deep dives duplicated here as 20–24)
deep-dives/      the 5 deep dives, canonical copies
sources/         source-ledger.md — FETCHED vs SEARCH vs STANDING, read before citing anything
_build_manifest.py       regenerates lessons.json
_improve_distractors.py  pass 1 on quiz distractors (documented in course.json → quiz_audit)
_improve_distractors2.py pass 2
```

Prose formatting is handled by the repo-level tool, not by anything in this folder:

```bash
python3 ../../../tools/unwrap_course_prose.py --check --all   # survey every course
python3 ../../../tools/unwrap_course_prose.py genomic-surveillance
```

**To regenerate the manifest after editing lessons or quizzes:**

```bash
python3 _build_manifest.py
python3 ../../../tools/audit_quiz.py lessons.json      # must stay clean
```

**Write lesson prose unwrapped — one line per paragraph.** The reader renders with
`nl2br`, so a hard wrap in the source becomes a forced line break that the paragraph can
never recover from. `tools/unwrap_course_prose.py` fixes it after the fact and is safe to
re-run, but writing it unwrapped in the first place is cheaper. Lists need a blank line
above them or they are not lists.

The dashboard reader (`routers/learning.py::_lesson_path`) resolves lesson files by the
**numeric prefix of the filename**, not by the manifest's `file` field. Renaming a lesson file
so its prefix no longer matches its `lesson-NN` id breaks the reader silently — the `file` field
is documentation and a check, not the lookup.

## Two things to know before using it

**1. Citations are graded, not blanket-warned.** The AI in Public Health course shipped with
"every citation is an unverified lead". This one grades them in `sources/source-ledger.md`:
**FETCHED** sources were read in full while writing (the virological post, the Applied Genomic
Epidemiology Handbook contents, the COG-Train curriculum); **SEARCH** sources were seen as
search results and their specific claims are not individually verified; **STANDING** material is
field knowledge with no source consulted. Verify anything in the last two categories before it
enters a manuscript.

**2. What this course does not cover**, deliberately — see `course.json → not_covered`.
The largest gap is **communicating genomics to media and policymakers**, to which COG-Train
devotes an entire week. The second is hands-on command-line practicals; the Wellcome Connecting
Science repositories are open and are the right resource for that.

## Pedagogy

Understand, and be able to **explain**. Following the AI in Public Health course rather than the
statistics drill: the reader should finish able to read a phylodynamic paper end to end, say what
every method phrase is doing, name what it would cost to get each one wrong, and explain any of
the five applications to a room. Tool names appear so they are recognisable in a methods section,
not so the reader runs them today. Each deep dive carries an *Explain it in 60 seconds* section
and a reading list.
