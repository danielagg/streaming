# Angry Berry — generation record

## Built-in image generation prompt

Use case: `stylized-concept`

Asset type: production key pose for a PNGTuber Remix sprite animation.

Create a full-body angry expression key pose of Berry. Use the current full-body
Berry render as the strict character identity, costume, proportions, rendering,
and style reference. Use the supplied angry-anime image only as a loose
expression and motion-language reference; do not copy its character or drawing
style.

Preserve Berry's charcoal beret with green pom-pom, olive frog skin and spots,
cream belly, brown curled moustache, proportions, and softly shaded outlined
illustration style. Give him sharply lowered brow/upper eyelid shapes, narrowed
glossy eyes, flushed cheeks, subtly flared nostrils, a compressed mouth beneath
the moustache, and tense webbed hands. Add only a few small reddish-orange stress
marks and pale steam puffs around the head.

Center the complete character on a perfectly uniform `#ff00ff` chroma field
with generous padding. No crop, text, watermark, cast shadow, reflection, props,
flames, or environmental scene. Do not use `#ff00ff` on Berry or the accents.

## Input roles

- `../../previews/preview_idle_transparent.png`: strict Berry identity and style
- user-supplied angry-anime still: expression and motion-language reference only

The built-in image generation tool produced the chroma master. The local
chroma-removal helper produced the transparent cutout; hard color matching was
used because the helper's soft magenta dominance matte incorrectly treated
Berry's cream belly as spill.
