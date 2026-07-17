import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "patch-node-source.py"
SPEC = importlib.util.spec_from_file_location("patch_node_source", MODULE_PATH)
PATCHER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PATCHER)


class PatcherTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "node"
        self.ndk = Path(self.temp.name) / "ndk"
        (self.root / "src").mkdir(parents=True)
        (self.root / "deps/v8/src/trap-handler").mkdir(parents=True)
        (self.ndk / "sources/android/cpufeatures").mkdir(parents=True)

        (self.root / "src/node_version.h").write_text(
            "#define NODE_MAJOR_VERSION 22\n", encoding="utf-8"
        )
        (self.root / "android_configure.py").write_text(
            "import os\n"
            "os.environ['CXX'] = toolchain_path + \"/bin/\" + TOOLCHAIN_PREFIX + android_sdk_version + \"-\" + \"clang++\"\n"
            "configure.configure_node(options, ['--openssl-no-asm --cross-compiling\")\n",
            encoding="utf-8",
        )
        (self.root / "deps/v8/src/trap-handler/trap-handler.h").write_text(
            "// X64 on Linux, Windows, MacOS, FreeBSD.\nold platform logic\n"
            "#if V8_OS_ANDROID && V8_TRAP_HANDLER_SUPPORTED\nandroid logic\n",
            encoding="utf-8",
        )
        block = (
            "  if (use_v8_handler) {\n"
            "    g_is_trap_handler_enabled = RegisterDefaultTrapHandler();\n"
            "    return g_is_trap_handler_enabled;\n"
            "  }\n"
        )
        (self.root / "deps/v8/src/trap-handler/handler-outside.cc").write_text(
            block, encoding="utf-8"
        )
        (self.root / "node.gyp").write_text(
            "# Skip cctest while building shared lib node for Windows\n"
            "        [ 'OS==\"win\" and node_shared==\"true\"', {\n"
            "      'conditions': [\n"
            "        [ 'openssl_default_cipher_list!=\"\"', {\n",
            encoding="utf-8",
        )
        for name in ("cpu-features.c", "cpu-features.h"):
            (self.ndk / "sources/android/cpufeatures" / name).write_text(
                f"/* {name} */\n", encoding="utf-8"
            )

    def tearDown(self):
        self.temp.cleanup()

    def test_patch_is_complete_and_idempotent(self):
        PATCHER.patch_source(self.root, self.ndk)
        first = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        PATCHER.patch_source(self.root, self.ndk)
        second = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(first, second)

        configure = (self.root / "android_configure.py").read_text(encoding="utf-8")
        self.assertIn("CC_host", configure)
        self.assertIn("--with-intl=none --cross-compiling --shared", configure)
        self.assertIn("import shutil", configure)

        gyp = (self.root / "node.gyp").read_text(encoding="utf-8")
        self.assertIn("cpu-features.c", gyp)
        self.assertIn("OS in (\"win\", \"android\")", gyp)

    def test_rejects_other_node_major_versions(self):
        (self.root / "src/node_version.h").write_text(
            "#define NODE_MAJOR_VERSION 23\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(PATCHER.PatchError, "Node.js 22"):
            PATCHER.patch_source(self.root, self.ndk)


if __name__ == "__main__":
    unittest.main()
