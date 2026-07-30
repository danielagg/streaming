from __future__ import annotations

import json
import base64
import hashlib
import queue
import socket
import subprocess
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from command_deck.app import CommandDeckApp
from command_deck.config import ActionDefinition, AppConfig, load_config
from command_deck.hotkeys import MultiPressDetector
from command_deck.remix import RemixClient
from command_deck.remix_startup import (
    GODOT_BOOL_VARIANT,
    GODOT_INT_VARIANT,
    enforce_scalar,
    read_float32,
    read_scalar,
)
from command_deck.remix_window import _scaled_point


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
        self.assertTrue(config.auto_launch_remix)
        self.assertTrue(config.force_remix_preview)
        self.assertTrue(config.force_transparent_background)
        self.assertIsNotNone(config.global_hotkeys)
        self.assertTrue(config.global_hotkeys.enabled)
        self.assertEqual(config.global_hotkeys.presses_required, 3)
        self.assertEqual(config.global_hotkeys.press_window_ms, 1200)
        self.assertEqual(
            {
                binding.key: binding.action_id
                for binding in config.global_hotkeys.bindings
            },
            {
                "F13": "whiskey",
                "F14": "croak",
                "F15": "fly",
            },
        )
        self.assertIsNotNone(config.remix_executable_path)
        self.assertTrue(config.remix_executable_path.is_file())
        self.assertEqual(
            config.remix_model_path,
            (
                PROJECT_DIRECTORY.parent
                / "Berry"
                / "Berry.pngRemix"
            ).resolve(),
        )
        self.assertTrue(config.remix_model_path.is_file())

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


class MultiPressDetectorTests(unittest.TestCase):
    def test_third_quick_press_triggers_and_resets_sequence(self) -> None:
        detector = MultiPressDetector(
            presses_required=3,
            press_window_seconds=1.2,
        )

        self.assertEqual(
            detector.register_press("F13", now=10.0),
            (1, False),
        )
        self.assertEqual(
            detector.register_press("F13", now=10.3),
            (2, False),
        )
        self.assertEqual(
            detector.register_press("F13", now=10.6),
            (3, True),
        )
        self.assertEqual(
            detector.register_press("F13", now=10.8),
            (1, False),
        )

    def test_press_outside_window_does_not_complete_sequence(self) -> None:
        detector = MultiPressDetector(
            presses_required=3,
            press_window_seconds=1.0,
        )

        detector.register_press("F14", now=20.0)
        detector.register_press("F14", now=20.4)

        self.assertEqual(
            detector.register_press("F14", now=21.1),
            (2, False),
        )


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
            auto_launch_remix=False,
            force_remix_preview=False,
            force_transparent_background=False,
            remix_executable_path=None,
            remix_model_path=None,
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

    def test_remix_launcher_passes_the_berry_model_to_the_executable(
        self,
    ) -> None:
        config = load_config(PROJECT_DIRECTORY / "config.json")
        app = object.__new__(CommandDeckApp)
        app.config = config

        with (
            patch("command_deck.app.enforce_remix_startup") as enforce,
            patch("command_deck.app.subprocess.Popen") as popen,
        ):
            popen.return_value.pid = 4123
            succeeded, message = app._launch_remix_model()

        self.assertTrue(succeeded)
        self.assertIn("Berry.pngRemix", message)
        self.assertIn("transparent Preview mode", message)
        enforce.assert_called_once_with(
            preferences_path=(
                config.remix_executable_path.parent / "Preferences.pRDat"
            ),
            model_path=config.remix_model_path,
            preview=True,
            transparent=True,
        )
        popen.assert_called_once_with(
            [
                str(config.remix_executable_path),
                str(config.remix_model_path),
            ],
            cwd=config.remix_executable_path.parent,
            close_fds=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        self.assertEqual(app._remix_process_id, 4123)


class RemixStartupSettingsTests(unittest.TestCase):
    def test_production_files_are_configured_for_transparent_preview(
        self,
    ) -> None:
        config = load_config(PROJECT_DIRECTORY / "config.json")
        preferences = (
            config.remix_executable_path.parent / "Preferences.pRDat"
        )

        self.assertEqual(
            read_scalar(preferences, "mode", GODOT_INT_VARIANT),
            1,
        )
        self.assertEqual(
            read_scalar(
                config.remix_model_path,
                "is_transparent",
                GODOT_BOOL_VARIANT,
            ),
            1,
        )
        self.assertEqual(
            read_float32(preferences, "ui_scaling"),
            1.0,
        )

    def test_scalar_enforcement_changes_only_the_target_value(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary_directory:
            settings_path = Path(temporary_directory) / "Preferences.pRDat"
            fixture = (
                b"before"
                + b"\x15\0\0\0\x04\0\0\0mode"
                + b"\x02\0\0\0\x00\0\0\0"
                + b"after"
            )
            settings_path.write_bytes(fixture)

            changed = enforce_scalar(
                settings_path,
                "mode",
                GODOT_INT_VARIANT,
                1,
                allowed_values={0, 1, 2},
            )

            self.assertTrue(changed)
            self.assertEqual(
                read_scalar(settings_path, "mode", GODOT_INT_VARIANT),
                1,
            )
            expected = fixture.replace(
                b"\x02\0\0\0\x00\0\0\0",
                b"\x02\0\0\0\x01\0\0\0",
            )
            self.assertEqual(settings_path.read_bytes(), expected)

    def test_preview_click_coordinates_follow_remix_ui_scale(self) -> None:
        self.assertEqual(_scaled_point((61, 16), 1.0), (61, 16))
        self.assertEqual(_scaled_point((61, 16), 1.5), (92, 24))


if __name__ == "__main__":
    unittest.main()
