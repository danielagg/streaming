# Berry — Understanding Nod

This add-on is Berry's focused “I understand” reaction for PNGTuber Remix. He
holds his chin analytically, considers the point, gives one deliberate nod, then
a smaller confirming nod.

## Production file

Import:

`sheets/berry_understanding_nod_16f_4x4.png`

The sheet contains 16 transparent `672 × 1292` cells in reading order. At
`8 FPS`, the one-shot lasts `2 seconds`.

The builder calibrates Berry's visible body to `1164 px`, matching the corrected
scale used by Embarrassed and closely matching the normal idle body's `1172 px`
footprint. Start at Remix Size X/Y `1.00`.

## PNGTuber Remix setup

1. Save a backup of the current `.pngRemix` model.
2. In **Settings → Import**, disable **Crop Images to Content**.
3. Add a state named exactly `Understanding`.
4. Hide the normal Berry rig objects in that state.
5. Import the production sheet as one Sprite object and name it
   `Berry_Understanding_Nod`.
6. Set:
   - Horizontal Frames: `4`
   - Vertical Frames: `4`
   - Animation Speed: `8 FPS`
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
8. Command Deck exposes Understanding as action `07`. The legacy helper uses a
   triple-tap of `F19`; do not also bind F19 inside Remix.

## Files

- `sources/understanding_key_pose_chroma.png`: preserved generated chroma master
- `sources/understanding_key_pose.png`: transparent production key pose
- `frames/`: all 16 transparent animation cells
- `sheets/berry_understanding_nod_16f_4x4.png`: Remix production sheet
- `previews/understanding_preview.gif`: final 8 FPS timing preview
- `previews/understanding_key_moments.png`: both nod depths and rests
- `previews/qa_understanding_4_backgrounds.png`: four-background visual QA
- `qa_report.json`: scale, transparency, clipping, and residue checks
- `build_understanding.py`: deterministic frame, sheet, preview, and QA builder

Run `python build_understanding.py` from this directory to rebuild everything.
