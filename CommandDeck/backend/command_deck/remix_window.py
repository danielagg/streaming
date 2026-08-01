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
    target_bounds: tuple[int, int, int, int] | None = None,
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
    if target_bounds is not None:
        _move_to_display(window, target_bounds)
    mode_x, mode_y = _scaled_point(MODE_BUTTON, ui_scale)
    preview_x, preview_y = _scaled_point(PREVIEW_MENU_ITEM, ui_scale)

    _post_click(window, mode_x, mode_y)
    time.sleep(0.25)
    _post_click(window, preview_x, preview_y)
    time.sleep(0.35)


def _scaled_point(point: tuple[int, int], scale: float) -> tuple[int, int]:
    return round(point[0] * scale), round(point[1] * scale)


def _centered_origin(
    window_size: tuple[int, int],
    display_bounds: tuple[int, int, int, int],
) -> tuple[int, int]:
    window_width, window_height = window_size
    x, y, display_width, display_height = display_bounds
    return (
        x + max(0, (display_width - window_width) // 2),
        y + max(0, (display_height - window_height) // 2),
    )


def _move_to_display(
    window: int, display_bounds: tuple[int, int, int, int]
) -> None:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    rectangle = wintypes.RECT()
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    if not user32.GetWindowRect(window, ctypes.byref(rectangle)):
        raise RemixWindowControlError("Could not measure the PNGTuber Remix window.")
    origin = _centered_origin(
        (rectangle.right - rectangle.left, rectangle.bottom - rectangle.top),
        display_bounds,
    )
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    no_size_or_focus = 0x0001 | 0x0004 | 0x0010
    if not user32.SetWindowPos(
        window,
        0,
        origin[0],
        origin[1],
        0,
        0,
        no_size_or_focus,
    ):
        raise RemixWindowControlError("Could not move PNGTuber Remix to the target display.")


def _wait_for_main_window(process_id: int, timeout_seconds: float) -> int:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        window = _find_main_window(process_id)
        if window:
            return window
        time.sleep(0.1)
    raise RemixWindowControlError("Could not find the PNGTuber Remix window.")


def _find_main_window(process_id: int) -> int:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    windows: list[int] = []

    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
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
        user32.GetWindowThreadProcessId(window, ctypes.byref(window_process_id))
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
        raise RemixWindowControlError("Could not send a click to PNGTuber Remix.")
    if not user32.PostMessageW(
        window,
        WM_LBUTTONUP,
        0,
        packed_coordinates,
    ):
        raise RemixWindowControlError("Could not complete a click in PNGTuber Remix.")
