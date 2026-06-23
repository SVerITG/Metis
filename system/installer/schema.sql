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
    library_source TEXT DEFAULT 'manual'
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
    discovered_at  TEXT NOT NULL
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
    source_type    TEXT DEFAULT 'news'
);

CREATE TABLE IF NOT EXISTS news_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    headline     TEXT NOT NULL,
    source       TEXT DEFAULT '',
    published_at TEXT DEFAULT '',
    signal_tag   TEXT DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

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
    starred       INTEGER DEFAULT 0
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
    indexed_at  TEXT NOT NULL DEFAULT (datetime('now'))
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
    created_at TEXT NOT NULL
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
