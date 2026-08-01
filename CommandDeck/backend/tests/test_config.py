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
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.actions[0].state_name == "Croaking"
    assert config.actions[0].audio_path == (tmp_path / "sound.mp3").resolve()


def test_rejects_duplicate_action_ids(tmp_path):
    path = tmp_path / "config.json"
    action = {"id": "same", "name": "Same", "stateName": "Same", "durationMs": 1}
    path.write_text(json.dumps({"actions": [action, action]}))
    with pytest.raises(ValueError, match="unique"):
        load_config(path)
