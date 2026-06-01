# 0017 - Collision / physics representation
Status: Proposed   Date: 2026-05-31

## Context
Nothing in the plan yet covers AC **collision** — it blocks all movement and
interaction, and the entire simulation-lane collision spec (`contract/` §5) is
UNKNOWN. AC's collision geometry is distinct from its render geometry: ACE derives
indoor collision from `EnvCell.CellBSP` / `PhysicsObj`, outdoor from the landblock
heightfield, and props from `Setup` bounds [REF-IMPL: ACE — relayed from the
multi-LLM review; confirm the exact `CellBSP`/`PhysicsObj` symbols]. This is a
**simulation-lane** concern: collision feeds parity-tested movement, so it must
MIRROR, not approximate with UE defaults.

## Candidate (proposed, not decided)
Derive UE collision from the AC source per domain: **indoor** from
`CellStruct`/`CellBSP`, **terrain** from the heightfield mesh, **props** from
`Setup` bounds. The movement component (the `UCharacterMovementComponent`
subclass) uses the AC collision *model* from `contract/` §5 (capsule size, step-up,
slope limit, wall/ceiling response, heightfield interpolation), not UE's defaults.

## Assumptions it depends on
- A1 [VERIFY]: `CellBSP`/`PhysicsObj` structure + semantics (is collision a BSP, a
  convex set, or render-geometry-derived?).
- A2 [VERIFY]: the §5 values (capsule per species, step-up height, max slope,
  slide/wall/ceiling response, heightfield interpolation — bilinear assumed).

## Evidence required before Accepted
- Extract one cell's collision data and confirm against `CellStruct`; fill
  `contract/` §5 from the client (with provenance).

## Failure mode if an assumption is false
- UE-default collision diverges from AC feel -> parity tests fail at scale even if
  geometry looks right.

## Alternatives still live
- UE auto-generated convex/complex collision from render meshes (loses authored
  BSP fidelity; a fallback if `CellBSP` proves unextractable).
- Capsule-vs-heightfield only (simpler; may miss prop/edge collision).

## Acceptance test
- A recorded movement trace over known indoor + terrain geometry matches the
  reference within the §5 parity tolerance (T-sim).

## Relationships
Feeds `contract/` §5; pairs with ADR-0009 (terrain mesh source), ADR-0019 (portal
transitions), and the determinism risk (sim runs on a fixed entity set per tick;
streaming must not change collision membership mid-tick).
