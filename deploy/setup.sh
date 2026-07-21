#!/usr/bin/env bash
# Install nginx and wire Crashout Recovery site (Ubuntu 26.04 / 24.04).
set -euo pipefail

APP_ROOT="/root/crashoutrecovery"
SRC_CONF="${APP_ROOT}/deploy/nginx.conf"
AVAILABLE="/etc/nginx/sites-available/crashoutrecovery"
ENABLED="/etc/nginx/sites-enabled/crashoutrecovery"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash ${APP_ROOT}/deploy/setup.sh" >&2
  exit 1
fi

if [[ ! -f "${SRC_CONF}" ]]; then
  echo "Missing ${SRC_CONF}" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "==> Installing nginx"
apt-get update -y
apt-get install -y nginx ufw

echo "==> Enabling UFW ports 80 and 443"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
if ! ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw --force enable
fi
ufw status verbose || true

echo "==> Installing site config"
cp -f "${SRC_CONF}" "${AVAILABLE}"
ln -sfn "${AVAILABLE}" "${ENABLED}"
rm -f /etc/nginx/sites-enabled/default

echo "==> Testing and reloading nginx"
nginx -t
systemctl enable nginx
systemctl reload nginx

echo "Done. Proxy :80 → http://127.0.0.1:8777"
echo "Static: /static → ${APP_ROOT}/static/"
