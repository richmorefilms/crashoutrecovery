"""SQLite helpers for Crashout Recovery auth + per-user persistence."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from app.config import DATABASE_PATH

SCHEMA_SQL = """
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

CREATE INDEX IF NOT EXISTS idx_seeds_user ON seeds(user_id);

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

CREATE INDEX IF NOT EXISTS idx_market_packs_user ON market_packs(user_id);

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

CREATE INDEX IF NOT EXISTS idx_refresh_user ON refresh_tokens(user_id);

CREATE TABLE IF NOT EXISTS revoked_tokens (
    jti TEXT PRIMARY KEY,
    expires_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_revoked_expires ON revoked_tokens(expires_at);

CREATE TABLE IF NOT EXISTS user_data (
    user_id INTEGER NOT NULL,
    data_key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, data_key),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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

CREATE INDEX IF NOT EXISTS idx_video_cache_youtube ON video_cache(youtube_id);
"""

CURATED_SCHEMA_MIGRATION = "2026-07-curated-crashout-v1"

CURATED_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS moderation_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        spike_text TEXT,
        suggested_rewrite TEXT,
        safe_move TEXT,
        tone TEXT,
        submitted_by INTEGER NOT NULL,
        ai_generated INTEGER NOT NULL CHECK (ai_generated IN (0, 1)),
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'approved', 'rejected')),
        reviewed_by INTEGER,
        reviewed_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (submitted_by) REFERENCES users(id) ON DELETE RESTRICT,
        FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE RESTRICT,
        CHECK (status != 'pending' OR spike_text IS NOT NULL)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_queue_status ON moderation_queue(status)",
    "CREATE INDEX IF NOT EXISTS idx_queue_submitted_by ON moderation_queue(submitted_by)",
    "CREATE INDEX IF NOT EXISTS idx_queue_reviewed_by ON moderation_queue(reviewed_by)",
    """
    CREATE TABLE IF NOT EXISTS crashout_database (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        episode_title TEXT NOT NULL,
        commentary TEXT NOT NULL,
        recovery_moves TEXT NOT NULL DEFAULT '[]',
        tone_variations TEXT NOT NULL DEFAULT '[]',
        curated_by INTEGER NOT NULL,
        source_queue_id INTEGER UNIQUE,
        ai_generated INTEGER NOT NULL CHECK (ai_generated IN (0, 1)),
        created_at TEXT NOT NULL,
        FOREIGN KEY (curated_by) REFERENCES users(id) ON DELETE RESTRICT,
        FOREIGN KEY (source_queue_id) REFERENCES moderation_queue(id) ON DELETE RESTRICT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_crashout_curated_by ON crashout_database(curated_by)",
    """
    CREATE TABLE IF NOT EXISTS crashout_tags (
        crashout_id INTEGER NOT NULL,
        tag TEXT NOT NULL
            CHECK (tag = lower(trim(tag)) AND length(tag) BETWEEN 1 AND 64),
        PRIMARY KEY (crashout_id, tag),
        FOREIGN KEY (crashout_id) REFERENCES crashout_database(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_crashout_tags_tag ON crashout_tags(tag)",
    """
    CREATE TABLE IF NOT EXISTS moderation_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        queue_id INTEGER NOT NULL,
        event_type TEXT NOT NULL
            CHECK (event_type IN ('queued', 'approved', 'rejected')),
        actor_id INTEGER NOT NULL,
        event_timestamp TEXT NOT NULL,
        details TEXT NOT NULL DEFAULT '{}',
        FOREIGN KEY (queue_id) REFERENCES moderation_queue(id) ON DELETE RESTRICT,
        FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE RESTRICT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_moderation_events_queue_id ON moderation_events(queue_id)",
    """
    CREATE TRIGGER IF NOT EXISTS moderation_events_no_update
    BEFORE UPDATE ON moderation_events
    BEGIN
        SELECT RAISE(ABORT, 'moderation_events is immutable');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS moderation_events_no_delete
    BEFORE DELETE ON moderation_events
    BEGIN
        SELECT RAISE(ABORT, 'moderation_events is immutable');
    END
    """,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def open_connection(path: Path | None = None) -> sqlite3.Connection:
    """Open one hardened SQLite connection.

    Foreign-key enforcement is connection-scoped in SQLite, so every caller
    must go through this helper.
    """
    db_path = path or DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


# Integer schema ladder (PRAGMA user_version). Curated base schema is version 1.
# Phase C: MIGRATIONS[2] adds compose_receipts provenance ledger.
# Phase D: MIGRATIONS[3] adds retention/expiry soft-delete columns.
# Phase E: MIGRATIONS[4] adds staff_audit_log for oversight actions.
# Phase F: MIGRATIONS[5] adds rate_limits + abuse_events.
# Phase G: MIGRATIONS[6–9] stories media, premium ads, club promos, impressions.
MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {}

CURATED_USER_VERSION = 1
COMPOSE_RECEIPTS_USER_VERSION = 2
COMPOSE_RETENTION_USER_VERSION = 3
STAFF_AUDIT_USER_VERSION = 4
RATE_LIMITS_USER_VERSION = 5
STORIES_MEDIA_USER_VERSION = 6
PREMIUM_ADS_USER_VERSION = 7
CLUB_PROMOS_USER_VERSION = 8
AD_IMPRESSIONS_USER_VERSION = 9

COMPOSE_RECEIPTS_DDL = """
CREATE TABLE IF NOT EXISTS compose_receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL UNIQUE,
    user_id INTEGER,
    staff_id INTEGER,
    input_prompt TEXT NOT NULL,
    output_text TEXT NOT NULL,
    tone TEXT,
    model_name TEXT,
    parameters_json TEXT,
    created_at TEXT NOT NULL,
    moderation_flags TEXT,
    output_hash TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE SET NULL
)
"""

STAFF_AUDIT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS staff_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    target_request_id TEXT,
    target_receipt_id INTEGER,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE RESTRICT
)
"""

RATE_LIMITS_DDL = """
CREATE TABLE IF NOT EXISTS rate_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id TEXT NOT NULL,
    window_start INTEGER NOT NULL,
    window_end INTEGER NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    limit_type TEXT NOT NULL
)
"""

ABUSE_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS abuse_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL
)
"""

