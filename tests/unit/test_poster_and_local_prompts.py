"""create_poster fills a template found in a machine-local folder; local prompts
are read from a machine-local folder. Neither the template nor the prompts ship."""
import asyncio
from pathlib import Path

import pytest

pptx = pytest.importorskip("pptx")


@pytest.fixture()
def root(tmp_path, monkeypatch):
    from metis_mcp.config import paths
    monkeypatch.setattr(paths, "root", tmp_path)
    monkeypatch.delenv("METIS_TEMPLATES_DIR", raising=False)
    return tmp_path


def _template(root: Path) -> Path:
    """A plain deck: its 'Title and Content' layout has one large body box."""
    d = root / "system" / "config" / "local" / "templates"
    d.mkdir(parents=True)
    p = d / "plain-poster.pptx"
    pptx.Presentation().save(str(p))
    return p


def test_no_template_names_the_folders(root):
    from metis_mcp.tools.authoring import create_poster
    out = asyncio.run(create_poster(title="T", sections="# A\nx"))[0].text
    assert "No poster template" in out
    assert "templates" in out


def test_poster_is_written_from_the_local_template(root):
    from metis_mcp.tools.authoring import create_poster
    _template(root)
    out = asyncio.run(create_poster(title="A poster", sections="# Results\n- one\n- two",
                                    authors="A. Author"))[0].text
    assert "plain-poster.pptx" in out
    written = list((root / "outputs" / "posters").glob("*.pptx"))
    assert len(written) == 1
    deck = pptx.Presentation(str(written[0]))
    assert len(deck.slides) == 1
    text = " ".join(sh.text_frame.text for sh in deck.slides[0].shapes if sh.has_text_frame)
    assert "A poster" in text and "one" in text


def test_too_many_sections_is_refused_not_truncated(root):
    from metis_mcp.tools.authoring import create_poster
    _template(root)
    out = asyncio.run(create_poster(
        title="T", sections="\n".join(f"# S{i}\nx" for i in range(9))))[0].text
    assert "Merge sections" in out


def test_local_prompts_are_loaded(tmp_path, monkeypatch):
    from metis_mcp.tools import prompts
    (tmp_path / "demo-one.md").write_text("# Demo one\nDo the thing.", encoding="utf-8")
    monkeypatch.setenv("METIS_LOCAL_PROMPTS_DIR", str(tmp_path))
    found = prompts._local_prompts()
    desc, fn = found["demo-one"]
    assert desc == "Demo one"
    assert fn().startswith("Do the thing.")
    assert "extra" in fn(note="extra")
