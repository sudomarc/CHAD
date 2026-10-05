from __future__ import annotations

from chad.app import ChadApp
from chad.core.config import AppConfig
from chad.interfaces.cli import run_cli
from chad.llm.http import HttpLapisClient


def main(mode: str = "cli") -> None:
    config = AppConfig.from_env()
    client = HttpLapisClient(config.lapis.base_url, config.lapis.model)
    try:
        app_instance = ChadApp.create(config, client)
        if mode == "web":
            from chad.interfaces.web import run_web
            run_web(app_instance)
        else:
            run_cli(app_instance)
    finally:
        client.close()


if __name__ == "__main__":
    main()
