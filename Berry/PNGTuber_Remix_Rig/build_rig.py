from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
LAYERS = ROOT / "layers"
SHEETS = ROOT / "sheets"
FRAMES = ROOT / "frames"
PREVIEWS = ROOT / "previews"

SOURCE_SIZE = (1254, 1254)
CROP_BOX = (350, 0, 862, 1254)
CANVAS_SIZE = (512, 1254)

SOURCE_NAMES = {
    "base": "base_blank_chroma.png",
    "eyes_open": "eyes_open_chroma.png",
    "eyes_half": "eyes_half_chroma.png",
    "eyes_deep": "eyes_quarter_chroma.png",
    "eyes_closed": "eyes_closed_chroma.png",
    "mouth_closed": "mouth_0_closed_chroma.png",
    "mouth_narrow": "mouth_1_narrow_chroma.png",
    "mouth_wide": "mouth_2_wide_chroma.png",
    "mouth_round": "mouth_3_round_chroma.png",
    "mouth_open": "mouth_4_open_chroma.png",
}

MOUTH_FRAME_MAP = [
    ("00_TH_CH_SH", "mouth_narrow"),
    ("01_S_Z", "mouth_narrow"),
    ("02_T_D", "mouth_narrow"),
    ("03_E", "mouth_wide"),
    ("04_F_V", "mouth_narrow"),
    ("05_I", "mouth_wide"),
    ("06_O", "mouth_round"),
    ("07_B_P_M", "mouth_closed"),
    ("08_R", "mouth_round"),
    ("09_U_OO", "mouth_round"),
    ("10_A_AH", "mouth_open"),
    ("11_G_K", "mouth_open"),
    ("12_L_N", "mouth_narrow"),
    ("13_SILENT", "mouth_closed"),
]

LAYER_FILENAMES = {
    "base": "00_base_underpaint.png",
    "eyes_open": "10_eyes_open.png",
    "eyes_half": "11_eyes_half.png",
    "eyes_deep": "12_eyes_three_quarter.png",
    "eyes_closed": "13_eyes_closed.png",
    "mouth_closed": "20_mouth_moustache_closed.png",
    "mouth_narrow": "21_mouth_moustache_narrow_teeth.png",
    "mouth_wide": "22_mouth_moustache_wide_E_I.png",
    "mouth_round": "23_mouth_moustache_round_O_R_U.png",
    "mouth_open": "24_mouth_moustache_open_A_G_K.png",
}


def load_rgb(name: str) -> Image.Image:
    image = Image.open(SOURCES / SOURCE_NAMES[name]).convert("RGB")
    if image.size != SOURCE_SIZE:
        raise ValueError(f"{name}: expected {SOURCE_SIZE}, got {image.size}")
    return image


