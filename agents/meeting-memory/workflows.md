# Meeting Memory Workflows

## 1. Meeting intake workflow

Possible inputs:

- audio recording
- transcript
- handwritten or typed meeting notes
- calendar or title metadata

Process:

1. Create a meeting record.
2. Store basic metadata:
   - date
   - meeting title
   - participants
   - domain
   - project
3. Save artifacts in the meeting folders.
4. Run or prepare transcription.
5. Create structured extraction.

## 2. Capture-mode workflow

Meeting Memory must support three modes:

### In-person

- mobile phone voice memo
- dedicated recorder if needed
- upload or place audio in local meeting folder

### Online

- local desktop audio capture
- local export from meeting software when available
- preserve original meeting title and date

### Mixed / hybrid

- prefer a single clean local recording
- if multiple recordings exist, choose one primary source and mark the others as supplementary

## 3. Transcription workflow

Recommended default:

- local Whisper-based transcription

Process:

1. Save raw audio.
2. Produce raw transcript.
3. Produce cleaned transcript.
4. Preserve timestamps if possible.
5. Never overwrite the raw transcript.

## 4. Structured extraction workflow

From the cleaned transcript, extract:

- summary
- decisions
- action items
- owners
- deadlines
- unresolved questions
- risks or concerns
- people mentioned
- linked projects
- linked PhD articles if relevant

## 5. Follow-up briefing workflow

Before a next meeting, `meeting_series_briefing(series_id)` gives:

- what was decided last time
- the open actions, by owner, with their ids and what is overdue
- the files kept from last time (compare the new figures with the old)
- the report rules for this series

## 6. Meeting continuity workflow — series

A **series** is one recurring meeting with ONE group (`meeting_series`). Two groups
reviewed on the same template are two series. Each meeting in a series links to
its predecessor; each action keeps one identity for its whole life, and every
meeting that reviews it records its status there (`meeting_action_reviews`).

Recognising the series of a new meeting (`match_meeting_series`), strongest first:

1. the group's code in the title or the file names
2. participants who attend only that series — people present in every series
   (the researcher, central colleagues) count for nothing
3. timing against the series' cadence
4. title similarity, as a tie-breaker

The matcher proposes; the researcher confirms in one line. Nothing is linked on
resemblance.

Report rules are learned per series: the researcher's final report is compared
with the draft (`learn_from_report_edits`) and each pattern becomes a rule
(`add_meeting_report_rule`).

## 7. Exception workflow

If transcript quality is poor:

- mark confidence as low
- preserve the raw transcript
- ask for manual confirmation on key decisions if needed

If no recording exists:

- accept notes only
- mark source quality accordingly
