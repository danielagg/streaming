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
class AppConfig:
    app_name: str
    websocket_url: str
    auto_launch_remix: bool
    remix_executable_path: Path | None
    remix_model_path: Path | None
    actions: tuple[ActionDefinition, ...]


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
        remix_executable_path=remix_executable_path,
        remix_model_path=remix_model_path,
        actions=tuple(actions),
    )
