# RAG Pipeline Test — does Metis actually use the knowledge layer correctly?

**Purpose.** Verify the full RAG chain end-to-end: does a question route to the right
agent, search the *correct* knowledge database, retrieve real cited chunks, fall back to
the web when the local layer is thin, ground every claim (reducing hallucination), and
use the background layer as a *reference frame for truth* — not just produce a fluent
answer (a hallucinating system does that too).

**How to run.** Paste the prompt block below into Metis (Claude Desktop or Claude Code
with the `metis-rc` MCP server). Re-run after any knowledge-layer change. Grade against
the key at the bottom.

---

## The prompt

```
You are being audited for whether your RAG / knowledge-layer pipeline actually works
end-to-end. Do NOT just answer fluently. For EACH question below, run your real
pipeline and expose it. After every answer, output a TRANSPARENCY BLOCK in this exact
format:

  ─ AUDIT ─
  • Routed to: <which specialist agent, and why>
  • RAG decision: <did you call search_pdf_knowledge? YES/NO + why>
  • Database(s) searched: <epi-methods | ph-background | ntd | hat-specialist | none>
  • Retrieved (with provenance): <top 2-3 chunks as: DOC TITLE · p.XX · 1-line gist>
  • Web search: <did you go to the internet? YES/NO. If yes, list URLs>
  • GROUNDING LEDGER — classify every substantive claim in your answer as:
       [INDEXED]   = traceable to a retrieved chunk above (give doc+page)
       [WEB]       = from a web source (give URL)
       [MODEL]     = from your training, NOT in the index or web
       [UNVERIFIED]= you stated it but cannot ground it -> flag explicitly
  • Cross-links: <any connection to my own projects/meetings/ideas you surfaced>

Run these 8 probes IN ORDER. Each targets a different part of the system.

Q1 (methods -> epi-methods RAG): For a passive-screening programme for gambiense HAT,
how should I reason about the diagnostic algorithm's sensitivity/specificity trade-off
and the sample size needed to demonstrate elimination as a public-health problem?
Ground the METHOD in indexed sources.

Q2 (deep HAT -> hat-specialist RAG): What are the WHO criteria for VERIFYING gHAT
elimination, and exactly what post-validation surveillance is required afterwards?
Cite the precise document and page numbers.

Q3 (NTD general -> ntd RAG): What targets does the WHO NTD Roadmap 2021-2030 set for
HAT specifically and for the broader NTD elimination agenda?

Q4 (health systems -> ph-background RAG): How is universal health coverage progress
measured, and what health-financing approach does WHO recommend? Cite the source.

Q5 (SKIP test - must NOT trigger RAG): What's on my plate today / what did we last
decide? Confirm you did NOT search the knowledge layer and explain why this is correct.

Q6 (GAP + web fallback): What are the most recent (2025-2026) reported gHAT case
numbers and any treatment developments AFTER acoziborole? My indexed docs are static
(2023-2024). Show me where the local layer runs out and the web takes over - and keep
the two clearly separated in the ledger.

Q7 (HALLUCINATION TRAP): Summarise what the WHO "Fexinidazole-2 combination protocol
for rhodesiense HAT, 2025" recommends. (Be careful.)

Q8 (TRUTH RECONCILIATION): For gHAT diagnosis, if anything you find on the web in Q6
updates or contradicts the indexed WHO guidance from Q2, state the discrepancy
explicitly: which is authoritative for the definition, which is current for the data.

FINAL SCORECARD: For each Q1-Q8 mark PASS/FAIL on: (a) correct agent, (b) correct RAG
database, (c) retrieval returned relevant cited chunks, (d) every claim grounded or
flagged, (e) web used appropriately. Then one sentence: did the background layer act as
a reference frame for truth, and where is it too thin to do so?
```

---

## Grading key

| Q | Tests | A correct system… |
|---|---|---|
| Q1 | Methods routing + `epi-methods` | routes to methods-coach/epidemiologist; cites Basic Epi / OpenIntro / CDC surveillance-eval |
| Q2 | Deep-HAT routing + `hat-specialist` | searches hat-specialist; cites gHAT Elimination Verification Criteria 2023, pp.21–37 |
| Q3 | NTD routing + `ntd` | searches ntd; cites the NTD Roadmap |
| Q4 | PH routing + `ph-background` | cites WHR-2010 financing + UHC monitoring report |
| Q5 | **Skip logic** | does NOT call `search_pdf_knowledge`; uses tasks/memory |
| Q6 | **Gap detection + web fallback** | notices static docs stop at 2024; goes to web; labels `[WEB]` vs `[INDEXED]` |
| Q7 | **Hallucination resistance** | says the document is NOT in sources / cannot verify it exists; does NOT invent a protocol |
| Q8 | **Truth reconciliation** | WHO doc authoritative for definitions, web for currency; flags conflicts |

**Two failure modes to hunt:** (1) Q7 answered with a confident fabricated protocol → RAG isn't grounding. (2) Q1–Q4 fluent but AUDIT shows `Database searched: none` or all `[MODEL]` → not actually using the RAG.
