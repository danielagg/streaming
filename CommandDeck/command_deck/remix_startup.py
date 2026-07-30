from __future__ import annotations

import os
import struct
from pathlib import Path


class RemixStartupSettingsError(RuntimeError):
    pass


GODOT_STRING_VARIANT = 21
GODOT_BOOL_VARIANT = 1
GODOT_INT_VARIANT = 2
GODOT_FLOAT_VARIANT = 3


def _field_signature(key: str, value_type: int) -> bytes:
    encoded_key = key.encode("utf-8")
    padding = b"\0" * (-len(encoded_key) % 4)
    return (
        struct.pack("<II", GODOT_STRING_VARIANT, len(encoded_key))
        + encoded_key
        + padding
        + struct.pack("<I", value_type)
    )


def read_scalar(path: Path, key: str, value_type: int) -> int:
    data = path.read_bytes()
    signature = _field_signature(key, value_type)
    positions = _find_all(data, signature)
    if len(positions) != 1:
        raise RemixStartupSettingsError(
            f"Expected one '{key}' setting in {path.name}, found "
            f"{len(positions)}."
        )

    value_offset = positions[0] + len(signature)
    if value_offset + 4 > len(data):
        raise RemixStartupSettingsError(
            f"The '{key}' setting in {path.name} is incomplete."
        )
    return struct.unpack_from("<i", data, value_offset)[0]


def read_float32(path: Path, key: str) -> float:
    data = path.read_bytes()
    signature = _field_signature(key, GODOT_FLOAT_VARIANT)
    positions = _find_all(data, signature)
    if len(positions) != 1:
        raise RemixStartupSettingsError(
            f"Expected one '{key}' setting in {path.name}, found "
            f"{len(positions)}."
        )

    value_offset = positions[0] + len(signature)
    if value_offset + 4 > len(data):
        raise RemixStartupSettingsError(
            f"The '{key}' setting in {path.name} is incomplete."
        )
    return struct.unpack_from("<f", data, value_offset)[0]


def enforce_scalar(
    path: Path,
    key: str,
    value_type: int,
    required_value: int,
    *,
    allowed_values: set[int],
) -> bool:
    if not path.is_file():
        raise RemixStartupSettingsError(f"Settings file was not found: {path}")

    data = bytearray(path.read_bytes())
    signature = _field_signature(key, value_type)
    positions = _find_all(data, signature)
    if len(positions) != 1:
        raise RemixStartupSettingsError(
            f"Expected one '{key}' setting in {path.name}, found "
            f"{len(positions)}."
        )

    value_offset = positions[0] + len(signature)
    if value_offset + 4 > len(data):
        raise RemixStartupSettingsError(
            f"The '{key}' setting in {path.name} is incomplete."
        )

    current_value = struct.unpack_from("<i", data, value_offset)[0]
    if current_value not in allowed_values:
        raise RemixStartupSettingsError(
            f"The '{key}' setting in {path.name} has unexpected value "
            f"{current_value}."
        )
    if current_value == required_value:
        return False

    struct.pack_into("<i", data, value_offset, required_value)
    _atomic_write(path, data)
    return True


def enforce_remix_startup(
    *,
    preferences_path: Path,
    model_path: Path,
    preview: bool,
    transparent: bool,
) -> tuple[str, ...]:
    changes: list[str] = []
    if preview and enforce_scalar(
        preferences_path,
        "mode",
        GODOT_INT_VARIANT,
        1,
        allowed_values={0, 1, 2},
    ):
        changes.append("Preview mode")

    if transparent and enforce_scalar(
        model_path,
        "is_transparent",
        GODOT_BOOL_VARIANT,
        1,
        allowed_values={0, 1},
    ):
        changes.append("transparent background")

    return tuple(changes)


def _find_all(data: bytes | bytearray, needle: bytes) -> list[int]:
    positions: list[int] = []
    offset = 0
    while True:
        position = data.find(needle, offset)
        if position < 0:
            return positions
        positions.append(position)
        offset = position + 1


def _atomic_write(path: Path, data: bytes | bytearray) -> None:
    temporary_path = path.with_name(
        f".{path.name}.command-deck-{os.getpid()}.tmp"
    )
    try:
        with temporary_path.open("wb") as temporary_file:
            temporary_file.write(data)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
