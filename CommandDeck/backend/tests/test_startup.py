import subprocess
from dataclasses import replace

from command_deck.config import ObsConfig, default_config
from command_deck.startup import launch_obs


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
