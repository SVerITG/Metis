"""
personas/conftest.py — pytest auto-discovery conftest for persona tests.

Defines dashboard_client and tmp_db fixtures for per-persona FastAPI tests.
The fixtures inspect request.cls.PERSONA to seed the database for the
right persona before each test.
"""

from pathlib import Path

import pytest

from .conftest_personas import make_persona_client
from .profiles import PERSONAS

# ── Per-class client fixtures ─────────────────────────────────────────────────


@pytest.fixture
def dashboard_client(request, tmp_path, monkeypatch):
    """
    FastAPI TestClient seeded for the persona defined by the test class.

    Test classes must define:
        PERSONA = PERSONA_BY_ID[n]   or   PERSONA = PERSONA_BY_SLUG["slug"]

    Falls back to persona 1 (PhD student) if no class-level PERSONA found.
    """
    cls = getattr(request, "cls", None)
    persona = getattr(cls, "PERSONA", PERSONAS[0])
    client, _db_path = make_persona_client(persona.slug, tmp_path, monkeypatch)
    return client


@pytest.fixture
def tmp_db(request, tmp_path, monkeypatch):
    """
    Returns the Path to the seeded SQLite database for the test class persona.
    Always created alongside dashboard_client — if you need only the db path,
    use this fixture; the db file is created as a side effect.
    """
    cls = getattr(request, "cls", None)
    persona = getattr(cls, "PERSONA", PERSONAS[0])
    _client, db_path = make_persona_client(persona.slug, tmp_path, monkeypatch)
    return db_path
