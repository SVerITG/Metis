# Background Maker — Agent Contract

## Inputs

| Field | Required | Description |
|---|---|---|
| `topic` | yes | Domain or topic to build a background for (e.g. "health economics", "disease epidemiology") |
| `depth` | no | `survey` (default) / `deep` / `exhaustive` |
| `layer_name` | no | Custom slug for the layer (auto-derived from topic if not given) |
| `source_types` | no | `papers,reports,web,rss` (default: all) |

## Outputs

| File | Description |
|---|---|
| `knowledge/domains/{layer}/layer-meta.yaml` | Layer metadata: name, doc count, topics, dates, source breakdown |
| `knowledge/domains/{layer}/README.md` | One-paragraph human summary of what the layer covers |
| `knowledge/domains/{layer}/paywalled.md` | List of DOIs that were paywalled (provide OA alternatives where found) |
| `knowledge/domains/{layer}/failed.md` | List of sources that failed to harvest (404, timeout, etc.) |
| SQLite (vector store) | Indexed chunks in `vec_pdf_chunks` + `library_fulltext` via MCP tools |

## Postconditions

- Layer is queryable via `search_fulltext(query, layer="{layer-name}")` immediately after build
- `layer-meta.yaml` exists and is valid YAML
- All indexed content passed Data Guardian scrub
- No personal data (PII, credentials, patient data) in the index

## Failure modes

| Failure | Behaviour |
|---|---|
| Source unavailable (404/timeout) | Log to `failed.md`, continue |
| Paywall | Log to `paywalled.md`, skip indexing, continue |
| Data Guardian flags content | Quarantine to `knowledge/domains/{layer}/quarantine/`, skip indexing |
| Vector store full | Report to user, suggest pruning old layers |
| User interrupts | Save manifest + progress state so the build can be resumed |
