# 0009 - World-scale streaming: landblock grid -> UE World Partition
Status: Proposed   Date: 2026-05-31

## Context
The world is a grid of landblocks addressed by an 8-bit X / 8-bit Y byte pair
[DATA: `Program.cs` `ListLandblocks`/`LandblockInfo` + glossary — the ID bit
layout / file-id patterns]. Each landblock is **192 m**, subdivided 8x8 into 24 m
land cells [REF-IMPL: ACViewer `Physics/Common/LandDefs.cs`
`BlockLength=192`/`CellLength=24`/`BlockSide=8`; the extractor does not yet emit
metric dimensions], giving a maximum extent of ~49 km per side (arithmetic; the
**255 landblocks/axis** count is now confirmed from the client — the cell-coord
guard `0x7f7` = 255·8−1 [DATA: acclient `LScape::update_block` 0x5063A0]). That
the world is **seamless/zoneless** with a long view distance is retail *client
behavior* [COMMUNITY/VERIFY]. The world *data* is keyed strictly per-landblock
[DATA] — the structural enabler for streaming — and the retail *client's*
active-landblock load policy is now **[DATA: acclient] RESOLVED (H1, 2026-06-02)**:
the client's `LScape` landscape engine keeps a square **`(2R+1) × (2R+1)` landblock
window** centered on the viewer, where **`R = mid_radius = Render::m_RenderPrefs.LandscapeDrawDistance`**
— a user graphics setting (presets 3/5/8/11/15; `LScape` default 5), **not** the
server-side ACE `LandblockManager`. Full evidence + provenance:
[notes/client-landblock-load-radius-findings.md](../notes/client-landblock-load-radius-findings.md). The current UE project stores **all
academy actors inline in one level** (no streaming); this **likely contributes**
to the `-game` "Waiting for static meshes to be ready N/618" hang, but the root
cause is **not isolated** (procedural-mesh build, Nanite/Lumen paths,
mesh-readiness/compilation, and actor count are all candidates) [DESIGN — validate
with a controlled before/after load trace]. It does not scale past one zone
regardless. See gap doc
[`../notes/feature-disposition-and-design-gaps.md`](../notes/feature-disposition-and-design-gaps.md) §D.

Disposition: **MIRROR** AC's per-landblock data partitioning via a UE mechanism;
the streaming *policy* mirrors the client's verified `(2R+1)²` window (H1, resolved
below), with the WP loading range exposed as a setting mapped to the client's
`LandscapeDrawDistance` tiers (baseline R=5).

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
- A1 [RESOLVED 2026-05-31, user sign-off — see [notes/envcell-colocation-findings.md](../notes/envcell-colocation-findings.md)
  and §3 census]: indoor cells' co-location within their parent landblock's XY footprint is
  **type-dependent**. Holds for all 8 sampled building-interior (`Buildings>0`) blocks (882/882
  cells in-footprint); **fails** for the 3 sampled zero-building blocks (2200/2259 cells outside).
  The fully general indoor coordinate domain across all blocks remains UNKNOWN (contract §0b); do
  not assume uniform co-location.
- A2 [VERIFY]: the monolithic level is a material cause of the hang (load trace).

## Verify before locking
- H1 [RESOLVED 2026-06-02 — [notes/client-landblock-load-radius-findings.md](../notes/client-landblock-load-radius-findings.md)]:
  AC **client** active-landblock load **radius/policy**, read from the client's
  `LScape` engine (not server-side ACE `LandblockManager`): a square `(2R+1)²`
  landblock window centered on the viewer, `R = LandscapeDrawDistance` (graphics
  presets 3/5/8/11/15; default 5 → 11×11 / 960 m radius). The grid shifts and loads
  only the new edge as the viewer crosses a block boundary.
- See also the deep-dive's "Verify before locking" and the per-assumption checks above.

---

# Deep-dive: concrete landblock -> World Partition mapping

Engineering detail for the Decision above. Tagged [DATA] (from the DAT/extractor/
methodology), [DESIGN] (our proposal, contestable), [VERIFY] (must confirm first).

