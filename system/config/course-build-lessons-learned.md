# Course Builder — Lessons Learned

*Reference implementation: `knowledge/courses/biostatistics/` (Biostatistics for Epidemiologists, 12 lessons)*  
*Written: 2026-05-13*

---

## What the reference build taught us

### 1. Lesson structure that actually works

Every lesson should follow this exact pattern — no deviations:

```
# [Title]

## Learning objectives
- Verb-first, one line each (Bloom level implied by the verb)
- 3–5 objectives maximum per lesson
- Each objective must be testable

## Prerequisites
- List prior lessons or explicit assumptions
- If none: write "None."

## Content

### Section N: [Named topic]
[prose — 200–400 words per section]
[concrete example grounded in the learner's domain]
[code block if applicable, in R by default]

## Summary
- Bullet list of key takeaways, one per objective
- Matches the learning objectives exactly

## Exercises
1. Application exercise (requires recall + application)
2. Challenge exercise (requires synthesis or evaluation)
3. Reflection prompt (connects to the learner's own research)

## Further reading
- [Author Year] [Title] — [what it adds beyond this lesson]
```

**Why this matters:** The biostatistics build drifted from this structure in lessons 8–12 (missing summaries, exercises collapsed into content). Downstream spaced-repetition seeding broke because the parser expected `## Exercises` as a top-level header.

---

### 2. `lessons.json` schema — follow it exactly

```json
{
  "lessons": [
    {
      "id": "lesson-NN",
      "title": "Human-readable title",
      "description": "One-sentence learning promise",
      "section": "Module group name",
      "order": 1
    }
  ]
}
```

- `id` must match the filename: `NN-slug.md` → `"lesson-NN"`
- `order` must be sequential — gaps break the Learning tab progress bar
- `section` groups lessons in the UI; keep to 3–4 groups per course

---

### 3. Bloom level discipline

Every learning objective must start with a Bloom-level verb:

| Level | Verbs to use |
|---|---|
| Remember | define, list, identify, name |
| Understand | explain, describe, summarize, distinguish |
| Apply | calculate, use, apply, demonstrate |
| Analyze | compare, examine, break down, classify |
| Evaluate | critique, justify, assess, defend |
| Create | design, construct, build, draft |

**Rule:** A lesson with only "understand" objectives should have no exercises requiring calculations. Match assessment difficulty to the ceiling verb in the objectives.

---

### 4. Example grounding

Every content section needs an example grounded in the learner's domain. For epidemiology courses, the pattern that worked best:

> "In a study of [disease] in [setting], the variable [X] would be treated as [type] because [reason]."

Generic mathematics examples ("suppose X = 5") lost learners in the biostatistics build. Domain-specific examples kept engagement.

---

### 5. Code blocks

For R code:
- Always use tidyverse style (no base-R dollar-sign indexing)
- Include `library()` call at the top of every block
- Provide expected output as a comment at the end: `# Expected: 0.42`
- Do not use data from packages not in the standard install — use `mtcars`, `iris`, or the course's own dataset

For Python code (if applicable):
- pandas + matplotlib
- Always show `import` at top of block

---

### 6. File naming

```
knowledge/courses/{slug}/
  lessons/
    01-first-topic.md
    02-second-topic.md
  lessons.json
  README.md
```

- **Slug format:** `NN-kebab-case.md` — double-digit prefix ensures sort order
- **README.md must include:** prerequisites, how to work through the course, how assessments are graded, glossary terms
- Never nest subdirectories under `lessons/` — the Learning tab assumes a flat list

---

### 7. Spaced-repetition seeding

After publishing, call `seed_sr_from_course(course_slug)` to extract key terms from each lesson's summary and objectives and insert them into `spaced_repetition` table.

**What went wrong in the biostatistics build:** Lessons 08–12 had no `## Summary` section → seeder produced 0 items for those lessons → learning progress for advanced regression topics was never tracked.

**Fix:** Before calling the seeder, run a quick validation:
```bash
for f in knowledge/courses/{slug}/lessons/*.md; do grep -q "## Summary" "$f" || echo "MISSING SUMMARY: $f"; done
```

---

### 8. Course metadata in `learning_courses` DB

When registering the course in the DB:

```sql
INSERT INTO learning_courses (title, category, progress_pct, total_modules, completed_modules, status, slug)
VALUES (?, ?, 0, ?, 0, 'active', ?);
```

- `total_modules` = number of entries in `lessons.json`, not number of files (they may differ if a file is a draft)
- `slug` must match the folder name exactly — this is the FK used in spaced repetition joins
- `category` should match the section names in `lessons.json` (use the first/primary section if mixed)

---

### 9. Review gate before publishing

Before status → 'active', verify:

1. All lessons have `## Learning objectives`, `## Content`, `## Summary`, `## Exercises`
2. All `id` values in `lessons.json` match filenames
3. `order` is sequential starting from 1
4. Methods Coach (or domain expert) has reviewed at least the most technical lesson
5. README.md exists with the four required sections
6. No lesson exceeds 2,500 words (use the challenge exercise prompt if more depth is needed)

---

### 10. What to do when sources are paywalled

The biostatistics build used OpenIntro + Khan Academy as open-access backbones. This worked well. For future courses:

1. First pass: check PaperQA2 index (`ask_library()`) for relevant indexed content
2. Second pass: OpenAlex → filter `is_oa=true`
3. Third pass: arXiv / bioRxiv / medRxiv
4. If the topic genuinely requires a paywalled textbook: ask the user if they have access and can provide a PDF for indexing. Do not scrape or reproduce copyrighted content.

---

## Anti-patterns (do not repeat)

| Anti-pattern | What happened | Fix |
|---|---|---|
| Mixing `## Exercises` into the content | Seeder missed them | Always use top-level `## Exercises` header |
| `lesson.id` = "L01" instead of "lesson-01" | Learning tab 404 on progress update | Always use `lesson-NN` format |
| Writing objectives as "Students will understand X" | Too vague to assess | Start with an action verb, not "Students will" |
| Generating code blocks without domain context | Learners couldn't connect to their own data | Always tie code to the course's focal disease/dataset |
| Publishing with `progress_pct = null` | Progress bar NaN error | Always initialize to 0 |
| Using `module` and `lesson` interchangeably | Schema confusion across files | Lessons are items; modules are groups of lessons. This codebase uses "lessons" as the primary atom. |
