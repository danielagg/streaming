from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
IDLE_SOURCE = ROOT.parent / "previews" / "preview_idle_transparent.png"
SURPRISED_SOURCE = ROOT / "sources" / "surprised_key_pose.png"
FRAME_DIR = ROOT / "frames"
SHEET_DIR = ROOT / "sheets"
PREVIEW_DIR = ROOT / "previews"

CELL_SIZE = (720, 1292)
GRID_SIZE = (4, 4)
FPS = 12
TARGET_IDLE_HEIGHT = 1172
TARGET_SURPRISED_HEIGHT = 1164


@dataclass(frozen=True)
class Beat:
    pose: str
    dx: int = 0
    dy: int = 0
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0
    mark_scale: float = 0.0
    mark_alpha: float = 0.0


# Neutral anticipation, a sharp airborne gasp, then a squashy landing. The
# symbols peak one beat after Berry launches and disappear before he lands.
BEATS = (
    Beat("idle"),
    Beat("idle", dy=6, scale_x=1.020, scale_y=0.985),
    Beat("idle", dy=18, scale_x=1.045, scale_y=0.955),
    Beat("surprised", dy=-18, scale_x=0.985, scale_y=1.020, mark_scale=0.55, mark_alpha=0.65),
    Beat("surprised", dy=-32, scale_x=0.975, scale_y=1.018, mark_scale=0.85, mark_alpha=0.90),
    Beat("surprised", dy=-38, scale_x=0.990, scale_y=1.010, mark_scale=1.00, mark_alpha=1.00),
    Beat("surprised", dy=-38, mark_scale=1.00, mark_alpha=1.00),
    Beat("surprised", dx=-2, dy=-32, scale_x=1.006, scale_y=0.994, rotation=-0.20, mark_scale=0.94, mark_alpha=0.90),
    Beat("surprised", dx=2, dy=-24, scale_x=0.996, scale_y=1.004, rotation=0.16, mark_scale=0.84, mark_alpha=0.72),
    Beat("surprised", dx=-1, dy=-14, scale_x=1.008, scale_y=0.988, rotation=-0.12, mark_scale=0.70, mark_alpha=0.48),
    Beat("surprised", dy=-5, scale_x=1.018, scale_y=0.974, mark_scale=0.52, mark_alpha=0.24),
    Beat("idle", dy=14, scale_x=1.045, scale_y=0.955),
    Beat("idle", dy=-7, scale_x=0.992, scale_y=1.014),
    Beat("idle", dx=-1, scale_x=1.002, scale_y=0.998, rotation=-0.12),
    Beat("idle", dx=1, scale_x=0.999, scale_y=1.001, rotation=0.06),
    Beat("idle"),
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


def normalize_source(source: Image.Image, target_height: int) -> Image.Image:
    bbox = source.getbbox()
    if bbox is None:
        raise RuntimeError("A Surprised animation source is completely transparent.")
    art = source.crop(bbox)
    scale = target_height / art.height
    size = (round(art.width * scale), target_height)
    if size[0] > CELL_SIZE[0] - 40:
        raise RuntimeError(f"Calibrated art is too wide for the cell: {size}")
    return art.resize(size, Image.Resampling.LANCZOS)


def transform_art(art: Image.Image, beat: Beat) -> Image.Image:
    size = (
        max(1, round(art.width * beat.scale_x)),
        max(1, round(art.height * beat.scale_y)),
    )
    moved = art.resize(size, Image.Resampling.LANCZOS)
    if beat.rotation:
        moved = moved.rotate(
            beat.rotation,
            resample=Image.Resampling.BICUBIC,
            expand=True,
        )
    return moved


def make_exclamation(scale: float, alpha: float, angle: float) -> Image.Image:
    supersample = 4
    icon = Image.new("RGBA", (96 * supersample, 176 * supersample), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)
    red = (231, 72, 67, round(255 * alpha))
    gold = (255, 211, 69, round(255 * alpha))
    points = [(30, 10), (68, 16), (59, 113), (39, 110)]
    points = [(x * supersample, y * supersample) for x, y in points]
    draw.polygon(points, fill=gold, outline=red, width=6 * supersample)
    draw.ellipse(
        (38 * supersample, 128 * supersample, 63 * supersample, 153 * supersample),
        fill=gold,
        outline=red,
        width=6 * supersample,
    )
    size = (
        max(1, round(icon.width * scale / supersample)),
        max(1, round(icon.height * scale / supersample)),
    )
    icon = icon.resize(size, Image.Resampling.LANCZOS)
    return icon.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)