## 1. The grid + the axis swap (get this right or the world transposes)
- The landblock id high-16 = `(LbX << 8) | LbY`, `LbX`/`LbY` each a byte [DATA:
  extractor ID layout]. ACE treats valid outdoor indices as **0..254 -> 255 per
  side** [REF-IMPL: ACE `LandblockId` rejects >254; `LandblockManager` uses a
  [255,255] table], not a full 256. A landblock is **192 m**, 8x8 land cells of
  **24 m** [REF-IMPL: ACViewer `LandDefs.cs`
  `BlockLength=192`/`CellLength=24`/`BlockSide=8`]; ~49 km/side is derived
  arithmetic [COMMUNITY/VERIFY for the retail playable limit].
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
- **Loading range = `R` x 19200 UU**, `R` = the client's `LandscapeDrawDistance`
  (H1, RESOLVED): the client keeps a square `(2R+1)²` landblock window hot, `R ∈
  {3,5,8,11,15}` (default 5). So **default loading range = 5 × 19200 = 96000 UU
  (960 m)**; expose it as a tunable mapped to those tiers (max 15 → 288000 UU).
  Mirror the client's *square* (Chebyshev) window, not a circular radius.
- Keep the streaming source on the player pawn (and on any render rig used for
  headless captures, so screenshots stream the same cells the player would).

## 3. What goes in each cell [DESIGN]
WP auto-assigns actors to grid cells by world location, so placement just works
if positions are correct:
- **Terrain** for that landblock (see §5).
- **Scenery** (`Scene 0x12`) as **HISM/foliage** instances, not actors.
- **Buildings / structures** (`LandblockInfo` 0xFFFE) static meshes.
- **Indoor `EnvCell`s**: **[VERIFY — this is the #1 gating assumption; substantially
  addressed by the census below]** the original working hypothesis was that an EnvCell's
  world frame sits within its parent landblock's XY footprint (the old guess being that dungeons
  were simply stacked at lower Z — now shown false). The census below shows this
  is **type-dependent**: it held for **all 8** sampled building-interior blocks (every cell
  in-footprint) but failed for the 3 zero-building blocks — so it must **not** be
  assumed uniformly. `contract/` §0b still marks the indoor coordinate domain UNKNOWN in the
  fully general case (the sample, while now broad for building interiors, is not exhaustive).
  Where interiors co-locate (all sampled building interiors): group them on a **Data Layer**;
  let **ADR-0013** drive per-cell occlusion. Where they do not (zero-building blocks): WP
  auto-assignment by world location lands them in a different grid cell than the addressing
  landblock, so ADR-0010 (coords) and ADR-0013 (culling) must handle interiors that cross
  block boundaries.

