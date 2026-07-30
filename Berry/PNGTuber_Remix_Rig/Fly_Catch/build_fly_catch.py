import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "sources" / "fly_catch_keyposes_transparent.png"
PRODUCTION_FRAMES = ROOT / "production_frames"
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

SOURCE_CELL = (512, 512)
PRODUCTION_CELL = (1056, 1292)
SHEET_GRID = (7, 2)
ART_SCALE = 2.4
BODY_CENTER_X = 650
FEET_Y = 1235


def checkerboard(size: tuple[int, int], tile: int = 32) -> Image.Image:
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


def body_center_x(cell: Image.Image) -> float:
    # Use Berry's lower green body rather than the tongue or detached fly.
    points: list[tuple[int, int]] = []
    pixels = cell.load()
    for y in range(200, SOURCE_CELL[1]):
        for x in range(SOURCE_CELL[0]):
            red, green, blue, alpha = pixels[x, y]
            if (
                alpha > 80
                and green > red * 0.93
                and green > blue * 1.25
                and red > 45
            ):
                points.append((x, y))
    if not points:
        raise RuntimeError("Could not locate Berry's body")
    left = min(point[0] for point in points)
    right = max(point[0] for point in points) + 1
    return (left + right) / 2


def build_production_pose(cell: Image.Image) -> Image.Image:
    alpha_bbox = cell.getchannel("A").getbbox()
    if alpha_bbox is None:
        raise RuntimeError("Encountered an empty key pose")

    source_center_x = body_center_x(cell)
    cropped = cell.crop(alpha_bbox)
    scaled_size = (
        round(cropped.width * ART_SCALE),
        round(cropped.height * ART_SCALE),
    )
    scaled = cropped.resize(scaled_size, Image.Resampling.LANCZOS)

    body_x_in_crop = (source_center_x - alpha_bbox[0]) * ART_SCALE
    paste_x = round(BODY_CENTER_X - body_x_in_crop)
    paste_y = round(FEET_Y - scaled.height)

    frame = Image.new("RGBA", PRODUCTION_CELL, (0, 0, 0, 0))
    frame.alpha_composite(scaled, (paste_x, paste_y))
    return frame


def count_magenta_pixels(image: Image.Image) -> int:
    count = 0
    for red, green, blue, alpha in image.getdata():
        if alpha > 32 and red > 220 and blue > 200 and green < 80:
            count += 1
    return count


