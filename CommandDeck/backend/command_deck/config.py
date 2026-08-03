from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    id: str
    name: str
    state_name: str
    duration_ms: int
    number: str = ""
    description: str = ""
    accent: str = "#ffffff"
    audio_path: Path | None = None


@dataclass(frozen=True, slots=True)
class TwitchConfig:
    enabled: bool = False
    client_id: str | None = None
    broadcaster_id: str | None = None
    token_path: Path | None = None


@dataclass(frozen=True, slots=True)
class ObsSceneDefinition:
    id: str
    name: str
    label: str
    accent: str = "#83e8ee"


@dataclass(frozen=True, slots=True)
class ObsConfig:
    enabled: bool = False
    websocket_url: str = "ws://127.0.0.1:4455"
    auto_launch: bool = False
    executable_path: Path | None = None
    password: str | None = None
    scenes: tuple[ObsSceneDefinition, ...] = ()
    starting_soon_scene: str = "Starting Soon"
    main_scene: str = "Main (screen share)"
    brb_scene: str = "BRB"
    music_input: str = "StartingSoon Music"
    music_tail_ms: int = 30_000
    music_fade_ms: int = 5_000


@dataclass(frozen=True, slots=True)
class AppConfig:
    app_name: str
    remix_websocket_url: str
    actions: tuple[ActionDefinition, ...]
    auto_launch_remix: bool = False
    force_remix_preview: bool = False
    force_transparent_background: bool = False
    remix_executable_path: Path | None = None
    remix_model_path: Path | None = None
    twitch: TwitchConfig = field(default_factory=TwitchConfig)
    obs: ObsConfig = field(default_factory=ObsConfig)


def default_config() -> AppConfig:
    return AppConfig(
        app_name="Command Deck",
        remix_websocket_url="ws://127.0.0.1:9321",
        actions=(
            ActionDefinition(
                "whiskey",
                "Whiskey Sip",
                "Whiskey Sip",
                2000,
                "01",
                "A measured two-second toast.",
                "#D5A653",
            ),
            ActionDefinition(
                "croak",
                "Croak Twice",
                "Croaking",
                3000,
                "02",
                "Two synchronized calls with audio.",
                "#8EBB74",
            ),
            ActionDefinition(
                "fly",
                "Fly Catch",
                "Fly Catch",
                1400,
                "03",
                "Fast tongue strike and recovery.",
                "#D96D91",
            ),
        ),
    )


def _path(base: Path, value: Any) -> Path | None:
    return (base / str(value)).resolve() if value else None


def load_config(path: Path | None) -> AppConfig:
    if path is None:
        return default_config()
    raw = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    actions = tuple(
        ActionDefinition(
            id=str(item["id"]),
            name=str(item["name"]),
            state_name=str(item.get("state_name", item.get("stateName"))),
            duration_ms=int(item.get("duration_ms", item.get("durationMs"))),
            number=str(item.get("number", "")),
            description=str(item.get("description", "")),
            accent=str(item.get("accent", "#ffffff")),
            audio_path=_path(base, item.get("audio_path", item.get("audioPath"))),
        )
        for item in raw.get("actions", [])
    )
    if not actions:
        raise ValueError("Command Deck needs at least one configured action.")
    if len({action.id for action in actions}) != len(actions):
        raise ValueError("Action ids must be unique.")
    twitch_raw = raw.get("twitch", {})
    twitch = TwitchConfig(
        enabled=bool(twitch_raw.get("enabled", False)),
        client_id=twitch_raw.get("client_id", twitch_raw.get("clientId")),
        broadcaster_id=twitch_raw.get(
            "broadcaster_id", twitch_raw.get("broadcasterId")
        ),
        token_path=_path(
            base, twitch_raw.get("token_path", twitch_raw.get("tokenPath"))
        ),
    )
    obs_raw = raw.get("obs", {})
    obs_scenes = tuple(
        ObsSceneDefinition(
            id=str(item["id"]),
            name=str(item["name"]),
            label=str(item.get("label", item["name"])),
            accent=str(item.get("accent", "#83e8ee")),
        )
        for item in obs_raw.get("scenes", [])
    )
    if len({scene.id for scene in obs_scenes}) != len(obs_scenes):
        raise ValueError("OBS scene ids must be unique.")
    if len({scene.name for scene in obs_scenes}) != len(obs_scenes):
        raise ValueError("OBS scene names must be unique.")
    password = os.environ.get("COMMAND_DECK_OBS_PASSWORD") or obs_raw.get("password")
    password_path = _path(base, obs_raw.get("passwordPath"))
    default_password_path = base / "obs-password.txt"
    if password_path is None and default_password_path.is_file():
        password_path = default_password_path
    if not password and password_path is not None:
        password = password_path.read_text(encoding="utf-8").strip() or None
    music_tail_ms = int(obs_raw.get("musicTailMs", 30_000))
    music_fade_ms = int(obs_raw.get("musicFadeMs", 5_000))
    if music_tail_ms < 0:
        raise ValueError("OBS music tail duration cannot be negative.")
    if music_fade_ms < 0 or music_fade_ms > music_tail_ms:
        raise ValueError("OBS music fade must fit inside the music tail.")
    obs = ObsConfig(
        enabled=bool(obs_raw.get("enabled", False)),
        websocket_url=str(obs_raw.get("websocketUrl", "ws://127.0.0.1:4455")),
        auto_launch=bool(obs_raw.get("autoLaunch", False)),
        executable_path=_path(base, obs_raw.get("executablePath")),
        password=str(password) if password else None,
        scenes=obs_scenes,
        starting_soon_scene=str(
            obs_raw.get("startingSoonScene", "Starting Soon")
        ),
        main_scene=str(obs_raw.get("mainScene", "Main (screen share)")),
        brb_scene=str(obs_raw.get("brbScene", "BRB")),
        music_input=str(obs_raw.get("musicInput", "StartingSoon Music")),
        music_tail_ms=music_tail_ms,
        music_fade_ms=music_fade_ms,
    )
    remix_raw = raw.get("remix", {})
    return AppConfig(
        app_name=str(raw.get("app_name", raw.get("appName", "Command Deck"))),
        remix_websocket_url=str(
            raw.get(
                "remix_websocket_url",
                raw.get(
                    "websocket_url",
                    remix_raw.get("websocketUrl", "ws://127.0.0.1:9321"),
                ),
            )
        ),
        actions=actions,
        auto_launch_remix=bool(
            raw.get("auto_launch_remix", remix_raw.get("autoLaunch", False))
        ),
        force_remix_preview=bool(
            raw.get("force_remix_preview", remix_raw.get("forcePreview", False))
        ),
        force_transparent_background=bool(
            raw.get(
                "force_transparent_background",
                remix_raw.get("forceTransparentBackground", False),
            )
        ),
        remix_executable_path=_path(
            base, raw.get("remix_executable_path", remix_raw.get("executablePath"))
        ),
        remix_model_path=_path(
            base, raw.get("remix_model_path", remix_raw.get("modelPath"))
        ),
        twitch=twitch,
        obs=obs,
    )
