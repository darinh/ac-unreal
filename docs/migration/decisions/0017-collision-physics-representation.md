# 0017 - Collision / physics representation
Status: Proposed   Date: 2026-05-31

## Context
Nothing in the plan yet covers AC **collision** — it blocks all movement and
interaction, and the entire simulation-lane collision spec (`contract/` §5) is
UNKNOWN. AC's collision geometry is distinct from its render geometry. In ACE the indoor cell
geometry lives on `CellStruct`, which carries **two polygon sets and three BSP trees**:
render `Polygons` build the `DrawingBSP`, while collision `PhysicsPolygons` build
**both** the `PhysicsBSP` (sphere/box collision sweeps) **and** the `CellBSP`
(point/box/sphere *containment* + cell-transit tests). Collision therefore derives
from `PhysicsPolygons` (via `PhysicsBSP` and `CellBSP`), distinct from the render
`Polygons`/`DrawingBSP`. The struct is referenced from a cell via `EnvCell.CellStructure`;
outdoor collision comes from the landblock heightfield, and props from `Setup` bounds.
`PhysicsObj` is ACE.Server *runtime* state, not a DAT structure. [REF-IMPL: ACE.DatLoader
`Entity/CellStruct.cs:11-16` (fields), `FileTypes/EnvCell.cs:27` (`CellStructure`); ACE.Server
`Physics/Common/CellStruct.cs:39-46` (BSP builds), `:49-73` (`CellBSP` containment) — verified]. This is a
**simulation-lane** concern: collision feeds parity-tested movement, so it must
MIRROR, not approximate with UE defaults.

## Candidate (proposed, not decided)
Derive UE collision from the AC source per domain: **indoor** from
`CellStruct.PhysicsPolygons` (the collision geometry — feeding `PhysicsBSP` for
sweeps and `CellBSP` for containment, *not* the render `Polygons`/`DrawingBSP`),
**terrain** from the heightfield mesh, **props** from
`Setup` bounds. The movement component (the `UCharacterMovementComponent`
subclass) uses the AC collision *model* from `contract/` §5 (capsule size, step-up,
slope limit, wall/ceiling response, heightfield interpolation), not UE's defaults.

## Assumptions it depends on
- A1 [VERIFY]: `CellStruct.PhysicsBSP`/`PhysicsPolygons` structure + semantics (is
  collision a BSP, a convex set, or render-geometry-derived?), and whether the
  client's runtime physics (the ACE.Server `PhysicsObj` analogue) consumes it as-is.
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
