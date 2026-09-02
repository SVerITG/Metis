#!/usr/bin/env python3
"""Add quiz questions and cards to the three lessons that had neither.

Audit 2026-08-29 found lesson-00 (the Atlas), lesson-20 and lesson-21 with empty
quiz arrays, and lesson-20/21 with no qbank entry either — so a learner reaching
any of those three got no self-check at all, and the two deep dives contributed
nothing to the spaced-repetition queue. The other 13 lessons were complete.

Option order for the NEW questions is shuffled with a fixed seed. The existing 97
are left untouched: they already audit clean at 25/24/24/24, and reshuffling them
would only risk making that worse.

Idempotent — it refuses to run twice.
"""
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).parent

NEW = {
"lesson-00": [
 ("The atlas claims there are six shapes rather than hundreds of kinds of health AI. What does 'shape' refer to?",
  ["The question being asked, which determines what evidence the claim owes you",
   "The algorithm family, which determines the computational requirements",
   "The data modality — tabular, image, text, or time series",
   "The clinical specialty in which the application is deployed"], 0,
  "A shape is a property of the question, not of the method or the data. That is why the same gradient-boosted tree is shape 1 when it scores how surprising today's count is and shape 2 when it predicts next month's — and why each shape owes a different kind of evidence."),
 ("Match the shape to its classical ancestor: which pairing is correct?",
  ["Find structure without labels — ARIMA and compartmental models",
   "Turn language into data — manual chart abstraction and coding",
   "Detect the unusual — logistic regression and diagnostic tests",
   "Choose an action — control charts and CUSUM"], 1,
  "Shape 5's ancestor is manual chart abstraction. The others are misassigned: clustering's ancestor is cluster and factor analysis, anomaly detection's is control charts and CUSUM, and decision support's is operations research and decision analysis. Naming the ancestor is how you find the comparator a claim must beat."),
 ("The atlas names two cross-cutting layers alongside the six shapes. What does it claim about the first of them?",
  ["Evaluation is a reporting requirement that follows the modelling work",
   "Evaluation and deployment are the same layer viewed at different scales",
   "Almost every failure in the atlas is an evaluation failure, not a modelling failure",
   "Evaluation matters most for regulator-cleared applications and least for research"], 2,
  "Evaluation decides whether a model is real, and deployment and governance decide whether a real model helps anyone. The stronger claim is the first: nearly everything in the cautionary canon failed on how it was evaluated rather than on how it was built."),
 ("A colleague brings you a new AI-in-health claim. What are the four questions the atlas puts it through?",
  ["Which shape · what comparator · how evaluated · maturity, honestly",
   "Which shape · what data · which model · what accuracy",
   "Which specialty · what regulator · what cost · what evidence grade",
   "Which population · what outcome · what comparator · what effect size"], 0,
  "Answer those four and the item becomes an atlas row; answer them in depth and it becomes a deep-dive page. Note the first one's escape hatch: if it does not fit any of the six shapes, that is itself a finding worth saying out loud."),
 ("Which of these is NOT one of the six cases in the atlas's cautionary canon?",
  ["Google Flu Trends — big data does not fix unstable predictors",
   "Obermeyer et al. 2019 — the label carries the bias",
   "The AI Clinician — off-policy evaluation is not evidence",
   "AlphaFold — structural prediction outran its validation set"], 3,
  "The canon is Google Flu Trends, the Epic Sepsis Model, Obermeyer et al., the Wynants COVID prognostic review, Beede et al. in Thailand, and the AI Clinician. Each teaches a distinct evaluation failure, which is why the atlas says the six read together teach more than a methods textbook."),
 ("The atlas keeps a visible list of what it is still missing. Why is that in the course rather than removed?",
  ["To signal the course is provisional and should be treated with caution",
   "Because the missing items are too technical for the intended audience",
   "It is the course's to-do queue, and a living course states what it does not yet cover",
   "Regulatory guidance requires disclosure of scope limitations in training material"], 2,
  "The course is marked `living`, and the gap list is where new entries come from. Stating what is not covered is also what stops a reader assuming the atlas is exhaustive — the same reason the genomic surveillance course carries an explicit `not_covered` block."),
],
"lesson-20": [
 ("Google Flu Trends failed twice, in opposite directions. What were the two failures?",
  ["It over-estimated 2009 and under-estimated 2012-13, both from search-volume drift",
   "It under-estimated the 2009 pandemic and over-estimated the 2012-13 peak",
   "It over-estimated both seasons, increasingly, as the model aged without recalibration",
   "It failed only in 2012-13; the 2009 performance was accurate but arrived too late"], 1,
  "It under-estimated the 2009 swine flu pandemic because the event was out of season and the model had only ever learned normal winters — so the one event it existed to catch was the one it could not catch. Then in 2012-13 it over-estimated the peak by roughly double."),
 ("Why does the deep dive describe the 2009 under-estimate as structural rather than bad luck?",
  ["The search index had not yet accumulated enough historical volume to fit on",
   "The model was retrained annually and 2009 fell between two retraining cycles",
   "It was fitted on seasonal influenza, so an out-of-season pandemic was outside everything it had learned",
   "Pandemic influenza produces different symptoms, so people searched different terms"], 2,
  "The model learned the relationship between search volume and ILI across normal winters. A pandemic arriving out of season is precisely the case with no analogue in the training data — which is why the failure is a property of the design rather than of that particular year."),
 ("Two causes are given for the 2012-13 over-estimate. What are they?",
  ["Predictors selected for correlation rather than sense, and Google changing what searchers saw",
   "A change in the CDC's ILI case definition, and reduced clinic attendance that season",
   "Overfitting to the 2009 pandemic, and a shift in the age distribution of searchers",
   "Loss of the original engineering team, and migration to a new data warehouse"], 0,
  "Predictors chosen by correlation alone have no reason to keep working when the world shifts. And Google kept changing what people saw when they searched — autocomplete, suggested terms, related searches — so the inputs quietly changed meaning underneath a model nobody was recalibrating."),
 ("What does the deep dive say the lesson is NOT?",
  ["That proxies require the real measurement to stay honest",
   "That unstable predictors are a hazard when selected purely by correlation",
   "That 'big data does not work'",
   "That a nowcast can supplement surveillance but not replace it"], 2,
  "The failure was not about volume of data. It was about a proxy drifting away from what it proxied, with no ground truth left in place to notice. That is why the durable conclusion is that a proxy can supplement surveillance and can never replace it."),
 ("Google Flu Trends is described in the course as the canonical shape-straddling failure. What does that mean here?",
  ["It combined tabular and text data without declaring which dominated",
   "It was evaluated on whether it tracked ILI, and marketed on whether it warned earlier",
   "It switched from a regression to a classification framing partway through",
   "It reported accuracy on one population and calibration on another"], 1,
  "Tracking ILI is shape 2, forecasting. Warning earlier than surveillance is shape 1, detecting the unusual. Those require different evidence, and a claim evaluated as one shape and sold as another is the most common failure mode in the field."),
 ("What is the appropriate present-day reading of this case for a surveillance programme?",
  ["Digital proxies are unusable for public health and should not be resourced",
   "Digital proxies are usable where a ground truth is maintained alongside them",
   "The failure was specific to search data; social media proxies avoid it",
   "The approach works if the model is retrained continuously on recent data"], 1,
  "Retraining helps but does not solve it, because retraining needs the ground truth the proxy was meant to replace. The honest position is that a proxy earns its place as a supplement to a maintained measurement, and loses it the moment the measurement is switched off."),
],
"lesson-21": [
 ("Chest X-ray AI for TB reached scale and dermatology AI largely did not, despite both matching specialists. What does the deep dive identify as the decisive difference?",
  ["The pathway each was placed in, not the accuracy either achieved",
   "The absolute accuracy achieved on external validation sets",
   "The volume of training data available in each speciality",
   "The regulatory route each product chose to pursue"], 0,
  "Both matched specialists on accuracy. The TB system was built as a triage step with a confirmatory laboratory test behind it; the skin apps were built to be the answer itself. Whether medical AI helps anyone depends far more on the pathway you put it in than on how good the model is."),
 ("What is the practical consequence of the TB system being a triage step rather than a diagnosis?",
  ["It requires a lower accuracy threshold, so evaluation is less demanding",
   "It can be deployed without regulatory clearance in most jurisdictions",
   "When it is wrong it costs a molecular test, rather than a missed cancer",
   "It removes the need for country-specific threshold setting"], 2,
  "It gives a score, each country sets its own cut-off, and anyone flagged gets a molecular test. The cost of a false positive is a test. For a skin app built as the answer itself, at a fixed threshold with no laboratory behind it, the cost of a false negative is someone with a melanoma being told not to worry."),
 ("The two applications also differed in what they were validated against. How?",
  ["TB against dermatologist consensus; dermatology against biopsy results",
   "TB against a laboratory result; dermatology largely against clinicians' opinions",
   "Both against expert consensus, but TB used more experts per image",
   "TB against prospective outcomes; dermatology against retrospective chart review"], 1,
  "TB models were validated against a culture or molecular result — an objective reference. Dermatology models were largely validated against dermatologists' opinions, which is a comparator that inherits the comparator's own error and cannot exceed it."),
 ("What does the deep dive say about the populations each was trained on?",
  ["Both were trained on globally representative image sets",
   "TB models used synthetic augmentation; dermatology used only real images",
   "TB models were trained on the populations they would be used in; dermatology mostly on light skin",
   "Dermatology models were trained on more diverse populations but tested on fewer"], 2,
  "And the compounding detail is that skin type was often not even recorded, so the gap could not be seen in the evaluation. A subgroup failure you have no field for is a subgroup failure nobody will find."),
 ("Which finding best illustrates that a dermatology model can learn the wrong thing entirely?",
  ["Models performed worse on images captured with older camera hardware",
   "Surgical skin markings raised melanoma probability and increased false positives on benign lesions",
   "Accuracy fell when images were resized below the training resolution",
   "Performance varied by anatomical site more than by lesion type"], 1,
  "Clinicians mark lesions they are already concerned about, so the marking is a proxy for clinical suspicion rather than for melanoma. The model learned the marking. It is the cleanest demonstration in the course that high accuracy can rest on a feature that will not be there — or will be there for the wrong reason — in deployment."),
 ("What should a programme take from this pair when assessing any new diagnostic AI?",
  ["Ask what happens when it is wrong, and what sits downstream to catch it",
   "Require external validation on at least three independent datasets",
   "Prefer applications where the model matches or exceeds specialist accuracy",
   "Choose applications with an existing regulatory clearance in a comparable market"], 0,
  "External validation and accuracy both matter, but they are not what separated these two cases. The separating question is about the pathway: what the failure costs, and whether anything downstream catches it. That is the question the whole course is organised around."),
],
}

