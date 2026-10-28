"""The morning pipeline must fail LOUDLY and recover the same day.

Written 2026-10-28 after an evaluation of why the morning brief, news and
articles kept not arriving. Every cause had the same shape: a failure that was
recorded as success (or as "skip"), which counts as done for the day, so
nothing tried again until tomorrow.

  1. A feed that never answers cannot hang the scan (no network timeout).
  2. The morning scan reports error / partial, never a blanket 'ok'.
  3. A brief that could not be written is an error, not "already cached".
  4. The brief waits for a scan that is still running.
  5. Weekly and catch-up briefs expire instead of being served for weeks.
  6. A secondary computer stands down only when the result really arrived.
  7. The start-up catch-up also covers last night's missed evening jobs.
  8. One session record per session, holding the conversation.
"""
import datetime
import socket
import sqlite3
import time

import pytest


def _jobs(db_path, job_id):
    con = sqlite3.connect(str(db_path))
    rows = con.execute(
        "SELECT status, details FROM jobs_log WHERE job_type = ? ORDER BY rowid", (job_id,)
    ).fetchall()
    con.close()
    return rows


@pytest.fixture()
def sched(tmp_db, monkeypatch):
    import scheduler
    monkeypatch.setattr(scheduler, "_main_computer_active", lambda: False)
    monkeypatch.setattr(scheduler, "_notify_windows", lambda *a, **k: None)
    scheduler._running.clear()
    return scheduler


# ── 1. feeds ─────────────────────────────────────────────────────────────────

def test_a_feed_that_never_answers_gives_up(monkeypatch):
    from metis_mcp.tools import content_scan as cs
    monkeypatch.setattr(cs, "FEED_TIMEOUT_S", 1)
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.delenv(var, raising=False)
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)  # accepts the connection, never sends a byte
    try:
        t0 = time.monotonic()
        parsed = cs._fetch_feed(f"http://127.0.0.1:{srv.getsockname()[1]}/feed")
        elapsed = time.monotonic() - t0
    finally:
        srv.close()
    assert parsed.entries == []
    assert parsed.get("timed_out") is True
    # One attempt, not two: a timed-out server is not retried with another UA.
    assert elapsed < 3, f"took {elapsed:.1f}s"


# ── 2. the morning scan's status ─────────────────────────────────────────────

def _patch_sources(monkeypatch, news_ok=True, pubmed_ok=True, alex_ok=True):
    from metis_mcp.tools import content_scan as cs
    from metis_mcp.tools import literature_monitor as lm

    def boom(*a, **k):
        raise OSError("offline")

    monkeypatch.setattr(cs, "scan_news_feeds", (lambda **k: {
        "news_added": 3, "errors": [], "feeds_checked": 5}) if news_ok else boom)
    monkeypatch.setattr(cs, "scan_literature_folder", lambda: {"papers_added": 0})
    monkeypatch.setattr(lm, "_user_pubmed_query", lambda: "q")
    monkeypatch.setattr(lm, "_user_openalex_query", lambda: "q")
    monkeypatch.setattr(lm, "_pubmed_esearch", (lambda *a, **k: []) if pubmed_ok else boom)
    monkeypatch.setattr(lm, "_openalex_search", (lambda *a, **k: []) if alex_ok else boom)


def test_morning_scan_all_failed_is_an_error_and_not_done(sched, tmp_db, monkeypatch):
    _patch_sources(monkeypatch, news_ok=False, pubmed_ok=False, alex_ok=False)
    sched.job_morning_scan()
    assert _jobs(tmp_db, "morning_scan")[-1][0] == "error"
    assert sched._ran_today("morning_scan") is False


def test_morning_scan_some_failed_is_partial_and_retried(sched, tmp_db, monkeypatch):
    _patch_sources(monkeypatch, pubmed_ok=False)
    sched.job_morning_scan()
    assert _jobs(tmp_db, "morning_scan")[-1][0] == "partial"
    assert sched._ran_today("morning_scan") is False


def test_every_feed_failing_is_offline_not_a_quiet_day(sched, tmp_db, monkeypatch):
    _patch_sources(monkeypatch)
    from metis_mcp.tools import content_scan as cs
    monkeypatch.setattr(cs, "scan_news_feeds", lambda **k: {
        "news_added": 0, "errors": ["a", "b"], "feeds_checked": 2})
    sched.job_morning_scan()
    status, details = _jobs(tmp_db, "morning_scan")[-1]
    assert status == "partial"
    assert "2/2 feeds failed" in details


