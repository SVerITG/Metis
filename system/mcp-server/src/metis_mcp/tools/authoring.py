"""authoring.py — let Metis MAKE things, not only remember them.

WHY THIS MODULE EXISTS
    An audit on 2026-08-21 asked a blunt question: what can a researcher who works
    entirely in Claude Desktop actually not do? The answer had a clean shape.
    Everything that goes through the DATABASE worked — projects, tasks, courses,
    library, memory, meetings. Everything that touches the FILESYSTEM did not.

    Of 236 tools, exactly three could write a file and all three wrote config.
    Zero could produce a document. `office.py` reads .pptx and .docx and cannot
    create either. So Metis could discuss a presentation at length and never make
    one.

    That gap was invisible in Claude Code, because Claude Code supplies Write,
    Edit and Bash itself — the assistant filled it without anyone noticing the
    tools had not. In Desktop, and in Cursor, and in whatever MCP client a future
    user picks, nothing fills it.

    These are MCP tools, so they work in every client at once. That is the point:
    a capability added here reaches Desktop, Code, and anything else that speaks
    the protocol, rather than being another Claude Code privilege.

WHERE FILES GO, AND WHY IT IS CONSTRAINED
    Everything is written under `outputs/` inside the Research Cortex, and paths
    are resolved and containment-checked before writing. A tool that can write
    anywhere is a tool that can overwrite anything, and this one is invoked by a
    model rather than a person. The constraint is not distrust of the model; it is
    that an accident here costs the researcher work they cannot recover.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths

log = logging.getLogger("metis")

_MAX_SLIDES = 60
_MAX_CHARS = 400_000


def _slug(text: str, limit: int = 60) -> str:
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-")
    return (t[:limit].strip("-") or "untitled").lower()


def _safe_target(subdir: str, filename: str) -> Path:
    """Resolve a path under outputs/ and refuse anything that escapes it."""
    base = (paths.root / "outputs" / subdir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    target = (base / filename).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("refusing to write outside outputs/")
    return target


# ---------------------------------------------------------------------------
# Presentations
# ---------------------------------------------------------------------------

@app.tool()
async def create_presentation(
    title: str,
    slides: str,
    subtitle: str = "",
    filename: str = "",
    template: str = "",
    closing: str = "",
) -> list[TextContent]:
    """Create a PowerPoint (.pptx) file from a simple text outline.

    The tool that closes the largest gap in Claude Desktop: Metis could read
    presentations but never produce one, so any "make me a deck" request had no
    way to land as a file.

    Args:
        title: Deck title, used on the title slide and in the filename.
        slides: The deck as plain text. Each slide starts with a line beginning
            "# " (the slide title); every following line becomes a bullet.
            A line beginning "> " becomes speaker notes for that slide.
            Blank lines are ignored. Example:

                # Why passive surveillance underperforms
                Health-facility detection depends on care-seeking
                Median delay to diagnosis exceeds 12 months
                > Open with the Mitashi 2014 figure

                # What changes with RDTs at the periphery
                Sensitivity holds at lower prevalence
            A line beginning "## " starts a section-divider slide instead.
        subtitle: Optional subtitle for the title slide.
        filename: Optional filename; derived from the title when omitted.
        template: The researcher's slide template stored in Metis (name or part
            of it). Empty = their default deck template if one is stored (see
            list_templates) — never ask them for the file. "none" = plain deck.
        closing: Text for the template's closing slide under "Thank you!" —
            e.g. presenter name, e-mail, website. Empty = no closing slide.

    Returns:
        The path written and a slide count.
    """
    if not title.strip():
        return [TextContent(type="text", text="A title is required.")]
    if len(slides) > _MAX_CHARS:
        return [TextContent(type="text", text="Outline too large.")]

    try:
        from pptx import Presentation
        from pptx.util import Pt
    except ImportError:
        return [TextContent(type="text", text=(
            "python-pptx is not installed in the Metis environment.\n"
            "Install it with:  ~/.local/share/metis-mcp/.venv/bin/pip install python-pptx"
        ))]

    # ── Parse the outline ───────────────────────────────────────────────────
    parsed: list[dict] = []
    for raw in slides.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("## "):
            parsed.append({"title": line.lstrip()[3:].strip(), "section": True,
                           "bullets": [], "notes": []})
        elif line.lstrip().startswith("# "):
            parsed.append({"title": line.lstrip()[2:].strip(),
                           "bullets": [], "notes": []})
        elif line.lstrip().startswith("> "):
            if parsed:
                parsed[-1]["notes"].append(line.lstrip()[2:].strip())
        else:
            if not parsed:
                # Bullets before any heading would otherwise be silently dropped.
                parsed.append({"title": title, "bullets": [], "notes": []})
            parsed[-1]["bullets"].append(line.strip().lstrip("-•* ").strip())

    if not parsed:
        return [TextContent(type="text", text=(
            "No slides found. Each slide must start with a line beginning '# '."
        ))]
    if len(parsed) > _MAX_SLIDES:
        return [TextContent(type="text",
                            text=f"{len(parsed)} slides exceeds the {_MAX_SLIDES} cap.")]

    # ── Build ───────────────────────────────────────────────────────────────
    tpl = None if template.strip().lower() == "none" else \
        _pick_template(template, "deck", (".potx", ".pptx"))
    if template.strip() and template.strip().lower() != "none" and tpl is None:
        have = ", ".join(p.name for p in _find_templates()) or "none"
        return [TextContent(type="text", text=(
            f"No slide template matched '{template}'. Stored templates: {have}."))]
    if tpl is not None:
        return _deck_from_template(tpl, title, subtitle, closing, parsed, filename)

    prs = Presentation()

    title_layout = prs.slide_layouts[0]
    s = prs.slides.add_slide(title_layout)
    s.shapes.title.text = title.strip()
    if subtitle and len(s.placeholders) > 1:
        s.placeholders[1].text = subtitle.strip()

    body_layout = prs.slide_layouts[1]
    for item in parsed:
        sl = prs.slides.add_slide(body_layout)
        sl.shapes.title.text = item["title"][:120]
        body = sl.placeholders[1].text_frame
        body.clear()
        bullets = item["bullets"] or [""]
        for i, b in enumerate(bullets):
            para = body.paragraphs[0] if i == 0 else body.add_paragraph()
            para.text = b[:300]
            para.level = 0
            for run in para.runs:
                run.font.size = Pt(20)
        if item["notes"]:
            sl.notes_slide.notes_text_frame.text = "\n".join(item["notes"])[:2000]

    stem = _slug(filename or title)
    target = _safe_target("presentations",
                          f"{datetime.now().date().isoformat()}_{stem}.pptx")
    prs.save(str(target))

    rel = target.relative_to(paths.root)
    return [TextContent(type="text", text=(
        f"Created {len(parsed) + 1} slides (title + {len(parsed)}).\n"
        f"Saved to: {rel}\n\n"
        f"Open it from the Research Cortex, or say the word and it can be revised "
        f"and rewritten to the same path."
    ))]


def _deck_from_template(tpl: Path, title: str, subtitle: str, closing: str,
                        parsed: list[dict], filename: str) -> list[TextContent]:
    """Build the deck on the researcher's own template, keeping its look.

    The template's sample slides are dropped, except that its own title and
    closing slides are reused when present — they carry the artwork that an
    empty picture placeholder would not. Layouts are chosen by name, so any
    template with a title, a content and (optionally) a section layout works.
    """
    try:
        prs = _open_template(tpl)
    except Exception as exc:  # noqa: BLE001
        return [TextContent(type="text", text=f"Could not open template {tpl.name}: {exc}")]

    def _layout(*names):
        for n in names:
            for lay in prs.slide_layouts:
                if n in lay.name.lower():
                    return lay
        return None

    lay_title = _layout("title slide") or prs.slide_layouts[0]
    lay_body = _layout("title and content", "content") or prs.slide_layouts[1]
    lay_section = _layout("section header - graphic", "section header", "section")
    lay_end = _layout("end slide - image", "end slide")

    sld_ids = prs.slides._sldIdLst
    pairs = [(sid, prs.part.related_part(sid.rId)) for sid in list(sld_ids)]

    def _first(pred):
        return next((sid for sid, part in pairs if pred(part.slide.slide_layout.name.lower())), None)

    keep_title = _first(lambda n: "title slide" in n)
    keep_end = _first(lambda n: "end slide" in n) if closing.strip() else None
    for sid, _part in pairs:
        if sid is not keep_title and sid is not keep_end:
            prs.part.drop_rel(sid.rId)
            sld_ids.remove(sid)
    # New slides are named slide<count+1>.xml; a kept sample slide may already
    # own that name, which writes two parts under one name and makes PowerPoint
    # offer to "repair" the file. Renumber the kept ones 1..N first.
    from pptx.opc.packuri import PackURI
    for i, sid in enumerate(sld_ids, start=1):
        prs.part.related_part(sid.rId).partname = PackURI(f"/ppt/slides/slide{i}.xml")

    def _fill(ph, text: str, bullets: bool = False):
        tf = ph.text_frame
        lines = [t for t in (text.split("\n") if bullets else [text])]
        tf.text = lines[0]
        for extra in lines[1:]:
            tf.add_paragraph().text = extra

    def _clear_empty_pictures(sl):
        for ph in list(sl.placeholders):
            if "PICTURE" in str(ph.placeholder_format.type) and not getattr(ph, "image", None):
                try:
                    ph._element.getparent().remove(ph._element)
                except Exception:  # noqa: BLE001
                    pass

    # Title slide
    if keep_title is not None:
        ts = prs.part.related_part(keep_title.rId).slide
    else:
        ts = prs.slides.add_slide(lay_title)
        _clear_empty_pictures(ts)
    for ph in ts.placeholders:
        t = str(ph.placeholder_format.type)
        if "TITLE" in t and "SUB" not in t:
            _fill(ph, title.strip())
        elif ph.has_text_frame and "PICTURE" not in t:
            _fill(ph, subtitle.strip())

    # Content and section slides
    for item in parsed:
        lay = lay_section if item.get("section") and lay_section is not None else lay_body
        sl = prs.slides.add_slide(lay)
        _clear_empty_pictures(sl)
        body_done = False
        for ph in sl.placeholders:
            t = str(ph.placeholder_format.type)
            if "TITLE" in t:
                ph.text_frame.text = item["title"][:120]
            elif ph.has_text_frame and not body_done:
                _fill(ph, "\n".join(b[:300] for b in item["bullets"]) or "", bullets=True)
                body_done = True
        if item["notes"]:
            sl.notes_slide.notes_text_frame.text = "\n".join(item["notes"])[:2000]

    # Closing slide: the template's own if kept, moved to the end
    if closing.strip():
        if keep_end is not None:
            es = prs.part.related_part(keep_end.rId).slide
            sld_ids.remove(keep_end)
            sld_ids.append(keep_end)
        elif lay_end is not None:
            es = prs.slides.add_slide(lay_end)
            _clear_empty_pictures(es)
        else:
            es = None
        if es is not None:
            for ph in es.placeholders:
                t = str(ph.placeholder_format.type)
                is_heading = "TITLE" in t and "SUBTITLE" not in t
                if ph.has_text_frame and not is_heading and "PICTURE" not in t:
                    _fill(ph, closing.strip(), bullets=True)

    stem = _slug(re.sub(r"\.pptx?$", "", filename, flags=re.I) or title)
    target = _safe_target("presentations", f"{datetime.now().date().isoformat()}_{stem}.pptx")
    prs.save(str(target))
    msg = [f"Created {len(prs.slides)} slides on template {tpl.name}.",
           f"Saved to: {target.relative_to(paths.root)}"]
    m = re.match(r"^/mnt/([a-z])/(.*)$", str(target))
    if m:
        msg.append("Open it from Windows: " + m.group(1).upper() + ":\\"
                   + m.group(2).replace("/", "\\"))
    return [TextContent(type="text", text="\n".join(msg))]


# ---------------------------------------------------------------------------
# Posters — filled into the researcher's own template
# ---------------------------------------------------------------------------
#
# A poster is not a deck: it is one slide, built on an institutional template
# whose layout is fixed. The template is the researcher's file, so it is looked
# up in machine-local folders and never shipped with Metis.

_PT = 12700  # EMU per point
_POSTER_SIZES = (50, 44, 40, 36, 32, 28, 24, 22, 20, 18)
_TITLE_SIZES = (105, 96, 88, 80, 72, 64, 56, 48, 44, 40, 36)


def _template_dirs() -> list[Path]:
    import os
    dirs = []
    if os.environ.get("METIS_TEMPLATES_DIR"):
        dirs.append(Path(os.environ["METIS_TEMPLATES_DIR"]).expanduser())
    dirs += [paths.root / "system" / "config" / "local" / "templates",
             paths.root / "knowledge" / "templates"]
    # An edition's institution pack ships its own templates (letterhead, poster,
    # slides). Searched last, so a researcher's own copy of the same name wins.
    try:
        from metis_mcp.edition import pack_dir
        pd = pack_dir()
        if pd is not None:
            dirs.append(pd / "templates")
    except Exception:  # noqa: BLE001 — a missing pack must not hide local templates
        pass
    return dirs


def _find_templates(exts: tuple = (".potx", ".pptx")) -> list[Path]:
    found: list[Path] = []
    for d in _template_dirs():
        if d.is_dir():
            found += sorted(p for p in d.rglob("*")
                            if p.suffix.lower() in exts and p.is_file()
                            and not p.name.startswith(("~$", ".")))
    return found


def _template_kind(p: Path) -> str:
    if p.suffix.lower() in (".docx", ".dotx"):
        return "document"
    return "poster" if "poster" in p.name.lower() else "deck"


def _pick_template(want: str, kind: str, exts: tuple) -> Path | None:
    """A path, a name fragment, or — when empty — the first template of this kind."""
    if want.strip():
        cand = Path(want).expanduser()
        if not cand.is_absolute():
            cand = paths.root / want
        if cand.is_file():
            return cand
        w = want.strip().lower()
        return next((p for p in _find_templates(exts) if w in p.name.lower()), None)
    return next((p for p in _find_templates(exts) if _template_kind(p) == kind), None)


@app.tool()
async def list_templates() -> list[TextContent]:
    """List the researcher's own templates stored in Metis — posters, slide decks, letters.

    Call this before making a poster, a presentation or a formal document. The
    templates are kept inside Metis (a private, machine-local folder), so never
    ask the researcher where a template is or to attach it: it is already here,
    and create_poster / create_presentation / fill_document_template find it by
    name or use the right one by default.
    """
    rows = _find_templates((".potx", ".pptx", ".docx", ".dotx"))
    if not rows:
        where = "\n".join(f"  - {d}" for d in _template_dirs())
        return [TextContent(type="text", text=f"No templates stored yet. Put them in:\n{where}")]
    label = {"poster": "Poster (create_poster)", "deck": "Slide deck (create_presentation)",
             "document": "Document (fill_document_template)"}
    lines = ["Templates stored in Metis (used automatically; no need to ask for them):", ""]
    for p in rows:
        lines.append(f"- {p.name} — {label[_template_kind(p)]}")
    return [TextContent(type="text", text="\n".join(lines))]


def _open_template(p: Path):
    """Open a .pptx, or a .potx — which python-pptx refuses only by content type."""
    import io
    import zipfile
    from pptx import Presentation

    if p.suffix.lower() != ".potx":
        return Presentation(str(p))
    buf = io.BytesIO()
    with zipfile.ZipFile(p) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(b"presentationml.template.main+xml",
                                    b"presentationml.presentation.main+xml")
            zout.writestr(item, data)
    buf.seek(0)
    return Presentation(buf)


def _poster_slots(layout) -> dict:
    """Read a layout's geometry: title, subtitle, band, and (header, box) pairs.

    Content boxes are the large placeholders; a header is the small text strip
    sitting just above a box. Whatever text placeholder is left is the band
    under the title (authors, affiliations, key message).
    """
    from pptx.enum.shapes import PP_PLACEHOLDER as P

    title = subtitle = None
    small, boxes = [], []
    for ph in layout.placeholders:
        t = ph.placeholder_format.type
        if t in (P.TITLE, P.CENTER_TITLE):
            title = ph
        elif t == P.SUBTITLE:
            subtitle = ph
        elif t in (P.OBJECT, P.BODY):
            (boxes if ph.height >= 6 * 360000 else small).append(ph)
    # Reading order: down the left column, then the next one.
    boxes.sort(key=lambda b: (round(b.left / 360000), b.top))
    pairs, used = [], set()
    for b in boxes:
        head = None
        for s in small:
            above = 0 <= b.top - (s.top + s.height) <= 3 * 360000
            overlap = s.left < b.left + b.width and b.left < s.left + s.width
            if above and overlap and id(s) not in used:
                head = s
                used.add(id(s))
                break
        pairs.append((head, b))
    band = [s for s in small if id(s) not in used]
    band.sort(key=lambda s: s.top)
    return {"title": title, "subtitle": subtitle,
            "band": band[0] if band else None, "pairs": pairs}


def _parse_sections(text: str) -> list[dict]:
    out: list[dict] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("# "):
            out.append({"heading": line.lstrip()[2:].strip(), "lines": []})
        else:
            if not out:
                out.append({"heading": "", "lines": []})
            out[-1]["lines"].append(line.strip())
    return out


def _fit_size(lines: list[str], width_emu: int, height_emu: int,
              sizes: tuple[int, ...] = _POSTER_SIZES,
              char_w: float = 0.5) -> tuple[int, bool]:
    """Largest point size at which the text plausibly fits. (size, fits)."""
    import math
    w, h = width_emu / _PT, height_emu / _PT
    for size in sizes:
        per_line = max(1, int(w / (char_w * size)))
        n = sum(max(1, math.ceil(len(l) / per_line)) for l in lines) or 1
        if n * size * 1.25 <= h * 0.92:
            return size, True
    return sizes[-1], False


def _first_level_is_heading(layout_ph) -> bool:
    """Does the box's list level 1 carry heading styling (numbered, bold or caps)?

    Poster templates often reserve level 1 for a block subtitle and put body text
    on level 2. Writing body text at level 1 there renders it bold, capitalised
    and numbered.
    """
    from pptx.oxml.ns import qn
    lvl1 = layout_ph._element.find(f".//{qn('a:lstStyle')}/{qn('a:lvl1pPr')}")
    if lvl1 is None:
        return False
    rpr = lvl1.find(qn("a:defRPr"))
    styled = rpr is not None and (rpr.get("b") == "1" or rpr.get("cap") == "all")
    return styled or lvl1.find(qn("a:buAutoNum")) is not None


def _fill(ph, lines: list[str], size: int | None = None,
          heading_level: bool = False) -> None:
    """Write lines into a placeholder.

    "## x" is a block subtitle; "- x" a point; anything else plain prose. With a
    heading-styled level 1 the subtitle uses it and body text drops to level 2.
    """
    from pptx.oxml.ns import qn
    from pptx.util import Pt

    tf = ph.text_frame
    tf.clear()
    tf.word_wrap = True
    body_lvl = 1 if heading_level else 0
    for i, raw in enumerate(lines or [""]):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        point = raw[:2] in ("- ", "* ", "• ")
        sub = raw.startswith("## ")
        text = raw[3:].strip() if sub else (raw[2:].strip() if point else raw)
        para.text = text
        para.level = 0 if sub else body_lvl
        if not point and not (sub and heading_level):
            ppr = para._p.get_or_add_pPr()
            for tag in ("a:buNone", "a:buAutoNum", "a:buChar", "a:buBlip"):
                for el in ppr.findall(qn(tag)):
                    ppr.remove(el)
            ppr.append(ppr.makeelement(qn("a:buNone"), {}))
            ppr.set("marL", "0")
            ppr.set("indent", "0")
        for run in para.runs:
            if size:
                run.font.size = Pt(size)
            if sub and not heading_level:
                run.font.bold = True


@app.tool()
async def create_poster(
    title: str,
    sections: str,
    authors: str = "",
    band: str = "",
    template: str = "",
    layout: str = "auto",
    filename: str = "",
) -> list[TextContent]:
    """Create a conference poster (.pptx) filled into the researcher's own template.

    The poster template is stored in Metis (see list_templates) and used by
    default — never ask the researcher for the file or where it is.

    The template (.potx or .pptx) is looked up in system/config/local/templates/,
    knowledge/templates/, or $METIS_TEMPLATES_DIR — or pass a path. Each layout's
    section boxes are detected from its geometry, so any template with a title,
    small section headers and large content boxes works.

    Args:
        title: Poster title.
        sections: The poster body as plain text. Each section starts with a line
            beginning "# " (its heading); following lines are its text. Lines
            beginning "- " become points, "## " a block subtitle inside the box,
            anything else plain prose. Sections fill the boxes down the first
            column, then the next. Example:

                # Background
                - Why the question matters
                # Methods
                - Design, setting, data
                # Results
                - The main finding, with its number
        authors: Authors line, shown under the title.
        band: Optional text for the band below the title — affiliations, or a
            one-sentence key message.
        template: Template file name (or part of it) or a path. Empty = the first
            template found; the result says which one was used.
        layout: "auto" (smallest layout with enough boxes), or part of a layout
            name such as "one column" / "two column".
        filename: Optional output filename; derived from the title when omitted.

    Returns:
        The path written, the template and layout used, and any section whose text
        is likely to overflow its box.
    """
    if not title.strip() or not sections.strip():
        return [TextContent(type="text", text="A title and sections are required.")]
    if len(sections) > _MAX_CHARS:
        return [TextContent(type="text", text="Sections too large.")]
    try:
        import pptx  # noqa: F401
    except ImportError:
        return [TextContent(type="text", text=(
            "python-pptx is not installed in the Metis environment.\n"
            "Install it with:  ~/.local/share/metis-mcp/.venv/bin/pip install python-pptx"
        ))]

    # ── Template ────────────────────────────────────────────────────────────
    # Prefer a template named as a poster; a deck template is a different shape.
    tpl = _pick_template(template, "poster", (".potx", ".pptx"))
    if tpl is None and not template.strip():
        found = _find_templates()
        tpl = found[0] if found else None
    if tpl is None:
        where = "\n".join(f"  - {d}" for d in _template_dirs())
        have = ", ".join(p.name for p in _find_templates()) or "none"
        return [TextContent(type="text", text=(
            f"No poster template matched '{template or '(any)'}'. Templates found: {have}.\n"
            f"Put a .potx or .pptx in one of:\n{where}"
        ))]

    try:
        prs = _open_template(tpl)
    except Exception as exc:  # noqa: BLE001
        return [TextContent(type="text", text=f"Could not open template {tpl.name}: {exc}")]

    parsed = _parse_sections(sections)

    # ── Layout ──────────────────────────────────────────────────────────────
    layouts = [(l, _poster_slots(l)) for l in prs.slide_layouts]
    layouts = [(l, s) for l, s in layouts if s["pairs"]]
    if not layouts:
        return [TextContent(type="text", text=(
            f"{tpl.name} has no layout with content boxes to fill."))]
    if layout.strip().lower() not in ("", "auto"):
        want = layout.strip().lower()
        layouts = [(l, s) for l, s in layouts if want in l.name.lower()] or layouts
    layouts.sort(key=lambda ls: len(ls[1]["pairs"]))
    chosen = next(((l, s) for l, s in layouts if len(s["pairs"]) >= len(parsed)),
                  layouts[-1])
    lay, slots = chosen
    capacity = len(slots["pairs"])
    if len(parsed) > capacity:
        return [TextContent(type="text", text=(
            f"{len(parsed)} sections, but the largest layout in {tpl.name} "
            f"('{lay.name}') has {capacity} boxes. Merge sections and try again."))]

    # ── Build: drop the template's sample slides, add one poster slide ─────
    sld_ids = prs.slides._sldIdLst
    for sld in list(sld_ids):
        prs.part.drop_rel(sld.rId)
        sld_ids.remove(sld)
    slide = prs.slides.add_slide(lay)
    by_idx = {ph.placeholder_format.idx: ph for ph in slide.placeholders}

    def _on_slide(layout_ph):
        return by_idx.get(layout_ph.placeholder_format.idx) if layout_ph is not None else None

    from pptx.util import Pt

    # Titles are capitalised in most poster templates, so size them as wide
    # glyphs; a title that does not fit grows out of the top of its box.
    for key, value, sizes, char_w in (("title", title, _TITLE_SIZES, 0.52),
                                      ("subtitle", authors, _TITLE_SIZES, 0.62),
                                      ("band", band, _POSTER_SIZES, 0.55)):
        lp = slots[key]
        if (ph := _on_slide(lp)) is None or not value.strip():
            continue
        ph.text_frame.text = value.strip()
        size, _ = _fit_size([value.strip()], lp.width, lp.height, sizes, char_w)
        for para in ph.text_frame.paragraphs:
            for run in para.runs:
                run.font.size = Pt(size)

    overflow: list[str] = []
    filled: set[int] = set()
    for sec, (head, box) in zip(parsed, slots["pairs"]):
        if (hp := _on_slide(head)) is not None:
            hp.text_frame.text = sec["heading"]
            filled.add(hp.placeholder_format.idx)
        bp = _on_slide(box)
        if bp is None:
            continue
        size, fits = _fit_size(sec["lines"], box.width, box.height)
        _fill(bp, sec["lines"], size, heading_level=_first_level_is_heading(box))
        filled.add(bp.placeholder_format.idx)
        if not fits:
            overflow.append(sec["heading"] or "(untitled section)")

    # Unused boxes would print as "Click to add text" prompts — remove them.
    for head, box in slots["pairs"][len(parsed):]:
        for lp in (head, box):
            sp = _on_slide(lp)
            if sp is not None and sp.placeholder_format.idx not in filled:
                sp._element.getparent().remove(sp._element)
    for key, value in (("subtitle", authors), ("band", band)):
        sp = _on_slide(slots[key])
        if sp is not None and not value.strip():
            sp._element.getparent().remove(sp._element)

    stem = _slug(re.sub(r"\.pptx?$", "", filename, flags=re.I) or title)
    target = _safe_target("posters", f"{datetime.now().date().isoformat()}_{stem}.pptx")
    prs.save(str(target))

    msg = [f"Poster saved to: {target.relative_to(paths.root)}"]
    # Under WSL the researcher opens files from Windows, where a /mnt/c/... path
    # means nothing; give the clickable form as well.
    m = re.match(r"^/mnt/([a-z])/(.*)$", str(target))
    if m:
        msg.append("Open it from Windows: " + m.group(1).upper() + ":\\"
                   + m.group(2).replace("/", "\\"))
    msg += [
        f"Template: {tpl.name} · layout '{lay.name}' · "
        f"{len(parsed)} of {capacity} sections filled · "
        f"{prs.slide_width / 360000:.0f} × {prs.slide_height / 360000:.0f} cm",
    ]
    if overflow:
        msg.append("Likely to overflow at the smallest size — shorten: "
                   + ", ".join(overflow))
    msg.append("Figures go in by hand in PowerPoint; the content boxes accept a pasted image.")
    return [TextContent(type="text", text="\n".join(msg))]


# ---------------------------------------------------------------------------
# Document templates — a formal letter filled in place
# ---------------------------------------------------------------------------
#
# An institutional letter template is mostly fixed text with a few marked gaps
# ("<TITLE>", "<1 paragraph ...>"). Rewriting it from scratch loses the
# letterhead and the institution's wording; filling it paragraph by paragraph
# keeps both. Each paragraph keeps its first run's formatting.

_DOC_EXTS = (".docx", ".dotx")


def _open_doc_template(p: Path):
    """Open a .docx, or a .dotx — python-docx refuses a template only by content type."""
    import io
    import zipfile
    from docx import Document

    if p.suffix.lower() != ".dotx":
        return Document(str(p))
    buf = io.BytesIO()
    with zipfile.ZipFile(p) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(b"wordprocessingml.template.main+xml",
                                    b"wordprocessingml.document.main+xml")
            zout.writestr(item, data)
    buf.seek(0)
    return Document(buf)


def _doc_slots(doc) -> list[tuple[str, object]]:
    """Every paragraph that can be edited, keyed p<N> (body) or h<N> (header)."""
    slots = [(f"p{i}", para) for i, para in enumerate(doc.paragraphs)]
    n = 0
    for sec in doc.sections:
        for para in sec.header.paragraphs:
            slots.append((f"h{n}", para))
            n += 1
    return slots


def _set_para_text(para, text: str) -> None:
    runs = para.runs
    if not runs:
        para.add_run(text)
        return
    runs[0].text = text
    for r in runs[1:]:
        r._element.getparent().remove(r._element)


@app.tool()
async def read_document_template(template: str = "") -> list[TextContent]:
    """Show a stored Word template paragraph by paragraph, so it can be filled in.

    The researcher's templates (e.g. an ethics-committee cover letter) are kept in
    Metis — see list_templates; never ask them for the file. Returns each
    non-empty paragraph with its key (p12, h0 for the header). Then call
    fill_document_template with the keys whose text should change.

    Args:
        template: Template name or part of it. Empty = the first stored document template.
    """
    try:
        import docx  # noqa: F401
    except ImportError:
        return [TextContent(type="text", text=(
            "python-docx is not installed.\n"
            "Install with: ~/.local/share/metis-mcp/.venv/bin/pip install python-docx"))]
    tpl = _pick_template(template, "document", _DOC_EXTS)
    if tpl is None:
        have = ", ".join(p.name for p in _find_templates(_DOC_EXTS)) or "none"
        return [TextContent(type="text", text=f"No document template matched '{template}'. Stored: {have}.")]
    doc = _open_doc_template(tpl)
    lines = [f"Template: {tpl.name}. Keys of the paragraphs to fill (empty ones omitted):", ""]
    for key, para in _doc_slots(doc):
        if para.text.strip():
            lines.append(f"{key}: {para.text}")
    lines += ["", "Placeholders look like <...>, '……', 'X.X' or 'DD-MMM-YYYY'. Fill them with "
              "fill_document_template; mark anything the researcher must still decide as "
              "[TO COMPLETE: ...] rather than inventing it."]
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def fill_document_template(
    edits: str,
    template: str = "",
    filename: str = "",
) -> list[TextContent]:
    """Fill a stored Word template (e.g. an ethics-committee cover letter) and save a copy.

    Call read_document_template first to get the paragraph keys. The template's
    letterhead, styles and fixed wording are kept; only the listed paragraphs change.

    Args:
        edits: JSON object mapping paragraph keys to their new text, e.g.
            {"p5": "Antwerp, 14 October 2026", "p19": "This study ...", "h0": ""}.
            An empty string empties that paragraph; null deletes it.
        template: Template name or part of it. Empty = the first stored document template.
        filename: Output name; derived from the template when omitted.

    Returns:
        Where the filled document was saved, including a path that opens from Windows.
    """
    import json
    try:
        import docx  # noqa: F401
    except ImportError:
        return [TextContent(type="text", text=(
            "python-docx is not installed.\n"
            "Install with: ~/.local/share/metis-mcp/.venv/bin/pip install python-docx"))]
    try:
        changes = json.loads(edits)
        assert isinstance(changes, dict)
    except Exception:  # noqa: BLE001
        return [TextContent(type="text", text='edits must be a JSON object like {"p5": "new text"}.')]
    tpl = _pick_template(template, "document", _DOC_EXTS)
    if tpl is None:
        have = ", ".join(p.name for p in _find_templates(_DOC_EXTS)) or "none"
        return [TextContent(type="text", text=f"No document template matched '{template}'. Stored: {have}.")]

    doc = _open_doc_template(tpl)
    slots = dict(_doc_slots(doc))
    unknown = [k for k in changes if k not in slots]
    if unknown:
        return [TextContent(type="text", text=(
            f"Unknown paragraph keys: {', '.join(unknown)}. Use read_document_template for the keys."))]
    deleted = 0
    for key, text in changes.items():
        para = slots[key]
        if text is None:
            para._element.getparent().remove(para._element)
            deleted += 1
        else:
            _set_para_text(para, str(text))

    stem = _slug(re.sub(r"\.docx?$", "", filename, flags=re.I) or tpl.stem)
    target = _safe_target("letters", f"{datetime.now().date().isoformat()}_{stem}.docx")
    doc.save(str(target))
    left = [k for k, p in _doc_slots(doc) if re.search(r"<[^>]{2,}>|……|\bX\.X\b|DD-MMM-YYYY", p.text)]
    msg = [f"Filled {len(changes) - deleted} paragraph(s), removed {deleted}, from {tpl.name}.",
           f"Saved to: {target.relative_to(paths.root)}"]
    m = re.match(r"^/mnt/([a-z])/(.*)$", str(target))
    if m:
        msg.append("Open it from Windows: " + m.group(1).upper() + ":\\"
                   + m.group(2).replace("/", "\\"))
    if left:
        msg.append(f"Still contains template placeholders in: {', '.join(left)}")
    return [TextContent(type="text", text="\n".join(msg))]


# ---------------------------------------------------------------------------
# Opening what was made
# ---------------------------------------------------------------------------
#
# A file written by a tool is invisible in a chat client. This opens it in its
# own application on the researcher's screen — PowerPoint, Word — so the work
# is seen, not just reported. Only files under outputs/ can be opened: this is
# a viewer for Metis's own products, not a general launcher.

def _windows_path(p: Path) -> str | None:
    m = re.match(r"^/mnt/([a-z])/(.*)$", str(p))
    return (m.group(1).upper() + ":\\" + m.group(2).replace("/", "\\")) if m else None


@app.tool()
async def open_output(paths_to_open: str) -> list[TextContent]:
    """Open files Metis created (decks, posters, letters, figures) on the researcher's screen.

    Call this at the end when the researcher asks to see, show or open what was
    made. Each file opens in its own Windows application (PowerPoint, Word, the
    browser). Only files under outputs/ can be opened.

    Args:
        paths_to_open: One or more paths as returned by the tool that wrote them
            (e.g. "outputs/presentations/2026-10-14_x.pptx"), separated by
            newlines or commas. Windows paths are accepted too.
    """
    import os
    import subprocess
    from metis_mcp.tools.files import resolve_user_path

    base = (paths.root / "outputs").resolve()
    explorer = "/mnt/c/Windows/explorer.exe"
    opened, refused = [], []
    for raw in re.split(r"[\n,]+", paths_to_open or ""):
        if not raw.strip():
            continue
        p = resolve_user_path(raw.strip()).resolve()
        if base not in p.parents or not p.is_file():
            refused.append(raw.strip())
            continue
        win = _windows_path(p)
        try:
            if win and os.path.exists(explorer):
                # explorer.exe opens the file with its default application and
                # exits 1 even on success, so its status is not checked.
                subprocess.Popen([explorer, win], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
            elif os.name == "nt":
                os.startfile(str(p))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(p)], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
            opened.append(p.name)
        except Exception as exc:  # noqa: BLE001
            refused.append(f"{raw.strip()} ({exc})")
    lines = []
    if opened:
        lines.append("Opened on screen: " + ", ".join(opened))
    if refused:
        lines.append("Not opened (not a file Metis made under outputs/): " + ", ".join(refused))
    return [TextContent(type="text", text="\n".join(lines) or "Nothing to open.")]


# ---------------------------------------------------------------------------
# Figures — a chart made in a chat, kept with its project
# ---------------------------------------------------------------------------
#
# A visual drawn as an artifact in a chat client lives only in that chat. This
# files it under outputs/figures/<project>/ where the dashboard's project panel
# shows it, so the work outlives the conversation. The file is the one author:
# the panel lists the folder, so there is no second store to drift from it.

_MAX_FIGURE = 3_000_000


@app.tool()
async def save_project_figure(
    project_id: str,
    title: str,
    html: str,
    caption: str = "",
) -> list[TextContent]:
    """Save a finished chart or visual (HTML) to a project so it shows on the dashboard.

    Use after drawing a figure as an artifact: pass the same self-contained HTML
    (inline SVG, or a chart library loaded from a CDN). It is stored under the
    project and appears in the Figures section of that project's panel on the
    Work tab, where it renders live. Saving again with the same title replaces it.

    Args:
        project_id: The project slug (as returned when the project was created).
        title: Short figure title, shown above it on the dashboard.
        html: The figure as HTML — a full page, or a fragment that will be wrapped.
        caption: One or two sentences on what the figure shows, including the
            denominator and data source.

    Returns:
        Where it was saved and the dashboard link that shows it.
    """
    import html as _htmlmod
    import json
    from metis_mcp.db import connect

    if not html.strip() or not title.strip():
        return [TextContent(type="text", text="A title and the figure's HTML are required.")]
    if len(html) > _MAX_FIGURE:
        return [TextContent(type="text", text="Figure too large (over 3 MB).")]
    try:
        with connect(paths.db) as con:
            row = con.execute("SELECT title FROM projects WHERE project_id = ?",
                              (project_id,)).fetchone()
    except Exception as exc:  # noqa: BLE001
        return [TextContent(type="text", text=f"Could not read projects: {exc}")]
    if not row:
        return [TextContent(type="text", text=(
            f"No project `{project_id}`. Use the id returned when the project was "
            "created (get_project_status lists them)."))]

    if "<html" not in html.lower():
        html = ("<!doctype html><html><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                f"<title>{_htmlmod.escape(title)}</title></head><body>{html}</body></html>")
    stem = _slug(title)
    target = _safe_target(f"figures/{_slug(project_id, 80)}", f"{stem}.html")
    target.write_text(html, encoding="utf-8")
    target.with_suffix(".json").write_text(json.dumps({
        "title": title.strip(), "caption": caption.strip(), "project_id": project_id,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    port = 8080
    msg = [
        f"Figure saved to project '{row[0]}': {target.relative_to(paths.root)}",
        f"On the dashboard: Work tab → open '{row[0]}' → Figures.",
        f"Direct link: http://127.0.0.1:{port}/figures/{target.parent.name}/{target.name}",
    ]
    return [TextContent(type="text", text="\n".join(msg))]


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@app.tool()
async def create_document(
    title: str,
    content: str,
    subdir: str = "reviews",
    fmt: str = "md",
) -> list[TextContent]:
    """Write a document to outputs/ — Markdown or Word (.docx).

    The general "save this properly" tool. Without it, anything Metis produces in
    a chat client exists only in the transcript, which is not somewhere work can
    be found again.

    Args:
        title: Document title; heads the file and derives its name.
        content: Body text. Markdown headings and bullets are honoured in both
            formats.
        subdir: Folder under outputs/ (default "reviews").
        fmt: "md" (default) or "docx".

    Returns:
        The path written.
    """
    if not title.strip() or not content.strip():
        return [TextContent(type="text", text="Both a title and content are required.")]
    if len(content) > _MAX_CHARS:
        return [TextContent(type="text", text="Content too large.")]
    if fmt not in ("md", "docx"):
        return [TextContent(type="text", text="fmt must be 'md' or 'docx'.")]

    stem = f"{datetime.now().date().isoformat()}_{_slug(title)}"

    if fmt == "md":
        target = _safe_target(subdir, f"{stem}.md")
        target.write_text(f"# {title.strip()}\n\n{content}\n", encoding="utf-8")
    else:
        try:
            from docx import Document
        except ImportError:
            return [TextContent(type="text", text=(
                "python-docx is not installed.\n"
                "Install with: ~/.local/share/metis-mcp/.venv/bin/pip install python-docx"
            ))]
        doc = Document()
        doc.add_heading(title.strip(), level=0)
        for raw in content.splitlines():
            line = raw.rstrip()
            if not line.strip():
                continue
            stripped = line.lstrip()
            if stripped.startswith("### "):
                doc.add_heading(stripped[4:], level=3)
            elif stripped.startswith("## "):
                doc.add_heading(stripped[3:], level=2)
            elif stripped.startswith("# "):
                doc.add_heading(stripped[2:], level=1)
            elif stripped.startswith(("- ", "* ", "• ")):
                doc.add_paragraph(stripped[2:], style="List Bullet")
            else:
                doc.add_paragraph(line)
        target = _safe_target(subdir, f"{stem}.docx")
        doc.save(str(target))

    return [TextContent(type="text", text=(
        f"Saved to: {target.relative_to(paths.root)}"
    ))]


@app.tool()
async def list_outputs(subdir: str = "", limit: int = 30) -> list[TextContent]:
    """List what Metis has produced, newest first.

    Exists because a file written by a tool is invisible to a chat client — the
    researcher has no way to see what was created without going to the folder.
    """
    base = (paths.root / "outputs").resolve()
    root = (base / subdir).resolve() if subdir else base
    if not str(root).startswith(str(base)) or not root.is_dir():
        return [TextContent(type="text", text=f"No such folder under outputs/: {subdir}")]

    files = sorted((p for p in root.rglob("*") if p.is_file()
                    and not p.name.startswith(".")),
                   key=lambda p: p.stat().st_mtime, reverse=True)[:max(1, limit)]
    if not files:
        return [TextContent(type="text", text=f"Nothing in outputs/{subdir}.")]

    lines = [f"{len(files)} file(s) in outputs/{subdir or ''}:", ""]
    for f in files:
        kb = f.stat().st_size // 1024
        when = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"  {when}  {kb:>6} KB  {f.relative_to(base)}")
    return [TextContent(type="text", text="\n".join(lines))]
