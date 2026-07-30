# Berry pupil tracking — rebuilt with real Remix clipping

This replaces every file from the rejected pupil-tracking attempt.

The original iris, pupil, and highlight were removed as one complete region.
The three new files are:

1. `01_CLIP_PARENT_stationary_clean_irises.png`
   - stationary brown irises
   - visible clipping parent
2. `02_CHILD_cursor_black_pupils.png`
   - only grayscale black pupils and white glints
   - the only mouse-follow object
3. `03_TOP_stationary_sclera_and_rims.png`
   - stationary whites, eyelids, and rim linework
   - always stays in front

All files are static 1×1 sprites on the original 512×1254 transparent canvas.
Import them without trimming.

## Remove the rejected objects

Delete or hide all three objects from the previous attempt before importing
these. Do not mix an old object with a rebuilt object; doing so will put an old
pupil fragment back into the eye.

## Exact PNGTuber Remix setup

1. Import the three rebuilt PNG files.
2. Set all three objects to:
   - `Should Blink`: `Open`
   - horizontal frames: `1`
   - vertical frames: `1`
3. Drag `02_CHILD_cursor_black_pupils` directly onto
   `01_CLIP_PARENT_stationary_clean_irises` in the Sprites tree. The pupil must
   appear indented underneath the iris parent.
4. Select `01_CLIP_PARENT_stationary_clean_irises` and enable
   `Clip Children`.
5. Set the child `02_CHILD_cursor_black_pupils` to `Z Order: 0`. This is
   mandatory for Remix/Godot clipping.
6. Keep `03_TOP_stationary_sclera_and_rims` as a root object and place it after
   the iris/pupil group so it draws in front.
7. Use tree order instead of high Z values. Set all three rebuilt objects to
   `Z Order: 0`.
8. Enable position mouse-follow only on `02_CHILD_cursor_black_pupils`:
   - follow option: `Mouse`
   - delay: `0.08`
   - range X min: `-5`
   - range X max: `5`
   - range Y min: `-3`
   - range Y max: `3`
   - `Invert Pos X`: enabled (Berry is flipped horizontally in OBS)
   - rotation follow: disabled
   - scale follow: disabled
9. Leave movement disabled on the iris parent and the top rim layer.
10. Enable these three objects only in Berry's normal state. Keep them off in
    `Whiskey Sip`, which has its own complete eye animation.

The stationary iris parent is both visible and the clipping mask. Even if a
tracking value is accidentally increased, the child pupil cannot render beyond
the stationary iris silhouette.

## Verification files

- `previews/qa_clean_rebuild.png` shows the original, the clean stationary eyes
  with the pupil layer hidden, neutral gaze, and full-left clipped gaze.
- `previews/pupil_tracking_clipped_preview.gif` exercises the complete
  recommended movement range.

The builder also verifies:

- the moving layer contains no brown pixels;
- the stationary inner irises contain no black pupil or white highlight;
- the rendered pupil alpha never exceeds the clipping-parent alpha at any
  tested extreme.