def test_library_scan_with_every_feed_failing_is_not_ok(sched, tmp_db, monkeypatch):
    from metis_mcp.tools import content_scan as cs
    monkeypatch.setattr(cs, "scan_library_feeds", lambda **k: {
        "papers_added": 0, "errors": ["x"] * 3, "feeds_checked": 3})
    monkeypatch.setattr(sched, "_sync_zotero_incremental", lambda: (-1, "no key"))
    monkeypatch.setattr(sched, "_topic_literature_search", lambda **k: 0)
    sched.job_library_scan()
    assert _jobs(tmp_db, "library_scan")[-1][0] == "partial"
    assert sched._ran_today("library_scan") is False


def test_morning_scan_clean_run_is_ok(sched, tmp_db, monkeypatch):
    _patch_sources(monkeypatch)
    sched.job_morning_scan()
    assert _jobs(tmp_db, "morning_scan")[-1][0] == "ok"
    assert sched._ran_today("morning_scan") is True


# ── 3 & 4. the brief job ─────────────────────────────────────────────────────

@pytest.fixture()
def today_mod(monkeypatch):
    from routers import today
    today._brief_failure_reason.clear()
    return today


def test_brief_failure_is_an_error_with_its_reason(sched, today_mod, tmp_db, monkeypatch):
    monkeypatch.setattr(today_mod, "_get_cached_brief", lambda p="daily": None)

    def fails(**k):
        today_mod._brief_failure_reason["daily"] = "the Claude API answered 529"
        return None

    monkeypatch.setattr(today_mod, "_get_or_generate_brief", fails)
    sched.job_brief_synthesis()
    status, details = _jobs(tmp_db, "brief_synthesis")[-1]
    assert status == "error"
    assert "529" in details
    assert sched._ran_today("brief_synthesis") is False


def test_no_api_key_hands_over_to_the_desktop_task(sched, today_mod, tmp_db, monkeypatch):
    monkeypatch.setattr(today_mod, "_get_cached_brief", lambda p="daily": None)

    def no_key(**k):
        today_mod._brief_failure_reason["daily"] = "no-api-key"

    monkeypatch.setattr(today_mod, "_get_or_generate_brief", no_key)
    sched.job_brief_synthesis()
    status, details = _jobs(tmp_db, "brief_synthesis")[-1]
    assert status == "skip" and "Desktop" in details


def test_brief_already_written_elsewhere_is_done(sched, today_mod, tmp_db, monkeypatch):
    monkeypatch.setattr(today_mod, "_get_cached_brief", lambda p="daily": "A brief.")
    monkeypatch.setattr(today_mod, "_get_or_generate_brief",
                        lambda **k: pytest.fail("must not regenerate"))
    sched.job_brief_synthesis()
    assert _jobs(tmp_db, "brief_synthesis")[-1][0] == "skip"


def test_brief_waits_for_a_running_scan(sched, today_mod, tmp_db, monkeypatch):
    monkeypatch.setattr(today_mod, "_get_cached_brief", lambda p="daily": None)
    seen = []
    monkeypatch.setattr(today_mod, "_get_or_generate_brief",
                        lambda **k: seen.append(sched.job_running("morning_scan")) or "Brief")
    sched._running.add("morning_scan")
    sleeps = []

    def fake_sleep(s):  # the scan finishes during the first wait
        sleeps.append(s)
        sched._running.discard("morning_scan")

    monkeypatch.setattr(time, "sleep", fake_sleep)
    sched.job_brief_synthesis()
    assert sleeps, "the brief did not wait for the scan"
    assert seen == [False]


def test_a_job_never_runs_twice_at_once(sched):
    calls = []
    guarded = sched._tracked("x_job", lambda: calls.append(1))
    sched._running.add("x_job")
    guarded()
    assert calls == []
    sched._running.discard("x_job")
    guarded()
    assert calls == [1] and not sched.job_running("x_job")


# ── 5. weekly / catch-up expiry ──────────────────────────────────────────────

def _insight(db_path, key, model, generated_at):
    con = sqlite3.connect(str(db_path))
    con.execute("""CREATE TABLE IF NOT EXISTS daily_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT, insight_date TEXT NOT NULL UNIQUE,
        content TEXT NOT NULL, sources TEXT DEFAULT '', generated_at TEXT NOT NULL,
        model TEXT DEFAULT '')""")
    con.execute("INSERT INTO daily_insights (insight_date, content, generated_at, model) "
                "VALUES (?, ?, ?, ?)", (key, f"brief {key}", generated_at, model))
    con.commit()
    con.close()


def test_an_old_weekly_brief_is_not_served(today_mod, tmp_db):
    old = datetime.datetime.now() - datetime.timedelta(days=20)
    _insight(tmp_db, old.date().isoformat() + "-weekly", "desktop-weekly", old.isoformat())
    assert today_mod._get_cached_brief("weekly") is None
    fresh = datetime.datetime.now() - datetime.timedelta(days=2)
    _insight(tmp_db, fresh.date().isoformat() + "-weekly", "claude-haiku-weekly", fresh.isoformat())
    assert today_mod._get_cached_brief("weekly") == f"brief {fresh.date().isoformat()}-weekly"


