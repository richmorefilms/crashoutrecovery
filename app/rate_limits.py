"""Phase F: rate-limit policies, enforcement, and lightweight abuse detection."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.db import insert_staff_audit_log, open_connection, utc_now_iso

# Limit type codes stored in rate_limits.limit_type
LIMIT_COMPOSE = "compose"
LIMIT_STAFF_VIEW = "staff_view"
LIMIT_STAFF_MODIFY = "staff_modify"

# Configurable policies
USER_COMPOSE_LIMIT = 30
USER_COMPOSE_WINDOW_SECONDS = 5 * 60

STAFF_COMPOSE_LIMIT = 200
STAFF_COMPOSE_WINDOW_SECONDS = 5 * 60

STAFF_VIEW_LIMIT = 500
STAFF_VIEW_WINDOW_SECONDS = 60 * 60

STAFF_MODIFY_LIMIT = 100
STAFF_MODIFY_WINDOW_SECONDS = 60 * 60

# Abuse: repeated rate-limit hits in a short window
ABUSE_HIT_THRESHOLD = 5
ABUSE_HIT_WINDOW_SECONDS = 10 * 60

EVENT_RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
EVENT_ABUSE_BURST = "ABUSE_BURST"
AUDIT_RATE_LIMIT_HIT = "RATE_LIMIT_HIT"
AUDIT_ABUSE_EVENT = "ABUSE_EVENT"


@dataclass(frozen=True)
class RateLimitPolicy:
    max_count: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitSnapshot:
    subject_id: str
    limit_type: str
    limit: int
    remaining: int
    window_end: int
    count: int


class RateLimitExceeded(Exception):
    """Raised when a subject exceeds a configured rate limit."""

    def __init__(
        self,
        *,
        subject_id: str,
        limit_type: str,
        limit: int,
        window_end: int,
        retry_after: int,
    ) -> None:
        self.subject_id = subject_id
        self.limit_type = limit_type
        self.limit = limit
        self.window_end = window_end
        self.retry_after = max(1, int(retry_after))
        super().__init__(
            f"Rate limit exceeded for {limit_type} ({limit} / window); "
            f"retry after {self.retry_after}s"
        )


def compose_policy_for_user(user: dict[str, Any] | None) -> RateLimitPolicy:
    if user and user.get("role") == "staff":
        return RateLimitPolicy(STAFF_COMPOSE_LIMIT, STAFF_COMPOSE_WINDOW_SECONDS)
    return RateLimitPolicy(USER_COMPOSE_LIMIT, USER_COMPOSE_WINDOW_SECONDS)


def staff_view_policy() -> RateLimitPolicy:
    return RateLimitPolicy(STAFF_VIEW_LIMIT, STAFF_VIEW_WINDOW_SECONDS)


def staff_modify_policy() -> RateLimitPolicy:
    return RateLimitPolicy(STAFF_MODIFY_LIMIT, STAFF_MODIFY_WINDOW_SECONDS)


def subject_for_user(user_id: int) -> str:
    return f"user:{int(user_id)}"


def subject_for_staff(staff_id: int) -> str:
    return f"staff:{int(staff_id)}"


def subject_for_ip(ip: str) -> str:
    cleaned = (ip or "unknown").strip() or "unknown"
    return f"ip:{cleaned}"


def compose_subject(user: dict[str, Any] | None, client_ip: str | None) -> str:
    if user and user.get("id") is not None:
        if user.get("role") == "staff":
            return subject_for_staff(int(user["id"]))
        return subject_for_user(int(user["id"]))
    return subject_for_ip(client_ip or "unknown")


def _active_window(
    conn: Any,
    *,
    subject_id: str,
    limit_type: str,
    now: int,
) -> Any | None:
    return conn.execute(
        """
        SELECT id, window_start, window_end, count
        FROM rate_limits
        WHERE subject_id = ? AND limit_type = ? AND window_end > ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (subject_id, limit_type, now),
    ).fetchone()


