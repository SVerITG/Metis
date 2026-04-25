# Course Builder Contract

## Inputs accepted
- Course slug from `learning_courses` placeholder
- Questionnaire responses (JSON or freeform)
- Optional: import path for existing material

## Outputs produced
- `metis/knowledge/courses/{slug}/course.json` (Learning Architect schema)
- `metis/knowledge/courses/{slug}/README.md`
- `metis/knowledge/courses/{slug}/modules/NN_slug/notes.md | exercises.md | assessment.md`
- `metis/knowledge/courses/{slug}/sources/` with YAML metadata
- Rows in `spaced_repetition` table for retain-long-term facts
- Updated row in `learning_courses` (status=active, progress_pct, module counts)

## Quality bar
- Passes all seven guardrail checks before publication.
- At least one primary source per module.
- Readable by target learner in the stated time budget.

## Boundaries
- Never writes directly to active production projects.
- Never sends data externally without Data Guardian approval.
- Never claims external credentials or access without user confirmation.
