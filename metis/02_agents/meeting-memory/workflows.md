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

Before a next meeting, Meeting Memory should produce:

- what was decided last time
- what was assigned
- what is still unresolved
- what changed since the previous meeting
- what needs attention now

## 6. Meeting continuity workflow

Meeting Memory should link meetings across time when they belong to:

- the same project
- the same article
- the same supervision stream
- the same operational topic

## 7. Exception workflow

If transcript quality is poor:

- mark confidence as low
- preserve the raw transcript
- ask for manual confirmation on key decisions if needed

If no recording exists:

- accept notes only
- mark source quality accordingly
