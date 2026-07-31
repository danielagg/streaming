from __future__ import annotations

import json
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
class HotkeyConfig:
    enabled: bool = True
    presses_required: int = 3
    press_window_ms: int = 1200
    bindings: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TwitchConfig:
    enabled: bool = False
    client_id: str | None = None
    broadcaster_id: str | None = None
    token_path: Path | None = None


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
    global_hotkeys: HotkeyConfig | None = None
    twitch: TwitchConfig = field(default_factory=TwitchConfig)


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
        global_hotkeys=HotkeyConfig(
            bindings={"F13": "whiskey", "F14": "croak", "F15": "fly"}
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
    hot_raw = raw.get("global_hotkeys", raw.get("globalHotkeys"))
    hotkeys = None
    if hot_raw is not None:
        hotkeys = HotkeyConfig(
            enabled=bool(hot_raw.get("enabled", True)),
            presses_required=int(
                hot_raw.get("presses_required", hot_raw.get("pressesRequired", 3))
            ),
            press_window_ms=int(
                hot_raw.get("press_window_ms", hot_raw.get("pressWindowMs", 1200))
            ),
            bindings={
                str(key).upper(): str(value)
                for key, value in hot_raw.get("bindings", {}).items()
            }
            or {
                str(item["hotkey"]).upper(): str(item["id"])
                for item in raw.get("actions", [])
                if item.get("hotkey")
            },
        )
        if hotkeys.presses_required < 1 or hotkeys.press_window_ms < 1:
            raise ValueError("Hotkey press count and window must be positive.")
        valid_ids = {action.id for action in actions}
        if set(hotkeys.bindings.values()) - valid_ids:
            raise ValueError("A hotkey references an unknown action.")
        if set(hotkeys.bindings) - {f"F{i}" for i in range(13, 25)}:
            raise ValueError("Only F13 through F24 are supported global hotkeys.")
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
        global_hotkeys=hotkeys,
        twitch=twitch,
    )
