# 0007 - Indoor lighting: Unlit emissive textures (point-light accents deferred)
Status: Accepted   Date: 2026-05-31
Supersedes: the open question in [`../notes/lighting-options.md`](../notes/lighting-options.md)

## Context
AC's renderer multiplies *(ambient + light-source contribution)* into each
surface's texture, computed per-vertex (Gouraud) at runtime. The Aluvian
academy reads **bright and evenly lit** in the reference (answer key), not a
dark dungeon. Constraints here:
- GI (Lumen) is disabled and crashes on the procedural academy (ADR-0002).
- There is no baked per-vertex colour in the data (`SWVertex` = pos/normal/UV).
- A Default-Lit base with no GI leaves enclosed interiors black, and the
  in-place "hybrid lit + emissive" material wiring proved unreliable in
  practice (rendered black across several attempts).
- We need a result that is correct and bright when a user just opens the map.

## Decision
Master materials (`M_AcademyBase`, `M_AcademyColor`) are **Unlit** with
**Emissive = the texture** (`BaseColorTex`) / solid colour. Fixed exposure
(`r.EyeAdaptationQuality=0`, `r.DefaultFeature.AutoExposure=False`). This
shows every surface at full, even brightness - a faithful, deterministic
match to AC's brightly-lit academy that **never renders black** and does not
depend on GI or scene lights.

Implemented by a re-runnable script pair (not a committed asset, per ADR-0003):
`rebuild_academy_masters.py` (`AC_SHADING=unlit`, `AC_EMISSIVE_SCALE=1.0`) then
`_refix_mi_textures.py` (re-applies each MaterialInstance's texture/colour
parameter, since the master rebuild reissues parameter GUIDs).

## Consequences
- Bright, even, correct, reproducible; matches the answer key's academy shell.
- **Flat** - no directional shading and no warm fireplace pools. Accepted for now.
- The lighting "recipe" lives in scripts and can be regenerated after any asset
  revert (UAssets are AC-derived and not committed).

## Deferred refinement (documented, not done)
Additive warm accents from the correctly-placed point lights (the braziers,
now at correct coordinates) via a hybrid Default-Lit + emissive material.
Deferred because: GI-off makes lit interiors unreliable/dark; the bright
academy is well-approximated unlit; and reliability for "open and look" wins
now. **Revisit when** GI is re-enabled (meshes made Nanite/RT-safe) or AC's
per-vertex Gouraud term is reproduced (would require extracting/computing
vertex colours, which the data does not store directly).

## Alternatives
- Hybrid Default-Lit + emissive + point lights: the most faithful, but unreliable today (see Context). This is the deferred refinement.
- Baked Lightmass: procedural meshes lack lightmap UVs; `r.AllowStaticLighting=False`.
