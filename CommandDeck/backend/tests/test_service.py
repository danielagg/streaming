import asyncio
from dataclasses import replace

import pytest

from command_deck.config import default_config
from command_deck.service import CommandDeckService


class FakeSocket:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


@pytest.mark.asyncio
async def test_trigger_command_acknowledges_and_completes(monkeypatch):
    config = default_config()
    config = type(config)(
        app_name=config.app_name,
        remix_websocket_url=config.remix_websocket_url,
        actions=(type(config.actions[0])("whiskey", "Whiskey", "Whiskey Sip", 0),),
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
async def test_ping_acknowledges_command_channel():
    service = CommandDeckService(default_config(), mock_remix=True)
    messages = []

    async def capture(kind, payload, request_id=None):
        messages.append((kind, payload, request_id))

    service.emit = capture
    await service.handle_command(
        {"version": 1, "id": "ping-1", "type": "backend.ping", "payload": {}}
    )

    assert messages == [("command.result", {"ok": True}, "ping-1")]


@pytest.mark.asyncio
async def test_cached_service_and_obs_state_is_replayed_to_late_client():
    service = CommandDeckService(default_config(), mock_remix=True)
    await service.emit(
        "service.status",
        {"service": "obs", "state": "online", "detail": "3 scenes available"},
    )
    await service.emit("obs.scene.changed", {"sceneName": "BRB"})
    socket = FakeSocket()

    await service._send_cached_state(socket)

    assert socket.messages == [
        service.event(
            "service.status",
            {"service": "obs", "state": "online", "detail": "3 scenes available"},
        ),
        service.event("obs.scene.changed", {"sceneName": "BRB"}),
        service.event("obs.music.tail", {"state": "idle", "remainingMs": 0}),
    ]


@pytest.mark.asyncio
async def test_start_launches_obs_before_starting_its_connection(monkeypatch):
    config = default_config()
    config = replace(
        config,
        obs=replace(config.obs, enabled=True, auto_launch=True),
    )
    service = CommandDeckService(config, mock_remix=True)
    calls = []

    class Process:
        pid = 73

    async def capture(event_type, payload, _request_id=None):
        calls.append((event_type, payload))

    async def watch_remix():
        return None

    async def start_twitch():
        calls.append(("twitch.start", {}))

    async def start_obs():
        calls.append(("obs.start", {}))

    service.emit = capture
    service._watch_remix = watch_remix
    service.twitch.start = start_twitch
    service.obs.start = start_obs
    monkeypatch.setattr("command_deck.service.launch_obs", lambda _config: Process())

    await service.start()
    await asyncio.gather(*service.tasks)

    assert calls == [
        (
            "service.status",
            {
                "service": "obs",
                "state": "connecting",
                "detail": "Launching process 73",
            },
        ),
        ("twitch.start", {}),
        ("obs.start", {}),
    ]


@pytest.mark.asyncio
async def test_probe_selects_preview_after_remix_is_ready(monkeypatch, tmp_path):
    monkeypatch.setenv("COMMAND_DECK_ELECTRON_PID", "314")
    monkeypatch.setenv("COMMAND_DECK_DISPLAY_X", "1920")
    monkeypatch.setenv("COMMAND_DECK_DISPLAY_Y", "0")
    monkeypatch.setenv("COMMAND_DECK_DISPLAY_WIDTH", "1080")
    monkeypatch.setenv("COMMAND_DECK_DISPLAY_HEIGHT", "1920")
    executable = tmp_path / "PNGTuber-Remix.exe"
    config = replace(
        default_config(),
        force_remix_preview=True,
        remix_executable_path=executable,
    )
    service = CommandDeckService(config, mock_remix=True)
    service.remix_process_id = 42
    selected: list[tuple[int, float, tuple[int, int, int, int] | None]] = []
    focused: list[tuple[int, str | None]] = []
    events: list[str] = []
    remix_closed = 0
    state_list_calls = 0

    async def capture(event_type, _payload, _request_id=None):
        events.append(event_type)

    service.emit = capture
    original_list_states = service.remix.list_states

    async def list_states():
        nonlocal state_list_calls
        state_list_calls += 1
        return await original_list_states()

    async def close_remix():
        nonlocal remix_closed
        remix_closed += 1

    service.remix.close = close_remix
    service.remix.list_states = list_states

    monkeypatch.setattr("command_deck.service.read_float32", lambda *_args: 1.5)
    monkeypatch.setattr(
        "command_deck.service.select_preview_mode",
        lambda process_id, *, ui_scale, target_bounds: selected.append(
            (process_id, ui_scale, target_bounds)
        ),
    )
    monkeypatch.setattr(
        "command_deck.service.focus_process_window",
        lambda process_id, *, title: focused.append((process_id, title)),
    )

    await service._probe_remix()

    assert selected == [(42, 1.5, (1920, 0, 1080, 1920))]
    assert focused == [(314, "Command Deck")]
    assert service.remix_process_id is None
    assert remix_closed == 1
    assert state_list_calls == 2
    assert "remix.preview.ready" in events


@pytest.mark.asyncio
async def test_remix_monitor_reports_disconnect_and_recovery():
    service = CommandDeckService(default_config(), mock_remix=True)
    events: list[dict[str, object]] = []
    outcomes = iter(
        [
            RuntimeError("connection lost"),
            RuntimeError("connection refused"),
            RuntimeError("connection refused"),
            [{"name": "Idle"}],
        ]
    )

    async def capture(event_type, payload, _request_id=None):
        if event_type == "service.status":
            events.append(payload)

    async def list_states():
        try:
            outcome = next(outcomes)
        except StopIteration:
            raise asyncio.CancelledError from None
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    service.emit = capture
    service.remix.list_states = list_states

    with pytest.raises(asyncio.CancelledError):
        await service._monitor_remix(
            initial_state="online",
            poll_interval=0,
            retry_interval=0,
        )

    assert [(event["state"], event["detail"]) for event in events] == [
        ("connecting", "connection lost"),
        ("offline", "connection refused"),
        ("online", "1 states available"),
    ]


@pytest.mark.asyncio
async def test_action_rejection_emits_a_terminal_error():
    service = CommandDeckService(default_config(), mock_remix=True)
    messages = []

    async def capture(kind, payload, request_id=None):
        messages.append((kind, payload, request_id))

    async def reject(_action_id, _request_id):
        raise RuntimeError("Another Berry action is already running.")

    service.emit = capture
    service.controller.trigger = reject

    await service._run_action("whiskey", "request-2")

    assert messages == [
        (
            "berry.action.error",
            {
                "actionId": "whiskey",
                "message": "Another Berry action is already running.",
            },
            "request-2",
        )
    ]
