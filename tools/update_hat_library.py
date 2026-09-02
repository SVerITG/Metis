#!/usr/bin/env python3
"""update_hat_library.py — keep the HAT presentation content library current.

WHAT THIS IS FOR
    the researcher, 2026-08-28: *"There needs to be a way to update everything as we will
    keep working on these presentations."*

    The training decks are living documents. Every time a deck is revised, the
    library must pick up what is new WITHOUT re-filing the 250 images already
    there and without losing the names given to them.

WHY IT KEYS OFF CONTENT HASHES AND NEVER MTIME
    This is the two-computer lesson (memory: two-computer silent failure class,
    rule 1). The library lives on OneDrive. OneDrive rewrites modification times
    on sync, so an mtime comparison reports "everything changed" on one machine
    and "nothing changed" on the other, and both answers are wrong.

    So state is a ledger of md5 hashes of the image bytes, in
    `_library_state.json`. An image already in the ledger is skipped no matter
    what its timestamps say; an image not in it is new no matter how old the
    file claims to be. That also makes the run idempotent and interruptible.

    A consequence worth knowing: renaming a filed image by hand is SAFE. The
    ledger keys on content, so the rename sticks and the image is never re-filed
    under the generated name again.

WHAT IT DOES NOT DO
    It never deletes and never overwrites. Curation removed ~37 junk images from
    the first Commons harvest by hand; a tool that re-derived the library from
    scratch each run would drag every one of them back. New material is added;
    what you have already judged stays judged.

USAGE
    python3 tools/update_hat_library.py                 # decks + manifests
    python3 tools/update_hat_library.py --commons       # also top up from Wikimedia
    python3 tools/update_hat_library.py --articles      # also fetch open-access papers
    python3 tools/update_hat_library.py --all
    python3 tools/update_hat_library.py --dry-run       # report, change nothing
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# ── locations ────────────────────────────────────────────────────────────────
ONEDRIVE = Path("/mnt/c/Users/<user>/OneDrive/Documents")
LIB = ONEDRIVE / "2. HAT disease/5. Presentations/Content"
DECK_DIRS = [
    ONEDRIVE / "3. Projects/2. CAF/3. Project/1. Implementation/Formations/RCA_FormationsCliniques",
    ONEDRIVE / "3. Projects/2. CAF/3. Project/1. Implementation/Formations/RCA_FormationsLabo",
]
STATE = LIB / "_library_state.json"
UA = "MetisResearchCortex/1.0 (ITM Antwerp HAT presentation library; researcher@example.org)"

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
MIN_BYTES = 12_000          # below this it is an icon, a bullet or a rule

# ── DECK IDENTITY BEATS CAPTION ──────────────────────────────────────────────
# A deck devoted to one procedure means every image in it belongs to that
# procedure, whatever the slide happens to be titled. Deck 7 is ponction
# ganglionnaire; only 4 of its 23 images mention "ganglion" in their slide title
# — the rest say "Matériel requise", "Préparation de la lame", or just "A" and
# "18". Keyword routing scattered them across a generic Procedures folder;
# routing on the deck put the whole sequence back together.
#
# Checked BEFORE the keyword rules, and matched on the deck's filename.
DECK_ROUTES: list[tuple[str, str, str]] = [
    (r"ponction\s*ganglionnaire", "Image/28_Procedure_GanglionPuncture", "GanglionPuncture"),
    (r"^\s*8[\._\s].*\bPL\b|presentation_pl|\bTP\s*LCR\b|^\s*10[\._\s].*LCR",
     "Image/29_Procedure_LumbarPuncture_CSF", "LumbarPuncture"),
    (r"kit de pr[eé]l[eè]vement de sang|\bKPS\b",
     "Image/30_Procedure_BloodSampling_KPS", "BloodSampling"),
]

# ── categorisation: FIRST match wins, so specific rules precede general ──────
RULES: list[tuple[str, str, list[str]]] = [
    ("Image/11_Diagnostic_Algorithms", "DiagnosticAlgorithm",
     [r"algorithm", r"crit[eè]res? de d[eé]pistage", r"suivi apr[eè]s"]),
    # ── treatment, one folder per drug (flat, one level) ──
    ("Image/12_Treatment_Fexinidazole", "TreatmentFexinidazole", [r"fexinidazole"]),
    ("Image/12_Treatment_Pentamidine", "TreatmentPentamidine", [r"pentamidine"]),
    ("Image/12_Treatment_Melarsoprol", "TreatmentMelarsoprol", [r"m[eé]larsoprol", r"melarsoprol"]),
    ("Image/12_Treatment_NECT", "TreatmentNECT", [r"\bnect\b"]),
    ("Image/12_Treatment_Eflornithine", "TreatmentEflornithine",
     [r"[eé]flornithine", r"eflornithine", r"ornidyl", r"\bdfmo\b"]),
    ("Image/12_Treatment_Nifurtimox", "TreatmentNifurtimox", [r"nifurtimox"]),
    ("Image/12_Treatment_Acoziborole", "TreatmentAcoziborole", [r"acozib", r"scyx"]),
    ("Image/12_Treatment_Suramin", "TreatmentSuramin", [r"suramin"]),
    ("Image/12_Treatment_AdverseEvents", "TreatmentAdverse",
     [r"adverse", r"effets? ind[eé]sirables?", r"toxicit", r"tol[eé]ranc", r"h[eé]patotox"]),
    ("Image/12_Treatment_TrialResults", "TreatmentTrial",
     [r"\btrial\b", r"randomi[sz]", r"efficacy", r"treatment failure", r"cure rate",
      r"gu[eé]rison", r"relapse", r"rechute"]),
    ("Image/12_Treatment_DrugSupply", "TreatmentSupply",
     [r"donation", r"\bsupply\b", r"stock", r"approvisionn"]),
    ("Image/12_Treatment_Dosing_Schedules", "Treatment",
     [r"posologie", r"dosage", r"sch[eé]ma th[eé]rapeutique", r"choix de traitement",
      r"prise en charge", r"\bdose", r"traitement", r"\btreatment of\b"]),
    ("Image/05_Diagnostics_mAECT", "DiagnosticsMAECT",
     [r"maect", r"mini.?anion", r"mini.?colonne"]),
    ("Image/04_Diagnostics_CATT", "DiagnosticsCATT",
     [r"\bcatt\b", r"\btdr\b", r"sero.?k.?set", r"s[eé]rologie", r"interpr[eé]tation",
      r"histoire du diagnostic"]),
    ("Image/28_Procedure_GanglionPuncture", "GanglionPuncture",
     [r"ponction ganglionnaire", r"suc ganglionnaire", r"lymph ?node", r"\bganglion"]),
    ("Image/29_Procedure_LumbarPuncture_CSF", "LumbarPuncture",
     [r"ponction lombaire", r"lumbar puncture", r"\blcr\b", r"\bcsf\b",
      r"c[eé]r[eé]brospinal", r"leucorachie", r"positionnement"]),
    ("Image/30_Procedure_BloodSampling_KPS", "BloodSampling",
     [r"\bkps\b", r"kit de pr[eé]l[eè]vement", r"sang veineux", r"blood sampl",
      r"whole blood", r"thick blood", r"blood film", r"goutte [eé]paisse"]),
    ("Image/14_Procedures_Sampling", "Procedure",
     [r"ponction", r"lombaire", r"\blcr\b", r"pr[eé]l[eè]vement",
      r"\bkps\b", r"kit de", r"mat[eé]riel requise", r"pr[eé]paration de la lame",
      r"positionnement", r"proc[eé]dure", r"centrifugation", r"mode op[eé]ratoire",
      r"comptage cellulaire", r"wbc count", r"\bdetection\b", r"technique"]),
    ("Image/13_Clinical_Presentation", "ClinicalPresentation",
     [r"stade [12]", r"pr[eé]sentation clinique", r"douleur", r"pathog[eé]nie",
      r"soins", r"gestion de la douleur", r"risques", r"pr[eé]cautions",
      r"h[oô]te et facteurs"]),
    ("Image/15_Forms_and_Reporting", "Form",
     [r"fiche", r"rapportage", r"circuit", r"pharmacovigilance", r"d[eé]claration",
      r"digitalisation", r"forfait", r"supervision"]),
    ("Image/07_Laboratory", "Laboratory",
     [r"microscop", r"bonnes pratiques", r"\bbpl\b", r"assurance qualit",
      r"quelques remarques", r"apprenez"]),
    ("Image/01_Parasite_Biology", "ParasiteBiology",
     [r"le parasite", r"cycle de transmission", r"variation antig", r"trypanosom"]),
    ("Image/02_Vector_Tsetse", "VectorTsetse",
     [r"le vecteur", r"glossin", r"ts[eé].?ts[eé]", r"mouche"]),
    ("Image/03_Vector_Control", "VectorControl",
     [r"tiny target", r"petits [eé]crans", r"impr[eé]gn", r"lutte antivect"]),
    # ── data, one folder per question (flat, one level) ──
    ("Image/08_Data_Maps_Distribution", "DataMap",
     [r"\bmaps?\b", r"\bcarte\b", r"distribution g[eé]ographique",
      r"geographic(al)? distribution", r"spatial", r"choropleth", r"\batlas\b",
      r"pr[eé]fecture", r"zones? de sant[eé]"]),
    ("Image/08_Data_PopulationAtRisk", "DataPopRisk",
     [r"population (at )?risk", r"population expos", r"superficie", r"areas? at risk",
      r"aires? [aà] risque", r"analyse de risque"]),
    ("Image/08_Data_ScreeningCoverage", "DataCoverage",
     [r"coverage", r"couverture", r"people screened", r"personnes examin",
      r"active case.?finding", r"d[eé]pistage passif|passif"]),
    ("Image/08_Data_Models_Projections", "DataModel",
     [r"\bmodel", r"projection", r"posterior", r"forecast", r"simulat", r"bayesian"]),
    ("Image/08_Data_CaseNumbers_Trends", "DataCases",
     [r"nombre (total )?de cas", r"number of (new )?cases", r"cas nouveaux",
      r"reported cases", r"\btrend", r"tendance", r"[eé]volution", r"incidence",
      r"pr[eé]valence", r"prevalence"]),
    ("Image/08_Clinical_Data_Graphs", "DataAndMaps",
     [r"en r[eé]publique centrafricaine", r"\brca\b", r"sites s[eé]lectionn"]),
    ("Image/17_Programme_Context", "ProgrammeContext",
     [r"focal", r"contexte", r"strat[eé]gie", r"feuille de route", r"d[eé]pistage",
      r"une strat[eé]gie qui [eé]volue", r"d[eé]finition", r"mat[eé]riel fourni",
      r"[eé]quipe"]),
]
FALLBACK = ("Image/18_Unsorted_FromCourses", "Unsorted")

# Open-access papers to harvest the CONTENTS of. The PDF itself is never kept —
# the researcher, 2026-08-28: "dont save the pdfs specifically, we only want to harvest if
# there is something interesting inside like maps and tables from franco 2017."
# A PDF is a container you still have to open and hunt through; a named map and a
# CSV are things you drop into a deck and a script.
#
# Only papers that actually contain figures or tables are listed. Franco 2024,
# Buscher 2017 and the WHO 2018 report were checked and hold ZERO of either —
# they are 4-6 page editorials, so there is nothing inside to take.
PLOS_PAPERS = [
    ("10.1371/journal.pntd.0005585", "Franco2017"),
    ("10.1371/journal.pntd.0006890", "Franco2018"),
    ("10.1371/journal.pntd.0008261", "Franco2020"),
]

# Video and audio live in ppt/media alongside the images. The first harvest read
# only `a:blip` image references and silently missed three procedure films.
VIDEO_EXT = re.compile(r"\.(mp4|mov|wmv|avi|m4v|mp3|wav|m4a)$", re.I)

# The logo window. The image floor is 12 KB, which is where organisation logos
# sit — so everything between 2 KB (above bullets and hairlines) and that floor
# is staged for identification rather than dropped.
LOGO_MIN, LOGO_MAX = 2_000, MIN_BYTES


def deaccent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def camel(s: str, maxlen: int = 52) -> str:
    words = re.findall(r"[A-Za-z0-9]+", deaccent(s or ""))
    stop = {"de", "la", "le", "les", "du", "des", "et", "en", "un", "une", "the", "a",
            "of", "sur", "pour", "au", "aux", "dans", "par"}
    keep = [w for w in words if w.lower() not in stop] or words
    return ("".join(w[:1].upper() + w[1:] for w in keep))[:maxlen] or "Untitled"


def decamel(name: str) -> str:
    """camelCase -> spaced words, for matching a FILENAME rather than a caption.

    Two bugs made this necessary while splitting the big folders. A pattern like
    `geographic distribution` can never match `GeographicDistributionHAT`, so only
    single-word rules fired and the map rule caught 3 files instead of ~100. And
    the generated prefix must be dropped first: every file in the data folder began
    `DataAndMaps_`, which de-camelises to "data and maps" and sent 136 of 139 files
    to the maps folder. The prefix is my own label, not evidence about the picture.
    """
    body = name.split("_", 1)[1] if "_" in name else name
    body = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", body)
    body = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", body)
    return re.sub(r"[_\-.]+", " ", body).lower()


def classify(title: str, deck: str, text: str) -> tuple[str, str]:
    dk = deaccent(deck or "").lower()
    for pat, folder, prefix in DECK_ROUTES:
        if re.search(pat, dk, re.I):
            return folder, prefix
    hay = deaccent(f"{title} {deck} {text[:200]}").lower()
    for folder, prefix, pats in RULES:
        if any(re.search(p, hay) for p in pats):
            return folder, prefix
    return FALLBACK


def load_state() -> dict:
    """State has TWO ledgers, and the second one is the one people forget.

    `media_hashes` records what is filed, so nothing is filed twice.
    `rejected_hashes` records what was deliberately THROWN AWAY, so a re-run
    cannot drag it back. Without it "additive only" is a half-promise: the first
    Commons harvest pulled in specimen catalogue records, a national-park photo
    and a file literally named HFDF, all of which were removed by hand — and the
    next --commons run proposed every one of them again.

    A curation decision is a decision. It has to be stored like one.
    """
    if STATE.exists():
        try:
            st = json.loads(STATE.read_text())
            st.setdefault("rejected_hashes", {})
            return st
        except Exception:
            print("! state file unreadable — treating every image as new", file=sys.stderr)
    return {"media_hashes": {}, "rejected_hashes": {}, "runs": [], "articles": {}}


def fetch(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ── decks ────────────────────────────────────────────────────────────────────
def sync_decks(state: dict, dry: bool) -> tuple[int, list[dict], list[dict]]:
    decks = sorted(p for d in DECK_DIRS if d.exists()
                   for p in d.rglob("*.pptx") if not p.name.startswith("~$"))
    known = state["media_hashes"]
    rejected = state.get("rejected_hashes", {})
    added, table_rows = 0, []
    new_rows: list[dict] = []

    for deck in decks:
        course = "Labo" if "Labo" in str(deck) else "Cliniques"
        archived = "Archive" in deck.parts
        try:
            z = zipfile.ZipFile(deck)
        except Exception as exc:
            print(f"  ! cannot open {deck.name}: {exc}")
            continue

        slide_names = sorted(
            (n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)", n.split("/")[-1]).group(1)))
        deck_new = 0

        for sname in slide_names:
            snum = int(re.search(r"(\d+)", sname.split("/")[-1]).group(1))
            try:
                root = ET.fromstring(z.read(sname))
            except Exception:
                continue
            texts = [t.text.strip() for t in root.iter(f"{{{A_NS}}}t") if (t.text or "").strip()]
            title = texts[0][:150] if texts else ""

            # tables (current decks only — archives would double every row)
            if not archived:
                for ti, tbl in enumerate(root.iter(f"{{{A_NS}}}tbl"), 1):
                    rows = []
                    for tr in tbl.findall(f"{{{A_NS}}}tr"):
                        cells = [re.sub(r"\s+", " ", " ".join(
                            t.text.strip() for t in tc.iter(f"{{{A_NS}}}t") if (t.text or "").strip()))
                            for tc in tr.findall(f"{{{A_NS}}}tc")]
                        if cells:
                            rows.append(cells)
                    if rows:
                        table_rows.append({"deck": deck.name, "slide": snum, "idx": ti,
                                           "title": title, "rows": rows})

            rels = f"ppt/slides/_rels/slide{snum}.xml.rels"
            rid2media = {}
            if rels in z.namelist():
                for rel in ET.fromstring(z.read(rels)):
                    tgt = rel.get("Target", "")
                    if "media/" in tgt:
                        rid2media[rel.get("Id")] = "ppt/" + tgt.split("../")[-1]

            # video and audio: referenced from the slide, stored in ppt/media
            for vid in [n for n in z.namelist()
                        if n.startswith("ppt/media/") and VIDEO_EXT.search(n)]:
                data = z.read(vid)
                h = hashlib.md5(data).hexdigest()
                if h in known:
                    continue
                dst = (LIB / "Video/04_Diagnostics" /
                       f"Video_{camel(deck.stem, 44)}_s{snum:02d}"
                       f"_Source-RCA-{'Labo' if course == 'Labo' else 'Clinique'}"
                       f"{Path(vid).suffix.lower()}")
                if not dry:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(data)
                    known[h] = str(dst.relative_to(LIB))
                added += 1
                print(f"  + video {dst.name[:66]} ({len(data)//1048576} MB)")

            # the logo window — staged, not filed, because a hash is not a name
            for sm in [n for n in z.namelist() if re.match(r"ppt/media/image", n)]:
                data = z.read(sm)
                if not (LOGO_MIN <= len(data) < LOGO_MAX):
                    continue
                if Path(sm).suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif",
                                                   ".emf", ".wmf"):
                    continue
                h = hashlib.md5(data).hexdigest()
                if h in known:
                    continue
                dst = (LIB / "Organisations_Logos/_from_decks_unidentified"
                       / f"logo_{h[:10]}{Path(sm).suffix.lower()}")
                if not dry:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(data)
                    known[h] = str(dst.relative_to(LIB))
                added += 1

            for blip in root.iter(f"{{{A_NS}}}blip"):
                mpath = rid2media.get(blip.get(R_EMBED))
                if not mpath or mpath not in z.namelist():
                    continue
                data = z.read(mpath)
                if len(data) < MIN_BYTES:
                    continue
                h = hashlib.md5(data).hexdigest()
                if h in known or h in rejected:
                    continue      # already filed, or deliberately thrown away

                folder, prefix = classify(title, deck.name, " | ".join(texts[:14]))
                ext = Path(mpath).suffix.lower().lstrip(".") or "png"
                dno = re.match(r"(\d+)", deck.name)
                dno = dno.group(1) if dno else "x"
                tag = "RCA-Labo" if course == "Labo" else "RCA-Clinique"
                base = (f"{prefix}_{camel(title) or f'Slide{snum}'}_FR"
                        f"_D{dno}s{snum:02d}_Source-{tag}{'-ARCHIVE' if archived else ''}")
                dst = LIB / folder / f"{base}.{ext}"
                n = 2
                while dst.exists():
                    dst = LIB / folder / f"{base}_{n}.{ext}"
                    n += 1

                if not dry:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(data)
                    known[h] = str(dst.relative_to(LIB))
                added += 1
                deck_new += 1
                new_rows.append({
                    "file": str(dst.relative_to(LIB)), "category": folder.split("/")[-1],
                    "language": "FR", "slide_title": title, "source_deck": deck.name,
                    "course": course, "slide": snum, "archived": archived,
                    "licence": "Internal — ITM/PNLTHA training material",
                    "credit_line": "ITM Antwerp / PNLTHA-RCA, projet FOCAL (internal)",
                    "bytes": len(data)})
        if deck_new:
            print(f"  + {deck_new:3d} new  {deck.name[:58]}")

    return added, new_rows, table_rows


def write_tables(table_rows: list[dict], dry: bool) -> int:
    tdir = LIB / "Image/16_Tables_Extracted"
    if dry:
        return len(table_rows)
    tdir.mkdir(parents=True, exist_ok=True)
    md = ["# Tables extracted from the RCA training decks", "",
          "Regenerated by `tools/update_hat_library.py`. The deck is the source of truth;",
          "this is a searchable copy.", ""]
    for t in table_rows:
        stem = f"{camel(t['deck'].rsplit('.', 1)[0], 40)}_s{t['slide']:02d}_t{t['idx']}"
        with (tdir / f"{stem}.csv").open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(t["rows"])
        md += [f"## {t['deck']} · slide {t['slide']} · table {t['idx']}",
               f"*{t['title'][:120]}*", ""]
        width = max(len(r) for r in t["rows"])
        head = t["rows"][0] + [""] * (width - len(t["rows"][0]))
        md.append("| " + " | ".join(c or " " for c in head) + " |")
        md.append("|" + "---|" * width)
        for row in t["rows"][1:]:
            row = row + [""] * (width - len(row))
            md.append("| " + " | ".join(c or " " for c in row) + " |")
        md.append("")
    (tdir / "_ALL_TABLES.md").write_text("\n".join(md), encoding="utf-8")
    return len(table_rows)


def append_manifest(new_rows: list[dict], dry: bool) -> None:
    """Append-only. Rewriting would discard hand corrections to earlier rows."""
    if not new_rows or dry:
        return
    man = LIB / "_COURSE_CONTENT_MANIFEST.csv"
    cols = list(new_rows[0].keys())
    exists = man.exists()
    with man.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerows(new_rows)


# ── open-access contents: figures and tables, never the PDF ─────────────────
def _txt(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def _kind_of(caption: str) -> str:
    """Chart / Map / Figure, from the ORIGINAL caption.

    Two bugs shaped this. Testing `"map" in caption` matched the word "Roadmap"
    and labelled every case-trend chart a map. Re-deriving the kind from the
    camel-cased FILENAME instead of the caption lost the stopwords the test needs
    ("number of reported cases" had become "NumberReportedCases"), and everything
    collapsed to Figure. Classify from the caption, with word boundaries.
    """
    c = (caption or "").lower()
    if ("number of reported cases" in c or "number of people screened" in c
            or "per year" in c or re.search(r"\btrends?\b", c)):
        return "Chart"
    if (re.search(r"\bmaps?\b", c) or "geographic distribution" in c
            or "distribution of" in c or "areas at risk" in c
            or "area at risk" in c or "health facilities" in c):
        return "Map"
    return "Figure"


def sync_plos_contents(state: dict, dry: bool) -> int:
    figdir = LIB / "Image/19_WHO_Atlas_Maps_and_CaseData"
    tabdir = LIB / "Image/16_Tables_Extracted/WHO_Franco_series"
    got = 0
    for doi, tag in PLOS_PAPERS:
        try:
            raw = fetch("https://journals.plos.org/plosntds/article/file?id="
                        + urllib.parse.quote(doi) + "&type=manuscript")
            root = ET.fromstring(raw)
        except Exception as exc:
            print(f"  ! {tag}: manuscript XML unavailable ({exc})")
            continue

        for fig in root.iter("fig"):
            fid = (fig.get("id") or "")
            gm = re.search(r"\.(g\d+)$", fid)
            if not gm:
                continue
            capel = fig.find("caption")
            cap = _txt(capel) if capel is not None else ""
            name = f"WHO_{_kind_of(cap)}_{camel(cap, 58)}_{tag}_{gm.group(1)}_Source-PLOSNTD.png"
            dest = figdir / name
            if dest.exists():
                continue
            try:
                data = fetch("https://journals.plos.org/plosntds/article/figure/image"
                             "?size=large&id=" + urllib.parse.quote(doi) + "." + gm.group(1))
            except Exception:
                continue
            if len(data) < 20_000 or data[:4] == b"<!DO":
                continue
            h = hashlib.md5(data).hexdigest()
            if h in state["media_hashes"]:
                continue
            if not dry:
                figdir.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                state["media_hashes"][h] = str(dest.relative_to(LIB))
            got += 1
            print(f"  + {name[:78]}")
            time.sleep(0.5)

        # Tables as CSV, not as pictures of tables. `.//table` and not
        # `find("table")`: JATS nests the table inside <alternatives>.
        for tw in root.iter("table-wrap"):
            tid = (tw.get("id") or "").rsplit(".", 1)[-1]
            if not re.fullmatch(r"t\d+", tid):
                continue
            capel = tw.find("caption")
            cap = _txt(capel) if capel is not None else ""
            tbl = tw.find(".//table")
            if tbl is None:
                continue
            rows = []
            for tr in tbl.iter("tr"):
                cells = [_txt(c) for c in tr if c.tag in ("td", "th")]
                if any(cells):
                    rows.append(cells)
            if not rows:
                continue
            out = tabdir / f"WHO_Table_{camel(cap, 46)}_{tag}_{tid}.csv"
            if out.exists():
                continue
            if not dry:
                tabdir.mkdir(parents=True, exist_ok=True)
                with out.open("w", newline="", encoding="utf-8") as fh:
                    csv.writer(fh).writerows(rows)
            got += 1
            print(f"  T {out.name[:74]}  ({len(rows)} rows)")
        time.sleep(0.4)
    return got


# ── commons top-up ───────────────────────────────────────────────────────────
def sync_commons(state: dict, dry: bool) -> int:
    """Fetch candidates from curated Commons categories into a REVIEW INBOX.

    It does not write into the topic folders, and that is the whole design.

    Measured on 2026-08-28: free-text Commons search for "sleeping sickness
    historical" returned bound volumes of the *Southern Historical Society Papers*
    — American Civil War documents that matched the word "Historical". Switching
    to human-curated categories fixed the worst of it, but `Category:African
    trypanosomiasis` is still dominated by colonial-era expedition archives, and
    near-duplicates at different resolutions hash differently so no ledger can
    catch them.

    About half of the first 74 downloads had to be deleted by hand. A tool that
    writes straight into `01_Parasite_Biology` makes that cleanup a permanent tax
    on every run. So: the machine fetches and states the licence, a person keeps
    or rejects, and `--reject <file>` records the decision so it is never asked
    again.
    """
    inbox = LIB / "Image/_INBOX_Commons_review"
    cats = [
        ("Category:Trypanosoma", "ParasiteBiology"),
        ("Category:Glossina", "VectorTsetse"),
        ("Category:African trypanosomiasis", "HAT-General"),
    ]
    ok = re.compile(r"(public domain|cc0|cc by|cc-by|attribution)", re.I)
    bad = re.compile(r"(\bnc\b|non-?commercial|\bnd\b|no-?deriv|non-free|fair use)", re.I)
    got = 0
    notes: list[str] = []
    for cat, prefix in cats:
        try:
            q = urllib.parse.urlencode({
                "action": "query", "format": "json", "formatversion": "2",
                "generator": "categorymembers", "gcmtitle": cat, "gcmtype": "file",
                "gcmlimit": "30", "prop": "imageinfo",
                "iiprop": "url|extmetadata|size|mime", "iiurlwidth": "1800"})
            d = json.loads(fetch("https://commons.wikimedia.org/w/api.php?" + q, 45))
        except Exception as exc:
            print(f"  ! {cat}: {exc}")
            continue
        for page in d.get("query", {}).get("pages", []) or []:
            ii = (page.get("imageinfo") or [{}])[0]
            em = ii.get("extmetadata", {}) or {}
            g = lambda k: re.sub(r"<[^>]+>", " ",
                                 (em.get(k, {}) or {}).get("value", "") or "").strip()
            lic = g("LicenseShortName") or g("UsageTerms")
            if bad.search(lic) or not ok.search(lic) or not ii.get("mime", "").startswith("image/"):
                continue
            if (ii.get("width") or 0) < 700:
                continue
            url = ii.get("thumburl") or ii.get("url")
            if not url:
                continue
            try:
                data = fetch(url)
            except Exception:
                continue
            if len(data) < MIN_BYTES:
                continue
            h = hashlib.md5(data).hexdigest()
            if h in state["media_hashes"] or h in state.get("rejected_hashes", {}):
                continue
            desc = g("ImageDescription") or page["title"].replace("File:", "").rsplit(".", 1)[0]
            ext = {"image/jpeg": "jpg", "image/png": "png",
                   "image/svg+xml": "svg"}.get(ii["mime"], "jpg")
            dst = inbox / f"{prefix}_{camel(desc)}_Source-Commons.{ext}"
            if dst.exists():
                continue
            if not dry:
                inbox.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
                state["media_hashes"][h] = str(dst.relative_to(LIB))
            got += 1
            print(f"  ? {dst.name[:70]}  [{lic}]")
            notes.append(f"| `{dst.name}` | {lic} | {g('Artist')[:60] or '—'} | "
                         f"https://commons.wikimedia.org/wiki/"
                         f"{urllib.parse.quote(page['title'].replace(' ', '_'))} |")
            time.sleep(0.4)
    if got and not dry:
        (inbox / "_TRIAGE.md").write_text(
            "# Commons review inbox\n\n"
            "Candidates fetched from curated Commons categories. **Nothing here is in the "
            "library yet** — move what you want into a topic folder and rename it, then:\n\n"
            "```bash\npython3 tools/update_hat_library.py --reject <file> [<file> ...]\n```\n\n"
            "to bin the rest permanently. Rejected hashes are remembered, so a later run "
            "will not offer them again.\n\n"
            "| File | Licence | Author | Commons page |\n|---|---|---|---|\n"
            + "\n".join(notes) + "\n", encoding="utf-8")
    return got


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--commons", action="store_true", help="top up from Wikimedia Commons categories")
    ap.add_argument("--articles", action="store_true",
                help="harvest figures and tables OUT of the open-access papers")
    ap.add_argument("--all", action="store_true", help="decks + commons + articles")
    ap.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    ap.add_argument("--reject", nargs="+", metavar="FILE",
                    help="record these files as deliberately rejected (hash remembered, "
                         "file deleted) so no future run re-fetches them")
    a = ap.parse_args()
    dry = a.dry_run
    if not LIB.exists():
        sys.exit(f"Library not found: {LIB}")

    state = load_state()

    if a.reject:
        n = 0
        for f in a.reject:
            fp = Path(f)
            if not fp.exists():
                print(f"  ! not found: {f}")
                continue
            h = hashlib.md5(fp.read_bytes()).hexdigest()
            state["rejected_hashes"][h] = fp.name
            state["media_hashes"].pop(h, None)
            if not dry:
                fp.unlink()
            n += 1
            print(f"  rejected {fp.name}")
        if not dry:
            STATE.write_text(json.dumps(state, indent=1))
        print(f"{n} file(s) recorded as rejected — no future run will re-fetch them")
        return

    print(f"HAT content library — {LIB}")
    print(f"{'DRY RUN · nothing will be written' if dry else 'updating'}")
    print(f"ledger: {len(state['media_hashes'])} filed · "
          f"{len(state.get('rejected_hashes', {}))} rejected\n")

    print("── training decks ──")
    added, new_rows, table_rows = sync_decks(state, dry)
    if not added:
        print("  no new images — every deck image is already in the library")
    ntab = write_tables(table_rows, dry)
    append_manifest(new_rows, dry)
    print(f"  {added} new images · {ntab} tables written")

    n_art = n_com = 0
    if a.articles or a.all:
        print("\n── open-access paper contents (figures + tables, no PDFs) ──")
        n_art = sync_plos_contents(state, dry)
        if not n_art:
            print("  nothing new")
    if a.commons or a.all:
        print("\n── Wikimedia Commons → review inbox (not filed directly) ──")
        n_com = sync_commons(state, dry)
        if not n_com:
            print("  nothing new")

    total = sum(1 for p in LIB.rglob("*")
                if p.is_file() and p.suffix.lower() in
                {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".svg", ".mp4", ".mov", ".pdf"})
    if not dry:
        state["runs"] = (state.get("runs") or [])[-19:] + [{
            "when": time.strftime("%Y-%m-%d %H:%M"), "deck_images": added,
            "tables": ntab, "articles": n_art, "commons": n_com, "total_files": total}]
        STATE.write_text(json.dumps(state, indent=1))

    print(f"\n{'would be ' if dry else ''}filed: {added + n_art + n_com} new items")
    print(f"library now holds {total} media files")
    if dry:
        print("\nRe-run without --dry-run to apply.")


if __name__ == "__main__":
    main()
