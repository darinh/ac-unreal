# 0002 - Lumen / Nanite / HW ray tracing disabled for now
Status: Accepted   Date: 2026-05-30

## Context
The academy import builds hundreds of procedural StaticMeshes via the Python
MeshDescription API and spawns ~1500 actors. With Lumen + Nanite + HW ray
tracing enabled, the map crashed on load (Renderer `IntFitsIn` assertion,
Nanite cluster generation on degenerate procedural meshes, fallback-RTPSO
black frames in `-game`). The root `README.md` decision #19 still describes
these as enabled; that entry predates the crashes and is stale.

## Decision
Disable in `Config/DefaultEngine.ini`: `r.DynamicGlobalIlluminationMethod=0`,
`r.ReflectionMethod=0`, `r.RayTracing=False`, `r.Nanite=0`. The ini is
authoritative; README #19 is to be corrected. Lighting must work without GI
in the interim.

## Consequences
- No global illumination; indoor lighting needs explicit lights/emissive (see ADR-0005).
- Renders are deterministic and stable headless.
- **Revisit trigger:** once procedural meshes are guaranteed Nanite-safe (>=3
  non-coplanar tris, valid tangents) and instance counts are reduced (HISM /
  cell merging), re-evaluate enabling Lumen for the presentation lane.

## Alternatives
- Keep Lumen on and chase the crashes now: rejected (blocks all visual progress).
