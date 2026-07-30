from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    id: str
    number: str
    name: str
    state_name: str
    description: str
    duration_ms: int
    accent: str
    audio_path: Path | None = None


@dataclass(frozen=True, slots=True)
class HotkeyBinding:
    key: str
    action_id: str


@dataclass(frozen=True, slots=True)
class GlobalHotkeyConfig:
    enabled: bool
    presses_required: int
    press_window_ms: int
    bindings: tuple[HotkeyBinding, ...]


@dataclass(frozen=True, slots=True)
class AppConfig:
    app_name: str
    websocket_url: str
    auto_launch_remix: bool
    force_remix_preview: bool
    force_transparent_background: bool
    remix_executable_path: Path | None
    remix_model_path: Path | None
    actions: tuple[ActionDefinition, ...]
    global_hotkeys: GlobalHotkeyConfig | None = None


def load_config(config_path: Path) -> AppConfig:
    with config_path.open("r", encoding="utf-8") as config_file:
        raw = json.load(config_file)

    base_directory = config_path.parent
    actions: list[ActionDefinition] = []
    for item in raw["actions"]:
        audio_value = item.get("audio_path")
        audio_path = (
            (base_directory / audio_value).resolve() if audio_value else None
        )
        actions.append(
            ActionDefinition(
                id=item["id"],
                number=item["number"],
                name=item["name"],
                state_name=item["state_name"],
                description=item["description"],
                duration_ms=int(item["duration_ms"]),
                accent=item["accent"],
                audio_path=audio_path,
            )
        )

    if not actions:
        raise ValueError("Command Deck needs at least one configured action.")

    hotkey_config: GlobalHotkeyConfig | None = None
    hotkey_value = raw.get("global_hotkeys")
    if hotkey_value is not None:
        presses_required = int(hotkey_value.get("presses_required", 3))
        press_window_ms = int(hotkey_value.get("press_window_ms", 1200))
        if presses_required < 1:
            raise ValueError("global_hotkeys.presses_required must be at least 1.")
        if press_window_ms < 1:
            raise ValueError("global_hotkeys.press_window_ms must be positive.")

        action_ids = {action.id for action in actions}
        bindings = tuple(
            HotkeyBinding(
                key=str(key).upper(),
                action_id=str(action_id),
            )
            for key, action_id in hotkey_value.get("bindings", {}).items()
        )
        unsupported_keys = sorted(
            binding.key
            for binding in bindings
            if binding.key not in {f"F{number}" for number in range(13, 25)}
        )
        if unsupported_keys:
            raise ValueError(
                "Unsupported global hotkey(s): "
                + ", ".join(unsupported_keys)
            )
        missing_actions = sorted(
            binding.action_id
            for binding in bindings
            if binding.action_id not in action_ids
        )
        if missing_actions:
            raise ValueError(
                "Global hotkey action(s) not found: "
                + ", ".join(missing_actions)
            )
        if bool(hotkey_value.get("enabled", False)) and not bindings:
            raise ValueError(
                "Enabled global hotkeys need at least one binding."
            )
        hotkey_config = GlobalHotkeyConfig(
            enabled=bool(hotkey_value.get("enabled", False)),
            presses_required=presses_required,
            press_window_ms=press_window_ms,
            bindings=bindings,
        )

    executable_value = raw.get("remix_executable_path")
    remix_executable_path = (
        (base_directory / executable_value).resolve()
        if executable_value
        else None
    )
    model_value = raw.get("remix_model_path")
    remix_model_path = (
        (base_directory / model_value).resolve() if model_value else None
    )

    return AppConfig(
        app_name=raw.get("app_name", "Command Deck"),
        websocket_url=raw["websocket_url"],
        auto_launch_remix=bool(raw.get("auto_launch_remix", False)),
        force_remix_preview=bool(raw.get("force_remix_preview", False)),
        force_transparent_background=bool(
            raw.get("force_transparent_background", False)
        ),
        remix_executable_path=remix_executable_path,
        remix_model_path=remix_model_path,
        actions=tuple(actions),
        global_hotkeys=hotkey_config,
    )
