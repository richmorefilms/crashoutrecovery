"""Tone regression tests for app/decision_flow.py."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.decision_flow import DEFAULT_TONE, RULES
from tests.conftest import detect_tone
from tests.tone.tone_fixtures import load_tone_cases, xfail_reasons

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DECISION_FLOW_JS = PROJECT_ROOT / "static" / "decision-flow.js"


def _cases(category: str) -> list[str]:
    return load_tone_cases()[category]


def _parametrize_cases(category: str):
    xfail = xfail_reasons()
    params = []
    for text in _cases(category):
        marks = ()
        if text in xfail:
            marks = (pytest.mark.xfail(reason=xfail[text], strict=False),)
        params.append(pytest.param(text, category, marks=marks))
    return params


class TestHumorousTone:
    @pytest.mark.parametrize("text,expected", _parametrize_cases("humorous"))
    def test_social_reaction_patterns(self, text: str, expected: str) -> None:
        assert detect_tone(text) == expected


class TestDirectTone:
    @pytest.mark.parametrize("text,expected", _parametrize_cases("direct"))
    def test_irreversible_action_patterns(self, text: str, expected: str) -> None:
        assert detect_tone(text) == expected


class TestStrategicTone:
    @pytest.mark.parametrize("text,expected", _parametrize_cases("strategic"))
    def test_algorithm_metrics_patterns(self, text: str, expected: str) -> None:
        assert detect_tone(text) == expected


class TestCalmTone:
    @pytest.mark.parametrize("text,expected", _parametrize_cases("calm"))
    def test_emotional_overwhelm_patterns(self, text: str, expected: str) -> None:
        assert detect_tone(text) == expected


class TestUniversalTone:
    @pytest.mark.parametrize("text,expected", _parametrize_cases("universal"))
    def test_fallback_patterns(self, text: str, expected: str) -> None:
        assert detect_tone(text) == expected


class TestPlaceholderNeutralTone:
    """Placeholders must not influence tone detection."""

    @pytest.mark.parametrize("text", _cases("placeholder_universal"))
    def test_placeholders_map_to_universal(self, text: str) -> None:
        assert detect_tone(text) == "universal"


class TestTonePriorityOrder:
    """Regression lock: humorous must stay above direct in rule ordering."""

    def test_python_rules_order(self) -> None:
        tones = [rule["tone"] for rule in RULES]
        assert tones[:4] == ["humorous", "direct", "strategic", "calm"]
        humorous_idx = tones.index("humorous")
        direct_idx = tones.index("direct")
        assert humorous_idx < direct_idx, "humorous block must remain above direct"

    def test_js_rules_order(self) -> None:
        src = DECISION_FLOW_JS.read_text(encoding="utf-8")
        tones = re.findall(r'tone:\s*"(\w+)"', src)
        assert tones[:4] == ["humorous", "direct", "strategic", "calm"]
        assert tones.index("humorous") < tones.index("direct")

    def test_default_tone_is_universal(self) -> None:
        assert DEFAULT_TONE == "universal"
        assert detect_tone("") == "universal"
        assert detect_tone("   ") == "universal"
