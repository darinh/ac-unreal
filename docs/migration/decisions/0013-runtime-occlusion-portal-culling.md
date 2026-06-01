# 0013 - Runtime occlusion / portal culling (CellPortals / VisibleCells)
Status: Proposed   Date: 2026-05-31

## Context
AC interiors are portal-connected `EnvCell`s: openings are `Stippling == NoPos`
portal polygons cross-referenced by `EnvCell.CellPortals` (`PolygonId ->
OtherCellId`) [DATA: ADR-0008], and cells carry a `VisibleCells` set whose
semantics are **not confirmed** — ACE `EnvCell.cs` literally comments "*I believe*
this is what cells can be seen from this one", so whether it is a true PVS or mere
adjacency is [VERIFY], not [DATA].
The extractor now correctly **skips** `NoPos` faces so openings show through
(ADR-0008), but there is **no runtime occlusion design**: all cells render in one
level, which (a) contributes to the `-game` load hang and (b) lets the outdoor
`SkyAtmosphere` show as "blue sky" through ceiling/doorway openings into cells
that are not present/occluding.

Disposition: **MIRROR** AC's portal/cell visibility.

## Decision
TBD (Proposed). These are **two separate problems** (the earlier draft conflated
them); each needs its own design + acceptance test:
1. **Interior cell visibility/culling.** Candidate [DESIGN]: drive UE visibility
   from the cell graph. *If* `VisibleCells` is confirmed PVS, cull by it; *if*
   adjacency-only, derive visibility separately (e.g. from `CellPortals`
   reachability). Integrate with ADR-0009 (cells as a Data Layer).
2. **Indoor sky/atmosphere suppression.** Culling cells does NOT by itself stop
   `SkyAtmosphere` leaking through portal holes; suppression likely needs a
   distinct mechanism (sky/stencil mask, post-process volume, lighting channel, or
   loading the occluding neighbour geometry). Ties to ADR-0011 (indoor vs outdoor).

## Consequences (if accepted)
- (1) cuts interior load/draw cost; (2) removes the indoor sky-leak. Required for
  dungeons at scale.
- Revisit trigger: if UE precomputed visibility / cull-distance volumes cannot
  represent AC's visibility faithfully, consider a custom visibility component.

## Alternatives (still live)
- Render every cell always (status quo): not selected (load + sky-leak + perf).
- Pure UE auto-occlusion with no portal data: not selected (loses AC's authored
  visibility), but may suffice as a fallback if `VisibleCells` is only adjacency.

## Assumptions it depends on
- A1 [VERIFY]: `EnvCell.VisibleCells` is a usable visibility set (PVS) vs mere
  adjacency (ACE hedges — see Context).
- A2 [VERIFY]: indoor cells are reachable as a streamable group (gated on the same
  indoor-domain question as ADR-0009 A1 / ADR-0010 A2 / contract §0b). *Partial: per-block
  co-location is RESOLVED (type-dependent) — see
  [notes/envcell-colocation-findings.md](../notes/envcell-colocation-findings.md); zero-building
  interiors can fall OUTSIDE the addressing landblock's footprint, so a streamable group must be
  keyed explicitly, not inferred from world location.*

## Evidence required before Accepted
- Compare `VisibleCells` against `CellPortals` adjacency on a representative
  dungeon (is it PVS or adjacency?).
- A prototype where (1) cells outside the visibility set are culled and (2) the
  outdoor sky does not appear through any portal opening.

## Sequencing
- ADR-0009 establishes the WP grid + interior Data Layer **first**; this ADR then
  layers visibility/culling and sky suppression on top.

## Acceptance test
- (1) From inside a multi-cell dungeon, only visible cells are resident/drawn.
- (2) Looking up/through every portal opening shows the neighbour cell or solid
  occluder — **never** the outdoor `SkyAtmosphere`.

## Verify before locking
- H4: exact `EnvCell.VisibleCells` semantics (PVS vs simple adjacency) - ACE `EnvCell`.
