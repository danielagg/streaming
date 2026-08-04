from __future__ import annotations

import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
INHALE_SOURCE = ROOT / "sources" / "vaping_inhale.png"
EXHALE_SOURCE = ROOT / "sources" / "vaping_exhale.png"
FRAME_DIR = ROOT / "frames"
SHEET_DIR = ROOT / "sheets"
PREVIEW_DIR = ROOT / "previews"

CELL_SIZE = (720, 1292)
GRID_SIZE = (9, 3)
FPS = 6
INHALE_FRAMES = 9
EXHALE_FRAMES = 18
TARGET_BODY_HEIGHT = 1164
BOTTOM_MARGIN = 40
INHALE_KEY = (251, 3, 247)
EXHALE_KEY = (245, 7, 238)

# Calibrated after normalizing and centering the exhale key pose.
SMOKE_ORIGIN = (300, 409)


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
        raise RuntimeError("A Vaping source is completely transparent.")
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
            for key in (INHALE_KEY, EXHALE_KEY):
                distance = max(
                    abs(red - key[0]),
                    abs(green - key[1]),
                    abs(blue - key[2]),
                )
                if alpha >= 240 and distance <= 16:
                    pixels[x, y] = (0, 0, 0, 0)
                    break


def transform_art(
    art: Image.Image,
    scale_x: float,
    scale_y: float,
    rotation: float = 0.0,
) -> Image.Image:
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
    return moved


def place_art(art: Image.Image, dx: int = 0, dy: int = 0) -> Image.Image:
    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    x = (CELL_SIZE[0] - art.width) // 2 + dx
    y = CELL_SIZE[1] - BOTTOM_MARGIN - art.height + dy
    frame.alpha_composite(art, (x, y))
    return frame


def puff_parameters(emission: int, lane: int, age: int) -> tuple[float, float, float, int]:
    rng = random.Random(emission * 97 + lane * 31)
    speed = 12.5 + rng.uniform(-1.2, 1.8)
    x = SMOKE_ORIGIN[0] - age * speed - lane * 4.0 + rng.uniform(-8, 8)
    y = (
        SMOKE_ORIGIN[1]
        - age * (4.2 + lane * 0.55)
        + math.sin((emission * 0.8 + age * 0.65 + lane) * 1.1) * (5 + lane * 2)
        + rng.uniform(-10, 10)
    )
    radius = 14.0 + age * 3.5 + lane * 4.0 + rng.uniform(-1.0, 2.0)
    alpha = max(0, round(104 - age * 2.8 - lane * 8))
    return x, y, radius, alpha


def make_smoke(exhale_index: int) -> Image.Image:
    smoke = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))

    # Emit through frame 14, leaving the final half-second to disperse.
    last_emission = min(exhale_index, 14)
    for emission in range(last_emission + 1):
        age = exhale_index - emission
        if age > 15:
            continue
        for lane in range(2):
            x, y, radius, alpha = puff_parameters(emission, lane, age)
            if alpha <= 0:
                continue
            width = max(4, round(radius * 2.15))
            height = max(4, round(radius * 1.55))
            puff = Image.new("RGBA", (width + 8, height + 8), (0, 0, 0, 0))
            puff_draw = ImageDraw.Draw(puff, "RGBA")
            puff_draw.ellipse(
                (4, 4, width + 3, height + 3),
                fill=(226, 235, 239, alpha),
            )
            puff = puff.filter(ImageFilter.GaussianBlur(radius=3.2))
            smoke.alpha_composite(
                puff,
                (round(x - puff.width / 2), round(y - puff.height / 2)),
            )

    # A thin curl gives the cloud Berry's established illustrated finish.
    progress = exhale_index / max(1, EXHALE_FRAMES - 1)
    curl_alpha = round(115 * min(1.0, progress * 3.0) * (1.0 - max(0.0, progress - 0.78) / 0.22))
    if curl_alpha > 0:
        curl_x = SMOKE_ORIGIN[0] - min(235, exhale_index * 13)
        curl_y = SMOKE_ORIGIN[1] - min(90, exhale_index * 5)
        curl_box = (curl_x - 34, curl_y - 25, curl_x + 34, curl_y + 25)
        curl_layer = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
        curl_draw = ImageDraw.Draw(curl_layer, "RGBA")
        curl_draw.arc(
            curl_box,
            start=205,
            end=530,
            fill=(206, 222, 227, curl_alpha),
            width=3,
        )
        smoke.alpha_composite(curl_layer.filter(ImageFilter.GaussianBlur(radius=0.4)))

    return smoke


