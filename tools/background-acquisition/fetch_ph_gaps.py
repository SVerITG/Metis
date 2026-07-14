#!/usr/bin/env python3
"""Download open-access PH-background gap documents and stage them for indexing.

Fills the coverage gaps found in the ph-background knowledge layer (2026-07-14):
authoritative WHO/global-health strategies the layer was missing. Downloads each
into the correct open-access-books/<category>/ folder that build_pdf_knowledge_db
already reads, validates it's a real PDF, and reports per-file status.

Never raises on a single failure — a dead URL is logged and the rest proceed.
"""
import sys
from pathlib import Path

import httpx

import os
ROOT = Path(os.environ.get("METIS_RC_ROOT") or Path(__file__).resolve().parents[2])
LIB = ROOT / "knowledge" / "library" / "open-access-books"

# (category folder, filename, url, tags)
DOCS = [
    ("Infectious Disease & Surveillance", "WHO_Global_Vector_Control_Response_2017-2030.pdf",
     "https://iris.who.int/server/api/core/bitstreams/68d92417-dd44-437d-bb8b-2befb7bdc732/content",
     "vector-control,vector-borne,ntd,who-strategy"),
    ("Infectious Disease & Surveillance", "WHO_Global_Technical_Strategy_Malaria_2016-2030_2021update.pdf",
     "https://cdn.who.int/media/docs/default-source/malaria/gts/who-global-technical-strategy-for-malaria-update-4apr2021.pdf?sfvrsn=ba276833_8",
     "malaria,who-strategy,elimination"),
    ("Infectious Disease & Surveillance", "WHO_World_Malaria_Report_2024.pdf",
     "https://www.mmv.org/sites/default/files/content/document/Worldmalariareport2024_EN.pdf",
     "malaria,surveillance,burden,who-report"),
    ("Infectious Disease & Surveillance", "WHO_Immunization_Agenda_2030_Framework.pdf",
     "https://cdn.who.int/media/docs/default-source/immunization/strategy/ia2030/ia2030_frameworkforactionv04.pdf?sfvrsn=e5374082_1&download=true",
     "immunization,ia2030,who-strategy"),
    ("Environmental & Occupational Health", "WHO_Global_Strategy_WASH_and_NTDs_2021-2030.pdf",
     "https://iris.who.int/server/api/core/bitstreams/5e900a5c-a51e-44b0-9849-a11ecb9757ea/content",
     "wash,ntd,water-sanitation,who-strategy"),
    ("Health Systems & Financing", "WHO_Global_Strategy_HRH_Workforce_2030.pdf",
     "https://www.afro.who.int/sites/default/files/2017-07/global-strategy-on-hrh-english.pdf",
     "health-workforce,health-systems,hrh,who-strategy"),
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Metis Research Cortex; background-maker)"}


def main() -> int:
    ok = fail = 0
    for category, fname, url, tags in DOCS:
        dest_dir = LIB / category
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / fname
        if dest.exists() and dest.stat().st_size > 10_000:
            print(f"  ✓ already present: {category}/{fname} ({dest.stat().st_size//1024} KB)")
            ok += 1
            continue
        try:
            with httpx.Client(verify=False, follow_redirects=True, timeout=120,
                              headers=HEADERS) as c:
                r = c.get(url)
            if r.status_code != 200:
                print(f"  ✗ HTTP {r.status_code}: {fname}  ({url[:60]})")
                fail += 1
                continue
            body = r.content
            if not body[:5].startswith(b"%PDF"):
                print(f"  ✗ not a PDF (got {body[:16]!r}): {fname}")
                fail += 1
                continue
            dest.write_bytes(body)
            print(f"  ✓ downloaded: {category}/{fname} ({len(body)//1024} KB)")
            ok += 1
        except Exception as e:
            print(f"  ✗ error {type(e).__name__}: {fname} — {e}")
            fail += 1
    print(f"\n  {ok} downloaded/present, {fail} failed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
