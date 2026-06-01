---
name: ac-world-streaming
description: "Use when implementing or reasoning about AC's open world in Unreal Engine — landblock streaming, World Partition setup, the AC->UE axis swap and grid indexing, terrain representation, HLOD, indoor cell data layers, and large-world coordinate precision (LWC). AC is a seamless ~49 km world keyed per 192 m landblock; loading it all at once hangs. Implements decisions ADR-0009/0010/0013."
metadata:
  category: world
---

# AC open world -> UE World Partition

AC is a **seamless, zoneless ~49 km world** partitioned into **192 m x 192 m
landblocks** (8x8 grid of 24 m land cells). The retail client streamed landblocks
around the player. The naive "all actors in one level" approach **hangs `-game`**
("Waiting for static meshes to be ready N/618") and does not scale. Mirror AC's
per-landblock streaming with **World Partition**. Decisions: ADR-0009 (streaming),
ADR-0010 (precision), ADR-0013 (occlusion).

## The axis-swap gotcha (get this right or the world transposes)
The AC->UE transform **swaps X and Y** (`UE.X = AC.Y*100`, `UE.Y = AC.X*100`).
So landblock `(LbX, LbY)` (id high-16 = `(LbX<<8)|LbY`) lands at UE
`X in [LbY*19200,...]`, `Y in [LbX*19200,...]`. Therefore **the WP grid column
(UE.X) indexes LbY and the row (UE.Y) indexes LbX.** Put this in ONE
`LandblockId <-> UE WP cell` helper with round-trip tests and use it everywhere;
an inconsistent swap mirrors/transposes the whole map. Pair with the world-origin
question (which landblock corner is UE origin) — `[VERIFY]` in `contract/` §0.

## Grid sizing
- WP runtime cell = **one landblock = 19200 UU**. Sparse ocean cells are free.
- **Loading range = (verified AC active-landblock radius) x 19200 UU.** Do NOT
  guess the radius — confirm it (ACE `LandblockManager`) and expose it as a tunable.
- Streaming source on the player pawn AND on any headless render rig (so captures
  stream the same cells a player would).

## What goes in each cell
WP auto-assigns actors by world location: terrain for that landblock; scenery
(`Scene 0x12`) as **HISM/foliage instances, never per-object actors**; buildings
(`LandblockInfo` 0xFFFE); and indoor `EnvCell`s (they carry world frames inside
the landblock footprint, dungeons stacked at lower Z). Group interiors on a
**Data Layer** and let `VisibleCells` (ADR-0013) do per-cell occlusion inside.

## Terrain — the one real wrinkle
AC terrain is **9x9 height verts = 8x8 quads/landblock @ 24 m**. UE Landscape wants
quads-per-section in {7,15,31,63,127,255}; 8 does not divide cleanly.
- **Recommended first: per-landblock static-mesh terrain** (1:1 from the 81
  heights, drops into the WP cell, Nanite-LOD-able once ADR-0014 re-enables it).
  We import terrain, we don't sculpt it, so losing Landscape tooling is cheap.
- **Evaluate later: UE Landscape** with heights resampled to a friendly
  resolution (better runtime LOD + virtual heightfield + layer blending for AC's
  6-UV terrain-type blend).

## Distant world = HLOD (an ADD; AC had none — it used fog)
Add a coarser HLOD layer (e.g. 4x4 landblocks/cell) generating merged proxies
beyond the loading range, out to the far clip. Tune far-clip + fog to the
extracted `RegionDesc` values (ADR-0011); HLOD fills what fog used to hide.

## Precision (LWC)
A 49 km world exceeds single-float comfort (~20 km). UE **LWC double precision**
is active (`largeworldcoordinates="1"`). Decide LWC-global vs landblock-local
rebasing (ADR-0010); avoid double-rebasing (WP origin-shift + landblock-local).

## Order of operations
1. Resolve the load radius + world origin (small extractions).
2. Build the `LandblockId <-> WP cell` helper with round-trip tests.
3. WP on a **2x2 landblock** test region (static-mesh terrain + scenery instances);
   confirm streaming in/out around a moving source.
4. Fold the academy landblock `0x8602` in as the indoor Data-Layer case (ADR-0013).
5. Scale out; add HLOD; revisit Landscape / Nanite.

## Verify before locking
AC client load radius · landblock-local vs global coords + world origin
(`contract/` §0/§0b) · `EnvCell.VisibleCells` semantics · whether terrain LOD is
distinct from `DegradeInfo`. See ADR-0009 deep-dive for the full mapping.
