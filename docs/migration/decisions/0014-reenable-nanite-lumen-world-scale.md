# 0014 - Re-enable Nanite / Lumen at world scale (revisit of 0002)
Status: Proposed   Date: 2026-05-31

## Context
ADR-0002 disabled Lumen/Nanite/HW-RT due to procedural-mesh crashes (`IntFitsIn`
assertion; empty-bounds Nanite clusters) [DATA: `Config/DefaultEngine.ini`;
methodology §8, which asks for this record]. A large, long-view, day-night world
can benefit from dynamic GI (Lumen) and auto-LOD on dense geometry (Nanite).
**Correction (M14):** a day-night cycle does **not** require Lumen — a dynamic
directional sun + SkyLight + SkyAtmosphere + fog achieves it (ADR-0011). Lumen is
a GI *quality* upgrade, not a day-night prerequisite.

## Candidate (proposed, not decided)
Keep Lumen/Nanite OFF as the baseline; re-enable only on **measured benefit**,
staged: (1) consider Lumen only if the T3/T4 lighting goal is NOT met by dynamic
sun+sky+fog alone; (2) consider Nanite for dense scatter/terrain.

## Assumptions it depends on
- A1: procedural meshes are Nanite-safe.
- A2: a perf/quality capture shows net benefit at world scale.

## Evidence required before Accepted
- Nanite-readiness is **necessary but not sufficient**: beyond ">=3 verts / finite
  bounds", validate masked/translucent materials, foliage/HISM, collision, and run
  a with/without perf capture on a representative *streamed* region.
- A T3/T4 lighting comparison showing whether dynamic-only meets the bar (this
  gates whether Lumen is even needed).

## Failure mode if enabled prematurely
- The original crash/instability returns, or perf regresses with no fidelity gain.

## Alternatives still live
- A permanent low-end tier (everything off; manual LOD/HLOD + dynamic sun/sky):
  acceptable as a scalability floor, not necessarily the default.

## Acceptance test
- With/without Nanite+Lumen on a streamed multi-landblock region: frame time,
  VRAM, and a T3 visual delta. Re-enable only where the data shows a win.

When accepted, this **supersedes ADR-0002**.
