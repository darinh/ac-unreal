# 0009 - World-scale streaming: landblock grid -> UE World Partition
Status: Proposed   Date: 2026-05-31

## Context
AC is a seamless, zoneless ~49 km world; all world data is keyed **per
landblock** (192 m x 192 m, 8x8 grid of 24 m cells) [DATA: `Program.cs`
`ListLandblocks`/`LandblockInfo`; glossary]. The retail client streamed
landblocks around the player (no zone loads) [COMMUNITY/VERIFY: confirm the
client's active-landblock radius against ACE `LandblockManager` + community
docs]. The current UE project stores **all academy actors inline in one level**
(no streaming), which is the direct cause of the `-game` "Waiting for static
meshes to be ready N/618" hang and does not scale past one zone. See gap doc
[`../notes/feature-disposition-and-design-gaps.md`](../notes/feature-disposition-and-design-gaps.md) §D.

Disposition: **MIRROR** AC's per-landblock streaming intent via a UE mechanism.

## Decision
TBD (Proposed). Candidate [DESIGN]: enable **World Partition** with a streaming
grid aligned to the 192 m landblock boundary (cell-size = 192 m or a divisor),
runtime streaming source on the player; indoor `EnvCell`s grouped as data layers
/ sublevels keyed by landblock. Loading range set from the verified AC radius
(item H1). Deep-dive of the concrete mapping is appended below once drafted.

## Consequences
- Fixes the all-in-one-level hang; required before any outdoor/multi-zone work.
- Forces decisions in ADR-0010 (precision/origin) and ADR-0013 (occlusion) to
  align with the grid; HLOD (an ADD) becomes the mechanism for distant blocks.
- Revisit trigger: if the verified AC load radius or cell size differs from the
  assumed grid, re-tune the WP grid before committing content.

## Alternatives
- Keep one monolithic level: rejected (the current hang; un-scalable).
- Hand-rolled level streaming volumes per landblock: rejected vs World Partition
  unless WP proves unable to honor the landblock grid.

## Verify before locking
- H1: AC client active-landblock load radius (ACE `LandblockManager`).

---

# Deep-dive: concrete landblock -> World Partition mapping

Engineering detail for the Decision above. Tagged [DATA] (from the DAT/extractor/
methodology), [DESIGN] (our proposal, contestable), [VERIFY] (must confirm first).

## 1. The grid + the axis swap (get this right or the world transposes)
- [DATA] A landblock is **192 m**; its id high-16 = `(LbX << 8) | LbY`, `LbX`/`LbY`
  each a byte -> up to **256 x 256** landblocks. Internally 8x8 land cells of 24 m.
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
- **Indoor `EnvCell`s**: they carry world `Position` frames inside the landblock
  footprint (AC dungeons sit under the block, same XY, lower Z) -> they fall into
  the same WP cell automatically. Group them on a **Data Layer** ("Interiors")
  so they can be toggled, and let **ADR-0013** (`VisibleCells` PVS) do the fine
  per-cell occlusion once inside.

## 4. Distant world (HLOD) [DESIGN / ADD]
- A coarser **HLOD layer** (e.g. 4x4 landblocks per HLOD cell ≈ 768 m) generates
  merged proxy meshes for blocks beyond the loading range, out to the far clip.
- AC hid the horizon with **fog** ([DATA] `RegionDesc`); tune the far clip + fog
  to the extracted RegionDesc values (ADR-0011), with HLOD filling the gap the
  fog used to hide. This is genuinely new (AC had no proxy-merge), so budget it.

## 5. Terrain representation — the one real wrinkle [DESIGN]
AC terrain is **9x9 height verts = 8x8 quads per landblock @ 24 m** ([DATA]
`ExportLandblock`). UE **Landscape** wants quads-per-section in `{7,15,31,63,127,255}`
and 1 or 4 sections/component — **8 does not divide cleanly**, so a 1:1 AC->Landscape
mapping needs resampling.
- **Option B (recommended first): per-landblock static-mesh terrain.** A trivial
  8x8 grid mesh from the 81 heights maps 1:1 to the data, drops straight into the
  WP cell, and (when ADR-0014 re-enables it) Nanite can LOD it. Simplest path to
  a streaming world; loses Landscape's sculpt/paint tooling (we don't author
  terrain, we import it, so that loss is cheap).
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
