# pdf-meta-extractor

Standalone Python CLI tool that reads a folder of PDF papers and outputs a CSV with:

| Column | Description |
|---|---|
| `filepath` | Absolute path to the PDF |
| `filename` | PDF filename |
| `title` | Paper title |
| `authors` | Author list (semicolon-separated) |
| `year` | Publication year |
| `doi` | DOI (e.g. `10.1234/abc`) |
| `abstract` | Abstract text (up to `--max-abstract` characters) |
| `source` | Where metadata came from: `pdf_meta`, `text_parse`, `crossref`, or `filename` |
| `warnings` | Any extraction warnings |

---

## Quick start

```bash
# 1. Install dependencies (one time)
bash setup.sh

# 2. Run on a folder of PDFs
python extract_pdf_metadata.py /path/to/papers/

# 3. Check the output
open pdf_metadata.csv
```

---

## Installation

### Recommended (into active Python / venv)
```bash
bash setup.sh
```

### Isolated virtual environment
```bash
bash setup.sh --venv
source .venv/bin/activate
```

### Manual install
```bash
pip install pymupdf pypdf pdfminer.six requests
```

---

## Usage

```
python extract_pdf_metadata.py <folder> [options]

Arguments:
  folder                   Folder containing PDF files

Options:
  -o, --output PATH        Output CSV path (default: pdf_metadata.csv)
  --crossref               Enrich missing metadata via Crossref API
  --email EMAIL            Your email for Crossref polite pool
  --max-abstract N         Max characters for abstract (default: 1500)
  --recursive              Scan subfolders recursively
  --delay SECONDS          Pause between Crossref calls (default: 1.0)
  -v, --verbose            Print per-file progress
  -h, --help               Show this help
```

---

## Examples

**Basic extraction:**
```bash
python extract_pdf_metadata.py ~/papers/
```

**Custom output path:**
```bash
python extract_pdf_metadata.py ~/papers/ -o ~/Desktop/library.csv
```

**With Crossref enrichment (requires internet):**
```bash
python extract_pdf_metadata.py ~/papers/ --crossref --email you@example.com
```

**Recursive scan with verbose output:**
```bash
python extract_pdf_metadata.py ~/papers/ --recursive -v -o full_library.csv
```

**Longer abstracts:**
```bash
python extract_pdf_metadata.py ~/papers/ --max-abstract 3000
```

---

## How it works

Metadata is extracted in three passes, stopping as soon as enough is found:

1. **Embedded PDF metadata** — reads title, author, and creation date from the PDF's internal metadata fields (fastest, works when publishers embed it correctly)
2. **Text parsing** — extracts and parses the first 3 pages to find DOI patterns, year, title candidates, and abstract sections
3. **Crossref API** (optional, `--crossref`) — looks up remaining gaps by DOI or title search

If no PDF library is installed, falls back to parsing the filename (works well for files named like `2023_Surname_Title.pdf`).

### PDF backends (tried in order)
| Library | Quality | Notes |
|---|---|---|
| PyMuPDF (`pymupdf`) | Best | Handles complex layouts, fastest |
| pypdf | Good | Pure Python, no binary dependencies |
| pdfminer.six | Fallback | Slower, no embedded metadata |

---

## Output example

```csv
filepath,filename,title,authors,year,doi,abstract,source,warnings
/papers/jones2022.pdf,jones2022.pdf,Passive surveillance of HAT in DRC,...,Jones, A; Smith, B,2022,10.1016/j.pntd.2022.01.001,Background: Human African trypanosomiasis...,pdf_meta,
```

---

## Integration with Metis library

To import the output into the Metis library database, use the MCP tool:
```
mcp__metis-rc__import_bibtex_library
```
or manually import rows with `mcp__metis-rc__search_library`.

---

## Requirements

- Python 3.8+
- At least one of: `pymupdf`, `pypdf`, `pdfminer.six`
- `requests` (for `--crossref` only)

No internet required unless `--crossref` is passed.

---

## Troubleshooting

**"No PDF library found"** — run `bash setup.sh` or `pip install pymupdf`

**Low coverage (many empty fields)** — try `--crossref` to fill gaps via Crossref

**DOIs found but abstract missing** — many PDFs have scanned (image) pages; PyMuPDF handles these best

**PyMuPDF install fails on Linux** — try `pip install pymupdf --no-binary pymupdf`
