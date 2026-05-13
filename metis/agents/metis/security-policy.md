# Metis System — Security and Data Protection Policy

**Scope:** All agents operating within the Metis second-brain system
**Derived from:** Ruflo v3.5 security module + local-first RC principles
**Applies to:** Metis, Software Engineer, Dashboard Engineer, Librarian, Meeting Memory, News Radar, and all specialist agents

---

## 1. Data Classification

| Class | Examples | Rule |
|-------|---------|------|
| **SENSITIVE** | Individual HAT case records, patient identifiers, GPS coordinates of cases | Never expose individually; aggregate only; never send to external services |
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

These rules apply to all code reviewed or produced by Software Engineer and Dashboard Engineer:

### SQL
- Parameterised queries only (`DBI::dbExecute(con, "... ?", params = list(...))`)
- Never concatenate user input into SQL strings
- ✓ Already enforced in `data_store.R`

### File system
- All file paths normalised with `normalizePath()` before use
- Paths constrained to known roots (`paths$second_brain_root`, `paths$data_root`, etc.)
- Never accept user-typed paths directly without validation

### External commands
- `system2()` and `system()` must never include user-controlled strings without sanitisation
- `browseURL()` only with DB-sourced or hardcoded URLs (not user-typed input)
- Shell commands in `run_script()` use `Rscript` with a known script path — no dynamic command injection

### Secrets
- API keys, database passwords, authentication tokens: always in `.env` files
- `.env` files in `.gitignore` — never committed
- No secrets in `app.R`, `data_store.R`, or any sourced R file

### Shiny UI
- `renderUI()` must never inject unsanitised user text as raw HTML
- `HTML()` with user-generated content is forbidden without `htmltools::htmlEscape()`
- File upload inputs must validate file type and size before processing

### R-specific
- No `eval(parse(text = user_input))` — ever
- `source()` only with known, controlled file paths

---

## 4. Privacy Rules for Research Data

- **HAT surveillance data** (case counts, health zone data) is **SENSITIVE**
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
