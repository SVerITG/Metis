# Deep dive — The consultation: AMIE and the ambient scribe

**Shape 5** (turn language into data), with **shape 6** (choose an action) underneath AMIE ·
Maturities **🔬 research, no deployment** vs **🚀 deployed at enormous scale** · Stresses
**deployment & governance**

> ⚠ Written from model knowledge to mid-2026. Figures and author lists are leads to verify.
> The structural argument is the durable content.

The imaging pair asked why one system reached practice and the other did not. This pair asks
something stranger, because it comes out **backwards**:

- **AMIE** has arguably the strongest experimental evidence of any clinical AI — a
  randomised, blinded trial in which it matched or beat physicians — and it is deployed
  **nowhere**.
- **Ambient documentation** has thin evidence on the thing that actually matters, and it is
  in **hundreds of thousands of consulting rooms right now**.

One proved without shipping. The other shipped without proving. Understanding why is a
lesson about regulation and naming, not about models.

---

## 1 · The questions someone actually asked

**Ambient documentation.** Clinicians spend an enormous share of the working day typing.
Documentation load is one of the best-evidenced drivers of burnout and attrition, and
after-hours EHR work — "pajama time" — is a measurable, hated thing. The question:
*can we take the typing away without taking the clinician away?*

**AMIE.** Diagnosis begins with a conversation: taking a history is a skilled, iterative,
information-gathering task. Most of the world has no access to a clinician skilled at it.
The question: *can a language model conduct a diagnostic conversation as well as a primary
care physician?*

✱ Notice these delegate opposite halves of the consultation. Ambient documentation removes
the **clerical** work and leaves the reasoning entirely with the human. AMIE takes over the
**reasoning** and leaves the human as the patient. They are not competing products; they are
opposite answers to "what should a machine do in a consulting room".

<svg viewBox="0 0 640 190" width="100%" style="max-width:640px" role="img" aria-label="Diagram of the consultation split into listening, reasoning, deciding and recording, showing ambient documentation taking only the recording step while AMIE takes listening, reasoning and part of deciding"><text x="8" y="16" font-size="11" font-weight="600" fill="currentColor">The consultation, as four tasks</text><rect x="8" y="26" width="146" height="34" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="81" y="47" font-size="10.5" text-anchor="middle" fill="currentColor">gather the history</text><rect x="162" y="26" width="146" height="34" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="235" y="47" font-size="10.5" text-anchor="middle" fill="currentColor">reason to a diagnosis</text><rect x="316" y="26" width="146" height="34" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="389" y="47" font-size="10.5" text-anchor="middle" fill="currentColor">decide and explain</text><rect x="470" y="26" width="162" height="34" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="551" y="47" font-size="10.5" text-anchor="middle" fill="currentColor">record what happened</text><rect x="466" y="80" width="170" height="26" rx="3" fill="currentColor" opacity="0.13"/><rect x="466" y="80" width="170" height="26" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"/><text x="551" y="97" font-size="10" text-anchor="middle" fill="currentColor">AMBIENT SCRIBE</text><text x="8" y="97" font-size="10" fill="currentColor" opacity="0.8">clinician keeps everything else →</text><rect x="4" y="122" width="404" height="26" rx="3" fill="currentColor" opacity="0.13"/><rect x="4" y="122" width="404" height="26" rx="3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-dasharray="5 3"/><text x="206" y="139" font-size="10" text-anchor="middle" fill="currentColor">AMIE (research only)</text><text x="418" y="139" font-size="10" fill="currentColor" opacity="0.8">← clinician becomes reviewer, or absent</text><text x="8" y="170" font-size="9.5" fill="currentColor" opacity="0.85">One removes the clerical work and leaves the judgement. The other takes the judgement.</text><text x="8" y="183" font-size="9.5" fill="currentColor" opacity="0.85">The deployed one is the modest one — and that is not a coincidence.</text></svg>

## 2 · Why each looked tractable

Both became possible for the same reason, and it is worth being blunt: **large language
models got good at fluent, structured English.** Neither required a medical breakthrough.

- **Ambient documentation** needed three things that all matured at once: speech recognition
  robust to a real consulting room, **speaker diarisation** (who said which words), and
  summarisation into a clinical note format. The last is the LLM contribution; the first two
  are older engineering.
