#!/usr/bin/env python3
"""Enrich the thin hat-specialist (5 docs) and ntd (5 docs) knowledge layers with
open-access HAT/NTD literature matched to the researcher's work (gambiense HAT surveillance,
elimination monitoring, spatial mapping, DRC)."""
import sys
from pathlib import Path
import httpx

import os
ROOT = Path(os.environ.get("METIS_RC_ROOT") or Path(__file__).resolve().parents[2])
OAB = ROOT / "knowledge" / "library" / "open-access-books"

def plos(doi_tail: str) -> str:
    return f"https://journals.plos.org/plosntds/article/file?id=10.1371/journal.pntd.{doi_tail}&type=printable"

# (category folder, filename, url, tags)  — HAT → deep personal layer; NTD → program layer
DOCS = [
    # ── hat-specialist (open-access-books/HAT) ──
    ("HAT", "Franco_2024_Monitoring_HAT_elimination_roadmap_targets.pdf", plos("0012111"),
     "hat,gambiense,elimination,surveillance,who-roadmap"),
    ("HAT", "Franco_HAT_elimination_the_long_last_mile.pdf", plos("0012091"),
     "hat,gambiense,elimination,surveillance"),
    ("HAT", "Simarro_Atlas_of_HAT_2010.pdf", "https://www.fao.org/4/article/am015e.pdf",
     "hat,atlas,spatial-epi,mapping"),
    ("HAT", "Buscher_Human_African_Trypanosomiasis_Lancet_Seminar_2017.pdf",
     "https://e.itg.be/MTM/ihealth/vector/2.pdf", "hat,clinical,review,seminar"),
    ("HAT", "Davis_2019_Village-scale_persistence_elimination_gHAT.pdf", plos("0007838"),
     "hat,gambiense,persistence,elimination,modelling"),
    # ── ntd (open-access-books/NTDs) — HAT-elimination program knowledge fits here too ──
    ("NTDs", "WHO_3rd_Stakeholders_Meeting_gHAT_Elimination.pdf", plos("0006925"),
     "ntd,hat,gambiense,elimination,who"),
    ("NTDs", "Franco_Monitoring_HAT_elimination_update_to_2016.pdf", plos("0006890"),
     "ntd,hat,surveillance,monitoring"),
]
H = {"User-Agent": "Mozilla/5.0 (Metis Research Cortex; background-maker)"}

def main() -> int:
    ok = fail = 0
    for cat, fname, url, _tags in DOCS:
        d = OAB / cat; d.mkdir(parents=True, exist_ok=True); dest = d / fname
        if dest.exists() and dest.stat().st_size > 10_000:
            print(f"  ✓ present: {cat}/{fname}"); ok += 1; continue
        try:
            with httpx.Client(verify=False, follow_redirects=True, timeout=120, headers=H) as c:
                r = c.get(url)
            if r.status_code != 200:
                print(f"  ✗ HTTP {r.status_code}: {fname}"); fail += 1; continue
            if not r.content[:5].startswith(b"%PDF"):
                print(f"  ✗ not a PDF ({r.content[:12]!r}): {fname}"); fail += 1; continue
            dest.write_bytes(r.content)
            print(f"  ✓ downloaded: {cat}/{fname} ({len(r.content)//1024} KB)"); ok += 1
        except Exception as e:
            print(f"  ✗ error {type(e).__name__}: {fname}"); fail += 1
    print(f"\n  {ok} ok, {fail} failed")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
