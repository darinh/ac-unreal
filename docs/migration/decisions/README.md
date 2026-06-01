# Architecture Decision Records (ADRs)

One file per significant, contestable decision, so the *why* survives and the
next agent challenges the rationale instead of silently reversing it.

**Status values:** `Proposed` (open, needs a call) - `Accepted` (in force) -
`Superseded by NNNN` - `Deprecated`.

**Format (keep it short):**
```
# NNNN - Title
Status: <status>   Date: YYYY-MM-DD
## Context     (the forces / constraints)
## Decision    (what we chose)
## Consequences (trade-offs, what this commits us to, revisit trigger)
## Alternatives (what we rejected and why)
```

When a `Proposed` ADR is decided, flip its status and note the date. When you
reverse a decision, add a new ADR and mark the old one `Superseded by NNNN`;
never edit history away.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-ace-datloader-via-acdat.md) | Use ACE.DatLoader (via the `acdat` CLI) for DAT extraction | Accepted |
| [0002](0002-lumen-nanite-rt-disabled.md) | Lumen / Nanite / HW ray tracing disabled for now | Accepted |
| [0003](0003-no-committed-ac-assets.md) | No AC-derived assets committed; users supply their own DATs | Accepted |
| [0004](0004-obj-transitional-gltf.md) | OBJ is a transitional intermediate; glTF for skinned/multi-UV | Proposed |
| [0006](0006-ace-linking-stance.md) | ACE.DatLoader linking stance (AGPL obligations) | Accepted |
| [0007](0007-indoor-lighting-unlit-emissive.md) | Indoor lighting: unlit emissive textures (point-light accents deferred) | Accepted |
| [0008](0008-skip-portal-polygons-on-export.md) | Skip portal polygons (`Stippling == NoPos`) on EnvCell export | Accepted |
| [0009](0009-world-streaming-landblock-world-partition.md) | World-scale streaming: landblock grid -> UE World Partition | Proposed |
| [0010](0010-coordinate-precision-strategy.md) | Coordinate & precision strategy (LWC vs landblock-local) | Proposed |
| [0011](0011-outdoor-lighting-day-night.md) | Outdoor lighting & day-night model (RegionDesc-driven) | Proposed |
| [0012](0012-animation-representation.md) | Animation representation: rigid part-based vs skeletal | Proposed |
| [0013](0013-runtime-occlusion-portal-culling.md) | Runtime occlusion / portal culling (CellPortals/VisibleCells) | Proposed |
| [0014](0014-reenable-nanite-lumen-world-scale.md) | Re-enable Nanite/Lumen at world scale (revisit of 0002) | Proposed |
| [0015](0015-indoor-first-expedients-are-temporary.md) | Indoor-first expedients are temporary (revisit triggers) | Proposed |
| [0016](0016-cpp-blueprint-split.md) | C++ / Blueprint split strategy | Proposed |
| [0017](0017-collision-physics-representation.md) | Collision / physics representation | Proposed |
| [0018](0018-water-liquid-swim.md) | Water / liquid surfaces + swim physics | Proposed |
| [0019](0019-portal-transitions.md) | Portal transitions / recall / teleport | Proposed |
| [0020](0020-network-object-lifecycle.md) | Network object lifecycle / replication of other players & creatures | Proposed |
| [0021](0021-determinism-at-world-scale.md) | Determinism at world scale (simulation vs streaming) | Proposed |
| [0022](0022-audio.md) | Audio (samples, event/ambient mapping, spatialization) | Proposed |

The open-world / world-scale design analysis that motivates ADRs 0009-0015 is in
[`../notes/feature-disposition-and-design-gaps.md`](../notes/feature-disposition-and-design-gaps.md).

Option analysis for the lighting decision is at
[`../notes/lighting-options.md`](../notes/lighting-options.md); the call is
recorded in ADR-0007.
