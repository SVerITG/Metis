# Scanner Rules — Personal Data Patterns

This file contains the compiled pattern list used by the Release Coordinator's personal data scanner. Every pattern here must be checked against any file before it is pushed to a public GitHub remote.

Patterns are grouped by category. Use regex where marked `(regex)`. All others are literal string matches (case-sensitive unless otherwise noted).

---

## Category: Names

| ID | Pattern | Type | Notes |
|---|---|---|---|
| N1 | `[Ss]tan\b` | regex | First name, case-insensitive, word boundary |
| N2 | `Verschaeve` | literal | Family name |
| N3 | `sverschaeve` | literal | Lowercase username form |
| N4 | `S\.V\.` | regex | Initials with escaped dots |
| N5 | `Stan V` | literal | Partial name (name + initial) |

---

## Category: Email

| ID | Pattern | Type | Notes |
|---|---|---|---|
| E1 | `@itg\.be` | regex | Institutional email domain |
| E2 | `sverschaeve@` | literal | Email address prefix |

---

## Category: Institution

| ID | Pattern | Type | Notes |
|---|---|---|---|
| I1 | `Institute of Tropical Medicine` | literal | Full institutional name |
| I2 | `\bITG\b` | regex | Abbreviation — word boundaries required. **Skip if inside a variable name, import path, or code comment.** |

**ITG false-positive exclusions (do not flag):**
- Variable names: `METIS_RC_ROOT`, `ANTHROPIC_API_KEY`, any `_ITG_` or `ITG_` prefixed identifier
- Import statements: any line beginning with `import` or `from`
- Lines beginning with `#` (comments)
- `.gitignore` entries
- `README.md` (authored public framing)

---

## Category: Local paths

| ID | Pattern | Type | Notes |
|---|---|---|---|
| P1 | `/mnt/c/Users/sverschaeve` | literal | WSL path |
| P2 | `C:\\Users\\sverschaeve` | literal | Windows backslash path |
| P3 | `C:/Users/sverschaeve` | literal | Windows forward-slash path |
| P4 | `OneDrive - ITG` | literal | OneDrive folder name |

**Exception:** `.gitignore` lines that contain these patterns are intentional exclusions — do not flag them.

---

## Category: Credentials and API keys

| ID | Pattern | Type | Notes |
|---|---|---|---|
| K1 | `sk-ant-[a-zA-Z0-9]` | regex | Anthropic API key prefix |
| K2 | `ANTHROPIC_API_KEY\s*=\s*sk-` | regex | Hardcoded key assignment |

---

## Category: Personal data references

| ID | Pattern | Type | Notes |
|---|---|---|---|
| D1 | `metis\.sqlite` combined with path containing `sverschaeve` or `OneDrive` | compound | SQLite path pointing to personal data location |
| D2 | `(my article\|my thesis)\s+[A-Z]` | regex | Personal work references in non-documentation files (`.md` in `docs/` or `README.md` are exempt) |

---

## Global exceptions — never flag

The following are always permitted regardless of category:

| Exception | Rationale |
|---|---|
| `SVerITG` | Public GitHub username — appears in remote URLs, README badges, etc. |
| `Stan` in a test fixture `name = "Stan"` or equivalent placeholder context | Clearly not personal data |
| `ITG` inside a variable or identifier name | Not a reference to the institution |
| Any line in `.gitignore` | Intentionally references private paths |
| Any line in `README.md` that is clearly authored public framing | Not private data |
| Lines inside `# comment` or `// comment` blocks containing N1–N5 where context is clearly fictional/placeholder | Use judgment |

---

## Severity levels

| Severity | When | Action |
|---|---|---|
| 🔴 BLOCK | K1, K2 (credentials) or P1–P4 (local paths) | Hard stop. Do not push. Report file:line. |
| 🔴 BLOCK | N2 (`Verschaeve`), E1, E2 (email), I1 (institution full name) | Hard stop. Do not push. Report file:line. |
| ⚠️ WARN | N1, N3–N5 (name variants) where context is ambiguous | Warn and request user confirmation before proceeding. |
| ⚠️ WARN | I2 (`\bITG\b`) outside exception categories | Warn. Likely fine but worth confirming. |
| ⚠️ WARN | D1, D2 (personal data references) | Warn. Likely in a config or comment — confirm before push. |

---

## Scanner behaviour

1. Read each file in scope as plain text.
2. For each line, test against all patterns in order.
3. Apply exceptions before flagging.
4. Collect findings as: `{ file, line_number, pattern_id, matched_text }`.
5. Output as a table sorted by file, then line number.
6. Report severity per finding.
7. Aggregate: if any 🔴 finding exists, block the operation and require user action before re-running.
