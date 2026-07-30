from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "sources" / "fly_catch_keyposes_transparent.png"
FRAMES = ROOT / "frames"
SHEETS = ROOT / "sheets"
PREVIEWS = ROOT / "previews"

POSE_NAMES = (
    "01_notice",
    "02_aim",
    "03_strike",
    "04_catch",
    "05_retract",
    "06_satisfied",
)

# Fourteen frames at 10 FPS: 1.4 seconds total.
SEQUENCE = (
    "01_notice",
    "01_notice",
    "01_notice",
    "02_aim",
    "02_aim",
    "03_strike",
    "04_catch",
    "04_catch",
    "05_retract",
    "05_retract",
    "06_satisfied",
    "06_satisfied",
    "06_satisfied",
    "06_satisfied",
)

CELL_SIZE = (512, 512)
SHEET_GRID = (7, 2)


def checkerboard(size: tuple[int, int], tile: int = 24) -> Image.Image:
    image = Image.new("RGBA", size, (235, 235, 235, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle(
                    (x, y, x + tile - 1, y + tile - 1),
                    fill=(195, 195, 195, 255),
                )
    return image


def main() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    SHEETS.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)

    study = Image.open(SOURCE).convert("RGBA")
    expected_size = (CELL_SIZE[0] * 3, CELL_SIZE[1] * 2)
    if study.size != expected_size:
        raise RuntimeError(
            f"Expected key-pose sheet {expected_size}, received {study.size}"
        )

    poses: dict[str, Image.Image] = {}
    for index, pose_name in enumerate(POSE_NAMES):
        x = (index % 3) * CELL_SIZE[0]
        y = (index // 3) * CELL_SIZE[1]
        pose = study.crop((x, y, x + CELL_SIZE[0], y + CELL_SIZE[1]))
        if pose.getchannel("A").getbbox() is None:
            raise RuntimeError(f"{pose_name} is empty")
        poses[pose_name] = pose
        pose.save(FRAMES / f"{pose_name}.png", optimize=True)

    sequence = [poses[name] for name in SEQUENCE]
    sprite_sheet = Image.new(
        "RGBA",
        (
            CELL_SIZE[0] * SHEET_GRID[0],
            CELL_SIZE[1] * SHEET_GRID[1],
        ),
        (0, 0, 0, 0),
    )
    for index, frame in enumerate(sequence):
        x = (index % SHEET_GRID[0]) * CELL_SIZE[0]
        y = (index // SHEET_GRID[0]) * CELL_SIZE[1]
        sprite_sheet.alpha_composite(frame, (x, y))
    sprite_sheet.save(
        SHEETS / "fly_catch_prototype_14f_7x2.png",
        optimize=True,
    )

    gif_frames = []
    for frame in sequence:
        board = checkerboard(CELL_SIZE)
        board.alpha_composite(frame)
        gif_frames.append(
            board.convert("P", palette=Image.Palette.ADAPTIVE, colors=255)
        )
    gif_frames[0].save(
        PREVIEWS / "fly_catch_timing_preview.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=100,
        loop=0,
        disposal=2,
    )

    key_poses = checkerboard((CELL_SIZE[0] * 3, CELL_SIZE[1] * 2))
    key_poses.alpha_composite(study)
    key_poses.save(PREVIEWS / "fly_catch_key_poses.png", optimize=True)

    print(
        "prototype="
        f"{len(sequence)} frames at 10 FPS, "
        f"{len(sequence) / 10:.1f} seconds"
    )
    print(
        "sheet="
        f"{sprite_sheet.width}x{sprite_sheet.height}, "
        f"cell={CELL_SIZE[0]}x{CELL_SIZE[1]}"
    )


if __name__ == "__main__":
    main()
