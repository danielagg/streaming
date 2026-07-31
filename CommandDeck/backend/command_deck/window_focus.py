from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


def focus_process_window(process_id: int, *, title: str | None = None) -> None:
    """Bring a visible top-level window owned by process_id to the foreground."""
    if os.name != "nt":
        return
    if process_id <= 0:
        raise ValueError("A valid process ID is required to restore window focus.")

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.AttachThreadInput.argtypes = [
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.BOOL,
    ]
    user32.AttachThreadInput.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.SetActiveWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetFocus.argtypes = [wintypes.HWND]
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD

    hwnd = _find_window(user32, process_id, title)
    if not hwnd:
        raise RuntimeError(f"No visible window found for process {process_id}.")

    foreground = user32.GetForegroundWindow()
    current_thread = kernel32.GetCurrentThreadId()
    foreground_thread = (
        user32.GetWindowThreadProcessId(foreground, None) if foreground else 0
    )
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)
    attached_threads: list[int] = []

    try:
        for thread_id in {foreground_thread, target_thread}:
            if (
                thread_id
                and thread_id != current_thread
                and user32.AttachThreadInput(current_thread, thread_id, True)
            ):
                attached_threads.append(thread_id)

        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.BringWindowToTop(hwnd)
        user32.SetActiveWindow(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)

        if user32.GetForegroundWindow() != hwnd:
            no_move_or_size = 0x0001 | 0x0002
            user32.SetWindowPos(
                hwnd, wintypes.HWND(-1), 0, 0, 0, 0, no_move_or_size
            )
            user32.SetWindowPos(
                hwnd, wintypes.HWND(-2), 0, 0, 0, 0, no_move_or_size
            )
            user32.SetForegroundWindow(hwnd)

        if user32.GetForegroundWindow() != hwnd:
            raise RuntimeError("Windows refused to return focus to Command Deck.")
    finally:
        for thread_id in reversed(attached_threads):
            user32.AttachThreadInput(current_thread, thread_id, False)


def _find_window(user32: ctypes.WinDLL, process_id: int, title: str | None) -> int:
    matches: list[int] = []
    enum_callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [
        wintypes.HWND,
        wintypes.LPWSTR,
        ctypes.c_int,
    ]
    user32.EnumWindows.argtypes = [enum_callback, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL

    def visit(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        owner_process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_process_id))
        if owner_process_id.value != process_id:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        if title is None or title.casefold() in buffer.value.casefold():
            matches.append(hwnd)
            return False
        return True

    user32.EnumWindows(enum_callback(visit), 0)
    return matches[0] if matches else 0
