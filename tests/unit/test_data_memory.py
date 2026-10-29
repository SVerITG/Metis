"""The Data Memory learns datasets from analysis code and never opens a data file.

Written 2026-10-29. The previous scanner recognised a read only when the path
was a literal string inside the call; on three real script trees, 1,775 of
2,504 reads went through a path object and were invisible to it. Each way real
projects name their files is pinned here, on synthetic scripts:

  · a path object built with file.path() in a setup script that is source()d
  · SCRIPT_DIR from rstudioapi inside tryCatch(), then dirname()
  · a CONFIG list, read inside a loader function whose parameter is the file,
    bound at the call site in a later sourced script (late binding)
  · Sys.getenv(unset = if (unix) "..." else "C:/...")
  · a file family written in a loop, kept as a {pattern}

And the two promises: data files are only ever stat()ed, and a combined table
does not smear its columns over every input file.
"""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

_SRC = str(Path(__file__).resolve().parents[2] / "system" / "mcp-server" / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from metis_mcp import data_memory as dm  # noqa: E402


def _w(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture()
def project(tmp_path):
    root = tmp_path / "proj"
    data = root / "data"
    _w(data / "cases.csv", "id,year,site\n1,2020,a\n")
    _w(data / "sites.csv", "site,region\n")
    _w(root / "README.md", "# Project\n\nThe cases file is the fixed reference list.\n"
       "\n## Metis integration\nCall create_task(...)\n")
    _w(root / "scripts" / "00_setup.R", f"""
# Shared setup
SCRIPT_DIR <- tryCatch(
  dirname(rstudioapi::getSourceEditorContext()$path),
  error = function(e) getwd()
)
BASE_DIR  <- dirname(SCRIPT_DIR)
DATA_DIR  <- file.path(BASE_DIR, "data")
path_cases <- file.path(DATA_DIR, "cases.csv")
OUT_DIR <- Sys.getenv("PROJ_OUT", unset = {{
  if (.Platform$OS.type == "unix") "/nowhere/out" else "C:/proj/out"
}})
""")
    _w(root / "scripts" / "01_cases.R", """
# Cases per year and site
source("00_setup.R")
library(dplyr)
cases <- read.csv(path_cases) %>%
  filter(site %in% c("north", "south"), year >= 2016) %>%
  mutate(period = if_else(year < 2020, "early", "late"))
by_year <- cases %>% count(year, site)
for (yr in 2016:2020) {
  write.csv(by_year, file.path(OUT_DIR, paste0("by_year_", yr, ".csv")))
}
""")
    _w(root / "scripts" / "app" / "config.R", """
CONFIG <- list(sites_file = file.path(DATA_DIR, "sites.csv"))
""")
    _w(root / "scripts" / "app" / "loading.R", """
load_sites <- function(sites_file) {
  raw <- read.csv(sites_file)
  raw %>% filter(region == "east") %>% select(site, region)
}
""")
    _w(root / "scripts" / "app" / "app.R", """
source("../00_setup.R")
source("config.R")
source("loading.R")
sites <- load_sites(CONFIG$sites_file)
""")
    # copies are noise and must be skipped
    _w(root / "scripts" / "History" / "old_01_cases.R", 'x <- read.csv("C:/old/cases.csv")\n')
    return root


def _scan(project, tmp_path):
    db = tmp_path / "memory.mem"
    stats = dm.scan(str(project), project_id="t", db=db)
    return db, stats


def test_path_objects_and_source_chain_are_resolved(project, tmp_path):
    db, stats = _scan(project, tmp_path)
    assert stats["scripts"] == 5, "History/ copies must be skipped"
    with dm.open_db(db) as conn:
        card = dm.dataset_card(conn, dm.dataset_key((project / "data" / "cases.csv").as_posix()))
    assert card["on_disk"] == 1
    assert any(Path(s).name == "01_cases.R" and o == "cases" for s, o, _ in card["read_by"])
    cols = {c["name"]: c for c in card["columns"]}
    assert {"site", "year", "period"} <= set(cols)
    assert set(cols["site"]["values"]) == {"north", "south"}
    assert "if_else" in cols["period"]["derived"]


def test_loader_function_is_bound_at_its_call_site(project, tmp_path):
    db, _ = _scan(project, tmp_path)
    with dm.open_db(db) as conn:
        card = dm.dataset_card(conn, dm.dataset_key((project / "data" / "sites.csv").as_posix()))
    assert any(Path(s).name == "loading.R" for s, _, _ in card["read_by"])
    cols = {c["name"]: c for c in card["columns"]}
    assert cols["region"]["values"] == ["east"]


def test_file_family_kept_as_pattern_and_windows_branch_chosen(project, tmp_path):
    db, _ = _scan(project, tmp_path)
    with dm.open_db(db) as conn:
        names = [r["path"] for r in conn.execute("SELECT path FROM dm_datasets")]
    fam = [n for n in names if n.endswith("by_year_{yr}.csv")]
    assert fam, names
    assert fam[0].startswith("C:/proj/out/"), "the researcher's R runs on Windows: its branch wins"


def test_data_files_are_never_opened(project, tmp_path):
    """stat() is allowed; open() is not. An unreadable data file must not matter."""
    data_files = [project / "data" / "cases.csv", project / "data" / "sites.csv"]
    for f in data_files:
        os.chmod(f, 0)
    try:
        if os.access(data_files[0], os.R_OK):
            pytest.skip("running as a user that can read mode-000 files")
        db, stats = _scan(project, tmp_path)
        with dm.open_db(db) as conn:
            card = dm.dataset_card(conn, dm.dataset_key(data_files[0].as_posix()))
        assert card["on_disk"] == 1 and card["columns"]
    finally:
        for f in data_files:
            os.chmod(f, stat.S_IRUSR | stat.S_IWUSR)


def test_notes_are_stories_without_assistant_instructions(project, tmp_path):
    db, _ = _scan(project, tmp_path)
    out = dm.context("cases per site", db=db)
    assert "fixed reference list" in out
    assert "create_task" not in out
    assert "DATA-PROTECTED MODE" in out


def test_combined_table_does_not_smear_columns(tmp_path):
    root = tmp_path / "p"
    for n in ("a", "b", "c"):
        _w(root / f"{n}.csv", "x\n")
    _w(root / "s.R", """
a <- read.csv("a.csv");
b <- read.csv("b.csv")
c3 <- read.csv("c.csv")
allx <- bind_rows(a, b, c3)
allx <- allx %>% mutate(only_in_combined = 1)
""")
    db = tmp_path / "m.mem"
    dm.scan(str(root), db=db)
    with dm.open_db(db) as conn:
        cols = {r[0] for r in conn.execute("SELECT column_name FROM dm_columns")}
    assert "only_in_combined" not in cols


def test_unchanged_scripts_are_not_reread(project, tmp_path):
    db, first = _scan(project, tmp_path)
    second = dm.scan(str(project), db=db)
    assert first["rescanned"] == 5 and second["rescanned"] == 0 and second["unchanged"] == 5


def test_wizard_registers_folders_without_reading_them(project, tmp_path, monkeypatch):
    """The wizard only registers; learning starts afterwards (background or terminal)."""
    db = tmp_path / "wizard.mem"
    monkeypatch.setenv("METIS_DB", str(db))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "install"))
    import process_wizard_answers as pwa
    root = Path(__file__).resolve().parents[2]
    out = pwa.register_script_folders(root, {"script_folders": f"{project}\n\n/no/such/folder\n"})
    assert out["registered"] and out["scripts"] == 5
    assert out["missing"] == ["/no/such/folder"]
    st = dm.status(db=db)
    assert st["scripts"] == 0 and len(st["sources"]) == 1 and st["sources"][0]["last_scan"] is None
    dm.refresh(db=db)
    assert dm.status(db=db)["scripts"] == 5


