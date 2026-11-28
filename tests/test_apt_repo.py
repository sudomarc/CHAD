"""Integration tests for signed APT repository generation."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEB_BUILDER = ROOT / "scripts" / "build_deb.py"
APT_BUILDER = ROOT / "scripts" / "build_apt_repo.py"


@unittest.skipUnless(
    all(shutil.which(command) for command in ("dpkg-deb", "dpkg-scanpackages", "gpg")),
    "dpkg and GnuPG packaging tools are required",
)
class AptRepositoryTests(unittest.TestCase):
    def test_builds_and_verifies_signed_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gpg_home = root / "test-gnupg"
            gpg_home.mkdir(mode=0o700)
            key_parameters = (
                "Key-Type: RSA\n"
                "Key-Length: 2048\n"
                "Key-Usage: sign\n"
                "Name-Real: CHAD CI Test Key\n"
                "Name-Email: chad-ci@example.invalid\n"
                "Expire-Date: 0\n"
                "%no-protection\n"
                "%commit\n"
            )
            subprocess.run(
                ["gpg", "--batch", "--homedir", str(gpg_home), "--generate-key"],
                input=key_parameters,
                check=True,
                capture_output=True,
                text=True,
            )
            private_key = subprocess.run(
                [
                    "gpg", "--batch", "--homedir", str(gpg_home),
                    "--armor", "--export-secret-keys",
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("BEGIN PGP PRIVATE KEY BLOCK", private_key)

            output = root / "public"
            downloads = output / "downloads"
            package_build = subprocess.run(
                [
                    sys.executable, str(DEB_BUILDER),
                    "--version", "0.4.1",
                    "--output", str(downloads),
                    "--root", str(ROOT),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(package_build.returncode, 0, f"Package build failed:\n{package_build.stdout}\n{package_build.stderr}")
            package = downloads / "chad_0.4.1_all.deb"
            env = dict(os.environ)
            env["CHAD_APT_GPG_PRIVATE_KEY"] = private_key
            subprocess.run(
                [
                    sys.executable, str(APT_BUILDER),
                    "--package", str(package),
                    "--version", "0.4.1",
                    "--output", str(output),
                ],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            repo = output / "apt"
            packages_index = repo / "dists/stable/main/binary-amd64/Packages"
            self.assertIn("Package: chad", packages_index.read_text(encoding="utf-8"))
            self.assertIn("Architecture: all", packages_index.read_text(encoding="utf-8"))
            self.assertTrue((repo / "dists/stable/main/binary-amd64/Packages.gz").is_file())
            self.assertTrue((repo / "dists/stable/Release").is_file())
            release_content = (repo / "dists/stable/Release").read_text(encoding="utf-8")
            release_hashes = release_content.split("SHA256:\\n", 1)[1].splitlines()
            indexed_paths = {
                line.split()[-1] for line in release_hashes if line.strip()
            }
            self.assertEqual(
                indexed_paths,
                {"main/binary-amd64/Packages", "main/binary-amd64/Packages.gz"},
            )
            self.assertTrue((repo / "dists/stable/Release.gpg").is_file())
            self.assertTrue((repo / "dists/stable/InRelease").is_file())
            self.assertIn("BEGIN PGP PUBLIC KEY BLOCK", (repo / "KEY.asc").read_text(encoding="ascii"))


if __name__ == "__main__":
    unittest.main()
