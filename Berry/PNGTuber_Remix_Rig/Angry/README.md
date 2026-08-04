# Berry — Angry Tremble

This add-on is Berry's short, classic cartoon/anime-style anger reaction for
PNGTuber Remix. Berry narrows his eyes, tenses both webbed hands, flushes, and
trembles between small steam puffs and stress marks. The motion builds for one
beat and settles cleanly instead of looping mechanically.

## Production file

Import:

`sheets/berry_angry_tremble_16f_4x4.png`

The sheet contains 16 transparent `672 × 1292` cells in reading order. At
`12 FPS`, the one-shot lasts `1.333 seconds`.

## PNGTuber Remix setup

1. Save a backup of the current `.pngRemix` model.
2. In **Settings → Import**, disable **Crop Images to Content**.
3. Add a state named exactly `Angry`.
4. Hide the normal Berry rig objects in that state.
5. Import the production sheet as one Sprite object and name it
   `Berry_Angry_Tremble`.
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
7. Use **Pause Movement** while aligning the sprite. Start at Size X/Y `0.93`,
   keep both values identical, then align Berry by his feet and body centerline.
   This is the confirmed match for the normal Berry rig's visible size.
8. Do not bind F16 inside Remix. `Start Berry Actions.cmd` handles F16 and
   returns to the previous normal state after the animation.

## Unified hotkey

With Remix's WebSocket server running on `ws://127.0.0.1:9321`, open
`Start Berry Actions.cmd` and triple-tap `F16`.

## Files

- `sources/angry_key_pose_chroma.png`: preserved generated chroma master
- `sources/angry_key_pose.png`: transparent production key pose
- `frames/`: all 16 transparent animation cells
- `sheets/berry_angry_tremble_16f_4x4.png`: Remix production sheet
- `previews/angry_preview.gif`: final 12 FPS timing preview
- `previews/qa_angry_4_backgrounds.png`: checker, white, black, and cyan QA
- `qa_report.json`: dimensions, transparency, clipping, and residue checks
- `build_angry.py`: deterministic frame, sheet, preview, and QA builder

Run `python build_angry.py` from this directory to rebuild the deliverables.
