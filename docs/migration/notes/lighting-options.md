# Note: indoor lighting options (decision pending)

This is a **research note, not a decision** (an ADR records a decision; this
records the open options). When a call is made, write it as an ADR and link
back here.

## Why it's open
AC computes per-vertex Gouraud lighting at runtime (`dot(N,-L)+ambient`)
multiplied into the texture; there is no baked vertex color (`SWVertex` is
position/normal/UV only). The real academy reads as a bright, evenly-lit stone
room with warm brazier accents, not a dark dungeon. GI is off (ADR-0002), so
we cannot lean on Lumen.

## Options
- **Unlit / emissive textures** - bright, even, deterministic; matches AC's flat
  base look; ignores the placed lights (no warm pools). Currently the interim.
- **Dynamic point lights + lit materials** - reproduces torch pools, but with GI
  off the enclosed interiors go black and need heavy tuning; depends on the
  light-placement coordinate work (fixed for lights, still broken for statics).
- **Baked Lightmass** - closest to AC's static feel, but procedural meshes lack
  lightmap UVs and `r.AllowStaticLighting=False` today.

## Recommended evaluation path
Unlit base (fidelity to the flat look) + a small set of correctly-placed
dynamic lights as additive warm accents, with an emissive floor so nothing is
ever pure black. Decide after rendering the real first room against the
reference at acceptance tier T2/T3, then promote to an ADR.
