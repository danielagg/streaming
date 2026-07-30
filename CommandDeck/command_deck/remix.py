from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import threading
from typing import Any
from urllib.parse import urlparse


class RemixConnectionError(RuntimeError):
    pass


class RemixProtocolError(RuntimeError):
    pass


class RemixClient:
    """Minimal synchronous RFC 6455 client for PNGTuber Remix's local API."""

    def __init__(self, url: str, timeout_seconds: float = 3.0) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self._socket: socket.socket | None = None
        self._read_buffer = bytearray()
        self._request_lock = threading.Lock()

    @property
    def connected(self) -> bool:
        return self._socket is not None

    def connect(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme != "ws":
            raise RemixConnectionError("Only local ws:// endpoints are supported.")
        if not parsed.hostname:
            raise RemixConnectionError(f"Invalid WebSocket URL: {self.url}")

        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        self.close()
        try:
            connection = socket.create_connection(
                (parsed.hostname, port),
                timeout=self.timeout_seconds,
            )
            connection.settimeout(self.timeout_seconds)
        except OSError as error:
            raise RemixConnectionError(
                f"Could not reach PNGTuber Remix at {self.url}."
            ) from error

        websocket_key = base64.b64encode(os.urandom(16)).decode("ascii")
        host_header = parsed.hostname
        if port != 80:
            host_header = f"{host_header}:{port}"
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {websocket_key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        ).encode("ascii")

        try:
            connection.sendall(request)
            response = bytearray()
            while b"\r\n\r\n" not in response:
                chunk = connection.recv(4096)
                if not chunk:
                    raise RemixProtocolError(
                        "Remix closed the connection during setup."
                    )
                response.extend(chunk)
                if len(response) > 65536:
                    raise RemixProtocolError(
                        "Remix returned an invalid WebSocket response."
                    )

            header_bytes, remainder = bytes(response).split(b"\r\n\r\n", 1)
            header_lines = header_bytes.decode("iso-8859-1").split("\r\n")
            if " 101 " not in f" {header_lines[0]} ":
                raise RemixProtocolError(
                    f"WebSocket setup failed: {header_lines[0]}"
                )

            headers: dict[str, str] = {}
            for line in header_lines[1:]:
                if ":" in line:
                    name, value = line.split(":", 1)
                    headers[name.strip().lower()] = value.strip()

            expected_accept = base64.b64encode(
                hashlib.sha1(
                    (
                        websocket_key
                        + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
                    ).encode("ascii")
                ).digest()
            ).decode("ascii")
            if headers.get("sec-websocket-accept") != expected_accept:
                raise RemixProtocolError(
                    "Remix returned an invalid WebSocket handshake."
                )

            self._socket = connection
            self._read_buffer = bytearray(remainder)
        except Exception:
            connection.close()
            raise

    def close(self) -> None:
        connection = self._socket
        self._socket = None
        self._read_buffer.clear()
        if connection is None:
            return
        try:
            connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        connection.close()

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._request_lock:
            if self._socket is None:
                self.connect()

            try:
                encoded = json.dumps(payload, separators=(",", ":")).encode(
                    "utf-8"
                )
                self._send_frame(opcode=0x1, payload=encoded)
                response = self._receive_message()
                decoded = json.loads(response.decode("utf-8"))
                if not isinstance(decoded, dict):
                    raise RemixProtocolError(
                        "Remix returned an unexpected response."
                    )
                return decoded
            except (OSError, TimeoutError, json.JSONDecodeError) as error:
                self.close()
                raise RemixConnectionError(
                    "The connection to PNGTuber Remix was interrupted."
                ) from error

    def list_states(self) -> list[dict[str, Any]]:
        response = self.request({"event": "list_states"})
        states = response.get("states")
        if not isinstance(states, list):
            raise RemixProtocolError("Remix did not return its state list.")
        return [state for state in states if isinstance(state, dict)]

    def set_state(self, state_name: str) -> None:
        self.request({"event": "state", "state_name": state_name})

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        connection = self._require_socket()
        frame = bytearray([0x80 | opcode])
        payload_length = len(payload)
        if payload_length < 126:
            frame.append(0x80 | payload_length)
        elif payload_length <= 0xFFFF:
            frame.append(0x80 | 126)
            frame.extend(struct.pack("!H", payload_length))
        else:
            frame.append(0x80 | 127)
            frame.extend(struct.pack("!Q", payload_length))

        mask = os.urandom(4)
        frame.extend(mask)
        frame.extend(
            byte ^ mask[index % 4] for index, byte in enumerate(payload)
        )
        connection.sendall(frame)

    def _receive_message(self) -> bytes:
        fragments = bytearray()
        message_started = False

        while True:
            first, second = self._read_exact(2)
            final = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            payload_length = second & 0x7F

            if payload_length == 126:
                payload_length = struct.unpack("!H", self._read_exact(2))[0]
            elif payload_length == 127:
                payload_length = struct.unpack("!Q", self._read_exact(8))[0]

            mask = self._read_exact(4) if masked else b""
            payload = bytearray(self._read_exact(payload_length))
            if masked:
                for index in range(payload_length):
                    payload[index] ^= mask[index % 4]

            if opcode == 0x8:
                self.close()
                raise RemixConnectionError(
                    "PNGTuber Remix closed the WebSocket connection."
                )
            if opcode == 0x9:
                self._send_frame(opcode=0xA, payload=bytes(payload))
                continue
            if opcode == 0xA:
                continue
            if opcode in (0x1, 0x2):
                fragments = payload
                message_started = True
            elif opcode == 0x0 and message_started:
                fragments.extend(payload)
            else:
                raise RemixProtocolError(
                    f"Unsupported WebSocket frame type: {opcode}"
                )

            if final:
                return bytes(fragments)

    def _read_exact(self, length: int) -> bytes:
        connection = self._require_socket()
        while len(self._read_buffer) < length:
            chunk = connection.recv(max(4096, length - len(self._read_buffer)))
            if not chunk:
                raise RemixConnectionError(
                    "PNGTuber Remix closed the WebSocket connection."
                )
            self._read_buffer.extend(chunk)

        result = bytes(self._read_buffer[:length])
        del self._read_buffer[:length]
        return result

    def _require_socket(self) -> socket.socket:
        if self._socket is None:
            raise RemixConnectionError("Command Deck is not connected to Remix.")
        return self._socket
