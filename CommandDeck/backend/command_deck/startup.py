from __future__ import annotations

import ctypes
import os
import struct
import subprocess
from ctypes import wintypes
from pathlib import Path

from .config import AppConfig

GODOT_STRING_VARIANT = 21
GODOT_BOOL_VARIANT = 1
GODOT_INT_VARIANT = 2
GODOT_FLOAT_VARIANT = 3


def _is_process_running(executable: Path) -> bool:
    """Return whether Windows already has a process with this executable name."""
    if os.name != "nt":
        return False

    class ProcessEntry32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_snapshot = kernel32.CreateToolhelp32Snapshot
    create_snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    create_snapshot.restype = wintypes.HANDLE
    process_first = kernel32.Process32FirstW
    process_first.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry32W)]
    process_first.restype = wintypes.BOOL
    process_next = kernel32.Process32NextW
    process_next.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry32W)]
    process_next.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    snapshot = create_snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    entry = ProcessEntry32W()
    entry.dwSize = ctypes.sizeof(entry)
    expected_name = executable.name.casefold()
    try:
        has_entry = process_first(snapshot, ctypes.byref(entry))
        while has_entry:
            if entry.szExeFile.casefold() == expected_name:
                return True
            has_entry = process_next(snapshot, ctypes.byref(entry))
        error = ctypes.get_last_error()
        if error != 18:  # ERROR_NO_MORE_FILES
            raise ctypes.WinError(error)
        return False
    finally:
        close_handle(snapshot)


def _signature(key: str, value_type: int) -> bytes:
    encoded = key.encode()
    return (
        struct.pack("<II", GODOT_STRING_VARIANT, len(encoded))
        + encoded
        + b"\0" * (-len(encoded) % 4)
        + struct.pack("<I", value_type)
    )


def enforce_scalar(
    path: Path, key: str, value_type: int, required: int, allowed: set[int]
) -> bool:
    data = bytearray(path.read_bytes())
    signature = _signature(key, value_type)
    positions = []
    start = 0
    while (position := data.find(signature, start)) >= 0:
        positions.append(position)
        start = position + 1
    if len(positions) != 1:
        raise RuntimeError(
            f"Expected one '{key}' setting in {path.name}, found {len(positions)}."
        )
    offset = positions[0] + len(signature)
    current = struct.unpack_from("<i", data, offset)[0]
    if current not in allowed:
        raise RuntimeError(f"Unexpected '{key}' value {current}.")
    if current == required:
        return False
    struct.pack_into("<i", data, offset, required)
    temporary = path.with_name(f".{path.name}.command-deck-{os.getpid()}.tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def read_float32(path: Path, key: str) -> float:
    data = path.read_bytes()
    signature = _signature(key, GODOT_FLOAT_VARIANT)
    positions: list[int] = []
    start = 0
    while (position := data.find(signature, start)) >= 0:
        positions.append(position)
        start = position + 1
    if len(positions) != 1:
        raise RuntimeError(
            f"Expected one '{key}' setting in {path.name}, found {len(positions)}."
        )
    offset = positions[0] + len(signature)
    if offset + 4 > len(data):
        raise RuntimeError(f"The '{key}' setting in {path.name} is incomplete.")
    return struct.unpack_from("<f", data, offset)[0]


def launch_remix(config: AppConfig) -> subprocess.Popen[bytes] | None:
    if not config.auto_launch_remix:
        return None
    executable, model = config.remix_executable_path, config.remix_model_path
    if executable is None:
        raise FileNotFoundError(f"PNGTuber Remix was not found: {executable}")
    if _is_process_running(executable):
        return None
    if not executable.is_file():
        raise FileNotFoundError(f"PNGTuber Remix was not found: {executable}")
    if model is None or not model.is_file():
        raise FileNotFoundError(f"Remix model was not found: {model}")
    preferences = executable.parent / "Preferences.pRDat"
    if config.force_remix_preview:
        enforce_scalar(preferences, "mode", GODOT_INT_VARIANT, 1, {0, 1, 2})
    if config.force_transparent_background:
        enforce_scalar(model, "is_transparent", GODOT_BOOL_VARIANT, 1, {0, 1})
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return subprocess.Popen(
        [str(executable), str(model)],
        cwd=executable.parent,
        close_fds=True,
        creationflags=flags,
    )


def launch_obs(config: AppConfig) -> subprocess.Popen[bytes] | None:
    if not config.obs.enabled or not config.obs.auto_launch:
        return None
    executable = config.obs.executable_path
    if executable is None:
        raise FileNotFoundError(f"OBS Studio was not found: {executable}")
    if _is_process_running(executable):
        return None
    if not executable.is_file():
        raise FileNotFoundError(f"OBS Studio was not found: {executable}")
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return subprocess.Popen(
        [str(executable)],
        cwd=executable.parent,
        close_fds=True,
        creationflags=flags,
    )
