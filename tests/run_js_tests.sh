#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "Running JS tone regression tests..."
node tests/tone/test_decision_flow_js.js
echo "JS tests passed."
