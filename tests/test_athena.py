import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("athena", Path(__file__).parents[1] / "Scripts/athena.py")
athena = importlib.util.module_from_spec(spec)
spec.loader.exec_module(athena)


class AthenaBuildTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.wrt = self.root / "wrt"
        self.target = self.root / "target"
        self.wrt.mkdir()
        (self.source / "athena-led").mkdir(parents=True)
        (self.source / "luci-app-athena-led").mkdir()
        self.recipe = self.source / "athena-led/Makefile"
        self.original = (
            "PKG_VERSION:=2.5.0\nPKG_SOURCE:=old.tar.gz\n"
            "PKG_SOURCE_URL:=https://example.invalid/release/\nPKG_HASH:=skip\n"
        )
        self.recipe.write_text(self.original)
        (self.source / "luci-app-athena-led/Makefile").write_text("PKG_VERSION:=2.5.0\n")
        (self.source / "athena-led/Cargo.toml").write_text('[package]\nname="athena-led"\nversion="2.5.0"\n')
        (self.source / "athena-led/Cargo.lock").write_text("version = 4\n")

    def test_rejects_mismatched_ui_before_build(self):
        (self.source / "luci-app-athena-led/Makefile").write_text("PKG_VERSION:=2.4.0\n")
        with patch.object(athena.subprocess, "run") as cargo:
            with self.assertRaisesRegex(ValueError, "versions must match"):
                athena.build(self.source, self.wrt, self.target)
            cargo.assert_not_called()
        self.assertEqual(self.recipe.read_text(), self.original)

    def test_requires_existing_lockfile(self):
        (self.source / "athena-led/Cargo.lock").unlink()
        with patch.object(athena.subprocess, "run") as cargo:
            with self.assertRaises(FileNotFoundError):
                athena.build(self.source, self.wrt, self.target)
            cargo.assert_not_called()

    def test_compile_failure_does_not_modify_package(self):
        with patch.object(athena, "output", return_value="a" * 40), patch.object(
            athena.subprocess, "run", side_effect=subprocess.CalledProcessError(17, "cargo")
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                athena.build(self.source, self.wrt, self.target)
        self.assertEqual(self.recipe.read_text(), self.original)
        self.assertFalse((self.wrt / "athena-dist").exists())

    def test_archive_hash_and_metadata_match_built_binary(self):
        binary = self.target / "aarch64-unknown-linux-musl/release/athena-led"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"test compiled payload")
        with patch.object(athena, "output", side_effect=["a" * 40, "rustc test", "cargo-zigbuild test"]), patch.object(
            athena.subprocess, "run"
        ) as cargo:
            athena.build(self.source, self.wrt, self.target)
        self.assertEqual(cargo.call_args.args[0], ["cargo", "zigbuild", "--locked", "--release", "--target", "aarch64-unknown-linux-musl"])
        metadata = json.loads((self.wrt / "athena-build.json").read_text())
        archive = self.wrt / "athena-dist" / metadata["archive"]
        self.assertIn("a" * 40, archive.name)
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), metadata["sha256"])
        recipe = self.recipe.read_text()
        self.assertIn("PKG_SOURCE_URL:=file://$(TOPDIR)/athena-dist", recipe)
        self.assertIn("PKG_HASH:=" + metadata["sha256"], recipe)
        self.assertNotIn("example.invalid", recipe)
        with tarfile.open(archive) as tar:
            self.assertEqual(tar.getnames(), ["athena-led"])
            self.assertEqual(tar.getmember("athena-led").mode, 0o755)
            self.assertEqual(tar.extractfile("athena-led").read(), binary.read_bytes())

    def test_rejects_ambiguous_makefile_fields(self):
        with self.assertRaises(ValueError):
            athena.replace_value("PKG_HASH:=skip\nPKG_HASH:=other\n", "PKG_HASH", "new")

    def test_led_package_is_scoped_to_ax6600_target_group(self):
        config = Path(__file__).parents[1] / "Config"
        option = "CONFIG_PACKAGE_luci-app-athena-led=y"
        self.assertIn(option, (config / "IPQ60XX.txt").read_text(encoding="utf-8"))
        self.assertNotIn(option, (config / "IPQ807X.txt").read_text(encoding="utf-8"))
        self.assertNotIn(option, (config / "GENERAL.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
