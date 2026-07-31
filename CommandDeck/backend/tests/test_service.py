from dataclasses import replace

import pytest

from command_deck.config import default_config
from command_deck.service import CommandDeckService


@pytest.mark.asyncio
async def test_trigger_command_acknowledges_and_completes(monkeypatch):
    config = default_config()
    config = type(config)(
        app_name=config.app_name,
        remix_websocket_url=config.remix_websocket_url,
        actions=(type(config.actions[0])("whiskey", "Whiskey", "Whiskey Sip", 0),),
        global_hotkeys=None,
    )
    service = CommandDeckService(config, mock_remix=True)
    messages = []

    async def capture(kind, payload, request_id=None):
        messages.append((kind, payload, request_id))

    service.emit = capture
    service.controller.emit = capture
    await service.handle_command(
        {
            "version": 1,
            "id": "abc",
            "type": "action.trigger",
            "payload": {"actionId": "whiskey"},
        }
    )
    await next(iter(service.tasks))
    assert messages[0] == ("command.result", {"ok": True, "accepted": True}, "abc")
    assert messages[-1][0] == "berry.action.completed"


@pytest.mark.asyncio
async def test_invalid_command_is_rejected():
    service = CommandDeckService(default_config(), mock_remix=True)
    with pytest.raises(ValueError, match="Invalid"):
        await service.handle_command({"version": 2})


@pytest.mark.asyncio
async def test_probe_selects_preview_after_remix_is_ready(monkeypatch, tmp_path):
    monkeypatch.setenv("COMMAND_DECK_ELECTRON_PID", "314")
    executable = tmp_path / "PNGTuber-Remix.exe"
    config = replace(
        default_config(),
        force_remix_preview=True,
        remix_executable_path=executable,
        global_hotkeys=None,
    )
    service = CommandDeckService(config, mock_remix=True)
    service.remix_process_id = 42
    selected: list[tuple[int, float]] = []
    focused: list[tuple[int, str | None]] = []
    events: list[str] = []

    async def capture(event_type, _payload, _request_id=None):
        events.append(event_type)

    service.emit = capture

    monkeypatch.setattr("command_deck.service.read_float32", lambda *_args: 1.5)
    monkeypatch.setattr(
        "command_deck.service.select_preview_mode",
        lambda process_id, *, ui_scale: selected.append((process_id, ui_scale)),
    )
    monkeypatch.setattr(
        "command_deck.service.focus_process_window",
        lambda process_id, *, title: focused.append((process_id, title)),
    )

    await service._probe_remix()

    assert selected == [(42, 1.5)]
    assert focused == [(314, "Command Deck")]
    assert service.remix_process_id is None
    assert "remix.preview.ready" in events
