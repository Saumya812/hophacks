#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=/opt/findmypal
REPO_URL=https://github.com/Saumya812/hophacks.git
BRANCH=main

if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" fetch --prune origin "$BRANCH"
  git -C "$APP_DIR" checkout -q "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
fi

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/backend/requirements.txt"

install -d -o findmypal -g findmypal /var/www/findmypal
(cd "$APP_DIR/frontend" && npm ci --include=dev)
(cd "$APP_DIR/frontend" && VITE_API_BASE_URL=/api npm run build)
rsync -a --delete "$APP_DIR/frontend/dist/" /var/www/findmypal/
chown -R findmypal:findmypal "$APP_DIR"

systemctl daemon-reload
systemctl enable findmypal.service
systemctl restart findmypal.service
if nginx -t; then
  systemctl reload nginx
fi

curl --fail --silent --show-error http://127.0.0.1:3077/health >/dev/null
test -f /var/www/findmypal/index.html
echo "FindMyPal deployed at $(git -C "$APP_DIR" rev-parse --short HEAD)"
