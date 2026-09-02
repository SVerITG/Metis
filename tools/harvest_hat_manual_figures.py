#!/usr/bin/env python3
"""Caption-driven extraction from the WHO TRS 984 manuals, EN and FR.

WHY DRIVEN BY CAPTIONS AND NOT BY IMAGES. The first attempt walked the embedded
images and looked for a caption near each one. Of 24 large images in the English
volume it filed 6, because an image whose caption sits slightly out of reach was
dropped rather than mis-filed — a defensible rule that produced a 75% loss.

Inverting it fixes that. These manuals number every exhibit ("Figure 2.2
Distribution of human African trypanosomiasis, 2000-2009"), so the captions are a
complete, human-written index of what is worth taking: 21 in EN, 28 in FR. Walk
THAT, and take whatever sits above each one — an embedded bitmap if there is one,
a render of the vector drawing if there is not.

Tables get taken twice, on purpose: as a PNG for dropping on a slide, and as a
CSV, because "Nombre total de cas nouveaux ... par pays" is data and a picture of
data cannot be replotted.
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
import fitz

RC = Path("/mnt/c/Users/<user>/OneDrive/Documents/7. Software/Research Cortex")
LIB = Path("/mnt/c/Users/<user>/OneDrive/Documents/2. HAT disease/5. Presentations/Content")
SRC = RC / "inputs/literature/sleeping-sickness"
SOURCES = [
    (SRC / "2013_Geneva_Control-and-surveillance-of-human-African-trypanos.pdf", "WHO_TRS984_EN", "EN"),
    (SRC / "2014_Santé_Trypanosomiase-humaine-africaine-lutte-et-survei.pdf", "WHO_TRS984_FR", "FR"),
]
LICENCE = "WHO copyright — non-commercial teaching use with attribution"
CREDIT = ("WHO/OMS Technical Report Series 984 · Control and surveillance of human "
          "African trypanosomiasis (2013 EN / 2014 FR)")
TABLE_DIR = "Image/16_Tables_Extracted/WHO_Manual_TRS984"
FIG_DEFAULT = "Image/24_WHO_Manual_Figures"

CAP_RE = re.compile(r"^\s*(figure|fig\.?|tableau|table|carte|planche|plate|encadr[eé]|box)\s*"
                    r"(\d+(?:\.\d+)*)", re.I)

# Word-boundary anchored throughout. `eau` as a bare substring matched
# "nouv-eau-x" and sent a case-trend chart to Habitat; in French that class of
# error also hits bureau, niveau, réseau, plateau, tableau.
ROUTES: list[tuple[str, str, list[str]]] = [
    ("Image/11_Diagnostic_Algorithms", "DiagnosticAlgorithm",
     [r"\balgorithm(e|es)?\b", r"arbre de d[eé]cision", r"organigramme", r"flow ?chart"]),
    ("Image/26_Diagnostics_Serology_Molecular", "DiagnosticsSeroMol",
     [r"\bi-?elisa\b", r"trypanolys", r"\belisa\b", r"\bpcr\b", r"\blamp\b",
      r"s[eé]rolog", r"serolog", r"\banticorps\b", r"antibod", r"papier[- ]filtre",
      r"filter paper", r"dried blood"]),
    ("Image/05_Diagnostics_mAECT", "DiagnosticsMAECT",
     [r"\bmaect\b", r"mini[- ]?anion", r"mini[- ]?colonne", r"[eé]change d.anions"]),
    ("Image/04_Diagnostics_CATT", "DiagnosticsCATT",
     [r"\bcatt\b", r"\btdr\b", r"\brdt\b", r"agglutination", r"test de d[eé]pistage"]),
    ("Image/14_Procedures_Sampling", "Procedure",
     [r"ponction", r"lumbar puncture", r"lymph node", r"\bganglion", r"suc ganglionnaire",
      r"pr[eé]l[eè]vement", r"blood sampl", r"\bcapillar", r"centrifug",
      r"microh[eé]matocrite", r"\bqbc\b", r"goutte [eé]paisse", r"thick (blood )?film"]),
    ("Image/12_Treatment_Regimens", "Treatment",
     [r"m[eé]larsoprol", r"melarsoprol", r"fexinidazole", r"nifurtimox",
      r"[eé]flornithine", r"eflornithine", r"pentamidine", r"\bnect\b",
      r"\bposologie\b", r"sch[eé]ma th[eé]rapeutique", r"treatment schedule",
      r"\btraitement\b", r"\btreatment\b", r"\bdrug", r"m[eé]dicament"]),
    ("Image/21_Historical_Treatments_and_Campaigns", "HistoricalCampaign",
     [r"\batoxyl\b", r"tryparsamide", r"\bsuramin(e)?\b", r"germanin", r"bayer 205",
      r"\barsenic", r"\blomidine\b", r"colonial", r"\bjamot\b",
      r"campagne de masse", r"mass campaign"]),
    ("Image/23_Animal_Reservoirs_OneHealth", "AnimalReservoir",
     [r"\bporc(s|in)?\b", r"\bpig(s)?\b", r"\bbovin(s)?\b", r"\bcattle\b",
      r"\bb[eé]tail\b", r"livestock", r"\bnagana\b", r"r[eé]servoir", r"reservoir",
      r"\bchien(s)?\b", r"\bdog(s)?\b", r"\bfaune\b", r"wildlife",
      r"animal trypanosom", r"trypanosomose animale", r"\bh[oô]te(s)?\b", r"\bhost(s)?\b"]),
    ("Image/03_Vector_Control", "VectorControl",
     [r"\bpi[eè]ge(s)?\b", r"\btrap(s)?\b", r"tiny target", r"[eé]cran(s)? impr",
      r"insecticide", r"pulv[eé]risation", r"insecte st[eé]rile", r"sterile insect",
      r"lutte antivectorielle", r"vector control"]),
    ("Image/02_Vector_Tsetse", "VectorTsetse",
     [r"\bglossin", r"\bts[eé]?[- ]?ts[eé]\b", r"\btsetse\b", r"puparium",
      r"proboscis", r"\btrompe\b"]),
    ("Image/20_Environment_and_Habitat", "Environment",
     [r"couverture (du sol|terrestre)", r"land ?cover", r"land ?use", r"v[eé]g[eé]tation",
      r"vegetation", r"\bhabitat\b", r"galerie foresti", r"gallery forest", r"riverine",
      r"\bfor[eê]t\b", r"\bforest\b", r"savane\b", r"savann", r"\bpaysage\b",
      r"landscape", r"point d.eau\b", r"water point", r"\brivi[eè]re\b", r"\briver\b",
      r"\bpalmeraie\b", r"plantation", r"[eé]cologi", r"ecolog", r"t[eé]l[eé]d[eé]tection",
      r"remote sensing", r"satellite", r"\bndvi\b", r"pluviom[eé]tri", r"rainfall", r"climat"]),
    ("Image/22_Historical_and_Atlas_Maps", "AtlasMap",
     [r"\bcarte\b", r"\bmap\b", r"r[eé]partition g[eé]ographique",
      r"distribution g[eé]ographique", r"geographic(al)? distribution", r"\batlas\b",
      r"\bfoyer(s)?\b", r"\bfocus(es)?\b", r"end[eé]mi", r"endemic",
      r"\bdistribution\b", r"niveaux de risque", r"risk level"]),
    ("Image/08_Clinical_Data_Graphs", "DataAndMaps",
     [r"nombre (total )?de cas", r"number of cases", r"cas nouveaux", r"new cases",
      r"cas d[eé]clar", r"reported cases", r"\b[eé]volution\b", r"\btendance",
      r"\btrend", r"incidence", r"couverture\b", r"coverage", r"d[eé]pist",
      r"screened", r"pr[eé]valence", r"prevalence", r"population expos",
      r"population at risk", r"superficie"]),
    ("Image/13_Clinical_Presentation", "ClinicalPresentation",
     [r"\bpatient", r"\bclinique\b", r"\bclinical\b", r"sympt", r"\bsigne(s)?\b",
      r"stade [12]", r"stage [12]", r"winterbottom", r"\bœd[eè]me\b", r"\bchancre\b",
      r"sommeil", r"\bsleep\b", r"polysomnog"]),
    ("Image/07_Laboratory", "Laboratory",
     [r"microscop", r"\blame(s)?\b", r"\bcentrifugeuse\b", r"\bcolorat", r"\bgiemsa\b",
      r"laboratoire", r"laboratory", r"\br[eé]actif", r"reagent"]),
    ("Image/01_Parasite_Biology", "ParasiteBiology",
     [r"trypanosom[ae]", r"\bparasite", r"cycle (de vie|biologique|de transmission)",
      r"life[- ]?cycle", r"trypomastigote", r"\bvsg\b", r"variant surface",
      r"triangle [eé]pid[eé]miologique", r"epidemiological triangle", r"classification"]),
    ("Image/15_Forms_and_Reporting", "Form",
     [r"\bfiche\b", r"\bformulaire\b", r"\bregistre\b", r"\bregister\b", r"rapportage",
      r"reporting", r"\bcahier\b"]),
]

TRAPS = {"Evolution des nouveaux cas THA rapportes": "Image/20_Environment_and_Habitat",
         "Tableau de bord du bureau national": "Image/20_Environment_and_Habitat",
         "Le reseau au niveau provincial": "Image/20_Environment_and_Habitat"}


def deaccent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def camel(s: str, n: int = 56) -> str:
    w = re.findall(r"[A-Za-z0-9]+", deaccent(s or ""))
    stop = {"the", "a", "an", "of", "in", "on", "at", "and", "or", "with", "from", "for",
            "by", "to", "is", "de", "la", "le", "les", "du", "des", "et", "en", "un",
            "une", "sur", "pour", "au", "aux", "dans", "par", "figure", "fig", "table",
            "tableau", "carte", "source", "qui", "ou"}
    k = [x for x in w if x.lower() not in stop] or w
    return ("".join(x[:1].upper() + x[1:] for x in k))[:n] or "Untitled"


def route(caption: str):
    hay = deaccent(caption or "").lower()
    for folder, prefix, pats in ROUTES:
        if any(re.search(p, hay) for p in pats):
            return folder, prefix
    return None


def self_test() -> None:
    bad = [f"{t!r}->{f}" for t, f in TRAPS.items()
           if (r := route(t)) and r[0] == f]
    if bad:
        sys.exit("ROUTING SELF-TEST FAILED: " + "; ".join(bad))
    assert route("Figure 2.2 Distribution of human African trypanosomiasis (HAT), 2000-2009")[0] \
        == "Image/22_Historical_and_Atlas_Maps"
    assert route("Figure 3.3 Life-cycle of trypanosomes")[0] == "Image/01_Parasite_Biology"
    print("routing self-test passed")


def main() -> None:
    self_test()
    state = json.loads((LIB / "_library_state.json").read_text())
    known, rejected = state["media_hashes"], state.get("rejected_hashes", {})
    rows, counts, n_csv = [], {}, 0

    for src, tag, lang in SOURCES:
        if not src.exists():
            print(f"! missing {src.name}"); continue
        doc = fitz.open(src)
        print(f"\n═══ {tag} — {doc.page_count} pp ═══")
        got = 0
        for pno in range(doc.page_count):
            page = doc[pno]
            blocks = [b for b in page.get_text("blocks") if len(b) >= 5 and (b[4] or "").strip()]
            caps = []
            for b in blocks:
                t = re.sub(r"\s+", " ", b[4]).strip()
                m = CAP_RE.match(t)
                if m and len(t) > 16:
                    caps.append((t[:300], fitz.Rect(b[0], b[1], b[2], b[3]),
                                 m.group(1).lower()))
            if not caps:
                continue

            imgs = []
            for im in page.get_images(full=True):
                try:
                    rs = page.get_image_rects(im[0])
                    if rs:
                        imgs.append((im[0], rs[0]))
                except Exception:
                    pass
            tables = []
            try:
                tables = list(page.find_tables().tables)
            except Exception:
                pass

            for cap, crect, kind in caps:
                is_table = kind.startswith(("tableau", "table"))
                # region: everything between the previous block's bottom and the caption
                above = [b[3] for b in blocks if b[3] <= crect.y0 - 4]
                top = max(above) if above else page.rect.y0 + 20
                if is_table:
                    top = page.rect.y0 + 20          # tables run tall; take the page band
                region = fitz.Rect(page.rect.x0 + 10, min(top, crect.y0 - 8),
                                   page.rect.x1 - 10, crect.y0 - 2)
                if not is_table and region.height < 90:
                    # nothing usable above the caption — this document titles its
                    # figures from the top, so look downwards instead
                    below = [b[1] for b in blocks if b[1] >= crect.y1 + 6]
                    bot = min(below) if below else page.rect.y1 - 20
                    region = fitz.Rect(page.rect.x0 + 10, crect.y1 + 2,
                                       page.rect.x1 - 10, max(bot, crect.y1 + 100))
                if is_table:
                    region = fitz.Rect(page.rect.x0 + 10, crect.y1 + 2,
                                       page.rect.x1 - 10, page.rect.y1 - 20)
                r = route(cap) or ((TABLE_DIR, "WHOTable") if is_table
                                   else (FIG_DEFAULT, "WHOManualFigure"))
                folder, prefix = r
                if is_table:
                    folder = TABLE_DIR if folder == FIG_DEFAULT else folder

                # a table's numbers as CSV — a picture of data cannot be replotted
                if is_table and tables:
                    best = max(tables, key=lambda t: fitz.Rect(t.bbox).get_area()
                               if fitz.Rect(t.bbox).intersects(region) else 0)
                    if fitz.Rect(best.bbox).intersects(region):
                        try:
                            data = [[(c or "").strip() for c in row] for row in best.extract()]
                        except Exception:
                            data = []
                        if len([r2 for r2 in data if any(r2)]) >= 3:
                            out = LIB / TABLE_DIR / f"WHOTable_{camel(cap, 48)}_{lang}_{tag}_p{pno+1:03d}.csv"
                            out.parent.mkdir(parents=True, exist_ok=True)
                            if not out.exists():
                                with out.open("w", newline="", encoding="utf-8") as fh:
                                    csv.writer(fh).writerows([r2 for r2 in data if any(r2)])
                                n_csv += 1

                # The picture. Take the nearest embedded bitmap in EITHER
                # direction, because this manual puts figure titles ABOVE the
                # figure while journals put captions below — and I built the
                # first version on the journal convention, which returned 0 of 21
                # figures while the tables (searched downwards) worked fine. Same
                # document, two opposite assumptions, one of them untested.
                pick = None
                if not is_table:
                    cands = []
                    for xref, bb in imgs:
                        if bb.get_area() <= 8000:
                            continue
                        if bb.y0 >= crect.y1 - 8:          # image below the title
                            gap = bb.y0 - crect.y1
                        elif bb.y1 <= crect.y0 + 8:        # image above the caption
                            gap = crect.y0 - bb.y1
                        else:
                            continue
                        if gap < 160:
                            cands.append((gap, xref, bb))
                    if cands:
                        cands.sort(key=lambda c: c[0])
                        pick = (cands[1], cands[2]) if False else (cands[0][1], cands[0][2])
                if pick is None:
                    for xref, bb in imgs:
                        inter = bb & region
                        if inter.get_area() > 0.45 * bb.get_area() and bb.get_area() > 8000:
                            pick = (xref, bb); break
                data = None
                px = None
                if pick and not is_table:
                    try:
                        p2 = fitz.Pixmap(doc, pick[0])
                        if p2.n - p2.alpha >= 4:
                            p2 = fitz.Pixmap(fitz.csRGB, p2)
                        if p2.width * p2.height >= 60_000:
                            data, px = p2.tobytes("png"), p2
                    except Exception:
                        pass
                if data is None:
                    if region.width < 110 or region.height < 80:
                        continue
                    try:
                        p2 = page.get_pixmap(clip=region, dpi=190)
                        data, px = p2.tobytes("png"), p2
                    except Exception:
                        continue
                if not data or len(data) < 9_000:
                    continue
                h = hashlib.md5(data).hexdigest()
                if h in known or h in rejected:
                    continue
                name = f"{prefix}_{camel(cap)}_{lang}_{tag}_p{pno+1:03d}.png"
                dst = LIB / folder / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                k = 2
                while dst.exists():
                    dst = dst.with_name(name[:-4] + f"_{k}.png"); k += 1
                dst.write_bytes(data)
                known[h] = str(dst.relative_to(LIB))
                counts[folder] = counts.get(folder, 0) + 1
                got += 1
                rows.append({"file": str(dst.relative_to(LIB)),
                             "category": folder.split("/")[-1], "language": lang,
                             "caption": cap[:300], "source_document": src.name,
                             "source_tag": tag, "page": pno + 1,
                             "render": "raster" if pick and not is_table else "clip",
                             "licence": LICENCE, "credit_line": CREDIT,
                             "px": f"{px.width}x{px.height}", "bytes": len(data)})
                print(f"   + p{pno+1:03d} {folder.split('/')[-1][:24]:24s} {cap[:56]}")
        print(f"   → {got} exhibits")
        doc.close()

    if rows:
        man = LIB / "_BOOKS_FIGURES_MANIFEST.csv"
        old = list(csv.DictReader(man.open(encoding="utf-8"))) if man.exists() else []
        cols = sorted({k for r in old + rows for k in r})
        with man.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader(); w.writerows(old + rows)
        (LIB / "_library_state.json").write_text(json.dumps(state, indent=1))

    print("\n" + "=" * 60)
    for f, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {f}")
    print(f"\n{len(rows)} images · {n_csv} table CSVs")


if __name__ == "__main__":
    main()
