from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Any

from aiohttp import WSMsgType, web

from .config import AppConfig
from .controller import ActionController
from .remix import MockRemixClient, RemixClient
from .remix_window import select_preview_mode
from .startup import launch_remix, read_float32
from .twitch import TwitchChatService
from .window_focus import focus_process_window

PROTOCOL_VERSION = 1


def _target_display_bounds() -> tuple[int, int, int, int] | None:
    names = (
        "COMMAND_DECK_DISPLAY_X",
        "COMMAND_DECK_DISPLAY_Y",
        "COMMAND_DECK_DISPLAY_WIDTH",
        "COMMAND_DECK_DISPLAY_HEIGHT",
    )
    values = [os.environ.get(name) for name in names]
    if any(value is None for value in values):
        return None
    try:
        x, y, width, height = (int(value) for value in values if value is not None)
    except ValueError:
        return None
    return (x, y, width, height) if width > 0 and height > 0 else None


class CommandDeckService:
    def __init__(
        self, config: AppConfig, *, mock_remix: bool = False, token: str | None = None
    ) -> None:
        self.config = config
        self.token = token
        self.mock_remix = mock_remix
        self.clients: set[web.WebSocketResponse] = set()
        self.shutdown_event = asyncio.Event()
        self.remix = (
            MockRemixClient([action.state_name for action in config.actions])
            if mock_remix
            else RemixClient(config.remix_websocket_url)
        )
        self.controller = ActionController(config.actions, self.remix, self.emit)
        self.twitch = TwitchChatService(config.twitch, self.emit)
        self.tasks: set[asyncio.Task[Any]] = set()
        self.remix_process_id: int | None = None
        self.target_display_bounds = _target_display_bounds()
        electron_process_id = os.environ.get("COMMAND_DECK_ELECTRON_PID")
        self.electron_process_id = (
            int(electron_process_id) if electron_process_id else None
        )

    async def emit(
        self, event_type: str, payload: dict[str, Any], request_id: str | None = None
    ) -> None:
        message: dict[str, Any] = {
            "version": PROTOCOL_VERSION,
            "type": event_type,
            "payload": payload,
        }
        if request_id is not None:
            message["requestId"] = request_id
        dead = []
        for socket in self.clients:
            try:
                await socket.send_json(message)
            except Exception:  # noqa: BLE001 - stale clients are removed
                dead.append(socket)
        self.clients.difference_update(dead)

    async def health(self, _request: web.Request) -> web.Response:
        return web.json_response(
            {
                "name": "Command Deck",
                "status": "ok",
                "protocolVersion": PROTOCOL_VERSION,
            }
        )

    async def websocket(self, request: web.Request) -> web.WebSocketResponse:
        if (
            self.token
            and request.headers.get("Authorization") != f"Bearer {self.token}"
            and request.query.get("token") != self.token
        ):
            raise web.HTTPUnauthorized()
        socket = web.WebSocketResponse(heartbeat=20)
        await socket.prepare(request)
        self.clients.add(socket)
        await socket.send_json(
            {
                "version": 1,
                "type": "backend.ready",
                "payload": {
                    "name": "Command Deck",
                    "protocolVersion": 1,
                    "actions": [
                        {"id": a.id, "name": a.name, "durationMs": a.duration_ms}
                        for a in self.config.actions
                    ],
                },
            }
        )
        try:
            async for message in socket:
                if message.type == WSMsgType.TEXT:
                    command: Any = None
                    try:
                        command = message.json()
                        await self.handle_command(command)
                    except Exception as error:  # noqa: BLE001 - protocol boundary
                        request_id = (
                            command.get("id") if isinstance(command, dict) else None
                        )
                        await socket.send_json(
                            self.event(
                                "command.result",
                                {"ok": False, "message": str(error)},
                                request_id,
                            )
                        )
        finally:
            self.clients.discard(socket)
        return socket

    @staticmethod
    def event(
        event_type: str, payload: dict[str, Any], request_id: str | None = None
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"version": 1, "type": event_type, "payload": payload}
        if request_id:
            result["requestId"] = request_id
        return result

    async def handle_command(self, command: Any) -> None:
        if (
            not isinstance(command, dict)
            or command.get("version") != 1
            or not isinstance(command.get("id"), str)
        ):
            raise ValueError("Invalid protocol command.")
        command_type, request_id = command.get("type"), command["id"]
        payload = command.get("payload", {})
        if command_type == "backend.ping":
            await self.emit("command.result", {"ok": True}, request_id)
        elif command_type == "action.trigger":
            action_id = payload.get("actionId")
            if not isinstance(action_id, str):
                raise ValueError("action.trigger requires payload.actionId.")
            task = asyncio.create_task(self._run_action(action_id, request_id))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
            await self.emit(
                "command.result", {"ok": True, "accepted": True}, request_id
            )
        elif command_type == "service.reconnect":
            service = payload.get("service", "remix")
            if service == "remix":
                try:
                    states = await self.remix.list_states()
                    await self.emit(
                        "service.status",
                        {
                            "service": "remix",
                            "state": "online",
                            "detail": f"{len(states)} states available",
                        },
                        request_id,
                    )
                    await self.emit("command.result", {"ok": True}, request_id)
                except Exception as error:  # noqa: BLE001 - report service failure
                    await self.emit(
                        "service.status",
                        {
                            "service": "remix",
                            "state": "offline",
                            "detail": str(error),
                        },
                        request_id,
                    )
                    await self.emit(
                        "command.result",
                        {"ok": False, "message": str(error)},
                        request_id,
                    )
            else:
                await self.twitch.start()
                await self.emit("command.result", {"ok": True}, request_id)
        elif command_type == "backend.shutdown":
            await self.emit("command.result", {"ok": True}, request_id)
            self.shutdown_event.set()
        else:
            raise ValueError(f"Unknown command type: {command_type}")

    async def _run_action(self, action_id: str, request_id: str) -> None:
        try:
            await self.controller.trigger(action_id, request_id)
        except Exception as error:  # noqa: BLE001 - every action needs a terminal event
            await self.emit(
                "berry.action.error",
                {"actionId": action_id, "message": str(error)},
                request_id,
            )

    async def start(self) -> None:
        if not self.mock_remix:
            try:
                process = launch_remix(self.config)
                if process:
                    self.remix_process_id = process.pid
                    await self.emit(
                        "service.status",
                        {
                            "service": "remix",
                            "state": "connecting",
                            "detail": f"Launching process {process.pid}",
                        },
                        None,
                    )
            except Exception as error:  # noqa: BLE001 - startup remains offline-friendly
                await self.emit(
                    "service.status",
                    {"service": "remix", "state": "offline", "detail": str(error)},
                    None,
                )
        remix_probe = asyncio.create_task(self._probe_remix())
        self.tasks.add(remix_probe)
        remix_probe.add_done_callback(self.tasks.discard)
        await self.twitch.start()

    async def _probe_remix(self) -> None:
        attempts = 1 if self.mock_remix else 30
        last_error: Exception | None = None
        for _attempt in range(attempts):
            try:
                states = await self.remix.list_states()
                preview_changed = await self._ensure_preview_mode()
                if preview_changed:
                    # Preview mode restarts Remix's command handling. Prove a
                    # fresh request/response round trip before enabling actions.
                    states = await self.remix.list_states()
                await self.emit(
                    "service.status",
                    {
                        "service": "remix",
                        "state": "online",
                        "detail": f"{len(states)} states available",
                    },
                    None,
                )
                return
            except Exception as error:  # noqa: BLE001 - startup probe is resilient
                last_error = error
                if attempts > 1:
                    await asyncio.sleep(1)
        await self.emit(
            "service.status",
            {
                "service": "remix",
                "state": "offline",
                "detail": str(last_error or "Remix is unavailable."),
            },
            None,
        )

    async def _ensure_preview_mode(self) -> bool:
        if (
            not self.config.force_remix_preview
            or self.remix_process_id is None
            or self.config.remix_executable_path is None
        ):
            return False
        preferences = self.config.remix_executable_path.parent / "Preferences.pRDat"
        ui_scale = read_float32(preferences, "ui_scaling")
        await asyncio.to_thread(
            select_preview_mode,
            self.remix_process_id,
            ui_scale=ui_scale,
            target_bounds=self.target_display_bounds,
        )
        # Switching Remix into Preview mode leaves its existing WebSocket
        # connected but unresponsive. Reconnect before the first action.
        await self.remix.close()
        self.remix_process_id = None
        if self.electron_process_id is not None:
            with contextlib.suppress(RuntimeError):
                await asyncio.to_thread(
                    focus_process_window,
                    self.electron_process_id,
                    title="Command Deck",
                )
        await self.emit("remix.preview.ready", {}, None)
        return True

    async def close(self) -> None:
        for task in self.tasks:
            task.cancel()
        for task in self.tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await self.twitch.close()
        await self.remix.close()


def create_app(service: CommandDeckService) -> web.Application:
    app = web.Application()
    app["command_deck_service"] = service
    app.router.add_get("/health", service.health)
    app.router.add_get("/ws", service.websocket)
    app.on_startup.append(lambda _app: service.start())
    app.on_cleanup.append(lambda _app: service.close())
    return app
