from __future__ import annotations

from chad.app import ChadApp
from chad.core.config import AppConfig
from chad.interfaces.cli import run_cli
from chad.llm.lapis import LocalLapisClient


def main() -> None:
    config = AppConfig.from_env()
    client = LocalLapisClient(config.lapis.checkpoint, config.lapis.device)
    run_cli(ChadApp.create(config, client))


if __name__ == "__main__":
    main()