def check_rate_limit(
    subject_id: str,
    limit_type: str,
    *,
    policy: RateLimitPolicy | None = None,
    path: Path | None = None,
    staff_id_for_audit: int | None = None,
) -> RateLimitSnapshot:
    """
    Verify the subject is under the limit for this window.
    Does not increment. Uses BEGIN IMMEDIATE for a consistent read.
    """
    resolved = policy or _default_policy(limit_type)
    now = int(time.time())
    conn = open_connection(path)
    exceeded_count: int | None = None
    window_end = now + resolved.window_seconds
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = _active_window(
            conn, subject_id=subject_id, limit_type=limit_type, now=now
        )
        if row is None:
            conn.commit()
            return RateLimitSnapshot(
                subject_id=subject_id,
                limit_type=limit_type,
                limit=resolved.max_count,
                remaining=resolved.max_count,
                window_end=window_end,
                count=0,
            )

        count = int(row["count"])
        window_end = int(row["window_end"])
        if count >= resolved.max_count:
            exceeded_count = count
            conn.commit()
        else:
            conn.commit()
            return RateLimitSnapshot(
                subject_id=subject_id,
                limit_type=limit_type,
                limit=resolved.max_count,
                remaining=max(0, resolved.max_count - count),
                window_end=window_end,
                count=count,
            )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    _record_rate_limit_hit(
        subject_id=subject_id,
        limit_type=limit_type,
        limit=resolved.max_count,
        window_end=window_end,
        count=int(exceeded_count or resolved.max_count),
        path=path,
        staff_id_for_audit=staff_id_for_audit,
    )
    raise RateLimitExceeded(
        subject_id=subject_id,
        limit_type=limit_type,
        limit=resolved.max_count,
        window_end=window_end,
        retry_after=window_end - now,
    )


