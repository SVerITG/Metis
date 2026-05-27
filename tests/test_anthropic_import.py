"""
test_anthropic_import.py — guard against silent SDK loss on fresh installs.

Several Metis features (morning brief generator, stop-hook LLM fact extractor,
any agent that calls Claude directly) depend on the `anthropic` SDK being
installed in the runtime venv. We pin it in pyproject.toml AND requirements.txt,
but those pins are only enforced when someone actually runs `pip install`.

This test fails the build if the SDK is missing — catches the failure mode
where a fresh install silently drops the dep and morning briefs go quiet.

Run via:
    python3 -m pytest tests/test_anthropic_import.py
    # or directly
    python3 tests/test_anthropic_import.py
"""
from __future__ import annotations


def test_anthropic_import() -> None:
    """The SDK must be importable from the runtime environment."""
    import anthropic  # noqa: F401  — import is the test

    assert hasattr(anthropic, "Anthropic"), "anthropic.Anthropic class missing"


def test_anthropic_version_minimum() -> None:
    """Pin floor matches pyproject.toml + requirements.txt (>=0.40)."""
    import anthropic

    version = getattr(anthropic, "__version__", "0.0.0")
    parts = [int(p) for p in version.split(".")[:2] if p.isdigit()]
    assert len(parts) >= 2, f"unexpected version format: {version!r}"
    major, minor = parts[0], parts[1]
    assert (major, minor) >= (0, 40), (
        f"anthropic SDK version {version} is below the pinned floor (>=0.40). "
        "Update system/mcp-server/pyproject.toml and system/app-py/requirements.txt."
    )


def test_anthropic_client_instantiates() -> None:
    """Instantiation should succeed even without an API key — we're not calling out."""
    from anthropic import Anthropic

    # Pass a synthetic key so we don't depend on the environment.
    # We never actually call the API; this just confirms the constructor signature.
    client = Anthropic(api_key="test-key-not-real-000000000000000000")
    assert client is not None


if __name__ == "__main__":
    # Allow running outside pytest for installer smoke tests.
    test_anthropic_import()
    test_anthropic_version_minimum()
    test_anthropic_client_instantiates()
    print("✓ anthropic SDK present and at supported version")
