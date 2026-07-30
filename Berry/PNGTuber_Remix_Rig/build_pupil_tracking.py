"""Build Berry's stationary irises and cursor-tracked black pupil layers.

The source eye layer remains untouched. At the neutral position, compositing the
three generated layers recreates the source artwork. Only the black pupil cores
and their white glints move; the cream whites, brown irises, and olive rims stay
stationary.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "layers" / "10_eyes_open.png"
BASE = ROOT / "layers" / "00_base_underpaint.png"
MOUTH = ROOT / "layers" / "20_mouth_moustache_closed.png"
OUTPUT = ROOT / "Pupil_Tracking"
PREVIEWS = OUTPUT / "previews"


@dataclass(frozen=True)
class Eye:
    pupil_center: tuple[int, int]
    pupil_radius: tuple[int, int]
    highlight_center: tuple[int, int]
    highlight_radius: tuple[int, int]
    cutout_center: tuple[int, int]
    cutout_radius: tuple[int, int]
    backing_radius: tuple[int, int]
    light_brown: tuple[int, int, int]
    dark_brown: tuple[int, int, int]


EYES = (
    Eye(
        pupil_center=(149, 255),
        pupil_radius=(12, 20),
        highlight_center=(145, 235),
        highlight_radius=(8, 9),
        cutout_center=(149, 253),
        cutout_radius=(17, 27),
        backing_radius=(20, 30),
        light_brown=(86, 55, 31),
        dark_brown=(24, 12, 7),
    ),
    Eye(
        pupil_center=(327, 267),
        pupil_radius=(17, 22),
        highlight_center=(315, 249),
        highlight_radius=(11, 12),
        cutout_center=(327, 264),
        cutout_radius=(22, 29),
        backing_radius=(26, 32),
        light_brown=(92, 58, 31),
        dark_brown=(25, 13, 7),
    ),
)


def ellipse_mask(
    size: tuple[int, int],
    center: tuple[int, int],
    radius: tuple[int, int],
    feather: float = 1.0,
) -> Image.Image:
    scale = 4
    mask = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = center
    rx, ry = radius
    draw.ellipse(
        (
            (cx - rx) * scale,
            (cy - ry) * scale,
            (cx + rx) * scale,
            (cy + ry) * scale,
        ),
        fill=255,
    )
    mask = mask.resize(size, Image.Resampling.LANCZOS)
    if feather:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    return mask


def make_iris_surface(
    size: tuple[int, int], eye: Eye, mask: Image.Image
) -> Image.Image:
    """Paint dark-brown iris texture behind the movable black pupil."""
    width, height = size
    cx, cy = eye.cutout_center
    rx, ry = eye.backing_radius

    yy, xx = np.mgrid[0:height, 0:width]
    nx = (xx - (cx - rx * 0.15)) / max(rx, 1)
    ny = (yy - (cy - ry * 0.20)) / max(ry, 1)
    radial = np.clip(np.sqrt(nx * nx + ny * ny), 0.0, 1.0)
    vertical = np.clip((yy - (cy - ry)) / max(2 * ry, 1), 0.0, 1.0)

    highlight = np.array(eye.light_brown, dtype=float)
    shadow = np.array(eye.dark_brown, dtype=float)
    mix = np.clip(radial * 0.55 + vertical * 0.18, 0.0, 1.0)[..., None]
    rgb = highlight * (1.0 - mix) + shadow * mix
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    rgba[..., 3] = np.asarray(mask, dtype=np.uint8)
    return Image.fromarray(rgba, "RGBA")


def make_pupil_art(size: tuple[int, int], eye: Eye) -> Image.Image:
    """Draw a neutral black pupil and white glint with no brown pixels."""
    width, height = size
    cx, cy = eye.pupil_center
    rx, ry = eye.pupil_radius
    pupil_mask = ellipse_mask(size, (cx, cy), (rx, ry), feather=0.45)

    yy, xx = np.mgrid[0:height, 0:width]
    nx = (xx - (cx - rx * 0.15)) / max(rx, 1)
    ny = (yy - (cy - ry * 0.20)) / max(ry, 1)
    radial = np.clip(np.sqrt(nx * nx + ny * ny), 0.0, 1.0)
    shade = np.clip(2.0 + radial * 10.0, 0.0, 14.0).astype(np.uint8)

    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[..., 0] = shade
    rgba[..., 1] = shade
    rgba[..., 2] = shade
    rgba[..., 3] = np.asarray(pupil_mask, dtype=np.uint8)
    pupil = Image.fromarray(rgba, "RGBA")

    highlight_mask = ellipse_mask(
        size, eye.highlight_center, eye.highlight_radius, feather=0.35
    )
    highlight = Image.new("RGBA", size, (255, 255, 255, 0))
    highlight.putalpha(highlight_mask)
    pupil.alpha_composite(highlight)
    return pupil


def offset_layer(layer: Image.Image, offset: tuple[int, int]) -> Image.Image:
    shifted = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    shifted.alpha_composite(layer, dest=offset)
    return shifted


def checkerboard(size: tuple[int, int], cell: int = 24) -> Image.Image:
    image = Image.new("RGBA", size, (232, 232, 232, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle(
                    (x, y, min(x + cell - 1, size[0]), min(y + cell - 1, size[1])),
                    fill=(196, 196, 196, 255),
                )
    return image


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)

    source = Image.open(SOURCE).convert("RGBA")
    size = source.size
    source_alpha = source.getchannel("A")

    cutout_mask = Image.new("L", size, 0)
    iris_backing = Image.new("RGBA", size, (0, 0, 0, 0))
    pupils = Image.new("RGBA", size, (0, 0, 0, 0))

    for eye in EYES:
        cutout = ellipse_mask(
            size, eye.cutout_center, eye.cutout_radius, feather=0.5
        )
        backing = ellipse_mask(
            size, eye.cutout_center, eye.backing_radius, feather=0.75
        )
        backing = ImageChops.darker(backing, source_alpha)
        cutout_mask = ImageChops.lighter(cutout_mask, cutout)
        iris_backing.alpha_composite(make_iris_surface(size, eye, backing))
        pupils.alpha_composite(make_pupil_art(size, eye))

    rims = source.copy()
    rims_alpha = rims.getchannel("A")
    rims_alpha = ImageChops.subtract(rims_alpha, cutout_mask)
    rims.putalpha(rims_alpha)
    rims_array = np.asarray(rims).copy()
    rims_array[rims_array[..., 3] == 0, :3] = 0
    rims = Image.fromarray(rims_array, "RGBA")

    whites_path = OUTPUT / "01_stationary_iris_backing.png"
    pupils_path = OUTPUT / "02_cursor_tracked_black_pupils.png"
    rims_path = OUTPUT / "03_stationary_whites_irises_and_rims.png"
    iris_backing.save(whites_path, optimize=True)
    pupils.save(pupils_path, optimize=True)
    rims.save(rims_path, optimize=True)

    base = Image.open(BASE).convert("RGBA")
    mouth = Image.open(MOUTH).convert("RGBA")

    offsets = (
        (0, 0),
        (-3, 0),
        (-3, -2),
        (0, -2),
        (3, -2),
        (3, 0),
        (3, 2),
        (0, 2),
        (-3, 2),
    )
    frames: list[Image.Image] = []
    for offset in offsets:
        frame = checkerboard(size)
        character = Image.new("RGBA", size, (0, 0, 0, 0))
        character.alpha_composite(base)
        character.alpha_composite(iris_backing)
        character.alpha_composite(offset_layer(pupils, offset))
        character.alpha_composite(rims)
        character.alpha_composite(mouth)
        frame.alpha_composite(character)
        frames.append(frame)

    preview = frames[0].crop((85, 165, 395, 340)).resize(
        (930, 525), Image.Resampling.LANCZOS
    )
    preview.save(PREVIEWS / "pupil_tracking_neutral.png", optimize=True)

    original = checkerboard(size)
    original_character = Image.new("RGBA", size, (0, 0, 0, 0))
    original_character.alpha_composite(base)
    original_character.alpha_composite(source)
    original_character.alpha_composite(mouth)
    original.alpha_composite(original_character)
    original_crop = original.crop((85, 165, 395, 340)).resize(
        (620, 350), Image.Resampling.LANCZOS
    )
    split_crop = frames[0].crop((85, 165, 395, 340)).resize(
        (620, 350), Image.Resampling.LANCZOS
    )
    comparison = Image.new("RGBA", (1240, 390), (245, 245, 245, 255))
    comparison.alpha_composite(original_crop, (0, 40))
    comparison.alpha_composite(split_crop, (620, 40))
    labels = ImageDraw.Draw(comparison)
    labels.text((12, 10), "ORIGINAL OPEN EYES", fill=(20, 20, 20, 255))
    labels.text((632, 10), "SPLIT LAYERS AT REST", fill=(20, 20, 20, 255))
    comparison.save(PREVIEWS / "qa_original_vs_split.png", optimize=True)

    gif_frames = [
        frame.crop((85, 165, 395, 340)).resize((620, 350), Image.Resampling.LANCZOS)
        for frame in frames
    ]
    gif_frames[0].save(
        PREVIEWS / "pupil_tracking_preview.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=280,
        loop=0,
        disposal=2,
    )

    reconstruction = Image.new("RGBA", size, (0, 0, 0, 0))
    reconstruction.alpha_composite(iris_backing)
    reconstruction.alpha_composite(pupils)
    reconstruction.alpha_composite(rims)
    difference = ImageChops.difference(source, reconstruction)
    difference_bbox = difference.getbbox()
    print(f"Wrote {whites_path.relative_to(ROOT)}")
    print(f"Wrote {pupils_path.relative_to(ROOT)}")
    print(f"Wrote {rims_path.relative_to(ROOT)}")
    print(f"Neutral reconstruction difference bbox: {difference_bbox}")


if __name__ == "__main__":
    main()
