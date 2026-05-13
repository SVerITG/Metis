---
name: Add Context
description: "add context, add specialist context, I'm also working on, add a new area, update my profile, I want Metis to know I also do, add domain, expand my profile, new research area, new specialty"
model: claude-haiku-4-5-20251001
effort: normal
complexity: quick
---

## Purpose

Adds a new specialist context to the user's Metis profile (`system/user-config.yaml`) without re-running the full `/metis_config` wizard. Keeps the profile current as the user's work evolves.

## What to do when invoked

**Step 1 — Gather information** (ask in one message):
- Context name: short label (e.g. "Epidemiological dashboards", "HAT surveillance mapping")
- Description: 1-2 sentences about what this covers and why it matters to the user's work
- Active in brainstorm sessions by default? (yes/no)

**Step 2 — Read current config:**
Read `system/user-config.yaml`.

If the file has a `specialist_contexts:` section, append the new entry.
If not, create the section.

New entry format:
```yaml
  - name: [context name]
    description: "[1-2 sentence description]"
    active: [true|false]
    added: [YYYY-MM-DD]
```

If user said yes to brainstorm default, also add the slug to `active_contexts:` list.

**Step 3 — Write updated config:**
Write the updated YAML back to `system/user-config.yaml`.

**Step 4 — Confirm:**
Reply with:
```
Added '[context name]' to your Metis profile.

Active in brainstorm sessions: [Yes / No — toggle in Ideas tab]
Available to: all agents (loaded when relevant)

Your specialist contexts:
[list all contexts with bullet points]

To remove or edit: open system/user-config.yaml or run /metis_config
```

## Edge cases
- `user-config.yaml` doesn't exist yet: create it with minimal structure (name, role, specialist_contexts).
- Context already exists with same name: ask whether to update the description or keep both.
- User provides a very long description: summarise to 2 sentences, show the shortened version and ask to confirm.
- User says "active by default" but no `active_contexts` key exists: create it.