STORIES_DDL = """
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    crashout_id INTEGER,
    published INTEGER NOT NULL DEFAULT 0 CHECK (published IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (crashout_id) REFERENCES crashout_database(id) ON DELETE SET NULL
)
"""

PREMIUM_ADS_DDL = """
CREATE TABLE IF NOT EXISTS premium_ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_type TEXT NOT NULL
        CHECK (ad_type IN ('banner', 'poster', 'video', 'club_promo')),
    media_url TEXT NOT NULL,
    target_url TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL
)
"""

CLUB_PROMOTIONS_DDL = """
CREATE TABLE IF NOT EXISTS club_promotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    media_url TEXT,
    video_url TEXT,
    description TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL
)
"""

AD_IMPRESSIONS_DDL = """
CREATE TABLE IF NOT EXISTS ad_impressions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_id INTEGER NOT NULL,
    ad_source TEXT NOT NULL CHECK (ad_source IN ('premium', 'club')),
    user_id INTEGER,
    surface TEXT NOT NULL DEFAULT 'web',
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
)
"""


def get_user_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0] if row else 0)


def set_user_version(conn: sqlite3.Connection, version: int) -> None:
    version = int(version)
    if version < 0:
        raise ValueError("user_version must be >= 0")
    # PRAGMA user_version does not accept bound parameters.
    conn.execute(f"PRAGMA user_version = {version}")


def _migrate_to_v2(conn: sqlite3.Connection) -> None:
    """Phase C: audit-grade compose receipt ledger."""
    conn.execute(COMPOSE_RECEIPTS_DDL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_compose_receipts_created_at "
        "ON compose_receipts(created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_compose_receipts_output_hash "
        "ON compose_receipts(output_hash)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_compose_receipts_user_id "
        "ON compose_receipts(user_id)"
    )


def _migrate_to_v3(conn: sqlite3.Connection) -> None:
    """Phase D: retention / soft-delete columns on compose_receipts."""
    cols = {
        row[1] for row in conn.execute("PRAGMA table_info(compose_receipts)").fetchall()
    }
    if "expires_at" not in cols:
        conn.execute("ALTER TABLE compose_receipts ADD COLUMN expires_at TEXT")
    if "deleted_at" not in cols:
        conn.execute("ALTER TABLE compose_receipts ADD COLUMN deleted_at TEXT")
    if "retention_policy" not in cols:
        conn.execute("ALTER TABLE compose_receipts ADD COLUMN retention_policy TEXT")
    # Existing rows keep expires_at NULL (no expiry assigned yet).
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_compose_receipts_expires_at "
        "ON compose_receipts(expires_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_compose_receipts_deleted_at "
        "ON compose_receipts(deleted_at)"
    )


