# Librarian Output Spec

## High-value item format

Each important new source should be summarized in this structure:

### Source

- title
- year
- source type
- source link
- local availability

### Relevance

- why it matters
- likely linked PhD article
- linked project or domain

### Tags

- disease
- geography
- method
- surveillance mode
- elimination phase
- diagnostic test if relevant

### Action

- already in library
- download now
- acquire manually
- read soon
- background only

## Scan summary format

Every scan should return:

- number of candidate items checked
- number of high-value items
- number of likely duplicates
- number of blocked-access items
- top 3 to 5 items to surface in the Control Room

## Status values

- `new_candidate`
- `seeded`
- `to_triage`
- `high_priority`
- `background`
- `duplicate`
- `acquisition_needed`
- `already_local`

## Control-room handoff format

For Monia, the Librarian should hand back:

- title
- one-line why-it-matters
- linked article or project
- action recommendation
