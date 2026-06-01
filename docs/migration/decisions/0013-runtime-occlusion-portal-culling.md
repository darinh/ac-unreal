# 0013 - Runtime occlusion / portal culling (CellPortals / VisibleCells)
Status: Proposed   Date: 2026-05-31

## Context
AC interiors are portal-connected `EnvCell`s: openings are `Stippling == NoPos`
portal polygons cross-referenced by `EnvCell.CellPortals` (`PolygonId ->
OtherCellId`), and cells carry a visibility set used for occlusion [DATA/REF-IMPL:
ADR-0008; README §II L84 `VisibleCells` - confirm exact field vs ACE `EnvCell`].
The extractor now correctly **skips** `NoPos` faces so openings show through
(ADR-0008), but there is **no runtime occlusion design**: all cells render in one
level, which (a) contributes to the `-game` load hang and (b) lets the outdoor
`SkyAtmosphere` show as "blue sky" through ceiling/doorway openings into cells
that are not present/occluding.

Disposition: **MIRROR** AC's portal/cell visibility.

## Decision
TBD (Proposed). Candidate [DESIGN]: drive UE visibility from the cell graph -
stream/cull cells by `VisibleCells` (interior PVS) and ensure interiors occlude
the outdoor sky (sky/atmosphere disabled or occluded inside cells). Integrate
with ADR-0009 (cells as data layers) and ADR-0011 (indoor vs outdoor sky).

## Consequences
- Removes the indoor sky-leak and a chunk of the load cost; required for dungeons
  to render correctly at scale.
- Revisit trigger: if UE precomputed visibility / cull-distance volumes cannot
  represent AC's PVS faithfully, consider a custom visibility component.

## Alternatives
- Render every cell always (status quo): rejected (hang + sky-leak + perf).
- Pure UE auto-occlusion with no portal data: rejected (loses AC's authored PVS).

## Verify before locking
- H4: exact `EnvCell.VisibleCells` semantics (PVS vs simple adjacency) - ACE `EnvCell`.
