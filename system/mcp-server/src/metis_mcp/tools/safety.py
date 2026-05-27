"""Data safety scanner for PII and sensitive content detection."""

import re

from mcp.types import TextContent

from metis_mcp.app_instance import app

# PII detection patterns
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE_RE = re.compile(r"\+?\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}")
_PATIENT_ID_RE = re.compile(
    r"\b(?:patient_?id|case_?id|patient\s*#)\s*[:=]?\s*\d+", re.IGNORECASE
)
_GPS_RE = re.compile(
    r"-?\d{1,3}\.\d{5,},?\s*-?\d{1,3}\.\d{5,}"
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
# HAT / PNLTHA case registration numbers (DRC sleeping-sickness programme)
_HAT_CASE_RE = re.compile(
    r"\b(?:hat[\s_-]?(?:case|id|n°|no|#|patient)|pnltha[\s_-]?\d+|cas[\s_-]?hat|hat[\s_-]?dossier)\s*[:=]?\s*[\dA-Z\-]{3,20}\b",
    re.IGNORECASE,
)
# DRC national ID card (16-digit number)
_DRC_NID_RE = re.compile(r"\b\d{16}\b")
# Name fields with associated identifier-type values
_NAME_ID_RE = re.compile(
    r"\b(?:nom|prenom|prénom|surname|firstname|first[\s_]name|last[\s_]name)\s*[:=]\s*[A-Za-zÀ-ÿ]{2,}",
    re.IGNORECASE,
)

_SENSITIVE_COLUMNS = {
    "patient", "patient_id", "case_id", "diagnosis", "dob",
    "date_of_birth", "test_result", "gps_lat", "gps_lon",
    # Added: name fields, record numbers, identity numbers
    "nom", "prenom", "prénom", "surname", "firstname", "first_name", "last_name",
    "mrn", "record_number", "dossier", "passport_number", "nid", "national_id",
    "hat_case_id", "hat_patient_id",
}


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

    # SENSITIVE: patient IDs, individual GPS, diagnostic results
    if any(kw in warning_text for kw in ["patient", "case_id", "gps coordinate", "diagnostic", "test_result"]):
        return "SENSITIVE"

    # CONFIDENTIAL: personal names + dates, files with sensitive columns
    if any(kw in warning_text for kw in ["belgian national id", "sensitive column"]):
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
    warnings: list[str] = []

    # Email addresses
    emails = _EMAIL_RE.findall(content)
    if emails:
        warnings.append(f"Email address(es) detected: {len(emails)} found")

    # Phone numbers
    phones = _PHONE_RE.findall(content)
    if phones:
        warnings.append(f"Phone number(s) detected: {len(phones)} found")

    # Patient/case IDs
    patient_ids = _PATIENT_ID_RE.findall(content)
    if patient_ids:
        warnings.append(f"Patient/case ID pattern(s) detected: {len(patient_ids)} found")

    # GPS coordinates (high precision = individual level)
    gps = _GPS_RE.findall(content)
    if gps:
        warnings.append(f"High-precision GPS coordinate(s) detected: {len(gps)} found")

    # Belgian national ID
    belgian = _BELGIAN_NID_RE.findall(content)
    if belgian:
        warnings.append(f"Belgian national ID pattern(s) detected: {len(belgian)} found")

    # Sensitive CSV headers
    header_warnings = _check_sensitive_headers(content)
    warnings.extend(header_warnings)

    # Classification
    classification = _classify(warnings, file_path)
    safe = len(warnings) == 0

    # Build result
    result = {
        "safe": safe,
        "classification": classification,
        "warnings": warnings,
    }

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
