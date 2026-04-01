# Cybersecurity Agent

Protects the Metis PKM from internet threats, prompt injection, malicious files, and unauthorized agent behavior.

## Files

- `system-prompt.md` — full operational rules, threat patterns, domain allowlist
- `contract.md` — scope, authority, coordination

## Key capabilities

- URL validation against allowlist before any agent fetches
- Prompt injection pattern detection in RSS feeds and web content
- File integrity checking for Crucible imports
- Agent scope enforcement (only 3 agents get internet)
- Security event logging

## No internet

This agent deliberately has no internet access to prevent it from becoming a vector.
