# Berry — Vaping

This add-on covers Berry while the streamer takes a vape break. Berry takes a
steady `1.5-second` drag, lowers the device, then exhales a curling smoke plume
for `3 seconds`.

## Production file

Import:

`sheets/berry_vaping_27f_9x3.png`

The sheet contains 27 transparent `720 × 1292` cells in reading order. At
`6 FPS`, the one-shot lasts exactly `4.5 seconds`:

- Frames 1–9: inhale (`1.5 seconds`)
- Frames 10–27: exhale (`3 seconds`)

Berry's visible body is calibrated to `1164 px`, closely matching the normal
idle body's `1172 px` footprint. Start at Remix Size X/Y `1.00`.

## PNGTuber Remix setup

1. Save a backup of the current `.pngRemix` model.
2. In **Settings → Import**, disable **Crop Images to Content**.
3. Add a state named exactly `Vaping`.
4. Hide the normal Berry rig objects in that state.
5. Import the production sheet as one Sprite object and name it `Berry_Vaping`.
6. Set:
   - Horizontal Frames: `9`
   - Vertical Frames: `3`
   - Animation Speed: `6 FPS`
   - Reset Animation: `On`
   - One Shot: `On`
   - Reset on State Change: `On`
   - Should Talk: `Disabled`
   - Should Blink: `Disabled`
   - Ignore Bounce: `On`
   - Enable Physics: `Off`
   - Z Order: `0`
7. Use **Pause Movement** while aligning the sprite. Start at Size X/Y `1.00`,
   keep both values identical, then align Berry by his feet and body centerline.
8. Command Deck exposes Vaping as action `08`. The legacy helper uses a
   triple-tap of `F20`; do not also bind F20 inside Remix.

## Files

- `sources/vaping_inhale_chroma.png`: generated inhale chroma master
- `sources/vaping_inhale.png`: transparent inhale key pose
- `sources/vaping_exhale_chroma.png`: generated exhale chroma master
- `sources/vaping_exhale.png`: transparent exhale key pose
- `frames/`: all 27 transparent animation cells
- `sheets/berry_vaping_27f_9x3.png`: Remix production sheet
- `previews/vaping_preview.gif`: final 6 FPS timing preview
- `previews/vaping_key_moments.png`: inhale and plume development
- `previews/qa_vaping_4_backgrounds.png`: smoke and edge QA
- `qa_report.json`: timing, scale, alpha, clipping, and residue checks
- `build_vaping.py`: deterministic motion, smoke, sheet, preview, and QA builder

Run `python build_vaping.py` from this directory to rebuild everything.
