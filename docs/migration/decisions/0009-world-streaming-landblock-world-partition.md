# 0009 - World-scale streaming: landblock grid -> UE World Partition
Status: Proposed   Date: 2026-05-31

## Context
The world is a grid of landblocks addressed by an 8-bit X / 8-bit Y byte pair
[DATA: `Program.cs` `ListLandblocks`/`LandblockInfo` + glossary — the ID bit
layout / file-id patterns]. Each landblock is **192 m**, subdivided 8x8 into 24 m
land cells [REF-IMPL: ACViewer `Physics/Common/LandDefs.cs`
`BlockLength=192`/`CellLength=24`/`BlockSide=8`; the extractor does not yet emit
metric dimensions], giving a maximum extent of ~49 km per side (arithmetic). That
the world is **seamless/zoneless** with a long view distance is retail *client
behavior* [COMMUNITY/VERIFY]. The world *data* is keyed strictly per-landblock
[DATA] — the structural enabler for streaming — but the retail *client's*
active-landblock load policy is [COMMUNITY/VERIFY]; do **not** infer it from ACE
`LandblockManager`, which is server-side. The current UE project stores **all
academy actors inline in one level** (no streaming); this **likely contributes**
to the `-game` "Waiting for static meshes to be ready N/618" hang, but the root
cause is **not isolated** (procedural-mesh build, Nanite/Lumen paths,
mesh-readiness/compilation, and actor count are all candidates) [DESIGN — validate
with a controlled before/after load trace]. It does not scale past one zone
regardless. See gap doc
[`../notes/feature-disposition-and-design-gaps.md`](../notes/feature-disposition-and-design-gaps.md) §D.

Disposition: **MIRROR** AC's per-landblock data partitioning via a UE mechanism;
the streaming *policy* mirrors the client only once the load radius is verified.

## Decision
TBD (Proposed). Candidate [DESIGN]: enable **World Partition** with a streaming
grid aligned to the 192 m landblock boundary (cell-size = 192 m or a divisor),
runtime streaming source on the player; indoor `EnvCell`s grouped as data layers
/ sublevels keyed by landblock. Loading range set from the verified AC radius
(item H1). Deep-dive of the concrete mapping is appended below once drafted.

## Consequences (if this candidate is accepted)
- Removes the monolithic-level load pressure (a likely contributor to the hang;
  root cause not yet isolated — see Context); required for outdoor/multi-zone work.
- Forces ADR-0010 (precision/origin) and ADR-0013 (occlusion) to align with the
  grid; HLOD (an ADD) becomes the mechanism for distant blocks.
- Revisit trigger: if the verified AC load radius or cell size differs from the
  assumed grid, re-tune the WP grid before committing content.

## Alternatives (still live — this is a Proposed candidate, not a decision)
- One monolithic level: not selected (does not scale; likely load pressure).
- Hand-rolled per-landblock streaming volumes: a fallback if World Partition
  cannot honor the landblock grid.

## Assumptions this candidate depends on (must hold before Accepted)
- A1 [VERIFY]: indoor cells are co-located within their parent landblock's XY
  footprint (so they stream with it) — see deep-dive; contradicts nothing only if
  confirmed (contract §0b marks the indoor domain UNKNOWN).
- A2 [VERIFY]: the monolithic level is a material cause of the hang (load trace).

