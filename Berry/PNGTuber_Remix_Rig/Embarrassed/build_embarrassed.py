from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "sources" / "embarrassed_key_pose.png"
FRAME_DIR = ROOT / "frames"
SHEET_DIR = ROOT / "sheets"
PREVIEW_DIR = ROOT / "previews"

CELL_SIZE = (672, 1292)
GRID_SIZE = (4, 4)
FPS = 8

# Angry's visible body is 1252 px tall and needed a 0.93 import scale. Baking
# that correction into this asset gives 1164 px, essentially the normal idle
# body's 1172 px footprint.
TARGET_BODY_HEIGHT = 1164

# A slow bashful sway: Berry leans away, gathers himself, then fidgets gently
# the other way. This deliberately avoids the rapid shake used by Angry.
MOTION = (
    (0, 0, 1.000, 1.000, 0.00),
    (-1, 0, 1.000, 1.000, -0.08),
    (-2, 0, 1.001, 0.999, -0.16),
    (-3, 1, 1.002, 0.998, -0.24),
    (-4, 1, 1.003, 0.997, -0.32),
    (-3, 1, 1.002, 0.998, -0.24),
    (-2, 0, 1.001, 0.999, -0.16),
    (-1, 0, 1.000, 1.000, -0.08),
    (0, 0, 1.000, 1.000, 0.00),
    (1, 0, 1.000, 1.000, 0.08),
    (2, 0, 1.001, 0.999, 0.16),
    (3, 1, 1.002, 0.998, 0.24),
    (4, 1, 1.003, 0.997, 0.32),
    (3, 1, 1.002, 0.998, 0.24),
    (2, 0, 1.001, 0.999, 0.16),
    (0, 0, 1.000, 1.000, 0.00),
)


