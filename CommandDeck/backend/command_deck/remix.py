from __future__ import annotations

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
        self.timeout = ClientTimeout(total=timeout_seconds)
        self._session: ClientSession | None = None
        self._socket = None

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

    async def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.connected:
            await self.connect()
        try:
            await self._socket.send_json(payload)
            message = await self._socket.receive()
            if message.type != WSMsgType.TEXT:
                raise RemixError("Remix returned a non-text response.")
            response = message.json()
            if not isinstance(response, dict):
                raise RemixError("Remix returned an invalid response.")
            return response
        except RemixError:
            raise
        except Exception as error:
            await self.close()
            raise RemixError("The Remix connection was interrupted.") from error

    async def list_states(self) -> list[dict[str, Any]]:
        states = (await self.request({"event": "list_states"})).get("states")
        if not isinstance(states, list):
            raise RemixError("Remix did not return its state list.")
        return [state for state in states if isinstance(state, dict)]

    async def set_state(self, state_name: str) -> None:
        await self.request({"event": "state", "state_name": state_name})

    async def close(self) -> None:
        if self._socket is not None:
            await self._socket.close()
        if self._session is not None:
            await self._session.close()
        self._socket = self._session = None


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
