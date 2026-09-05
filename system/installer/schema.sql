-- Metis Research Cortex — SQLite schema
-- Generated from production DB. Run via init_db.py or: sqlite3 metis.sqlite < schema.sql

CREATE TABLE IF NOT EXISTS agent_runs (
    run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_slug    TEXT,
    task_summary  TEXT,
    input_path    TEXT,
    output_path   TEXT,
    status        TEXT DEFAULT 'completed',
    created_at    TEXT,
    input_tokens  INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    model         TEXT DEFAULT '',
    session_id    TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS agent_spans (
    span_id     TEXT PRIMARY KEY,
    parent_id   TEXT,
    run_id      INTEGER,
    session_id  TEXT,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'internal',
    status      TEXT NOT NULL DEFAULT 'running',
    start_ms    INTEGER NOT NULL,
    end_ms      INTEGER,
    duration_ms INTEGER,
    error       TEXT,
    tags        TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS brainstorm_sessions (
    session_id      TEXT PRIMARY KEY,
    topic           TEXT NOT NULL,
    sources_used    TEXT DEFAULT '',
    summary         TEXT DEFAULT '',
    linked_idea_ids TEXT DEFAULT '',
    created_at      TEXT NOT NULL,
    session_uuid    TEXT NOT NULL DEFAULT (lower(hex(randomblob(8))))
);

CREATE TABLE IF NOT EXISTS consent_ledger (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           TEXT NOT NULL DEFAULT (datetime('now')),
    action              TEXT NOT NULL,
    data_classification TEXT DEFAULT 'PUBLIC',
    agent_slug          TEXT DEFAULT '',
    notes               TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS contacts (
    contact_id  TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    role        TEXT DEFAULT '',
    affiliation TEXT DEFAULT '',
    notes       TEXT DEFAULT '',
    last_seen   TEXT DEFAULT '',
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS course_progress (
    progress_id  TEXT PRIMARY KEY,
    course_id    TEXT NOT NULL,
    lesson_id    TEXT NOT NULL,
    completed_at TEXT,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS course_topics (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    keyword   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    code          TEXT DEFAULT '',
    semester      TEXT DEFAULT '',
    description   TEXT DEFAULT '',
    student_count INTEGER DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS crucible_intake (
    intake_id           TEXT PRIMARY KEY,
    filename            TEXT,
    file_type           TEXT,
    analysis_type       TEXT,
    project_link        TEXT,
    phd_article_link    TEXT,
    analysis_depth      TEXT,
    focus               TEXT,
    custom_instructions TEXT,
    stored_path         TEXT,
    output_path         TEXT,
    status              TEXT DEFAULT 'pending',
    ideas_extracted     INTEGER DEFAULT 0,
    tasks_created       INTEGER DEFAULT 0,
    created_at          TEXT
);

CREATE TABLE IF NOT EXISTS daily_insights (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_date TEXT NOT NULL UNIQUE,
    content      TEXT NOT NULL,
    sources      TEXT DEFAULT '',
    generated_at TEXT NOT NULL,
    model        TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS dropzone_intake (
    intake_id               TEXT PRIMARY KEY,
    filename                TEXT,
    file_type               TEXT,
    analysis_type           TEXT,
    project_link            TEXT,
    research_article_link   TEXT,
    analysis_depth          TEXT,
    focus                   TEXT,
    custom_instructions     TEXT,
    stored_path             TEXT,
    output_path             TEXT,
    status                  TEXT DEFAULT 'pending',
    ideas_extracted         INTEGER DEFAULT 0,
    tasks_created           INTEGER DEFAULT 0,
    created_at              TEXT
);

CREATE TABLE IF NOT EXISTS finance_snapshots (
    snapshot_id   TEXT PRIMARY KEY,
    snapshot_date TEXT,
    category      TEXT,
    label         TEXT,
    headline      TEXT,
    detail        TEXT,
    trend         TEXT,
    project_link  TEXT,
    created_at    TEXT
);

CREATE TABLE IF NOT EXISTS finance_watchlist (
    item_id    TEXT PRIMARY KEY,
    category   TEXT,
    label      TEXT,
    notes      TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS focus_items (
    item_id   TEXT NOT NULL,
    item_type TEXT NOT NULL,
    week      TEXT NOT NULL,
    label     TEXT,
    pinned_at TEXT,
    PRIMARY KEY (item_id, week)
);

CREATE TABLE IF NOT EXISTS idea_links (
    link_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id_a TEXT,
    idea_id_b TEXT,
    link_label TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS ideas (
    idea_id        TEXT PRIMARY KEY,
    text           TEXT,
    project_id     TEXT,
    idea_type      TEXT,
    tags           TEXT,
    created_at     TEXT,
    domain         TEXT,
    linked_papers  TEXT,
    feasibility    TEXT,
    phd_relevance  TEXT,
    novelty_status TEXT
);

CREATE TABLE IF NOT EXISTS jobs_log (
    job_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type   TEXT,
    status     TEXT,
    details    TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS journal_entries (
    entry_id     TEXT PRIMARY KEY,
    content      TEXT NOT NULL,
    mood         TEXT DEFAULT '',
    energy_score INTEGER DEFAULT 0,
    summary      TEXT DEFAULT '',
    image_path   TEXT DEFAULT '',
    tags         TEXT DEFAULT '',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_links (
    link_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT,
    source_id   TEXT,
    target_type TEXT,
    target_id   TEXT,
    link_label  TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS learning_activities (
    activity_id   TEXT PRIMARY KEY,
    competency_id TEXT,
    activity_type TEXT,
    description   TEXT,
    completed_at  TEXT
);

CREATE TABLE IF NOT EXISTS learning_competencies (
    competency_id TEXT PRIMARY KEY,
    domain        TEXT,
    topic         TEXT,
    level         TEXT DEFAULT 'beginner',
    notes         TEXT,
    last_activity TEXT,
    created_at    TEXT
);

CREATE TABLE IF NOT EXISTS learning_courses (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    title             TEXT NOT NULL,
    category          TEXT DEFAULT '',
    progress_pct      REAL DEFAULT 0,
    total_modules     INTEGER DEFAULT 0,
    completed_modules INTEGER DEFAULT 0,
    status            TEXT DEFAULT 'active',
    completed_at      TEXT DEFAULT NULL,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    slug              TEXT,
    project_id        TEXT,
    current_lesson    TEXT DEFAULT '',
    next_lesson       TEXT DEFAULT '',
    course_url        TEXT DEFAULT '',
    lesson_notes      TEXT DEFAULT '',
    updated_at        TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS learning_resources (
    resource_id    TEXT PRIMARY KEY,
    competency_id  TEXT,
    title          TEXT,
    resource_type  TEXT,
    url            TEXT,
    recommended_by TEXT,
    created_at     TEXT
);

CREATE TABLE IF NOT EXISTS library_cards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    domain      TEXT DEFAULT '',
    tags        TEXT DEFAULT '',
    summary     TEXT DEFAULT '',
    source_path TEXT DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS library_duplicates (
    hash            TEXT,
    duplicate_count INTEGER,
    file            TEXT
);

CREATE TABLE IF NOT EXISTS library_fulltext (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    filename   TEXT NOT NULL UNIQUE,
    filepath   TEXT NOT NULL,
    title      TEXT,
    text_chunk TEXT,
    word_count INTEGER,
    indexed_at TEXT
);

CREATE TABLE IF NOT EXISTS library_inventory (
    relative_path TEXT PRIMARY KEY,
    basename      TEXT,
    top_folder    TEXT,
    extension     TEXT,
    size_bytes    INTEGER,
    modified_date TEXT
);

CREATE TABLE IF NOT EXISTS library_item_status (
    relative_path TEXT PRIMARY KEY,
    status        TEXT DEFAULT 'active',
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS library_seeded (
    relative_path      TEXT PRIMARY KEY,
    basename           TEXT,
    top_folder         TEXT,
    extension          TEXT,
    size_bytes         INTEGER,
    modified_date      TEXT,
    entity_type        TEXT,
    disease            TEXT,
    geography          TEXT,
    method             TEXT,
    surveillance_mode  TEXT,
    elimination_phase  TEXT,
    diagnostic_test    TEXT,
    project_link       TEXT,
    phd_article_link   TEXT,
    relevance_note     TEXT,
    status             TEXT
);

CREATE TABLE IF NOT EXISTS literature_metadata (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT NOT NULL,
    authors        TEXT DEFAULT '',
    year           TEXT DEFAULT '',
    source         TEXT DEFAULT '',
    tags           TEXT DEFAULT '',
    doi            TEXT DEFAULT '',
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    abstract       TEXT DEFAULT '',
    journal        TEXT DEFAULT '',
    item_type      TEXT DEFAULT '',
    url            TEXT DEFAULT '',
    zotero_key     TEXT DEFAULT '',
    zotero_version INTEGER DEFAULT 0,
    collection     TEXT DEFAULT '',
    library_source TEXT DEFAULT 'manual',
    -- Reading state. `is_read` existed in the live database from the day the
    -- read/unread toggle was built but was NEVER added here, so a fresh install
    -- or the second computer had no such column and the toggle would have failed
    -- there silently. Added to the schema 2026-08-29 (see the two-computer
    -- silent-failure rules: a new column goes in schema.sql, always).
    is_read        INTEGER DEFAULT 0,
    -- WHEN it was read, which is what makes "new since you last looked"
    -- answerable. Null means never read.
    read_at        TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS meeting_actions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id  INTEGER NOT NULL,
    description TEXT NOT NULL,
    status      TEXT DEFAULT 'open',
    due_date    TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS meeting_attendance (
    meeting_id TEXT,
    person_id  TEXT,
    PRIMARY KEY (meeting_id, person_id)
);

CREATE TABLE IF NOT EXISTS meeting_persons (
    person_id         TEXT PRIMARY KEY,
    name              TEXT,
    role              TEXT,
    last_meeting_date TEXT,
    meeting_count     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS meetings (
    meeting_id            TEXT PRIMARY KEY,
    title                 TEXT,
    meeting_date          TEXT,
    domain                TEXT,
    project               TEXT,
    source_filename       TEXT,
    stored_audio_path     TEXT,
    structured_note_path  TEXT,
    created_at            TEXT,
    transcript_path       TEXT,
    transcript_status     TEXT,
    attendees             TEXT,
    meeting_type          TEXT,
    decisions             TEXT,
    action_items          TEXT,
    follow_ups            TEXT,
    linked_meetings       TEXT,
    pre_briefing_path     TEXT,
    transcript            TEXT,
    duration_minutes      INTEGER,
    status                TEXT DEFAULT 'filed'
);

CREATE TABLE IF NOT EXISTS memory_entries (
    entry_id   TEXT PRIMARY KEY,
    entry_date TEXT,
    entry_type TEXT,
    topics     TEXT,
    title      TEXT,
    summary    TEXT,
    file_path  TEXT,
    computer   TEXT,
    created_at TEXT
);

-- The New Literature surface reads all of these. Keep this block in step with
-- `_NEW_PUBLICATIONS_DDL` in mcp-server/src/metis_mcp/tools/intelligence.py.
--
-- The columns below the original ten were added for the New Literature surface
-- and, for a while, existed ONLY in that module's DDL plus a hand-run script
-- (tools/migrate_new_literature.py). That is not enough. `CREATE TABLE IF NOT
-- EXISTS` never upgrades a table that already exists, so on any machine where
-- the script had not been run by hand the surface queried columns that were not
-- there — `no such column: title_key` (found 2026-08-24 on the second computer,
-- whose code syncs over OneDrive while its database does not).
--
-- This file is the one place the dashboard consults on every startup to add
-- missing columns to existing tables, so it is the only place that makes a
-- schema change reach every machine on its own. New column → add it HERE.
CREATE TABLE IF NOT EXISTS new_publications (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT NOT NULL,
    journal        TEXT DEFAULT '',
    pub_date       TEXT DEFAULT '',
    doi            TEXT DEFAULT '',
    topic_tag      TEXT DEFAULT '',
    relevance_note TEXT DEFAULT '',
    source_url     TEXT DEFAULT '',
    read_at        TEXT DEFAULT '',
    discovered_at  TEXT NOT NULL,
    -- Bibliographic: a catalogue row has to be readable on its own.
    authors        TEXT DEFAULT '',
    abstract       TEXT DEFAULT '',
    feed_name      TEXT DEFAULT '',
    -- Classification. entry_kind = what it is (article/review/preprint/book/
    -- report); lane = where it belongs (field | general science).
    entry_kind     TEXT DEFAULT 'article',
    lane           TEXT DEFAULT 'field',
    relevance      REAL DEFAULT 0,
    -- Normalised publication date. pub_date keeps whatever the source sent;
    -- pub_iso is the only field safe to compare or sort on.
    pub_iso        TEXT DEFAULT '',
    pub_precision  TEXT DEFAULT '',
    -- Deduplication key derived from the title.
    title_key      TEXT DEFAULT '',
    -- Acquisition state — what the red dot reads.
    acq_status     TEXT DEFAULT '',
    acq_reason     TEXT DEFAULT '',
    pdf_path       TEXT DEFAULT '',
    -- Lifecycle, split apart: added is not the same as dismissed.
    added_at       TEXT DEFAULT '',
    dismissed_at   TEXT DEFAULT '',
    zotero_key     TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS news_brief_topics (
    brief_id TEXT,
    topic_id TEXT,
    PRIMARY KEY (brief_id, topic_id)
);

CREATE TABLE IF NOT EXISTS news_briefs (
    brief_id       TEXT PRIMARY KEY,
    brief_date     TEXT,
    title          TEXT,
    domain         TEXT,
    signal_strength TEXT,
    summary        TEXT,
    project_link   TEXT,
    created_at     TEXT,
    source_url     TEXT,
    tags           TEXT,
    surprise_flag  INTEGER DEFAULT 0,
    source_type    TEXT DEFAULT 'news',
    -- Seen state. Without it the News surface showed the same 859 items on every
    -- visit with no sense of what had arrived since last time — which is the one
    -- thing that makes a feed readable rather than a wall. Added 2026-08-12.
    seen_at        TEXT DEFAULT NULL,
    -- When the story was PUBLISHED, from the feed. created_at is the SCAN time, so
    -- it answers "when did Metis notice this" — after the 13 Jul → 18 Aug 2026 scan
    -- gap every July story was stamped 18 August. Any daily/weekly/monthly filter
    -- must read COALESCE(published_at, created_at). Added 2026-08-19.
    published_at   TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS news_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    headline     TEXT NOT NULL,
    source       TEXT DEFAULT '',
    published_at TEXT DEFAULT '',
    signal_tag   TEXT DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Story threads. A long-running event (an epidemic, a funding shift) produces
-- fresh wire items every day; without grouping them into one persistent story
-- the daily brief led with the same thing every morning, because each item was
-- genuinely new. Cooldown is keyed on daily_insights.read_at — a brief that was
-- never marked read delivered nothing and must not silence a thread.
-- See mcp-server/src/metis_mcp/tools/news_threads.py. Added 2026-08-19.
CREATE TABLE IF NOT EXISTS news_threads (
    thread_id   TEXT PRIMARY KEY,
    label       TEXT NOT NULL,
    subject     TEXT DEFAULT '',
    place       TEXT DEFAULT '',
    keywords    TEXT DEFAULT '',
    domain      TEXT DEFAULT '',
    first_seen  TEXT,
    last_seen   TEXT,
    item_count  INTEGER DEFAULT 0,
    peak_signal TEXT DEFAULT 'low',
    max_number  INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'active'
);

-- Keyed on news_briefs.rowid, NOT brief_id: SQLite permits NULL in a TEXT
-- PRIMARY KEY, and most existing news_briefs rows have brief_id IS NULL.
CREATE TABLE IF NOT EXISTS news_thread_items (
    thread_id   TEXT NOT NULL,
    brief_ref   INTEGER NOT NULL,
    assigned_at TEXT,
    PRIMARY KEY (thread_id, brief_ref)
);

-- What each brief actually led with / mentioned, and the analytical angle used,
-- so recurring threads get a new lens rather than the same paragraph.
CREATE TABLE IF NOT EXISTS news_thread_mentions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id   TEXT NOT NULL,
    insight_key TEXT NOT NULL,
    period      TEXT NOT NULL DEFAULT 'daily',
    role        TEXT NOT NULL DEFAULT 'mention',
    angle       TEXT DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_thread_items_brief ON news_thread_items(brief_ref);
CREATE INDEX IF NOT EXISTS idx_thread_mentions_thread ON news_thread_mentions(thread_id);
CREATE INDEX IF NOT EXISTS idx_thread_mentions_key ON news_thread_mentions(insight_key);

-- Superseded by news_threads above. Retained because older installs have it;
-- no code writes to it.
CREATE TABLE IF NOT EXISTS news_topics (
    topic_id        TEXT PRIMARY KEY,
    label           TEXT,
    domain          TEXT,
    first_seen      TEXT,
    last_seen       TEXT,
    mention_count   INTEGER DEFAULT 1,
    trend_direction TEXT DEFAULT 'stable'
);

CREATE TABLE IF NOT EXISTS note_links (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path  TEXT NOT NULL,
    target_path  TEXT NOT NULL,
    link_type    TEXT NOT NULL DEFAULT 'related',
    source_title TEXT,
    target_title TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS personal_notes (
    note_id    TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    title      TEXT DEFAULT '',
    tags       TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    project_id TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS projects (
    project_id    TEXT PRIMARY KEY,
    title         TEXT,
    domain        TEXT,
    status        TEXT,
    priority      TEXT,
    next_step     TEXT,
    created_at    TEXT,
    external_path TEXT,
    github_url    TEXT,
    launch_cmd    TEXT,
    launcher_type TEXT,
    launcher_path TEXT,
    source        TEXT DEFAULT 'manual',
    description   TEXT,
    display_order    INTEGER DEFAULT 999,
    launchers        TEXT,
    dashboard_url    TEXT,
    notes            TEXT,
    project_type     TEXT DEFAULT 'research',
    context_doc      TEXT DEFAULT '',
    history_log      TEXT DEFAULT '[]',
    prompt_memory    TEXT DEFAULT '',
    last_session_at  TEXT,
    detection_source TEXT DEFAULT 'manual',
    tracked          INTEGER DEFAULT 1,
    started_at       TEXT,
    completed_at     TEXT,
    tags             TEXT DEFAULT '',
    image_url        TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS content_packs (
    pack_id      TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    version      TEXT DEFAULT '1.0',
    pack_type    TEXT DEFAULT 'course',
    description  TEXT DEFAULT '',
    installed_at TEXT,
    enabled      INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS reflexion_log (
    reflexion_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    agent_slug      TEXT NOT NULL,
    went_well       TEXT DEFAULT '',
    could_improve   TEXT DEFAULT '',
    missing_context TEXT DEFAULT '',
    tool_wishes     TEXT DEFAULT '',
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_milestones (
    milestone_id  TEXT PRIMARY KEY,
    article_title TEXT NOT NULL,
    target_date   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'planned',
    notes         TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_context (
    context_id   TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL,
    context_type TEXT NOT NULL,
    label        TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_events (
    event_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    client      TEXT DEFAULT 'code',
    computer    TEXT DEFAULT '',
    started_at  TEXT NOT NULL,
    last_active TEXT NOT NULL,
    summary     TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS skill_improvement_proposals (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_slug       TEXT NOT NULL,
    proposed_at      TEXT NOT NULL,
    rationale        TEXT DEFAULT '',
    current_content  TEXT DEFAULT '',
    proposed_content TEXT NOT NULL,
    status           TEXT DEFAULT 'pending',
    reviewer_note    TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS spaced_repetition (
    sr_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source_table  TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    front_text    TEXT,
    back_text     TEXT,
    next_review   TEXT NOT NULL,
    interval_days INTEGER DEFAULT 1,
    ease_factor   REAL DEFAULT 2.5,
    repetitions   INTEGER DEFAULT 0,
    created_at    TEXT NOT NULL,
    reviewed_at   TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS lesson_completions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    course_slug  TEXT NOT NULL,
    lesson_id    TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    UNIQUE(course_slug, lesson_id)
);

CREATE TABLE IF NOT EXISTS course_builds (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    slug             TEXT NOT NULL UNIQUE,
    title            TEXT NOT NULL,
    topic            TEXT NOT NULL,
    target_audience  TEXT DEFAULT '',
    duration_hours   INTEGER DEFAULT 0,
    status           TEXT DEFAULT 'intake',
    step             INTEGER DEFAULT 1,
    intake_json      TEXT DEFAULT '{}',
    outline_json     TEXT DEFAULT '[]',
    sources_dir      TEXT DEFAULT '',
    notes            TEXT DEFAULT '',
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS talks (
    talk_id              TEXT PRIMARY KEY,
    title                TEXT,
    speaker              TEXT,
    source               TEXT,
    event_name           TEXT,
    talk_date            TEXT,
    url                  TEXT,
    transcript_path      TEXT,
    structured_note_path TEXT,
    domain               TEXT,
    project_link         TEXT,
    key_takeaways        TEXT,
    created_at           TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id    TEXT PRIMARY KEY,
    project_id TEXT,
    title      TEXT,
    status     TEXT,
    due_date   TEXT,
    owner      TEXT,
    notes      TEXT,
    created_at TEXT,
    category      TEXT DEFAULT 'project',
    updated_at    TEXT DEFAULT NULL,
    display_order INTEGER DEFAULT 999,
    starred       INTEGER DEFAULT 0,
    -- Five queries across work.py and planner.py sort by t.priority. The column
    -- never existed on `tasks` (only on `projects`), so every one of them raised
    -- "no such column", db_query swallowed it into its empty default, and the Work
    -- surface reported "No open tasks across any project" while 79 open tasks sat
    -- in the table. Added 2026-08-12 with a default, so existing rows sort as
    -- 'medium' rather than vanishing.
    priority      TEXT DEFAULT 'medium'
);

CREATE TABLE IF NOT EXISTS tracked_files (
    path          TEXT PRIMARY KEY,
    last_modified TEXT NOT NULL,
    last_scanned  TEXT NOT NULL,
    label         TEXT DEFAULT '',
    watch         INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_topics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    topic       TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    active      INTEGER DEFAULT 1,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS zotero_sync_state (
    id           INTEGER PRIMARY KEY,
    last_version INTEGER DEFAULT 0,
    last_synced  TEXT,
    item_count   INTEGER DEFAULT 0
);

-- Phase L: PDF Knowledge Database — layered architecture
-- Users build knowledge layer by layer: foundation → specialist → custom

CREATE TABLE IF NOT EXISTS knowledge_databases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT NOT NULL UNIQUE,   -- 'ph-background', 'hat-specialist', 'epi-methods'
    name        TEXT NOT NULL,          -- 'Public Health Background'
    description TEXT DEFAULT '',
    layer       INTEGER DEFAULT 1,      -- 1=foundation, 2=specialist, 3=methods, 4+=custom
    color       TEXT DEFAULT '#6c757d', -- badge color for UI
    doc_count   INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    last_built  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pdf_chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    db_id       INTEGER NOT NULL DEFAULT 0,  -- FK → knowledge_databases.id
    source_file TEXT NOT NULL,
    domain      TEXT DEFAULT '',
    title       TEXT DEFAULT '',
    page_start  INTEGER DEFAULT 0,
    page_end    INTEGER DEFAULT 0,
    chunk_idx   INTEGER NOT NULL,
    chunk_text  TEXT NOT NULL,
    char_count  INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pdf_chunks_source ON pdf_chunks (source_file);
CREATE INDEX IF NOT EXISTS idx_pdf_chunks_domain  ON pdf_chunks (domain);
CREATE INDEX IF NOT EXISTS idx_pdf_chunks_db_id   ON pdf_chunks (db_id);

CREATE TABLE IF NOT EXISTS pdf_index_state (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    db_id       INTEGER NOT NULL DEFAULT 0,  -- FK → knowledge_databases.id
    source_file TEXT NOT NULL UNIQUE,
    domain      TEXT DEFAULT '',
    title       TEXT DEFAULT '',
    total_pages INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    file_size   INTEGER DEFAULT 0,
    indexed_at  TEXT NOT NULL DEFAULT (datetime('now')),
    -- Per-document provenance. Added 2026-08-24.
    --
    -- Background Maker's own instructions say "every document in the layer must
    -- have a real, verifiable URL or DOI. If a source can't be verified, skip
    -- it." That rule was not merely unenforced — there was NOWHERE TO RECORD THE
    -- ANSWER. A layer could not state where its own documents came from, so
    -- "verify at ingest and trust at read" had no substrate to stand on.
    --
    -- provenance: '' (never checked) | 'verified' (DOI/URL resolves)
    --             | 'unresolved' (looked, found nothing) | 'local' (no external
    --             source expected — own notes, meeting records)
    doi                    TEXT DEFAULT '',
    source_url             TEXT DEFAULT '',
    provenance             TEXT DEFAULT '',
    provenance_checked_at  TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS user_config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL DEFAULT '',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS session_summaries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    summary    TEXT NOT NULL,
    key_topics TEXT,
    decisions  TEXT,
    created_at TEXT NOT NULL,
    -- Five Today-surface queries filter on `archived` and the column never
    -- existed, so each raised "no such column", db_query swallowed it, and four
    -- panels rendered nothing while 716 summaries and 2,036 episodic memories sat
    -- in the tables. Same shape as the missing tasks.priority. Added 2026-08-12.
    archived   INTEGER DEFAULT 0
);

-- episodic_memory is created by the MCP server (tools/observation.py), not here,
-- but the dashboard filters it on `archived` too. Declared so the migration adds
-- the column regardless of which process created the table first.
CREATE TABLE IF NOT EXISTS episodic_memory (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    event_type TEXT,
    content    TEXT,
    metadata   TEXT,
    created_at TEXT,
    archived   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS speakers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    embedding   BLOB,
    sample_count INTEGER DEFAULT 1,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- ── Code Repository (reproducibility + code reuse) ──────────────────────────
CREATE TABLE IF NOT EXISTS code_artifacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  TEXT DEFAULT '',
    title       TEXT NOT NULL,
    language    TEXT DEFAULT '',
    kind        TEXT DEFAULT 'script',
    purpose     TEXT DEFAULT '',
    tags        TEXT DEFAULT '',
    code        TEXT DEFAULT '',
    file_path   TEXT DEFAULT '',
    packages    TEXT DEFAULT '',
    params      TEXT DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS data_dictionary (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    TEXT DEFAULT '',
    dataset_name  TEXT NOT NULL,
    dataset_path  TEXT DEFAULT '',
    variable_name TEXT NOT NULL,
    var_type      TEXT DEFAULT '',
    label         TEXT DEFAULT '',
    unique_values TEXT DEFAULT '',
    units         TEXT DEFAULT '',
    notes         TEXT DEFAULT '',
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dataset_treatments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id     TEXT DEFAULT '',
    dataset_name   TEXT NOT NULL,
    step_order     INTEGER DEFAULT 0,
    step_type      TEXT DEFAULT '',
    description    TEXT DEFAULT '',
    code           TEXT DEFAULT '',
    input_dataset  TEXT DEFAULT '',
    output_dataset TEXT DEFAULT '',
    created_at     TEXT NOT NULL
);

-- Data automation triggers — "when X happens, do Y"
CREATE TABLE IF NOT EXISTS data_triggers (
    trigger_id   TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    event_type   TEXT NOT NULL,           -- file-added, file-modified, scheduled, record-count
    source_path  TEXT DEFAULT '',          -- file or folder to watch
    action       TEXT NOT NULL,           -- profile, suggest-cleaning, clean, reindex-kg, alert, custom
    action_args  TEXT DEFAULT '{}',        -- JSON with action-specific parameters
    schedule     TEXT DEFAULT '',          -- cron expression for scheduled triggers
    project_id   TEXT DEFAULT '',          -- optional project link
    enabled      INTEGER DEFAULT 1,
    last_run_at  TEXT DEFAULT '',
    last_status  TEXT DEFAULT '',
    last_message TEXT DEFAULT '',
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

-- Log of trigger executions
CREATE TABLE IF NOT EXISTS data_trigger_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_id   TEXT NOT NULL,
    status       TEXT NOT NULL,           -- ok, error, skipped
    message      TEXT DEFAULT '',
    ran_at       TEXT NOT NULL
);

-- Today board items — Outbreaks · Events · Funding boxes on the Today surface
CREATE TABLE IF NOT EXISTS today_board_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    board       TEXT NOT NULL,          -- 'outbreaks' | 'events' | 'funding'
    title       TEXT NOT NULL,
    url         TEXT DEFAULT '',
    description TEXT DEFAULT '',
    source      TEXT DEFAULT '',        -- 'WHO DON', 'ProMED', 'manual', etc.
    starred     INTEGER DEFAULT 0,      -- 1 = favorited
    dismissed   INTEGER DEFAULT 0,      -- 1 = soft-deleted by user
    -- seen_at answers a DIFFERENT question from starred/dismissed: those two
    -- record a decision, this records attention. Without it the only way to
    -- stop an item looking new was to delete it, and the "new" highlight was
    -- computed from created_at age — so it cleared on a clock rather than on
    -- being read, and every visible row was highlighted at once.
    seen_at     TEXT DEFAULT '',        -- ISO ts when the reader acknowledged it
    auto_added  INTEGER DEFAULT 1,      -- 1 = from scan, 0 = manually added
    start_date  TEXT DEFAULT '',        -- event start date / outbreak onset
    end_date    TEXT DEFAULT '',        -- event end date
    -- PINNING IS FOLLOWING, and it needs two things starring never had.
    -- Asked for 2026-09-04: "i want to follow a certain outbreak like Ebola,
    -- I pin it and so every day it can show the newest report of it... I can
    -- also chose their order and see which one I put on top."
    -- pin_order  = the order the reader chose, lowest first. 0 means unset,
    --              so an unordered pin still sorts by recency behind ordered ones.
    -- follow_terms = what to watch for in the news stream. Empty means derive
    --              it from the title, because the common case is pinning an
    --              item you are already looking at and expecting it to follow
    --              itself.
    pin_order   INTEGER DEFAULT 0,
    follow_terms TEXT DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_board_items_board ON today_board_items (board, dismissed, created_at);

-- ── Day planner (Work → Calendar) ────────────────────────────────────────────
-- One table covers every planning object the Work calendar shows, because they
-- differ only in `kind`: a project dragged onto a day, a written focus for that
-- day, or a reminder. Multiple rows per date = multiple focuses, which is the
-- normal case. end_date makes a focus span several days without duplicating rows.
CREATE TABLE IF NOT EXISTS day_plan (
    plan_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date  TEXT NOT NULL,
    end_date    TEXT,
    kind        TEXT NOT NULL DEFAULT 'focus',
    project_id  TEXT,
    text        TEXT,
    remind_at   TEXT,
    done        INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_day_plan_start ON day_plan(start_date);
CREATE INDEX IF NOT EXISTS idx_day_plan_span  ON day_plan(start_date, end_date);

-- ── Open decisions ledger ────────────────────────────────────────────────────
-- Separate from user_decisions: that holds STANDING preferences with no lifecycle
-- ("always use tidyverse"). This holds a question awaiting a call, with a lifecycle
-- (open → agreed/rejected/deferred/dropped) and the reasoning behind the outcome.
-- The fingerprint is a normalised token set, so a decision restated in different
-- words updates times_seen instead of creating a duplicate row.
CREATE TABLE IF NOT EXISTS open_decisions (
    od_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    statement    TEXT NOT NULL,
    fingerprint  TEXT NOT NULL UNIQUE,
    project_id   TEXT,
    first_seen   TEXT NOT NULL,
    last_seen    TEXT NOT NULL,
    times_seen   INTEGER NOT NULL DEFAULT 1,
    state        TEXT NOT NULL DEFAULT 'open',
    resolution   TEXT,
    resolved_at  TEXT,
    source       TEXT
);
CREATE INDEX IF NOT EXISTS idx_open_decisions_state ON open_decisions(state, last_seen DESC);

-- ---------------------------------------------------------------------------
-- Citation ledger — every verification verdict Metis has ever reached.
--
-- Declared HERE and not only in tools/verification.py, for the reason recorded
-- on 2026-08-24: this file is the one mechanism that carries a schema change to
-- the other computer on its own. The dashboard reads it on every startup and
-- adds anything missing. A table that lives only in a module's DDL exists on
-- whichever machine happened to run that module first.
--
-- Without this table a verification result lived for one reply and evaporated,
-- which is why "which of my outputs rest on unverified citations?" was an
-- archaeology problem rather than a query.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS citation_checks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    claim         TEXT NOT NULL,
    source_cited  TEXT DEFAULT '',
    page_cited    INTEGER,
    quote_cited   TEXT DEFAULT '',
    doi           TEXT DEFAULT '',
    tier          TEXT DEFAULT 'A',
    verdict       TEXT NOT NULL,
    detail        TEXT DEFAULT '',
    artifact_path TEXT DEFAULT '',
    session_id    TEXT DEFAULT '',
    checked_at    TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Focus areas — a lens over news, literature and your own thinking.
--
-- Added 2026-08-24. A focus is for a subject you want to stay CURRENT on, which
-- is a different shape from a course you finish or a project you deliver. The
-- "AI in Public Health course" was the case that made this obvious: it had no
-- end, so a course was the wrong container for it.
--
-- A FOCUS OWNS NO CONTENT. It owns a query. News stays in news_briefs, papers in
-- new_publications, thinking in ideas/personal_notes tagged `focus:<slug>`,
-- documents in pdf_chunks. That is what makes removal safe: archiving a lens
-- cannot remove what was seen through it, and two overlapping focuses do not
-- duplicate a single paper.
--
-- keyword_groups is JSON list-of-lists: OR within a group, AND across groups.
-- A flat keyword list for "AI in health" returns "Can AI ever be conscious?";
-- the conjunction returns "AI model helps clinicians detect heart obstruction".
--
-- state: active (on the shelf, max 3, in the navbar) | following (off the
--        navbar, still queryable) | archived (read-only, no refresh).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS focus_areas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    slug              TEXT NOT NULL UNIQUE,
    title             TEXT NOT NULL,
    subtitle          TEXT DEFAULT '',
    state             TEXT DEFAULT 'following',
    shelf_slot        INTEGER,
    keyword_groups    TEXT DEFAULT '[]',
    layers            TEXT DEFAULT '',
    overview          TEXT DEFAULT '',
    created_at        TEXT NOT NULL,
    activated_at      TEXT DEFAULT '',
    archived_at       TEXT DEFAULT '',
    last_visited_at   TEXT DEFAULT '',
    last_refreshed_at TEXT DEFAULT '',
    sections          TEXT DEFAULT '',
    links             TEXT DEFAULT '',
    n_new             INTEGER DEFAULT 0,
    n_new_at          TEXT DEFAULT ''
);

-- ---------------------------------------------------------------------------
-- Standing decisions, attributable to an agent.
--
-- Added 2026-08-24. `user_decisions` held TWO rows while session summaries held
-- 7,578 decision entries — the write path had no reader, again, and it was the
-- most consequential instance yet: it is the reason invoking a specialist added
-- nothing. An agent that cannot recall "how the researcher wants a dashboard
-- built" is a persona, not a specialist, so there was never a reason to route to
-- one.
--
-- agent_slug attributes a standing preference to the specialist that should
-- apply it: frontend-designer-builder remembers layout decisions, writing-partner
-- remembers prose decisions, librarian remembers what matters in the library.
-- NULL/'' means it applies to every agent (a project-wide rule).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category    TEXT DEFAULT '',
    decision    TEXT NOT NULL,
    context     TEXT DEFAULT '',
    scope       TEXT DEFAULT 'always',
    source      TEXT DEFAULT 'user',
    hits        INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL,
    agent_slug  TEXT DEFAULT '',
    supersedes  INTEGER,
    last_applied_at TEXT DEFAULT ''
);

-- ---------------------------------------------------------------------------
-- READING STACK — one triage store for everything that arrives (2026-08-26).
--
-- Before it, "I will read this later" had three implementations and one hole:
-- papers used new_publications.added_at/dismissed_at/read_at, focus areas used
-- focus_verdict, and news had nothing at all — the News surface rendered seven
-- tabs and 337 links with zero actions on any of them.
--
-- A paper's verdict is ALSO mirrored onto the new_publications columns, because
-- the Library surface reads those directly; without the mirror the two pages
-- disagree the first time either is used alone. `added_at` is deliberately never
-- written from here: on this schema it means "acquired, with a PDF".
-- ---------------------------------------------------------------------------
-- ── Corpus title aliases ────────────────────────────────────────────────
-- One document indexed twice under two names is not two documents. 69 such
-- groups were found on 2026-08-31 — 3,671 chunks, ~8% of the index — where the
-- TEXT was byte-identical and only the naming convention differed: a
-- descriptive title beside a journal id, a WHO document code, an author tag, or
-- a bare filename ("Bumpyroadtoelimination", "Lancet").
--
-- They are MERGED rather than deleted. The text is kept once under the most
-- informative title; every other name is recorded here. Three reasons, and the
-- third is why this table exists at all:
--   1. retrieval stops spending two of six slots on the same passage;
--   2. searching for the old name still finds the document;
--   3. NOTHING IS LOST in the handful where the right name is genuinely
--      unclear — one group has a thesis and a paper by DIFFERENT AUTHORS
--      sharing a fingerprint, so one file is mislabelled. Deleting the "copy"
--      there would destroy the correct name for something still held; keeping
--      both as aliases leaves the question open and answerable later.
--
-- needs_review marks exactly those. chunks_removed makes the operation
-- auditable, and the row is what an undo would read.
CREATE TABLE IF NOT EXISTS pdf_title_aliases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_title TEXT NOT NULL,
    alias_title     TEXT NOT NULL,
    alias_file      TEXT DEFAULT '',
    chunks_removed  INTEGER DEFAULT 0,
    needs_review    INTEGER DEFAULT 0,
    merged_at       TEXT NOT NULL,
    UNIQUE(alias_title)
);
CREATE INDEX IF NOT EXISTS idx_alias_canonical ON pdf_title_aliases(canonical_title);

CREATE TABLE IF NOT EXISTS reading_stack (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT NOT NULL,          -- 'news' | 'paper'
    item_id    TEXT NOT NULL,
    state      TEXT NOT NULL,          -- saved | later | declined | read
    title      TEXT DEFAULT '',
    url        TEXT DEFAULT '',
    source     TEXT DEFAULT '',
    tags       TEXT DEFAULT '',
    note       TEXT DEFAULT '',
    added_at   TEXT NOT NULL,
    state_at   TEXT NOT NULL,
    -- Flagged as worth the START of a day, not merely worth reading. This is
    -- what reaches back to the Today surface: one line under "what should I
    -- read", never a list. Added 2026-08-29 — the stack stops being a tab and
    -- becomes a tab inside Library, so it needs a way to speak to Today.
    crucial    INTEGER DEFAULT 0,
    UNIQUE(kind, item_id)
);
CREATE INDEX IF NOT EXISTS idx_stack_state ON reading_stack(state, state_at);
CREATE INDEX IF NOT EXISTS idx_stack_kind  ON reading_stack(kind, item_id);

-- ---------------------------------------------------------------------------
-- FOCUS SAFE — one researcher's judgement on one item seen through one lens.
--
-- `title` is denormalised on purpose: the taste model needs the words even for
-- rows later pruned from news_briefs, and a safe whose contents vanish when
-- upstream tidies up is not a safe.
--
-- Declining DEMOTES, it never deletes. In a research tool an absence you were
-- never told about cannot be audited.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS focus_verdict (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    slug       TEXT NOT NULL,
    kind       TEXT NOT NULL,          -- 'news' | 'reading'
    item_id    TEXT NOT NULL,
    verdict    TEXT NOT NULL,          -- 'kept' | 'declined'
    title      TEXT DEFAULT '',
    url        TEXT DEFAULT '',
    note       TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(slug, kind, item_id)
);
CREATE INDEX IF NOT EXISTS idx_verdict_slug ON focus_verdict(slug, verdict);

-- A generated focus brief is KEPT, not recomputed on view — same reason as the
-- morning brief: a brief read on Tuesday must still say on Friday what it said.
CREATE TABLE IF NOT EXISTS focus_brief_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    slug       TEXT NOT NULL,
    body       TEXT NOT NULL,
    n_news     INTEGER DEFAULT 0,
    n_reading  INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_focus_brief_slug ON focus_brief_log(slug, created_at);

-- Per-occurrence state for a repeating calendar plan. One row plus a rule is
-- expanded at draw time, so "done", "skipped" and "moved" cannot live on the
-- plan itself — they belong to a single occurrence of it.
CREATE TABLE IF NOT EXISTS day_plan_occurrence (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id      INTEGER NOT NULL,
    occurred_on  TEXT NOT NULL,
    done         INTEGER DEFAULT 0,
    skipped      INTEGER DEFAULT 0,
    moved_to     TEXT DEFAULT '',
    notified_at  TEXT DEFAULT '',
    UNIQUE(plan_id, occurred_on)
);


-- ---------------------------------------------------------------------------
-- NATURE BRIEFING (2026-08-27) — the editorial digests, as EDITIONS.
--
-- Not a wire feed: someone decided what mattered today and in what order, and
-- that running order is the value. Shredding an edition into news_briefs would
-- add its stories to a feed already carrying 3,700 and lose exactly that.
--
-- Reached through the public Mailchimp campaign archive linked in the footer of
-- every issue. One feed carries every variant — Daily, AI & Robotics,
-- Translational Research, and the translated editions — told apart by the
-- masthead image's alt text. `lang` exists because Nature publishes the Arabic
-- Briefing on the same list; it is the daily briefing and belongs in the table,
-- just not in a panel read in English.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS briefing_edition (
    edition_id   TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    lang         TEXT DEFAULT 'en',
    title        TEXT NOT NULL,
    published_at TEXT NOT NULL,
    url          TEXT DEFAULT '',
    n_items      INTEGER DEFAULT 0,
    fetched_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_edition_kind ON briefing_edition(kind, published_at DESC);

CREATE TABLE IF NOT EXISTS briefing_item (
    item_id     TEXT PRIMARY KEY,
    edition_id  TEXT NOT NULL,
    ord         INTEGER DEFAULT 0,
    headline    TEXT NOT NULL,
    blurb       TEXT DEFAULT '',
    url         TEXT DEFAULT '',
    source      TEXT DEFAULT '',
    -- FETCHED FROM THE ARTICLE PAGE, not from the briefing e-mail. The e-mail
    -- carries neither: `blurb` is its own summary cut at 420 characters, and
    -- there is no image at all. Asked for both on 2026-09-04, so
    -- tools/enrich_briefing_items.py reads each article's own og:image and
    -- og:description. `enriched_at` records the attempt so a failure is not
    -- retried on every render, and `enrich_note` says WHY when it failed —
    -- several publishers refuse a scripted request, and a silent blank is
    -- indistinguishable from an article with no picture.
    image_url    TEXT DEFAULT '',
    description  TEXT DEFAULT '',
    enriched_at  TEXT DEFAULT '',
    enrich_note  TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_item_edition ON briefing_item(edition_id, ord);

-- ---------------------------------------------------------------------------
-- VIZ LIBRARY (2026-08-28) — saved visual taste, as rows rather than prose.
--
-- Four tables and not one, because "multiple styles per type of visualization"
-- is only expressible if kind, method and look vary independently:
--   viz_exemplars  what was admired, and where it came from (provenance)
--   viz_recipes    the METHOD — survives a complete restyle
--   viz_styles     the LOOK — reusable across recipes
--   viz_uses       every render: recipe x style x dataset x verdict
--
-- `viz_recipes.data_contract` is the load-bearing field: a JSON object of
-- role -> meaning. Reproducing a figure with other data is mechanical only if
-- the recipe declares what SHAPE of data it needs.
--
-- `unverified` on exemplars and styles exists because the first record was
-- written from knowledge of a page that blocks automated fetching. A field
-- known to be unconfirmed must say so in the row, or the library launders
-- recollection into fact.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS viz_exemplars (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    source          TEXT DEFAULT '',
    url             TEXT DEFAULT '',
    published       TEXT DEFAULT '',
    kind            TEXT DEFAULT '',
    what_you_liked  TEXT DEFAULT '',
    screenshot_path TEXT DEFAULT '',
    unverified      TEXT DEFAULT '',
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS viz_recipes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    kind          TEXT NOT NULL,
    one_liner     TEXT DEFAULT '',
    encoding      TEXT DEFAULT '',
    mark_unit     TEXT DEFAULT '',
    data_contract TEXT DEFAULT '{}',
    interaction   TEXT DEFAULT '',
    medium        TEXT DEFAULT '',
    code          TEXT DEFAULT '',
    caveats       TEXT DEFAULT '',
    default_style TEXT DEFAULT '',
    derived_from  TEXT DEFAULT '',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_viz_recipes_kind ON viz_recipes(kind);

CREATE TABLE IF NOT EXISTS viz_styles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    one_liner       TEXT DEFAULT '',
    good_for        TEXT DEFAULT '',
    palette         TEXT DEFAULT '',
    type_scale      TEXT DEFAULT '',
    axis_treatment  TEXT DEFAULT '',
    annotation_rule TEXT DEFAULT '',
    motion          TEXT DEFAULT '',
    theme_pair      TEXT DEFAULT '',
    notes           TEXT DEFAULT '',
    derived_from    TEXT DEFAULT '',
    unverified      TEXT DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS viz_uses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe       TEXT NOT NULL,
    style        TEXT DEFAULT '',
    dataset      TEXT DEFAULT '',
    project_id   TEXT DEFAULT '',
    output_path  TEXT DEFAULT '',
    artifact_url TEXT DEFAULT '',
    verdict      TEXT DEFAULT '',
    note         TEXT DEFAULT '',
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_viz_uses_recipe ON viz_uses(recipe, verdict);
CREATE INDEX IF NOT EXISTS idx_viz_uses_style  ON viz_uses(style, verdict);

-- ── LIBRARY SHELVES ─────────────────────────────────────────────────────────
-- A shelf is a REASON FOR KEEPING, not a topic label. Asked for 2026-09-05:
-- "if I put an article in Methodology, I like the article for its methodology
-- that interests me, maybe not straight away. If I put something in AI it's
-- because I am making an AI library to follow up its development."
--
-- Those two sentences describe two different OBJECTS, and that is why one flat
-- `collection` column has been NULL on all 1,144 library rows since it was
-- added: a single list cannot behave two ways. `kind` is what makes a shelf
-- usable rather than merely labelled:
--
--   purpose     why the work is good. Timeless, raided on demand, never a
--               queue. Sorted by fit to what you are doing now, not by date.
--   tracking    following a field as it develops. Chronological, and the only
--               kind for which "what is new since I last looked" is a question.
--   attachment  evidence bound to one project or course. It surfaces on that
--               thing's own card, because that is where it will be wanted.
CREATE TABLE IF NOT EXISTS library_shelves (
    slug        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'purpose',  -- purpose | tracking | attachment
    blurb       TEXT DEFAULT '',
    ref         TEXT DEFAULT '',   -- attachment only: project_id or course slug
    sort_order  INTEGER DEFAULT 0,
    archived    INTEGER DEFAULT 0,
    created_at  TEXT,
    -- Stamped when a TRACKING category is opened, so "new since you last
    -- looked" means since you last read it — not since a scan ran, which is a
    -- fact about the machine and not about the reader. Null on the other kinds,
    -- which have no such question.
    last_seen_at TEXT
);

-- A JOIN TABLE, not a column on the item. One paper legitimately belongs on
-- several shelves — a spatial analysis kept for its methods, filed against a
-- project, and part of a subject you track — and the standing preference is
-- that overlap between narrow categories costs nothing while a category broad
-- enough to need filtering costs time on every visit.
CREATE TABLE IF NOT EXISTS library_shelf_items (
    shelf     TEXT NOT NULL,
    kind      TEXT NOT NULL,       -- 'paper' | 'news'
    item_id   TEXT NOT NULL,
    note      TEXT DEFAULT '',
    added_at  TEXT NOT NULL,
    PRIMARY KEY (shelf, kind, item_id)
);
CREATE INDEX IF NOT EXISTS idx_shelf_items_shelf ON library_shelf_items(shelf, added_at DESC);
CREATE INDEX IF NOT EXISTS idx_shelf_items_item  ON library_shelf_items(kind, item_id);
