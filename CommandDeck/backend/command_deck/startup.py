from __future__ import annotations

import os
import struct
import subprocess
from pathlib import Path

from .config import AppConfig

GODOT_STRING_VARIANT = 21
GODOT_BOOL_VARIANT = 1
GODOT_INT_VARIANT = 2
GODOT_FLOAT_VARIANT = 3


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
    if executable is None or not executable.is_file():
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