def remove_magenta(image: Image.Image) -> Image.Image:
    """Remove only the generated magenta field, preserving pale belly and pink tongue."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    b = rgb[:, :, 2].astype(np.int16)

    magenta = (
        (r > 110)
        & (b > 100)
        & (g < 100)
        & ((r - g) > 55)
        & ((b - g) > 45)
    )

    alpha = np.where(magenta, 0, 255).astype(np.uint8)
    alpha_image = Image.fromarray(alpha, mode="L").filter(
        ImageFilter.GaussianBlur(radius=0.55)
    )
    alpha = np.asarray(alpha_image, dtype=np.uint8).copy()
    alpha[alpha < 12] = 0
    alpha[alpha > 243] = 255

    cleaned = rgb.copy()
    fringe = (
        (alpha > 0)
        & (r > 90)
        & (b > 80)
        & ((r - g) > 28)
        & ((b - g) > 25)
    )
    edge_cap = np.clip(g + 10, 0, 255).astype(np.uint8)
    cleaned[:, :, 0] = np.where(
        fringe, np.minimum(cleaned[:, :, 0], edge_cap), cleaned[:, :, 0]
    )
    cleaned[:, :, 2] = np.where(
        fringe, np.minimum(cleaned[:, :, 2], edge_cap), cleaned[:, :, 2]
    )

    rgba = np.dstack((cleaned, alpha))
    rgba[alpha == 0, :3] = 0
    return Image.fromarray(rgba, mode="RGBA")


def feature_zone(kind: str) -> Image.Image:
    zone = Image.new("L", SOURCE_SIZE, 0)
    draw = ImageDraw.Draw(zone)
    if kind == "eyes":
        draw.ellipse((452, 195, 548, 320), fill=255)
        draw.ellipse((612, 195, 735, 330), fill=255)
    elif kind == "mouth":
        draw.rounded_rectangle((405, 285, 735, 480), radius=32, fill=255)
    else:
        raise ValueError(kind)
    return zone


def retain_components(mask: Image.Image, min_area: int) -> Image.Image:
    data = np.asarray(mask, dtype=np.uint8) > 0
    height, width = data.shape
    seen = np.zeros_like(data, dtype=bool)
    kept = np.zeros_like(data, dtype=np.uint8)

    for y in range(height):
        for x in range(width):
            if not data[y, x] or seen[y, x]:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            component: list[tuple[int, int]] = []
            while stack:
                px, py = stack.pop()
                component.append((px, py))
                for nx, ny in (
                    (px - 1, py),
                    (px + 1, py),
                    (px, py - 1),
                    (px, py + 1),
                ):
                    if (
                        0 <= nx < width
                        and 0 <= ny < height
                        and data[ny, nx]
                        and not seen[ny, nx]
                    ):
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if len(component) >= min_area:
                for px, py in component:
                    kept[py, px] = 255
    return Image.fromarray(kept, mode="L")


def extract_feature(
    state_rgb: Image.Image,
    base_rgb: Image.Image,
    state_rgba: Image.Image,
    kind: str,
) -> Image.Image:
    state = np.asarray(state_rgb, dtype=np.int16)
    base = np.asarray(base_rgb, dtype=np.int16)
    difference = np.max(np.abs(state - base), axis=2)

    threshold = 18 if kind == "eyes" else 20
    raw_mask = Image.fromarray(
        np.where(difference > threshold, 255, 0).astype(np.uint8), mode="L"
    )
    raw_mask = Image.composite(raw_mask, Image.new("L", SOURCE_SIZE, 0), feature_zone(kind))
    raw_mask = retain_components(raw_mask, min_area=18 if kind == "eyes" else 28)
    raw_mask = raw_mask.filter(ImageFilter.MaxFilter(size=7))
    raw_mask = raw_mask.filter(ImageFilter.GaussianBlur(radius=0.8))

    state_alpha = state_rgba.getchannel("A")
    feature_alpha = Image.new("L", SOURCE_SIZE, 0)
    feature_alpha = Image.composite(raw_mask, feature_alpha, state_alpha)

    result = state_rgba.copy()
    result.putalpha(feature_alpha)
    return result


def crop(image: Image.Image) -> Image.Image:
    return image.crop(CROP_BOX)


def alpha_composite(*images: Image.Image) -> Image.Image:
    output = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    for image in images:
        output = Image.alpha_composite(output, image)
    return output


def make_sheet(images: list[Image.Image]) -> Image.Image:
    sheet = Image.new(
        "RGBA", (CANVAS_SIZE[0] * len(images), CANVAS_SIZE[1]), (0, 0, 0, 0)
    )
    for index, image in enumerate(images):
        sheet.alpha_composite(image, (index * CANVAS_SIZE[0], 0))
    return sheet


def checker_background(size: tuple[int, int], square: int = 24) -> Image.Image:
    width, height = size
    bg = Image.new("RGB", size, (235, 235, 235))
    draw = ImageDraw.Draw(bg)
    for y in range(0, height, square):
        for x in range(0, width, square):
            if ((x // square) + (y // square)) % 2:
                draw.rectangle(
                    (x, y, min(x + square - 1, width), min(y + square - 1, height)),
                    fill=(202, 202, 202),
                )
    return bg


def flatten_on(image: Image.Image, color: tuple[int, int, int] | None) -> Image.Image:
    background = (
        checker_background(image.size)
        if color is None
        else Image.new("RGB", image.size, color)
    )
    background.paste(image, mask=image.getchannel("A"))
    return background


def build_previews(
    base: Image.Image,
    eyes: dict[str, Image.Image],
    mouths: dict[str, Image.Image],
) -> None:
    idle = alpha_composite(base, eyes["eyes_open"], mouths["mouth_closed"])
    idle.save(PREVIEWS / "preview_idle_transparent.png")

    blink_states = [
        alpha_composite(base, eyes["eyes_open"], mouths["mouth_closed"]),
        alpha_composite(base, eyes["eyes_half"], mouths["mouth_closed"]),
        alpha_composite(base, eyes["eyes_deep"], mouths["mouth_closed"]),
        alpha_composite(base, eyes["eyes_closed"], mouths["mouth_closed"]),
        alpha_composite(base, eyes["eyes_deep"], mouths["mouth_closed"]),
        alpha_composite(base, eyes["eyes_half"], mouths["mouth_closed"]),
    ]
    blink_frames = [
        flatten_on(frame, (50, 185, 205)).resize((256, 627), Image.Resampling.LANCZOS)
        for frame in blink_states
    ]
    blink_frames[0].save(
        PREVIEWS / "preview_blink.gif",
        save_all=True,
        append_images=blink_frames[1:],
        duration=[650, 55, 55, 80, 55, 55],
        loop=0,
        disposal=2,
    )

    blink_contact = Image.new(
        "RGB",
        (192 * len(blink_states), 470 * 4),
        (128, 128, 128),
    )
    for row, background in enumerate(
        [None, (255, 255, 255), (12, 12, 12), (0, 210, 220)]
    ):
        for column, state in enumerate(blink_states):
            thumb = flatten_on(state, background).resize(
                (192, 470), Image.Resampling.LANCZOS
            )
            blink_contact.paste(thumb, (column * 192, row * 470))
    blink_contact.save(PREVIEWS / "qa_blink_states_4_backgrounds.png")

    mouth_order = [
        "mouth_closed",
        "mouth_narrow",
        "mouth_wide",
        "mouth_round",
        "mouth_open",
    ]
    talk_states = [
        alpha_composite(base, eyes["eyes_open"], mouths[name]) for name in mouth_order
    ]
    talk_frames = [
        flatten_on(frame, (50, 185, 205)).resize((256, 627), Image.Resampling.LANCZOS)
        for frame in talk_states
    ]
    talk_frames[0].save(
        PREVIEWS / "preview_visemes.gif",
        save_all=True,
        append_images=talk_frames[1:] + talk_frames[-2:0:-1],
        duration=170,
        loop=0,
        disposal=2,
    )

    backgrounds = [None, (255, 255, 255), (12, 12, 12), (0, 210, 220)]
    thumb_size = (192, 470)
    contact = Image.new(
        "RGB",
        (thumb_size[0] * len(talk_states), thumb_size[1] * len(backgrounds)),
        (128, 128, 128),
    )
    for row, background in enumerate(backgrounds):
        for column, state in enumerate(talk_states):
            thumb = flatten_on(state, background).resize(
                thumb_size, Image.Resampling.LANCZOS
            )
            contact.paste(thumb, (column * thumb_size[0], row * thumb_size[1]))
    contact.save(PREVIEWS / "qa_mouth_states_4_backgrounds.png")


def alpha_stats(image: Image.Image) -> dict[str, int]:
    alpha = np.asarray(image.getchannel("A"), dtype=np.uint8)
    return {
        "transparent": int(np.count_nonzero(alpha == 0)),
        "partial": int(np.count_nonzero((alpha > 0) & (alpha < 255))),
        "opaque": int(np.count_nonzero(alpha == 255)),
    }


def main() -> None:
    for directory in (LAYERS, SHEETS, FRAMES, PREVIEWS):
        directory.mkdir(parents=True, exist_ok=True)

    rgb_sources = {name: load_rgb(name) for name in SOURCE_NAMES}
    keyed_sources = {name: remove_magenta(image) for name, image in rgb_sources.items()}

    base = crop(keyed_sources["base"])
    base.save(LAYERS / LAYER_FILENAMES["base"])

    eyes: dict[str, Image.Image] = {}
    for name in ("eyes_open", "eyes_half", "eyes_deep", "eyes_closed"):
        layer = extract_feature(
            rgb_sources[name],
            rgb_sources["base"],
            keyed_sources[name],
            kind="eyes",
        )
        eyes[name] = crop(layer)
        eyes[name].save(LAYERS / LAYER_FILENAMES[name])

    mouths: dict[str, Image.Image] = {}
    for name in (
        "mouth_closed",
        "mouth_narrow",
        "mouth_wide",
        "mouth_round",
        "mouth_open",
    ):
        layer = extract_feature(
            rgb_sources[name],
            rgb_sources["base"],
            keyed_sources[name],
            kind="mouth",
        )
        mouths[name] = crop(layer)
        mouths[name].save(LAYERS / LAYER_FILENAMES[name])

    blink_frames = [
        eyes["eyes_open"],
        eyes["eyes_half"],
        eyes["eyes_deep"],
        eyes["eyes_closed"],
        eyes["eyes_deep"],
        eyes["eyes_half"],
    ]
    make_sheet(blink_frames).save(SHEETS / "11_eyes_blink_6x1.png")
    make_sheet(
        [
            eyes["eyes_open"],
            eyes["eyes_half"],
            eyes["eyes_closed"],
            eyes["eyes_half"],
        ]
    ).save(SHEETS / "11_eyes_blink_4x1.png")

    viseme_frames = [mouths[state] for _, state in MOUTH_FRAME_MAP]
    make_sheet(viseme_frames).save(SHEETS / "20_mouth_moustache_visemes_14x1.png")

    for index, (label, state) in enumerate(MOUTH_FRAME_MAP):
        frame_path = FRAMES / f"{index:02d}_{label[3:]}.png"
        mouths[state].save(frame_path)

    build_previews(base, eyes, mouths)

    base_alpha = np.asarray(base.getchannel("A"), dtype=np.uint8)
    dynamic_union = np.zeros((CANVAS_SIZE[1], CANVAS_SIZE[0]), dtype=bool)
    for layer in [*eyes.values(), *mouths.values()]:
        dynamic_union |= np.asarray(layer.getchannel("A"), dtype=np.uint8) > 0

    covered_by_base = dynamic_union & (base_alpha > 0)
    intentional_overhang = dynamic_union & (base_alpha == 0)
    coverage_ratio = (
        float(np.count_nonzero(covered_by_base)) / float(np.count_nonzero(dynamic_union))
        if np.count_nonzero(dynamic_union)
        else 1.0
    )

    report = {
        "canvas": {"width": CANVAS_SIZE[0], "height": CANVAS_SIZE[1]},
        "crop_box_from_generated_sources": list(CROP_BOX),
        "base_alpha": alpha_stats(base),
        "layer_alpha": {
            name: alpha_stats(layer)
            for name, layer in {**eyes, **mouths}.items()
        },
        "dynamic_pixels_covered_by_base_ratio": round(coverage_ratio, 6),
        "dynamic_overhang_pixels": int(np.count_nonzero(intentional_overhang)),
        "note": (
            "Overhang pixels are expected at moustache curl tips and antialiased "
            "outer-eye contours; face roots remain painted in the base."
        ),
        "mouth_frame_map": [
            {"frame": index, "label": label[3:], "art_state": state}
            for index, (label, state) in enumerate(MOUTH_FRAME_MAP)
        ],
    }
    (ROOT / "qa_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
