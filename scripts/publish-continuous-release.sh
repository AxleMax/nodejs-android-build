#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: publish-continuous-release.sh <archive> <archive-sha256> [release-tag]"
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi
if [[ $# -lt 2 || $# -gt 3 ]]; then
  usage >&2
  exit 2
fi

: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${GITHUB_SHA:?GITHUB_SHA is required}"
command -v gh >/dev/null

ARCHIVE="$(realpath "$1")"
CHECKSUM="$(realpath "$2")"
TAG="${3:-continuous}"
NODE_VERSION="${NODE_VERSION:-22.23.1}"
ANDROID_API="${ANDROID_API:-26}"
NDK_VERSION="${NDK_VERSION:-28.2.13676358}"
RUN_URL="${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID:-unknown}"

test -s "$ARCHIVE"
test -s "$CHECKSUM"
(cd "$(dirname "$ARCHIVE")" && sha256sum -c "$(basename "$CHECKSUM")")

TITLE="Continuous Node.js ${NODE_VERSION} Android arm64-v8a build"
NOTES="Automated build from the main branch.

- Node.js: ${NODE_VERSION}
- Android ABI: arm64-v8a
- Android API: ${ANDROID_API}
- Android NDK: ${NDK_VERSION}
- Source commit: ${GITHUB_SHA}
- Workflow run: ${RUN_URL}

The release is updated after each successful main build. Verify the archive
with the attached SHA-256 file before use."

if gh release view "$TAG" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
  gh api --method PATCH \
    "repos/${GITHUB_REPOSITORY}/git/refs/tags/${TAG}" \
    -f sha="$GITHUB_SHA" \
    -F force=true >/dev/null
  gh release upload "$TAG" "$ARCHIVE" "$CHECKSUM" \
    --repo "$GITHUB_REPOSITORY" --clobber
  gh release edit "$TAG" --repo "$GITHUB_REPOSITORY" \
    --title "$TITLE" --notes "$NOTES"
else
  gh release create "$TAG" "$ARCHIVE" "$CHECKSUM" \
    --repo "$GITHUB_REPOSITORY" \
    --target "$GITHUB_SHA" \
    --title "$TITLE" \
    --notes "$NOTES"
fi
