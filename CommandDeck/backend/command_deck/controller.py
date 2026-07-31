from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from .audio import WindowsAudioPlayer
from .config import ActionDefinition
from .remix import RemixAPI

EventSink = Callable[[str, dict[str, Any], str | None], Awaitable[None]]


class ActionController:
    def __init__(
        self,
        actions: tuple[ActionDefinition, ...],
        remix: RemixAPI,
        emit: EventSink,
        audio: WindowsAudioPlayer | Any | None = None,
    ) -> None:
        self.actions = {action.id: action for action in actions}
        self.remix = remix
        self.emit = emit
        self.audio = audio or WindowsAudioPlayer()
        self._lock = asyncio.Lock()
        self._last_normal_state: str | None = None

    async def trigger(self, action_id: str, request_id: str | None = None) -> None:
        action = self.actions.get(action_id)
        if action is None:
            raise ValueError(f"Unknown action: {action_id}")
        if self._lock.locked():
            raise RuntimeError("Another Berry action is already running.")
        async with self._lock:
            await self._execute(action, request_id)

    async def _audio_call(self, name: str, *args: Any) -> None:
        result = await asyncio.to_thread(getattr(self.audio, name), *args)
        if inspect.isawaitable(result):
            await result

    async def _execute(self, action: ActionDefinition, request_id: str | None) -> None:
        normal_state = None
        changed = False
        failure: Exception | None = None
        try:
            states = await self.remix.list_states()
            available = {
                str(state.get("name")) for state in states if state.get("name")
            }
            if action.state_name not in available:
                raise RuntimeError(f"Remix has no state named '{action.state_name}'.")
            action_states = {item.state_name for item in self.actions.values()}
            current = next((state for state in states if state.get("is_current")), None)
            if current and current.get("name") not in action_states:
                normal_state = str(current["name"])
            elif self._last_normal_state in available:
                normal_state = self._last_normal_state
            else:
                fallback = next(
                    (
                        state
                        for state in states
                        if state.get("name") not in action_states
                    ),
                    None,
                )
                normal_state = str(fallback["name"]) if fallback else None
            if not normal_state:
                raise RuntimeError("Remix has no normal state to restore.")
            self._last_normal_state = normal_state
            await self.remix.set_state(action.state_name)
            changed = True
            if action.audio_path:
                await self._audio_call("play", action.audio_path)
            await self.emit(
                "berry.action.progress",
                {
                    "actionId": action.id,
                    "remainingMs": action.duration_ms,
                },
                request_id,
            )
            await asyncio.sleep(action.duration_ms / 1000)
        except Exception as error:  # noqa: BLE001 - action boundary reports failures
            failure = error
        finally:
            try:
                await self._audio_call("stop")
            except Exception as error:  # noqa: BLE001 - cleanup must continue
                failure = failure or error
            if changed and normal_state:
                try:
                    await self.remix.set_state(normal_state)
                except Exception as error:  # noqa: BLE001 - preserve first failure
                    failure = failure or error
        if failure:
            await self.emit(
                "berry.action.error",
                {"actionId": action.id, "name": action.name, "message": str(failure)},
                request_id,
            )
            return
        await self.emit(
            "berry.action.completed",
            {"actionId": action.id, "name": action.name, "restoredState": normal_state},
            request_id,
        )
