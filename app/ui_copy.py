"""Load user-facing copy dictionary from UI_COPY.json."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import UI_COPY_PATH


@lru_cache(maxsize=1)
def load_ui_copy(path: Path | None = None) -> dict[str, dict[str, str]]:
    target = path or UI_COPY_PATH
    with target.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        return {}
    return data


def ui_label(key: str, default: str = "") -> str:
    entry = load_ui_copy().get(key) or {}
    return entry.get("label") or default or key


def ui_tooltip(key: str, default: str = "") -> str:
    entry = load_ui_copy().get(key) or {}
    return entry.get("tooltip") or default


def ui_copy_context() -> dict[str, Any]:
    """Jinja-friendly context: ui_copy.seed.label / .tooltip"""
    return load_ui_copy()
