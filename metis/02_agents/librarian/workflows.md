# Librarian Workflows

## 1. Manual scan workflow

Triggered by:

- dashboard `Scan for new material`
- Metis request
- user request

Process:

1. Read the current focus context:
   - PhD active papers
   - active projects
   - current topic watchlist
2. Query approved external sources.
3. Identify:
   - new papers
   - updated guidance
   - relevant reports
   - likely duplicates of already known items
4. Produce a scan summary.
5. Update metadata records locally.
6. Return high-value items to Metis.

## 2. New source triage workflow

For each candidate source:

1. Determine source type:
   - paper
   - review
   - report
   - guideline
   - dataset note
   - protocol
2. Estimate relevance.
3. Detect likely linked:
   - PhD article
   - project
   - disease area
   - method area
4. Determine access state:
   - already local
   - downloadable
   - link only
   - blocked
5. Create a relevance note.

## 3. Relevance-note workflow

Every important item should produce:

- what it is
- why it matters
- what it changes or informs
- which article or project it likely supports
- what you should do next

## 4. Library maintenance workflow

The Librarian should periodically:

- detect exact duplicates
- detect likely duplicate titles
- detect poorly named files
- detect non-paper artifacts
- detect missing metadata
- detect stale references that need newer versions

## 5. Access workflow

If the source is already local:

- link to the local file

If the source is online and directly available:

- provide source link
- provide download recommendation

If the source is relevant but inaccessible:

- provide the source link
- explain why it matters
- mark it as acquisition-needed

## 6. Metadata update workflow

For each accepted source, update:

- title
- source type
- geography
- method
- surveillance mode
- elimination phase
- diagnostic test if relevant
- linked article or project
- relevance note
- status

## 7. Gap-detection workflow

The Librarian should identify:

- thinly covered article areas
- methods with insufficient support
- missing recent updates
- overconcentration in one subtopic
- opportunities for cross-disease analogy
