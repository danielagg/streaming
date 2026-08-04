# Berry — Embarrassed Sway

This add-on is Berry's bashful embarrassment reaction for PNGTuber Remix. He
avoids eye contact, blushes heavily, fidgets with his fingertips, and rocks
gently from side to side while trying to look composed.

## Production file

Import:

`sheets/berry_embarrassed_sway_16f_4x4.png`

The sheet contains 16 transparent `672 × 1292` cells in reading order. At
`8 FPS`, the one-shot lasts `2 seconds`.

The builder calibrates Berry's visible body to `1164 px` tall—Angry's
`1252 px` body multiplied by the confirmed `0.93` correction. This matches the
normal idle body's `1172 px` footprint, so start at Remix Size X/Y `1.00`.

## PNGTuber Remix setup

1. Save a backup of the current `.pngRemix` model.
2. In **Settings → Import**, disable **Crop Images to Content**.
3. Add a state named exactly `Embarrassed`.
4. Hide the normal Berry rig objects in that state.
5. Import the production sheet as one Sprite object and name it
   `Berry_Embarrassed_Sway`.
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
8. Do not bind F17 inside Remix. `Start Berry Actions.cmd` handles F17 and
   returns to the previous normal state after about 2.1 seconds.

## Unified hotkey

With Remix's WebSocket server running on `ws://127.0.0.1:9321`, open
`Start Berry Actions.cmd` and triple-tap `F17`.

## Files

- `sources/embarrassed_key_pose_chroma.png`: preserved generated chroma master
- `sources/embarrassed_key_pose.png`: transparent production key pose
- `frames/`: all 16 transparent animation cells
- `sheets/berry_embarrassed_sway_16f_4x4.png`: Remix production sheet
- `previews/embarrassed_preview.gif`: final 8 FPS timing preview
- `previews/qa_embarrassed_4_backgrounds.png`: four-background visual QA
- `qa_report.json`: size calibration, transparency, clipping, and residue checks
- `build_embarrassed.py`: deterministic frame, sheet, preview, and QA builder

Run `python build_embarrassed.py` from this directory to rebuild everything.
