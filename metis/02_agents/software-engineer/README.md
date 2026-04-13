# Software Engineer Agent

Code reviewer, debugger, and builder for all software in the Metis system and personal/research projects.

## Languages
R (primary), Python, JavaScript/TypeScript (secondary)

## Environments
RStudio, R Shiny, VS Code, Docker, MCP servers

## Key files
- `system-prompt.md` — full operating instructions
- `contract.md` — scope, triggers, outputs, escalation rules
- `workflows.md` — six named workflows for common task types
- `patterns.md` — running log of successful solutions (memory)

## Design principles
1. Search `patterns.md` before every task (memory-before pattern)
2. Append to `patterns.md` after every success (memory-after pattern)
3. Route by complexity before acting (trivial / medium / complex)
4. Security checklist on every code review
