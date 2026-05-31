# Content/Presentation/

The **presentation lane** per the brief. Lumen, hardware ray tracing,
Niagara, PBR materials, post-processing volumes, post-FX. This
directory MUST NOT contain anything that a recorded simulation trace
depends on — gameplay-relevant timings (cast windows, projectile
launch frames, damage application frames) live in `Content/Data/` and
the C++ sim core, not here.

## Subdirectories (created as content lands)

- `Materials/` — master materials + parameter collections. See
  `Materials/README.md` for the PBR master-material pattern.
- `Niagara/` — Niagara emitters + systems for re-authored particle FX.
- (future) `PostProcess/` — PostProcessVolumes + exposure curves.
- (future) `Lighting/` — sky / directional light defaults, lumen profile data.
- (future) `Decals/` — decal materials.

## Why the rendering settings live in `Config/DefaultEngine.ini`, not here

Lumen, RT, Nanite, virtual shadow maps, virtual textures, etc. are
*engine-wide* render settings. Project-level switches live in
`Config/DefaultEngine.ini`. Per-scene tuning happens via
PostProcessVolumes, Sky Atmosphere, Volumetric Cloud, etc. — assets
that go in the `PostProcess/` and `Lighting/` subdirs above.

## Brief honesty about Nanite

Nanite is **enabled** at project level for forward-compat with
re-authored high-poly meshes. Nanite on 1999-era ~200-tri AC source
meshes adds overhead with no benefit. The win lands when we replace
the source geometry with high-poly equivalents (a separate art
effort). Until then, Nanite is "on but mostly inert."

See README decision #14 for the project-level call.