def test_dead_reference_folds_into_the_file_that_exists(tmp_path):
    root = tmp_path / "p"
    _w(root / "data" / "list.csv", "x\n")
    _w(root / "a.R", 'v <- read.csv("data/list.csv")\n')
    _w(root / "earlier" / "b.R", 'v <- read.csv("/gone/list.csv")\n')
    db = tmp_path / "m.mem"
    dm.scan(str(root), db=db)
    with dm.open_db(db) as conn:
        rows = dm.list_datasets(conn)
    assert len(rows) == 1 and rows[0]["on_disk"] == 1 and rows[0]["n_aliases"] == 1


def test_forget_source_drops_what_was_learnt(project, tmp_path):
    db, _ = _scan(project, tmp_path)
    assert dm.forget_source(str(project), db=db) == 5
    st = dm.status(db=db)
    assert st["scripts"] == 0 and st["datasets"] == 0 and not st["sources"]
    assert (project / "data" / "cases.csv").exists(), "forgetting never touches disk"


def test_researcher_story_is_attached_to_the_dataset(project, tmp_path):
    db, _ = _scan(project, tmp_path)
    where = dm.add_story("cases.csv", "Counts before 2018 exclude one district.", db=db)
    assert where.startswith("dataset:")
    out = dm.context("cases", db=db)
    assert "exclude one district" in out