def test_a_catch_up_brief_is_for_its_own_day(today_mod, tmp_db):
    y = datetime.datetime.now() - datetime.timedelta(days=1)
    _insight(tmp_db, y.date().isoformat() + "-catchup", "desktop-catchup", y.isoformat())
    assert today_mod._get_cached_brief("catchup") is None
    t = datetime.date.today().isoformat() + "-catchup"
    _insight(tmp_db, t, "desktop-catchup", datetime.datetime.now().isoformat())
    assert today_mod._get_cached_brief("catchup") == f"brief {t}"


# ── 6. the second computer ───────────────────────────────────────────────────

def test_secondary_waits_for_the_main_computers_brief_then_takes_over(sched, tmp_db, monkeypatch):
    monkeypatch.setattr(sched, "_main_computer_active", lambda: True)
    monkeypatch.setattr(sched, "_hours_past_slot", lambda j: 1.0)
    assert sched._stand_down_reason("brief_synthesis") == "deferred"
    assert sched._ran_today("brief_synthesis") is False  # deferred is not done
    monkeypatch.setattr(sched, "_hours_past_slot", lambda j: 5.0)
    assert sched._stand_down_reason("brief_synthesis") is None  # runs here


def test_secondary_stands_down_once_the_brief_arrived(sched, tmp_db, monkeypatch):
    monkeypatch.setattr(sched, "_main_computer_active", lambda: True)
    _insight(tmp_db, datetime.date.today().isoformat(), "desktop-brief",
             datetime.datetime.now().isoformat())
    assert sched._stand_down_reason("brief_synthesis") == "skip"


# ── 7. catch-up slots ────────────────────────────────────────────────────────

@pytest.mark.parametrize("now_hm, job_time, expect", [
    ("10:00", "09:00", "today"),       # passed today
    ("08:00", "22:00", "yesterday"),   # evening job, morning start: last night's
    ("07:00", "09:00", None),          # due within 4 h: leave it to the cron
    ("23:30", "22:00", "today"),
])
def test_catchup_slot(sched, now_hm, job_time, expect):
    h, m = map(int, now_hm.split(":"))
    now = datetime.datetime(2026, 10, 28, h, m)
    slot = sched._catchup_slot(job_time, now)
    if expect is None:
        assert slot is None
    else:
        day = 28 if expect == "today" else 27
        jh, jm = map(int, job_time.split(":"))
        assert slot == datetime.datetime(2026, 10, day, jh, jm)


def test_evening_jobs_run_in_the_evening(sched):
    for job in ("evening_reflexion", "memory_consolidation", "nightly_backup"):
        hour = int(sched.JOB_DEFAULTS[job]["time"].split(":")[0])
        assert hour >= 21, f"{job} runs at {sched.JOB_DEFAULTS[job]['time']}"


# ── 8. session records ───────────────────────────────────────────────────────

def test_one_record_per_session(tmp_db):
    from metis_mcp._consolidate_session import upsert_session_summary
    con = sqlite3.connect(str(tmp_db))
    assert upsert_session_summary(con, "s-1", "first", ["a"], ["d"]) == "inserted"
    assert upsert_session_summary(con, "s-1", "second", None, None) == "updated"
    assert upsert_session_summary(con, "s-2", "other", [], []) == "inserted"
    rows = con.execute("SELECT session_id, summary, key_topics, decisions "
                       "FROM session_summaries ORDER BY id").fetchall()
    con.close()
    assert rows == [("auto:s-1", "second", '["a"]', '["d"]'),
                    ("auto:s-2", "other", "[]", "[]")]


def test_the_conversation_leads_the_record():
    from metis_mcp._consolidate_session import compose_summary
    text = compose_summary("## What was discussed\n- coverage in Kwilu",
                           "## Active projects\n- **HAT** — x" + " pad" * 40)
    assert text.startswith("## What was discussed")
    assert "The day's context" in text


def test_the_hourly_retry_reruns_only_unfinished_morning_work(sched, tmp_db, monkeypatch):
    ran = []
    monkeypatch.setattr(sched, "JOB_FUNCS", {
        "morning_scan": lambda: ran.append("morning_scan"),
        "library_scan": lambda: ran.append("library_scan"),
        "brief_synthesis": lambda: ran.append("brief_synthesis"),
    })
    monkeypatch.setattr(sched, "_hours_past_slot", lambda j: 2.0)
    sched._log_job("morning_scan", "error", "offline")   # failed → retried
    sched._log_job("library_scan", "ok", "fine")         # done → left alone
    sched._log_job("brief_synthesis", "deferred", "x")   # waiting → retried
    sched.job_retry_missed()
    assert ran == ["morning_scan", "brief_synthesis"]
