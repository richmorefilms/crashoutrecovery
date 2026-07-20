"""Shared tone regression helpers."""

from __future__ import annotations

import json
from pathlib import Path

TONE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TONE_DIR.parent.parent
CASES_PATH = TONE_DIR / "tone_cases.json"

EXPECTED_ORDER = ["humorous", "direct", "strategic", "calm", "universal"]


def load_tone_cases() -> dict:
    with CASES_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def all_labeled_cases() -> list[tuple[str, str, str]]:
    """Return (category, text, expected_tone) for every case."""
    data = load_tone_cases()
    rows: list[tuple[str, str, str]] = []
    for category in ("humorous", "direct", "strategic", "calm", "universal"):
        for text in data[category]:
            rows.append((category, text, category if category != "universal" else "universal"))
    for text in data.get("placeholder_universal", []):
        rows.append(("placeholder_universal", text, "universal"))
    return rows


def all_parity_inputs() -> list[str]:
    data = load_tone_cases()
    texts: list[str] = []
    for key in ("humorous", "direct", "strategic", "calm", "universal", "placeholder_universal"):
        texts.extend(data.get(key, []))
    return texts


def xfail_reasons() -> dict[str, str]:
    return load_tone_cases().get("xfail", {})
