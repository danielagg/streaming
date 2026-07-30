# Berry — Croak Twice animation

This add-on synchronizes Berry's illustrated throat sac to `Croak Twice.mp3`.
The sound is 2.952 seconds long; the overlay animation is exactly 3.000 seconds.

The vocal sac:

- inflates once during the first croak phrase (`~0.10–1.18 s`);
- fully disappears during the central pause;
- inflates again during the second phrase (`~1.64–2.74 s`);
- finishes on a completely transparent frame.

It is a deformation overlay rather than a replacement character sheet. Berry's
normal body, blinking, and clipped cursor-tracking pupils remain active. The
sheet includes a croak-specific static moustache foreground; the normal
mouth/moustache sheet must be hidden in the `Croaking` state.

## Production file

Import:

`sheets/berry_croak_twice_overlay_24f_6x4.png`

Sprite-sheet settings:

- Horizontal Frames: `6`
- Vertical Frames: `4`
- Animation Speed: `8 FPS`
- Reset Animation: `On`
- One Shot: `On`
- Reset on State Change: `On`
- Should Talk: `Disabled`
- Should Blink: `Disabled`
- Z Order: `0`

The sheet contains 24 uniform 512×1254 cells and lasts three seconds.

## Recommended Remix state

1. Back up the current `.pngRemix` file.
2. Duplicate the normal state and name the duplicate exactly `Croaking`.
3. Keep the normal body, blink objects, and rebuilt pupil-tracking hierarchy
   visible.
4. Hide the normal `20_mouth_moustache...` object in this state. The production
   croak sheet already contains a clean moustache foreground without the normal
   layer's conflicting stationary chest patch.
5. In `Settings → Import`, temporarily disable `Crop Images to Content`.
6. Import the production sprite sheet as one Sprite object.
7. Apply the settings above.
8. Give it the exact position, scale, rotation, and pivot used by
   `00_base_underpaint`.
9. In the Sprites tree, place the croak sheet immediately after the base and
   before the eye objects:

   ```text
   00_base_underpaint
   Berry_Croak_Twice
   normal eyes / blink objects
   ```

   Keep these objects at Z Order `0` and use the tree order.

## One-key synchronized playback

`Start Croaking F14.cmd` provides the same workflow as the whiskey helper:

1. Name the Remix state exactly `Croaking`.
2. Do not assign F14 inside Remix.
3. Start Remix's local WebSocket server at `ws://127.0.0.1:9321`.
4. Open `Start Croaking F14.cmd`.
5. Press F14.

The helper remembers the current state, enters `Croaking`, starts the MP3,
waits three seconds, and returns to the previous state.

## Files

- `Croak Twice.mp3`: original supplied audio
- `sheets/berry_croak_twice_overlay_24f_6x4.png`: production sheet
- `frames/`: all 24 transparent overlay frames
- `previews/berry_croak_twice_preview.gif`: timing preview
- `previews/berry_croak_key_moments.png`: rest/peak/gap/peak QA
- `previews/berry_croak_growth_stages.png`: outward-growth sequence QA
- `sources/croak_integrated_study.png`: integrated full-pose design study
- `sources/rejected/`: older isolated-sac passes, retained only for history
- `croak_moustache_foreground.png`: clean static foreground baked into the sheet
- `build_croaking.py`: deterministic sheet and preview builder

## QA

The builder verifies:

- exactly 24 frames at 8 FPS;
- exactly two separated visible inflation cycles;
- no throat deformation in the first and last frames;
- a 3072×5016 production sheet with uniform 512×1254 cells.
