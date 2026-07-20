"""Pytest configuration for Crashout Recovery tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.decision_flow import explain_match  # noqa: E402


def detect_tone(text: str | None) -> str:
    """Tone detection helper — wraps explain_match (production API)."""
    return explain_match(text)["tone"]


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "compose_receipts: exercise compose_receipts DB persistence",
    )


@pytest.fixture(autouse=True)
def _stub_compose_receipt_persist(monkeypatch, request):
    """Avoid writing compose provenance during unit tests unless opted in."""
    if request.node.get_closest_marker("compose_receipts"):
        return
    monkeypatch.setattr(
        "app.compose_engine.record_compose_receipt",
        lambda **_kwargs: 0,
    )
