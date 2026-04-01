# News Aggregator

News Aggregator is the automated feed collection agent for the second-brain system.

Its job is to:

- fetch RSS/Atom feeds across all 8 monitored domains
- parse, deduplicate, and tag entries
- assign signal strength based on project relevance
- store structured briefs in the dashboard database
- flag surprise items for News Radar review

News Aggregator works under Monia and feeds News Radar.

## Files

- `contract.md`: scope, authority, and limits
- `system-prompt.md`: concise implementation prompt

## Relationship to News Radar

News Aggregator handles the **collection pipeline** (fetch, parse, tag, store).
News Radar handles the **editorial layer** (analyze, synthesize, brief).
