---
name: metis-library-setup
description: "set up library, configure zotero, configure mendeley, connect reference manager, import papers, library setup, zotero setup, mendeley setup, connect my library"
model: claude-sonnet-4-6
---

## Purpose

Walk the user through connecting their reference manager (Zotero or Mendeley) to Metis.
After setup, all their papers are searchable, appear in the Knowledge tab, and can be
organised by AI topic clustering.

## Step 1 — Ask which reference manager

Ask exactly:

> "Do you use **Zotero** or **Mendeley** to manage your papers?
> (Or neither — in that case I can still import papers from a folder or BibTeX file.)"

Wait for their answer before proceeding.

---

## If they say **Zotero**

### Step 2a — Check if already configured

Call `get_library_stats()`. If it returns Zotero items, the connection is already set up —
tell them and offer to run a sync instead.

### Step 2b — Get API credentials

Explain:

> "To connect Zotero, I need two things from you:
>
> **Step 1 — Get your API key:**
> 1. Go to https://www.zotero.org/settings/keys (you must be logged in)
> 2. Click **Create new private key**
> 3. Give it a name like "Metis" and tick **Allow library access** (read-only is fine)
> 4. Click **Save Key** and copy the key shown
>
> **Step 2 — Get your User ID:**
> On that same page, your numeric User ID is shown at the top (e.g. `12345678`)
>
> Paste both here when you have them."

Wait for their key and ID.

### Step 3a — Configure and sync

Call `configure_library_provider(provider="zotero", api_key="...", user_id="...")`.
Then immediately call `sync_zotero_library()` to import the full library.
Report how many papers were imported.

### Step 4a — Offer organisation

Say: "Your library is now synced. Want me to run an AI topic analysis to suggest
how to organise your papers into collections? (Run `propose_library_organization()`)"

---

## If they say **Mendeley**

### Step 2b — Export instructions

Explain:

> "Mendeley's API requires a complex setup, so the recommended approach is to
> export your library as BibTeX — it takes about 30 seconds:
>
> 1. Open **Mendeley Desktop** (or Mendeley Reference Manager)
> 2. Go to **File → Export** (or select all papers with Ctrl+A, then File → Export)
> 3. Choose **BibTeX (.bib)** format
> 4. Save the file somewhere you can find it (e.g. Downloads folder)
>
> Tell me the full path to the file when it's ready.
> Example: `C:\Users\you\Downloads\library.bib`"

Wait for the path.

### Step 3b — Import

Call `configure_library_provider(provider="mendeley", bibtex_path="...")`.
Report how many papers were imported.

### Step 4b — Tip

Say: "To add new Mendeley papers in the future, just re-export and I'll import the
new ones automatically (duplicates are skipped)."

---

## If they say **neither / folder / BibTeX file**

- If they have a folder of PDFs: guide them to run `scan_literature()` which will
  discover and register all PDFs in inputs/literature/
- If they have a BibTeX file from any source: call `import_bibtex_library(bibtex_path="...")`

---

## After any setup

Always end with:
- `get_library_stats()` — show the final paper count
- Remind them: "Run `/metis-update literature` anytime to check for new papers,
  or `/librarian` to search and explore your library"
