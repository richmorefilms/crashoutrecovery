-- Crashout Recovery SQLite reference schema.
-- Runtime migrations are authoritative in app/db.py.
-- Database file: data/crashout.db

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'basic',
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'staff')),
    created_at TEXT NOT NULL,
    last_login TEXT
);

CREATE TABLE IF NOT EXISTS recovery (
    user_id INTEGER PRIMARY KEY,
    streak_days INTEGER NOT NULL DEFAULT 0,
    last_win_date TEXT,
    spike_history TEXT NOT NULL DEFAULT '[]',
    tones TEXT NOT NULL DEFAULT '[]',
    wins INTEGER NOT NULL DEFAULT 0,
    last_safe_move TEXT,
    last_safe_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS seeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    tone TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS market_packs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    pack_name TEXT NOT NULL,
    pack_type TEXT,
    pack_payload TEXT,
    installed_at TEXT NOT NULL,
    UNIQUE(user_id, pack_name),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
-- Legacy compatibility table. No current user-facing Market UI.

CREATE TABLE IF NOT EXISTS world_signals (
    user_id INTEGER NOT NULL,
    signal_date TEXT NOT NULL,
    signals TEXT NOT NULL DEFAULT '{}',
    forecast TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (user_id, signal_date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    jti TEXT NOT NULL UNIQUE,
    expires_at REAL NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS revoked_tokens (
    jti TEXT PRIMARY KEY,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS video_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL UNIQUE COLLATE NOCASE,
    youtube_id TEXT,
    title TEXT,
    channel TEXT,
    duration TEXT,
    thumbnail_url TEXT,
    source TEXT NOT NULL DEFAULT 'auto',
    cached_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS moderation_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spike_text TEXT,
    suggested_rewrite TEXT,
    safe_move TEXT,
    tone TEXT,
    submitted_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    ai_generated INTEGER NOT NULL CHECK (ai_generated IN (0, 1)),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by INTEGER REFERENCES users(id) ON DELETE RESTRICT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL,
    CHECK (status != 'pending' OR spike_text IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS crashout_database (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_title TEXT NOT NULL,
    commentary TEXT NOT NULL,
    recovery_moves TEXT NOT NULL DEFAULT '[]',
    tone_variations TEXT NOT NULL DEFAULT '[]',
    curated_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    source_queue_id INTEGER UNIQUE REFERENCES moderation_queue(id) ON DELETE RESTRICT,
    ai_generated INTEGER NOT NULL CHECK (ai_generated IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crashout_tags (
    crashout_id INTEGER NOT NULL REFERENCES crashout_database(id) ON DELETE CASCADE,
    tag TEXT NOT NULL
        CHECK (tag = lower(trim(tag)) AND length(tag) BETWEEN 1 AND 64),
    PRIMARY KEY (crashout_id, tag)
);

CREATE TABLE IF NOT EXISTS moderation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_id INTEGER NOT NULL REFERENCES moderation_queue(id) ON DELETE RESTRICT,
    event_type TEXT NOT NULL CHECK (event_type IN ('queued', 'approved', 'rejected')),
    actor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    event_timestamp TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_queue_status ON moderation_queue(status);
CREATE INDEX IF NOT EXISTS idx_queue_submitted_by ON moderation_queue(submitted_by);
CREATE INDEX IF NOT EXISTS idx_queue_reviewed_by ON moderation_queue(reviewed_by);
CREATE INDEX IF NOT EXISTS idx_crashout_tags_tag ON crashout_tags(tag);
CREATE INDEX IF NOT EXISTS idx_crashout_curated_by ON crashout_database(curated_by);
CREATE INDEX IF NOT EXISTS idx_moderation_events_queue_id ON moderation_events(queue_id);

CREATE TRIGGER IF NOT EXISTS moderation_events_no_update
BEFORE UPDATE ON moderation_events
BEGIN
    SELECT RAISE(ABORT, 'moderation_events is immutable');
END;

CREATE TRIGGER IF NOT EXISTS moderation_events_no_delete
BEFORE DELETE ON moderation_events
BEGIN
    SELECT RAISE(ABORT, 'moderation_events is immutable');
END;

-- localStorage key mapping:
-- crashout_recovery      -> recovery
-- crashout_seeds         -> seeds
-- crashout_market_packs  -> market_packs
-- crashout_world_signals -> world_signals
-- CrashoutMonetization tier -> users.tier
