from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import math
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from aiohttp import ClientSession, ClientTimeout, WSMsgType

from .config import ObsConfig


class ObsError(RuntimeError):
    pass


class ObsAPI(Protocol):
    @property
    def connected(self) -> bool: ...

    async def connect(self) -> None: ...
    async def request(
        self, request_type: str, request_data: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...
    async def wait_closed(self) -> None: ...
    async def close(self) -> None: ...


def build_auth_response(password: str, salt: str, challenge: str) -> str:
    secret = base64.b64encode(
        hashlib.sha256(f"{password}{salt}".encode()).digest()
    ).decode()
    return base64.b64encode(
        hashlib.sha256(f"{secret}{challenge}".encode()).digest()
    ).decode()


class ObsWebSocketClient:
    """Minimal OBS WebSocket v5 client for scenes and media controls."""

    EVENT_SUBSCRIPTIONS = 1 | 4 | 256  # General, Scenes, MediaInputs

    def __init__(
        self,
        url: str,
        password: str | None,
        event_handler: Callable[[str, dict[str, Any]], Awaitable[None]],
        timeout_seconds: float = 5.0,
    ) -> None:
        self.url = url
        self.password = password
        self.event_handler = event_handler
        self.timeout_seconds = timeout_seconds
        self._session: ClientSession | None = None
        self._socket = None
        self._reader_task: asyncio.Task[None] | None = None
        self._event_tasks: set[asyncio.Task[None]] = set()
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._send_lock = asyncio.Lock()
        self._closed = asyncio.Event()
        self._closed.set()

    @property
    def connected(self) -> bool:
        return self._socket is not None and not self._socket.closed

    async def connect(self) -> None:
        await self.close()
        self._closed.clear()
        self._session = ClientSession(
            timeout=ClientTimeout(total=None, connect=self.timeout_seconds)
        )
        try:
            self._socket = await self._session.ws_connect(self.url)
            hello = await self._receive_json("OBS did not send its greeting.")
            if hello.get("op") != 0 or not isinstance(hello.get("d"), dict):
                raise ObsError("OBS returned an invalid WebSocket greeting.")
            authentication = hello["d"].get("authentication")
            identify: dict[str, Any] = {
                "rpcVersion": 1,
                "eventSubscriptions": self.EVENT_SUBSCRIPTIONS,
            }
            if authentication is not None:
                if not self.password:
                    raise ObsError(
                        "OBS requires a password. Create CommandDeck/obs-password.txt "
                        "or set COMMAND_DECK_OBS_PASSWORD."
                    )
                if not isinstance(authentication, dict):
                    raise ObsError("OBS returned invalid authentication data.")
                salt = authentication.get("salt")
                challenge = authentication.get("challenge")
                if not isinstance(salt, str) or not isinstance(challenge, str):
                    raise ObsError("OBS returned invalid authentication data.")
                identify["authentication"] = build_auth_response(
                    self.password, salt, challenge
                )
            await self._socket.send_json({"op": 1, "d": identify})
            identified = await self._receive_json("OBS did not finish authentication.")
            if identified.get("op") != 2:
                raise ObsError("OBS rejected the WebSocket connection.")
            self._reader_task = asyncio.create_task(self._read_messages())
        except Exception:
            await self.close()
            raise

    async def _receive_json(self, message: str) -> dict[str, Any]:
        socket = self._socket
        if socket is None:
            raise ObsError("OBS is not connected.")
        response = await asyncio.wait_for(
            socket.receive(), timeout=self.timeout_seconds
        )
        if response.type != WSMsgType.TEXT:
            raise ObsError(message)
        payload = response.json()
        if not isinstance(payload, dict):
            raise ObsError(message)
        return payload

    async def request(
        self, request_type: str, request_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        socket = self._socket
        if socket is None or socket.closed:
            raise ObsError("OBS is not connected.")
        request_id = str(uuid.uuid4())
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        payload = {
            "requestType": request_type,
            "requestId": request_id,
            "requestData": request_data or {},
        }
        try:
            async with self._send_lock:
                await socket.send_json({"op": 6, "d": payload})
            return await asyncio.wait_for(future, timeout=self.timeout_seconds)
        except TimeoutError as error:
            raise ObsError(f"OBS did not respond to {request_type}.") from error
        finally:
            self._pending.pop(request_id, None)

    async def _read_messages(self) -> None:
        socket = self._socket
        if socket is None:
            return
        try:
            async for message in socket:
                if message.type != WSMsgType.TEXT:
                    continue
                payload = message.json()
                if not isinstance(payload, dict) or not isinstance(payload.get("d"), dict):
                    continue
                data = payload["d"]
                if payload.get("op") == 7:
                    request_id = data.get("requestId")
                    future = self._pending.get(request_id)
                    if future is None or future.done():
                        continue
                    status = data.get("requestStatus", {})
                    if status.get("result") is True:
                        response_data = data.get("responseData", {})
                        future.set_result(
                            response_data if isinstance(response_data, dict) else {}
                        )
                    else:
                        future.set_exception(
                            ObsError(
                                str(status.get("comment") or "OBS rejected the request.")
                            )
                        )
                elif payload.get("op") == 5:
                    event_type = data.get("eventType")
                    event_data = data.get("eventData", {})
                    if isinstance(event_type, str) and isinstance(event_data, dict):
                        task = asyncio.create_task(
                            self.event_handler(event_type, event_data)
                        )
                        self._event_tasks.add(task)
                        task.add_done_callback(self._event_tasks.discard)
        finally:
            self._closed.set()
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(ObsError("The OBS connection was interrupted."))

    async def wait_closed(self) -> None:
        await self._closed.wait()

    async def close(self) -> None:
        reader, socket, session = self._reader_task, self._socket, self._session
        self._reader_task = None
        self._socket = None
        self._session = None
        if socket is not None:
            with contextlib.suppress(Exception):
                await socket.close()
        if reader is not None and reader is not asyncio.current_task():
            reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reader
        for task in tuple(self._event_tasks):
            task.cancel()
        for task in tuple(self._event_tasks):
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._event_tasks.clear()
        if session is not None:
            with contextlib.suppress(Exception):
                await session.close()
        self._closed.set()


class ObsService:
    RECONNECT_DELAY_SECONDS = 3.0

    def __init__(
        self,
        config: ObsConfig,
        emit: Callable[[str, dict[str, Any], str | None], Awaitable[None]],
        client: ObsAPI | None = None,
    ) -> None:
        self.config = config
        self.emit = emit
        self.client: ObsAPI = client or ObsWebSocketClient(
            config.websocket_url, config.password, self._handle_obs_event
        )
        self.current_scene: str | None = None
        self._run_task: asyncio.Task[None] | None = None
        self._tail_task: asyncio.Task[None] | None = None
        self._scene_lock = asyncio.Lock()
        self._closing = False
        self._music_volume_db: float | None = None

    @property
    def configured_scene_names(self) -> set[str]:
        return {scene.name for scene in self.config.scenes}

    async def start(self) -> None:
        if not self.config.enabled:
            await self.emit(
                "service.status",
                {"service": "obs", "state": "offline", "detail": "Disabled"},
                None,
            )
            return
        if self._run_task is None or self._run_task.done():
            self._closing = False
            self._run_task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        while not self._closing:
            await self.emit(
                "service.status",
                {
                    "service": "obs",
                    "state": "connecting",
                    "detail": f"Connecting to {self.config.websocket_url}",
                },
                None,
            )
            try:
                await self.client.connect()
                await self._load_initial_state()
                await self.emit(
                    "service.status",
                    {
                        "service": "obs",
                        "state": "online",
                        "detail": f"{len(self.config.scenes)} scenes available",
                    },
                    None,
                )
                await self.client.wait_closed()
                if not self._closing:
                    raise ObsError("The OBS connection closed.")
            except asyncio.CancelledError:
                raise
            except Exception as error:  # noqa: BLE001 - connection boundary
                if not self._closing:
                    await self.emit(
                        "service.status",
                        {
                            "service": "obs",
                            "state": "error",
                            "detail": str(error),
                        },
                        None,
                    )
            finally:
                await self._cancel_tail()
                self.current_scene = None
                await self.emit(
                    "obs.music.tail", {"state": "idle", "remainingMs": 0}, None
                )
                await self.client.close()
            if not self._closing:
                await asyncio.sleep(self.RECONNECT_DELAY_SECONDS)

    async def _load_initial_state(self) -> None:
        scene_list = await self.client.request("GetSceneList")
        scenes = scene_list.get("scenes", [])
        available_scenes = {
            scene.get("sceneName")
            for scene in scenes
            if isinstance(scene, dict) and isinstance(scene.get("sceneName"), str)
        }
        missing = sorted(self.configured_scene_names - available_scenes)
        if missing:
            raise ObsError(f"OBS is missing configured scenes: {', '.join(missing)}")
        input_list = await self.client.request("GetInputList")
        inputs = input_list.get("inputs", [])
        available_inputs = {
            item.get("inputName")
            for item in inputs
            if isinstance(item, dict) and isinstance(item.get("inputName"), str)
        }
        if self.config.music_input not in available_inputs:
            raise ObsError(
                f"OBS has no input named '{self.config.music_input}'."
            )
        current = scene_list.get("currentProgramSceneName")
        self.current_scene = current if isinstance(current, str) else None
        if self.current_scene is not None:
            await self.emit(
                "obs.scene.changed", {"sceneName": self.current_scene}, None
            )

    async def _handle_obs_event(
        self, event_type: str, event_data: dict[str, Any]
    ) -> None:
        if event_type != "CurrentProgramSceneChanged":
            return
        scene_name = event_data.get("sceneName")
        if isinstance(scene_name, str):
            await self._scene_changed(scene_name)

    async def _scene_changed(self, scene_name: str) -> None:
        async with self._scene_lock:
            previous = self.current_scene
            if scene_name == previous:
                return
            self.current_scene = scene_name
            await self.emit("obs.scene.changed", {"sceneName": scene_name}, None)
            if scene_name == self.config.starting_soon_scene:
                await self._cancel_tail()
                await self._restore_music_volume()
                await self._media_action("RESTART")
                await self.emit(
                    "obs.music.tail", {"state": "idle", "remainingMs": 0}, None
                )
            elif (
                previous == self.config.starting_soon_scene
                and scene_name == self.config.main_scene
            ):
                await self._start_tail()
            elif self._tail_task is not None:
                await self._cancel_tail()
                await self._stop_music()

    async def set_scene(self, scene_name: str) -> None:
        if scene_name not in self.configured_scene_names:
            raise ObsError(f"Scene '{scene_name}' is not configured in Command Deck.")
        await self.client.request(
            "SetCurrentProgramScene", {"sceneName": scene_name}
        )

    async def reconnect(self) -> None:
        if not self.config.enabled:
            raise ObsError("OBS integration is disabled.")
        await self.client.close()
        if self._run_task is None or self._run_task.done():
            await self.start()

    async def stop_music(self) -> None:
        await self._cancel_tail()
        await self._stop_music()

    async def _start_tail(self) -> None:
        await self._cancel_tail()
        volume = await self.client.request(
            "GetInputVolume", {"inputName": self.config.music_input}
        )
        input_volume_db = volume.get("inputVolumeDb")
        self._music_volume_db = (
            float(input_volume_db)
            if isinstance(input_volume_db, (int, float))
            else 0.0
        )
        self._tail_task = asyncio.create_task(self._run_music_tail())

    async def _run_music_tail(self) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.config.music_tail_ms / 1000
        fade_seconds = self.config.music_fade_ms / 1000
        fade_start = deadline - fade_seconds
        try:
            while loop.time() < fade_start:
                remaining_ms = max(0, math.ceil((deadline - loop.time()) * 1000))
                await self.emit(
                    "obs.music.tail",
                    {"state": "playing", "remainingMs": remaining_ms},
                    None,
                )
                await asyncio.sleep(min(1.0, max(0.0, fade_start - loop.time())))
            if fade_seconds > 0:
                steps = max(1, math.ceil(fade_seconds / 0.25))
                original_db = self._music_volume_db or 0.0
                silent_db = min(original_db, -60.0)
                for step in range(1, steps + 1):
                    progress = step / steps
                    target_db = original_db + (silent_db - original_db) * progress
                    await self.client.request(
                        "SetInputVolume",
                        {
                            "inputName": self.config.music_input,
                            "inputVolumeDb": target_db,
                        },
                    )
                    remaining_ms = max(
                        0, math.ceil((deadline - loop.time()) * 1000)
                    )
                    await self.emit(
                        "obs.music.tail",
                        {"state": "fading", "remainingMs": remaining_ms},
                        None,
                    )
                    target_time = fade_start + fade_seconds * progress
                    await asyncio.sleep(max(0.0, target_time - loop.time()))
            await self._stop_music()
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 - surface media failures
            await self.emit(
                "service.status",
                {"service": "obs", "state": "error", "detail": str(error)},
                None,
            )
        finally:
            if self._tail_task is asyncio.current_task():
                self._tail_task = None

    async def _cancel_tail(self) -> None:
        task = self._tail_task
        self._tail_task = None
        if task is None or task is asyncio.current_task():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _media_action(self, action: str) -> None:
        await self.client.request(
            "TriggerMediaInputAction",
            {
                "inputName": self.config.music_input,
                "mediaAction": f"OBS_WEBSOCKET_MEDIA_INPUT_ACTION_{action}",
            },
        )

    async def _restore_music_volume(self) -> None:
        if self._music_volume_db is None or not self.client.connected:
            return
        await self.client.request(
            "SetInputVolume",
            {
                "inputName": self.config.music_input,
                "inputVolumeDb": self._music_volume_db,
            },
        )

    async def _stop_music(self) -> None:
        await self._media_action("STOP")
        await self._restore_music_volume()
        await self.emit(
            "obs.music.tail", {"state": "idle", "remainingMs": 0}, None
        )

    async def close(self) -> None:
        self._closing = True
        await self._cancel_tail()
        await self.client.close()
        if self._run_task is not None:
            self._run_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._run_task
            self._run_task = None
