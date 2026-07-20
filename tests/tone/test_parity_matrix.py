"""Cross-language Python vs JS tone parity matrix."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.conftest import detect_tone
from tests.tone.tone_fixtures import all_parity_inputs

TONE_DIR = Path(__file__).resolve().parent
JS_BATCH = TONE_DIR / "js_tone_batch.mjs"


def _run_js_tones() -> dict[str, str]:
    result = subprocess.run(
        ["node", str(JS_BATCH)],
        capture_output=True,
        text=True,
        check=True,
        cwd=TONE_DIR.parent.parent,
    )
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def js_tones() -> dict[str, str]:
    try:
        return _run_js_tones()
    except FileNotFoundError as exc:
        pytest.skip(f"Node.js required for parity tests: {exc}")
    except subprocess.CalledProcessError as exc:
        pytest.fail(f"JS tone batch failed: {exc.stderr}")


class TestParityMatrix:
    def test_python_js_parity_for_all_inputs(self, js_tones: dict[str, str]) -> None:
        mismatches: list[str] = []
        matrix_rows: list[str] = []

        for text in all_parity_inputs():
            py_tone = detect_tone(text)
            js_tone = js_tones.get(text)
            status = "OK" if py_tone == js_tone else "MISMATCH"
            matrix_rows.append(f"{status:10} | py={py_tone:10} | js={js_tone or 'MISSING':10} | {text!r}")
            if py_tone != js_tone:
                mismatches.append(
                    f'Tone mismatch: Python={py_tone}, JS={js_tone} for input: "{text}"'
                )

        if mismatches:
            header = "Tone Parity Matrix (failures)\n" + "-" * 80 + "\n"
            body = "\n".join(matrix_rows)
            pytest.fail(header + body + "\n\n" + "\n".join(mismatches))
