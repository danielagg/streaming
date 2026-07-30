# Berry — Fly Catch

This add-on contains Berry's production-ready fly-catching animation for
PNGTuber Remix.

## Production file

Import:

`sheets/fly_catch_14f_7x2.png`

The sheet is 7392 × 2584 px. It contains 14 uniform 1056 × 1292 px cells in
reading order. At 10 FPS, the one-shot lasts 1.4 seconds.

The animation has six key poses:

1. Berry notices and tracks one fly.
2. He makes a small anticipation squash.
3. His tongue fires from beneath the moustache.
4. The fly sticks to the rounded tongue tip.
5. The tongue retracts with the fly attached.
6. Berry gives one smug, satisfied swallow.

## PNGTuber Remix setup

1. Save a backup of the current `.pngRemix` model.
2. In **Settings → Import**, disable **Crop Images to Content**.
3. Add a state named exactly `Fly Catch`.
4. Hide the normal Berry rig objects in that state.
5. Import `sheets/fly_catch_14f_7x2.png` as one Sprite object and name it
   `Berry_Fly_Catch`.
6. Set:
   - Horizontal Frames: `7`
   - Vertical Frames: `2`
   - Animation Speed: `10 FPS`
   - Reset Animation: `On`
   - One Shot: `On`
   - Reset on State Change: `On`
   - Should Talk: `Disabled`
   - Should Blink: `Disabled`
   - Ignore Bounce: `On`
   - Enable Physics: `Off`
   - Z Order: `0`
7. Use **Pause Movement** while aligning it. Start at Size X/Y `1.0`; keep the
   two size values identical. Align Berry by his feet and body centerline.
8. Do not bind F15 inside Remix. `Start Berry Actions.cmd` handles F15 and
   restores the previous normal state automatically.

## Unified hotkey

With Remix's WebSocket server running on `ws://127.0.0.1:9321`, open the
root-level `Start Berry Actions.cmd`:

- Triple-tap `F13`: Whiskey Sip
- Triple-tap `F14`: Croaking
- Triple-tap `F15`: Fly Catch

## QA and source files

- `production_frames/`: six full-resolution transparent key poses
- `previews/fly_catch_preview.gif`: final timing preview
- `previews/fly_catch_key_poses_production.png`: production contact sheet
- `previews/qa_fly_catch_4_backgrounds.png`: checker, white, black, and cyan QA
- `qa_report.json`: dimensions, alpha, clipping, and chroma validation
- `sources/`: preserved generated chroma and transparent source studies
- `build_fly_catch.py`: deterministic production builder
- `build_fly_catch_preview.py`: retained timing-study builder
