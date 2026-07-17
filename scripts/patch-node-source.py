#!/usr/bin/env python3
"""Apply the minimal source changes needed for a Node.js 22 Android build."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


class PatchError(RuntimeError):
    pass


def replace_once(path: Path, old: str, new: str, already_present: str) -> None:
    text = path.read_text(encoding="utf-8")
    if already_present in text:
        return
    if old not in text:
        raise PatchError(f"Expected source marker not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_configure(root: Path) -> None:
    path = root / "android_configure.py"
    cxx = (
        "os.environ['CXX'] = toolchain_path + \"/bin/\" + TOOLCHAIN_PREFIX + "
        "android_sdk_version + \"-\" + \"clang++\""
    )
    host_tools = (
        cxx
        + "\nos.environ['CC_host'] = shutil.which('gcc') or 'gcc'"
        + "\nos.environ['CXX_host'] = shutil.which('g++') or 'g++'"
    )
    text = path.read_text(encoding="utf-8")
    if "import shutil" not in text:
        if "import os" not in text:
            raise PatchError(f"Expected import marker not found in {path}")
        text = text.replace("import os", "import os\nimport shutil", 1)
    if "os.environ['CC_host']" not in text:
        if cxx not in text:
            raise PatchError(f"Expected compiler marker not found in {path}")
        text = text.replace(cxx, host_tools, 1)
    shared_old = "--openssl-no-asm --cross-compiling\")"
    shared_new = "--openssl-no-asm --with-intl=none --cross-compiling --shared\")"
    if "--with-intl=none --cross-compiling --shared" not in text:
        if shared_old not in text:
            raise PatchError(f"Expected configure arguments not found in {path}")
        text = text.replace(shared_old, shared_new, 1)
    path.write_text(text, encoding="utf-8")


def patch_trap_handler(root: Path) -> None:
    header = root / "deps/v8/src/trap-handler/trap-handler.h"
    text = header.read_text(encoding="utf-8")
    marker = "// nodejs-android-build: Android trap handling is disabled"
    if marker not in text:
        start_marker = "// X64 on Linux, Windows, MacOS, FreeBSD."
        end_marker = "\n#if V8_OS_ANDROID && V8_TRAP_HANDLER_SUPPORTED"
        if start_marker not in text or end_marker not in text:
            raise PatchError(f"Expected trap-handler markers not found in {header}")
        start = text.index(start_marker)
        end = text.index(end_marker, start)
        replacement = (
            f"{marker} because it has not had the required V8 security review.\n"
            "// Keep host snapshot and Android target sources consistent.\n"
            "#define V8_TRAP_HANDLER_SUPPORTED false\n"
        )
        header.write_text(text[:start] + replacement + text[end:], encoding="utf-8")

    outside = root / "deps/v8/src/trap-handler/handler-outside.cc"
    block = (
        "  if (use_v8_handler) {\n"
        "    g_is_trap_handler_enabled = RegisterDefaultTrapHandler();\n"
        "    return g_is_trap_handler_enabled;\n"
        "  }\n"
    )
    guarded = "#if V8_TRAP_HANDLER_SUPPORTED\n" + block + "#endif\n"
    replace_once(outside, block, guarded, guarded)


def patch_gyp(root: Path) -> None:
    path = root / "node.gyp"
    text = path.read_text(encoding="utf-8")
    old_tests = (
        "# Skip cctest while building shared lib node for Windows\n"
        "        [ 'OS==\"win\" and node_shared==\"true\"', {"
    )
    new_tests = (
        "# Android shared-library builds do not ship test executables.\n"
        "        [ 'OS in (\"win\", \"android\") and node_shared==\"true\"', {"
    )
    if "OS in (\"win\", \"android\")" not in text:
        if old_tests not in text:
            raise PatchError(f"Expected test target condition not found in {path}")
        text = text.replace(old_tests, new_tests, 1)

    condition = (
        "        [ 'OS==\"android\"', {\n"
        "          'sources': [ 'deps/android/cpu-features.c' ],\n"
        "          'include_dirs': [ 'deps/android' ],\n"
        "        }],\n"
    )
    anchor = "      'conditions': [\n        [ 'openssl_default_cipher_list!=\"\"', {"
    if "'deps/android/cpu-features.c'" not in text:
        if anchor not in text:
            raise PatchError(f"Expected conditions anchor not found in {path}")
        text = text.replace(
            anchor,
            "      'conditions': [\n" + condition + "        [ 'openssl_default_cipher_list!=\"\"', {",
            1,
        )
    path.write_text(text, encoding="utf-8")


def patch_source(root: Path, ndk: Path) -> None:
    version = (root / "src/node_version.h").read_text(encoding="utf-8")
    if "#define NODE_MAJOR_VERSION 22" not in version:
        raise PatchError("This patch set supports Node.js 22.x source only")

    cpu_features = ndk / "sources/android/cpufeatures"
    for filename in ("cpu-features.c", "cpu-features.h"):
        if not (cpu_features / filename).is_file():
            raise PatchError(f"Missing NDK source: {cpu_features / filename}")

    patch_configure(root)
    patch_trap_handler(root)
    patch_gyp(root)

    android_deps = root / "deps/android"
    android_deps.mkdir(exist_ok=True)
    for filename in ("cpu-features.c", "cpu-features.h"):
        shutil.copy2(cpu_features / filename, android_deps / filename)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--ndk", required=True, type=Path)
    args = parser.parse_args()
    patch_source(args.source.resolve(), args.ndk.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
