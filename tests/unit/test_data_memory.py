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
        owners = {r[0] for r in conn.execute(
            "SELECT d.format FROM dm_columns c JOIN dm_datasets d ON d.key = c.dataset_key "
            "WHERE c.column_name = 'only_in_combined'")}
    # credited to the combined table itself, never smeared over the three inputs
    assert owners == {"table in code"}


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


@pytest.fixture()
def pipeline(tmp_path):
    """A dashboard-shaped project: nested CONFIG, a wrapper reader, a folder of
    yearly files read in a loop, a combined table saved to a cache file, a
    column dictionary and definitions in comments."""
    root = tmp_path / "dash"
    for y in ("2025", "2026"):
        _w(root / "data" / "Yearly" / y / "region_a.csv", "x\n")
    _w(root / "data" / "ref.csv", "x\n")
    _w(root / "dash.Rproj", "")
    _w(root / "00_config.R", """
ROOT <- here::here()
CONFIG <- list(
  files = list(
    yearly = file.path(ROOT, "data", "Yearly"),
    ref    = file.path(ROOT, "data", "ref.csv")
  ),
  cache = file.path(ROOT, "cache")
)
VARS <- c(zone = "zone_name", site = "site_name")
AREA_PATTERN <- "NORTH|SOUTH"
# ---- Definitions agreed for this project ----
# ACTIVE = a site with at least one record that year
#          (annual, not cumulative).
read_chr <- function(path) {
  readr::read_delim(path, delim = ",")
}
save_cache <- function(obj, path) {
  fst::write_fst(obj, path)
}
""")
    _w(root / "01_build.R", """
source("00_config.R")
load_yearly <- function(folder_path) {
  files <- list.files(folder_path, pattern = "\\\\.csv$", recursive = TRUE, full.names = TRUE)
  out <- list()
  for (f in files) {
    out[[f]] <- read_chr(f)
  }
  dplyr::bind_rows(out)
}
yearly <- load_yearly(CONFIG$files$yearly)
ref <- read_chr(CONFIG$files$ref) |> select(all_of(VARS))
extra1 <- read_chr(file.path(ROOT, "data", "e1.csv"))
extra2 <- read_chr(file.path(ROOT, "data", "e2.csv"))
records <- bind_rows(yearly, ref, extra1, extra2)
records <- records |>
  filter(str_detect(region, AREA_PATTERN)) |>
  mutate(active = n_records > 0)
save_cache(records, file.path(CONFIG$cache, "dm_records.fst"))
""")
    return root


def test_folder_listing_loop_and_nested_config(pipeline, tmp_path):
    db = tmp_path / "p.mem"
    dm.scan(str(pipeline), db=db)
    with dm.open_db(db) as conn:
        paths = {r["path"]: r for r in conn.execute("SELECT * FROM dm_datasets")}
    fam = [p for p in paths if p.endswith("Yearly/**/*.csv")]
    assert fam and paths[fam[0]]["format"] == "folder of files" and paths[fam[0]]["on_disk"] == 1
    assert any(p.endswith("data/ref.csv") for p in paths), "CONFIG$files$ref through the read_chr wrapper"


def test_combined_table_keeps_its_columns_and_its_cache_file_inherits_them(pipeline, tmp_path):
    db = tmp_path / "p.mem"
    dm.scan(str(pipeline), db=db)
    with dm.open_db(db) as conn:
        tkey = conn.execute("SELECT key FROM dm_datasets WHERE format='table in code' AND name='records'").fetchone()
        assert tkey, "the combined object is remembered as a table"
        table = dm.dataset_card(conn, tkey[0])
        assert len(table["built_from"]) >= 3
        assert "active" in {c["name"] for c in table["columns"]}
        cache = conn.execute("SELECT key FROM dm_datasets WHERE name='dm_records.fst'").fetchone()
        assert cache, "a write through the save_cache wrapper is bound at its call"
        card = dm.dataset_card(conn, cache[0])
    assert "records" in card["saved_from"]
    cols = {c["name"]: c for c in card["columns"]}
    assert "active" in cols and "~NORTH|SOUTH" in cols["region"]["values"]


