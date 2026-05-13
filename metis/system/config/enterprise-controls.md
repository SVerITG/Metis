# Metis — Enterprise Controls

**Document status:** Active  
**Applies to:** Institutional deployments of the Metis Research Cortex (v1.0+)  
**Maintained by:** System administrator or IT department deploying Metis  

This document specifies the governance framework for deploying Metis to research teams in
institutional settings (universities, research institutes, public health agencies). It covers
data classification, access controls, escalation procedures, and audit requirements.

---

## Data classification policy

Metis operates across four data classification tiers:

| Tier | Label | Description | Examples |
|---|---|---|---|
| 1 | PUBLIC | Can leave the institution without restriction | Published papers, WHO reports, news items |
| 2 | INTERNAL | Circulates within the institution but not externally | Draft manuscripts, project notes, meeting summaries |
| 3 | CONFIDENTIAL | Restricted to named individuals or teams | Unpublished findings, grant applications, personnel notes |
| 4 | SENSITIVE | Highest protection — individual-level or patient data | Patient records, trial participant data, GPS coordinates |

**Classification is automatic.** The Metis pipeline (Stage 2) classifies every input before
routing it. Tier 3 generates a warning. Tier 4 is blocked by default — it cannot be passed
to any agent or external API.

### Data-at-rest rules

- Patient data (Tier 4) must NEVER reside in the Research Cortex root folder.
- `basket/private/` is the only permitted location for personal/participant data held locally.
  No agent may read files from this location.
- `inbox/` is a processing staging area. Files dropped here are logged and classified.
  Sensitive files should be reviewed and moved before they are routed.

---

## Access controls

### Single-user deployment (default)

Metis is designed for personal use. The database, outputs, and journal are owned by the
researcher and stored in their user profile. No multi-user access is implemented.

### Institutional deployment considerations

When deploying Metis to a shared environment (shared server, Docker, multi-user WSL):

1. **Separate databases per user.** Set `METIS_DB` to a per-user path. Do not share a single
   SQLite file across users.
2. **API key isolation.** Each user's `ANTHROPIC_API_KEY` must be stored in their own `.env`
   file, not a shared environment variable.
3. **Inbox isolation.** Set `METIS_RC_ROOT` per user so each inbox is private.
4. **Audit logging.** Enable the PostToolUse hook profile (`METIS_HOOK_PROFILE=full`) for
   all sessions involving research data.

---

## Agent behaviour rules (institutional)

Agents operating in an institutional deployment must follow these constraints in addition to
the base `system/config/red-lines.md`:

1. **No external transmission of Tier 3+ data.** Agents may not send CONFIDENTIAL or SENSITIVE
   content to any API endpoint, including Claude, unless the user has explicitly approved this
   action in the current session.
2. **No bulk export.** Agents may not query the full contents of the `literature_metadata`,
   `meetings`, or `ideas` tables and transmit them externally.
3. **No credential relay.** Agents may not read `.env` files or environment variables and
   include their values in any output or API call.
4. **Audit trail required.** Every substantive agent run must produce an entry in the
   `agent_runs` table. Runs that fail to log may indicate a hook bypass — investigate.

---

## Escalation procedures

### Low-severity events (warn)

- Domain not on allowlist during WebFetch
- Potential PII in tool output (post-tool-use hook fires)
- Sensitive path written during Write/Edit

**Action:** Review in next session using `/security-scan`. No immediate action required.

### Medium-severity events (investigate)

- Injection pattern fired in pre-tool-use hook
- Tier 3 (CONFIDENTIAL) data classified in an agent request

**Action:** Pause the current session. Run `/security-scan`. Check outputs directory for any
transmitted content. Report to your institution's data protection officer if CONFIDENTIAL
research data may have been processed externally.

### High-severity events (block + report)

- Tier 4 (SENSITIVE) data classified — pipeline blocks automatically
- Three or more injection patterns in the same session — hook blocks with reason
- `rm -rf` targeting the RC root — hook blocks automatically

**Action:** Do not continue the session. Export the session log from
`journal/sessions/session-YYYY-MM-DD.jsonl`. Report to your institution's information
security team. Preserve the log for investigation.

---

## Audit requirements

### Session logs

The PostToolUse hook writes a JSONL entry for every tool call:
```
journal/sessions/session-YYYY-MM-DD.jsonl
```

Retain these files for a minimum of 90 days when processing research data. Do not delete
session logs from sessions involving external data (web fetches, API calls, file uploads).

### Handoff briefs

The Stop hook writes a session-end summary:
```
journal/sessions/handoff-YYYY-MM-DD-HH-MM.md
```

These provide a human-readable record of what was done in each session. Retain alongside
session logs.

### Database backup

The nightly backup job copies `metis.sqlite` to `system/app/data/backups/`. Retain at
minimum the last 30 daily backups. For production institutional deployments, mirror the
backup directory to institutional storage.

### Periodic review

IT or system administrators deploying Metis institutionally should schedule a quarterly
review of:
- Active API keys (rotate annually or on staff departure)
- Domain allowlist in `pre-tool-use.mjs` (add/remove as research scope changes)
- Agent run history for anomalous volumes (>200 runs/day may indicate misconfiguration)
- Backup integrity (test a restore from the most recent backup)

---

## Compliance notes

Metis is research software, not a clinical system. It is not certified for HIPAA, GDPR
regulated health data processing, or clinical trial data management. Researchers working
with data subject to these regulations must:

1. Confirm with their DPO that Metis's data flows are permissible under their data
   processing agreement with Anthropic.
2. Ensure that only de-identified or synthetic data enters the Research Cortex.
3. Document the legal basis for processing in their research protocol.

The Data Guardian agent (`/data-guardian`) is available to assess specific data handling
questions. Its findings are advisory — final decisions rest with the researcher and their DPO.
