#!/usr/bin/env python3
"""Audit multiple-choice quizzes for the defects that let a learner score well
without understanding anything.

Checks, in order of how badly each one breaks a quiz:

  1. POSITION BIAS  — is the correct option always in the same slot?
     A learner who notices scores 100%. Fatal, and invisible per-question.
  2. LONGEST-IS-CORRECT — is the correct option the uniquely longest one?
     Chance is 1/n_options. Well above that is an exploitable tell.
  3. LENGTH RATIO — correct-answer words / mean-distractor words. The recorded
     procedure's threshold is 2.5.
  4. SPREAD — option word-count range, which makes the tell visible at a glance.
  5. DUPLICATES — near-identical question stems.

Usage:
    python3 tools/audit_quiz.py <manifest.json> [more.json ...]

Reads either shape: a list of lessons, or {"lessons": [...]}, where each lesson
has a "quiz" list of {question, options, correct, explanation}.
"""
import json
import statistics
import sys
from collections import Counter


def load_quizzes(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    lessons = data.get("lessons", data) if isinstance(data, dict) else data
    for lesson in lessons:
        lid = lesson.get("id", "?")
        for idx, q in enumerate(lesson.get("quiz") or []):
            opts, ci = q.get("options") or [], q.get("correct")
            if not opts or ci is None or not (0 <= ci < len(opts)):
                continue
            yield lid, idx, q, opts, ci


def audit(path):
    rows = []
    for lid, idx, q, opts, ci in load_quizzes(path):
        wc = [len(o.split()) for o in opts]
        distr = [w for i, w in enumerate(wc) if i != ci]
        mean_d = statistics.mean(distr) if distr else 0
        rows.append(dict(
            lesson=lid, idx=idx, n_opts=len(opts), correct_pos=ci,
            correct_wc=wc[ci], mean_distractor_wc=round(mean_d, 1),
            ratio=round(wc[ci] / mean_d, 2) if mean_d else 99.0,
            spread=max(wc) - min(wc),
            longest_is_correct=(wc[ci] == max(wc) and wc.count(max(wc)) == 1),
            stem=q.get("question", "")[:70],
        ))

    print(f"\n{'=' * 72}\n{path}\n{'=' * 72}")
    if not rows:
        print("no scorable questions found")
        return rows
    n = len(rows)
    print(f"questions: {n}")

    # 1. position bias
    pos = Counter(r["correct_pos"] for r in rows)
    n_opts = statistics.mode(r["n_opts"] for r in rows)
    expected = n / n_opts
    print(f"\n1. POSITION BIAS  (expect ~{expected:.1f} per slot across {n_opts} slots)")
    for slot in range(n_opts):
        got = pos.get(slot, 0)
        bar = "#" * int(40 * got / n)
        flag = "  <-- FATAL" if got > 0.6 * n else ""
        print(f"   slot {slot}: {got:4d}  {bar}{flag}")
    worst = max(pos.values()) / n
    print(f"   most-used slot holds {worst * 100:.1f}% of answers"
          f"{'  ** EXPLOITABLE **' if worst > 0.4 else '  ok'}")

    # 2. longest-is-correct
    li = [r for r in rows if r["longest_is_correct"]]
    chance = 100 / n_opts
    print(f"\n2. LONGEST-IS-CORRECT: {len(li)}/{n} = {100 * len(li) / n:.1f}%"
          f"  (chance {chance:.0f}%)"
          f"{'  ** EXPLOITABLE **' if 100 * len(li) / n > chance + 15 else '  ok'}")

    # 3. length ratio
    ratios = [r["ratio"] for r in rows]
    over = [r for r in rows if r["ratio"] > 2.5]
    print(f"\n3. LENGTH RATIO: median {statistics.median(ratios):.2f}  "
          f"mean {statistics.mean(ratios):.2f}")
    print(f"   ratio > 2.5: {len(over)} ({100 * len(over) / n:.1f}%)"
          f"{'  <-- fix these' if over else '  ok'}")
    for r in sorted(over, key=lambda x: -x["ratio"])[:5]:
        print(f"     {r['ratio']:5.1f}  {r['correct_wc']:3d}w vs "
              f"{r['mean_distractor_wc']:5.1f}w  {r['lesson']} q{r['idx']}  {r['stem']}")

    # 4. spread
    wide = [r for r in rows if r["spread"] > 20]
    print(f"\n4. OPTION SPREAD > 20 words: {len(wide)} ({100 * len(wide) / n:.1f}%)"
          f"{'  <-- visible tell' if wide else '  ok'}")

    # 5. duplicates
    stems = Counter(r["stem"].lower() for r in rows)
    dupes = {s: c for s, c in stems.items() if c > 1}
    print(f"\n5. DUPLICATE STEMS: {len(dupes)}")
    for s, c in list(dupes.items())[:5]:
        print(f"     x{c}  {s}")
    return rows


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for p in sys.argv[1:]:
        audit(p)
    print()
