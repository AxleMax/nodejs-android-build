#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash -n "$ROOT/scripts/build-node-android.sh"
bash -n "$ROOT/scripts/publish-continuous-release.sh"
bash -n "$ROOT/scripts/verify-output.sh"
python3 -m py_compile "$ROOT/scripts/patch-node-source.py"
"$ROOT/scripts/build-node-android.sh" --help | grep -q "arm64-v8a"
"$ROOT/scripts/publish-continuous-release.sh" --help | grep -q "release-tag"
"$ROOT/scripts/verify-output.sh" --help | grep -q "build-output-directory"

if grep -RInEi --exclude='smoke.sh' \
  'studio-platform|mineflayer|minecraft|pairing|websocket|outbox|journal|desired state' \
  "$ROOT/README.md" "$ROOT/.github" "$ROOT/scripts" "$ROOT/tests"; then
  echo "Application-specific content detected" >&2
  exit 1
fi

echo "Smoke checks passed"
