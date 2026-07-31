from __future__ import annotations

import ctypes
import sys
import threading
from pathlib import Path


class WindowsAudioPlayer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._alias = "command_deck_action_audio"
        self._mci = (
            ctypes.WinDLL("winmm").mciSendStringW if sys.platform == "win32" else None
        )

    def _send(self, command: str, ignore_error: bool = False) -> None:
        if self._mci is None:
            raise RuntimeError("Audio playback is only available on Windows.")
        result = self._mci(command, None, 0, None)
        if result and not ignore_error:
            raise RuntimeError(f"Windows audio command failed with code {result}.")

    def play(self, path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(path)
        with self._lock:
            self._close()
            escaped = str(path).replace('"', '""')
            self._send(f'open "{escaped}" type mpegvideo alias {self._alias}')
            self._send(f"play {self._alias} from 0")

    def stop(self) -> None:
        with self._lock:
            self._close()

    def _close(self) -> None:
        if self._mci:
            self._send(f"stop {self._alias}", True)
            self._send(f"close {self._alias}", True)
