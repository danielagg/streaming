# Fly Catch image-generation prompt

Built-in image generation was used in `stylized-concept` mode with:

- `previews/preview_idle_transparent.png` as Berry's identity and neutral-pose
  reference;
- `Whiskey_Sip/previews/whiskey_sip_key_poses.png` as the animation style and
  anatomy reference.

The requested six-pose sequence was:

1. notice one fly using pupil movement only;
2. anticipation squash with pupils locked on the fly;
3. tongue strike from the mouth beneath the moustache;
4. fly caught on the rounded tongue tip;
5. tongue retracting with the fly attached;
6. satisfied swallow with relaxed half-lidded eyes.

Invariants included Berry's exact identity, proportions, spot pattern, hat,
pom, moustache, limbs, palette, contour style, and three-quarter orientation.
The generation used a flat `#ff00ff` background, which was removed locally with
the installed image-generation chroma-key helper.
