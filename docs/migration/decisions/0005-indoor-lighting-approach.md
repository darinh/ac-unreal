# 0005 - Indoor lighting approach (unlit vs dynamic vs baked)
Status: Proposed   Date: 2026-05-30

## Context
AC computes per-vertex Gouraud lighting at runtime (`dot(N,-L)+ambient`)
multiplied into the texture; there is no baked vertex color in the data
(`SWVertex` is position/normal/UV only). The real academy reads as a *bright,
evenly-lit* stone room with warm brazier accents - not a dark dungeon. GI is
off (ADR-0002). We need a faithful look without Lumen.

Options explored this session:
- **Unlit / emissive textures** - bright, even, deterministic; matches AC's flat
  base look; ignores the placed lights (no warm pools). Currently in use as the
  interim.
- **Dynamic point lights + lit materials** - reproduces torch pools, but with GI
  off the enclosed interiors go black and it needs heavy tuning; the placed
  lights also depend on the (now-fixed for lights, still-broken for statics)
  coordinate work.
- **Baked Lightmass** - closest to AC's static feel, but procedural meshes lack
  lightmap UVs and `r.AllowStaticLighting=False` currently.

## Decision (proposed)
TBD. Recommended path to evaluate first: **unlit base for fidelity to the flat
look + a small set of correctly-placed dynamic lights as additive warm accents**
(emissive floor so nothing is ever pure black). Decide after rendering the real
first room against the reference at acceptance tier T2/T3.

## Consequences
Whichever is chosen becomes the per-cell material/lighting recipe replayed for
every room; document it in the methodology once decided.

## Alternatives
See options above.
