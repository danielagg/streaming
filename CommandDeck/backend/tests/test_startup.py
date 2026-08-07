import subprocess
from dataclasses import replace

from command_deck.config import ObsConfig, default_config
from command_deck.startup import launch_obs, launch_remix


def test_launch_obs_uses_its_install_directory(monkeypatch, tmp_path):
    executable = tmp_path / "obs-studio" / "bin" / "64bit" / "obs64.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    config = replace(
        default_config(),
        obs=ObsConfig(enabled=True, auto_launch=True, executable_path=executable),
    )
    calls = []

    class Process:
        pid = 42

    def popen(args, **kwargs):
        calls.append((args, kwargs))
        return Process()

    monkeypatch.setattr("command_deck.startup._is_process_running", lambda _: False)
    monkeypatch.setattr("command_deck.startup.subprocess.Popen", popen)

    process = launch_obs(config)

    assert process.pid == 42
    assert calls == [
        (
            [str(executable)],
            {
                "cwd": executable.parent,
                "close_fds": True,
                "creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            },
        )
    ]


def test_launch_obs_is_disabled_by_default(monkeypatch):
    def unexpected_popen(*_args, **_kwargs):
        raise AssertionError("OBS should not launch")

    monkeypatch.setattr("command_deck.startup.subprocess.Popen", unexpected_popen)

    assert launch_obs(default_config()) is None


def test_launch_obs_skips_an_existing_instance(monkeypatch, tmp_path):
    executable = tmp_path / "obs64.exe"
    config = replace(
        default_config(),
        obs=ObsConfig(enabled=True, auto_launch=True, executable_path=executable),
    )
    checked = []

    def is_process_running(path):
        checked.append(path)
        return True

    def unexpected_popen(*_args, **_kwargs):
        raise AssertionError("A second OBS instance should not launch")

    monkeypatch.setattr("command_deck.startup._is_process_running", is_process_running)
    monkeypatch.setattr("command_deck.startup.subprocess.Popen", unexpected_popen)

    assert launch_obs(config) is None
    assert checked == [executable]


def test_launch_remix_skips_an_existing_instance(monkeypatch, tmp_path):
    executable = tmp_path / "PNGTuber-Remix.exe"
    model = tmp_path / "Berry.pngRemix"
    config = replace(
        default_config(),
        auto_launch_remix=True,
        remix_executable_path=executable,
        remix_model_path=model,
    )
    checked = []

    def is_process_running(path):
        checked.append(path)
        return True

    def unexpected_popen(*_args, **_kwargs):
        raise AssertionError("A second PNGTuber Remix instance should not launch")

    monkeypatch.setattr("command_deck.startup._is_process_running", is_process_running)
    monkeypatch.setattr("command_deck.startup.subprocess.Popen", unexpected_popen)

    assert launch_remix(config) is None
    assert checked == [executable]
