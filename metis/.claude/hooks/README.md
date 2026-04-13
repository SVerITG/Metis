# Metis Security Hooks

## pre-tool-use.mjs

Fires automatically before every `WebFetch`, `WebSearch`, `Bash`, `Write`, and `Edit` call.

### What it checks

| Check | Tools | Action |
|-------|-------|--------|
| Domain not on allowlist | WebFetch | Warning shown to user |
| Prompt injection in URL/query | WebFetch, WebSearch | **Blocked** |
| Sensitive path in file write | Write, Edit | Warning shown to user |
| Network call in Bash (curl/wget) | Bash | Warning shown to user |
| Sensitive path in Bash command | Bash | Warning shown to user |
| Destructive `rm -rf` in RC root | Bash | **Blocked** |

### Behaviour

- **Warnings** (⚠️) — shown in stderr before the tool runs. The user sees them and can stop if needed.
- **Blocks** — the tool does not run; the user sees the reason and an alternative.

### Allowlist

Edit the `ALLOWED_DOMAINS` array at the top of `pre-tool-use.mjs` to add trusted domains.

### Sensitive paths

Edit the `SENSITIVE_PATH_PATTERNS` array to add or remove path patterns that trigger data protection warnings.
