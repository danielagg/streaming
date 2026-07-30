"""Build Berry's two-cycle croaking throat-sac overlay for PNGTuber Remix."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "layers" / "00_base_underpaint.png"
EYES = ROOT.parent / "layers" / "10_eyes_open.png"
MOUTH = ROOT.parent / "layers" / "20_mouth_moustache_closed.png"
FRAMES = ROOT / "frames"
SHEETS = ROOT / "sheets"
PREVIEWS = ROOT / "previews"

CELL_SIZE = (512, 1254)
FPS = 8
FRAME_COUNT = 24
SHEET_GRID = (6, 4)
AUDIO_DURATION_SECONDS = 2.952125

# The vocal sac is a deformation of Berry's existing throat/chest paint. The
# source crop contains the green-to-cream transition and native brush texture.
THROAT_TEXTURE_BOX = (184, 370, 306, 530)
SAC_TOP_CENTER = (244, 343)
SAC_MAX_WIDTH = 228
SAC_MAX_HEIGHT = 188


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def cycle_scale(time_s: float, start: float, peak: float, end: float) -> float:
    if time_s < start or time_s >= end:
        return 0.0
    if time_s <= peak:
        return smoothstep((time_s - start) / (peak - start))
    return 1.0 - smoothstep((time_s - peak) / (end - peak))


def animation_scale(time_s: float) -> float:
    # Measured from Croak Twice.mp3:
    # phrase 1: approximately 0.10-1.18 s
    # phrase 2: approximately 1.64-2.74 s
    first = cycle_scale(time_s, 0.08, 0.84, 1.32)
    second = cycle_scale(time_s, 1.58, 2.36, 2.90)
    return max(first, second)


def render_overlay(base: Image.Image, scale: float) -> Image.Image:
    """Render a throat/chest deformation with no separate sac outline."""
    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    if scale < 0.035:
        return frame

    # A real frog's throat first broadens, then projects farther forward. The
    # shallow early frames are therefore wide before they become deep.
    width_progress = 0.42 + 0.58 * (scale**0.68)
    height_progress = scale**1.20
    width = max(4, round(SAC_MAX_WIDTH * width_progress))
    height = max(2, round(SAC_MAX_HEIGHT * height_progress))
    x = round(SAC_TOP_CENTER[0] - width / 2)
    y = SAC_TOP_CENTER[1]

    texture = base.crop(THROAT_TEXTURE_BOX).resize(
        (width, height), Image.Resampling.LANCZOS
    )
    rgba = np.asarray(texture, dtype=np.float32).copy()

    yy, xx = np.mgrid[0:height, 0:width]
    yn = yy / max(height - 1, 1)
    xn = np.abs((xx - (width - 1) / 2.0) / max(width / 2.0, 1.0))

    # Open-topped organic silhouette: broad attachment under the moustache,
    # fuller upper-middle, then a gently rounded lower contour.
    upper_t = np.clip(yn / 0.34, 0.0, 1.0)
    upper_smooth = upper_t * upper_t * (3.0 - 2.0 * upper_t)
    upper_width = 0.74 + 0.26 * upper_smooth
    lower_t = np.clip((yn - 0.34) / 0.66, 0.0, 1.0)
    lower_width = np.clip(1.0 - lower_t * lower_t, 0.0, 1.0) ** 0.34
    width_fraction = np.where(yn <= 0.34, upper_width, lower_width)

    edge_distance = (width_fraction - xn) * (width / 2.0)
    edge_alpha = np.clip(edge_distance / 15.0, 0.0, 1.0)
    edge_alpha = edge_alpha * edge_alpha * (3.0 - 2.0 * edge_alpha)

    # The top melts into Berry's existing throat rather than closing with a
    # visible line. The moustache layer then hides the physical attachment.
    top_blend_t = np.clip(yn / 0.15, 0.0, 1.0)
    top_blend = 0.62 + 0.38 * (
        top_blend_t * top_blend_t * (3.0 - 2.0 * top_blend_t)
    )

    local_x = np.divide(
        xn,
        np.maximum(width_fraction, 0.001),
        out=np.ones_like(xn),
        where=width_fraction > 0.001,
    )
    local_y = (yn - 0.42) / 0.72
    radial = np.clip(local_x * local_x + local_y * local_y, 0.0, 1.0)
    forward_depth = np.sqrt(1.0 - radial)

    # Volume comes from Berry's own painted texture plus restrained spherical
    # shading—not from a glossy highlight or a drawn perimeter.
    brightness = (
        0.91
        + 0.13 * forward_depth
        + 0.025 * (1.0 - local_x) * (1.0 - yn)
        - 0.12 * np.clip((yn - 0.70) / 0.30, 0.0, 1.0)
    )
    brightness = 1.0 + (brightness - 1.0) * scale
    rgba[..., :3] = np.clip(rgba[..., :3] * brightness[..., None], 0.0, 255.0)

    source_alpha = rgba[..., 3] / 255.0
    inflation_opacity = min(1.0, scale / 0.16)
    rgba[..., 3] = (
        255.0 * source_alpha * edge_alpha * top_blend * inflation_opacity
    )
    patch = Image.fromarray(np.clip(rgba, 0.0, 255.0).astype(np.uint8), "RGBA")

    # A soft contact shadow on the original chest is what makes the inflated
    # surface project toward the viewer. It is not an outline around the sac.
    shadow_alpha = Image.new("L", CELL_SIZE, 0)
    shadow_draw = ImageDraw.Draw(shadow_alpha)
    shadow_left = round(SAC_TOP_CENTER[0] - width * 0.42)
    shadow_right = round(SAC_TOP_CENTER[0] + width * 0.42)
    shadow_top = y + height - max(5, round(10 * scale))
    shadow_bottom = shadow_top + max(5, round(18 * scale))
    shadow_draw.ellipse(
        (shadow_left, shadow_top, shadow_right, shadow_bottom),
        fill=round(44 * (scale**1.35)),
    )
    shadow_alpha = shadow_alpha.filter(
        ImageFilter.GaussianBlur(max(2.5, 10.0 * scale))
    )
    shadow = Image.new("RGBA", CELL_SIZE, (71, 55, 27, 0))
    shadow.putalpha(shadow_alpha)
    frame.alpha_composite(shadow)
    frame.alpha_composite(patch, (x, y))
    return frame


def checkerboard(size: tuple[int, int], tile: int = 24) -> Image.Image:
    board = Image.new("RGBA", size, (231, 234, 237, 255))
    draw = ImageDraw.Draw(board)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle(
                    (x, y, x + tile - 1, y + tile - 1),
                    fill=(197, 202, 207, 255),
                )
    return board


def make_moustache_foreground(mouth: Image.Image) -> Image.Image:
    """Keep the moustache/mouth ink but remove its stationary cream chest patch."""
    rgba = np.asarray(mouth, dtype=np.uint8)
    rgb = rgba[..., :3].astype(np.float32)
    alpha = rgba[..., 3]
    yy, xx = np.mgrid[0:mouth.height, 0:mouth.width]
    luminance = (
        0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    )

    # The moustache and mouth ink are dark; the underpaint is pale cream.
    # A right-side positional guard removes the one dark olive panel boundary
    # that otherwise survives the colour separation.
    seed = (
        (alpha > 0)
        & (luminance < 188.0)
        & (yy <= 380)
        & ~((xx > 320) & (yy > 338))
    )
    mask = Image.fromarray((seed.astype(np.uint8) * 255), "L")
    mask = mask.filter(ImageFilter.MaxFilter(3)).filter(
        ImageFilter.GaussianBlur(0.55)
    )
    mask = Image.fromarray(
        np.minimum(np.asarray(mask, dtype=np.uint8), alpha), "L"
    )
    foreground = mouth.copy()
    foreground.putalpha(mask)
    return foreground


def composite_character(
    base: Image.Image,
    eyes: Image.Image,
    overlay: Image.Image,
    mouth: Image.Image,
) -> Image.Image:
    # Sac is intentionally between the body and the moustache.
    character = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    character.alpha_composite(base)
    character.alpha_composite(eyes)
    character.alpha_composite(overlay)
    character.alpha_composite(mouth)
    return character


def main() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    SHEETS.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)

    base = Image.open(BASE).convert("RGBA")
    eyes = Image.open(EYES).convert("RGBA")
    mouth = Image.open(MOUTH).convert("RGBA")
    for name, image in (("base", base), ("eyes", eyes), ("mouth", mouth)):
        if image.size != CELL_SIZE:
            raise RuntimeError(f"{name} is {image.size}, expected {CELL_SIZE}")

    moustache_foreground = make_moustache_foreground(mouth)
    moustache_foreground.save(ROOT / "croak_moustache_foreground.png", optimize=True)

    times = [index / FPS for index in range(FRAME_COUNT)]
    scales = [animation_scale(time_s) for time_s in times]
    overlays = [render_overlay(base, scale) for scale in scales]
    production_frames: list[Image.Image] = []
    for overlay in overlays:
        frame = overlay.copy()
        frame.alpha_composite(moustache_foreground)
        production_frames.append(frame)

    # The first and last frames must be empty, and the sequence must contain
    # exactly two separated visible cycles.
    if overlays[0].getchannel("A").getbbox() is not None:
        raise RuntimeError("The first frame is not transparent.")
    if overlays[-1].getchannel("A").getbbox() is not None:
        raise RuntimeError("The final frame is not transparent.")
    visible = [frame.getchannel("A").getbbox() is not None for frame in overlays]
    runs = 0
    in_run = False
    for value in visible:
        if value and not in_run:
            runs += 1
            in_run = True
        elif not value:
            in_run = False
    if runs != 2:
        raise RuntimeError(f"Expected two visible croak cycles, found {runs}.")

    for index, frame in enumerate(production_frames, start=1):
        frame.save(FRAMES / f"{index:02d}_croak_overlay.png", optimize=True)

    sheet = Image.new(
        "RGBA",
        (CELL_SIZE[0] * SHEET_GRID[0], CELL_SIZE[1] * SHEET_GRID[1]),
        (0, 0, 0, 0),
    )
    for index, frame in enumerate(production_frames):
        x = (index % SHEET_GRID[0]) * CELL_SIZE[0]
        y = (index // SHEET_GRID[0]) * CELL_SIZE[1]
        sheet.alpha_composite(frame, (x, y))
    sheet_path = SHEETS / "berry_croak_twice_overlay_24f_6x4.png"
    sheet.save(sheet_path, optimize=True)

    preview_frames: list[Image.Image] = []
    for overlay in overlays:
        board = checkerboard(CELL_SIZE)
        board.alpha_composite(
            composite_character(base, eyes, overlay, moustache_foreground)
        )
        preview = board.resize((384, 940), Image.Resampling.LANCZOS)
        preview_frames.append(
            preview.convert("P", palette=Image.Palette.ADAPTIVE, colors=255)
        )
    preview_frames[0].save(
        PREVIEWS / "berry_croak_twice_preview.gif",
        save_all=True,
        append_images=preview_frames[1:],
        duration=round(1000 / FPS),
        loop=0,
        disposal=2,
    )

    # Four easy-to-inspect moments: rest, first peak, gap, second peak.
    indices = (0, round(0.84 * FPS), round(1.46 * FPS), round(2.36 * FPS))
    labels = ("REST", "FIRST CROAK", "GAP", "SECOND CROAK")
    panel_size = (444, 500)
    contact = Image.new(
        "RGBA", (panel_size[0] * 2, panel_size[1] * 2), (245, 245, 245, 255)
    )
    for panel_index, (frame_index, label) in enumerate(zip(indices, labels)):
        canvas = checkerboard(CELL_SIZE)
        canvas.alpha_composite(
            composite_character(
                base, eyes, overlays[frame_index], moustache_foreground
            )
        )
        crop = canvas.crop((58, 170, 430, 650)).resize(
            (panel_size[0], panel_size[1] - 32), Image.Resampling.LANCZOS
        )
        panel = Image.new("RGBA", panel_size, (245, 245, 245, 255))
        ImageDraw.Draw(panel).text((10, 9), label, fill=(20, 20, 20, 255))
        panel.alpha_composite(crop, (0, 32))
        x = (panel_index % 2) * panel_size[0]
        y = (panel_index // 2) * panel_size[1]
        contact.alpha_composite(panel, (x, y))
    contact.save(PREVIEWS / "berry_croak_key_moments.png", optimize=True)

    # Show the first cycle as an actual outward deformation sequence.
    stage_indices = (0, 3, 5, 7, 9, 12)
    stage_labels = (
        "REST",
        "SHALLOW BULGE",
        "GROWING OUT",
        "FULL PROJECTION",
        "DEFLATING",
        "GAP",
    )
    stage_size = (360, 420)
    stages = Image.new(
        "RGBA",
        (stage_size[0] * 3, stage_size[1] * 2),
        (245, 245, 245, 255),
    )
    for panel_index, (frame_index, label) in enumerate(
        zip(stage_indices, stage_labels)
    ):
        canvas = checkerboard(CELL_SIZE)
        canvas.alpha_composite(
            composite_character(
                base, eyes, overlays[frame_index], moustache_foreground
            )
        )
        crop = canvas.crop((58, 170, 430, 650)).resize(
            (stage_size[0], stage_size[1] - 30), Image.Resampling.LANCZOS
        )
        panel = Image.new("RGBA", stage_size, (245, 245, 245, 255))
        ImageDraw.Draw(panel).text((9, 8), label, fill=(20, 20, 20, 255))
        panel.alpha_composite(crop, (0, 30))
        px = (panel_index % 3) * stage_size[0]
        py = (panel_index // 3) * stage_size[1]
        stages.alpha_composite(panel, (px, py))
    stages.save(PREVIEWS / "berry_croak_growth_stages.png", optimize=True)

    print(f"audio={AUDIO_DURATION_SECONDS:.6f}s")
    print(
        f"animation={FRAME_COUNT / FPS:.3f}s, fps={FPS}, "
        f"frames={FRAME_COUNT}, sheet={sheet.size}"
    )
    print("visible-runs=2")
    print(f"peak-scales={max(scales[:12]):.3f},{max(scales[12:]):.3f}")
    print(f"wrote={sheet_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