def test_column_dictionary_and_definitions(pipeline, tmp_path):
    db = tmp_path / "p.mem"
    dm.scan(str(pipeline), db=db)
    with dm.open_db(db) as conn:
        ref = conn.execute("SELECT key FROM dm_datasets WHERE name='ref.csv'").fetchone()[0]
        names = {c["name"] for c in dm.dataset_card(conn, ref)["columns"]}
    assert {"zone_name", "site_name"} <= names
    out = dm.context("active sites", db=db)
    assert "ACTIVE = a site with at least one record that year (annual, not cumulative)." in out


def test_cache_by_name_and_columns_inside_a_helper(tmp_path):
    """cache_write(obj, "name") builds its path inside the helper from a config
    default; a create_x(df) function uses columns on its argument."""
    root = tmp_path / "app"
    _w(root / "src.csv", "x\n")
    _w(root / "app.R", f"""
CONFIG <- list(cache_folder = "{(root / 'cache').as_posix()}")
cache_write <- function(obj, name, config = CONFIG) {{
  dir  <- config$cache_folder
  ext  <- if (use_fst) ".fst" else ".rds"
  path <- file.path(dir, paste0(name, ext))
  fst::write_fst(obj, path)
}}
create_summary <- function(cases_df) {{
  cases_df |> filter(status == "confirmed") |> count(zone, year)
}}
raw <- read.csv("{(root / 'src.csv').as_posix()}")
summary_tbl <- create_summary(raw)
cache_write(summary_tbl, "dm_summary")
""")
    db = tmp_path / "c.mem"
    dm.scan(str(root), db=db)
    with dm.open_db(db) as conn:
        hit = conn.execute("SELECT key FROM dm_datasets WHERE name = 'dm_summary.fst'").fetchone()
        assert hit, "the cache file is found from its name and the helper's recipe"
        card = dm.dataset_card(conn, hit[0])
        src = conn.execute("SELECT key FROM dm_datasets WHERE name = 'src.csv'").fetchone()[0]
        cols = {c["name"]: c for c in dm.dataset_card(conn, src)["columns"]}
    assert card["written_by"]
    assert cols["status"]["values"] == ["confirmed"], "columns used inside create_summary land on src.csv"
    assert {"zone", "year"} <= set(cols)


def test_a_path_returned_by_the_researchers_own_function(tmp_path):
    root = tmp_path / "app"
    _w(root / "cache" / "dm_zone_table.fst", "x")
    _w(root / "app.R", f"""
CONFIG <- list(cache_folder = "{(root / 'cache').as_posix()}")
cache_path <- function(name, config = CONFIG) {{
  file.path(config$cache_folder, paste0(name, ".fst"))
}}
cache_read <- function(name, config = CONFIG) {{
  path <- cache_path(name, config)
  fst::read_fst(path)
}}
zones <- cache_read("dm_zone_table")
zones |> filter(level == "zone")
""")
    db = tmp_path / "r.mem"
    dm.scan(str(root), db=db)
    with dm.open_db(db) as conn:
        hit = conn.execute("SELECT key, on_disk FROM dm_datasets WHERE name = 'dm_zone_table.fst'").fetchone()
        assert hit and hit["on_disk"] == 1
        card = dm.dataset_card(conn, hit["key"])
    assert any(o == "zones" for _, o, _ in card["read_by"])
    assert {c["name"]: c["values"] for c in card["columns"]}.get("level") == ["zone"]


def test_function_variables_stay_local_and_outputs_belong_to_the_caller(tmp_path):
    root = tmp_path / "proj"
    out = (root / "out").as_posix()
    _w(root / "helpers.R", f"""
OUT <- "{out}"
other_helper <- function() {{
  path <- "C:/somewhere/else/wrong.csv"
  path
}}
save_table <- function(x, name) {{
  path <- file.path(OUT, paste0(name, ".csv"))
  readr::write_csv(x, path)
}}
""")
    _w(root / "main.R", """
source("helpers.R")
tbl <- data.frame(a = 1)
save_table(tbl, "endemic_summary")
""")
    db = tmp_path / "s.mem"
    dm.scan(str(root), db=db)
    with dm.open_db(db) as conn:
        names = {r[0] for r in conn.execute("SELECT name FROM dm_datasets")}
        hit = conn.execute("SELECT key FROM dm_datasets WHERE name = 'endemic_summary.csv'").fetchone()
        assert "wrong.csv" not in names, "a variable inside one helper never resolves another's path"
        assert hit, names
        card = dm.dataset_card(conn, hit[0])
    assert [Path(s).name for s in card["written_by"]] == ["main.R"], "credited to the caller, not helpers.R"