- **AMIE** needed something less obvious: a way to *practise*. Diagnostic conversation is
  interactive, so you cannot learn it from a static corpus of notes. The insight was to
  generate the interaction.

## 3 · The data

**Ambient documentation** trains on and operates over **real consultations** — audio plus
the resulting clinician-signed notes. This is the most privacy-sensitive data in medicine,
recorded continuously, in a room where the patient's consent is often a poster on the wall.

⚠ What it does not represent: quiet rooms, one accent, one language, no interruptions, no
family member talking over the patient. Real consultations in your settings are
multilingual, code-switched and noisy — precisely the conditions ASR degrades in, and
precisely the populations least represented in training audio.

**AMIE** trained partly on real medical corpora but critically on **self-generated
dialogue**: simulated consultations between a simulated patient and the model, critiqued and
iterated. Evaluation then used **149 scenario packs** (75 India, 60 Canada, 14 UK)
performed by **20 validated patient actors**, in **text chat**, in a **randomised double-blind
crossover** design against **20 board-certified primary care physicians**.

⚠ What that does not represent: real patients, spoken conversation, physical examination,
continuity of care, or any language other than English. The authors say so.

## 4 · The methods, explained

### Ambient documentation
A pipeline, and each stage can fail differently:

1. **Capture** — ambient microphone, whole encounter.
2. **Transcribe** — ASR to text, with diarisation to separate clinician from patient.
3. **Summarise** — an LLM converts the transcript into a structured note, typically in a
   clinical format such as SOAP, discarding the vast majority of the words.
4. **Review and sign** — the clinician reads and attests.

✱ Step 3 is where the interesting risk lives, and it is not fabrication. It is **omission**.
The system's job is to throw away 95% of what was said. A note that omits the one sentence
that mattered looks completely normal — there is nothing to notice. Fabrication is
detectable; omission is invisible. And step 4 is the control that is supposed to catch it,
performed by someone who adopted the product specifically to stop reading and typing.

### AMIE
The methodological novelty is **self-play**, and it is worth understanding because it will
recur:

1. A model plays the **doctor**; another instance plays a **patient** with a defined
   condition and personality.
2. They hold a consultation. The doctor asks questions, forms a differential, explains.
3. A **critic** model evaluates the exchange against criteria — was the history
   complete, was the differential appropriate, was the communication good?
4. The critique feeds back, the scenario set is expanded across conditions and specialties,
   and the loop runs at a scale no human curriculum could match.

⚠ The obvious hazard: the model is being graded by a model, on scenarios generated by a
model. Self-play can amplify a shared blind spot rather than correct it. This is why the
*external* evaluation against real physicians carries all the weight — and why AMIE's
authors ran one, which is to their considerable credit.

## 5 · What each found

**Ambient documentation.** Consistent, modest, well-replicated improvements in
clinician-reported outcomes: less documentation time, less after-hours EHR work, lower
burnout and higher satisfaction scores. ⚠ With an important dissonance in the literature —
several studies found **improved *perceived* burden with little or no change in objectively
measured EHR time.** That gap is a finding in itself, not a measurement failure: feeling less
besieged is a real outcome, and it is not the same as being faster.

**AMIE.** In the randomised, double-blind, crossover OSCE-style study, AMIE performed **at least
as well as the primary care physicians on the large majority of rated axes** — **28 of 32 axes**
rated by specialist physicians and **24 of 26 axes** rated by the patient actors — including on
**diagnostic accuracy** and on several dimensions of **empathy and communication**.
✓ Figures verified 2026-08-21 against Nature 2025;642(8067):442–450.

The empathy result is the one that surprises people, and it should not. Unlimited patience,
no time pressure, no prior patient, no hunger, and no memory of the last difficult
consultation are structural advantages in a rated conversation.

## 6 · How each was evaluated

| Question | Ambient documentation | AMIE |
|---|---|---|
| **Shape** | 5 — text in, structured note out | 5 with 6 underneath: it also reasons to a decision |
| **Comparator** | The clinician typing — a genuine, fair comparator | 20 PCPs, **also confined to text chat** |
| **Primary endpoint** | Clinician burden and burnout | Diagnostic accuracy + rated conversation quality |
| **The endpoint that matters** | **Note accuracy — rarely measured against an independent standard** | Real-world patient outcomes — **not measured at all** |
| **Design strength** | Mostly pre/post, single-system, unblinded | **Randomised, blinded, prospective.** Unusually strong |
| **Shape 5's debt — a written definition of *correct*?** | **Largely unpaid.** What is a correct note? | Paid, for the diagnostic component: a defined reference diagnosis |

