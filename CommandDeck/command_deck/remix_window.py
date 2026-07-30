from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes


class RemixWindowControlError(RuntimeError):
    pass


WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001

MODE_BUTTON = (61, 16)
PREVIEW_MENU_ITEM = (88, 74)


def select_preview_mode(
    process_id: int,
    *,
    ui_scale: float = 1.0,
    timeout_seconds: float = 5.0,
) -> None:
    if sys.platform != "win32":
        raise RemixWindowControlError(
            "Preview mode automation is only available on Windows."
        )
    if process_id <= 0:
        raise RemixWindowControlError(
            "PNGTuber Remix did not report a valid process ID."
        )
    if not 0.5 <= ui_scale <= 3.0:
        raise RemixWindowControlError(
            f"Remix reported an unsupported UI scale: {ui_scale:g}."
        )

    window = _wait_for_main_window(process_id, timeout_seconds)
    mode_x, mode_y = _scaled_point(MODE_BUTTON, ui_scale)
    preview_x, preview_y = _scaled_point(PREVIEW_MENU_ITEM, ui_scale)

    _post_click(window, mode_x, mode_y)
    time.sleep(0.25)
    _post_click(window, preview_x, preview_y)
    time.sleep(0.35)


def _scaled_point(point: tuple[int, int], scale: float) -> tuple[int, int]:
    return round(point[0] * scale), round(point[1] * scale)


def _wait_for_main_window(
    process_id: int, timeout_seconds: float
) -> int:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        window = _find_main_window(process_id)
        if window:
            return window
        time.sleep(0.1)
    raise RemixWindowControlError(
        "Could not find the PNGTuber Remix window."
    )


def _find_main_window(process_id: int) -> int:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    windows: list[int] = []

    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int

    @callback_type
    def visit_window(window: int, _parameter: int) -> bool:
        window_process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(
            window, ctypes.byref(window_process_id)
        )
        if (
            window_process_id.value == process_id
            and user32.IsWindowVisible(window)
            and user32.GetWindowTextLengthW(window) > 0
        ):
            windows.append(window)
            return False
        return True

    user32.EnumWindows(visit_window, 0)
    return windows[0] if windows else 0


def _post_click(window: int, x: int, y: int) -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.PostMessageW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.PostMessageW.restype = wintypes.BOOL
    packed_coordinates = (y << 16) | (x & 0xFFFF)
    if not user32.PostMessageW(
        window,
        WM_LBUTTONDOWN,
        MK_LBUTTON,
        packed_coordinates,
    ):
        raise RemixWindowControlError(
            "Could not send a click to PNGTuber Remix."
        )
    if not user32.PostMessageW(
        window,
        WM_LBUTTONUP,
        0,
        packed_coordinates,
    ):
        raise RemixWindowControlError(
            "Could not complete a click in PNGTuber Remix."
        )
