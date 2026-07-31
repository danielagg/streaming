import struct

import pytest

from command_deck.remix_window import _scaled_point
from command_deck.startup import GODOT_FLOAT_VARIANT, _signature, read_float32


def test_preview_click_coordinates_follow_ui_scale():
    assert _scaled_point((61, 16), 1.5) == (92, 24)
    assert _scaled_point((88, 74), 1.5) == (132, 111)


def test_read_float32_reads_remix_ui_scale(tmp_path):
    preferences = tmp_path / "Preferences.pRDat"
    preferences.write_bytes(
        b"prefix"
        + _signature("ui_scaling", GODOT_FLOAT_VARIANT)
        + struct.pack("<f", 1.25)
        + b"suffix"
    )

    assert read_float32(preferences, "ui_scaling") == pytest.approx(1.25)
