# 0011 - Outdoor lighting & day-night model (RegionDesc-driven)
Status: Proposed   Date: 2026-05-31

## Context
AC computes per-vertex **Gouraud** lighting at runtime (`dot(N,-L)+ambient`
multiplied into the texture; no baked vertex color) [DATA/REF-IMPL: methodology
§5, glossary]. Global sky/sun/moon/fog/ambient and the day-night cycle ("lighting
of day") live in **`RegionDesc` (0x13)** [DATA: methodology §2]. The only lighting
decision so far is **indoor-only**: ADR-0007 chose unlit emissive textures as a
deterministic interim look. That expedient cannot do day-night or atmospheric
shading and must not be inherited outdoors (see ADR-0015). `RegionDesc.SkyDesc`
has **not been extracted**, so exact fog/sky/sun values are unknown.

Disposition: **MIRROR** the data-driven sky/fog/day-night; **IMPROVE** the
rendering (dynamic sun + SkyAtmosphere + height fog, volumetrics optional).

## Decision
TBD (Proposed). Candidate [DESIGN]: a time-of-day system driving a directional
sun + SkyLight + SkyAtmosphere + ExponentialHeightFog from extracted
`RegionDesc` curves; surfaces move to a lit/PBR-ish material set (keeping
`Luminosity` as emissive). Indoors keeps an occluded sky (ADR-0013) and may
retain emissive ambient. Extract `RegionDesc.SkyDesc` first; do **not** invent
fog distances or a day-night period.

## Consequences
- Supersedes the *scope* of ADR-0007 (indoor) for the outdoor world; ADR-0007
  stays valid as the indoor interim until a unified lit model lands.
- Pairs with ADR-0014 (Lumen) for GI and ADR-0013 (indoor sky occlusion).

## Alternatives
- Keep unlit emissive world-wide: rejected (no day-night, flat, unfaithful outdoors).
- Baked Lightmass: rejected for a dynamic day-night cycle.

## Verify before locking
- H3: `RegionDesc.SkyDesc` contents (fog start/end, sky/ambient colors,
  sun/moon path, day-night period) - extract via a new `export-region`.
