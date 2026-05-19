# Transcription Stack

## Baseline recommendation

Use a local-first transcription stack.

Preferred core:

- local audio capture
- local Whisper-based transcription
- local storage of all artifacts

## Why this stack

- aligns with your privacy requirement
- supports in-person, online, and mixed meetings
- keeps operational and scientific conversations under your control

## Practical capture recommendations

### In-person meetings

Recommended:

- phone voice memo app
- or dedicated recorder for better audio quality

Requirements:

- stable file export
- local saving
- clear file naming with date and title

### Online meetings

Recommended:

- local desktop audio capture
- or meeting export if available and saved locally

Requirements:

- keep the original recording
- preserve meeting title and date

### Mixed meetings

Recommended:

- one primary recorder near the main speaker group
- if possible, also retain the online recording as backup

## Suggested artifact chain

For each meeting keep:

1. `audio/`
2. `transcripts/raw`
3. `transcripts/clean`
4. `structured/`
5. `briefings/`

## Important rule

Do not store only the cleaned summary.

The system should preserve:

- raw audio
- raw transcript
- cleaned transcript
- structured extraction

This is essential for auditability and later correction.