def main() -> None:
    PRODUCTION_FRAMES.mkdir(parents=True, exist_ok=True)
    SHEETS.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)

    study = Image.open(SOURCE).convert("RGBA")
    expected_size = (SOURCE_CELL[0] * 3, SOURCE_CELL[1] * 2)
    if study.size != expected_size:
        raise RuntimeError(
            f"Expected source sheet {expected_size}, received {study.size}"
        )

    poses: dict[str, Image.Image] = {}
    pose_report: dict[str, object] = {}
    for index, pose_name in enumerate(POSE_NAMES):
        source_x = (index % 3) * SOURCE_CELL[0]
        source_y = (index // 3) * SOURCE_CELL[1]
        source_pose = study.crop(
            (
                source_x,
                source_y,
                source_x + SOURCE_CELL[0],
                source_y + SOURCE_CELL[1],
            )
        )
        pose = build_production_pose(source_pose)
        bbox = pose.getchannel("A").getbbox()
        if bbox is None:
            raise RuntimeError(f"{pose_name} is empty")
        if (
            bbox[0] <= 4
            or bbox[1] <= 4
            or bbox[2] >= PRODUCTION_CELL[0] - 4
            or bbox[3] >= PRODUCTION_CELL[1] - 4
        ):
            raise RuntimeError(f"{pose_name} is too close to a cell edge: {bbox}")

        magenta_pixels = count_magenta_pixels(pose)
        if magenta_pixels:
            raise RuntimeError(
                f"{pose_name} retains {magenta_pixels} chroma-colored pixels"
            )

        poses[pose_name] = pose
        pose.save(PRODUCTION_FRAMES / f"{pose_name}.png", optimize=True)
        pose_report[pose_name] = {
            "bbox": bbox,
            "alpha_extrema": pose.getchannel("A").getextrema(),
            "magenta_pixels": magenta_pixels,
        }

    sequence = [poses[name] for name in SEQUENCE]
    sheet_size = (
        PRODUCTION_CELL[0] * SHEET_GRID[0],
        PRODUCTION_CELL[1] * SHEET_GRID[1],
    )
    if max(sheet_size) > 8192:
        raise RuntimeError(f"Sprite sheet exceeds 8192 pixels: {sheet_size}")

    sprite_sheet = Image.new("RGBA", sheet_size, (0, 0, 0, 0))
    for index, frame in enumerate(sequence):
        x = (index % SHEET_GRID[0]) * PRODUCTION_CELL[0]
        y = (index // SHEET_GRID[0]) * PRODUCTION_CELL[1]
        sprite_sheet.alpha_composite(frame, (x, y))
    production_sheet = SHEETS / "fly_catch_14f_7x2.png"
    sprite_sheet.save(production_sheet, optimize=True)

    preview_size = (
        PRODUCTION_CELL[0] // 2,
        PRODUCTION_CELL[1] // 2,
    )
    gif_frames = []
    for frame in sequence:
        preview = frame.resize(preview_size, Image.Resampling.LANCZOS)
        board = checkerboard(preview_size, tile=24)
        board.alpha_composite(preview)
        gif_frames.append(
            board.convert("P", palette=Image.Palette.ADAPTIVE, colors=255)
        )
    gif_frames[0].save(
        PREVIEWS / "fly_catch_preview.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=100,
        loop=0,
        disposal=2,
    )

    contact = checkerboard(
        (preview_size[0] * 3, preview_size[1] * 2),
        tile=24,
    )
    for index, pose_name in enumerate(POSE_NAMES):
        pose = poses[pose_name].resize(preview_size, Image.Resampling.LANCZOS)
        x = (index % 3) * preview_size[0]
        y = (index // 3) * preview_size[1]
        contact.alpha_composite(pose, (x, y))
    contact.save(PREVIEWS / "fly_catch_key_poses_production.png", optimize=True)

    backgrounds = (
        ("checker", None),
        ("white", (255, 255, 255, 255)),
        ("black", (0, 0, 0, 255)),
        ("cyan", (0, 255, 255, 255)),
    )
    qa_thumb = (PRODUCTION_CELL[0] // 4, PRODUCTION_CELL[1] // 4)
    qa = Image.new(
        "RGBA",
        (qa_thumb[0] * len(POSE_NAMES), qa_thumb[1] * len(backgrounds)),
        (0, 0, 0, 255),
    )
    for row, (_, color) in enumerate(backgrounds):
        for column, pose_name in enumerate(POSE_NAMES):
            if color is None:
                tile = checkerboard(qa_thumb, tile=16)
            else:
                tile = Image.new("RGBA", qa_thumb, color)
            pose = poses[pose_name].resize(qa_thumb, Image.Resampling.LANCZOS)
            tile.alpha_composite(pose)
            qa.alpha_composite(tile, (column * qa_thumb[0], row * qa_thumb[1]))
    qa.save(PREVIEWS / "qa_fly_catch_4_backgrounds.png", optimize=True)

    report = {
        "source": str(SOURCE),
        "production_sheet": str(production_sheet),
        "cell_size": PRODUCTION_CELL,
        "sheet_grid": SHEET_GRID,
        "sheet_size": sheet_size,
        "frames": len(sequence),
        "fps": 10,
        "duration_seconds": len(sequence) / 10,
        "art_scale": ART_SCALE,
        "body_center_x": BODY_CENTER_X,
        "feet_y": FEET_Y,
        "poses": pose_report,
    }
    (ROOT / "qa_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(
        f"production={len(sequence)} frames at 10 FPS, "
        f"{len(sequence) / 10:.1f} seconds"
    )
    print(
        f"sheet={sheet_size[0]}x{sheet_size[1]}, "
        f"cell={PRODUCTION_CELL[0]}x{PRODUCTION_CELL[1]}"
    )
    for pose_name, details in pose_report.items():
        print(f"{pose_name}: {details}")


if __name__ == "__main__":
    main()
