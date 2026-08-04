from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "sources" / "understanding_key_pose.png"
FRAME_DIR = ROOT / "frames"
SHEET_DIR = ROOT / "sheets"
PREVIEW_DIR = ROOT / "previews"

CELL_SIZE = (672, 1292)
GRID_SIZE = (4, 4)
FPS = 8
TARGET_BODY_HEIGHT = 1164
KEY_COLOR = (247, 3, 240)

# A thoughtful pause, one deliberate nod, then a smaller confirming nod. Every
# frame is bottom-anchored: scale_y lowers the head while the feet stay planted.
MOTION = (
    (1.000, 1.000, 0.00),
    (1.000, 1.000, 0.00),
    (1.001, 0.992, 0.00),
    (1.003, 0.978, 0.05),
    (1.004, 0.965, 0.10),
    (1.003, 0.978, 0.05),
    (1.001, 0.992, 0.00),
    (1.000, 1.000, 0.00),
    (1.000, 1.000, 0.00),
    (1.001, 0.990, -0.03),
    (1.002, 0.978, -0.06),
    (1.003, 0.970, -0.08),
    (1.002, 0.982, -0.04),
    (1.001, 0.995, 0.00),
    (1.000, 1.000, 0.00),
    (1.000, 1.000, 0.00),
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
        raise RuntimeError("Understanding source is completely transparent.")
    art = source.crop(bbox)
    scale = TARGET_BODY_HEIGHT / art.height
    size = (round(art.width * scale), TARGET_BODY_HEIGHT)
    if size[0] > CELL_SIZE[0] - 40:
        raise RuntimeError(f"Calibrated art is too wide for the cell: {size}")
    return art.resize(size, Image.Resampling.LANCZOS)


def clear_resampled_chroma(image: Image.Image) -> None:
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            distance = max(
                abs(red - KEY_COLOR[0]),
                abs(green - KEY_COLOR[1]),
                abs(blue - KEY_COLOR[2]),
            )
            if alpha >= 240 and distance <= 16:
                pixels[x, y] = (0, 0, 0, 0)


def render_frame(
    art: Image.Image,
    motion: tuple[float, float, float],
) -> Image.Image:
    scale_x, scale_y, rotation = motion
    size = (
        max(1, round(art.width * scale_x)),
        max(1, round(art.height * scale_y)),
    )
    moved = art.resize(size, Image.Resampling.LANCZOS)
    if rotation:
        moved = moved.rotate(
            rotation,
            resample=Image.Resampling.BICUBIC,
            expand=True,
        )

    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    x = (CELL_SIZE[0] - moved.width) // 2
    y = CELL_SIZE[1] - 40 - moved.height
    frame.alpha_composite(moved, (x, y))
    clear_resampled_chroma(frame)
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
        PREVIEW_DIR / "understanding_preview.gif",
        save_all=True,
        append_images=preview_frames[1:],
        duration=round(1000 / FPS),
        loop=0,
        disposal=2,
        optimize=False,
    )


def make_key_moments(frames: list[Image.Image]) -> None:
    size = (CELL_SIZE[0] // 3, CELL_SIZE[1] // 3)
    samples = [frames[index].resize(size, Image.Resampling.LANCZOS) for index in (0, 4, 8, 11)]
    strip = Image.new("RGBA", (size[0] * len(samples), size[1]), "white")
    for index, sample in enumerate(samples):
        background = checker(size, 12)
        background.alpha_composite(sample)
        strip.alpha_composite(background, (index * size[0], 0))
    strip.save(PREVIEW_DIR / "understanding_key_moments.png")


def make_qa(frames: list[Image.Image]) -> None:
    size = (CELL_SIZE[0] // 2, CELL_SIZE[1] // 2)
    sample = frames[4].resize(size, Image.Resampling.LANCZOS)
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
    qa.save(PREVIEW_DIR / "qa_understanding_4_backgrounds.png")


def count_opaque_chroma_residue(image: Image.Image) -> int:
    count = 0
    for red, green, blue, alpha in image.get_flattened_data():
        distance = max(
            abs(red - KEY_COLOR[0]),
            abs(green - KEY_COLOR[1]),
            abs(blue - KEY_COLOR[2]),
        )
        if alpha >= 240 and distance <= 16:
            count += 1
    return count


def count_magenta_like_outline(image: Image.Image) -> int:
    return sum(
        1
        for red, green, blue, alpha in image.get_flattened_data()
        if alpha and red > 200 and green < 80 and blue > 170
    )


def main() -> None:
    for directory in (FRAME_DIR, SHEET_DIR, PREVIEW_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    source = Image.open(SOURCE).convert("RGBA")
    art = normalize_source(source)
    frames = [render_frame(art, motion) for motion in MOTION]

    for index, frame in enumerate(frames, start=1):
        frame.save(FRAME_DIR / f"{index:02d}_understanding.png")

    sheet = make_sheet(frames)
    sheet_path = SHEET_DIR / "berry_understanding_nod_16f_4x4.png"
    sheet.save(sheet_path)
    make_preview(frames)
    make_key_moments(frames)
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
        "magenta_like_outline_pixels": max(
            count_magenta_like_outline(frame) for frame in frames
        ),
    }
    (ROOT / "qa_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Built {len(frames)} frames at {FPS} FPS ({report['duration_ms']} ms).")
    print(f"Sheet: {sheet_path} ({sheet.width}x{sheet.height}, {sheet.mode})")
    print(
        "Maximum opaque chroma-key residue: "
        f"{report['opaque_chroma_key_residue_pixels']} pixels"
    )
    print(
        "Maximum magenta-like outline: "
        f"{report['magenta_like_outline_pixels']} pixels"
    )


if __name__ == "__main__":
    main()
