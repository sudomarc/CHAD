#!/usr/bin/env python3
"""Build and sign a small Debian APT repository for CHAD."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def run(command: list[str]) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout


def build_repository(package: Path, output: Path, version: str) -> None:
    private_key = os.environ.get("CHAD_APT_GPG_PRIVATE_KEY", "").strip()
    if not package.is_file():
        raise FileNotFoundError(f"Debian package not found: {package}")
    metadata = subprocess.run(
        ["dpkg-deb", "--field", str(package), "Package", "Version", "Architecture"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if metadata != ["chad", version, "all"]:
        raise RuntimeError(f"Package metadata does not match requested release: {metadata!r}")
    if not private_key:
        raise RuntimeError("CHAD_APT_GPG_PRIVATE_KEY is not configured.")

    if not shutil.which("dpkg-scanpackages"):
        raise RuntimeError("dpkg-scanpackages is missing; install dpkg-dev.")
    if not shutil.which("gpg"):
        raise RuntimeError("gpg is missing; install gnupg.")

    repo = output / "apt"
    pool = repo / "pool" / "main" / "c" / "chad"
    distribution = repo / "dists" / "stable"
    index_dir = distribution / "main" / "binary-amd64"
    pool.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(package, pool / package.name)

    # dpkg-scanpackages must run from the repository root so filenames in
    # Packages are relative to the repository URL.
    scanned = subprocess.run(
        ["dpkg-scanpackages", "--arch", "amd64", "pool/main/c/chad"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    packages_path = index_dir / "Packages"
    packages_path.write_text(scanned.stdout, encoding="utf-8")
    with packages_path.open("rb") as source, (index_dir / "Packages.gz").open("wb") as target:
        import gzip
        with gzip.GzipFile(filename="", mode="wb", fileobj=target, compresslevel=9, mtime=0) as zipped:
            shutil.copyfileobj(source, zipped)

    files = [packages_path, index_dir / "Packages.gz"]
    hashes = []
    for path in files:
        relative = path.relative_to(repo).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes.append(f" {digest} {path.stat().st_size} {relative}")

    release = (
        "Origin: CHAD\n"
        "Label: CHAD\n"
        "Suite: stable\n"
        "Codename: stable\n"
        "Architectures: amd64\n"
        "Components: main\n"
        "Description: CHAD signed APT repository\n"
        f"Date: {datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S UTC')}\n"
        "Acquire-By-Hash: no\n"
        "SHA256:\n"
        + "\n".join(hashes)
        + "\n"
    )
    release_path = distribution / "Release"
    release_path.write_text(release, encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="chad-apt-gpg-") as home:
        os.chmod(home, 0o700)
        home_path = Path(home)
        imported = subprocess.run(
            ["gpg", "--batch", "--homedir", home, "--import"],
            input=private_key,
            check=True,
            capture_output=True,
            text=True,
        )
        secret_keys = run([
            "gpg", "--batch", "--homedir", home, "--with-colons",
            "--list-secret-keys",
        ])
        fingerprints = [
            line.split(":")[9]
            for line in secret_keys.splitlines()
            if line.startswith("fpr:")
        ]
        if not fingerprints:
            raise RuntimeError("No private-key fingerprint was found after import.")
        fingerprint = fingerprints[0]

        passphrase = os.environ.get("CHAD_APT_GPG_PASSPHRASE", "")
        passphrase_args: list[str] = []
        passphrase_file = home_path / "passphrase"
        if passphrase:
            passphrase_file.write_text(passphrase, encoding="utf-8")
            passphrase_file.chmod(0o600)
            passphrase_args = [
                "--pinentry-mode", "loopback",
                "--passphrase-file", str(passphrase_file),
            ]

        run([
            "gpg", "--batch", "--yes", "--homedir", home,
            *passphrase_args, "--local-user", fingerprint,
            "--digest-algo", "SHA256", "--detach-sign",
            "--output", str(distribution / "Release.gpg"),
            str(release_path),
        ])
        run([
            "gpg", "--batch", "--yes", "--homedir", home,
            *passphrase_args, "--local-user", fingerprint,
            "--digest-algo", "SHA256", "--clearsign",
            "--output", str(distribution / "InRelease"),
            str(release_path),
        ])

        public_key = run([
            "gpg", "--batch", "--homedir", home,
            "--armor", "--export", fingerprint,
        ])
        key_path = repo / "KEY.asc"
        key_path.write_text(public_key, encoding="ascii")

        # Verify both signatures before allowing the directory to be published.
        run(["gpg", "--batch", "--homedir", home, "--verify",
             str(distribution / "InRelease")])
        run(["gpg", "--batch", "--homedir", home, "--verify",
             str(distribution / "Release.gpg"), str(release_path)])



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    try:
        build_repository(args.package.resolve(), args.output.resolve(), args.version)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"build_apt_repo: {exc}", file=sys.stderr)
        return 1
    print("Signed APT repository built and both signatures verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
