# Finding: EnvCell ↔ landblock co-location is type-dependent (RESOLVED)

**Status:** ACCEPTED — user sign-off 2026-05-31. Empirical result, [PRELIMINARY] only
where explicitly noted in §6.
**Owner question (the #1 gating assumption of [ADR-0009](../decisions/0009-world-streaming-landblock-world-partition.md)):**
do an indoor `EnvCell`'s world coordinates fall inside the XY footprint of the landblock
whose ID addresses it — i.e. will UE World Partition stream a dungeon/building interior with
the same grid cell as its parent landblock?

**Why this note exists:** this was researched, mis-concluded (twice), then corrected and
widened under adversarial multi-model review. This note is the durable record **so it is never
re-derived**. Every retail-client/DAT claim below carries a provenance tag and a citation that
*literally* states it (tags per `feature-disposition-and-design-gaps.md` §anti-hallucination:
`[DATA]` = from DAT/extractor/committed artifact; `[REF-IMPL]` = ACE/ACViewer source).

---

## 1. Decision (what we now rely on)

1. **Compose every EnvCell to world coordinates with the proven formula** (§3); never assume an
   EnvCell sits inside its addressing landblock's footprint **without checking the category**.
2. **Co-location is type-dependent** (§5):
   - **Building-interior** landblocks (`LandblockInfo.Buildings > 0`): EnvCells **are** co-located
     — every cell falls inside the `[0,192]²` footprint (8/8 sampled blocks, 882/882 cells).
   - **Zero-building** landblocks (`LandblockInfo.Buildings == 0`): EnvCells are **mostly NOT**
     co-located — the large majority fall outside the footprint (3/3 sampled blocks, 2200/2259
     cells out, into negative-Y).
3. **Design impact** ([ADR-0009](../decisions/0009-world-streaming-landblock-world-partition.md) §3,
   carried here): a UE **Data Layer keyed by addressing landblock** organizes interiors, but for
   zero-building blocks it does **not** predict which World Partition cell streams them — WP
   auto-assignment by world location lands them in a *different* grid cell. ADR-0010 (coords) and
   ADR-0013 (culling) must handle interiors that cross block boundaries.

---

## 2. Background: what an EnvCell is

- An `EnvCell` is "mostly dungeons, but can also be a building interior."
  `[REF-IMPL: ACE.DatLoader FileTypes/EnvCell.cs:11]`
- A landblock's `LandblockInfo` (Cell-DAT file `0xXXXXFFFE`) carries its `Buildings` list and
  `NumCells` (count of indoor EnvCells). `[DATA: acdat landblock-info / find-building-blocks]`
- ACViewer flags a landblock `IsDungeon` when **all terrain heights are 0 AND it has EnvCells AND
  it has zero buildings.** `[REF-IMPL: ACViewer Physics/Common/Landblock.cs:592-604]`
  We measured only the **zero-building** half of that predicate, so this note says **"zero-building,"
  never "dungeon"** — zero-building is *necessary but not sufficient* for `IsDungeon`. (The project's
  "academy" block `0x8602` is zero-building.)

---

## 3. PROOF A — how an EnvCell is placed in the world

**Formula (proven):**
```
world = (LbX*192 + Frame.Origin.X,  LbY*192 + Frame.Origin.Y,  Frame.Origin.Z)
```
where `LbX/LbY` are the high bytes of the cell ID and **Z gets no terrain offset** (the Z
translation is 0, modulo a +0.05 z-fight nudge). The frame stored in the EnvCell is therefore
**landblock-local**, and a frame outside `[0,192]` simply renders in a *different* world block.

Citations (all verified by reading the exact lines):
- `[REF-IMPL: ACViewer Extensions/PositionExtensions.cs:22-29]` — `GetWorldPos()` returns
  `(LbX*BlockLength + Frame.Origin.X, LbY*BlockLength + Frame.Origin.Y, Frame.Origin.Z)`.
- `[REF-IMPL: ACViewer Render/R_Landblock.cs:51-56 (AddEnvCells), Render/Buffer.cs:340-344,
  Render/InstanceBatch.cs:98-105]` — the **batched world renderer** places each EnvCell instance at
  `origin = EnvCell.Pos.GetWorldPos()`. (The unbatched model-viewer path
  `PositionExtensions.ToXna:9-20` / `R_EnvCell.cs:47-49,78` composes identically.)
- `[REF-IMPL: ACViewer Physics/Common/LandDefs.cs:102]` — `BlockLength = 192`.
- `[REF-IMPL: ACE.Entity Position.cs:123]` — the `Position.SetLandblock` block-offset
  normalization does **not** apply to indoor cells: `if (Indoors) return false;` (early return).
- `[REF-IMPL: ACViewer Render/R_Landblock.cs:90-100]` — the world renderer walks exactly
  `Info.NumCells` cells from `0x100` (`envCellID = landblockID | (0x100 + i)`), so `NumCells` is
  the rendered subset (relevant where a block has more EnvCell *files* than `NumCells`; see §5 note).

---

## 4. PROOF B — census method & tooling (fully reproducible)

Two single-process `acdat` commands (open the DATs once; the footprint test is computed in C#)
make this auditable end-to-end. `[DATA]`

- **`acdat find-building-blocks <datDir>`** — scans **every** `LandblockInfo` (Cell-DAT file
  key low-16 == `0xFFFE`) and lists landblocks with `Buildings > 0`. Result on DAT iteration 982:
  **1639 of 5346** landblocks have buildings. Source: `pipeline/dat-extract/Program.cs`
  (`FindBuildingBlocks`).
- **`acdat dump-envcell-positions <datDir> <hexId>`** — full per-block census: enumerates the
  **real** EnvCell file keys `0x0100..0xFFFD` (not a probe, not a first-N slice), prints each
  cell's local `Frame.Origin`, the composed world position, and whether `Frame.Origin.X,Y` are in
  `[0,192]`; plus bbox and IN/OUT totals. Source: `pipeline/dat-extract/Program.cs`
  (`DumpEnvCellPositions`). **Validated** to reproduce the earlier slow per-cell census exactly
  (e.g. `0xA9B4` 138/138, `0xC6A9` 205/205).

**Sample selection:** the 8 building-interior blocks were drawn from `find-building-blocks` output
across the building-count range (1..49 buildings) and 2..251 EnvCell files per block. This is **not**
the full population — `Buildings>0` blocks reach `NumCells ~2468` (e.g. `0x200F`), which the sample
does not cover (see §6). The 3 zero-building blocks are carried from the original census.

**Auditable raw artifact (every cell row):**
`pipeline/dat-extract/samples/envcell_position_census.txt` — regenerate with the sibling
`envcell_position_census.ps1`. `[DATA]`

---

## 5. PROOF C — results (full census, DAT iteration 982)

`Category` = building-interior (`Buildings>0`) vs zero-building (`Buildings==0`). bbox values are the
exact two-decimal strings from the committed `.txt` summary lines.

| Landblock | LbX,LbY | Buildings | Category | Frame.Origin bbox (X / Y / Z) | Cells in `[0,192]²` |
|---|---|---|---|---|---|
| `0x1203` | 18,3 | 49 | building interior | X[12.00..156.00] Y[12.00..156.00] Z[0.00..0.00] | **182 / 182 IN** |
| `0xDA55` | 218,85 | 42 | building interior | X[9.12..188.40] Y[3.96..186.58] Z[20.00..20.04] | **251 / 251 IN** |
| `0x8851` | 136,81 | 38 | building interior | X[12.00..180.00] Y[12.00..180.00] Z[0.00..30.00] | **76 / 76 IN** |
| `0xC6A9` | 198,169 | 30 | building interior | X[12.00..132.00] Y[12.00..108.00] Z[42.00..42.00] | **205 / 205 IN** |
| `0xA9B4` (Holtburg) | 169,180 | 12 | building interior | X[31.50..161.93] Y[7.50..159.50] Z[66.00..94.00] | **138 / 138 IN** |
| `0x0503` | 5,3 | 3 | building interior | X[84.00..132.00] Y[36.00..36.00] Z[150.00..225.00] | **21 / 21 IN** |
| `0x0408` | 4,8 | 1 | building interior | X[108.02..108.02] Y[132.29..132.29] Z[87.19..87.19] | **7 / 7 IN** |
| `0x0604` | 6,4 | 1 | building interior | X[60.00..60.00] Y[108.00..108.00] Z[22.00..22.00] | **2 / 2 IN** |
| `0x8602` (academy) | 134,2 | 0 | zero-building | X[0.00..210.00] Y[-250.00..0.00] Z[-12.00..18.00] | 36 IN / **532 OUT** |
| `0x01AE` | 1,174 | 0 | zero-building | X[0.00..180.00] Y[-140.00..0.00] Z[-36.00..24.00] | 11 IN / **734 OUT** |
| `0x00D6` | 0,214 | 0 | zero-building | X[0.00..120.00] Y[-340.00..0.00] Z[-6.00..96.00] | 12 IN / **934 OUT** |

**Totals:** building interiors **882 / 882 IN (100%)** (`138+182+251+76+205+21+7+2`);
zero-building **2200 / 2259 OUT (97.4%)** (`532+734+934` out of `568+745+946`).

**Note on file-count vs `NumCells`:** two building blocks have more EnvCell *files* than
`LandblockInfo.NumCells` (`0xA9B4` 138 vs 123; `0xDA55` 251 vs 236). `NumCells` is the subset the
world renderer walks `[REF-IMPL: ACViewer Render/R_Landblock.cs:90-100]`; since **all** files in those
blocks are in-footprint, the rendered subset is too.

---

## 6. Scope: proven vs still [PRELIMINARY]

**Proven (cited above, reproducible):**
- The placement formula and that Z carries no terrain offset (§3).
- For the **11 sampled blocks**, the type-dependent co-location split (§5).

**Still [PRELIMINARY] — do NOT over-generalize:**
- The building-interior co-location result is **broadly sampled (n=8, all cells)** but **not proven
  for all 1639 building blocks**, especially the high-`NumCells` ones (up to ~2468) the sample omits.
- Only the **zero-building** half of ACViewer's `IsDungeon` was measured; the **all-heights-0** half
  is unverified per block, so no row is asserted to be a "dungeon."
- The raw frame **Z range is wide** (e.g. `0x00D6` Z[-6..96]); whether any Z sits **above or below
  ground is UNMEASURED** (needs the landblock height table) and is **not** claimed.

To strengthen later: widen the building-interior census (add high-`NumCells` blocks), and measure
heights-0 to promote "zero-building" → "dungeon."

---

## 7. Reproduce

```powershell
$exe = "pipeline\dat-extract\bin\Release\net8.0-windows\acdat.exe"
$dat = "C:\Turbine\Asheron's Call"

# 1. find building-interior candidates (Buildings>0)
& $exe find-building-blocks $dat

# 2. full census for one block (per-cell rows + bbox + IN/OUT)
& $exe dump-envcell-positions $dat A9B4

# 3. regenerate the committed 11-block artifact
pipeline\dat-extract\samples\envcell_position_census.ps1
```

---

## 8. Provenance of this finding (how it was hardened)

- Initial empirical attempt **mis-concluded** ("co-location refuted") by conflating zero-building
  dungeons with building interiors and citing the wrong source lines.
- Corrected under **ruthless multi-model adversarial review** (Claude Sonnet 4.6, GPT-5.3-Codex,
  MAI-Code, Opus/rubber-duck): wrong citations replaced and verified, biased first-N sample replaced
  with a full per-block census.
- Independently re-verified by **two model families** (GPT-5.5, GPT-5.3-Codex), which reproduced the
  census exactly and confirmed every citation.
- **Widened** (this note's n=8 building sample) and reviewed again (rubber-duck) before user sign-off.
- Commits on `worktree-design-gap-analysis`: `ce20ed1` → `a8c85e2` (corrective) → `4cf836e`
  (refinement) → `d2d98a3` (widening).
