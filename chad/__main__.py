from __future__ import annotations

from chad.app import ChadApp
from chad.core.config import AppConfig
from chad.interfaces.cli import run_cli
from chad.llm.http import HttpLapisClient


def main() -> None:
    config = AppConfig.from_env()
    client = HttpLapisClient(config.lapis.base_url, config.lapis.model)
    try:
        run_cli(ChadApp.create(config, client))
    finally:
        client.close()


if __name__ == "__main__":
    main()
