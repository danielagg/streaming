from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from .config import TwitchConfig


class TwitchChatService:
    """Optional TwitchIO lifecycle boundary; disabled unless explicitly configured.

    OAuth/device-code UI remains a frontend concern. A future authenticated TwitchIO
    adapter can feed normalized messages through ``publish_message`` without changing
    the sidecar protocol.
    """

    def __init__(
        self,
        config: TwitchConfig,
        emit: Callable[[str, dict[str, Any], str | None], Awaitable[None]],
    ) -> None:
        self.config = config
        self.emit = emit
        self.running = False

    async def start(self) -> None:
        if not self.config.enabled:
            await self.emit(
                "service.status",
                {"service": "twitch", "state": "offline", "detail": "Disabled"},
                None,
            )
            return
        try:
            import twitchio  # noqa: F401
        except ImportError:
            await self.emit(
                "service.status",
                {
                    "service": "twitch",
                    "state": "error",
                    "detail": "Install Command Deck with the twitch extra.",
                },
                None,
            )
            return
        if not self.config.client_id or not self.config.broadcaster_id:
            await self.emit(
                "service.status",
                {
                    "service": "twitch",
                    "state": "error",
                    "detail": "Twitch client and broadcaster ids are required.",
                },
                None,
            )
            return
        self.running = True
        await self.emit(
            "service.status",
            {
                "service": "twitch",
                "state": "connecting",
                "detail": "TwitchIO is ready for authentication.",
            },
            None,
        )

    async def publish_message(self, message: dict[str, Any]) -> None:
        await self.emit("chat.message", message, None)

    async def close(self) -> None:
        self.running = False
