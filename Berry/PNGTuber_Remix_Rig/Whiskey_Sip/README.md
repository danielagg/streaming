# Berry — Whiskey Sip animation

This add-on contains a transparent, full-character whiskey-sip animation for PNGTuber Remix.

## Production file

Import:

`sheets/whiskey_sip_12f_4x3.png`

The sheet is 2688 × 3876 px. It contains 12 uniform 672 × 1292 px cells in reading order, left-to-right and then top-to-bottom.

Animation:

1. Lift and anticipation
2. Glass approaches the moustache
3. Eyes-closed sip
4. Satisfied half-lidded beat
5. Lower and return

At 6 FPS the complete one-shot lasts 2 seconds.

The four transparent key poses are also available in `frames/`. The magenta generation masters are retained non-destructively in `sources/`.

## Recommended PNGTuber Remix setup

1. Save a backup copy of the current `.pngRemix` model.
2. In **Settings → Import**, temporarily disable **Crop Images to Content**. The sheet's exact grid dimensions must be preserved.
3. Add a new state and name it `Whiskey Sip`. In Remix 1.4.x, use the **Remap** button above the states to rename it and assign an input key.
4. In the new state, hide the normal Berry rig objects.
5. Import `sheets/whiskey_sip_12f_4x3.png` as one Sprite object and name it `Berry_Whiskey_Sip`.
6. Set:
   - Horizontal Frames: `4`
   - Vertical Frames: `3`
   - Animation Speed: `6 FPS`
   - Reset Animation: `On`
   - One Shot: `On`
   - Reset on State Change: `On`
   - Should Talk: `Off`
   - Should Blink: `Off`
   - Ignore Bounce: `On` (recommended)
7. Use **Pause Movement** while matching the sprite's position and scale to the normal state. Start near a uniform scale of `0.93`, then align the feet and centerline by eye.
8. Switch to Preview mode and test the state hotkey. The animation should play once and stop on its final lowered-glass pose.

The normal state should retain the existing layered eye and mouth rig. Do not add those lip-sync layers above the sip sheet; the sheet already contains its own facial poses.

## Returning automatically with one physical hotkey

The included Windows helper is the simplest option:

1. Name the sipping state exactly `Whiskey Sip`.
2. Do **not** assign F13 inside Remix.
3. Open `Start Whiskey F13.cmd` while Remix is running.
4. Press F13. The helper remembers the current state, plays `Whiskey Sip` for two seconds, and returns to the remembered state.
5. Leave the small helper window open while streaming. Close it or press Ctrl+C in it to stop the hotkey.

The helper talks only to PNGTuber Remix's local WebSocket server at `ws://127.0.0.1:9321`.

Alternatively, Streamer.bot, TouchPortal, a Stream Deck multi-action, or another WebSocket-capable hotkey tool can perform the same sequence:

1. Send:

   `{"event":"state","state_name":"Whiskey Sip"}`

2. Wait `2000 ms`.
3. Send:

   `{"event":"state","state_name":"Idle"}`

Replace `Idle` with the exact name of the normal state. PNGTuber Remix's WebSocket server uses `ws://127.0.0.1:9321` by default.

Without an external macro, map one Remix key to `Whiskey Sip` and a second key to the normal state.

## QA and rebuilding

- `previews/whiskey_sip_preview.gif` shows the 6 FPS timing on a checkerboard.
- `previews/whiskey_sip_key_poses.png` shows the four source poses.
- Run `build_whiskey_sip.py` with Pillow installed to rebuild the production sheet and previews from the transparent frames.

Official references:

- https://mudkipworld.github.io/PNGRemix-Doc/
- https://github.com/MudkipWorld/PNGTuber-Remix/blob/1.4.x/OnlineDoc/websocket.md
