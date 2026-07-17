#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: verify-output.sh <build-output-directory>"
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi
if [[ $# -ne 1 ]]; then
  usage >&2
  exit 2
fi

OUTPUT_DIR="$(realpath "$1")"
LIBNODE="$OUTPUT_DIR/bin/arm64-v8a/libnode.so"
HEADERS="$OUTPUT_DIR/include/node"

test -s "$LIBNODE"
for header in node.h node_api.h node_version.h v8.h uv.h; do
  test -s "$HEADERS/$header"
done
test -s "$OUTPUT_DIR/LICENSE.node"
test -s "$OUTPUT_DIR/BUILD-METADATA.txt"

FILE_DESCRIPTION="$(file -b "$LIBNODE")"
grep -q "ELF 64-bit" <<<"$FILE_DESCRIPTION"
grep -Eq "ARM aarch64|AArch64" <<<"$FILE_DESCRIPTION"

ELF_HEADER="$(readelf -h "$LIBNODE")"
grep -Eq "Class:[[:space:]]+ELF64" <<<"$ELF_HEADER"
grep -Eq "Machine:[[:space:]]+AArch64" <<<"$ELF_HEADER"
grep -q '^#define NODE_MAJOR_VERSION 22$' "$HEADERS/node_version.h"
grep -q '^android_abi=arm64-v8a$' "$OUTPUT_DIR/BUILD-METADATA.txt"

(cd "$OUTPUT_DIR" && sha256sum bin/arm64-v8a/libnode.so > LIBNODE.SHA256)
echo "Verified: $FILE_DESCRIPTION"
cat "$OUTPUT_DIR/LIBNODE.SHA256"
