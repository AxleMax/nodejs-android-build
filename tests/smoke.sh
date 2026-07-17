#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash -n "$ROOT/scripts/build-node-android.sh"
python3 -m py_compile "$ROOT/scripts/patch-node-source.py"
"$ROOT/scripts/build-node-android.sh" --help | grep -q "arm64-v8a"

if grep -RInE --exclude-dir=.git --exclude='smoke.sh' \
  'studio-platform|mineflayer|minecraft|pairing|websocket|outbox|journal|desired state' "$ROOT"; then
  echo "Application-specific content detected" >&2
  exit 1
fi

echo "Smoke checks passed"