def render_inhale(art: Image.Image, index: int) -> Image.Image:
    progress = index / max(1, INHALE_FRAMES - 1)
    eased = progress * progress * (3.0 - 2.0 * progress)
    moved = transform_art(
        art,
        scale_x=1.0 + eased * 0.010,
        scale_y=1.0 + eased * 0.002,
        rotation=-0.04 * eased,
    )
    frame = place_art(moved, dy=-round(eased * 2))
    clear_resampled_chroma(frame)
    return frame


def render_exhale(art: Image.Image, index: int) -> Image.Image:
    progress = index / max(1, EXHALE_FRAMES - 1)
    moved = transform_art(
        art,
        scale_x=1.008 - progress * 0.010,
        scale_y=1.0 - progress * 0.002,
        rotation=0.03 * math.sin(progress * math.pi),
    )
    frame = place_art(moved)
    clear_resampled_chroma(frame)
    frame.alpha_composite(make_smoke(index))
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
        PREVIEW_DIR / "vaping_preview.gif",
        save_all=True,
        append_images=preview_frames[1:],
        # GIF delays are stored in 10 ms units. 170 ms is closer to 1/6 second
        # than Pillow's downward quantization of a requested 167 ms to 160 ms.
        duration=170,
        loop=0,
        disposal=2,
        optimize=False,
    )


def make_key_moments(frames: list[Image.Image]) -> None:
    size = (CELL_SIZE[0] // 3, CELL_SIZE[1] // 3)
    samples = [frames[index].resize(size, Image.Resampling.LANCZOS) for index in (0, 8, 12, 22)]
    strip = Image.new("RGBA", (size[0] * len(samples), size[1]), "white")
    for index, sample in enumerate(samples):
        background = checker(size, 12)
        background.alpha_composite(sample)
        strip.alpha_composite(background, (index * size[0], 0))
    strip.save(PREVIEW_DIR / "vaping_key_moments.png")


def make_qa(frames: list[Image.Image]) -> None:
    size = (CELL_SIZE[0] // 2, CELL_SIZE[1] // 2)
    sample = frames[22].resize(size, Image.Resampling.LANCZOS)
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
    qa.save(PREVIEW_DIR / "qa_vaping_4_backgrounds.png")


def count_opaque_chroma_residue(image: Image.Image) -> int:
    count = 0
    for red, green, blue, alpha in image.get_flattened_data():
        for key in (INHALE_KEY, EXHALE_KEY):
            distance = max(
                abs(red - key[0]),
                abs(green - key[1]),
                abs(blue - key[2]),
            )
            if alpha >= 240 and distance <= 16:
                count += 1
                break
    return count


def count_partial_alpha(image: Image.Image) -> int:
    return sum(1 for *_, alpha in image.get_flattened_data() if 0 < alpha < 255)


def main() -> None:
    for directory in (FRAME_DIR, SHEET_DIR, PREVIEW_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    inhale = normalize_source(Image.open(INHALE_SOURCE).convert("RGBA"))
    exhale = normalize_source(Image.open(EXHALE_SOURCE).convert("RGBA"))
    frames = [render_inhale(inhale, index) for index in range(INHALE_FRAMES)]
    frames.extend(render_exhale(exhale, index) for index in range(EXHALE_FRAMES))

    for index, frame in enumerate(frames, start=1):
        frame.save(FRAME_DIR / f"{index:02d}_vaping.png")

    sheet = make_sheet(frames)
    sheet_path = SHEET_DIR / "berry_vaping_27f_9x3.png"
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
        raise RuntimeError("Rendered art or smoke touches a frame edge.")

    report = {
        "frame_count": len(frames),
        "fps": FPS,
        "duration_ms": round(len(frames) / FPS * 1000),
        "inhale_frames": INHALE_FRAMES,
        "inhale_duration_ms": round(INHALE_FRAMES / FPS * 1000),
        "exhale_frames": EXHALE_FRAMES,
        "exhale_duration_ms": round(EXHALE_FRAMES / FPS * 1000),
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
        "maximum_partial_alpha_pixels": max(count_partial_alpha(frame) for frame in frames),
    }
    (ROOT / "qa_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    print(
        f"Built {len(frames)} frames at {FPS} FPS: "
        f"{report['inhale_duration_ms']} ms inhale + "
        f"{report['exhale_duration_ms']} ms exhale."
    )
    print(f"Sheet: {sheet_path} ({sheet.width}x{sheet.height}, {sheet.mode})")
    print(
        "Maximum opaque chroma-key residue: "
        f"{report['opaque_chroma_key_residue_pixels']} pixels"
    )


if __name__ == "__main__":
    main()
