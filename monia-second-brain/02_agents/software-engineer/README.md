# Software Engineer Agent

Code reviewer, debugger, and builder for all software in the Monia system and personal/research projects.

## Languages
R (primary), Python, JavaScript/TypeScript (secondary)

## Environments
RStudio, R Shiny, VS Code, Docker, MCP servers

## Key files
- `system-prompt.md` — full operating instructions
- `contract.md` — scope, triggers, outputs, escalation rules
- `workflows.md` — six named workflows for common task types
- `patterns.md` — running log of successful solutions (memory)

## Design principles extracted from ruflo
1. Search `patterns.md` before every task (memory-before pattern)
2. Append to `patterns.md` after every success (memory-after pattern)
3. Route by complexity before acting (trivial / medium / complex)
4. Security checklist on every code review (from ruflo @claude-flow/security)
5. Escalate to ruflo swarm for 10+ file tasks (not for routine work)

## Relationship to ruflo
The full ruflo repository is stored at `02_agents/ruflo-reference/` with a full analysis at `02_agents/ruflo-reference/ANALYSIS.md`. This agent distils the patterns that are applicable to a personal PKM at reasonable scale. The ruflo CLI can be optionally activated for large-scale code work.