> **Evidence gathered (2026-05-31, empirical — full per-block census, [PRELIMINARY]):**
> *(Durable standalone record with all citations: [notes/envcell-colocation-findings.md](../notes/envcell-colocation-findings.md) — RESOLVED, user sign-off 2026-05-31.)*
> Method: enumerated **every** indoor `EnvCell` (real Cell-DAT file keys `0x0100..0xFFFD`,
> full census — not a first-N slice, not a probe) in **11 landblocks** and composed each local
> frame to world coordinates with the placement formula proven below, via
> `acdat dump-envcell-positions` (single-process; the footprint test is computed in C#).
> The 8 building-interior candidates were found by scanning **all 5346** `LandblockInfo`
> records with `acdat find-building-blocks` (1639 of 5346 landblocks have `Buildings>0`) and
> sampling across the building-count range (1..49 buildings) and spanning 2..251 EnvCell files
> per block (not the full population, which reaches `NumCells` ~2468). Raw per-cell
> output (every cell ID + frame + composed world position + IN/OUT) is committed at
> `pipeline/dat-extract/samples/envcell_position_census.txt` (regenerate with the sibling
> `.ps1`); DAT iteration 982.
>
> **Proven — how an `EnvCell` is placed in the world (ACViewer render path):**
> `world = (LbX*192 + Frame.Origin.X, LbY*192 + Frame.Origin.Y, Frame.Origin.Z)`, where
> `LbX/LbY` are the cell-id's high bytes and **Z gets no terrain offset** (the Z translation is
> 0, modulo a +0.05 z-fight nudge). [REF-IMPL: ACViewer `Extensions/PositionExtensions.cs:22-29`
> — `GetWorldPos()` returns `(LbX*BlockLength + Frame.Origin.X, LbY*BlockLength + Frame.Origin.Y,
> Frame.Origin.Z)`; the **world renderer** places each EnvCell instance at that origin —
> `Render/R_Landblock.cs:51-56` (`AddEnvCells`), `Render/Buffer.cs:340-344`,
> `Render/InstanceBatch.cs:98-105` (`origin = EnvCell.Pos.GetWorldPos()`);
> `Physics/Common/LandDefs.cs:102` — `BlockLength=192` — verified. (`PositionExtensions.ToXna:9-20`
> / `R_EnvCell.cs:47-49,78` give the same composition for the unbatched model-viewer path.)]
> The frame is therefore **landblock-local**, and a frame outside `[0,192]` simply renders in a
> different world block.
> (The ACE.Entity `Position.SetLandblock` block-offset normalization does **not** apply to
> EnvCells: it early-returns for indoor cells — `if (Indoors) return false`,
> ACE.Entity `Position.cs:123` — verified.)
>
> **The hypothesis must be split by cell type.** An `EnvCell` is "mostly dungeons, but can also
> be a building interior" [REF-IMPL: ACE.DatLoader `FileTypes/EnvCell.cs:11` — verified]. ACViewer
> flags a landblock `IsDungeon` when all terrain heights are 0 **and** it has EnvCells but **zero
> buildings** [REF-IMPL: ACViewer `Physics/Common/Landblock.cs:592-604` — verified]. I measured
> only the **zero-building** half of that predicate (`LandblockInfo.Buildings==0`); the
> all-heights-0 half is **unverified per block**, so the zero-building rows below are labeled as
> such — a *necessary, not sufficient* condition for ACViewer's `IsDungeon`, and **not** an
> asserted dungeon/content classification. (`0x8602`, the project's "academy", is zero-building.)
> **"building interior"** = `LandblockInfo.Buildings>0`. Census, split by category:
>
> | Landblock | LbX,LbY | Buildings | Category | Frame.Origin bbox (X / Y / Z) | Cells in `[0,192]²` |
> |---|---|---|---|---|---|
> | `0x1203` | 18,3 | 49 | **building interior** | X[12.00..156.00] Y[12.00..156.00] Z[0.00..0.00] | **182 / 182 IN** |
> | `0xDA55` | 218,85 | 42 | **building interior** | X[9.12..188.40] Y[3.96..186.58] Z[20.00..20.04] | **251 / 251 IN** |
> | `0x8851` | 136,81 | 38 | **building interior** | X[12.00..180.00] Y[12.00..180.00] Z[0.00..30.00] | **76 / 76 IN** |
> | `0xC6A9` | 198,169 | 30 | **building interior** | X[12.00..132.00] Y[12.00..108.00] Z[42.00..42.00] | **205 / 205 IN** |
> | `0xA9B4` (Holtburg) | 169,180 | 12 | **building interior** | X[31.50..161.93] Y[7.50..159.50] Z[66.00..94.00] | **138 / 138 IN** |
> | `0x0503` | 5,3 | 3 | **building interior** | X[84.00..132.00] Y[36.00..36.00] Z[150.00..225.00] | **21 / 21 IN** |
> | `0x0408` | 4,8 | 1 | **building interior** | X[108.02..108.02] Y[132.29..132.29] Z[87.19..87.19] | **7 / 7 IN** |
> | `0x0604` | 6,4 | 1 | **building interior** | X[60.00..60.00] Y[108.00..108.00] Z[22.00..22.00] | **2 / 2 IN** |
> | `0x8602` (academy) | 134,2 | 0 | zero-building | X[0.00..210.00] Y[-250.00..0.00] Z[-12.00..18.00] | 36 IN / **532 OUT** |
> | `0x01AE` | 1,174 | 0 | zero-building | X[0.00..180.00] Y[-140.00..0.00] Z[-36.00..24.00] | 11 IN / **734 OUT** |
> | `0x00D6` | 0,214 | 0 | zero-building | X[0.00..120.00] Y[-340.00..0.00] Z[-6.00..96.00] | 12 IN / **934 OUT** |
>
> **Result (11 blocks: 8 building-interior + 3 zero-building; [PRELIMINARY]):** co-location is
> **type-dependent**. **All 8 building-interior blocks were fully co-located — 882 / 882 cells
> (100%) inside the addressing landblock's XY footprint**, across the sampled range
> (1..49 buildings; 2..251 EnvCell files per block — note `Buildings>0` blocks in the
> population reach far higher cell counts, e.g. `NumCells` up to ~2468, which this sample does
> **not** cover). All 3 **zero-building** blocks placed the **large majority**
> of cells *outside* that footprint (532/568, 734/745, 934/946 — combined **2200/2259, 97.4%
> OUT**, into negative-Y, i.e. the block(s) to the south), with only a small minority near the
> origin inside. (Two building blocks have more EnvCell *files* than `LandblockInfo.NumCells` —
> `0xA9B4` 138 vs 123, `0xDA55` 251 vs 236; `NumCells` is the subset ACViewer's world renderer
> walks — `R_Landblock.cs:90-100` iterates `0x100..0x100+NumCells` — and since *all* files in
> those blocks are in-footprint, the rendered subset is too.) Z is the raw frame Z with no
> terrain offset; the Z ranges are wide (e.g. `0x00D6` spans Z[-6..96]), and whether any given Z
> sits above or below ground is **unmeasured** (would require the landblock height table) and is
> **not** claimed here.
>
> **Decision impact:** (a) compose every EnvCell with `LbX/Y*192` per the proven formula —
> never assume in-footprint without checking the category; (b) for the sampled **zero-building**
> blocks, WP auto-assignment by world location would place most geometry in a **different** grid
> cell than the addressing landblock, so a Data Layer keyed by addressing landblock organizes
> interiors but does **not** predict which WP cell streams them; (c) ADR-0010 (coords) and
> ADR-0013 (culling) must handle interiors that cross block boundaries. The building-interior
> co-location result is now **broadly sampled** (n=8, every cell co-located); the *fully general*
> claim across all ~1639 building blocks and the zero-building Z-vs-ground question remain
> **[PRELIMINARY]** pending wider sampling and the heights-0 measurement.

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
1. ~~Resolve H1 (load radius) + world origin (contract §0)~~ **DONE 2026-06-02**
   (decompile, not extraction) — [notes/client-landblock-load-radius-findings.md](../notes/client-landblock-load-radius-findings.md):
   R = `LandscapeDrawDistance` (default 5); world axes +X East / +Y North / +Z up
   [DATA], origin corner = SW of LB(0,0) [DERIVED].
2. Build the `LandblockId <-> UE WP cell` helper (§1) with round-trip tests.
3. Stand up WP on a **2x2 landblock** test region (terrain Option B + scenery
   instances) and confirm streaming in/out around a moving source.
4. Fold the existing academy landblock `0x8602` in as the indoor Data-Layer case
   (ties to ADR-0013).
5. Only then scale out, add the HLOD layer (§4), and revisit Landscape (§5A) /
   Nanite (ADR-0014).

## Open technical questions [VERIFY/DESIGN]
- ~~World origin corner~~ **RESOLVED**: axes `+X` East, `+Y` North, `+Z` up
  **[DATA: acclient `get_block_orient` 0x504F90]**; world `(0,0,0)` = **SW corner of
  landblock `(0,0)`** **[DERIVED]** (from axes + intra-block `[0,192)` clamp + id
  encoding). On Z, the DATA fact is narrower: `calc_frame` applies **no Z offset**
  (there is no `viewer_b_zoff`; `origin.z = 0`) **[DATA: acclient 0x505460]** — so
  **"UE Z = AC height directly" is the [DERIVED] mapping**, still gated by the open
  negative-heights / UE-Z-datum question. See findings note.
- Does any landblock's content exceed a single WP cell (large surface buildings)?
  If so, raise the cell size or rely on WP's actor-spanning handling.
- Interaction of LWC (ADR-0010) with WP cell origins: confirm we are not double-
  rebasing (WP origin-shift + landblock-local both applied). **Note [DATA]:** the
  retail client's **`LScape` terrain** path already used a single viewer-block-
  relative floating origin — `calc_frame` rebases the landscape on the viewer's
  block, with `viewer_b_xoff/yoff` set in `calc_draw_order` [acclient: 0x505460,
  0x505C70]. **Mirror that for outdoor terrain; do not stack** WP origin-shift on a
  landblock offset. Whether non-terrain/indoor paths (`CellManager`/`CObjMaint`/
  portals) add their own frame is **[DESIGN]**, unverified → issue #4. See ADR-0010.
