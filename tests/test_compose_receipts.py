"""Phase C: compose_receipts provenance ledger."""

from __future__ import annotations

import json

import jwt
import pytest

from app.compose_engine import (
    COMPOSE_ENGINE_VERSION,
    _text_hash,
    build_compose_response,
)
from app.config import JWT_ALGORITHM, JWT_SECRET
from app.db import get_user_version, init_db, open_connection


@pytest.mark.compose_receipts
def test_compose_persists_receipt_row(tmp_path, monkeypatch):
    db_path = tmp_path / "compose_provenance.db"
    init_db(db_path)

    monkeypatch.setattr("app.compose_engine._find_curated_matches", lambda _text: [])

    spike = "I need to slow down before I post"
    response = build_compose_response(spike, db_path=db_path)

    payload = jwt.decode(response.compose_receipt, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    request_id = payload["jti"]

    conn = open_connection(db_path)
    try:
        assert get_user_version(conn) == 9
        row = conn.execute(
            "SELECT * FROM compose_receipts WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        assert row is not None
        assert row["input_prompt"] == spike
        assert row["tone"] == response.tone
        assert row["engine_version"] == COMPOSE_ENGINE_VERSION
        assert row["output_hash"] == _text_hash(row["output_text"])
        assert row["model_name"] == "compose_engine"
        assert row["retention_policy"] == "default_365d"
        assert row["expires_at"]
        assert row["deleted_at"] is None
        params = json.loads(row["parameters_json"])
        assert params["ai_generated"] is True
        output = json.loads(row["output_text"])
        assert output["curated_matches"] == 0
        assert len(output["tone_suggestions"]) == 3
    finally:
        conn.close()


@pytest.mark.compose_receipts
def test_migration_creates_compose_receipts_with_retention(tmp_path):
    db_path = tmp_path / "v3.db"
    init_db(db_path)
    conn = open_connection(db_path)
    try:
        assert get_user_version(conn) == 9
        cols = {row[1] for row in conn.execute("PRAGMA table_info(compose_receipts)")}
        assert {
            "id",
            "request_id",
            "input_prompt",
            "output_text",
            "output_hash",
            "engine_version",
            "created_at",
            "expires_at",
            "deleted_at",
            "retention_policy",
        }.issubset(cols)
    finally:
        conn.close()
