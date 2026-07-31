from __future__ import annotations

import argparse
import os
from pathlib import Path

from aiohttp import web

from .config import load_config
from .service import CommandDeckService, create_app


def main() -> None:
    default_config_path = Path(__file__).resolve().parents[2] / "config.json"
    parser = argparse.ArgumentParser(description="Command Deck Python sidecar")
    parser.add_argument("--config", type=Path, default=default_config_path)
    parser.add_argument(
        "--host", default=os.environ.get("COMMAND_DECK_HOST", "127.0.0.1")
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("COMMAND_DECK_PORT", "8765"))
    )
    parser.add_argument("--token", help="Optional local WebSocket bearer token")
    parser.add_argument("--mock-remix", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    token = args.token or os.environ.get("COMMAND_DECK_TOKEN") or None
    service = CommandDeckService(config, mock_remix=args.mock_remix, token=token)
    web.run_app(
        create_app(service),
        host=args.host,
        port=args.port,
        print=lambda message: print(message, flush=True),
    )


if __name__ == "__main__":
    main()
