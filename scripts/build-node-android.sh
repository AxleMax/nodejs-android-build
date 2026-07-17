#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: build-node-android.sh <node-v22-source> <android-ndk> <output-directory> [android-api]

Cross-compiles Node.js 22 into an Android arm64-v8a shared library and exports
the headers required by an embedding application. The source tree is patched
in place. The default Android API level is 26.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi
if [[ $# -lt 3 || $# -gt 4 ]]; then
  usage >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(realpath "$1")"
NDK_DIR="$(realpath "$2")"
OUTPUT_DIR="$(realpath -m "$3")"
ANDROID_API="${4:-26}"
TOOLCHAIN="$NDK_DIR/toolchains/llvm/prebuilt/linux-x86_64"

[[ "$ANDROID_API" =~ ^[0-9]+$ ]] || { echo "Android API must be numeric" >&2; exit 2; }
test -f "$SOURCE_DIR/src/node_version.h"
test -x "$TOOLCHAIN/bin/aarch64-linux-android${ANDROID_API}-clang"
command -v python3 >/dev/null
command -v make >/dev/null

python3 "$SCRIPT_DIR/patch-node-source.py" --source "$SOURCE_DIR" --ndk "$NDK_DIR"

cd "$SOURCE_DIR"
./android-configure "$NDK_DIR" "$ANDROID_API" arm64
make -j"$(getconf _NPROCESSORS_ONLN)"

test -f out/Release/libnode.so
rm -rf "$OUTPUT_DIR"
HEADERS="$OUTPUT_DIR/include/node"
mkdir -p "$OUTPUT_DIR/bin/arm64-v8a" "$HEADERS/libplatform" "$HEADERS/cppgc"
cp out/Release/libnode.so "$OUTPUT_DIR/bin/arm64-v8a/libnode.so"
cp common.gypi config.gypi "$HEADERS/"
cp src/*.h "$HEADERS/"
cp deps/v8/include/v8*.h "$HEADERS/"
cp deps/v8/include/libplatform/*.h "$HEADERS/libplatform/"
cp deps/v8/include/cppgc/*.h "$HEADERS/cppgc/"
cp -r deps/uv/include/* "$HEADERS/"
cp deps/zlib/zconf.h deps/zlib/zlib.h "$HEADERS/"
cp LICENSE "$OUTPUT_DIR/LICENSE.node"

VERSION="$(sed -nE 's/^#define NODE_(MAJOR|MINOR|PATCH)_VERSION ([0-9]+)$/\2/p' src/node_version.h | paste -sd . -)"
cat >"$OUTPUT_DIR/BUILD-METADATA.txt" <<EOF
node_version=$VERSION
android_abi=arm64-v8a
android_api=$ANDROID_API
ndk=$(basename "$NDK_DIR")
EOF

file "$OUTPUT_DIR/bin/arm64-v8a/libnode.so"
grep -E 'NODE_(MAJOR|MINOR|PATCH)_VERSION' "$HEADERS/node_version.h" | head -3
"$SCRIPT_DIR/verify-output.sh" "$OUTPUT_DIR"