✱ Look at row four in both columns. Each product's weakest evidence is on the outcome that
would decide whether it should exist. And the two weaknesses are opposite: the scribe has
strong evidence on a *proxy* and weak evidence on *correctness*; AMIE has strong evidence on
*correctness* and none on *doing any good to anyone*.

## 7 · What happened next

**Ambient documentation** went to scale, fast — DAX Copilot, Abridge, Nabla, Suki and others,
adopted across large health systems and now standard-issue in some. By volume it is the most
widely used clinical AI in the world.

**AMIE** produced further research — multimodal versions, management-reasoning versions — and
**no deployment, no regulatory clearance, no patient contact.**

The reason for the gap is regulatory, and it turns on a word:

<svg viewBox="0 0 640 250" width="100%" style="max-width:640px" role="img" aria-label="Diagram showing how calling a product documentation avoids medical-device regulation while calling it diagnosis triggers a high evidence bar, with the consequence that the less-regulated product is the widely deployed one"><text x="8" y="16" font-size="11" font-weight="600" fill="currentColor">The same technology, two names, opposite regulatory fates</text><rect x="8" y="30" width="180" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"/><text x="98" y="47" font-size="10.5" text-anchor="middle" fill="currentColor">called DOCUMENTATION</text><text x="98" y="61" font-size="9" text-anchor="middle" fill="currentColor" opacity="0.75">"it just writes the note"</text><path d="M188 50 L226 50" stroke="currentColor" stroke-width="1.2"/><path d="M220 46 l6 4 -6 4" fill="currentColor"/><rect x="227" y="30" width="176" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3"/><text x="315" y="47" font-size="10.5" text-anchor="middle" fill="currentColor">not a medical device</text><text x="315" y="61" font-size="9" text-anchor="middle" fill="currentColor" opacity="0.75">no clinical validation required</text><path d="M403 50 L441 50" stroke="currentColor" stroke-width="1.2"/><path d="M435 46 l6 4 -6 4" fill="currentColor"/><rect x="442" y="30" width="190" height="40" rx="3" fill="currentColor" opacity="0.13"/><rect x="442" y="30" width="190" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"/><text x="537" y="47" font-size="10.5" text-anchor="middle" fill="currentColor">in every consulting room</text><text x="537" y="61" font-size="9" text-anchor="middle" fill="currentColor" opacity="0.75">deployed at enormous scale</text><rect x="8" y="104" width="180" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"/><text x="98" y="121" font-size="10.5" text-anchor="middle" fill="currentColor">called DIAGNOSIS</text><text x="98" y="135" font-size="9" text-anchor="middle" fill="currentColor" opacity="0.75">"it works out what's wrong"</text><path d="M188 124 L226 124" stroke="currentColor" stroke-width="1.2"/><path d="M220 120 l6 4 -6 4" fill="currentColor"/><rect x="227" y="104" width="176" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.2"/><text x="315" y="121" font-size="10.5" text-anchor="middle" fill="currentColor">high-risk device</text><text x="315" y="135" font-size="9" text-anchor="middle" fill="currentColor" opacity="0.75">EU AI Act + MDR, or FDA SaMD</text><path d="M403 124 L441 124" stroke="currentColor" stroke-width="1.2"/><path d="M435 120 l6 4 -6 4" fill="currentColor"/><rect x="442" y="104" width="190" height="40" rx="3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-dasharray="5 3"/><text x="537" y="121" font-size="10.5" text-anchor="middle" fill="currentColor">deployed nowhere</text><text x="537" y="135" font-size="9" text-anchor="middle" fill="currentColor" opacity="0.75">despite a randomised trial</text><line x1="8" y1="168" x2="632" y2="168" stroke="currentColor" stroke-width="0.8" opacity="0.35"/><text x="8" y="190" font-size="10" font-weight="600" fill="currentColor">The consequence</text><text x="8" y="208" font-size="9.5" fill="currentColor" opacity="0.85">The product carrying LESS oversight is the one actually touching patients — because its risk was</text><text x="8" y="222" font-size="9.5" fill="currentColor" opacity="0.85">classified by what it is called, not by what it can break. A corrupted note propagates into the next</text><text x="8" y="236" font-size="9.5" fill="currentColor" opacity="0.85">clinical decision, the billing code, the audit trail and the research dataset.</text></svg>

