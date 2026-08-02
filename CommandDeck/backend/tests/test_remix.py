from types import SimpleNamespace

import pytest
from aiohttp import WSMsgType

from command_deck.remix import RemixClient


class FakeSocket:
    def __init__(self, message):
        self.closed = False
        self.message = message
        self.sent = []

    async def send_json(self, payload):
        self.sent.append(payload)

    async def receive(self):
        return self.message

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_request_reconnects_when_a_stale_socket_closes(monkeypatch):
    stale = FakeSocket(SimpleNamespace(type=WSMsgType.CLOSE))
    healthy = FakeSocket(
        SimpleNamespace(
            type=WSMsgType.TEXT,
            json=lambda: {"result": "success", "states": []},
        )
    )
    sockets = iter((stale, healthy))
    client = RemixClient("ws://example.invalid")

    async def connect():
        await client.close()
        client._socket = next(sockets)

    monkeypatch.setattr(client, "connect", connect)

    response = await client.request({"event": "list_states"})

    assert response == {"result": "success", "states": []}
    assert stale.closed is True
    assert healthy.sent == [{"event": "list_states"}]
    await client.close()
