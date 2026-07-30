from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames"
SHEETS = ROOT / "sheets"
PREVIEWS = ROOT / "previews"

SOURCE_FILES = {
    "lift": FRAMES / "01_lift.png",
    "approach": FRAMES / "02_approach.png",
    "sip": FRAMES / "03_sip.png",
    "satisfied": FRAMES / "04_satisfied.png",
}

# At 6 FPS this plays for two seconds. Repeated poses create intentional holds.
SEQUENCE = [
    "lift",
    "lift",
    "approach",
    "approach",
    "sip",
    "sip",
    "sip",
    "satisfied",
    "satisfied",
    "approach",
    "lift",
    "lift",
]

CELL_SIZE = (672, 1292)
SHEET_GRID = (4, 3)


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    return image.getchannel("A").getbbox()


def checkerboard(size: tuple[int, int], tile: int = 32) -> Image.Image:
    board = Image.new("RGBA", size, (235, 235, 235, 255))
    draw = ImageDraw.Draw(board)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(195, 195, 195, 255))
    return board


def fit_frame(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    image.thumbnail(CELL_SIZE, Image.Resampling.LANCZOS)
    cell = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    x = (CELL_SIZE[0] - image.width) // 2
    y = (CELL_SIZE[1] - image.height) // 2
    cell.alpha_composite(image, (x, y))
    return cell


def main() -> None:
    SHEETS.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)

    originals = {name: Image.open(path).convert("RGBA") for name, path in SOURCE_FILES.items()}
    for name, image in originals.items():
        if image.getchannel("A").getextrema()[0] != 0:
            raise RuntimeError(f"{name} has no fully transparent pixels")
        if alpha_bbox(image) is None:
            raise RuntimeError(f"{name} is unexpectedly empty")

    fitted = {name: fit_frame(image) for name, image in originals.items()}
    sequence = [fitted[name] for name in SEQUENCE]

    sheet = Image.new(
        "RGBA",
        (CELL_SIZE[0] * SHEET_GRID[0], CELL_SIZE[1] * SHEET_GRID[1]),
        (0, 0, 0, 0),
    )
    for index, frame in enumerate(sequence):
        x = (index % SHEET_GRID[0]) * CELL_SIZE[0]
        y = (index // SHEET_GRID[0]) * CELL_SIZE[1]
        sheet.alpha_composite(frame, (x, y))
    sheet.save(SHEETS / "whiskey_sip_12f_4x3.png", optimize=True)

    gif_frames = []
    for frame in sequence:
        board = checkerboard(CELL_SIZE)
        board.alpha_composite(frame)
        gif_frames.append(board.convert("P", palette=Image.Palette.ADAPTIVE, colors=255))
    gif_frames[0].save(
        PREVIEWS / "whiskey_sip_preview.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=167,
        loop=0,
        disposal=2,
    )

    contact = Image.new("RGBA", (CELL_SIZE[0] * 2, CELL_SIZE[1] * 2), (0, 0, 0, 0))
    for index, name in enumerate(("lift", "approach", "sip", "satisfied")):
        x = (index % 2) * CELL_SIZE[0]
        y = (index // 2) * CELL_SIZE[1]
        contact.alpha_composite(fitted[name], (x, y))
    contact.save(PREVIEWS / "whiskey_sip_key_poses.png", optimize=True)

    print(f"sheet={sheet.width}x{sheet.height}, cell={CELL_SIZE[0]}x{CELL_SIZE[1]}, frames={len(sequence)}")
    for name, image in originals.items():
        print(f"{name}: size={image.size}, alpha={image.getchannel('A').getextrema()}, bbox={alpha_bbox(image)}")


if __name__ == "__main__":
    main()
