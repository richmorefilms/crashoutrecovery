import asyncio
import json

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.auth_deps import require_staff
from app.compose_engine import (
    InvalidComposeReceipt,
    build_compose_response,
    verify_compose_receipt,
)
from app.compose_schemas import ApproveSeedRequest


def test_curated_content_is_preferred_without_assistance(monkeypatch):
    monkeypatch.setattr(
        "app.compose_engine._find_curated_matches",
        lambda _text: [
            {
                "id": 7,
                "tone_variations": json.dumps(
                    ["Calm reviewed", "Clear reviewed", "Stable reviewed"]
                ),
                "recovery_moves": json.dumps(
                    ["Save reviewed", "Pause reviewed", "Share reviewed"]
                ),
            }
        ],
    )

    response = build_compose_response("I need to slow down before I post")

    assert [item.source for item in response.tone_suggestions] == [
        "staff-curated",
        "staff-curated",
        "staff-curated",
    ]
    assert [item.source for item in response.cta_suggestions] == [
        "staff-curated",
        "staff-curated",
        "staff-curated",
    ]
    assert all(item.crashout_id == 7 for item in response.tone_suggestions)
    assert verify_compose_receipt(response.compose_receipt, "I need to slow down before I post") is False


def test_sparse_content_is_clearly_labeled_assisted(monkeypatch):
    monkeypatch.setattr("app.compose_engine._find_curated_matches", lambda _text: [])
    logged = []
    monkeypatch.setattr("team_model.log_pattern", logged.append)
    monkeypatch.setattr(
        "team_model.log_suggestion_for_training",
        lambda *_args, **_kwargs: logged.append("training"),
    )
    text = "I am deleting everything forever"

    response = build_compose_response(text)

    assert response.curated_matches == 0
    assert response.tone_suggestions
    assert response.cta_suggestions
    assert all(item.source == "AI-assisted" for item in response.tone_suggestions)
    assert all(item.source == "AI-assisted" for item in response.cta_suggestions)
    assert response.predictor.risk_level in {"rising", "high"}
    assert verify_compose_receipt(response.compose_receipt, text) is True
    with pytest.raises(InvalidComposeReceipt):
        verify_compose_receipt(response.compose_receipt, f"{text} changed")
    assert logged == []


def test_moderation_lists_are_bounded_before_serialization():
    with pytest.raises(ValidationError):
        ApproveSeedRequest(
            episode_title="Reviewed title",
            commentary="Staff-edited commentary",
            recovery_moves=["x" * 501],
        )
    with pytest.raises(ValidationError):
        ApproveSeedRequest(
            episode_title="Reviewed title",
            commentary="Staff-edited commentary",
            tone_variations=[123],
        )


def test_staff_authorization_is_role_based_not_tier_based():
    user = {"id": 1, "role": "user", "tier": "pro"}
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_staff(user))
    assert exc.value.status_code == 403

    staff = {"id": 2, "role": "staff", "tier": "basic"}
    assert asyncio.run(require_staff(staff)) == staff
