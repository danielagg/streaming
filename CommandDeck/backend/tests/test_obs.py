import asyncio

import pytest

from command_deck.config import ObsConfig, ObsSceneDefinition
from command_deck.obs import ObsError, ObsService, build_auth_response


class FakeObsClient:
    def __init__(self) -> None:
        self.connected = True
        self.calls: list[tuple[str, dict]] = []

    async def connect(self) -> None:
        self.connected = True

    async def request(self, request_type, request_data=None):
        data = request_data or {}
        self.calls.append((request_type, data))
        if request_type == "GetInputVolume":
            return {"inputVolumeDb": -8.0, "inputVolumeMul": 0.4}
        return {}

    async def wait_closed(self) -> None:
        await asyncio.Future()

    async def close(self) -> None:
        self.connected = False


def obs_config(*, tail_ms=60, fade_ms=20):
    return ObsConfig(
        enabled=True,
        scenes=(
            ObsSceneDefinition("main", "Main (screen share)", "Main"),
            ObsSceneDefinition("starting", "Starting Soon", "Starting Soon"),
            ObsSceneDefinition("brb", "BRB", "BRB"),
        ),
        music_tail_ms=tail_ms,
        music_fade_ms=fade_ms,
    )


@pytest.mark.asyncio
async def test_starting_soon_to_main_keeps_music_then_fades_and_stops():
    client = FakeObsClient()
    events = []

    async def emit(kind, payload, request_id=None):
        events.append((kind, payload, request_id))

    service = ObsService(obs_config(), emit, client=client)
    await service._scene_changed("Starting Soon")
    await service._scene_changed("Main (screen share)")
    await asyncio.wait_for(service._tail_task, timeout=1)

    media_actions = [
        data["mediaAction"]
        for request, data in client.calls
        if request == "TriggerMediaInputAction"
    ]
    assert media_actions == [
        "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART",
        "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_STOP",
    ]
    volumes = [
        data["inputVolumeDb"]
        for request, data in client.calls
        if request == "SetInputVolume"
    ]
    assert min(volumes) == -60.0
    assert volumes[-1] == -8.0
    assert events[-1][0:2] == (
        "obs.music.tail",
        {"state": "idle", "remainingMs": 0},
    )


@pytest.mark.asyncio
async def test_leaving_main_for_brb_cancels_tail_and_stops_music():
    client = FakeObsClient()

    async def emit(_kind, _payload, _request_id=None):
        return None

    service = ObsService(obs_config(tail_ms=10_000, fade_ms=1_000), emit, client=client)
    await service._scene_changed("Starting Soon")
    await service._scene_changed("Main (screen share)")
    await asyncio.sleep(0)
    await service._scene_changed("BRB")

    assert service._tail_task is None
    assert client.calls[-2:] == [
        (
            "TriggerMediaInputAction",
            {
                "inputName": "StartingSoon Music",
                "mediaAction": "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_STOP",
            },
        ),
        (
            "SetInputVolume",
            {"inputName": "StartingSoon Music", "inputVolumeDb": -8.0},
        ),
    ]


@pytest.mark.asyncio
async def test_rejects_scene_outside_configured_controls():
    client = FakeObsClient()

    async def emit(_kind, _payload, _request_id=None):
        return None

    service = ObsService(obs_config(), emit, client=client)
    with pytest.raises(ObsError, match="not configured"):
        await service.set_scene("Private helper scene")


def test_obs_auth_response_matches_protocol_formula():
    assert build_auth_response("password", "salt", "challenge") == (
        "zTM5ki6L2vVvBQiTG9ckH1Lh64AbnCf6XZ226UmnkIA="
    )
