from __future__ import annotations

import argparse

from chad.__main__ import main as start


def app() -> None:
    parser = argparse.ArgumentParser(
        prog="chad",
        description="CHAD — the conversational application for LapisLLM.",
    )
    parser.add_argument("command", nargs="?", choices=("start",), help="start CHAD")
    args = parser.parse_args()
    if args.command in (None, "start"):
        start()


if __name__ == "__main__":
    app()
