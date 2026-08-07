import json

import pytest

from command_deck.config import load_config


def test_loads_root_camel_case_config(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "appName": "Command Deck",
                "remix": {"websocketUrl": "ws://127.0.0.1:9321", "autoLaunch": False},
                "actions": [
                    {
                        "id": "croak",
                        "name": "Croak",
                        "stateName": "Croaking",
                        "durationMs": 10,
                        "audioPath": "sound.mp3",
                        "bounce": {
                            "spriteName": "Berry",
                            "height": 180,
                            "durationMs": 750,
                            "delayMs": 150,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.actions[0].state_name == "Croaking"
    assert config.actions[0].audio_path == (tmp_path / "sound.mp3").resolve()
    assert config.actions[0].bounce is not None
    assert config.actions[0].bounce.sprite_name == "Berry"
    assert config.actions[0].bounce.height == 180
    assert config.actions[0].bounce.duration_ms == 750
    assert config.actions[0].bounce.delay_ms == 150


def test_rejects_duplicate_action_ids(tmp_path):
    path = tmp_path / "config.json"
    action = {"id": "same", "name": "Same", "stateName": "Same", "durationMs": 1}
    path.write_text(json.dumps({"actions": [action, action]}))
    with pytest.raises(ValueError, match="unique"):
        load_config(path)


def test_loads_obs_scene_and_music_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("COMMAND_DECK_OBS_PASSWORD", "local-secret")
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "actions": [
                    {"id": "croak", "name": "Croak", "stateName": "Croaking", "durationMs": 1}
                ],
                "obs": {
                    "enabled": True,
                    "autoLaunch": True,
                    "executablePath": "OBS Studio/bin/64bit/obs64.exe",
                    "scenes": [
                        {"id": "main", "name": "Main (screen share)", "label": "Main"}
                    ],
                    "musicInput": "StartingSoon Music",
                    "musicTailMs": 30000,
                    "musicFadeMs": 5000,
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.obs.enabled is True
    assert config.obs.auto_launch is True
    assert config.obs.executable_path == (
        tmp_path / "OBS Studio/bin/64bit/obs64.exe"
    ).resolve()
    assert config.obs.password == "local-secret"
    assert config.obs.scenes[0].name == "Main (screen share)"
    assert config.obs.music_input == "StartingSoon Music"