def _migrate_to_v4(conn: sqlite3.Connection) -> None:
    """Phase E: staff audit log for receipt oversight actions."""
    conn.execute(STAFF_AUDIT_LOG_DDL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_staff_audit_created_at "
        "ON staff_audit_log(created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_staff_audit_staff_id "
        "ON staff_audit_log(staff_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_staff_audit_action_type "
        "ON staff_audit_log(action_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_staff_audit_target_request "
        "ON staff_audit_log(target_request_id)"
    )


def _migrate_to_v5(conn: sqlite3.Connection) -> None:
    """Phase F: rate-limit windows and abuse event ledger."""
    conn.execute(RATE_LIMITS_DDL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_rate_limits_subject_type "
        "ON rate_limits(subject_id, limit_type, window_end)"
    )
    conn.execute(ABUSE_EVENTS_DDL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_abuse_events_subject_created "
        "ON abuse_events(subject_id, created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_abuse_events_type_created "
        "ON abuse_events(event_type, created_at)"
    )


def _migrate_to_v6(conn: sqlite3.Connection) -> None:
    """Phase G: story presentation table + media URL columns (not crashout_database)."""
    conn.execute(STORIES_DDL)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(stories)").fetchall()}
    if "image_url" not in cols:
        conn.execute("ALTER TABLE stories ADD COLUMN image_url TEXT")
    if "video_url" not in cols:
        conn.execute("ALTER TABLE stories ADD COLUMN video_url TEXT")
    if "thumbnail_url" not in cols:
        conn.execute("ALTER TABLE stories ADD COLUMN thumbnail_url TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_stories_published_created "
        "ON stories(published, created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_stories_crashout_id ON stories(crashout_id)"
    )


def _migrate_to_v7(conn: sqlite3.Connection) -> None:
    """Phase G: premium ad inventory."""
    conn.execute(PREMIUM_ADS_DDL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_premium_ads_active_type "
        "ON premium_ads(active, ad_type)"
    )


def _migrate_to_v8(conn: sqlite3.Connection) -> None:
    """Phase G: club promotion slots."""
    conn.execute(CLUB_PROMOTIONS_DDL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_club_promotions_active "
        "ON club_promotions(active, created_at)"
    )


def _migrate_to_v9(conn: sqlite3.Connection) -> None:
    """Phase G: ad impression logging."""
    conn.execute(AD_IMPRESSIONS_DDL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ad_impressions_created "
        "ON ad_impressions(created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ad_impressions_ad "
        "ON ad_impressions(ad_source, ad_id)"
    )


MIGRATIONS[COMPOSE_RECEIPTS_USER_VERSION] = _migrate_to_v2
MIGRATIONS[COMPOSE_RETENTION_USER_VERSION] = _migrate_to_v3
MIGRATIONS[STAFF_AUDIT_USER_VERSION] = _migrate_to_v4
MIGRATIONS[RATE_LIMITS_USER_VERSION] = _migrate_to_v5
MIGRATIONS[STORIES_MEDIA_USER_VERSION] = _migrate_to_v6
MIGRATIONS[PREMIUM_ADS_USER_VERSION] = _migrate_to_v7
MIGRATIONS[CLUB_PROMOS_USER_VERSION] = _migrate_to_v8
MIGRATIONS[AD_IMPRESSIONS_USER_VERSION] = _migrate_to_v9


def migrate(conn: sqlite3.Connection) -> None:
    """Apply pending MIGRATIONS entries in ascending order; bump user_version each step."""
    current = get_user_version(conn)
    for version in sorted(MIGRATIONS.keys()):
        if version <= current:
            continue
        if version != current + 1:
            raise RuntimeError(
                f"Migration gap: database is at user_version={current}, "
                f"next registered migration is {version}"
            )
        runner = MIGRATIONS[version]
        conn.execute("BEGIN IMMEDIATE")
        try:
            runner(conn)
            set_user_version(conn, version)
            conn.commit()
            current = version
        except Exception:
            conn.rollback()
            raise


def init_db(path: Path | None = None) -> None:
    """Create/upgrade base schema (v1) then apply MIGRATIONS ladder."""
    db_path = path or DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = open_connection(db_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA_SQL)
        _ensure_base_schema(conn)
        migrate(conn)
    finally:
        conn.close()


