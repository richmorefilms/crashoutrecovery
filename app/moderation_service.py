"""Atomic moderation services for the curated crashout business ledger."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from app.compose_engine import verify_compose_receipt
from app.compose_schemas import ApproveSeedRequest, SaveSeedRequest
from app.config import DATABASE_PATH
from app.db import open_connection, utc_now_iso


class ModerationNotFoundError(LookupError):
    pass


class ModerationConflictError(RuntimeError):
    pass


class ModerationValidationError(ValueError):
    pass


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def normalize_tags(tags: Iterable[str]) -> list[str]:
    return sorted({tag.strip().lower() for tag in tags if tag.strip()})


def queue_seed(
    request: SaveSeedRequest,
    *,
    submitted_by: int,
    db_path: Path | None = None,
) -> int:
    ai_generated = verify_compose_receipt(
        request.compose_receipt,
        request.spike_text,
    )
    conn = open_connection(db_path or DATABASE_PATH)
    try:
        conn.execute("BEGIN IMMEDIATE")
        now = utc_now_iso()
        cursor = conn.execute(
            """
            INSERT INTO moderation_queue (
                spike_text, suggested_rewrite, safe_move, tone, submitted_by,
                ai_generated, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                request.spike_text,
                request.suggested_rewrite,
                request.safe_move,
                request.tone,
                submitted_by,
                int(ai_generated),
                now,
            ),
        )
        queue_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO moderation_events (
                queue_id, event_type, actor_id, event_timestamp, details
            )
            VALUES (?, 'queued', ?, ?, ?)
            """,
            (
                queue_id,
                submitted_by,
                now,
                json.dumps(
                    {
                        "ai_generated": ai_generated,
                        "has_rewrite": bool(request.suggested_rewrite),
                        "has_safe_move": bool(request.safe_move),
                        "tone": request.tone,
                    },
                    separators=(",", ":"),
                ),
            ),
        )
        conn.commit()
        return queue_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _load_queue_row(conn: sqlite3.Connection, queue_id: int) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT id, spike_text, status, ai_generated
        FROM moderation_queue
        WHERE id = ?
        """,
        (queue_id,),
    ).fetchone()
    if row is None:
        raise ModerationNotFoundError("Moderation item not found")
    if row["status"] != "pending":
        raise ModerationConflictError("Moderation item has already been reviewed")
    return row


def promote_moderation_item(
    queue_id: int,
    request: ApproveSeedRequest,
    *,
    curated_by: int,
    db_path: Path | None = None,
) -> int:
    conn = open_connection(db_path or DATABASE_PATH)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = _load_queue_row(conn, queue_id)
        original_spike = str(row["spike_text"] or "")
        if _normalized_text(request.commentary) == _normalized_text(original_spike):
            raise ModerationValidationError(
                "Commentary must be staff-edited and cannot copy the submitted spike"
            )

        tags = normalize_tags(request.tags)
        now = utc_now_iso()
        update = conn.execute(
            """
            UPDATE moderation_queue
            SET status = 'approved',
                spike_text = NULL,
                suggested_rewrite = NULL,
                safe_move = NULL,
                reviewed_by = ?,
                reviewed_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (curated_by, now, queue_id),
        )
        if update.rowcount != 1:
            status_row = conn.execute(
                "SELECT status FROM moderation_queue WHERE id = ?",
                (queue_id,),
            ).fetchone()
            if status_row is None:
                raise ModerationNotFoundError("Moderation item not found")
            raise ModerationConflictError("Moderation item has already been reviewed")

        cursor = conn.execute(
            """
            INSERT INTO crashout_database (
                episode_title, commentary, recovery_moves, tone_variations,
                curated_by, source_queue_id, ai_generated, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.episode_title,
                request.commentary,
                json.dumps(request.recovery_moves, ensure_ascii=False),
                json.dumps(request.tone_variations, ensure_ascii=False),
                curated_by,
                queue_id,
                int(row["ai_generated"]),
                now,
            ),
        )
        crashout_id = int(cursor.lastrowid)

        for tag in tags:
            conn.execute(
                "INSERT INTO crashout_tags (crashout_id, tag) VALUES (?, ?)",
                (crashout_id, tag),
            )

        conn.execute(
            """
            INSERT INTO moderation_events (
                queue_id, event_type, actor_id, event_timestamp, details
            )
            VALUES (?, 'approved', ?, ?, ?)
            """,
            (
                queue_id,
                curated_by,
                now,
                json.dumps(
                    {
                        "crashout_id": crashout_id,
                        "ai_generated": bool(row["ai_generated"]),
                        "recovery_move_count": len(request.recovery_moves),
                        "tone_variation_count": len(request.tone_variations),
                        "tag_count": len(tags),
                    },
                    separators=(",", ":"),
                ),
            ),
        )
        conn.commit()
        return crashout_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reject_moderation_item(
    queue_id: int,
    *,
    reviewed_by: int,
    reason: str,
    db_path: Path | None = None,
) -> None:
    conn = open_connection(db_path or DATABASE_PATH)
    try:
        conn.execute("BEGIN IMMEDIATE")
        _load_queue_row(conn, queue_id)
        now = utc_now_iso()
        update = conn.execute(
            """
            UPDATE moderation_queue
            SET status = 'rejected',
                spike_text = NULL,
                suggested_rewrite = NULL,
                safe_move = NULL,
                reviewed_by = ?,
                reviewed_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (reviewed_by, now, queue_id),
        )
        if update.rowcount != 1:
            status_row = conn.execute(
                "SELECT status FROM moderation_queue WHERE id = ?",
                (queue_id,),
            ).fetchone()
            if status_row is None:
                raise ModerationNotFoundError("Moderation item not found")
            raise ModerationConflictError("Moderation item has already been reviewed")

        conn.execute(
            """
            INSERT INTO moderation_events (
                queue_id, event_type, actor_id, event_timestamp, details
            )
            VALUES (?, 'rejected', ?, ?, ?)
            """,
            (
                queue_id,
                reviewed_by,
                now,
                json.dumps(
                    {
                        "reason_recorded": bool(reason.strip()),
                        "reason_sha256": hashlib.sha256(
                            reason.strip().encode("utf-8")
                        ).hexdigest(),
                    },
                    separators=(",", ":"),
                ),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_pending_moderation(
    *,
    limit: int = 50,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    conn = open_connection(db_path or DATABASE_PATH)
    try:
        rows = conn.execute(
            """
            SELECT q.id, q.spike_text, q.suggested_rewrite, q.safe_move, q.tone,
                   q.submitted_by, u.username AS submitter_username,
                   q.ai_generated, q.status, q.created_at
            FROM moderation_queue q
            JOIN users u ON u.id = q.submitted_by
            WHERE q.status = 'pending'
            ORDER BY q.created_at ASC, q.id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "spike_text": row["spike_text"],
                "suggested_rewrite": row["suggested_rewrite"],
                "safe_move": row["safe_move"],
                "tone": row["tone"],
                "submitted_by": int(row["submitted_by"]),
                "submitter_username": row["submitter_username"],
                "ai_generated": bool(row["ai_generated"]),
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    finally:
        conn.close()
