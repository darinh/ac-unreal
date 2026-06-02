# Client landblock load radius + world origin — decompile findings

**Status:** RESOLVED (client-sourced). Closes issue #3 (gates ADR-0009 H1, ADR-0010 A1).
**Date:** 2026-06-02
**Source of truth:** the decompiled **retail AC client** (`acclient.exe`, PDB-named
Ghidra pseudo-C) at `C:\Users\darin\repos\ac-client\decomp\_baseline\by_addr\`.
Per issue #3 the load policy is taken from the **client** (the `LScape` landscape
engine), **not** from server-side ACE `LandblockManager`. ACE corroboration is
noted where it agrees, but the citations below are the client binary.

> **Citation form:** `[acclient: <addr>]` → function at
> `decomp/_baseline/by_addr/<addr>__<name>.c`. Tags: **[DATA]** = read directly
> from the client; **[DERIVED]** = arithmetic from DATA; **[NOT-CLAIMED]** = out of
> scope / unverified.

---

## TL;DR (the two answers issue #3 asked for)

1. **Active-landblock load radius / policy [DATA].** The client's landscape engine
   (`LScape`) keeps a **square `(2R+1) × (2R+1)` window of landblocks centered on
   the viewer's landblock**, where **`R = mid_radius = Render::m_RenderPrefs.LandscapeDrawDistance`**
   — a **user graphics setting**, not a fixed constant. The whole window is the
   loaded/active set (terrain + static objects + buildings); as the viewer crosses
   a block boundary the grid shifts and only the new edge blocks are loaded.
   - **`LScape` constructor default `R = 5`** → 11×11 window. [acclient: 00505370]
   - **Graphics-quality presets set `R ∈ {3, 5, 8, 11, 15}`** (low→high). [acclient: 0054B020 `SetOverallGraphicsQuality`]
   - In metres (`R × 192 m` radius; `(2R+1) × 192 m` window side):

     | `R` (LandscapeDrawDistance) | Window | Radius | Window side |
     |---|---|---|---|
     | 3 (lowest) | 7×7 | 576 m | 1344 m |
     | **5 (default / "medium")** | **11×11** | **960 m** | **2112 m** |
     | 8 | 17×17 | 1536 m | 3264 m |
     | 11 | 23×23 | 2112 m | 4416 m |
     | 15 (highest) | 31×31 | 2880 m | 5952 m |

2. **World origin + axes [DATA].** AC world space is **+X = East, +Y = North,
   +Z = up** (Z-up, height above 0). The **world origin `(0,0,0)` is the
   south-west (min-East, min-North) corner of landblock `(LbX=0, LbY=0)`**. A
   landblock `(LbX, LbY)` occupies AC-metres `X ∈ [LbX·192, (LbX+1)·192]`,
   `Y ∈ [LbY·192, (LbY+1)·192]`; intra-block local coordinates run `[0, 192)` from
   that SW corner. The landblock id high-16 encodes `(LbX << 8) | LbY` — **high
   byte = LbX (East), low byte = LbY (North)** — with **255 landblocks per axis**.
   - Bonus (resolves **ADR-0010 A1**): AC stores positions **landblock-LOCAL**
     (`objcell_id` + an intra-cell frame), not global; world coordinates are
     *composed* from the cell id. The client's *render* frame goes one step
     further and rebases the whole landscape **relative to the viewer's block**
     (a floating origin) — see §3.

---

## 1. The landscape engine: `LScape` and the `mid_radius` window

`LScape` is the client's outdoor landscape manager. Its constructor establishes the
loaded-landblock window:

```c
// [acclient: 00505370] LScape::LScape
this->land_blocks      = 0;   // (CLandBlock**) — the loaded grid, allocated later
this->loaded_cell_id   = 0;   // the landblock the window is currently centered on
this->viewer_cell_id   = 0;
this->viewer_b_xoff    = 0;   // viewer block offset → drives the floating render origin (§3)
this->viewer_b_yoff    = 0;
this->mid_radius       = 5;   // default load radius in LANDBLOCKS
this->mid_width        = 0xb;  // = 11 = 2*5 + 1
```

The radius/width relationship is fixed by `SetMidRadius`:

```c
// [acclient: 00504C00] LScape::SetMidRadius(radius)
if (radius > 0 && this->land_blocks == NULL) {   // only settable BEFORE allocation
    this->mid_radius = radius;
    this->mid_width  = radius * 2 + 1;            // window side = 2R+1
    return 1;
}
return 0;
```

So `mid_width = 2·mid_radius + 1`, and the radius is an **init-time parameter** —
it can only change while `land_blocks` is unallocated. Changing it at runtime
requires tearing the landscape down and resetting the cell manager:

```c
// [acclient: 00453180] SmartBox::set_mid_radius(radius)
CellManager::Reset(this->cell_manager);
LScape::SetMidRadius(this->lscape, radius);
// ... then re-seat the player position
```

**The grid is exactly `mid_width²` landblocks.** The loader allocates it as one
flat array and walks the whole thing:

```c
// [acclient: 005063A0] LScape::update_block
ppCVar6 = operator_new__(this->mid_width * this->mid_width * 4);  // (2R+1)^2 pointers
this->land_blocks = ppCVar6;
// nested do/while over [0, mid_width) × [0, mid_width), one CLandBlock* per cell;
// out-of-world slots (coord < 0 or > 0x7f7) are left NULL.
```

`update_loadpoint` is the per-move entry point: if the viewer is still inside the
loaded center it does nothing; otherwise it calls `update_block` to shift the
window and load the freshly-exposed edge, releasing blocks that fell outside.
[acclient: 00506CD0 `update_loadpoint`; 005063A0 `update_block`]

`get_landblock` reads the same grid, confirming the indexing and the ±`mid_radius`
acceptance window (viewer sits at the center index `mid_radius`):

```c
// [acclient: 00505E40] LScape::get_landblock — index math (paraphrased)
base = mid_radius * 8;                                   // center, in CELL units (8 cells/block)
col  = (base + (query_x_cell - loaded_x_cell)) >> 3;     // → block offset + mid_radius
row  = (base + (query_y_cell - loaded_y_cell)) >> 3;
if (0 <= col < mid_width && 0 <= row < mid_width)
    return land_blocks[mid_width * col + row];           // else NULL → not loaded