**A note is "documentation".** It is not a diagnosis, so a scribe is generally not regulated
as a medical device, and no clinical validation is required before selling it. **A
differential diagnosis is a diagnosis.** Under the EU AI Act and MDR — or FDA's
software-as-a-medical-device route — an AMIE-like system is high-risk: risk management, data
governance, human oversight, post-market surveillance. ⚠ Verify the current EU AI Act
timeline before relying on dates.

✱ So the evidence bar was set by the product's **name**, not by what it can break. And the
result is inverted: the system with weaker safety oversight is the one in the room with
patients.

## 8 · What each is actually worth

**Ambient documentation: genuinely valuable, with an unmeasured liability.**

In the units of the decision: **clinician-hours returned**. At a plausible saving of one to
two minutes per encounter across twenty encounters a day, that is 20–40 minutes daily per
clinician — and the after-hours reduction matters more than the raw minutes, because that is
where attrition is generated. In a system short of clinicians, giving each one back an hour
a day is a workforce intervention, not a gadget. That is a real and defensible benefit.

The liability is **silent record degradation**. Every note feeds four downstream things: the
next clinician's decision, the billing code, the medico-legal record, and the research
dataset. An omission rate of even a few percent, distributed non-randomly — worse for
accented speech, for interpreted consultations, for interrupted encounters — degrades all
four in a way no one is currently measuring. ✱ And note the specific epidemiological harm:
**if scribes are used unevenly across populations, they introduce differential
misclassification into every dataset built from those records.** That is a bias in your
denominator, arriving through the back door.

**The condition under which the value flips:** if clinicians stop genuinely reviewing. The
whole safety case rests on step 4, performed by someone whose reason for buying the product
was to stop doing step 4.

**AMIE: the potential is access, and the evidence does not yet speak to it.**

The honest reading of the trial: *in synchronous text consultation with simulated patients,
a language model performed at least as well as primary-care physicians who were also confined
to text.* That is a real result about a real and growing setting — telehealth is text and
video, and the world has a great deal of it.

But the transformative potential is elsewhere: **populations with no physician at all.** A
system that takes a history and produces a sensible differential could be genuinely
consequential where the counterfactual is nobody. Which is precisely where the evidence is
weakest — the trial was English, text, actors, in a high-income framing, against PCPs. It
tells you almost nothing about a rural clinic where the user is a nurse, the language is
Lingala, and the differential includes diseases barely represented in the training data.

**What would change my assessment:** an evaluation with real patients, in the target setting,
with a health-worker-in-the-loop design and patient outcomes as the endpoint. Until then
AMIE is a strong proof of capability and not evidence of benefit — and the distinction is the
whole of this course.

⚠ And the failure mode to watch is not stupidity, it is **fluent confidence**. A wrong number
looks wrong; a wrong differential, well explained, looks like good medicine.

## 9 · Transferable lessons

1. **The regulatory class is set by the claim, not the risk.** Call it documentation and the
   evidence bar vanishes. Anyone building health AI should notice how much is decided by
   naming, and anyone appraising it should ask what the thing can break rather than what it
   is called.
2. **Strong evidence on a proxy is not evidence on the outcome.** Burnout is a legitimate
   endpoint. It is not note accuracy, and it cannot substitute for it.
3. **Perceived and measured burden can move apart** — and both are real. Do not dismiss the
   subjective finding, and do not let it stand in for the objective one.
4. **Omission is the invisible error.** In any summarisation task, ask what was left out.
   That number is almost never reported, because it is expensive to measure and unflattering.
5. **A human-in-the-loop control fails when the loop is what you sold.** If review is the
   safety mechanism, and the product's value proposition is not having to review, the control
   is decorative.
6. **Constraining the comparator can make a comparison fairer *and* narrower.** AMIE's
   text-only design was methodologically defensible and it bounds the conclusion tightly.
   Both things are true; say both.
7. **Self-play scales practice and can amplify shared blind spots.** Any system graded by a
   model on scenarios written by a model needs an external, human evaluation to mean anything.
8. **Differential misclassification is the epidemiologist's stake in all of this.** If an AI
   touches records unevenly across populations, every study built on those records inherits
   the unevenness.

## 10 · Explain it in 60 seconds

