# Meeting Memory Output Spec

## Required outputs per meeting

### 1. Meeting record

- title
- date
- participants
- project
- domain
- related article if relevant

### 2. Raw transcript

- direct transcription output
- minimal normalization only

### 3. Cleaned transcript

- readable
- speaker or section clarity where possible
- no invented content

### 4. Structured note

Should contain:

- short summary
- decisions
- action items
- owners
- deadlines
- unresolved questions
- important concerns
- linked topics

### 5. Briefing note

Should contain:

- last meeting summary
- outstanding actions
- unresolved issues
- what needs discussion next

## Confidence field

Every meeting extraction should include a confidence marker:

- high
- medium
- low

This should reflect transcript quality and extraction certainty.

## Status values

- `recorded`
- `transcribed_raw`
- `transcript_cleaned`
- `structured`
- `briefing_ready`
- `needs_review`

## Folder usage

- `05_sources/meetings/audio`
- `05_sources/meetings/transcripts`
- `05_sources/meetings/structured`
- `05_sources/meetings/briefings`
- `05_sources/meetings/templates`