```

A landblock is therefore "loaded" iff its block offset from the center is within
**`[-mid_radius, +mid_radius]`** on both axes — the `(2R+1)²` square.

## 2. The radius IS the user's "Landscape Detail" graphics setting

When the client enters a region it sets the radius straight from render prefs:

```c
// [acclient: 004531F0] SmartBox::SetRegion(region)
CRegionDesc::SetRegion(region);
LScape::ChangeRegion(this->lscape);
set_mid_radius(this, Render::m_RenderPrefs.LandscapeDrawDistance);   // ← the load radius
```

`LandscapeDrawDistance` is a `UIPreferences` enum the user picks in Options →
Graphics (`ID_Graphics_LandscapeDrawDistance`) [acclient: 004035B0
`InitUIPreferences`; 00455C30 `HandleRenderOption`; 0049E400 `InitOptions`]. The
graphics-quality presets write concrete landblock counts into it:

```c
// [acclient: 0054B020] SetOverallGraphicsQuality(tier)
m_RenderPrefs.LandscapeDrawDistance = 3;     // tier 1
m_RenderPrefs.LandscapeDrawDistance = 5;     // tier 2
m_RenderPrefs.LandscapeDrawDistance = 8;     // tier 3
m_RenderPrefs.LandscapeDrawDistance = 0xb;   // 11, tier 4
m_RenderPrefs.LandscapeDrawDistance = 0xf;   // 15, tier 5
```

…and the reverse map reads them back as literal radii (`== 3`, `== 5`, …)
[acclient: 0054B170 `DetermineOverallGraphicsQuality`]. The stored value is the
**landblock radius itself** (3/5/8/11/15), passed unmodified to `SetMidRadius` →
`mid_width = 2R+1`.

**Consequence for the migration:** there is no single "retail load radius." It is a
graphics tunable spanning **3–15 landblocks** (576 m – 2880 m). Use **R = 5 (the
`LScape` default, the lower-middle preset) as the baseline** and expose the WP
loading range as a setting mapped to these tiers (ADR-0009 §2/§6).

## 3. World origin, axes, and the viewer-relative floating render frame

**Axes — `+X East, +Y North` [DATA].** `get_block_orient` maps a block's grid
position (relative to the center) to a compass direction. Reading the cases:
`+x-offset → EAST`, `+y-offset → NORTH`, both-max → `NORTHEAST_OF_VIEWER`:

```c
// [acclient: 00504F90] LScape::get_block_orient(bx, by, ...)
dx = bx - mid_radius;  dy = by - mid_radius;
// dx == +r && dy == +r → NORTHEAST_OF_VIEWER
// dx == +r            → EAST_OF_VIEWER        (so +X = East)
// dy == +r            → NORTH_OF_VIEWER       (so +Y = North)
// ... WEST / SOUTH / SOUTHWEST symmetric; |dx|,|dy| <= 1 → IN_VIEWER_BLOCK
```

**Landblock id encoding + 255/axis [DATA].** `update_block` constructs each block's
data id from its global cell coords:

```c
// [acclient: 005063A0] LScape::update_block
//   id = ((blockX << 8) | blockY) << 16 | 0xffff,  blockX = x_cell>>3, blockY = y_cell>>3
// guard: cells must satisfy 0 <= coord <= 0x7f7  (0x7f7 = 2039 = 255*8 - 1)
```

So the high-16 is `(LbX << 8) | LbY` (high byte = LbX = East, low byte = LbY =
North), the low-16 `0xffff` is the whole-landblock sentinel, and the valid range
is **0..254 → 255 landblocks per axis** (cell coords 0..2039). This matches ACE
`LandDefs` (`block = (x>>3<<8)|(y>>3)`, indices 0..254) — but is read here from the
client.

**Landblock metric size [DATA + DATA].** The client computes
`block_length = square_length * 8.0f` (`0x41000000` = 8.0) [acclient: 006C2CD0 and
siblings, `$E108`/`$E93`/… region-init thunks]. With `square_length = 24 m` from
the committed region export (`pipeline/dat-extract/samples/region_dereth.json`
`land_defs`, [DATA]) that is **block_length = 192 m**, 8 cells of 24 m per side.

**World origin = SW corner of LB(0,0) [DERIVED from the above].** A landblock's
local frame runs `[0, block_length)` on each axis (the client clamps intra-block
coords to `0 ≤ c < block_length` in `within_block`/`obj_within_block`/
`get_land_scenes` [acclient: 0050E800, 00511030, 00530460]) and `+X/+Y` increase
East/North. The block origin (local `(0,0)`) is thus the **min-East, min-North =
south-west corner**, and absolute world `X = LbX·192 + local_x`,
`Y = LbY·192 + local_y`. Therefore world `(0,0,0)` is the **SW corner of landblock
`(LbX=0, LbY=0)`**, `+X` East, `+Y` North, `+Z` up (height above 0). (This is the
same composition ACViewer uses and that the EnvCell census in
[envcell-colocation-findings.md](envcell-colocation-findings.md) already proved for
indoor frames: `world = LbX·192 + Origin.X, LbY·192 + Origin.Y, Origin.Z`.)

**Stored convention is landblock-LOCAL, not global [DATA] (resolves ADR-0010 A1).**
A physics object's position is `(objcell_id, local frame)` —
`CPhysicsObj::m_position.objcell_id` plus an intra-cell offset
[acclient: 00453180 references `player->m_position.objcell_id`]; the wire `Position`
is `uint32 LandblockId + float X/Y/Z + quaternion` (already documented from ACE in
`physics-feel-spec-response.md` §0/§10). World coordinates are **composed** from the
cell id, never stored globally.

**The render frame floats around the viewer [DATA] (direct evidence for ADR-0010's
"exactly one layer rebases" invariant).** `calc_frame` sets each loaded block's
**render** origin relative to the *viewer's* block, not to world (0,0):

```c
// [acclient: 00505460] LScape::calc_frame(block, bx, by)
block_frame.origin.x = (bx - this->viewer_b_xoff) * block_length;   // viewer-relative
block_frame.origin.y = (by - this->viewer_b_yoff) * block_length;
block_frame.origin.z = 0;                                           // no per-block Z offset
```

i.e. the retail client kept float precision across a ~49 km world by **rebasing the
landscape on the viewer's landblock every time the window shifts** — exactly the
"one origin-rebasing layer" UE5 will reproduce with World Partition origin shifting
+ LWC (ADR-0010 invariant; ADR-0009 §6 open question on double-rebasing).

---

## Provenance table

| Fact | Function | Addr |
|---|---|---|
| Default load radius `R=5`, window 11 | `LScape::LScape` | 00505370 |
| `mid_width = 2R+1`; init-time only | `LScape::SetMidRadius` | 00504C00 |
| Radius reset path (resets CellManager) | `SmartBox::set_mid_radius` | 00453180 |
| **Radius = `LandscapeDrawDistance` pref** | `SmartBox::SetRegion` | 004531F0 |
| **Preset radii 3/5/8/11/15** | `SetOverallGraphicsQuality` | 0054B020 |
| Reverse map (`==3`,`==5`,…) | `DetermineOverallGraphicsQuality` | 0054B170 |
| Pref is a UI graphics enum | `InitUIPreferences` | 004035B0 |
| Grid = `(2R+1)²`; shift/load/release | `LScape::update_block` | 005063A0 |
| Per-move load entry point | `LScape::update_loadpoint` | 00506CD0 |
| ±`mid_radius` acceptance, grid index | `LScape::get_landblock` | 00505E40 |
| **Axes: +X East, +Y North** | `LScape::get_block_orient` | 00504F90 |
| **Viewer-relative floating render origin** | `LScape::calc_frame` | 00505460 |
| Edge-of-window draw extents (block_length) | `LScape::draw_check_blocks` | 00505F80 |
| Intra-block local coords `[0, block_length)` | `within_block` / `obj_within_block` | 0050E800 / 00511030 |
| `block_length = square_length * 8.0f` | region-init thunks (`$E108` …) | 006C2CD0 |
| Stored pos = `objcell_id` + local frame | `m_position.objcell_id` use | 00453180 |

## What is NOT claimed (scope discipline — the rest is issue #4)

- **`mid_radius` is the LANDSCAPE/terrain window only.** Dungeon/interior cells are
  loaded by a separate `CellManager` (visible-cell grab/release: `grab_visible_cells`
  0x504EC0, `release_visible_cells` 0x504F50, `PreFetchCells` 0x505660), and dynamic
  *object* visibility is `CObjMaint` — both **out of scope here** and unmeasured.
- **The full §0/§0b coordinate contract** (handedness sign convention, angular unit,
  indoor cell-id domain, portal origin-shift) is **issue #4**. This note fills only
  the **world-origin/axes** row of §0 plus the **load policy** for ADR-0009; the
  handedness *label* (left vs right) is inferred from Z-up + (East,North,Up) and is
  flagged for #4 to confirm against the client's matrix/winding code.
- Heights are **above world Z=0**; whether a given block's terrain sits above/below a
  reference is governed by the LandHeightTable (`region_dereth.json`), not asserted
  per-block here.
- These are read from **static pseudo-C**, not a running client; the numbers are
  consistent across every function that touches them, but no in-situ trace was taken.

## Cross-references / impact

- **ADR-0009** H1 (load radius) → resolved; deep-dive §2 loading-range and §6 step 1
  updated; the open "world origin / Z offset" question answered (SW corner; Z origin 0).
- **ADR-0010** A1 (stored convention = landblock-local) → resolved; the floating
  render origin is direct evidence for the single-rebasing-layer invariant.
- **ADR-0011** A2 (retail draw distance) — *bonus*: `LandscapeDrawDistance ∈ {3..15}`
  landblocks is the retail landscape draw distance. ADR-0011 stays Proposed (its fog
  /horizon treatment, M4, is still [VERIFY]), but the block-count side of A2 now has
  client evidence; see ADR-0009 §4.
- **contract §0** world-origin row filled in
  [`../../../contract/decompile-artifacts/physics-feel-spec-response.md`](../../../contract/decompile-artifacts/physics-feel-spec-response.md).
