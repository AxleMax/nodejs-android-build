# Node.js Android Build

A small, reproducible build environment for cross-compiling Node.js 22 as an
Android `arm64-v8a` shared library. The output is suitable for embedding in an
Android application through JNI or another native bridge.

This repository is intentionally application-agnostic. It contains no product
runtime, application protocol, credentials, or prebuilt proprietary artifacts.

## Status

- Target: Android `arm64-v8a`
- Tested Node.js line: `22.x`
- Default Android API level: `26`
- Default NDK: `28.2.13676358` (r28c)
- Host: Ubuntu 22.04/24.04 or WSL2 Ubuntu
- Output: `libnode.so` plus embeddable Node/V8/libuv headers

The patch set is deliberately narrow and checks the expected Node.js 22 source
layout before changing it. A new Node.js major version should be validated and
supported in a separate change.

## Local build

Install the host dependencies:

```bash
sudo apt-get update
sudo apt-get install -y build-essential curl file git make python3 unzip xz-utils
```

Download and unpack the official Node.js source archive and Android NDK, then
run:

```bash
./scripts/build-node-android.sh \
  /path/to/node-v22.23.1 \
  /path/to/android-ndk-r28c \
  "$PWD/dist" \
  26
```

The result has this layout:

```text
dist/
├── bin/arm64-v8a/libnode.so
├── include/node/...
├── LICENSE.node
├── BUILD-METADATA.txt
└── LIBNODE.SHA256
```

The source tree is patched in place. Use a fresh source tree for each build if
you need a pristine checkout; applying the patch a second time is safe.

## GitHub Actions

Every push or merged pull request to `main` runs **Build Node.js for Android**
with Node.js `22.23.1` and Android API `26`. The workflow can also be run
manually with a selected Node.js 22 version and API level. It verifies the
Node.js source checksum published by nodejs.org, builds the library, validates
the ELF architecture and required headers, and uploads a compressed bundle and
SHA-256 checksum as workflow artifacts. After a successful `main` build, the
same files are published to the rolling `continuous` GitHub Release so they
remain directly available from the Releases page.

No binary is committed to this repository. The `continuous` release is mutable
and always represents the most recent successful `main` build; its attached
checksum must be verified before use.

## Validation

```bash
./tests/smoke.sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

After a full build, inspect the target architecture:

```bash
file dist/bin/arm64-v8a/libnode.so
readelf -h dist/bin/arm64-v8a/libnode.so | grep -E 'Class|Machine'
```

Expected values are ELF 64-bit and AArch64.

## Licensing

The build scripts and patch helper in this repository are MIT licensed. Node.js
and its bundled dependencies retain their own licenses. Redistributing a build
requires preserving the applicable upstream notices; `LICENSE.node` is copied
into each output bundle as a starting point.