> There are two very different AIs in the consulting room, and the story about them comes out
> backwards from what you'd expect.
>
> The first just **listens and writes the note**. It doesn't diagnose anything — the doctor
> still does all the thinking. It's now in hundreds of thousands of consulting rooms, and the
> evidence is decent that it reduces burnout and after-hours paperwork. What almost nobody has
> measured is whether the notes are *right* — and the specific risk isn't that it makes things
> up, it's that it leaves things out, which is invisible, because a note missing the one
> sentence that mattered looks completely normal.
>
> The second, Google's AMIE, actually **takes the history and works out the diagnosis**. In a
> randomised blinded trial it matched or beat primary care doctors — on accuracy *and* on
> empathy, which sounds shocking until you remember it's never tired and never rushed. It is
> deployed absolutely nowhere.
>
> And here's the punchline. The difference isn't the technology, it's what you *call* it.
> Writing a note is "documentation", so it isn't a medical device and needs no clinical
> validation. Producing a diagnosis is "diagnosis", so it's a high-risk device with an
> enormous evidence bar. **So the one with less oversight is the one actually in the room with
> patients** — because the risk was classified by the product's name, not by what it can break.

## 11 · Read more

**Diagnostic dialogue**
- **Tu T, Schaekermann M, Palepu A, et al.** *Towards conversational diagnostic artificial
  intelligence.* **Nature** 2025;642(8067):442–450. doi:10.1038/s41586-025-08866-7
  (arXiv preprint 2401.05654, 2024). **The paper.** ✓ Verified 2026-08-21. Read the methods and
  the limitations, not the abstract — the limitations are unusually honest and are where the
  learning is.
- **Singhal K et al.** *Large language models encode clinical knowledge* (Med-PaLM),
  **Nature** 2023, and the Med-PaLM 2 follow-up. The benchmark lineage AMIE grew out of, and
  a good illustration of why exam performance is not clinical performance.
- Follow-on AMIE work on **multimodal inputs** and on **management reasoning** (rather than
  diagnosis alone), 2025. ⚠ I am not confident of the exact titles; worth a librarian pass.

**Ambient documentation**
- Look for **pre/post evaluations from large health systems** (Kaiser Permanente, Stanford,
  Mass General Brigham and others) on DAX Copilot and Abridge, reporting documentation time,
  after-hours EHR time and burnout scores. ⚠ This literature moves fast and is heavily
  vendor-adjacent — read the funding statements. Several report improved *perceived* burden
  with little change in *measured* EHR time; those are the most informative papers.
- **Sinsky C, Shanafelt T** and colleagues on documentation burden, EHR time and burnout —
  the pre-AI baseline literature. Essential for judging whether an effect size matters.
- Work on **note quality and error taxonomies** for AI-generated clinical documentation
  (omission vs fabrication vs mis-attribution). Thin, and the gap is the point.

**The governance frame — the part that explains the whole story**
- **EU AI Act** (Regulation 2024/1689) and **EU MDR** — how a clinical-decision-support
  claim triggers the high-risk tier. ⚠ Obligations phase in through 2026–27; check current
  dates.
- **FDA** guidance on **clinical decision support software** and on **predetermined change
  control plans** for adaptive AI. The US framing of the same naming problem.
- **WHO.** *Ethics and governance of artificial intelligence for health* (2021) and the
  later guidance on **large multi-modal models** for health. The global-health framing, free.
- **DECIDE-AI** — the reporting guideline for early live clinical evaluation. Exactly the
  missing evidence stage in both stories here.

**Wider reading**
- **Wachter R.** *The Digital Doctor* (2015). Pre-LLM, and still the best account of how
  clinical software reshapes clinical work in ways nobody intended. Read it and the ambient
  scribe story becomes predictable.
- **Topol E.** *Deep Medicine* (2019) — chapters on the clinician-patient relationship. The
  optimistic case for exactly this technology.
- **Nundy S, Cooper LA, Mate KS.** *The quintuple aim* — where "clinician wellbeing" became
  a legitimate health-system endpoint, which is what makes the burnout evidence count.

⚠ Every reference here is from memory. The Nature AMIE paper, Med-PaLM, the EU AI Act, WHO
guidance and Wachter's book I am confident exist as described; the ambient-documentation
evaluations I have deliberately described by *type* rather than inventing citations, because
that literature is recent and I would get the specifics wrong.
