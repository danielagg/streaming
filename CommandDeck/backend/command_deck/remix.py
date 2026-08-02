from __future__ import annotations

import asyncio
import contextlib
from typing import Any, Protocol

from aiohttp import ClientSession, ClientTimeout, WSMsgType


class RemixError(RuntimeError):
    pass


class RemixAPI(Protocol):
    async def list_states(self) -> list[dict[str, Any]]: ...
    async def set_state(self, state_name: str) -> None: ...
    async def close(self) -> None: ...


class RemixClient:
    """Small async client for PNGTuber Remix's local JSON WebSocket API."""

    def __init__(self, url: str, timeout_seconds: float = 3.0) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.timeout = ClientTimeout(total=timeout_seconds)
        self._session: ClientSession | None = None
        self._socket = None
        self._request_lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._socket is not None and not self._socket.closed

    async def connect(self) -> None:
        await self.close()
        self._session = ClientSession(timeout=self.timeout)
        try:
            self._socket = await self._session.ws_connect(self.url)
        except Exception as error:
            await self.close()
            raise RemixError(
                f"Could not reach PNGTuber Remix at {self.url}."
            ) from error

    async def _request_once(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.connected:
            await self.connect()
        socket = self._socket
        if socket is None:
            raise RemixError("The Remix connection was not established.")
        await asyncio.wait_for(socket.send_json(payload), self.timeout_seconds)
        message = await asyncio.wait_for(socket.receive(), self.timeout_seconds)
        if message.type != WSMsgType.TEXT:
            raise RemixError("Remix closed the connection without a response.")
        response = message.json()
        if not isinstance(response, dict):
            raise RemixError("Remix returned an invalid response.")
        if response.get("result") == "error":
            raise RemixError(str(response.get("message") or "Remix rejected the request."))
        return response

    async def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with self._request_lock:
            last_error: Exception | None = None
            for attempt in range(2):
                try:
                    return await self._request_once(payload)
                except TimeoutError:
                    last_error = RemixError("PNGTuber Remix did not respond in time.")
                except RemixError as error:
                    last_error = error
                except Exception as error:  # noqa: BLE001 - normalize API failures
                    last_error = RemixError("The Remix connection was interrupted.")
                    last_error.__cause__ = error
                await self.close()
                if attempt == 0:
                    continue
                raise last_error
            raise last_error or RemixError("The Remix request failed.")

    async def list_states(self) -> list[dict[str, Any]]:
        states = (await self.request({"event": "list_states"})).get("states")
        if not isinstance(states, list):
            raise RemixError("Remix did not return its state list.")
        return [state for state in states if isinstance(state, dict)]

    async def set_state(self, state_name: str) -> None:
        await self.request({"event": "state", "state_name": state_name})

    async def close(self) -> None:
        socket, session = self._socket, self._session
        self._socket = self._session = None
        if socket is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(socket.close(), 1.0)
        if session is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(session.close(), 1.0)


class MockRemixClient:
    def __init__(self, action_states: list[str], normal_state: str = "Idle") -> None:
        self.current = normal_state
        self.states = [normal_state, *action_states]
        self.transitions: list[str] = []

    async def list_states(self) -> list[dict[str, Any]]:
        return [
            {"name": name, "is_current": name == self.current} for name in self.states
        ]

    async def set_state(self, state_name: str) -> None:
        if state_name not in self.states:
            raise RemixError(f"Remix has no state named '{state_name}'.")
        self.current = state_name
        self.transitions.append(state_name)

    async def close(self) -> None:
        return None