## Verify before locking
- H1: AC client active-landblock load **radius/policy** (NOT from server-side ACE
  `LandblockManager` alone; confirm the client's behavior).
- See also the deep-dive's "Verify before locking" and the per-assumption checks above.

---

# Deep-dive: concrete landblock -> World Partition mapping

Engineering detail for the Decision above. Tagged [DATA] (from the DAT/extractor/
methodology), [DESIGN] (our proposal, contestable), [VERIFY] (must confirm first).

## 1. The grid + the axis swap (get this right or the world transposes)
- The landblock id high-16 = `(LbX << 8) | LbY`, `LbX`/`LbY` each a byte -> up to
  **256 x 256** landblocks [DATA: extractor ID layout]. A landblock is **192 m**,
  8x8 land cells of **24 m** [REF-IMPL: ACViewer `LandDefs.cs`
  `BlockLength=192`/`CellLength=24`/`BlockSide=8`]; ~49 km/side is arithmetic.
- [DATA] The AC->UE transform **swaps X and Y** and scales m->cm:
  `UE.X = AC.Y*100`, `UE.Y = AC.X*100` (methodology §4).
- [DESIGN] Therefore landblock `(LbX, LbY)`, occupying AC metres
  `X'∈[LbX·192,(LbX+1)·192]`, `Y'∈[LbY·192,(LbY+1)·192]`, lands in UE at
  `UE.X∈[LbY·19200,(LbY+1)·19200]`, `UE.Y∈[LbX·19200,(LbX+1)·19200]`.
  **Consequence:** the WP grid column (UE.X) indexes **LbY**, and the row (UE.Y)
  indexes **LbX**. Pick one convention in a single helper
  (`LandblockId <-> UE cell`) and use it everywhere; an inconsistent swap mirrors
  or transposes the whole map. This pairs with the world-origin question
  ([VERIFY] contract §0: which landblock corner is UE origin).

## 2. WP grid sizing [DESIGN]
- **Runtime grid cell = one landblock = 19200 UU.** Simple 1:1 mental model;
  WP handles the sparse ocean blocks (empty cells cost nothing).
- **Loading range = (verified AC radius) x 19200 UU.** Do **not** guess the
  radius; set it from H1. If AC kept an `R`-landblock neighborhood hot, range ≈
  `R·192 m`. Expose it as a tunable, default to the verified value.
- Keep the streaming source on the player pawn (and on any render rig used for
  headless captures, so screenshots stream the same cells the player would).

## 3. What goes in each cell [DESIGN]
WP auto-assigns actors to grid cells by world location, so placement just works
if positions are correct:
- **Terrain** for that landblock (see §5).
- **Scenery** (`Scene 0x12`) as **HISM/foliage** instances, not actors.
- **Buildings / structures** (`LandblockInfo` 0xFFFE) static meshes.
- **Indoor `EnvCell`s**: **[VERIFY — this is the #1 gating assumption]** the
  working hypothesis is that an EnvCell's world frame sits within its parent
  landblock's XY footprint (dungeons stacked at lower Z), so WP would assign it to
  the same cell automatically. This is **NOT confirmed** — `contract/` §0b marks
  the indoor coordinate domain UNKNOWN, and it is only observed for *some* academy
  cells. **Required check before accepting this ADR:** dump transformed UE XY
  bounds for EnvCells across several known dungeons/buildings and confirm they lie
  within the parent landblock footprint (and record whether interiors are global /
  landblock-local / a separate domain). If false, the WP grouping, ADR-0010
  (coords), ADR-0013 (culling), and portal-transition handling all change. Once
  confirmed: group interiors on a **Data Layer**; let **ADR-0013** drive per-cell
  occlusion.

## 4. Distant world (HLOD) [DESIGN / ADD]
- A coarser **HLOD layer** (e.g. 4x4 landblocks per HLOD cell ~= 768 m) generates
  merged proxy meshes for blocks beyond the loading range, out to the far clip.
- `RegionDesc` **contains fog params** [DATA]; that the retail client used fog to
  hide the draw-distance horizon is [VERIFY] (M4) — confirm the client's
  draw-distance/horizon treatment before treating fog as the fidelity baseline.
  Tune far clip + fog to the extracted values (ADR-0011); HLOD fills what fog hid.
  Proxy-merge is genuinely new (AC had none), so **budget the HLOD build cost**;
  a 255x255 grid could block CI -> spike a 4x4 region first.

## 5. Terrain representation — the one real wrinkle [DESIGN]
AC terrain is **9x9 height verts = 8x8 quads per landblock @ 24 m** ([DATA]
`ExportLandblock`). UE **Landscape** wants quads-per-section in `{7,15,31,63,127,255}`
and 1 or 4 sections/component — **8 does not divide cleanly**, so a 1:1 AC->Landscape
mapping needs resampling.
- **Option B (prototype first, NOT "trivial" — C4): per-landblock static-mesh
  terrain.** A per-landblock grid mesh from the 81 heights is the simplest path to
  a streaming world, but it is a **prototype** with unresolved requirements, not a
  drop-in. Acceptance criteria before it counts as working:
  - height **indices -> metres** via `RegionDesc.LandDefs.LandHeightTable`
    (`ExportLandblock` currently writes raw indices cast to float — a TODO);
  - **edge-compatible** verts + normals across the 2x2 landblock boundary (no
    cracks / lighting seams);
  - terrain-type **alpha blending** preserved (AC's 6-UV `LandVertex`) or the
    visual loss explicitly accepted; roads/overlays handled;
  - **collision** present + a movement test on the slope;
  - HLOD cost measured.
  (When ADR-0014 re-enables it, Nanite can LOD the mesh.)
- **Option A (evaluate later): UE Landscape** with WP streaming proxies, AC
  heights resampled to a Landscape-friendly resolution. Better runtime LOD +
  virtual-heightfield + landscape-material layer blending (matches AC's 6-UV
  terrain-type blend), at the cost of a resampling step and authoring its
  material layers. Revisit once the world streams.

## 6. Order of operations [DESIGN]
1. Resolve H1 (load radius) + world origin (contract §0) — small extractions.
2. Build the `LandblockId <-> UE WP cell` helper (§1) with round-trip tests.
3. Stand up WP on a **2x2 landblock** test region (terrain Option B + scenery
   instances) and confirm streaming in/out around a moving source.
4. Fold the existing academy landblock `0x8602` in as the indoor Data-Layer case
   (ties to ADR-0013).
5. Only then scale out, add the HLOD layer (§4), and revisit Landscape (§5A) /
   Nanite (ADR-0014).

## Open technical questions [VERIFY/DESIGN]
- World origin corner + whether AC Z (height) needs an offset to keep UE Z sane.
- Does any landblock's content exceed a single WP cell (large surface buildings)?
  If so, raise the cell size or rely on WP's actor-spanning handling.
- Interaction of LWC (ADR-0010) with WP cell origins: confirm we are not double-
  rebasing (WP origin-shift + landblock-local both applied).
