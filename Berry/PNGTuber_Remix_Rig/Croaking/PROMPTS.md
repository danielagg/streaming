# Croaking visual-generation prompt

Built-in image generation was used with two references:

- Berry's idle render as the exact illustration-style reference;
- the supplied frog photograph as the anatomical/composition reference.

## Final integrated-deformation study prompt

```text
Use case: precise-object-edit
Asset type: full-inflation key pose for Berry's PNGTuber croak animation
Input images: Image 1 is the edit target and exact character/style anchor.
Image 2 is anatomical reference only for the way a frog vocal sac projects
forward from the throat.
Primary request: modify only Berry's throat and upper chest so his own throat
skin is naturally inflated outward into a frog vocal sac. This must be an
anatomical deformation of Berry, never a separate circular object placed on
top.
Integration requirements: the inflated skin begins directly beneath and behind
the moustache; its upper edge has no visible closed outline and flows
continuously out of Berry's green lower face. The cream belly marking stretches
upward and across the center of the inflated sac while olive-green throat skin
remains along the upper corners and sides. The sac projects forward through
soft radial volume shading, stretched painted texture, and a subtle contact
shadow on the chest immediately below. The lower contour is broad and softly
rounded, but its side transitions blend naturally back into Berry's torso
instead of forming a complete sticker border.
Size/shape: moderate natural frog vocal sac, about as wide as the space between
Berry's shoulders, wider than tall, full but not spherical, not hanging like a
pouch.
Style: preserve Image 1's exact warm hand-painted 2D cartoon rendering, line
weight, palette, texture, and lighting.
Invariants: preserve Berry's identity, pose, proportions, hat, pom-pom, eyes,
pupils, nose, moustache, arms, legs, spots, outer body silhouette, framing, and
all areas outside the throat/upper chest. Keep the moustache fully visible in
front of the inflation.
Backdrop: keep the existing transparent/empty backdrop appearance; do not add
scenery.
Avoid: separate blob, pasted circle, complete outline around the sac, hard top
edge, seam, vertical crease, glossy balloon, white glare, yellow bean, pouch,
double chin, open mouth, extra anatomy, text, watermark.
```

The generated full-pose study established the depth and integration. Production
pixels are rebuilt directly from Berry's original throat/chest artwork so the
rest of the character remains exact.
