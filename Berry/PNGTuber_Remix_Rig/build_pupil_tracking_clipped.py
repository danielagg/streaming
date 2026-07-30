"""Rebuild Berry's pupil tracking as a real PNGTuber Remix clipping rig.

The untouched open-eye layer is not split by colour. Instead, each complete
original iris (including its old pupil and highlight) is removed wholesale.
Clean stationary irises are repainted as the visible clipping parent, and a
new achromatic pupil layer becomes its mouse-follow child.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "layers" / "10_eyes_open.png"
BASE = ROOT / "layers" / "00_base_underpaint.png"
MOUTH = ROOT / "layers" / "20_mouth_moustache_closed.png"
OUTPUT = ROOT / "Pupil_Tracking"
PREVIEWS = OUTPUT / "previews"

SUPERSAMPLE = 4
TRAVEL_OFFSETS = (
    (0, 0),
    (-5, 0),
    (-5, -3),
    (0, -3),
    (5, -3),
    (5, 0),
    (5, 3),
    (0, 3),
    (-5, 3),
)


@dataclass(frozen=True)
class Eye:
    iris_center: tuple[float, float]
    iris_radius: tuple[float, float]
    pupil_center: tuple[float, float]
    pupil_radius: tuple[float, float]
    glint_center: tuple[float, float]
    glint_radius: tuple[float, float]


EYES = (
    Eye(
        iris_center=(149.0, 252.5),
        iris_radius=(22.5, 32.5),
        pupil_center=(149.0, 253.5),
        pupil_radius=(15.5, 24.5),
        glint_center=(143.5, 236.0),
        glint_radius=(7.0, 8.0),
    ),
    Eye(
        iris_center=(324.5, 263.5),
        iris_radius=(31.5, 37.0),
        pupil_center=(325.0, 265.0),
        pupil_radius=(21.5, 27.0),
        glint_center=(314.5, 247.5),
        glint_radius=(10.0, 10.5),
    ),
)


def high_res_ellipse_mask(
    size: tuple[int, int],
    center: tuple[float, float],
    radius: tuple[float, float],
) -> Image.Image:
    """Return an antialiased ellipse mask."""
    scale = SUPERSAMPLE
    mask = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = center
    rx, ry = radius
    draw.ellipse(
        (
            round((cx - rx) * scale),
            round((cy - ry) * scale),
            round((cx + rx) * scale),
            round((cy + ry) * scale),
        ),
        fill=255,
    )
    return mask.resize(size, Image.Resampling.LANCZOS)


def union_masks(masks: list[Image.Image], size: tuple[int, int]) -> Image.Image:
    result = Image.new("L", size, 0)
    for mask in masks:
        result = ImageChops.lighter(result, mask)
    return result


def paint_stationary_iris(size: tuple[int, int], eye: Eye) -> Image.Image:
    """Paint one complete pupil-free iris, including its dark stationary rim."""
    width, height = size
    cx, cy = eye.iris_center
    rx, ry = eye.iris_radius
    yy, xx = np.mgrid[0:height, 0:width]

    nx = (xx - cx) / rx
    ny = (yy - cy) / ry
    radial = np.sqrt(nx * nx + ny * ny)

    # The outer band is the stationary iris outline. The inner field stays
    # unmistakably brown everywhere; no black pupil-shaped area is retained.
    inner_top = np.array((111.0, 73.0, 42.0))
    inner_bottom = np.array((55.0, 32.0, 18.0))
    vertical = np.clip((ny + 1.0) * 0.5, 0.0, 1.0)[..., None]
    rgb = inner_top * (1.0 - vertical) + inner_bottom * vertical

    light = np.exp(
        -(
            ((xx - (cx - 0.24 * rx)) / (0.72 * rx)) ** 2
            + ((yy - (cy - 0.30 * ry)) / (0.72 * ry)) ** 2
        )
    )[..., None]
    rgb = np.clip(rgb + light * np.array((13.0, 9.0, 5.0)), 0.0, 255.0)

    edge_start = 0.80
    edge_mix = np.clip((radial - edge_start) / (1.0 - edge_start), 0.0, 1.0)[
        ..., None
    ]
    edge_colour = np.array((24.0, 14.0, 8.0))
    rgb = rgb * (1.0 - edge_mix) + edge_colour * edge_mix

    alpha = np.asarray(
        high_res_ellipse_mask(size, eye.iris_center, eye.iris_radius),
        dtype=np.uint8,
    )
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[..., :3] = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
    rgba[..., 3] = alpha
    return Image.fromarray(rgba, "RGBA")


def paint_moving_pupil(size: tuple[int, int], eye: Eye) -> Image.Image:
    """Paint one grayscale pupil and its attached white glint."""
    width, height = size
    cx, cy = eye.pupil_center
    rx, ry = eye.pupil_radius
    yy, xx = np.mgrid[0:height, 0:width]

    pupil_mask = high_res_ellipse_mask(size, eye.pupil_center, eye.pupil_radius)
    radial = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    shade = np.clip(3.0 + radial * 7.0, 3.0, 10.0).astype(np.uint8)

    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[..., 0] = shade
    rgba[..., 1] = shade
    rgba[..., 2] = shade
    rgba[..., 3] = np.asarray(pupil_mask, dtype=np.uint8)
    result = Image.fromarray(rgba, "RGBA")

    glint_mask = high_res_ellipse_mask(size, eye.glint_center, eye.glint_radius)
    glint = Image.new("RGBA", size, (255, 255, 255, 0))
    glint.putalpha(glint_mask)
    result.alpha_composite(glint)
    return result


def offset_layer(layer: Image.Image, offset: tuple[int, int]) -> Image.Image:
    shifted = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    shifted.alpha_composite(layer, dest=offset)
    return shifted


def clip_child(child: Image.Image, parent_alpha: Image.Image) -> Image.Image:
    """Simulate Remix's Clip Children result for preview and QA."""
    clipped = child.copy()
    clipped.putalpha(ImageChops.multiply(child.getchannel("A"), parent_alpha))
    return clipped


