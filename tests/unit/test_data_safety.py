"""
Unit tests for the Data Guardian PII scanner (metis_mcp.tools.safety.scan_content).

Guards against the regression where richer patterns (names, DOB, passport, MRN,
national ID numbers) were *defined* but never wired into the live scan — so the
pipeline Data Guardian only caught 5 of them. scan_content is now the single
source of truth used by both the tool and the pipeline (Stage 3).

These tests cover the GENERIC, domain-agnostic patterns that ship publicly.
Field-specific patterns (e.g. a national case-registry format) are loaded at
runtime from the gitignored local override and are intentionally NOT asserted
here, since they are absent in CI and in the public source.
"""

import pytest

from metis_mcp.tools.safety import scan_content


class TestSensitiveDetection:
    @pytest.mark.parametrize("text", [
        "patient_id: 4521 came in Tuesday",
        "coordinates -4.32100, 15.31234 for the household",
        "case_id: 4521 logged",
    ])
    def test_individual_identifiers_are_sensitive(self, text):
        r = scan_content(text)
        assert r["safe"] is False
        assert r["classification"] == "SENSITIVE", (text, r["warnings"])


class TestConfidentialDetection:
    @pytest.mark.parametrize("text", [
        "nom: Mukendi",
        "DOB: 12/03/1980",
        "passport: AB123456",
        "MRN: 88421",
        "ID 1234567890123456",          # 16-digit national ID
    ])
    def test_pii_is_confidential(self, text):
        r = scan_content(text)
        assert r["safe"] is False
        assert r["classification"] == "CONFIDENTIAL", (text, r["warnings"])

    def test_sensitive_csv_header_is_confidential(self):
        r = scan_content("nom,prenom,village\nx,y,z")
        assert r["classification"] == "CONFIDENTIAL"
        assert any("column" in w.lower() for w in r["warnings"])

    def test_named_rows_with_a_result_are_a_sensitive_line_list(self):
        # A name next to a clinical fact is individually identifying.
        for header in ("nom,prenom,diagnosis", "name,village,gps,catt_result"):
            r = scan_content(header + "\nx,y,z,w")
            assert r["classification"] == "SENSITIVE", (header, r["warnings"])

    def test_aggregate_counts_are_not_flagged(self):
        r = scan_content("village,screened,catt_positive\nKibala,120,3")
        assert r["safe"] is True


class TestLowerSensitivity:
    def test_email_alone_is_internal_not_blocked(self):
        # Email/phone are noted but should not escalate to CONFIDENTIAL/SENSITIVE.
        r = scan_content("reach me at jane@example.org")
        assert r["safe"] is False
        assert r["classification"] == "INTERNAL"

    def test_clean_text_is_public_and_safe(self):
        r = scan_content("Please help me draft an introduction for my methods section.")
        assert r["safe"] is True
        assert r["classification"] == "PUBLIC"
        assert r["warnings"] == []


class TestPipelineUsesSharedScanner:
    def test_pipeline_scan_matches_tool(self):
        # The pipeline's Data Guardian must see the same result as the tool.
        from metis_mcp.tools.pipeline import _scan_safety
        text = "patient_id: 4521"
        assert _scan_safety(text)["classification"] == scan_content(text)["classification"] == "SENSITIVE"


class TestAnonymizeTables:
    """A pasted line-list: identifiers sit in cells with no cue word beside them."""

    TABLE = (
        "case_id,name,date_of_birth,phone,gps,test_result\n"
        "C-1,Anne-Sophie Example,1990-01-02,+32 470 12 34 56,-4.3317 15.2662,positive\n"
        "C-2,Paul Sample,1985-05-06,+32 471 98 76 54,-4.4410 15.7790,negative"
    )

    def _anon(self, text):
        import asyncio
        import json
        from metis_mcp.tools.anonymization import anonymize_text
        return json.loads(asyncio.run(anonymize_text(content=text, replace_names=True))[0].text)

    def test_identifier_columns_are_masked(self):
        out = self._anon(self.TABLE)["anonymized"]
        for leaked in ("Anne", "Sophie", "1990-01-02", "15.2662", "470 12"):
            assert leaked not in out, leaked

    def test_outcome_columns_are_kept(self):
        out = self._anon(self.TABLE)["anonymized"]
        assert "positive" in out and "negative" in out

    def test_hyphenated_first_name_is_masked_whole(self):
        out = self._anon("the form was signed by Anne-Sophie Example.")["anonymized"]
        assert "Anne" not in out


def test_one_warning_per_label():
    r = scan_content("call +243 812 345 678 or +243 997 001 223")
    phone = [w for w in r["warnings"] if w.startswith("Phone number")]
    assert len(phone) == 1


def test_consent_event_logs_on_an_installer_built_table(tmp_path, monkeypatch):
    """schema.sql created consent_ledger without session_id; every insert failed."""
    import asyncio
    import sqlite3
    from metis_mcp.config import paths
    from metis_mcp.tools.anonymization import get_consent_ledger, log_consent_event

    db = tmp_path / "t.sqlite"
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE consent_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        action TEXT NOT NULL, data_classification TEXT DEFAULT 'PUBLIC',
        agent_slug TEXT DEFAULT '', notes TEXT DEFAULT '')""")
    con.commit()
    con.close()
    monkeypatch.setattr(paths, "db", db)
    asyncio.run(log_consent_event(action="blocked", data_classification="SENSITIVE"))
    assert "blocked" in asyncio.run(get_consent_ledger(limit=5))[0].text
