from __future__ import annotations

import json
import base64
import hashlib
import socket
import threading
import unittest
import queue
from pathlib import Path

from command_deck.app import CommandDeckApp
from command_deck.config import ActionDefinition, AppConfig, load_config
from command_deck.remix import RemixClient


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent


class ConfigTests(unittest.TestCase):
    def test_production_config_has_three_unique_actions(self) -> None:
        config = load_config(PROJECT_DIRECTORY / "config.json")

        self.assertEqual(len(config.actions), 3)
        self.assertEqual(len({action.id for action in config.actions}), 3)
        self.assertEqual(
            [action.state_name for action in config.actions],
            ["Whiskey Sip", "Croaking", "Fly Catch"],
        )

    def test_audio_path_resolves_to_existing_mp3(self) -> None:
        config = load_config(PROJECT_DIRECTORY / "config.json")
        croak = next(action for action in config.actions if action.id == "croak")

        self.assertIsNotNone(croak.audio_path)
        self.assertTrue(croak.audio_path.is_file())


class WebSocketFrameTests(unittest.TestCase):
    def test_client_text_frame_is_masked_and_decodable(self) -> None:
        client_socket, server_socket = socket.socketpair()
        self.addCleanup(client_socket.close)
        self.addCleanup(server_socket.close)

        client = RemixClient("ws://127.0.0.1:9321")
        client._socket = client_socket
        payload = json.dumps({"event": "list_states"}).encode("utf-8")

        sender = threading.Thread(
            target=client._send_frame,
            kwargs={"opcode": 0x1, "payload": payload},
        )
        sender.start()

        header = server_socket.recv(2)
        self.assertEqual(header[0], 0x81)
        self.assertTrue(header[1] & 0x80)
        payload_length = header[1] & 0x7F
        mask = server_socket.recv(4)
        masked_payload = server_socket.recv(payload_length)
        decoded = bytes(
            byte ^ mask[index % 4]
            for index, byte in enumerate(masked_payload)
        )
        sender.join(timeout=1)

        self.assertEqual(decoded, payload)

    def test_fragmented_server_message_is_reassembled(self) -> None:
        client_socket, server_socket = socket.socketpair()
        self.addCleanup(client_socket.close)
        self.addCleanup(server_socket.close)

        client = RemixClient("ws://127.0.0.1:9321")
        client._socket = client_socket
        server_socket.sendall(b"\x01\x05hello\x80\x06 world")

        self.assertEqual(client._receive_message(), b"hello world")

    def test_connection_handshake_and_state_request(self) -> None:
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        self.addCleanup(server.close)
        host, port = server.getsockname()
        server_errors: list[Exception] = []

        def run_server() -> None:
            try:
                connection, _address = server.accept()
                with connection:
                    request = bytearray()
                    while b"\r\n\r\n" not in request:
                        request.extend(connection.recv(4096))
                    headers = request.decode("iso-8859-1").split("\r\n")
                    websocket_key = next(
                        line.split(":", 1)[1].strip()
                        for line in headers
                        if line.lower().startswith("sec-websocket-key:")
                    )
                    accept = base64.b64encode(
                        hashlib.sha1(
                            (
                                websocket_key
                                + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
                            ).encode("ascii")
                        ).digest()
                    ).decode("ascii")
                    connection.sendall(
                        (
                            "HTTP/1.1 101 Switching Protocols\r\n"
                            "Upgrade: websocket\r\n"
                            "Connection: Upgrade\r\n"
                            f"Sec-WebSocket-Accept: {accept}\r\n"
                            "\r\n"
                        ).encode("ascii")
                    )

                    first, second = connection.recv(2)
                    self.assertEqual(first, 0x81)
                    payload_length = second & 0x7F
                    mask = connection.recv(4)
                    masked = connection.recv(payload_length)
                    payload = bytes(
                        byte ^ mask[index % 4]
                        for index, byte in enumerate(masked)
                    )
                    self.assertEqual(
                        json.loads(payload),
                        {"event": "list_states"},
                    )

                    response = json.dumps(
                        {
                            "states": [
                                {"name": "Idle", "is_current": True}
                            ]
                        }
                    ).encode("utf-8")
                    connection.sendall(bytes([0x81, len(response)]) + response)
            except Exception as error:
                server_errors.append(error)

        server_thread = threading.Thread(target=run_server)
        server_thread.start()

        client = RemixClient(f"ws://{host}:{port}")
        self.addCleanup(client.close)
        client.connect()
        states = client.list_states()
        server_thread.join(timeout=2)

        self.assertFalse(server_thread.is_alive())
        self.assertFalse(server_errors)
        self.assertEqual(states, [{"name": "Idle", "is_current": True}])


class ActionControllerTests(unittest.TestCase):
    def test_action_enters_target_and_restores_current_normal_state(self) -> None:
        action = ActionDefinition(
            id="test",
            number="01",
            name="Test Action",
            state_name="Action State",
            description="Test",
            duration_ms=0,
            accent="#ffffff",
        )

        class FakeClient:
            def __init__(self) -> None:
                self.transitions: list[str] = []

            def list_states(self) -> list[dict[str, object]]:
                return [
                    {"name": "Idle", "is_current": True},
                    {"name": "Action State", "is_current": False},
                ]

            def set_state(self, state_name: str) -> None:
                self.transitions.append(state_name)

            def close(self) -> None:
                pass

        class FakeAudio:
            def play(self, _audio_path: Path) -> None:
                pass

            def stop(self) -> None:
                pass

        app = object.__new__(CommandDeckApp)
        app.config = AppConfig(
            app_name="Test",
            websocket_url="ws://127.0.0.1:1",
            actions=(action,),
        )
        app.client = FakeClient()
        app.audio = FakeAudio()
        app._ui_queue = queue.Queue()
        app._stop_event = threading.Event()
        app._last_normal_state = None

        app._execute_action(action)

        self.assertEqual(
            app.client.transitions,
            ["Action State", "Idle"],
        )
        events = list(app._ui_queue.queue)
        self.assertEqual(events[0][0], "action_started")
        self.assertEqual(events[1][0], "action_complete")


if __name__ == "__main__":
    unittest.main()
