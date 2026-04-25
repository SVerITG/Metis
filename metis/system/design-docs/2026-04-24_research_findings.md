# Research Findings — 2026-04-24

Two research questions commissioned by the user during the editorial redesign session.

---

## 1. PDF-Extract-Kit evaluation — **SKIP**

**Question:** Should Metis scraper agents (Content Harvester, Librarian, News Aggregator) adopt OpenDataLab's `PDF-Extract-Kit`?

### Verdict
SKIP. The repo has been **effectively abandoned** — last release v1.0.0 in Oct 2024. OpenDataLab's attention has moved to **MinerU** (v3.1.4, 2026-04-24, 61k stars, 157 releases), which wraps the same models in a cleaner Markdown/JSON CLI.

### What PDF-Extract-Kit does
Modular pipeline: DocLayout-YOLO for layout, UniMERNet for formulas → LaTeX, PaddleOCR+TableMaster for tables, PaddleOCR for OCR. Output = structured blocks with bounding boxes. Built for papers / textbooks / reports.

### Install cost
Python 3.10 only (clashes with our 3.12 venv — would need a sibling venv), PyTorch + PaddlePaddle + YOLO (~15–25 GB models), GPU recommended, known dependency-resolution headaches on Windows/WSL.

### Recommended path for Metis
| Layer | Tool | Why |
|---|---|---|
| **Default** | PyMuPDF | 95% of cases: clean text + biblio metadata, fast, pure Python |
| **Tables/formulas fallback** | **Docling (IBM)** | Py 3.12 compatible, 97.9% table accuracy, 2x faster than alternatives, clean Markdown output, active 2025-2026 |
| **Heavy OCR (optional)** | MinerU | Only if we start ingesting many scanned WHO surveillance PDFs |

**Action item**: do not install PDF-Extract-Kit. Consider adding Docling to Librarian as a secondary parser when PyMuPDF fails on tables.

---

## 2. Agentic OS — field survey + gap analysis

### Three schools of thought
1. **Kernel school** — "agents as the primitive" (AIOS arXiv 2403.16971, Letta). LLM = CPU, memory is tiered (core/recall/archival), tools = syscalls. Academic, architectural.
2. **Orchestration school** — "layer over existing OSes" (Slack Agentic OS, Microsoft 365 Copilot agents, Markovate). Coordination + governance + connectors. Pragmatic, enterprise.
3. **Replacement school** — "death of Windows" (Rabbit R1, Humane AI Pin). Hardware/UX bet, mostly failed commercially.

### Real-world systems worth watching
- **AIOS (agiresearch)** — open-source LLM kernel: scheduler + context manager + memory/storage/tool managers. The most literal "OS".
- **Letta (ex-MemGPT)** — "LLM-as-OS" with tiered memory (core/recall/archival), git-backed memory, skills, subagents.
- **OpenAI ChatGPT Agent / GPT-5.5** — cloud-sandboxed agent with browser+terminal; 82.7% Terminal-Bench 2.0, 78.7% OSWorld.
- **Claude Computer Use / Claude Code / Skills** — local-first CLI + screen control; skills = portable capability bundles; MCP = tool protocol.
- **LangGraph / CrewAI / AutoGen** — frameworks, not OSes (no scheduling, no kernel).
- **Microsoft 365 Copilot + Agent Builder** — closest "enterprise agentic OS" shipping at scale.

### What Metis already does well (vs the field)
- Domain-native agent roster (epidemiologist, phd-architect, librarian, writing-partner)
- Local-first + OneDrive-portable
- Data-guardian + constitution + injection-probe — stronger safety than any popular framework
- Research-specific UX (Teach tab, PhD focus kanban)
- Reflexive memory + reflexions — rare outside academic papers

### What Metis is missing
- **OS-style scheduling** (no kernel deciding which agent gets the LLM)
- **Self-editing memory** — we have episodic/semantic/procedural but agents can't update core memory autonomously
- **Standards-based observability** — no OpenTelemetry gen_ai spans, no trace replay
- **Fork/branch exploration** — no way to spawn N speculative agent branches and commit the winner
- **Computer-use / browser driving** — can't fill a PubMed web form beyond MCP
- **Skills registry with signing** — no versioning, discovery, or SHA verification
- **Eval harness** — no regression suite; silent degradation is possible when tweaking prompts

### Prioritized recommendations (for Phase 9+)

1. **OpenTelemetry gen_ai spans for agent_spans table** — replaces planned Phase 5.9. Emit OTel spans for every agent run, tool call, LLM invocation. Lets us swap in LangSmith/Langfuse later without rewrites. **High ROI, already on roadmap.**
2. **Formalize memory tiers à la Letta** — rename layers to *core / recall / archival*. Add a self-editing `memory_update` MCP tool so agents promote/demote facts. Unlocks "agents that learn over time".
3. **Eval harness** — YAML suite of ~20 canned research prompts per agent, run nightly, store pass/fail in `agent_evals` table, show regressions on Metis tab. Prevents silent prompt degradation — nobody else in our research space has this.
4. **Scoped browser-use agent** via Playwright + MCP (allowlist: PubMed, WHO, bioRxiv, ECDC). Not general computer use — domain-scoped, auditable by cybersecurity + data-guardian.
5. **Skills registry with frontmatter + SHA signing** — each `/metis_*` skill gets version, author, signature, changelog. Prep for publishing Metis as a template for public-health research peers.

### Deprioritize
- Fork/branch OS primitives (academic, premature)
- Full computer-use (security cost > benefit)
- Replacing Windows (not the goal)

---

### References

- AIOS paper: https://arxiv.org/abs/2403.16971
- Letta (ex-MemGPT): https://www.letta.com/
- AgenticOS 2026 Workshop CFP: https://os-for-agent.github.io/
- OTel AI Agent Observability: https://opentelemetry.io/blog/2025/ai-agent-observability/
- Docling paper: https://arxiv.org/pdf/2501.17887
- MinerU: https://github.com/opendatalab/MinerU