def checker(size: tuple[int, int], block: int = 24) -> Image.Image:
    image = Image.new("RGBA", size, (232, 232, 232, 255))
    draw = ImageDraw.Draw(image)
    dark = (190, 190, 190, 255)
    for y in range(0, size[1], block):
        for x in range(0, size[0], block):
            if (x // block + y // block) % 2:
                draw.rectangle((x, y, x + block - 1, y + block - 1), fill=dark)
    return image


def normalize_source(source: Image.Image) -> Image.Image:
    bbox = source.getbbox()
    if bbox is None:
        raise RuntimeError("Embarrassed source is completely transparent.")

    art = source.crop(bbox)
    scale = TARGET_BODY_HEIGHT / art.height
    size = (round(art.width * scale), TARGET_BODY_HEIGHT)
    if size[0] > CELL_SIZE[0] - 40:
        raise RuntimeError(f"Calibrated art is too wide for the cell: {size}")
    return art.resize(size, Image.Resampling.LANCZOS)


def render_frame(
    art: Image.Image,
    motion: tuple[int, int, float, float, float],
) -> Image.Image:
    dx, dy, scale_x, scale_y, rotation = motion
    size = (max(1, round(art.width * scale_x)), max(1, round(art.height * scale_y)))
    moved = art.resize(size, Image.Resampling.LANCZOS)
    if rotation:
        moved = moved.rotate(
            rotation,
            resample=Image.Resampling.BICUBIC,
            expand=True,
        )

    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    x = (CELL_SIZE[0] - moved.width) // 2 + dx
    y = CELL_SIZE[1] - 40 - moved.height + dy
    frame.alpha_composite(moved, (x, y))
    return frame


def make_sheet(frames: list[Image.Image]) -> Image.Image:
    sheet = Image.new(
        "RGBA",
        (CELL_SIZE[0] * GRID_SIZE[0], CELL_SIZE[1] * GRID_SIZE[1]),
        (0, 0, 0, 0),
    )
    for index, frame in enumerate(frames):
        x = (index % GRID_SIZE[0]) * CELL_SIZE[0]
        y = (index // GRID_SIZE[0]) * CELL_SIZE[1]
        sheet.alpha_composite(frame, (x, y))
    return sheet


def make_preview(frames: list[Image.Image]) -> None:
    size = (CELL_SIZE[0] // 2, CELL_SIZE[1] // 2)
    preview_frames: list[Image.Image] = []
    for frame in frames:
        small = frame.resize(size, Image.Resampling.LANCZOS)
        background = checker(size, 12)
        background.alpha_composite(small)
        preview_frames.append(background.convert("RGB"))

    preview_frames[0].save(
        PREVIEW_DIR / "embarrassed_preview.gif",
        save_all=True,
        append_images=preview_frames[1:],
        duration=round(1000 / FPS),
        loop=0,
        disposal=2,
        optimize=False,
    )


def make_qa(frames: list[Image.Image]) -> None:
    size = (CELL_SIZE[0] // 2, CELL_SIZE[1] // 2)
    sample = frames[12].resize(size, Image.Resampling.LANCZOS)
    backgrounds = [
        checker(size, 12),
        Image.new("RGBA", size, "white"),
        Image.new("RGBA", size, "black"),
        Image.new("RGBA", size, (0, 220, 230, 255)),
    ]
    qa = Image.new("RGBA", (size[0] * len(backgrounds), size[1]), "white")
    for index, background in enumerate(backgrounds):
        background.alpha_composite(sample)
        qa.alpha_composite(background, (index * size[0], 0))
    qa.save(PREVIEW_DIR / "qa_embarrassed_4_backgrounds.png")


def count_opaque_chroma_residue(image: Image.Image) -> int:
    key = (251, 6, 206)
    count = 0
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            distance = max(abs(red - key[0]), abs(green - key[1]), abs(blue - key[2]))
            if alpha >= 240 and distance <= 16:
                count += 1
    return count


def main() -> None:
    for directory in (FRAME_DIR, SHEET_DIR, PREVIEW_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    source = Image.open(SOURCE).convert("RGBA")
    art = normalize_source(source)
    frames = [render_frame(art, motion) for motion in MOTION]

    for index, frame in enumerate(frames, start=1):
        frame.save(FRAME_DIR / f"{index:02d}_embarrassed.png")

    sheet = make_sheet(frames)
    sheet_path = SHEET_DIR / "berry_embarrassed_sway_16f_4x4.png"
    sheet.save(sheet_path)
    make_preview(frames)
    make_qa(frames)

    frame_boxes = [frame.getbbox() for frame in frames]
    if any(box is None for box in frame_boxes):
        raise RuntimeError("At least one rendered frame is empty.")
    if any(
        box[0] <= 0 or box[1] <= 0 or box[2] >= CELL_SIZE[0] or box[3] >= CELL_SIZE[1]
        for box in frame_boxes
        if box is not None
    ):
        raise RuntimeError("Rendered art touches a frame edge.")

    report = {
        "frame_count": len(frames),
        "fps": FPS,
        "duration_ms": round(len(frames) / FPS * 1000),
        "cell_size": list(CELL_SIZE),
        "grid_size": list(GRID_SIZE),
        "sheet_size": list(sheet.size),
        "mode": sheet.mode,
        "target_body_height": TARGET_BODY_HEIGHT,
        "normal_idle_body_height_reference": 1172,
        "recommended_import_scale": 1.0,
        "normalized_art_size": list(art.size),
        "all_corners_transparent": all(
            frame.getpixel((x, y))[3] == 0
            for frame in frames
            for x, y in (
                (0, 0),
                (CELL_SIZE[0] - 1, 0),
                (0, CELL_SIZE[1] - 1),
                (CELL_SIZE[0] - 1, CELL_SIZE[1] - 1),
            )
        ),
        "frame_bounding_boxes": [list(box) for box in frame_boxes if box is not None],
        "opaque_chroma_key_residue_pixels": max(
            count_opaque_chroma_residue(frame) for frame in frames
        ),
    }
    (ROOT / "qa_report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Built {len(frames)} frames at {FPS} FPS ({report['duration_ms']} ms).")
    print(f"Sheet: {sheet_path} ({sheet.width}x{sheet.height}, {sheet.mode})")
    print(f"Calibrated body height: {TARGET_BODY_HEIGHT}px at Remix scale 1.00")
    print(
        "Maximum opaque chroma-key residue: "
        f"{report['opaque_chroma_key_residue_pixels']} pixels"
    )


if __name__ == "__main__":
    main()
