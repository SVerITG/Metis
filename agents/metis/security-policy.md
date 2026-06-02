# Metis System — Security and Data Protection Policy

**Scope:** All agents operating within the Metis second-brain system
**Derived from:** Ruflo v3.5 security module + local-first RC principles
**Applies to:** Metis, Software Engineer, Dashboard Engineer, Librarian, Meeting Memory, News Radar, and all specialist agents

---

## 1. Data Classification

| Class | Examples | Rule |
|-------|---------|------|
| **SENSITIVE** | Individual case records, patient identifiers, GPS coordinates of cases | Never expose individually; aggregate only; never send to external services |
| **CONFIDENTIAL** | Meeting notes, delegation decisions, personal research judgements | Local storage only; do not sync to cloud services without explicit consent |
| **INTERNAL** | Literature metadata, project notes, code, analysis scripts | Local by default; GitHub with `.gitignore` protection for data files |
| **PUBLIC** | Published papers, public news, WHO data, GitHub-hosted code | Can be shared, cached, and cited freely |

---

## 2. Local-First Principle

- **Default: all data stays local.** Nothing leaves the machine without explicit user decision.
- The only agents with internet permission are:
  - **Librarian** — literature search and metadata retrieval only
  - **News Radar** — public news and RSS feeds only
- Meeting Memory, PHD Architect, Writing Partner, Methods Coach, Dashboard Engineer, Software Engineer: **no internet access without explicit permission per task**.

---

## 3. Code Security Rules

These rules apply to all code reviewed or produced by Software Engineer and Dashboard Engineer. The system is Python (MCP server + FastAPI dashboard) over SQLite.

### SQL
- Parameterised queries only — `?` placeholders via `system/app-py/db.py` helpers / `sqlite3` (`con.execute("... WHERE x = ?", (val,))`)
- Never f-string or concatenate user input into SQL
- Enforced in `db.py` and the MCP tool DB helpers

### File system
- Resolve paths through `metis_mcp.config.paths`; never accept user-typed absolute paths unvalidated
- Constrain reads/writes to known roots (RC root, library, outputs); refuse `basket/private/`
- Use `pathlib.resolve()` and confirm the path stays within the allowed root

### External commands
- `subprocess` without `shell=True`; never interpolate user-controlled strings into a command
- Open only DB-sourced or hardcoded/allowlisted URLs (Cybersecurity validates) — never raw user-typed input

### Secrets
- API keys, database passwords, authentication tokens: always in `system/.env` (loaded from env), never hardcoded
- `.env` is in `.gitignore` — never committed
- No secrets in any source file (the release scan blocks `sk-ant-` prefixes and key assignments)

### Templates / UI (FastAPI + HTMX + Jinja2)
- Rely on Jinja2 autoescaping; never disable it for user-generated content and never `| safe` raw user/scraped text
- Endpoints returning partials must escape any external content before rendering
- File upload inputs must validate type and size before processing

### Python-specific
- No `eval()` / `exec()` on user input — ever
- No dynamic import from user-controlled names

---

## 4. Privacy Rules for Research Data

- **Research surveillance data** (case counts, health zone data) is **SENSITIVE**
  - Display aggregate statistics only (counts by zone × year)
  - Never display records with identifiable fields (patient ID, date + location combination)
  - The research dashboard must enforce this at the data layer, not the UI layer

- **Meeting content** is **CONFIDENTIAL**
  - Audio files stay in `outputs/reviews/meeting-memory/` — local only
  - Transcripts are local by default; never auto-uploaded to cloud transcription services
  - Meeting notes containing names or decisions: treat as CONFIDENTIAL

- **Literature PDFs** are **INTERNAL**
  - PDFs stored locally in `knowledge/library/` — not re-distributed
  - Metadata (title, DOI, abstract) can be shared; full text cannot

---

## 5. Agent-Specific Rules

| Agent | Internet | Sensitive data | External services |
|-------|---------|---------------|------------------|
| Metis | ✗ | Routes only | None |
| Software Engineer | ✗ | Code review | None |
| Dashboard Engineer | ✗ | Aggregated only | None |
| Librarian | ✓ (literature only) | No patient data | Pubmed, DOI, preprint servers |
| Meeting Memory | ✗ | Confidential | None (local Whisper only) |
| News Radar | ✓ (news only) | No personal data | RSS, public APIs |
| PhD Architect | ✗ | Aggregated/published | None |
| Writing Partner | ✗ | Published/aggregated | None |
| Methods Coach | ✗ | Aggregated/published | None |
| Presentation Maker | ✗ | Aggregated/published | None |
| Builder | ✗ | Depends on task | Ask permission |
| News Aggregator | ✓ (RSS/public feeds) | No personal data | RSS, public news APIs |
| UX Engineer | ✗ | No | None |
| Epidemiologist | ✗ | Aggregated/published | None |
| Cybersecurity | ✗ | Reviews outbound requests | None (deliberately isolated) |
| Data Guardian | ✗ | Scans for PII/sensitive data | None (pre-submit filtering) |

---

## 6. When to Escalate

Escalate to the user before proceeding if:
- A task requires sending data to an external API (even metadata)
- A new external tool or service is being integrated
- A file path is being passed directly from user input to a system call
- Data from a SENSITIVE class is requested for a new purpose
- A new database table will store personally identifiable information

---

## 7. Derived from Ruflo v3.5

The following Ruflo security module components informed this policy:
- `@claude-flow/security` — Input validation (Zod), path traversal prevention (PathValidator), command injection protection (SafeExecutor)
- `SECURITY.md` — vulnerability reporting policy, parameterized SQL, secrets management
- `CLAUDE.md` — no secrets in source, no hardcoded paths, multi-layer input validation

**Ruflo swarm** should be invoked for security audits of externally-deployed apps (see Software Engineer system prompt for commands).
