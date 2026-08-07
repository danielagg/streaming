from pathlib import Path

import pytest

from command_deck.config import ActionDefinition, BounceEffect
from command_deck.controller import ActionController
from command_deck.remix import MockRemixClient


class FakeAudio:
    def __init__(self):
        self.played: list[Path] = []
        self.stopped = 0

    def play(self, path):
        self.played.append(path)

    def stop(self):
        self.stopped += 1


@pytest.mark.asyncio
async def test_action_restores_normal_state():
    action = ActionDefinition(
        "croak", "Croak", "Croaking", 0, audio_path=Path("sound.mp3")
    )
    remix = MockRemixClient(["Croaking"])
    events = []

    async def emit(kind, payload, request_id):
        events.append((kind, payload, request_id))

    audio = FakeAudio()
    controller = ActionController((action,), remix, emit, audio)
    await controller.trigger("croak", "request-1")
    assert remix.transitions == ["Croaking", "Idle"]
    assert [event[0] for event in events] == [
        "berry.action.progress",
        "berry.action.completed",
    ]
    assert events[-1][1]["restoredState"] == "Idle"
    assert audio.stopped == 1


@pytest.mark.asyncio
async def test_missing_state_emits_error():
    action = ActionDefinition("fly", "Fly", "Missing", 0)
    remix = MockRemixClient([])
    events = []

    async def emit(kind, payload, request_id):
        events.append((kind, payload))

    await ActionController((action,), remix, emit, FakeAudio()).trigger("fly")
    assert events[0][0] == "berry.action.error"


@pytest.mark.asyncio
async def test_action_applies_configured_sprite_bounce():
    action = ActionDefinition(
        "surprised",
        "Surprised",
        "Surprised",
        0,
        bounce=BounceEffect("berry_surprised_hop_16f_4x4", 180, 750),
    )
    remix = MockRemixClient(["Surprised"])

    async def emit(kind, payload, request_id):
        return None

    await ActionController((action,), remix, emit, FakeAudio()).trigger("surprised")
    assert remix.bounces == [("berry_surprised_hop_16f_4x4", 180, 0.75)]
