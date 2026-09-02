#!/usr/bin/env python3
"""Harvest figures, maps and plates from the HAT books already in Metis' library.

the researcher, 2026-08-28: *"historical epidemiological maps like some books in metis'
library"*. He was right that the gap was there and right about where to look —
the `hat-specialist` layer holds 221 documents including the WHO HAT Atlas, the
WHO control-and-surveillance manual in English AND French, a land-cover-mapping
volume for tsetse, and colonial-medicine histories. None of it had been mined
for images.

NAMED BY THE NEAREST CAPTION, not by guesswork. PyMuPDF gives each image's
bounding box; the caption is the text block directly below it (or above, for
plates). That is the same principle that made the PowerPoint harvest reliable:
let the document say what the picture is.

LICENCE IS RECORDED PER SOURCE AND IS NOT UNIFORM. The Atlas is CC BY; the WHO
manuals are WHO-copyright, reusable for non-commercial teaching with attribution;
a book chapter is neither. Every row says which, because "I found it in my own
folder" is not a licence.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, "/home/<user>/.local/share/metis-mcp/.venv/lib/python3.12/site-packages")
import fitz  # PyMuPDF

RC = Path("/mnt/c/Users/<user>/OneDrive/Documents/7. Software/Research Cortex")
LIB = Path("/mnt/c/Users/<user>/OneDrive/Documents/2. HAT disease/5. Presentations/Content")

MIN_PX = 90_000        # ~300x300 — below this it is a rule, an icon or a logo
MIN_BYTES = 15_000

# (path fragment, tag, licence, credit, default folder, default prefix, lang)
SOURCES = [
    ("Simarro_Atlas_of_HAT_2010", "SimarroAtlas2010",
     "CC BY 2.0 (open access)",
     "Simarro et al. 2010, Int J Health Geogr — CC BY 2.0",
     "Image/22_Historical_and_Atlas_Maps", "AtlasMap", "EN"),
    ("WHO-HAT-TRS-984-Control-Surveillance-2013", "WHO_TRS984_2013",
     "WHO copyright — non-commercial teaching use with attribution",
     "WHO Technical Report Series 984 (2013)",
     "Image/24_WHO_Manual_Figures", "WHOManual", "EN"),
    ("Trypanosomiase-humaine-africaine-lutte-et-survei", "WHO_TRS984_2014_FR",
     "WHO copyright — non-commercial teaching use with attribution",
     "OMS, Série de Rapports techniques 984 (2014, version française)",
     "Image/24_WHO_Manual_Figures", "WHOManual", "FR"),
    ("Standardizing_land_cover_mapping_for_tsetse", "LandCover2008",
     "Check before external use — FAO/PAAT technical document",
     "Standardizing land cover mapping for tsetse and trypanosomiasis (2008)",
     "Image/20_Environment_and_Habitat", "Environment", "EN"),
    ("Montero_The-Legacy-of-Colonial-Medicine", "Montero2021",
     "Check before external use — journal article, licence not verified",
     "Montero 2021, The legacy of colonial medicine in Central Africa",
     "Image/21_Historical_Treatments_and_Campaigns", "HistoricalCampaign", "EN"),
    ("since_1885", "CentralAfrica1885",
     "Book chapter — INTERNAL USE ONLY, do not publish externally",
     "Health in Central Africa since 1885, chapter 17",
     "Image/21_Historical_Treatments_and_Campaigns", "HistoricalCampaign", "EN"),
    ("Rapport_Annuel_2023_PNLTHA_RDC", "PNLTHA_RDC_2023",
     "PNLTHA-RDC national programme report — internal / programme use",
     "PNLTHA-RDC, Rapport annuel 2023",
     "Image/08_Clinical_Data_Graphs", "DataAndMaps", "FR"),
    ("Kabeya_-_Facteurs_socioculturels", "Kabeya_Socioculturel",
     "Thesis — check before external use",
     "Kabeya, Facteurs socioculturels et contrôle de la THA",
     "Image/25_Community_and_Sociocultural", "Community", "FR"),
]

# Caption keyword -> (folder, prefix). Checked in order; first match wins.
# These are the NEW categories the gap analysis identified, plus redirects into
# existing folders when a figure clearly belongs there.
ROUTES: list[tuple[str, str, list[str]]] = [
    ("Image/22_Historical_and_Atlas_Maps", "AtlasMap",
     [r"\bmap\b", r"\bcarte\b", r"distribution", r"r[eé]partition", r"atlas",
      r"foyer", r"focus(es)? of", r"geo(graphic|referenc)", r"village.?level",
      r"endemic(ity)?", r"prevalence map"]),
    ("Image/20_Environment_and_Habitat", "Environment",
     [r"land ?cover", r"vegetation", r"habitat", r"riverine", r"gallery forest",
      r"galerie", r"savanna", r"forest", r"land ?use", r"satellite", r"ndvi",
      r"remote sensing", r"rainfall", r"temperature", r"climate", r"paysage",
      r"eau", r"water point", r"riv(er|i[eè]re)", r"palm", r"plantation",
      r"ecolog", r"[eé]colog"]),
    ("Image/23_Animal_Reservoirs_OneHealth", "AnimalReservoir",
     [r"\bpig\b", r"porc", r"cattle", r"bovin", r"b[eé]tail", r"livestock",
      r"nagana", r"reservoir", r"r[eé]servoir", r"animal trypanosom",
      r"\bdog\b", r"chien", r"wildlife", r"faune", r"antelope", r"warthog"]),
    ("Image/21_Historical_Treatments_and_Campaigns", "HistoricalCampaign",
     [r"atoxyl", r"tryparsamide", r"suramin", r"germanin", r"bayer 205",
      r"arsenic", r"colonial", r"jamot", r"mass (screening|treatment|campaign)",
      r"campagne", r"histor", r"19[0-5][0-9]", r"lomidine", r"pentamidin[ei]sation"]),
    ("Image/26_Diagnostics_Serology_Molecular", "DiagnosticsSeroMol",
     [r"ielisa", r"i-elisa", r"trypanolys", r"\btl\b", r"\bpcr\b", r"\blamp\b",
      r"serolog", r"s[eé]rolog", r"elisa", r"antibod", r"anticorps",
      r"filter paper", r"papier filtre", r"dried blood"]),
    ("Image/14_Procedures_Sampling", "Procedure",
     [r"lumbar puncture", r"ponction lombaire", r"lymph node", r"ganglion",
      r"blood sampl", r"pr[eé]l[eè]vement", r"venipuncture", r"finger.?prick",
      r"capillary", r"centrifug", r"microhematocrit", r"woo"]),
    ("Image/12_Treatment_Regimens", "Treatment",
     [r"melarsoprol", r"m[eé]larsoprol", r"fexinidazole", r"nifurtimox",
      r"eflornithine", r"pentamidine", r"nect", r"treatment schedule",
      r"sch[eé]ma th[eé]rapeutique", r"dosage", r"posologie"]),
    ("Image/03_Vector_Control", "VectorControl",
     [r"\btrap\b", r"pi[eè]ge", r"tiny target", r"[eé]cran", r"screen",
      r"insecticide", r"spray", r"sterile insect", r"aerial"]),
    ("Image/02_Vector_Tsetse", "VectorTsetse",
     [r"glossina", r"tsetse", r"ts[eé].?ts[eé]", r"mouche", r"\bfly\b", r"puparium"]),
    ("Image/01_Parasite_Biology", "ParasiteBiology",
     [r"trypanosom[ae]", r"parasite", r"life ?cycle", r"cycle de vie",
      r"trypomastigote", r"vsg", r"variant surface"]),
    ("Image/11_Diagnostic_Algorithms", "DiagnosticAlgorithm",
     [r"algorithm", r"algorithme", r"decision tree", r"arbre de d[eé]cision",
      r"flow ?chart", r"organigramme"]),
    ("Image/08_Clinical_Data_Graphs", "DataAndMaps",
     [r"number of cases", r"nombre de cas", r"trend", r"tendance", r"reported cases",
      r"cas d[eé]clar", r"incidence", r"coverage", r"couverture", r"screened",
      r"d[eé]pist"]),
    ("Image/13_Clinical_Presentation", "ClinicalPresentation",
     [r"patient", r"clinical", r"clinique", r"sympt", r"stage [12]", r"stade [12]",
      r"winterbottom", r"oedema", r"chancre", r"sleep pattern", r"polysomnog"]),
]


def deaccent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def camel(s: str, n: int = 54) -> str:
    w = re.findall(r"[A-Za-z0-9]+", deaccent(s or ""))
    stop = {"the", "a", "an", "of", "in", "on", "at", "and", "or", "with", "from", "for",
            "by", "to", "is", "de", "la", "le", "les", "du", "des", "et", "en", "un",
            "une", "sur", "pour", "au", "aux", "dans", "par", "figure", "fig", "table",
            "map", "carte", "source"}
    k = [x for x in w if x.lower() not in stop] or w
    return ("".join(x[:1].upper() + x[1:] for x in k))[:n] or "Untitled"


def route(caption: str, default: tuple[str, str]) -> tuple[str, str]:
    hay = deaccent(caption or "").lower()
    for folder, prefix, pats in ROUTES:
        if any(re.search(p, hay) for p in pats):
            return folder, prefix
    return default


def caption_for(page, bbox) -> str:
    """Nearest caption-looking text block. Below first, then above.

    A figure caption in a scientific PDF sits directly under the graphic and
    usually opens with Figure/Fig./Table/Map/Carte. Preferring a block that
    starts that way, and only then falling back to plain proximity, keeps body
    text from being mistaken for a caption.
    """
    blocks = [b for b in page.get_text("blocks") if len(b) >= 5 and (b[4] or "").strip()]
    cands = []
    for x0, y0, x1, y1, txt, *_ in blocks:
        t = re.sub(r"\s+", " ", txt).strip()
        if len(t) < 12:
            continue
        below = y0 >= bbox.y1 - 6
        above = y1 <= bbox.y0 + 6
        if not (below or above):
            continue
        dist = (y0 - bbox.y1) if below else (bbox.y0 - y1)
        if dist > 190:
            continue
        looks = bool(re.match(r"(figure|fig\.?|table|tableau|map|carte|plate|planche)\b",
                              t, re.I))
        cands.append((0 if looks else 1, 0 if below else 1, dist, t))
    if not cands:
        return ""
    cands.sort()
    return cands[0][3][:300]


def main() -> None:
    state = json.loads((LIB / "_library_state.json").read_text())
    known, rejected = state["media_hashes"], state.get("rejected_hashes", {})
    rows: list[dict] = []
    counts: dict[str, int] = {}

    pdfs = {p.name: p for p in list(RC.rglob("*.pdf"))}
    for frag, tag, lic, credit, dfolder, dprefix, lang in SOURCES:
        match = [p for n, p in pdfs.items() if frag.lower() in n.lower()]
        if not match:
            print(f"! not found: {frag}")
            continue
        src = match[0]
        try:
            doc = fitz.open(src)
        except Exception as exc:
            print(f"! {src.name}: {exc}")
            continue
        print(f"\n═══ {tag} — {doc.page_count} pp — {src.name[:56]} ═══")
        got = 0
        for pno in range(doc.page_count):
            page = doc[pno]
            for img in page.get_images(full=True):
                xref = img[0]
                try:
                    rects = page.get_image_rects(xref)
                    bbox = rects[0] if rects else None
                    pix = fitz.Pixmap(doc, xref)
                except Exception:
                    continue
                if pix.width * pix.height < MIN_PX:
                    continue
                if pix.n - pix.alpha >= 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                try:
                    data = pix.tobytes("png")
                except Exception:
                    continue
                if len(data) < MIN_BYTES:
                    continue
                h = hashlib.md5(data).hexdigest()
                if h in known or h in rejected:
                    continue
                cap = caption_for(page, bbox) if bbox else ""
                folder, prefix = route(cap, (dfolder, dprefix))
                label = camel(cap) if cap else f"Page{pno+1:03d}"
                name = f"{prefix}_{label}_{lang}_{tag}_p{pno+1:03d}.png"
                dst = LIB / folder / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                k = 2
                while dst.exists():
                    dst = dst.with_name(f"{prefix}_{label}_{lang}_{tag}_p{pno+1:03d}_{k}.png")
                    k += 1
                dst.write_bytes(data)
                known[h] = str(dst.relative_to(LIB))
                counts[folder] = counts.get(folder, 0) + 1
                got += 1
                rows.append({
                    "file": str(dst.relative_to(LIB)),
                    "category": folder.split("/")[-1], "language": lang,
                    "caption": cap[:300], "source_document": src.name,
                    "source_tag": tag, "page": pno + 1,
                    "licence": lic, "credit_line": credit,
                    "px": f"{pix.width}x{pix.height}", "bytes": len(data),
                })
                if got <= 6 or got % 25 == 0:
                    print(f"   + p{pno+1:03d} {folder.split('/')[-1][:26]:26s} "
                          f"{pix.width}x{pix.height}  {cap[:52]}")
        print(f"   → {got} images")
        doc.close()

    if rows:
        man = LIB / "_BOOKS_FIGURES_MANIFEST.csv"
        exists = man.exists()
        with man.open("a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), extrasaction="ignore")
            if not exists:
                w.writeheader()
            w.writerows(rows)
        (LIB / "_library_state.json").write_text(json.dumps(state, indent=1))

    print("\n" + "=" * 62)
    for f, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {f}")
    print(f"\n{len(rows)} images filed from {len(SOURCES)} source documents")


if __name__ == "__main__":
    main()
