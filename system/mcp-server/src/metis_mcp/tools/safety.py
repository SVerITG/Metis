"""Data safety scanner for PII and sensitive content detection."""

import re

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.local_overrides import load_overrides

# PII detection patterns
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE_RE = re.compile(r"\+?\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}")
# International numbers written in small (e.g. 2-digit) groups — Belgian/French style
# "+32 478 12 34 56", "+243 81 234 5678". A privacy guard errs toward flagging.
_INTL_PHONE_RE = re.compile(r"\+\d{1,3}(?:[\s.\-/]?\d){7,}")
_PATIENT_ID_RE = re.compile(
    r"\b(?:patient_?id|case_?id|patient\s*#)\s*[:=]?\s*\d+", re.IGNORECASE
)
_GPS_RE = re.compile(
    # Coordinate pair with ≥4 decimal places each (~11 m — household-identifying).
    r"-?\d{1,3}\.\d{4,},?\s*-?\d{1,3}\.\d{4,}"
)
_BELGIAN_NID_RE = re.compile(r"\b\d{2}\.\d{2}\.\d{2}-\d{3}\.\d{2}\b")
# Date of birth (explicit label + date value)
_DOB_RE = re.compile(
    r"\b(?:dob|date[\s_]?of[\s_]?birth|born|n[eé][e]?|naissance)\s*[:=]?\s*\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}",
    re.IGNORECASE,
)
# Passport number (letter prefix + digits)
_PASSPORT_RE = re.compile(
    r"\b(?:passport|passeport)[\s_]?(?:no|n°|#|number|num)?\s*[:=]?\s*[A-Z]{1,2}\d{6,8}\b",
    re.IGNORECASE,
)
# Medical record / dossier number
_MRN_RE = re.compile(
    r"\b(?:mrn|medical[\s_]?record(?:[\s_]?(?:no|#|number))?|dossier[\s_]?(?:no|#|médical|medical)?|numéro[\s_]?dossier)\s*[:=]?\s*[\dA-Z\-]{4,15}\b",
    re.IGNORECASE,
)
# 16-digit national ID number (several national ID cards use a 16-digit format)
_NID16_RE = re.compile(r"\b\d{16}\b")
# Name fields with associated identifier-type values
_NAME_ID_RE = re.compile(
    r"\b(?:nom|prenom|prénom|surname|firstname|first[\s_]name|last[\s_]name)\s*[:=]\s*[A-Za-zÀ-ÿ]{2,}",
    re.IGNORECASE,
)

_SENSITIVE_COLUMNS = {
    "patient", "patient_id", "case_id", "diagnosis", "dob",
    "date_of_birth", "test_result", "gps_lat", "gps_lon",
    # Name fields, record numbers, identity numbers
    "nom", "prenom", "prénom", "surname", "firstname", "first_name", "last_name",
    "mrn", "record_number", "dossier", "passport_number", "nid", "national_id",
}
# Merge any field-specific sensitive column names from the local override file.
_SENSITIVE_COLUMNS |= {
    str(c).lower() for c in load_overrides().get("extra_sensitive_columns", [])
}


def _build_extra_checks():
    """Compile field-specific PII patterns from the local override file (if any).

    Lets a user keep their own institution/programme identifiers (e.g. a national
    case-registry number format) private and out of the public source, while still
    being detected on their own machine.
    """
    checks: list[tuple[re.Pattern, str]] = []
    sensitive: set[str] = set()
    confidential: set[str] = set()
    for item in load_overrides().get("extra_pii_patterns", []):
        try:
            flags = re.IGNORECASE if "i" in str(item.get("flags", "")).lower() else 0
            rx = re.compile(item["regex"], flags)
        except Exception:
            continue
        label = str(item.get("label", "Sensitive identifier"))
        checks.append((rx, label))
        level = str(item.get("level", "SENSITIVE")).upper()
        if level == "CONFIDENTIAL":
            confidential.add(label.lower())
        else:
            sensitive.add(label.lower())
    return checks, sensitive, confidential


_EXTRA_CHECKS, _EXTRA_SENSITIVE_LABELS, _EXTRA_CONFIDENTIAL_LABELS = _build_extra_checks()


