# Metis Domain Packs

Metis ships as a domain-agnostic research platform. A **domain pack** adds the
specialist knowledge, tuned prompts, and example projects for a specific field —
without touching the base codebase.

---

## What is a domain pack?

The base Metis installation gives you:

- 34 specialist agents with generic, field-neutral system prompts
- 165+ MCP tools covering literature, data, news, code, and research workflow
- A FastAPI dashboard with 9 tabs
- RAG infrastructure (sqlite-vec, nomic-embed-text) ready to index any PDF corpus
- The constitution, red-lines, and persona contract templates
- The `/metis_config` wizard, which personalises names, interests, and monitoring topics

What base Metis does **not** include is knowledge. It knows nothing about your disease
area, your methodology, your field's jargon, or the specific databases you monitor.
That is what a domain pack adds.

A domain pack is a thin layer on top of base Metis:

```
base Metis
└── domain pack
    ├── knowledge/library/{your-domain}/      PDFs, indexed background papers
    ├── system/config/user-config.yaml.example  Field-specific defaults
    ├── agents/{agent}/system-prompt-tuning.md  Optional prompt refinements
    └── example projects                        PLANNING.md templates, demo data
```

Domain packs live in their own repositories (or forks). They pull in base Metis as
a dependency and add their layer on top. Installing a domain pack is exactly like
installing base Metis — the same setup script, the same wizard — but with richer
defaults and pre-loaded knowledge.

---

## Metis_PH — the reference domain pack

**Metis_PH** is the Public Health and Epidemiology edition. It was built alongside
base Metis and serves as the reference implementation for what a domain pack looks like.

### What Metis_PH includes

**Knowledge layers** (indexed at install time via the Background Maker agent):

| Layer | Contents |
|---|---|
| Epidemiology foundations | Study design, causal inference, surveillance methodology |
| Global health | WHO frameworks, burden estimation, UHC indicators |
| NTD / HAT reference (example) | Disease area PDFs seeded by the installer |
| DHIS2 documentation | Technical docs, API reference, metadata design guides |
| Health information systems | HMIS frameworks, data quality, routine data methods |

**Agent prompt tuning:**

| Agent | Tuning added |
|---|---|
| Epidemiologist | Emphasis on surveillance evaluation and observational designs |
| Methods Coach | Multilevel models, spatial analysis, disease burden estimation |
| DHIS2 Expert | Full DHIS2 tracker, metadata, and NTD implementation context |
| Librarian | PubMed, WHO IRIS, OpenAlex, AfricArXiv source priority |
| News Radar | WHO NTD updates, DHIS2 releases, global health policy signals |

**Field-specific user-config defaults:**

The `user-config.yaml.example` shipped with Metis_PH pre-fills the `research.field`
with "Public Health · Epidemiology" and seeds example interests, compliance settings
(GDPR, ethics), and news monitoring topics relevant to the field.

**Example projects:**

- PhD thesis scaffold (article-based thesis, three papers structure)
- Surveillance study design template
- DHIS2 NTD module implementation tracker

### What Metis_PH is NOT

Metis_PH does not contain patient data, unpublished results, or personal research
files from any individual researcher. The knowledge layers contain only publicly
available documents (WHO guidelines, open-access papers, DHIS2 documentation).

---

## How to build your own domain pack

You have two options: fork an existing pack, or build from base Metis.

### Option A: Fork Metis_PH (recommended for health researchers)

1. Fork the Metis_PH repository to your own GitHub account.
2. Run the installer: `bash system/install/setup-mcp.sh`
3. Run `/metis_config` to personalise names, interests, and monitoring topics.
4. Use `/background-maker` to add knowledge PDFs for your specific area.
5. Commit your domain layer (knowledge index, tuned prompts) to your fork.

### Option B: Build from base Metis

1. Fork the base Metis repository.
2. Create a `knowledge/library/{your-domain}/` folder and add your PDFs.
3. Run `index_missing_pdfs()` to build the vector index.
4. Copy `system/config/user-config.yaml.example` and tune the defaults for your field.
5. Optionally edit agent system prompts in `agents/{agent}/system-prompt.md` to add
   field-specific methodology notes (keep the base structure — add a "Domain context"
   section at the top).
6. Add `docs/DOMAIN-PACKS.md` (or update it) describing what your pack includes.
7. Publish as a new repository named `Metis_{YourDomain}`.

### Step-by-step: adding a knowledge layer

```bash
# 1. Drop PDFs into the staging folder
cp ~/Downloads/who-guideline-2024.pdf knowledge/library/{your-domain}/

# 2. Index them (run from within Claude Code or call directly)
/background-maker add knowledge/library/{your-domain}/

# 3. Verify indexing
# The MCP tool index_missing_pdfs() will log how many chunks were added.
# Check the Knowledge tab in the dashboard to confirm they appear.
```

### Step-by-step: tuning an agent prompt

Each agent has a `system-prompt.md` file at `agents/{agent-slug}/system-prompt.md`.
The safe way to tune it for your domain is to add a clearly marked block near the top,
rather than rewriting the whole prompt:

```markdown
## Domain context (added by {YourDomain} pack)

You are operating in the context of {your field}. Key terminology:
- {term}: {plain-English definition}

Preferred sources for this domain:
- {journal or database 1}
- {journal or database 2}

When reviewing study designs, pay particular attention to:
- {domain-specific methodological concern}
```

This approach survives base Metis upgrades: when the base prompt is updated, your
domain block is easy to re-apply.

---

## What belongs in base Metis (never in a domain pack)

| Component | Where it lives |
|---|---|
| All 34 agent generic system prompts | `agents/{slug}/system-prompt.md` |
| All 165+ MCP tools | `system/mcp-server/src/metis_mcp/tools/` |
| FastAPI dashboard (all 9 tabs) | `system/app-py/` |
| Constitution and red-lines | `system/config/constitution.md`, `system/config/red-lines.md` |
| Persona contract template | `system/config/metis-persona.example.md` |
| User config template | `system/config/user-config.yaml.example` |
| RAG infrastructure (sqlite-vec, nomic) | `system/mcp-server/src/metis_mcp/tools/rag.py` |
| Installer and setup scripts | `system/install/` |
| Claude Code skills | `.claude/skills/` |
| Core documentation | `docs/`, `README.md` |

If a change is useful to any researcher in any field, it belongs in base Metis.
If it only makes sense for a specific field, it belongs in a domain pack.

---

## What belongs in a domain pack

| Component | Notes |
|---|---|
| Knowledge PDFs and their vector index | Never committed to git — generated at install time |
| `knowledge/library/{your-domain}/` structure | Folder scaffold can be committed; PDFs cannot |
| Domain-specific agent prompt tuning | Additive blocks only — do not rewrite base prompts |
| Field-specific `user-config.yaml.example` | Shows relevant defaults for new users in the field |
| Example `PLANNING.md` templates | For common project types in the field |
| Field-specific seeding scripts | `system/install/seed_{domain}.py` |
| Domain README additions | Notes on field-specific setup steps |

---

## Naming convention

Domain pack repositories follow the pattern `Metis_{Domain}`:

| Pack | Repository | Field |
|---|---|---|
| Metis_PH | `{username}/Metis_PH` | Public Health / Epidemiology |
| Metis_Econ | `{username}/Metis_Econ` | Health Economics / Development Economics |
| Metis_Env | `{username}/Metis_Env` | Environmental Science / Climate |
| Metis_Clin | `{username}/Metis_Clin` | Clinical Research / Medicine |

You are welcome to name your fork anything you like. The `Metis_` prefix is a convention,
not a requirement.