def add_surprise_marks(frame: Image.Image, beat: Beat) -> None:
    if beat.mark_scale <= 0 or beat.mark_alpha <= 0:
        return
    left = make_exclamation(beat.mark_scale, beat.mark_alpha, -12)
    right = make_exclamation(beat.mark_scale * 0.88, beat.mark_alpha, 12)
    frame.alpha_composite(left, (22, 205))
    frame.alpha_composite(right, (CELL_SIZE[0] - right.width - 24, 225))


def render_frame(art: Image.Image, beat: Beat) -> Image.Image:
    moved = transform_art(art, beat)
    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    x = (CELL_SIZE[0] - moved.width) // 2 + beat.dx
    y = CELL_SIZE[1] - 40 - moved.height + beat.dy
    frame.alpha_composite(moved, (x, y))
    add_surprise_marks(frame, beat)
    clear_resampled_chroma(frame)
    return frame


def clear_resampled_chroma(image: Image.Image) -> None:
    """Remove rare opaque key-colored pixels created by transform resampling."""
    key = (243, 5, 204)
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            distance = max(
                abs(red - key[0]), abs(green - key[1]), abs(blue - key[2])
            )
            if alpha >= 240 and distance <= 16:
                pixels[x, y] = (0, 0, 0, 0)


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
        PREVIEW_DIR / "surprised_preview.gif",
        save_all=True,
        append_images=preview_frames[1:],
        duration=round(1000 / FPS),
        loop=0,
        disposal=2,
        optimize=False,
    )


def make_key_moments(frames: list[Image.Image]) -> None:
    size = (CELL_SIZE[0] // 3, CELL_SIZE[1] // 3)
    samples = [frames[index].resize(size, Image.Resampling.LANCZOS) for index in (0, 2, 5, 11)]
    strip = Image.new("RGBA", (size[0] * len(samples), size[1]), "white")
    for index, sample in enumerate(samples):
        background = checker(size, 12)
        background.alpha_composite(sample)
        strip.alpha_composite(background, (index * size[0], 0))
    strip.save(PREVIEW_DIR / "surprised_key_moments.png")


def make_qa(frames: list[Image.Image]) -> None:
    size = (CELL_SIZE[0] // 2, CELL_SIZE[1] // 2)
    sample = frames[5].resize(size, Image.Resampling.LANCZOS)
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
    qa.save(PREVIEW_DIR / "qa_surprised_4_backgrounds.png")


def count_opaque_chroma_residue(image: Image.Image) -> int:
    key = (243, 5, 204)
    count = 0
    for red, green, blue, alpha in image.get_flattened_data():
        distance = max(abs(red - key[0]), abs(green - key[1]), abs(blue - key[2]))
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

    idle = normalize_source(Image.open(IDLE_SOURCE).convert("RGBA"), TARGET_IDLE_HEIGHT)
    surprised = normalize_source(
        Image.open(SURPRISED_SOURCE).convert("RGBA"), TARGET_SURPRISED_HEIGHT
    )
    art_by_pose = {"idle": idle, "surprised": surprised}
    frames = [render_frame(art_by_pose[beat.pose], beat) for beat in BEATS]

    for index, frame in enumerate(frames, start=1):
        frame.save(FRAME_DIR / f"{index:02d}_surprised.png")

    sheet = make_sheet(frames)
    sheet_path = SHEET_DIR / "berry_surprised_hop_16f_4x4.png"
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
        "target_idle_height": TARGET_IDLE_HEIGHT,
        "target_surprised_height": TARGET_SURPRISED_HEIGHT,
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