def checkerboard(size: tuple[int, int], cell: int = 24) -> Image.Image:
    image = Image.new("RGBA", size, (231, 234, 237, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle(
                    (x, y, x + cell - 1, y + cell - 1),
                    fill=(197, 202, 207, 255),
                )
    return image


def compose_character(
    base: Image.Image,
    iris_parent: Image.Image,
    pupil_child: Image.Image,
    sclera_rims: Image.Image,
    mouth: Image.Image,
    offset: tuple[int, int],
) -> Image.Image:
    result = Image.new("RGBA", base.size, (0, 0, 0, 0))
    result.alpha_composite(base)
    result.alpha_composite(iris_parent)
    shifted = offset_layer(pupil_child, offset)
    result.alpha_composite(clip_child(shifted, iris_parent.getchannel("A")))
    result.alpha_composite(sclera_rims)
    result.alpha_composite(mouth)
    return result


def label_panel(image: Image.Image, label: str) -> Image.Image:
    panel = Image.new("RGBA", (image.width, image.height + 34), (245, 245, 245, 255))
    panel.alpha_composite(image, (0, 34))
    ImageDraw.Draw(panel).text((10, 10), label, fill=(20, 20, 20, 255))
    return panel


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)

    source = Image.open(SOURCE).convert("RGBA")
    base = Image.open(BASE).convert("RGBA")
    mouth = Image.open(MOUTH).convert("RGBA")
    size = source.size

    iris_masks = [
        high_res_ellipse_mask(size, eye.iris_center, eye.iris_radius)
        for eye in EYES
    ]
    all_iris_mask = union_masks(iris_masks, size)

    # Remove the complete old iris/pupil/highlight regions in one operation.
    # This is deliberately geometric rather than based on dark/brown colours.
    sclera_rims = source.copy()
    sclera_rims.putalpha(
        ImageChops.multiply(source.getchannel("A"), ImageChops.invert(all_iris_mask))
    )

    iris_parent = Image.new("RGBA", size, (0, 0, 0, 0))
    pupil_child = Image.new("RGBA", size, (0, 0, 0, 0))
    for eye in EYES:
        iris_parent.alpha_composite(paint_stationary_iris(size, eye))
        pupil_child.alpha_composite(paint_moving_pupil(size, eye))

    # Remove hidden RGB from transparent pixels to keep imported layers clean.
    for image in (iris_parent, pupil_child, sclera_rims):
        array = np.asarray(image).copy()
        array[array[..., 3] == 0, :3] = 0
        image.paste(Image.fromarray(array, "RGBA"))

    iris_path = OUTPUT / "01_CLIP_PARENT_stationary_clean_irises.png"
    pupil_path = OUTPUT / "02_CHILD_cursor_black_pupils.png"
    overlay_path = OUTPUT / "03_TOP_stationary_sclera_and_rims.png"
    iris_parent.save(iris_path, optimize=True)
    pupil_child.save(pupil_path, optimize=True)
    sclera_rims.save(overlay_path, optimize=True)

    # Automated guarantees.
    pupil_array = np.asarray(pupil_child)
    visible = pupil_array[..., 3] > 0
    assert np.array_equal(pupil_array[..., 0][visible], pupil_array[..., 1][visible])
    assert np.array_equal(pupil_array[..., 1][visible], pupil_array[..., 2][visible])

    for eye in EYES:
        inner = high_res_ellipse_mask(
            size,
            eye.iris_center,
            (eye.iris_radius[0] * 0.66, eye.iris_radius[1] * 0.66),
        )
        inner_pixels = np.asarray(inner) > 240
        iris_array = np.asarray(iris_parent)
        # A clean stationary iris has no black pupil or white glint.
        luminance = iris_array[..., :3][inner_pixels].mean(axis=1)
        assert luminance.min() >= 30.0
        assert luminance.max() <= 145.0

    for offset in TRAVEL_OFFSETS:
        shifted = offset_layer(pupil_child, offset)
        clipped = clip_child(shifted, iris_parent.getchannel("A"))
        child_alpha = np.asarray(clipped.getchannel("A"), dtype=np.uint16)
        parent_alpha = np.asarray(iris_parent.getchannel("A"), dtype=np.uint16)
        assert np.all(child_alpha <= parent_alpha)

    crop_box = (92, 175, 388, 325)
    preview_size = (888, 450)

    frames: list[Image.Image] = []
    for offset in TRAVEL_OFFSETS:
        canvas = checkerboard(size)
        canvas.alpha_composite(
            compose_character(
                base, iris_parent, pupil_child, sclera_rims, mouth, offset
            )
        )
        frames.append(
            canvas.crop(crop_box).resize(preview_size, Image.Resampling.LANCZOS)
        )

    frames[0].save(PREVIEWS / "01_neutral.png", optimize=True)
    frames[1].save(PREVIEWS / "02_full_left.png", optimize=True)
    frames[5].save(PREVIEWS / "03_full_right.png", optimize=True)
    frames[0].save(
        PREVIEWS / "pupil_tracking_clipped_preview.gif",
        save_all=True,
        append_images=frames[1:],
        duration=300,
        loop=0,
        disposal=2,
    )

    original_canvas = checkerboard(size)
    original_character = Image.new("RGBA", size, (0, 0, 0, 0))
    original_character.alpha_composite(base)
    original_character.alpha_composite(source)
    original_character.alpha_composite(mouth)
    original_canvas.alpha_composite(original_character)

    no_pupil_canvas = checkerboard(size)
    no_pupil_character = Image.new("RGBA", size, (0, 0, 0, 0))
    no_pupil_character.alpha_composite(base)
    no_pupil_character.alpha_composite(iris_parent)
    no_pupil_character.alpha_composite(sclera_rims)
    no_pupil_character.alpha_composite(mouth)
    no_pupil_canvas.alpha_composite(no_pupil_character)

    panels = []
    panel_specs = (
        (original_canvas, "ORIGINAL"),
        (no_pupil_canvas, "CLEAN STATIONARY EYES - NO PUPILS"),
    )
    for image, label in panel_specs:
        crop = image.crop(crop_box).resize((592, 300), Image.Resampling.LANCZOS)
        panels.append(label_panel(crop, label))
    for frame, label in (
        (frames[0].resize((592, 300), Image.Resampling.LANCZOS), "NEW NEUTRAL"),
        (frames[1].resize((592, 300), Image.Resampling.LANCZOS), "FULL LEFT - CLIPPED"),
    ):
        panels.append(label_panel(frame, label))

    qa = Image.new("RGBA", (1184, 668), (245, 245, 245, 255))
    qa.alpha_composite(panels[0], (0, 0))
    qa.alpha_composite(panels[1], (592, 0))
    qa.alpha_composite(panels[2], (0, 334))
    qa.alpha_composite(panels[3], (592, 334))
    qa.save(PREVIEWS / "qa_clean_rebuild.png", optimize=True)

    print(f"Wrote {iris_path.relative_to(ROOT)}")
    print(f"Wrote {pupil_path.relative_to(ROOT)}")
    print(f"Wrote {overlay_path.relative_to(ROOT)}")
    print("QA passed: stationary irises contain no black pupil or white glint")
    print("QA passed: moving layer is achromatic")
    print("QA passed: every tested pupil position is clipped to the iris parent")


if __name__ == "__main__":
    main()
