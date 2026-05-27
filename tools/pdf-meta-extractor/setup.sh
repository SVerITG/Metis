#!/usr/bin/env bash
# setup.sh — Install dependencies for pdf-meta-extractor
#
# Usage:
#   bash setup.sh              # Install into active Python / venv
#   bash setup.sh --venv       # Create a local .venv and install there

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

USE_VENV=false
for arg in "$@"; do
  [[ "$arg" == "--venv" ]] && USE_VENV=true
done

if $USE_VENV; then
  echo "Creating virtual environment at $SCRIPT_DIR/.venv ..."
  python3 -m venv "$SCRIPT_DIR/.venv"
  PIP="$SCRIPT_DIR/.venv/bin/pip"
  PYTHON="$SCRIPT_DIR/.venv/bin/python"
  echo ""
  echo "  Activate with: source $SCRIPT_DIR/.venv/bin/activate"
  echo "  Then run:      python extract_pdf_metadata.py <folder>"
else
  PIP="pip"
  PYTHON="python3"
fi

echo ""
echo "Installing PDF extraction libraries ..."
$PIP install --upgrade pip --quiet

# Primary: PyMuPDF (best quality, handles complex layouts)
if $PIP install pymupdf --quiet 2>/dev/null; then
  echo "  [ok] pymupdf"
else
  echo "  [skip] pymupdf (not available for this platform)"
fi

# Fallback 1: pypdf (pure Python)
$PIP install pypdf --quiet && echo "  [ok] pypdf"

# Fallback 2: pdfminer.six
$PIP install pdfminer.six --quiet && echo "  [ok] pdfminer.six"

# Crossref enrichment
$PIP install requests --quiet && echo "  [ok] requests (for --crossref)"

echo ""
echo "Setup complete."
echo ""
echo "Usage examples:"
echo "  $PYTHON $SCRIPT_DIR/extract_pdf_metadata.py /path/to/papers/"
echo "  $PYTHON $SCRIPT_DIR/extract_pdf_metadata.py /path/to/papers/ -o results.csv --crossref"
echo "  $PYTHON $SCRIPT_DIR/extract_pdf_metadata.py /path/to/papers/ --recursive -v"
