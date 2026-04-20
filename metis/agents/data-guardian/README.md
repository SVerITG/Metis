# Data Guardian

Protects patient data, medical records, original research content, and personal information from being exposed or transmitted to external services.

## Files

- `system-prompt.md` — full rules, PII patterns, data classification, intervention rules
- `contract.md` — scope, blocking authority, escalation

## Key protections

- Patient/medical data: always blocked from external transmission
- Excel/CSV/data files: requires explicit user confirmation before sending
- Original content (articles, ideas, proposals): user is informed about API data retention
- Database files: never sent externally
- GPS coordinates at individual level: always blocked

## Important context

Claude API (used by Claude Code/Desktop) does NOT use data for model training. But data is retained 30 days on Anthropic servers for safety. The Data Guardian ensures the user is aware and consents.
