"""Tests for building the Debian package."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_deb.py"


@unittest.skipUnless(shutil.which("dpkg-deb"), "dpkg-deb is required for package tests")
class DebianPackageTests(unittest.TestCase):
    def test_builds_installable_architecture_independent_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "dist"
            result = subprocess.run(
                [
                    sys.executable,
                    str(BUILDER),
                    "--version",
                    "0.9.7",
                    "--output",
                    str(output),
                    "--root",
                    str(ROOT),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, f"Package build failed:\n{result.stdout}\n{result.stderr}")
            package = output / "chad_0.9.7_all.deb"
            self.assertTrue(package.is_file())

            metadata = subprocess.run(
                ["dpkg-deb", "--field", str(package), "Package", "Version", "Architecture", "Depends"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            self.assertEqual(metadata, ["Package: chad", "Version: 0.9.7", "Architecture: all", "Depends: python3 (>= 3.11)"])

            extracted = Path(temp) / "extracted"
            subprocess.run(["dpkg-deb", "--extract", str(package), str(extracted)], check=True)
            env = dict(__import__("os").environ)
            env["PYTHONPATH"] = str(extracted / "usr" / "lib" / "chad")
            check = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    ("from chad import __version__; assert __version__ == '0.9.7'; "
                     "from chad.cli import build_parser; assert build_parser().prog == 'chad'"),
                ],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(check.returncode, 0)

            wrapper = extracted / "usr" / "bin" / "chad"
            self.assertTrue(wrapper.is_file())
            self.assertTrue(wrapper.stat().st_mode & 0o111)

    def test_rejects_non_semver_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(BUILDER),
                    "--version",
                    "dev.test-0.1",
                    "--output",
                    temp,
                    "--root",
                    str(ROOT),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("MAJOR.MINOR.PATCH", result.stderr)


if __name__ == "__main__":
    unittest.main()
