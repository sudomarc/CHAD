#!/usr/bin/env python3
"""Render the CHAD installation site into a GitHub Pages artifact."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def render(version: str, apt_enabled: bool, output: Path, root: Path) -> None:
    source = root / "site" / "index.html"
    if not source.is_file():
        raise FileNotFoundError(f"Site template not found: {source}")

    output.mkdir(parents=True, exist_ok=True)
    html = source.read_text(encoding="utf-8")
    html = html.replace("__CHAD_VERSION__", version)
    html = html.replace("__APT_ENABLED__", "true" if apt_enabled else "false")
    (output / "index.html").write_text(html, encoding="utf-8")

    static_dir = root / "site" / "assets"
    if static_dir.is_dir():
        shutil.copytree(static_dir, output / "assets", dirs_exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--apt-enabled", choices=("true", "false"), required=True)
    parser.add_argument("--output", type=Path, default=Path("public"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    render(args.version, args.apt_enabled == "true", args.output.resolve(), args.root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