def insert_compose_receipt(
    *,
    request_id: str,
    input_prompt: str,
    output_text: str,
    output_hash: str,
    engine_version: str,
    tone: str | None = None,
    model_name: str | None = None,
    parameters_json: str | None = None,
    moderation_flags: str | None = None,
    user_id: int | None = None,
    staff_id: int | None = None,
    created_at: str | None = None,
    expires_at: str | None = None,
    retention_policy: str | None = None,
    deleted_at: str | None = None,
    path: Path | None = None,
) -> int:
    """Persist one compose provenance row. Returns receipt id."""
    now = created_at or utc_now_iso()
    with get_conn(path) as conn:
        cur = conn.execute(
            """
            INSERT INTO compose_receipts (
                request_id, user_id, staff_id, input_prompt, output_text,
                tone, model_name, parameters_json, created_at,
                moderation_flags, output_hash, engine_version,
                expires_at, deleted_at, retention_policy
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                user_id,
                staff_id,
                input_prompt,
                output_text,
                tone,
                model_name,
                parameters_json,
                now,
                moderation_flags,
                output_hash,
                engine_version,
                expires_at,
                deleted_at,
                retention_policy,
            ),
        )
        return int(cur.lastrowid)


def soft_delete_compose_receipt(
    *,
    request_id: str | None = None,
    receipt_id: int | None = None,
    deleted_at: str | None = None,
    path: Path | None = None,
) -> bool:
    """Mark a compose receipt soft-deleted. Returns True if a row was updated."""
    if (request_id is None) == (receipt_id is None):
        raise ValueError("Provide exactly one of request_id or receipt_id")
    stamp = deleted_at or utc_now_iso()
    with get_conn(path) as conn:
        if request_id is not None:
            cur = conn.execute(
                """
                UPDATE compose_receipts
                SET deleted_at = ?
                WHERE request_id = ? AND deleted_at IS NULL
                """,
                (stamp, request_id),
            )
        else:
            cur = conn.execute(
                """
                UPDATE compose_receipts
                SET deleted_at = ?
                WHERE id = ? AND deleted_at IS NULL
                """,
                (stamp, int(receipt_id)),
            )
        return cur.rowcount > 0


def list_active_compose_receipts(
    *,
    limit: int = 50,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return non-deleted compose receipts (newest first)."""
    return query_compose_receipts(include_deleted=False, limit=limit, path=path)


def query_compose_receipts(
    *,
    user_id: int | None = None,
    staff_id: int | None = None,
    request_id: str | None = None,
    retention_policy: str | None = None,
    moderation_flags: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    expires_from: str | None = None,
    expires_to: str | None = None,
    deleted_from: str | None = None,
    deleted_to: str | None = None,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    """Staff browser query over compose_receipts with optional filters."""
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    clauses: list[str] = []
    params: list[Any] = []

    if not include_deleted:
        clauses.append("deleted_at IS NULL")
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(int(user_id))
    if staff_id is not None:
        clauses.append("staff_id = ?")
        params.append(int(staff_id))
    if request_id:
        clauses.append("request_id = ?")
        params.append(request_id)
    if retention_policy:
        clauses.append("retention_policy = ?")
        params.append(retention_policy)
    if moderation_flags:
        clauses.append("moderation_flags LIKE ? ESCAPE '\\'")
        escaped = (
            moderation_flags.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        params.append(f"%{escaped}%")
    if created_from:
        clauses.append("created_at >= ?")
        params.append(created_from)
    if created_to:
        clauses.append("created_at <= ?")
        params.append(created_to)
    if expires_from:
        clauses.append("expires_at >= ?")
        params.append(expires_from)
    if expires_to:
        clauses.append("expires_at <= ?")
        params.append(expires_to)
    if deleted_from:
        clauses.append("deleted_at >= ?")
        params.append(deleted_from)
    if deleted_to:
        clauses.append("deleted_at <= ?")
        params.append(deleted_to)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.extend((limit, offset))
    with get_conn(path) as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM compose_receipts
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
    return [{key: row[key] for key in row.keys()} for row in rows]


def get_compose_receipt(
    *,
    request_id: str | None = None,
    receipt_id: int | None = None,
    include_deleted: bool = False,
    path: Path | None = None,
) -> dict[str, Any] | None:
    """Fetch one compose receipt by request_id or id."""
    if (request_id is None) == (receipt_id is None):
        raise ValueError("Provide exactly one of request_id or receipt_id")
    clauses = ["request_id = ?"] if request_id is not None else ["id = ?"]
    params: list[Any] = [request_id if request_id is not None else int(receipt_id)]
    if not include_deleted:
        clauses.append("deleted_at IS NULL")
    with get_conn(path) as conn:
        row = conn.execute(
            f"""
            SELECT * FROM compose_receipts
            WHERE {' AND '.join(clauses)}
            LIMIT 1
            """,
            params,
        ).fetchone()
    return row_to_dict(row)


def update_compose_receipt_retention(
    *,
    request_id: str | None = None,
    receipt_id: int | None = None,
    retention_policy: str | None = None,
    expires_at: str | None = None,
    path: Path | None = None,
) -> dict[str, Any] | None:
    """Update retention fields on a non-deleted receipt. Returns updated row or None."""
    if (request_id is None) == (receipt_id is None):
        raise ValueError("Provide exactly one of request_id or receipt_id")
    if retention_policy is None and expires_at is None:
        raise ValueError("Provide retention_policy and/or expires_at")

    sets: list[str] = []
    params: list[Any] = []
    if retention_policy is not None:
        sets.append("retention_policy = ?")
        params.append(retention_policy)
    if expires_at is not None:
        sets.append("expires_at = ?")
        params.append(expires_at)

    if request_id is not None:
        where = "request_id = ? AND deleted_at IS NULL"
        params.append(request_id)
    else:
        where = "id = ? AND deleted_at IS NULL"
        params.append(int(receipt_id))

    with get_conn(path) as conn:
        cur = conn.execute(
            f"UPDATE compose_receipts SET {', '.join(sets)} WHERE {where}",
            params,
        )
        if cur.rowcount <= 0:
            return None
        if request_id is not None:
            row = conn.execute(
                "SELECT * FROM compose_receipts WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM compose_receipts WHERE id = ?",
                (int(receipt_id),),
            ).fetchone()
    return row_to_dict(row)


def insert_staff_audit_log(
    *,
    staff_id: int,
    action_type: str,
    target_request_id: str | None = None,
    target_receipt_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    created_at: str | None = None,
    path: Path | None = None,
) -> int:
    """Append one staff audit event. Returns log id."""
    now = created_at or utc_now_iso()
    metadata_json = (
        json.dumps(metadata, sort_keys=True, separators=(",", ":")) if metadata else None
    )
    with get_conn(path) as conn:
        cur = conn.execute(
            """
            INSERT INTO staff_audit_log (
                staff_id, action_type, target_request_id, target_receipt_id,
                metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(staff_id),
                action_type,
                target_request_id,
                target_receipt_id,
                metadata_json,
                now,
            ),
        )
        return int(cur.lastrowid)


def list_staff_audit_log(
    *,
    limit: int = 50,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    with get_conn(path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM staff_audit_log
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [{key: row[key] for key in row.keys()} for row in rows]


def _ensure_base_schema(conn: sqlite3.Connection) -> None:
    """Legacy ALTER + curated tables/triggers; stamp PRAGMA user_version = 1."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )

        cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "last_login" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
        if "tier" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN tier TEXT NOT NULL DEFAULT 'basic'")
        if "role" not in cols:
            conn.execute(
                """
                ALTER TABLE users
                ADD COLUMN role TEXT NOT NULL DEFAULT 'user'
                CHECK (role IN ('user', 'staff'))
                """
            )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")

        video_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(video_cache)").fetchall()
        }
        if video_cols and "source" not in video_cols:
            conn.execute(
                "ALTER TABLE video_cache ADD COLUMN source TEXT NOT NULL DEFAULT 'auto'"
            )

        applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = ?",
            (CURATED_SCHEMA_MIGRATION,),
        ).fetchone()
        if not applied:
            for statement in CURATED_SCHEMA_STATEMENTS:
                conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
                (CURATED_SCHEMA_MIGRATION, utc_now_iso()),
            )

        # Staff roles are assigned explicitly (CLI or staff-gated API), never by email.

        # Curated schema is schema version 1. Do not downgrade newer databases.
        if get_user_version(conn) < CURATED_USER_VERSION:
            set_user_version(conn, CURATED_USER_VERSION)

        conn.commit()
    except Exception:
        conn.rollback()
        raise


def promote_user_to_staff(username_or_email: str, path: Path | None = None) -> dict[str, Any] | None:
    """Explicit staff promotion by username or email. Returns updated user row or None."""
    identity = (username_or_email or "").strip()
    if not identity:
        return None
    with get_conn(path) as conn:
        row = conn.execute(
            """
            SELECT id, username, email, tier, role, created_at, last_login
            FROM users
            WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE
            """,
            (identity, identity.lower()),
        ).fetchone()
        if not row:
            return None
        conn.execute("UPDATE users SET role = 'staff' WHERE id = ?", (int(row["id"]),))
        updated = conn.execute(
            """
            SELECT id, username, email, tier, role, created_at, last_login
            FROM users WHERE id = ?
            """,
            (int(row["id"]),),
        ).fetchone()
    return row_to_dict(updated)


@contextmanager
def get_conn(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = open_connection(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}