def test_read_script_serves_code_only_inside_registered_folders(pipeline, tmp_path):
    db = tmp_path / "p.mem"
    dm.scan(str(pipeline), db=db)
    text, where = dm.read_script(str(pipeline / "01_build.R"), db=db)
    assert text and "load_yearly" in text
    text, _ = dm.read_script("01_build.R", db=db)
    assert text, "a unique file name is enough"
    text, why = dm.read_script(str(pipeline / "data" / "ref.csv"), db=db)
    assert text is None and "Only analysis scripts" in why
    outside = _w(tmp_path / "elsewhere" / "x.R", "1\n")
    text, why = dm.read_script(str(outside), db=db)
    assert text is None and "not inside a folder" in why


def test_researcher_story_is_attached_to_the_dataset(project, tmp_path):
    db, _ = _scan(project, tmp_path)
    where = dm.add_story("cases.csv", "Counts before 2018 exclude one district.", db=db)
    assert where.startswith("dataset:")
    out = dm.context("cases", db=db)
    assert "exclude one district" in out


def test_vocabulary_keeps_only_words_found_in_several_kinds_of_place(tmp_path):
    """A word one folder name carries ("claude") is not about the data; the subject is everywhere."""
    db = tmp_path / "v.mem"
    with dm.open_db(db) as conn:
        conn.execute("INSERT INTO dm_datasets(key, path, name, folder, format) VALUES "
                     "('a', '/x/Claude/endemic_sites.csv', 'endemic_sites.csv', '/x/Claude/endemic', 'csv')")
        conn.execute("INSERT INTO dm_scripts(path, title, folder) VALUES ('/x/s.R', 'endemic_summary.R', '/x')")
        conn.commit()
    dm.export_vocab(db)
    terms = dm.load_vocab(db)
    assert "endemic" in terms          # file name, folder, script title
    assert "claude" not in terms       # one folder only


def test_context_leads_with_templates_and_recorded_work(tmp_path):
    """A long answer must lose its file cards, never the scripts and saved code to start from."""
    db = tmp_path / "c.mem"
    with dm.open_db(db) as conn:
        conn.execute("CREATE TABLE code_artifacts (id INTEGER PRIMARY KEY, project_id TEXT, title TEXT, "
                     "language TEXT, kind TEXT, purpose TEXT, tags TEXT, code TEXT, file_path TEXT, "
                     "packages TEXT, params TEXT, created_at TEXT, updated_at TEXT)")
        conn.execute("INSERT INTO code_artifacts(id, title, kind, purpose, code, updated_at) VALUES "
                     "(1, 'Region assignment', 'snippet', 'assign the region to each site', 'x <- 1', '2026-01-01')")
        conn.execute("INSERT INTO dm_scripts(path, title, folder, purpose) VALUES "
                     "('/x/region.R', 'region.R', '/x', 'assign region to each site')")
        for i in range(12):
            conn.execute("INSERT INTO dm_datasets(key, path, name, folder, format, on_disk) VALUES "
                         f"('k{i}', '/x/site_region_{i}.rds', 'site_region_{i}.rds', '/x', 'rds', 1)")
            conn.execute("INSERT INTO dm_links(script_path, dataset_key, role) VALUES ('/x/region.R', ?, 'read')",
                         (f"k{i}",))
            for c in range(30):
                conn.execute("INSERT INTO dm_columns(dataset_key, script_path, column_name) "
                             "VALUES (?, '/x/region.R', ?)", (f"k{i}", f"region_site_column_{c}"))
        conn.commit()
    out = dm.context("assign the region to each site", db=db, max_chars=2500)
    assert "Region assignment" in out and "artifact:1" in out
    assert "Closest existing scripts" in out
    assert out.index("Closest existing scripts") < out.index("### site_region_")
    assert dm.read_script("artifact:1", db=db) == ("x <- 1", "saved code: Region assignment")
