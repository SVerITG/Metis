# Release Coordinator — Contract

## Triggers

- Any request involving a git release, version bump, or push to a public repo
- "scan for personal data", "pre-publish check", "is this safe to push"
- "sync to base", "propagate to Metis", "push to origin"
- "generate changelog", "what changed since last release"
- "check installers", "verify CLAUDE.md", "is the Dockerfile in sync"
- Direct invocation: `/release-coordinator` or `rc [command]`

## Always loads before acting

- `agents/release-coordinator/skill.md` (this agent's own system prompt)
- `agents/release-coordinator/scanner-rules.md` (compiled regex patterns)
- `.gitignore` (to understand what is already excluded)
- `system/config/constitution.md` (red lines apply to release too)

## Commands handled

| Command | Description |
|---|---|
| `scan [path\|staged\|all]` | Run personal data scanner. Default: staged files. |
| `release [patch\|minor\|major] [--dry-run]` | Full release sequence with scan, bump, changelog, propagate, tag. |
| `sync [base\|Metis_BM\|Metis_CL]` | Propagate generic files to the named variant. |
| `verify` | Check installers, CLAUDE.md, Dockerfile for consistency. |
| `changelog [--since tag]` | Generate CHANGELOG entry from git log since last tag. |

## Output contract

Every command produces:
1. A **status block** — one line per check with ✅ / ⚠️ / 🔴 indicator
2. A **detail section** — expanded only for warnings and blocks
3. An **action required** section — numbered list of steps the user must take before proceeding
4. For `release`: a GitHub release notes draft in Markdown

Outputs are NOT saved to `outputs/reviews/` by default (this is an infrastructure agent, not a research agent). Exception: if the user explicitly asks for a saved release report, write to `outputs/reviews/release-coordinator/YYYY-MM-DD_release-vX.Y.Z.md`.

## Hard stops (never proceed past these)

- `scan` finds personal data patterns in files staged for commit → block release, report all findings
- Version file (`pyproject.toml`) not found → block release
- Remote `origin` or `metis-ph` not configured → block sync/release, provide setup command
- Any file in the propagation list contains PH-specific or personal content → block sync

## Never

- Push directly from a personal/local installation to any public remote
- Propagate `release-coordinator/` agent files to any public remote
- Propagate any `*-context.md` file to any public remote
- Propagate `user-preferences.json`, `user-config.yaml`, or any `.sqlite` file
- Amend or force-push a tag that has already been pushed to a remote
- Skip the personal data scan before any push operation
- Write to `basket/private/` or read from it