def _check_sensitive_headers(content: str) -> list[str]:
    """Check first line of content for sensitive CSV/TSV column names."""
    first_line = content.split("\n", 1)[0].lower()
    # Check for CSV or TSV headers
    separators = [",", "\t", ";", "|"]
    for sep in separators:
        if sep in first_line:
            headers = {h.strip().strip('"').strip("'") for h in first_line.split(sep)}
            found = headers & _SENSITIVE_COLUMNS
            if found:
                return [f"Sensitive column(s) detected: {', '.join(sorted(found))}"]
    return []


def _classify(warnings: list[str], file_path: str) -> str:
    """Determine classification based on warnings and file type."""
    warning_text = " ".join(warnings).lower()

    # SENSITIVE: direct individual identifiers — patient/case IDs, individual GPS,
    # diagnostic results, plus any field-specific identifiers from local overrides.
    if any(kw in warning_text for kw in [
        "patient", "case_id", "gps coordinate", "diagnostic", "test_result",
    ]) or any(lbl in warning_text for lbl in _EXTRA_SENSITIVE_LABELS):
        return "SENSITIVE"

    # CONFIDENTIAL: other PII — names, DOB, passport/record/identity numbers,
    # files with sensitive columns.
    if any(kw in warning_text for kw in [
        "national id", "sensitive column",
        "date of birth", "passport", "medical record", "name field",
    ]) or any(lbl in warning_text for lbl in _EXTRA_CONFIDENTIAL_LABELS):
        return "CONFIDENTIAL"

    if file_path:
        ext = file_path.lower().rsplit(".", 1)[-1] if "." in file_path else ""
        if ext in ("xlsx", "xls", "csv") and warnings:
            return "CONFIDENTIAL"

    # If there are warnings but not sensitive/confidential
    if warnings:
        return "INTERNAL"

    # Check file type for default classification
    if file_path:
        ext = file_path.lower().rsplit(".", 1)[-1] if "." in file_path else ""
        if ext in ("py", "r", "js", "ts", "yaml", "yml", "json", "toml"):
            return "INTERNAL"

    return "PUBLIC"


# Ordered (regex, label) PII checks applied to any text Metis is about to send out.
# Single source of truth — used by both check_data_safety() and the pipeline's
# Stage-3 Data Guardian (via scan_content), so the two can never drift apart.
_PII_CHECKS: list[tuple[re.Pattern, str]] = [
    (_EMAIL_RE, "Email address"),
    (_PHONE_RE, "Phone number"),
    (_INTL_PHONE_RE, "Phone number"),
    (_PATIENT_ID_RE, "Patient/case ID pattern"),
    (_GPS_RE, "High-precision GPS coordinate"),
    (_BELGIAN_NID_RE, "Belgian national ID"),
    (_DOB_RE, "Date of birth"),
    (_PASSPORT_RE, "Passport number"),
    (_MRN_RE, "Medical record number"),
    (_NID16_RE, "16-digit national ID number"),
    (_NAME_ID_RE, "Name field"),
]
# Append any field-specific patterns kept in the local (gitignored) override file.
_PII_CHECKS.extend(_EXTRA_CHECKS)


def scan_content(content: str, file_path: str = "") -> dict:
    """Scan text for PII patterns + sensitive CSV/TSV headers and classify it.

    The one scanner both the check_data_safety tool and the pipeline Data Guardian
    call. Returns {safe, classification, warnings}.

    Args:
        content: Text content to scan.
        file_path: Optional file path for context-based classification.
    """
    warnings: list[str] = []
    for pattern, label in _PII_CHECKS:
        hits = pattern.findall(content)
        if hits:
            warnings.append(f"{label}(s) detected: {len(hits)} found")
    warnings.extend(_check_sensitive_headers(content))
    classification = _classify(warnings, file_path)
    return {"safe": len(warnings) == 0, "classification": classification, "warnings": warnings}


@app.tool()
async def check_data_safety(
    content: str,
    file_path: str = "",
) -> list[TextContent]:
    """Scan content for PII patterns and classify sensitivity level.

    Returns safety status, classification, and specific warnings.

    Args:
        content: Text content to scan.
        file_path: Optional file path for context-based classification.
    """
    result = scan_content(content, file_path)
    safe = result["safe"]
    classification = result["classification"]
    warnings = result["warnings"]

    lines = [
        f"**Safe:** {safe}",
        f"**Classification:** {classification}",
    ]
    if warnings:
        lines.append("**Warnings:**")
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("No PII or sensitive patterns detected.")

    return [TextContent(type="text", text="\n".join(lines))]
