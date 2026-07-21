#!/usr/bin/env bash
# Let's Encrypt TLS for crashoutrecovery.app (+ www); auto-configures HTTPS in nginx.
set -euo pipefail

APP_ROOT="/root/crashoutrecovery"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: CERTBOT_EMAIL=you@example.com sudo -E bash ${APP_ROOT}/deploy/ssl.sh" >&2
  exit 1
fi

if [[ -z "${CERTBOT_EMAIL:-}" ]]; then
  echo "Set CERTBOT_EMAIL, e.g.:" >&2
  echo "  CERTBOT_EMAIL=you@example.com sudo -E bash ${APP_ROOT}/deploy/ssl.sh" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "==> Installing certbot + python3-certbot-nginx"
apt-get update -y
apt-get install -y certbot python3-certbot-nginx

echo "==> Ensuring nginx is running"
systemctl enable --now nginx
nginx -t
systemctl reload nginx

echo "==> Issuing certificates"
certbot --nginx \
  --non-interactive \
  --agree-tos \
  --email "${CERTBOT_EMAIL}" \
  --redirect \
  -d crashoutrecovery.app \
  -d www.crashoutrecovery.app

echo "==> Renewal timer"
systemctl enable --now certbot.timer || true
certbot renew --dry-run || true

echo "HTTPS ready: https://crashoutrecovery.app"
