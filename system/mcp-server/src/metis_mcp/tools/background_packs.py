"""background_packs.py — make a knowledge background a thing you can hand over.

THE PROBLEM (Keystone P4.3)
    A "background" was a database row plus a list of LOCAL FOLDER PATHS, and its
    content was PDFs sitting on one machine. There was nothing to give anyone: no
    manifest, no version, no bundle. "Download a background" could not be built
    because a background was not an object.

THE SHAPE (owner's decision, 2026-08-12)
    A pack is a small JSON manifest of OPEN-ACCESS SOURCES that ships inside the
    Metis repo; installing it fetches those documents onto the researcher's own
    machine and indexes them locally. Chosen over shipping the PDFs themselves
    because it keeps the repo small, avoids redistributing other people's
    copyrighted work, and still works for the published base edition — which now
    ships with no backgrounds at all (P4.6) and needs a way to gain one.

    backgrounds/<slug>/pack.json
      { slug, name, version, description, folder, sources: [ ... ] }

    A source is one of two kinds:
      {title, url, filename}                     — fetched on install
      {title, access: "manual", doi|isbn, note}  — named, never fetched

    The second kind exists because most fields have a canonical text that no script
    can retrieve: the publisher gates it behind a browser check, or it is behind an
    institutional subscription. Omitting those would make a pack quietly claim the
    field is covered by whatever was downloadable. Instead they are written to
    `_TO-OBTAIN.md` inside the target folder, with DOIs. Because a layer indexes its
    FOLDER, a PDF dropped in later needs no re-install and no manifest edit.

    `folder` is relative to knowledge/library/, so an installed pack lands beside
    the layers that are already there and is indexed by exactly the same path.

WHAT IS DELIBERATELY NOT HERE
    No pack registry, no remote index, no auto-update. Those need a hosting story
    and a trust story, and neither exists yet. A manifest in the repo can be read,
    reviewed and edited by the person installing it — which is the right first
    version of "where does this content come from?".
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

log = logging.getLogger("metis.background_packs")

PACK_DIR_NAME = "backgrounds"
# Only http(s), and only to hosts the manifest names. A pack manifest is data, and
# data that can make the machine fetch arbitrary schemes (file://, ftp://) is an
# attack surface, not a feature.
_ALLOWED_SCHEMES = ("http://", "https://")


def _packs_root() -> Path:
    return paths.root / PACK_DIR_NAME


def _read_pack(slug: str) -> dict | None:
    f = _packs_root() / slug / "pack.json"
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _installed_slugs() -> dict[str, dict]:
    out: dict[str, dict] = {}
    try:
        with connect(paths.db) as con:
            for r in con.execute(
                "SELECT slug, name, COALESCE(enabled,1) AS enabled, doc_count, last_built "
                "FROM knowledge_databases"
            ).fetchall():
                out[r["slug"]] = dict(r)
    except Exception:
        pass
    return out


@app.tool()
async def list_background_packs() -> list[TextContent]:
    """List the knowledge background packs available to install, and what is already installed.

    A pack is a curated set of open-access documents for a subject area. Installing
    one downloads those documents to your machine and indexes them so questions can
    be grounded in them.
    """
    root = _packs_root()
    installed = _installed_slugs()
    lines = ["**Knowledge background packs**", ""]

    available = []
    if root.is_dir():
        for d in sorted(root.iterdir()):
            if d.is_dir() and (pack := _read_pack(d.name)):
                available.append(pack)

    if available:
        lines.append("**Available to install:**")
        for p in available:
            slug = p.get("slug", "?")
            mark = "already installed" if slug in installed else f"{len(p.get('sources', []))} document(s)"
            lines.append(f"- `{slug}` — {p.get('name', slug)} v{p.get('version', '?')} · {mark}")
            if p.get("description"):
                lines.append(f"    {p['description']}")
        lines.append("")
    else:
        lines.append("_No packs are bundled with this copy of Metis._\n")

    if installed:
        lines.append("**Installed on this machine:**")
        for slug, d in sorted(installed.items()):
            state = "on" if d["enabled"] else "off"
            built = (d.get("last_built") or "")[:10] or "not indexed"
            lines.append(f"- `{slug}` — {d['name']} · {d.get('doc_count') or 0} docs · {state} · built {built}")

    lines += ["", "Install one with: install_background_pack('<slug>')"]
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def install_background_pack(slug: str, confirm: bool = False) -> list[TextContent]:
    """Install a knowledge background pack: fetch its documents and register the layer.

    Without confirm=True this only reports what WOULD be downloaded — a pack fetches
    files from the internet, so the researcher should see the list and the hosts
    before it runs.

    Indexing is NOT run here; it happens on the next nightly background index, or
    immediately via the Rebuild button on the Library surface.

    Args:
        slug: The pack's slug, from list_background_packs().
        confirm: True to actually download and register.
    """
    pack = _read_pack(slug)
    if not pack:
        return [TextContent(type="text", text=f"No pack called '{slug}'. Try list_background_packs().")]

    sources = [s for s in (pack.get("sources") or []) if isinstance(s, dict)]
    folders = [f.strip("/") for f in (pack.get("folders") or []) if str(f).strip()]
    folder = (folders[0] if folders else (pack.get("folder") or f"open-access-books/{slug}")).strip("/")
    target = paths.root / "knowledge" / "library" / folder

    # A pack has two kinds of source. Most are open-access URLs Metis fetches.
    # The rest are `access: "manual"` — a canonical text that exists but cannot be
    # fetched by a script: it is behind a publisher's browser check, or behind an
    # institutional subscription. Those are named, never fetched, and handed back
    # as a shopping list. This is what keeps a pack honest: a background whose
    # field has a standard textbook should SAY so and stay redistributable,
    # rather than quietly substituting whatever happened to be downloadable.
    manual = [s for s in sources if s.get("access") == "manual" or not s.get("url")]
    fetchable = [s for s in sources if s not in manual]

    bad = [s for s in fetchable if not str(s.get("url", "")).startswith(_ALLOWED_SCHEMES)]
    if bad:
        return [TextContent(type="text", text=(
            f"Refused: '{slug}' contains {len(bad)} source(s) that are not plain http(s) links. "
            f"A pack manifest is data; it must not be able to make Metis fetch arbitrary schemes."
        ))]

    if not confirm:
        hosts = sorted({re.sub(r"^https?://([^/]+).*", r"\1", s["url"]) for s in fetchable})
        lines = [f"**{pack.get('name', slug)}** v{pack.get('version','?')} — "
                 f"{len(fetchable)} document(s) to download"
                 + (f", {len(manual)} you obtain yourself" if manual else ""),
                 f"Downloads to `knowledge/library/{folder}/`"
                 + (f" from: {', '.join(hosts)}" if hosts else ""), ""]
        for s in fetchable[:20]:
            lines.append(f"- {s.get('title') or s.get('filename')}")
        if len(fetchable) > 20:
            lines.append(f"- …and {len(fetchable)-20} more")
        if manual:
            lines += ["", f"**Not downloadable ({len(manual)})** — needs your library login or a browser:"]
            lines += [f"- {s.get('title')}" + (f" · {s['doi']}" if s.get("doi") else "") for s in manual[:20]]
        lines += ["", f"To go ahead: install_background_pack('{slug}', confirm=True)"]
        return [TextContent(type="text", text="\n".join(lines))]

    target.mkdir(parents=True, exist_ok=True)
    got, failed, skipped = 0, [], 0
    for s in fetchable:
        name = s.get("filename") or Path(s["url"]).name or "document.pdf"
        dest = target / re.sub(r"[^\w.\- ]", "_", name)
        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            continue
        try:
            # A browser-shaped User-Agent, because several open-access repositories
            # reject unfamiliar clients outright. NCBI Bookshelf returns 403 to
            # "Metis/1.0" while serving the identical URL to a browser — so the
            # first install of a perfectly valid pack failed on all 13 documents.
            # Requesting an open-access PDF is exactly what a browser does here;
            # this is not evading a restriction, it is meeting one.
            req = urllib.request.Request(s["url"], headers={
                "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
                "Accept": "application/pdf,*/*",
            })
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()

            # VERIFY WHAT ARRIVED — a 200 is not a PDF.
            #
            # Checking only for an empty file is not enough, and the first real
            # install proved it: both WHO IRIS links returned a 755-byte DSpace
            # HTML page with a 200 status, which was written out as a .pdf and
            # reported as "2 downloaded". Indexing those would have filled a
            # knowledge layer with website markup that answers could then cite.
            # A repository behind a redirect, a login wall or a rename fails
            # exactly this way, so the check belongs here permanently.
            if not body.startswith(b"%PDF-"):
                head = body[:200].decode("utf-8", "replace").strip().replace("\n", " ")
                raise OSError(
                    "not a PDF — the server returned "
                    + ("an HTML page" if b"<html" in body[:400].lower() else "something else")
                    + f" ({len(body)} bytes: {head[:60]}…). The link probably redirects or has moved."
                )
            dest.write_bytes(body)
            got += 1
        except Exception as exc:
            dest.unlink(missing_ok=True)
            failed.append(f"{name}: {exc}")

    # The shopping list lives IN the folder it refers to, not in the chat reply that
    # scrolls away. Drop a PDF beside it and the layer picks it up on the next index —
    # no re-install, no manifest edit, because the layer indexes the folder.
    if manual:
        lines = [f"# {pack.get('name', slug)} — still to obtain", "",
                 "These are standard texts for this field that a script cannot fetch: the",
                 "publisher requires a browser, or your institution's subscription.",
                 "Save each PDF into **this folder**. It will be indexed automatically",
                 "on the next rebuild — nothing else to do.", "",
                 "If you save them in Zotero instead (the browser connector, logged in",
                 "through your institution, keeps the citation too), put them in one",
                 "collection and ask Metis to import that collection into this layer —",
                 "it copies the PDFs here for you.", ""]
        for s in manual:
            lines.append(f"- **{s.get('title','?')}**")
            if s.get("doi"):
                lines.append(f"  - DOI: `{s['doi']}` · https://doi.org/{s['doi']}")
            if s.get("isbn"):
                lines.append(f"  - ISBN: `{s['isbn']}`"
                             + (f" — {s['isbn_note']}" if s.get("isbn_note") else "")
                             + f" · https://www.worldcat.org/isbn/{s['isbn']}")
            if s.get("note"):
                lines.append(f"  - {s['note']}")
        (target / "_TO-OBTAIN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if got == 0 and skipped == 0:
        # Registering a layer with nothing in it would put an empty background on
        # the Library surface and schedule a nightly index of no documents — a
        # feature that looks installed and is not. Fail visibly instead.
        return [TextContent(type="text", text="\n".join(
            [f"Could not install **{pack.get('name', slug)}** — none of its {len(fetchable)} "
             f"downloadable document(s) could be fetched, so no layer was created."
             + (f" ({len(manual)} manual entries were listed in "
                f"`knowledge/library/{folder}/_TO-OBTAIN.md`.)" if manual else ""), ""]
            + [f"- {f}" for f in failed[:10]]
            + ["", "The links in `backgrounds/" + slug + "/pack.json` may have moved. "
               "Fix them there and try again."]
        ))]

    # Register on PARTIAL download — a background with most of its documents is
    # useful, and the missing ones are named so they can be retried.
    try:
        with connect(paths.db) as con:
            con.execute(
                "INSERT OR IGNORE INTO knowledge_databases "
                "(slug, name, description, layer, color, folders) VALUES (?,?,?,?,?,?)",
                (slug, pack.get("name", slug), pack.get("description", ""), 5,
                 pack.get("color", "#7a8b99"), "\n".join(folders or [folder])),
            )
            con.execute("UPDATE knowledge_databases SET folders=? WHERE slug=?",
                        ("\n".join(folders or [folder]), slug))
            con.commit()
    except Exception as exc:
        return [TextContent(type="text", text=f"Downloaded {got} file(s) but could not register the layer: {exc}")]

    msg = [f"Installed **{pack.get('name', slug)}** — {got} downloaded"
           + (f", {skipped} already present" if skipped else "")
           + (f", {len(failed)} failed" if failed else "") + ".",
           f"Documents are in `knowledge/library/{folder}/`.",
           "It will be indexed by tonight's background index, or press Rebuild on the Library surface to do it now."]
    if failed:
        msg += ["", "Could not fetch:"] + [f"- {f}" for f in failed[:10]]
    if manual:
        ident = sum(1 for s in manual if s.get("doi") or s.get("isbn"))
        msg += ["", f"**{len(manual)} text(s) you need to fetch yourself** — listed in "
                    f"`knowledge/library/{folder}/_TO-OBTAIN.md`"
                    + (f" ({ident} with a DOI or ISBN, {len(manual)-ident} by title only)"
                       if ident < len(manual) else " with DOIs or ISBNs")
                    + ". Save the PDFs into that same folder and they join the layer on the "
                      "next rebuild."]
    return [TextContent(type="text", text="\n".join(msg))]


@app.tool()
async def export_background_pack(database: str, out_dir: str = "") -> list[TextContent]:
    """Write a pack manifest for one of your installed background layers.

    Produces the `pack.json` another machine (or another person) can install from.
    It records the layer's identity and the documents it contains BY NAME; it does
    not copy the PDFs, and it cannot invent a download URL for a file that came off
    your own disk — those entries are written with an empty url and must be filled
    in before the pack can be installed elsewhere. Saying so is the point: a
    manifest that silently omitted them would look complete and install empty.

    Args:
        database: The layer's slug (e.g. 'ntd').
        out_dir: Where to write it. Defaults to backgrounds/<slug>/ in the repo.
    """
    try:
        with connect(paths.db) as con:
            row = con.execute(
                "SELECT id, slug, name, description, folders FROM knowledge_databases WHERE slug=?",
                (database,),
            ).fetchone()
            if not row:
                return [TextContent(type="text", text=f"No knowledge layer called '{database}'.")]
            docs = [r["source_file"] for r in con.execute(
                "SELECT DISTINCT source_file FROM pdf_index_state WHERE db_id=?", (row["id"],)
            ).fetchall()]
    except Exception as exc:
        return [TextContent(type="text", text=f"Could not read '{database}': {exc}")]

    # Built-in layers keep their folder list in BUILTIN_DATABASES, not in the
    # `folders` column, which is empty for them. Guessing "open-access-books/<slug>"
    # produced `open-access-books/ntd` for a layer whose real folder is
    # `open-access-books/NTDs` — a manifest that looks right and installs nothing.
    # ALL folders, not just the first. ph-background spans 15 topic folders
    # (Health Systems, Governance, Equity, NCDs, …) and taking `[0]` produced a
    # manifest that claimed to be the public-health background while describing one
    # fifteenth of it — a pack that installs a sliver and looks complete.
    folders: list[str] = []
    if row["folders"]:
        folders = [f.strip() for f in row["folders"].splitlines() if f.strip()]
    else:
        try:
            from metis_mcp.tools.knowledge_db import BUILTIN_DATABASES

            for b in BUILTIN_DATABASES:
                if b["slug"] == database and b.get("folders"):
                    folders = list(b["folders"])
                    break
        except Exception:
            pass
    folders = folders or [f"open-access-books/{database}"]
    manifest = {
        "slug": row["slug"],
        "name": row["name"],
        "version": "1.0.0",
        "description": row["description"] or "",
        # `folder` stays for single-folder packs (installers read it); `folders`
        # carries the full set so a multi-topic layer round-trips intact.
        "folder": folders[0],
        "folders": folders,
        "sources": [{"title": Path(d).stem.replace("-", " ").replace("_", " ")[:120],
                     "filename": Path(d).name, "url": ""} for d in sorted(docs)],
    }

    dest_dir = Path(out_dir) if out_dir else (_packs_root() / row["slug"])
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "pack.json"
        dest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        return [TextContent(type="text", text=f"Could not write the manifest: {exc}")]

    missing = sum(1 for s in manifest["sources"] if not s["url"])
    note = (f"\n\n⚠ {missing} of {len(manifest['sources'])} entries have no download URL — they came "
            f"from your own disk. Fill those in before sharing, or the pack installs empty.") if missing else ""
    return [TextContent(type="text", text=(
        f"Wrote `{dest}` — {len(manifest['sources'])} document(s) from '{row['name']}'.{note}"
    ))]
