"""Tests for rendering the installation website."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "render_site.py"


class SiteRenderTests(unittest.TestCase):
    def test_renders_version_and_only_advertises_available_installers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "public"
            downloads = output / "downloads"
            downloads.mkdir(parents=True)
            (downloads / "chad_1.2.3_all.deb").write_bytes(b"test package")
            subprocess.run(
                [
                    sys.executable, str(RENDERER),
                    "--version", "1.2.3",
                    "--apt-enabled", "true",
                    "--output", str(output),
                    "--root", str(ROOT),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertTrue((output / ".nojekyll").is_file())
            self.assertIn('const CHAD_VERSION = "1.2.3";', html)
            self.assertIn("const aptEnabled = true;", html)
            self.assertIn("const packageAvailable = true;", html)
            self.assertIn("chad_1.2.3_all.deb", html)
            self.assertNotIn("__CHAD_VERSION__", html)
            self.assertNotIn("__APT_ENABLED__", html)

            # Signed APT is preferred on amd64 only when a candidate exists;
            # the direct .deb remains visible as a fallback.
            self.assertLess(html.index('id="apt-card"'), html.index('id="deb-card"'))
            self.assertIn("dpkg --print-architecture", html)
            self.assertIn("apt-cache policy chad", html)
            self.assertIn("Candidate", html)
            self.assertIn("Architecture: all", html)
            self.assertIn("Unable to locate package chad", html)
            self.assertIn("sudo apt install chad", html)
            self.assertIn("sudo apt update && sudo apt upgrade chad", html)
            self.assertIn("aptEnabled = true;", html)
            self.assertNotIn("TUI optionnel", html)

    def test_renders_without_apt_or_download_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "public"
            subprocess.run(
                [
                    sys.executable, str(RENDERER),
                    "--version", "0.1.0",
                    "--apt-enabled", "false",
                    "--output", str(output),
                    "--root", str(ROOT),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertTrue((output / ".nojekyll").is_file())
            self.assertIn("const aptEnabled = false;", html)
            self.assertIn("const packageAvailable = false;", html)
            self.assertIn('id="deb-card"', html)


if __name__ == "__main__":
    unittest.main()