CARDS = {
"lesson-20": [
 ("Google Flu Trends: what were the two failures, and why is that pairing the point?",
  "It UNDER-estimated the 2009 swine flu pandemic — out of season, and the model had only learned normal winters, so the one event it existed to catch was the one it could not. Then it OVER-estimated the 2012-13 peak by roughly double. Failing in both directions rules out a simple bias and points at the design."),
 ("Name the two causes of the 2012-13 Google Flu Trends over-estimate.",
  "Predictors selected for correlation rather than for making sense, so they had no reason to keep working when the world shifted; and Google changing what searchers saw — autocomplete, suggestions, related searches — so the inputs quietly changed meaning underneath a model nobody was recalibrating."),
 ("What is the durable lesson of Google Flu Trends, stated so it does not collapse into 'big data doesn't work'?",
  "A proxy needs the real measurement to stay honest. It can supplement surveillance and can never replace it — because the moment you switch off the ground truth, you also switch off your ability to notice the proxy drifting, and you cannot retrain without it either."),
 ("Why is Google Flu Trends the canonical shape-straddling failure?",
  "It was evaluated on whether it tracked ILI (shape 2, forecasting) and marketed on whether it warned earlier than surveillance (shape 1, detection). Those need different evidence. A claim evaluated as one shape and sold as another is the most common failure mode in the field."),
 ("What did Google Flu Trends actually achieve, before the failures?",
  "It estimated current influenza levels from search volume roughly two weeks ahead of the official surveillance reporting lag, and it fitted the historical data well. Both are real. The value question is not whether it worked but whether it stayed working without the measurement it was meant to pre-empt."),
],
"lesson-21": [
 ("TB chest X-ray AI reached scale and dermatology AI did not, despite comparable accuracy. What separated them?",
  "The pathway, not the model. TB CAD is a triage step: it gives a score, each country sets its own cut-off, and anyone flagged gets a confirmatory molecular test — so a false positive costs a test. The skin apps were built to be the answer itself, at a fixed threshold with no laboratory behind them, so a false negative sends someone with a melanoma home reassured."),
 ("What were the two applications validated against, and why does the difference matter?",
  "TB models against a culture or molecular result — an objective reference. Dermatology models largely against dermatologists' opinions, which inherits the comparator's own error and cannot exceed it. Validating against expert opinion caps you at expert performance and hides shared blind spots."),
 ("What is the surgical-skin-marking finding, and what does it demonstrate?",
  "Markings in dermoscopic images raised the model's melanoma probability and increased false positives on benign nevi by roughly 40%. Clinicians mark lesions they are already worried about, so the marking is a proxy for clinical suspicion, not for melanoma. It is the cleanest demonstration that high accuracy can rest on a feature that will not be present, or will mean something else, in deployment."),
 ("Why was the dermatology skin-tone gap so slow to surface?",
  "Models were trained mostly on light skin, and skin type was often not recorded at all — so the subgroup could not be stratified in evaluation. A subgroup failure you have no field for is a subgroup failure nobody will find, which is a metadata problem before it is a modelling one."),
 ("What single question does this pair suggest asking of any new diagnostic AI?",
  "What happens when it is wrong, and what sits downstream to catch it? Accuracy and external validation matter, but they are not what separated these two cases. Design the pathway first: a model behind a confirmatory test is forgiving of error in a way that a model acting as the answer never is."),
],
}


