---
name: ac-world-streaming
description: "Use when implementing or reasoning about AC's open world in Unreal Engine — landblock streaming, World Partition setup, the AC->UE axis swap and grid indexing, terrain representation, HLOD, indoor cell data layers, and large-world coordinate precision (LWC). AC is a seamless ~49 km world keyed per 192 m landblock; loading it all at once hangs. Implements decisions ADR-0009/0010/0013."
metadata:
  category: world
---

# AC open world -> UE World Partition

AC is a **~49 km world** `[REF-IMPL: derived from ACE/ACViewer LandDefs +
`ACE.Entity/Position.cs:516-519`]` partitioned into **192 m x 192 m
landblocks** (8x8 grid of 24 m land cells) `[REF-IMPL: `Position.cs:516-519`]`.
Whether the retail *client* streamed landblocks around the player (and presented a
"seamless/zoneless" world) is `[COMMUNITY/VERIFY]` — ACE's `LandblockManager` is
**server-side** `[REF-IMPL]`, not proof of client behavior. Regardless, the naive
"all actors in one level" approach **hangs `-game`**
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
  guess the radius — confirm it from the **client** (ACE's `LandblockManager` is
  server-side, not client proof — see above) and expose it as a tunable.
- Streaming source on the player pawn AND on any headless render rig (so captures
  stream the same cells a player would).

## What goes in each cell
WP auto-assigns actors by world location: terrain for that landblock; scenery
(`Scene 0x12`) as **HISM/foliage instances, never per-object actors**; buildings
(`LandblockInfo` 0xFFFE); and indoor `EnvCell`s. Each `EnvCell` carries a
**landblock-local** `Frame Position` `[REF-IMPL: `EnvCell.cs:28,56`]`; world position is
`(LbX*192 + Frame.X, LbY*192 + Frame.Y, Frame.Z)` with **no terrain offset on Z** `[REF-IMPL:
ACViewer `PositionExtensions.GetWorldPos:22-29`; world renderer places each EnvCell at that
origin — `R_Landblock.cs:51-56`, `Buffer.cs:340-344`, `InstanceBatch.cs:98-105`]`.
**Measured (ADR-0009 full per-block census; [PRELIMINARY]):** whether that frame stays in the
addressing landblock's `[0..192]` footprint is **type-dependent**. The one **building-interior**
block sampled (Holtburg `0xA9B4`, 12 buildings) was fully co-located (all sampled cells in
footprint); all three **zero-building** blocks (`Buildings==0` — the zero-building half of ACViewer's
`IsDungeon` predicate, not a verified dungeon) placed the large majority of cells **outside** it
(532/568, 734/745, 934/946 — negative-Y, block(s) south), Z spanning a wide range. So **never
assume interiors sit in their parent footprint or at a fixed Z** — compose the frame with
`LbX/Y*192` and check. A Data Layer keyed by addressing landblock organizes interiors but does
not predict which WP cell streams a dungeon. Let `VisibleCells` (ADR-0013) do per-cell occlusion inside.

## Terrain — the one real wrinkle
AC terrain is **9x9 height verts = 8x8 quads/landblock @ 24 m**. UE Landscape wants
quads-per-section in {7,15,31,63,127,255}; 8 does not divide cleanly.
- **Recommended first: per-landblock static-mesh terrain** (1:1 from the 81
  heights, drops into the WP cell, Nanite-LOD-able once ADR-0014 re-enables it).
  We import terrain, we don't sculpt it, so losing Landscape tooling is cheap.
- **Evaluate later: UE Landscape** with heights resampled to a friendly
  resolution (better runtime LOD + virtual heightfield + layer blending for AC's
  6-UV terrain-type blend).

## Distant world = HLOD (an ADD; whether AC used HLOD is `[VERIFY]`)
Add a coarser HLOD layer (e.g. 4x4 landblocks/cell) generating merged proxies
beyond the loading range, out to the far clip. Tune far-clip + fog to the
extracted `RegionDesc` values (ADR-0011; fog params are `[REF-IMPL:
`SkyTimeOfDay.cs:18-21`]`). AC clearly had **no UE-style HLOD**; whether it leaned
on fog to mask draw distance is `[COMMUNITY/VERIFY]`, not established here.

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
