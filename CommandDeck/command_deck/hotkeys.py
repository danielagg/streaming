from __future__ import annotations

import ctypes
import threading
import time
from collections.abc import Callable, Mapping
from ctypes import wintypes


WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_NOREPEAT = 0x4000
PM_NOREMOVE = 0x0000
VK_BY_KEY = {
    f"F{number}": 0x70 + number - 1
    for number in range(13, 25)
}


class HotkeyRegistrationError(RuntimeError):
    pass


class MultiPressDetector:
    def __init__(
        self,
        *,
        presses_required: int,
        press_window_seconds: float,
    ) -> None:
        if presses_required < 1:
            raise ValueError("presses_required must be at least 1.")
        if press_window_seconds <= 0:
            raise ValueError("press_window_seconds must be positive.")
        self.presses_required = presses_required
        self.press_window_seconds = press_window_seconds
        self._press_times: dict[str, list[float]] = {}

    def register_press(
        self,
        key: str,
        *,
        now: float | None = None,
    ) -> tuple[int, bool]:
        pressed_at = time.monotonic() if now is None else now
        cutoff = pressed_at - self.press_window_seconds
        recent = [
            timestamp
            for timestamp in self._press_times.get(key, [])
            if timestamp >= cutoff
        ]
        recent.append(pressed_at)
        count = len(recent)
        triggered = count >= self.presses_required
        if triggered:
            self._press_times.pop(key, None)
        else:
            self._press_times[key] = recent
        return count, triggered


class GlobalHotkeyListener:
    def __init__(
        self,
        bindings: Mapping[str, str],
        callback: Callable[[str, str, int, bool], None],
        *,
        presses_required: int,
        press_window_ms: int,
    ) -> None:
        normalized = {
            key.upper(): action_id
            for key, action_id in bindings.items()
        }
        unsupported = sorted(set(normalized) - set(VK_BY_KEY))
        if unsupported:
            raise ValueError(
                f"Unsupported global hotkey(s): {', '.join(unsupported)}"
            )
        if not normalized:
            raise ValueError("At least one global hotkey is required.")

        self.bindings = normalized
        self.callback = callback
        self.detector = MultiPressDetector(
            presses_required=presses_required,
            press_window_seconds=press_window_ms / 1000,
        )
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._start_error: Exception | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._ready.clear()
        self._start_error = None
        self._thread = threading.Thread(
            target=self._message_loop,
            name="command-deck-hotkeys",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=2):
            raise HotkeyRegistrationError(
                "Windows did not initialize the global hotkeys in time."
            )
        if self._start_error is not None:
            raise HotkeyRegistrationError(str(self._start_error))

    def stop(self) -> None:
        thread = self._thread
        thread_id = self._thread_id
        if thread is None:
            return
        if thread.is_alive() and thread_id is not None:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.PostThreadMessageW(
                thread_id,
                WM_QUIT,
                0,
                0,
            )
            thread.join(timeout=1)
        self._thread = None
        self._thread_id = None

    def _message_loop(self) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32.RegisterHotKey.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            wintypes.UINT,
            wintypes.UINT,
        ]
        user32.RegisterHotKey.restype = wintypes.BOOL
        user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.UnregisterHotKey.restype = wintypes.BOOL
        user32.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ]
        user32.GetMessageW.restype = wintypes.BOOL
        user32.PeekMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
            wintypes.UINT,
        ]
        user32.PeekMessageW.restype = wintypes.BOOL
        kernel32.GetCurrentThreadId.argtypes = []
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD

        message = wintypes.MSG()
        self._thread_id = int(kernel32.GetCurrentThreadId())
        user32.PeekMessageW(
            ctypes.byref(message),
            None,
            0,
            0,
            PM_NOREMOVE,
        )

        registrations: dict[int, tuple[str, str]] = {}
        try:
            for offset, (key, action_id) in enumerate(
                self.bindings.items()
            ):
                hotkey_id = 0x6D00 + offset
                registered = user32.RegisterHotKey(
                    None,
                    hotkey_id,
                    MOD_NOREPEAT,
                    VK_BY_KEY[key],
                )
                if not registered:
                    error_code = ctypes.get_last_error()
                    raise OSError(
                        error_code,
                        f"Windows could not register {key}. "
                        "Another app may already be using it.",
                    )
                registrations[hotkey_id] = (key, action_id)
            self._ready.set()

            while True:
                result = user32.GetMessageW(
                    ctypes.byref(message),
                    None,
                    0,
                    0,
                )
                if result == 0:
                    break
                if result == -1:
                    raise ctypes.WinError(ctypes.get_last_error())
                if message.message != WM_HOTKEY:
                    continue

                binding = registrations.get(int(message.wParam))
                if binding is None:
                    continue
                key, action_id = binding
                count, triggered = self.detector.register_press(key)
                self.callback(
                    key,
                    action_id,
                    count,
                    triggered,
                )
        except Exception as error:
            self._start_error = error
            self._ready.set()
        finally:
            for hotkey_id in registrations:
                user32.UnregisterHotKey(None, hotkey_id)
            self._ready.set()
