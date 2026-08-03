import struct
import sys

import pytest

from command_deck import remix_window
from command_deck.remix_window import _centered_origin, _scaled_point
from command_deck.startup import GODOT_FLOAT_VARIANT, _signature, read_float32


def test_preview_click_coordinates_follow_ui_scale():
    assert _scaled_point((61, 16), 1.5) == (92, 24)
    assert _scaled_point((88, 74), 1.5) == (132, 111)


def test_window_is_centered_inside_target_display():
    assert _centered_origin((800, 600), (1920, 0, 1080, 1920)) == (2060, 660)
    assert _centered_origin((1200, 2000), (-1080, 0, 1080, 1920)) == (-1080, 0)


def test_preview_selection_retries_after_display_move(monkeypatch):
    moves = []
    clicks = []
    sleeps = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(remix_window, "_wait_for_main_window", lambda *_args: 123)
    monkeypatch.setattr(
        remix_window,
        "_move_to_display",
        lambda window, bounds: moves.append((window, bounds)),
    )
    monkeypatch.setattr(
        remix_window,
        "_post_click",
        lambda window, x, y: clicks.append((window, x, y)),
    )
    monkeypatch.setattr(remix_window.time, "sleep", sleeps.append)

    remix_window.select_preview_mode(
        42,
        ui_scale=1.5,
        target_bounds=(0, 0, 1920, 1080),
        attempts=2,
    )

    assert moves == [(123, (0, 0, 1920, 1080))]
    assert clicks == [
        (123, 92, 24),
        (123, 132, 111),
        (123, 92, 24),
        (123, 132, 111),
    ]
    assert sleeps == [0.25, 0.3, 0.35, 0.3, 0.35]


def test_read_float32_reads_remix_ui_scale(tmp_path):
    preferences = tmp_path / "Preferences.pRDat"
    preferences.write_bytes(
        b"prefix"
        + _signature("ui_scaling", GODOT_FLOAT_VARIANT)
        + struct.pack("<f", 1.25)
        + b"suffix"
    )

    assert read_float32(preferences, "ui_scaling") == pytest.approx(1.25)
