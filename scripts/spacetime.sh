#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI="$ROOT/.spacetime/bin/current/spacetimedb-cli"
if [[ ! -x "$CLI" ]]; then
  echo 'Install the local CLI first: see docs/spacetimedb.md' >&2
  exit 1
fi
case "${1:-start}" in
  start)
    exec "$CLI" --root-dir "$ROOT/.spacetime" start --listen-addr 127.0.0.1:3000 --data-dir "$ROOT/.spacetime/server" --non-interactive
    ;;
  publish)
    exec "$CLI" --root-dir "$ROOT/.spacetime" publish "${2:-findmypal}" -p "$ROOT/spacetimedb/spacetimedb" -s http://127.0.0.1:3000 --yes=skip-login --delete-data=never
    ;;
  generate)
    exec "$CLI" --root-dir "$ROOT/.spacetime" generate --lang typescript --module-path "$ROOT/spacetimedb/spacetimedb" --out-dir "$ROOT/frontend/src/spacetime" --yes
    ;;
  *) echo 'Usage: bash scripts/spacetime.sh start|publish [database]|generate' >&2; exit 2 ;;
esac
