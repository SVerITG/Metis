"""Store the runbook FILE as procedural memory #8, so the two cannot drift.

Two different clients reach this content by two different paths:
  * get_agent_context("methods-coach")  → reads the .md file
  * semantic_search(layers="procedural") → reads procedural_memory
Writing it twice by hand is how the last inventory went stale. Generated instead.
"""
import sqlite3, datetime, pathlib, sys
RC = pathlib.Path("/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex")
src = RC / "agents/methods-coach/risk-mapping-runbook-context.md"
body = src.read_text(encoding="utf-8")

db="/home/sverschaeve/.local/share/metis/metis.sqlite"
con=sqlite3.connect(db, timeout=120.0); con.execute("PRAGMA busy_timeout=120000")
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
steps = (f"*Generated from `agents/methods-coach/risk-mapping-runbook-context.md` "
         f"on {now[:10]}. Edit that file, then re-run tools/sync_runbook.py — "
         f"do not hand-edit this record, or the two will disagree.*\n\n" + body)

con.execute("""UPDATE procedural_memory
   SET steps=?, trigger_context=?, procedure_name=? WHERE id=8""",
  (steps,
   "'Do the risk mapping for <country>', 'risk map for Angola/DRC/…', a request for "
   "HAT risk areas, foci delineation, cross-border transmission analysis, or "
   "risk-area change over time — usually with a path to a case dataset. Also: "
   "repeating the DRC/Angola analysis for a new country. Covers the full runbook: "
   "interview, the 10-script country pipeline, the 3-year cross-border pipeline, "
   "validation checks and known traps.",
   "Run HAT risk mapping for a country (full runbook, incl. cross-border)"))
con.commit()
n,L=con.execute("SELECT procedure_name, length(steps) FROM procedural_memory WHERE id=8").fetchone()
print(f"#8 → {n}\n     {L} chars, synced from {src.name}")
con.close()
