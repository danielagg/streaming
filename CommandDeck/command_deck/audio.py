from __future__ import annotations

import ctypes
import sys
import threading
from pathlib import Path


class AudioPlaybackError(RuntimeError):
    pass


class WindowsAudioPlayer:
    """Small MP3 player backed by Windows' built-in Media Control Interface."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._alias = "command_deck_action_audio"
        self._active = False

        if sys.platform != "win32":
            self._mci = None
            return

        self._mci = ctypes.WinDLL("winmm").mciSendStringW
        self._mci.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_uint,
            ctypes.c_void_p,
        ]
        self._mci.restype = ctypes.c_uint

    def _send(self, command: str, *, ignore_error: bool = False) -> None:
        if self._mci is None:
            raise AudioPlaybackError("Audio playback is only available on Windows.")

        result = self._mci(command, None, 0, None)
        if result and not ignore_error:
            raise AudioPlaybackError(
                f"Windows audio command failed with code {result}."
            )

    def play(self, audio_path: Path) -> None:
        if not audio_path.is_file():
            raise AudioPlaybackError(f"Audio file was not found: {audio_path}")

        with self._lock:
            self._close_locked()
            escaped_path = str(audio_path).replace('"', '""')
            self._send(
                f'open "{escaped_path}" type mpegvideo alias {self._alias}'
            )
            try:
                self._send(f"play {self._alias} from 0")
                self._active = True
            except Exception:
                self._close_locked()
                raise

    def stop(self) -> None:
        with self._lock:
            self._close_locked()

    def _close_locked(self) -> None:
        if self._mci is None:
            return
        self._send(f"stop {self._alias}", ignore_error=True)
        self._send(f"close {self._alias}", ignore_error=True)
        self._active = False
