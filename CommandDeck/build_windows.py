from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image


APP_DIRECTORY = Path(__file__).resolve().parent
ASSETS_DIRECTORY = APP_DIRECTORY / "assets"
SOURCE_IMAGE = ASSETS_DIRECTORY / "CommandDeckIconMaster.png"
ICON_PATH = ASSETS_DIRECTORY / "CommandDeck.ico"
ENTRY_POINT = APP_DIRECTORY / "CommandDeck.pyw"
BUILD_DIRECTORY = APP_DIRECTORY / ".build"
EXECUTABLE_PATH = APP_DIRECTORY / "CommandDeck.exe"

ICON_SIZES = [
    (16, 16),
    (20, 20),
    (24, 24),
    (32, 32),
    (40, 40),
    (48, 48),
    (64, 64),
    (128, 128),
    (256, 256),
]


def create_icon() -> None:
    if not SOURCE_IMAGE.is_file():
        raise FileNotFoundError(f"Command Deck icon master not found: {SOURCE_IMAGE}")

    ASSETS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE_IMAGE) as source:
        icon = source.convert("RGBA")
        icon.save(ICON_PATH, format="ICO", sizes=ICON_SIZES)


def build_executable() -> None:
    BUILD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--name",
            "CommandDeck",
            "--icon",
            str(ICON_PATH),
            "--distpath",
            str(APP_DIRECTORY),
            "--workpath",
            str(BUILD_DIRECTORY / "work"),
            "--specpath",
            str(BUILD_DIRECTORY),
            str(ENTRY_POINT),
        ],
        cwd=APP_DIRECTORY,
        check=True,
    )

    if not EXECUTABLE_PATH.is_file():
        raise RuntimeError("PyInstaller did not create CommandDeck.exe.")


def main() -> None:
    create_icon()
    build_executable()
    print(EXECUTABLE_PATH)


if __name__ == "__main__":
    main()
