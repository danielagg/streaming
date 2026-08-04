# Berry — Surprised Hop

This add-on is Berry's quick comic surprise reaction for PNGTuber Remix. He
compresses for a beat, springs into a wide-eyed airborne gasp as two exclamation
marks pop beside him, then lands with a short squash and settles back to idle.

## Production file

Import:

`sheets/berry_surprised_hop_16f_4x4.png`

The sheet contains 16 transparent `720 × 1292` cells in reading order. At
`12 FPS`, the one-shot lasts `1.333 seconds`.

Both poses are calibrated to Berry's normal `1172 px` visible-body footprint;
the generated hop pose is set to `1164 px`, matching the corrected scale used by
Embarrassed. Start at Remix Size X/Y `1.00`.

## PNGTuber Remix setup

1. Save a backup of the current `.pngRemix` model.
2. In **Settings → Import**, disable **Crop Images to Content**.
3. Add a state named exactly `Surprised`.
4. Hide the normal Berry rig objects in that state.
5. Import the production sheet as one Sprite object and name it
   `Berry_Surprised_Hop`.
6. Set:
   - Horizontal Frames: `4`
   - Vertical Frames: `4`
   - Animation Speed: `12 FPS`
   - Reset Animation: `On`
   - One Shot: `On`
   - Reset on State Change: `On`
   - Should Talk: `Disabled`
   - Should Blink: `Disabled`
   - Ignore Bounce: `On`
   - Enable Physics: `Off`
   - Z Order: `0`
7. Use **Pause Movement** while aligning the sprite. Start at Size X/Y `1.00`,
   keep both values identical, then align Berry by his resting feet and body
   centerline.
8. Command Deck exposes Surprised as action `06`. The legacy helper uses a
   triple-tap of `F18`; do not also bind F18 inside Remix.

## Files

- `sources/surprised_key_pose_chroma.png`: preserved generated chroma master
- `sources/surprised_key_pose.png`: transparent production key pose
- `frames/`: all 16 transparent animation cells
- `sheets/berry_surprised_hop_16f_4x4.png`: Remix production sheet
- `previews/surprised_preview.gif`: final 12 FPS timing preview
- `previews/surprised_key_moments.png`: idle, anticipation, apex, and landing
- `previews/qa_surprised_4_backgrounds.png`: four-background visual QA
- `qa_report.json`: scale, transparency, clipping, and residue checks
- `build_surprised.py`: deterministic frame, sheet, preview, and QA builder

Run `python build_surprised.py` from this directory to rebuild everything.