def increment_rate_limit(
    subject_id: str,
    limit_type: str,
    *,
    policy: RateLimitPolicy | None = None,
    path: Path | None = None,
) -> RateLimitSnapshot:
    """Increment the active window counter (or open a new window)."""
    resolved = policy or _default_policy(limit_type)
    now = int(time.time())
    conn = open_connection(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = _active_window(
            conn, subject_id=subject_id, limit_type=limit_type, now=now
        )
        if row is None:
            window_end = now + resolved.window_seconds
            conn.execute(
                """
                INSERT INTO rate_limits (
                    subject_id, window_start, window_end, count, limit_type
                ) VALUES (?, ?, ?, 1, ?)
                """,
                (subject_id, now, window_end, limit_type),
            )
            count = 1
        else:
            window_end = int(row["window_end"])
            count = int(row["count"]) + 1
            conn.execute(
                "UPDATE rate_limits SET count = ? WHERE id = ?",
                (count, int(row["id"])),
            )
        conn.commit()
        return RateLimitSnapshot(
            subject_id=subject_id,
            limit_type=limit_type,
            limit=resolved.max_count,
            remaining=max(0, resolved.max_count - count),
            window_end=window_end,
            count=count,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reset_rate_limit_windows(*, path: Path | None = None) -> None:
    """Clear rate-limit windows (test helper)."""
    conn = open_connection(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM rate_limits")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def log_abuse_event(
    subject_id: str,
    event_type: str,
    metadata: dict[str, Any] | None = None,
    *,
    path: Path | None = None,
    staff_id_for_audit: int | None = None,
) -> int:
    """Persist an abuse_events row; optionally mirror to staff_audit_log."""
    now = utc_now_iso()
    metadata_json = (
        json.dumps(metadata, sort_keys=True, separators=(",", ":")) if metadata else None
    )
    conn = open_connection(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            """
            INSERT INTO abuse_events (subject_id, event_type, metadata_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (subject_id, event_type, metadata_json, now),
        )
        event_id = int(cur.lastrowid)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if staff_id_for_audit is not None:
        insert_staff_audit_log(
            staff_id=staff_id_for_audit,
            action_type=AUDIT_ABUSE_EVENT,
            metadata={
                "subject_id": subject_id,
                "event_type": event_type,
                "abuse_event_id": event_id,
                **(metadata or {}),
            },
            path=path,
        )
    return event_id


def _default_policy(limit_type: str) -> RateLimitPolicy:
    if limit_type == LIMIT_STAFF_VIEW:
        return staff_view_policy()
    if limit_type == LIMIT_STAFF_MODIFY:
        return staff_modify_policy()
    return RateLimitPolicy(USER_COMPOSE_LIMIT, USER_COMPOSE_WINDOW_SECONDS)


def _record_rate_limit_hit(
    *,
    subject_id: str,
    limit_type: str,
    limit: int,
    window_end: int,
    count: int,
    path: Path | None,
    staff_id_for_audit: int | None,
) -> None:
    metadata = {
        "limit_type": limit_type,
        "limit": limit,
        "count": count,
        "window_end": window_end,
    }
    log_abuse_event(
        subject_id,
        EVENT_RATE_LIMIT_EXCEEDED,
        metadata,
        path=path,
        staff_id_for_audit=None,
    )
    if staff_id_for_audit is not None:
        insert_staff_audit_log(
            staff_id=staff_id_for_audit,
            action_type=AUDIT_RATE_LIMIT_HIT,
            metadata={"subject_id": subject_id, **metadata},
            path=path,
        )
    _maybe_flag_abuse_burst(
        subject_id=subject_id,
        path=path,
        staff_id_for_audit=staff_id_for_audit,
    )


def _maybe_flag_abuse_burst(
    *,
    subject_id: str,
    path: Path | None,
    staff_id_for_audit: int | None,
) -> None:
    """If >N rate-limit hits in abuse window, emit ABUSE_BURST once per window-ish."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(seconds=ABUSE_HIT_WINDOW_SECONDS)
    ).replace(microsecond=0).isoformat()
    conn = open_connection(path)
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS hits
            FROM abuse_events
            WHERE subject_id = ?
              AND event_type = ?
              AND created_at >= ?
            """,
            (subject_id, EVENT_RATE_LIMIT_EXCEEDED, cutoff),
        ).fetchone()
        hits = int(row["hits"] if row else 0)
    finally:
        conn.close()

    if hits < ABUSE_HIT_THRESHOLD:
        return

    # Avoid duplicate burst rows flooding: only log if no recent ABUSE_BURST.
    conn = open_connection(path)
    try:
        recent = conn.execute(
            """
            SELECT 1 FROM abuse_events
            WHERE subject_id = ? AND event_type = ? AND created_at >= ?
            LIMIT 1
            """,
            (subject_id, EVENT_ABUSE_BURST, cutoff),
        ).fetchone()
    finally:
        conn.close()
    if recent:
        return

    log_abuse_event(
        subject_id,
        EVENT_ABUSE_BURST,
        {
            "hits": hits,
            "threshold": ABUSE_HIT_THRESHOLD,
            "window_seconds": ABUSE_HIT_WINDOW_SECONDS,
        },
        path=path,
        staff_id_for_audit=staff_id_for_audit,
    )


def rate_limit_headers(snapshot: RateLimitSnapshot) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(snapshot.limit),
        "X-RateLimit-Remaining": str(snapshot.remaining),
        "X-RateLimit-Reset": str(snapshot.window_end),
    }


def http_429(exc: RateLimitExceeded) -> dict[str, Any]:
    return {
        "status_code": 429,
        "detail": {
            "error": "rate_limit_exceeded",
            "message": str(exc),
            "limit_type": exc.limit_type,
            "limit": exc.limit,
            "retry_after": exc.retry_after,
        },
        "headers": {
            "Retry-After": str(exc.retry_after),
            "X-RateLimit-Limit": str(exc.limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(exc.window_end),
        },
    }
