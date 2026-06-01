# 0014 - Re-enable Nanite / Lumen at world scale (revisit of 0002)
Status: Proposed   Date: 2026-05-31

## Context
ADR-0002 disabled Lumen, Nanite, and hardware ray tracing because procedural
meshes + large instance counts crashed those paths (`IntFitsIn` assertion;
empty-bounds Nanite clusters) [DATA: `Config/DefaultEngine.ini`; methodology §8,
which explicitly asks for a record on re-enabling once meshes are Nanite-safe].
That was the right call to unblock the first indoor room, but a large, long-view
open world normally wants Nanite (auto-LOD on massive geometry) and a dynamic GI
solution (Lumen) - especially with a day-night cycle (ADR-0011).

Disposition: **ADD/IMPROVE** (re-enable modern rendering) - pending a fix and a
cost/benefit call given AC's low-poly assets.

## Decision
TBD (Proposed). Re-enable when: (1) the procedural-build pipeline produces
Nanite-safe meshes (>=3 valid verts, finite bounds, no degenerate clusters), and
(2) a perf pass shows benefit at world scale. Likely staged: Lumen for dynamic
GI/day-night first (pairs with ADR-0011); Nanite second (its win is largest for
dense scatter/terrain - weigh against AC's low poly counts). When accepted, this
**supersedes ADR-0002**.

## Consequences
- Until then, ADR-0002 stands and ADR-0015 governs the interim look.
- Distance-field-dependent features (some Lumen modes) need
  `r.GenerateMeshDistanceFields=True`, currently off.

## Alternatives
- Keep everything off permanently: rejected (no dynamic GI for day-night; manual
  LOD/HLOD only). Acceptable as a low-end scalability tier, not the default.

## Verify before locking
- Procedural meshes pass Nanite validation; a representative-scene perf capture
  with/without Nanite + Lumen.