def main():
    lj = HERE / "lessons.json"
    qj = HERE / "qbank.json"
    cj = HERE / "course.json"
    data = json.loads(lj.read_text())
    qbank = json.loads(qj.read_text())

    already = [l["id"] for l in data["lessons"] if l["id"] in NEW and l.get("quiz")]
    if already:
        print(f"already populated, refusing to run twice: {already}")
        return 1

    rng = random.Random(20260829)
    added_q = added_c = 0
    for lesson in data["lessons"]:
        lid = lesson["id"]
        if lid not in NEW:
            continue
        quiz = []
        for q, opts, correct, expl in NEW[lid]:
            idx = list(range(len(opts)))
            rng.shuffle(idx)
            quiz.append({"question": q,
                         "options": [opts[i] for i in idx],
                         "correct": idx.index(correct),
                         "explanation": expl})
        lesson["quiz"] = quiz
        added_q += len(quiz)

    for lid, cards in CARDS.items():
        if lid in qbank:
            print(f"qbank already has {lid}; refusing"); return 1
        qbank[lid] = {"cards": [{"front": f, "back": b} for f, b in cards]}
        added_c += len(cards)

    lj.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    qj.write_text(json.dumps(qbank, indent=2, ensure_ascii=False) + "\n")

    c = json.loads(cj.read_text())
    c["quiz_questions"] = sum(len(l.get("quiz") or []) for l in data["lessons"])
    c["cards_authored"] = sum(len(v.get("cards", [])) for k, v in qbank.items() if k != "_note")
    c["coverage_note"] = (
        "Audit 2026-08-29 found lesson-00, lesson-20 and lesson-21 with empty quiz arrays, and "
        "lesson-20/21 with no qbank entry — a learner reaching any of the three got no self-check, "
        "and the two deep dives contributed nothing to the review queue. Filled: every lesson now "
        "carries both. Option order for the new questions was shuffled with a fixed seed; the "
        "existing 97 were left untouched because they already audit clean.")
    cj.write_text(json.dumps(c, indent=2, ensure_ascii=False) + "\n")

    print(f"added {added_q} questions across {len(NEW)} lessons, {added_c} cards across {len(CARDS)}")
    print(f"course totals: {c['quiz_questions']} questions, {c['cards_authored']} cards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
