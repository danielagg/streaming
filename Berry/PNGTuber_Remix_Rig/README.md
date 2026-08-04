# Berry — PNGTuber Remix rig pack

This pack turns `Draft.png` into an occlusion-safe PNGTuber Remix setup with:

- a fully painted body/head foundation with no eye, mouth, or moustache holes;
- a synchronized four-frame blink;
- five distinct speech drawings mapped across Remix's required 14 advanced-lip-sync frames;
- a moustache pose baked into every mouth state, so the moustache moves with the mic-driven mouth without desynchronizing or exposing a face gap.

All production PNGs use RGBA transparency. Static and individual-state layers share the same **512 × 1254** canvas and origin.

## Files to import

Import these three production assets:

1. `layers/00_base_underpaint.png`
2. `sheets/11_eyes_blink_6x1.png`
3. `sheets/20_mouth_moustache_visemes_14x1.png`

For the normal open-eye object, import:

4. `layers/10_eyes_open.png`

The other files in `layers/` and `frames/` are editable/diagnostic versions of the same states.

## Optional pupil-only cursor tracking

The `Pupil_Tracking/` add-on replaces the single normal open-eye object with
three stacked objects: stationary eye whites, cursor-tracked pupils, and a
stationary rim overlay. This makes only Berry's pupils/irises follow the mouse;
the eye sockets themselves do not move.

See `Pupil_Tracking/README.md` for the import order and recommended Remix
settings. The existing blink sheet and `Whiskey Sip` state remain unchanged.

## Suggested layer tree and settings

Use this order from back to front:

```text
Berry_Face_Rig
├─ 00_base_underpaint
├─ 20_mouth_moustache_visemes_14x1
├─ 10_eyes_open
└─ 11_eyes_blink_4x1
```

Keep all four objects at the same position, scale, and pivot. Disable automatic transparent-edge trimming if the importer offers that option; the common full canvas is intentional.

### Base

- Animation: off/static
- Talk: off
- Blink: off

The nostrils, hat, body, belly, limbs, and all static shading are baked here. Do not erase the blank face areas: that underpaint is what prevents holes during state changes.

### Open eyes

- `Should Blink`: on
- `Eye Open`: on
- Animation: off/static

### Blink sheet

- Horizontal Frames: `6`
- Vertical Frames: `1`
- Frame order: open → half → three-quarter → closed → three-quarter → half
- `Should Blink`: on
- `Eye Open`: off/closed-eye object
- One Shot: on
- Reset animation on blink: on
- Animation speed: about `18 fps`

Start around the default global blink duration/chance. The brief transition frames make the eyelid travel visible without turning the blink into a held sleepy expression. A simpler four-frame compatibility sheet is also included; use the six-frame sheet by default.

### Mouth + moving moustache sheet

- Advanced Lip Sync: on
- Horizontal Frames: `14` (Remix also forces this in advanced mode)
- Vertical Frames: `1`
- Ordinary `Should Talk`: off
- Keep this object visible in both idle and talking states

Frame 13 is the silent/rest frame. The sheet combines mouth and moustache in every cell; do not add a second static moustache on the base.

## Advanced lip-sync frame map

| Frame | Sound group | Drawing used |
|---:|---|---|
| 0 | TH / CH / SH | Narrow/teeth |
| 1 | S / Z | Narrow/teeth |
| 2 | T / D | Narrow/teeth |
| 3 | E | Wide |
| 4 | F / V | Narrow/teeth |
| 5 | I | Wide |
| 6 | O | Round |
| 7 | B / P / M | Closed |
| 8 | R | Round |
| 9 | U / OO | Round |
| 10 | A / AH | Open |
| 11 | G / K | Open |
| 12 | L / N | Narrow/teeth |
| 13 | Silence | Closed |

This gives five visibly different mouth positions while satisfying Remix's current advanced-lip-sync indexing.

## Calibration and QA

1. Calibrate advanced lip sync against the microphone you will stream with.
2. In Preview mode, force a blink while speaking. The eye and speech systems are independent and should work simultaneously.
3. Inspect `previews/preview_blink.gif` and `previews/preview_visemes.gif`.
4. Inspect both four-background QA sheets. They test checkerboard, white, black, and cyan so pale holes, dark seams, pink fringe, and stray pixels are easy to spot.
5. If you move or scale an object, apply the exact same transform to every rig object.

The generated base is opaque beneath the facial swap zones. The only intended dynamic overhang is the moustache curl silhouette and antialiased outer contours.

## Current Remix references

- [PNGTuber Remix V1.4.6 release](https://github.com/MudkipWorld/PNGTuber-Remix/releases/tag/V1.4.6)
- [Official documentation](https://mudkipworld.github.io/PNGRemix-Doc/)
- [Advanced lip-sync implementation](https://github.com/MudkipWorld/PNGTuber-Remix/blob/1.4.x/Scripts/Objects/sprite_object.gd)
- [Current phoneme index enum](https://github.com/MudkipWorld/PNGTuber-Remix/blob/1.4.x/UI/Lipsync%20stuff/godot-lip-sync/phonemes.gd)

Remix is still under active development, so a future release may rename UI labels while keeping the same concepts.

## Rebuilding

`build_rig.py` is the deterministic assembly and QA script. It removes the flat magenta generation background without treating the pale belly or pink tongue as background, extracts facial differences, constructs the sprite sheets, and regenerates previews plus `qa_report.json`.

The `sources/` directory contains the non-destructive chroma-key source renders. The original `Berry/Draft.png` is untouched.

## Unified animation hotkeys

Open `Start Berry Actions.cmd` once while streaming. It maintains one local
WebSocket connection to Remix and handles the one-shot animations:

- Triple-tap `F13`: Whiskey Sip for 2 seconds
- Triple-tap `F14`: Croak once with synchronized audio
- Triple-tap `F15`: Fly Catch for 1.4 seconds
- Triple-tap `F16`: Angry Tremble for 1.4 seconds
- Triple-tap `F17`: Embarrassed Sway for 2.1 seconds
- Triple-tap `F18`: Surprised Hop for 1.4 seconds
- Triple-tap `F19`: Understanding Nod for 2.1 seconds

The helper remembers and restores whichever normal state was active. Keep the
Remix states named exactly `Whiskey Sip`, `Croaking`, `Fly Catch`, `Angry`,
`Embarrassed`, `Surprised`, and `Understanding`, start Remix's WebSocket server
on port `9321`, and do not also bind F13/F14/F15/F16/F17/F18/F19 inside Remix.
