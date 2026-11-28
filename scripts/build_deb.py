#!/usr/bin/env python3
"""Build a self-contained, architecture-independent CHAD Debian package."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def project_version(root: Path) -> str:
    with (root / "pyproject.toml").open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def build_package(version: str, output_dir: Path, root: Path) -> Path:
    if not VERSION_RE.fullmatch(version):
        raise ValueError("Version must use MAJOR.MINOR.PATCH (for example 0.1.0).")

    dpkg_deb = shutil.which("dpkg-deb")
    if not dpkg_deb:
        raise RuntimeError("dpkg-deb is required; install the dpkg package tools.")

    source_package = root / "src" / "chad"
    if not (source_package / "cli.py").is_file():
        raise RuntimeError(f"CHAD Python package not found at {source_package}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"chad_{version}_all.deb"

    with tempfile.TemporaryDirectory(prefix="chad-deb-") as temp:
        staging = Path(temp) / "package"
        control_dir = staging / "DEBIAN"
        python_dir = staging / "usr" / "lib" / "chad"
        binary_dir = staging / "usr" / "bin"
        control_dir.mkdir(parents=True)
        python_dir.mkdir(parents=True)
        binary_dir.mkdir(parents=True)

        shutil.copytree(
            source_package,
            python_dir / "chad",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )

        init_file = python_dir / "chad" / "__init__.py"
        init_text = init_file.read_text(encoding="utf-8")
        updated, replacements = re.subn(
            r'(?m)^__version__\s*=\s*["\'][^"\']+["\']\s*$',
            f'__version__ = "{version}"',
            init_text,
            count=1,
        )
        if replacements != 1:
            raise RuntimeError("Could not safely set the package version.")
        init_file.write_text(updated, encoding="utf-8")

        control = (
            "Package: chad\n"
            f"Version: {version}\n"
            "Section: utils\n"
            "Priority: optional\n"
            "Architecture: all\n"
            "Maintainer: CHAD maintainers <chad@localhost>\n"
            "Depends: python3 (>= 3.11)\n"
            "Homepage: https://github.com/sudomarc/CHAD\n"
            "Description: Local-first software engineering agent\n"
            " CHAD provides a Python command-line interface and bounded agent runtime.\n"
        )
        (control_dir / "control").write_text(control, encoding="utf-8")

        wrapper = (
            "#!/usr/bin/python3\n"
            '"""System entry point for the CHAD Debian package."""\n'
            "import sys\n"
            'sys.path.insert(0, "/usr/lib/chad")\n'
            "from chad.cli import main\n"
            "raise SystemExit(main())\n"
        )
        executable = binary_dir / "chad"
        executable.write_text(wrapper, encoding="utf-8")
        executable.chmod(0o755)

        subprocess.run(
            [dpkg_deb, "--build", "--root-owner-group", str(staging), str(output)],
            check=True,
        )

    fields = subprocess.run(
        [dpkg_deb, "--field", str(output), "Package", "Version", "Architecture"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if fields != [f"Package: chad", f"Version: {version}", "Architecture: all"]:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"Unexpected Debian package metadata: {fields!r}")

    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=None, help="MAJOR.MINOR.PATCH; defaults to pyproject.toml")
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    root = args.root.resolve()
    version = args.version or project_version(root)
    try:
        package = build_package(version, args.output.resolve(), root)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"build_deb: {exc}", file=sys.stderr)
        return 1

    print(f"Built {package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
