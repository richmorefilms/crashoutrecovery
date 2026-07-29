#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="/root/crashoutrecovery"
VENV_PY="$REPO_DIR/venv/bin/python"
LOGDIR="/var/log/crashout"
SMOKE_URL="http://127.0.0.1:8777/api/tiktok/feed"

echo "=== Deploy TikTok integration: $(date) ==="

# 1) Pull latest code
cd "$REPO_DIR"
echo "-- git fetch/reset"
git fetch origin
git reset --hard origin/main

# 2) Ensure .env exists (do not overwrite if present)
if [ ! -f .env ]; then
  echo "-- creating .env from example"
  cp .env.example .env || true
  chmod 600 .env
fi

# 3) Apply migration v10
echo "-- applying migration v10"
$VENV_PY - <<PY
from app import db
print("Applying migrations up to 10")
db.apply_migrations(10)
print("Migrations applied")
PY

# 4) Restart app service and reload nginx
echo "-- restarting crashout service"
systemctl daemon-reload
systemctl restart crashout
sleep 2
systemctl status crashout --no-pager || true

echo "-- testing nginx config and reloading"
nginx -t
systemctl reload nginx

# 5) Run smoke tests
echo "-- running smoke tests"
# run the fast tiktok feed unit test if pytest available
if command -v pytest >/dev/null 2>&1; then
  pytest tests/test_tiktok.py::test_feed_endpoint -q || echo "pytest returned non-zero"
fi

# 6) API smoke call
echo "-- curl smoke call to $SMOKE_URL"
curl -sS "$SMOKE_URL" | head -n 40 || echo "curl failed"

# 7) Ensure log dir exists
mkdir -p "$LOGDIR"
chown root:root "$LOGDIR"
chmod 755 "$LOGDIR"

echo "=== Deploy script finished: $(date) ==="
