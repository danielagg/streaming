from __future__ import annotations

import ctypes
import sys
import threading
import time
from collections.abc import Callable, Mapping
from ctypes import wintypes


class MultiPressDetector:
    def __init__(self, presses_required: int, press_window_seconds: float) -> None:
        if presses_required < 1 or press_window_seconds <= 0:
            raise ValueError("Press count and window must be positive.")
        self.presses_required = presses_required
        self.press_window_seconds = press_window_seconds
        self._presses: dict[str, list[float]] = {}

    def register_press(self, key: str, now: float | None = None) -> tuple[int, bool]:
        instant = time.monotonic() if now is None else now
        recent = [
            value
            for value in self._presses.get(key, [])
            if value >= instant - self.press_window_seconds
        ]
        recent.append(instant)
        triggered = len(recent) >= self.presses_required
        if triggered:
            self._presses.pop(key, None)
        else:
            self._presses[key] = recent
        return len(recent), triggered


class GlobalHotkeyListener:
    """Windows F13-F24 listener. start() is a harmless no-op off Windows."""

    def __init__(
        self,
        bindings: Mapping[str, str],
        callback: Callable[[str, str, int, bool], None],
        presses_required: int,
        press_window_ms: int,
    ) -> None:
        self.bindings = {key.upper(): value for key, value in bindings.items()}
        self.callback = callback
        self.detector = MultiPressDetector(presses_required, press_window_ms / 1000)
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._stop = threading.Event()

    def start(self) -> bool:
        if sys.platform != "win32" or not self.bindings:
            return False
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="command-deck-hotkeys", daemon=True
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._thread_id is not None and sys.platform == "win32":
            ctypes.WinDLL("user32", use_last_error=True).PostThreadMessageW(
                self._thread_id, 0x0012, 0, 0
            )
        if self._thread:
            self._thread.join(timeout=1)

    def _run(self) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._thread_id = int(kernel32.GetCurrentThreadId())
        registrations: dict[int, tuple[str, str]] = {}
        try:
            for offset, item in enumerate(self.bindings.items()):
                key, action_id = item
                hotkey_id = 0x6D00 + offset
                vk = 0x70 + int(key[1:]) - 1
                if not user32.RegisterHotKey(None, hotkey_id, 0x4000, vk):
                    raise OSError(ctypes.get_last_error(), f"Could not register {key}")
                registrations[hotkey_id] = (key, action_id)
            message = wintypes.MSG()
            while (
                not self._stop.is_set()
                and user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0
            ):
                if message.message == 0x0312 and int(message.wParam) in registrations:
                    key, action_id = registrations[int(message.wParam)]
                    count, triggered = self.detector.register_press(key)
                    self.callback(key, action_id, count, triggered)
        finally:
            for hotkey_id in registrations:
                user32.UnregisterHotKey(None, hotkey_id)
