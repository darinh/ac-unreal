# 0008 - Skip portal polygons (Stippling == NoPos) on EnvCell export
Status: Accepted   Date: 2026-05-31

## Context
An AC indoor `EnvCell` is one room. Cells connect to their neighbours through
**portal** polygons — the see-through openings (a doorway into the next room, a
floor/ceiling opening into the cell stacked above or below). In the DAT these
openings are real polygons in `CellStruct.Polygons`, listed by id in
`CellStruct.Portals`, and cross-referenced by `EnvCell.CellPortals`
(`PolygonId -> OtherCellId`). They carry a placeholder surface (often a solid
black colour) and are flagged with stippling `NoPos` ("no positive surface to
draw").

The extractor's `ExportEnvCell` originally emitted **every** polygon as a solid
OBJ face. That baked an opaque surface over every opening. Concretely, the first
academy room (`0x860201AD`) has two `NoPos` portals: poly 12 -> `0x...01B4`
(the hallway) and poly 13 -> `0x...02E2` (the wood-beam cell above). Poly 13 was
exported as a solid black quad at the ceiling, occluding the wood beams you are
supposed to see through the opening.

The reference renderer **ACViewer** (`Render/R_CellStruct.cs`, `Draw()`) skips
exactly these: `if (polygon._polygon.Stippling == StipplingType.NoPos) continue;`
— it draws only `PosSurface` and never `NoPos` faces.

## Decision
`ExportEnvCell` skips polygons whose `Stippling == StipplingType.NoPos` before
triangulating to OBJ, mirroring ACViewer's EnvCell render path exactly (exact
equality, **not** `HasFlag`, so `NoUVS = 0x14` — which shares the `NoPos` bit —
is still rendered, matching ACViewer). The adjacent cell's own (rendered) facing
polygon is what shows through the opening; AC stacks cells with one see-through
`NoPos` side and one normal rendered side.

## Consequences
- Openings render through to the neighbouring cell (wood ceiling, hallway, etc.)
  instead of an opaque placeholder surface; the solid-black portal "material"
  (`surf_*`) no longer appears in the OBJ/MTL.
- General and academy-wide: applies to every cell via `export-academy`, no
  per-room logic. Verified with the new `audit-portals` command — across all
  **568** academy cells, **every** skipped (`NoPos`) polygon is a declared
  portal (`NoPos ⊆ CellStruct.Portals`), **0** cells where a skipped polygon is
  not a portal, and **0** cells left with no geometry. Portals are a *superset*:
  109 portal sides are normal `Positive` faces and are correctly **kept** (these
  are the surfaces seen through the openings from the other side).
- Re-extraction is required for already-exported cells to pick up the change
  (the committed first-room asset was rebuilt; full academy re-import is a
  follow-up via the pipeline).
- New read-only diagnostics: `dump-poly-stippling`, `audit-portals`.

## Alternatives
- Filter by `CellStruct.Portals.Contains(polyId)` instead of the stippling flag:
  more "semantic", but the audit shows portals are a superset of `NoPos`
  (some portal sides are rendered), so filtering by the portal list would wrongly
  drop the rendered facing surfaces. The stippling flag is the render-faithful
  criterion (it is exactly what ACViewer uses); the portal list is retained only
  as a validation cross-check.
- Emit portals to a separate non-rendered OBJ group: rejected as unnecessary
  complexity — nothing downstream consumes them.
