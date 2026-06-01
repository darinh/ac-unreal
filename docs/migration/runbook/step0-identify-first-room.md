# Runbook - Step 0: identify the first-room cell(s)

Goal: name the exact EnvCell id(s) of the reference screenshot's first room
(`~/repos/ac-screenshots/aluvian training academy first room.png`).

Status: **CONFIRMED + coexistence PROVEN** (2026-06-01, user sign-off). The
room shell (walls + floor + ceiling) renders correctly *together* from a fixed
6-view sweep that passes `test_renders.py --manifest`. The earlier "BLOCKED on
Step 1 (texture identity)" status is **resolved** — see "Coexistence proof"
below. The old blocking notes are kept for history but are superseded.

## Reference signature (read off the screenshot)
- Floor: blue-grey stone tile.
- Walls: grey-blue **masonry blocks** (large rectangular, mortar lines).
- One fireplace/brazier (warm light), low on a wall.
- Furniture: bookshelf with books, wooden cabinets/desk; a green **urn** on the right.
- A wooden door / tan-stone arch in the back wall.
- The pink-robed figure is the **player**; the green object is an urn.
  **There is no NPC in this screenshot** (corrects an early wrong assumption -
  the academy's single `npc`-category entity is in `0x86020278`, an unrelated
  brown-dirt-walled cell).

## Method that actually works (data-driven, cheap)
Match the reference's distinctive **textures + fixtures**, do not assume "the
spawn cell". Steps:
1. Floor texture is `06003C9A` (blue-grey stone). Find cells whose `.mtl`
   references it: `grep -l 06003C9A out/academy_8602/cell_*.mtl` -> 174 cells.
2. Narrow by fixtures: a **warm fire light** (`is_warm_for_fire_fx` in the
   lights JSON) + high **furniture density** (statics-per-cell from the
   statics JSON). Rank the floor-cells by `(warm_lights, statics)`.
3. Top candidates: `0x860201AD` (pos UE -3000,1000,0; 2 fire lights; 30
   statics; documented "spawn cell"; textures `06003C9A`+`06003C9C`),
   `0x860201B6` (pos -4000,2000,0; 4 fire lights; 29 statics; same textures).

## Coexistence proof (2026-06-01, Step 0/1 — PROVEN, user sign-off)
The room SHELL renders correctly **together** (walls + floor + ceiling in one
coherent set), not just from a lucky single angle. Proven by the fixed-camera
sweep + manifest formula, so it is re-runnable and regression-guarded.

- **Tooling:** `pipeline/ue-import/render_firstroom_sweep.ps1` renders 6 fixed
  cameras from the room center (UE world -3000,1000,250): `wall_n/e/s/w`
  (yaw 0/90/180/270, pitch 0), `ceiling` (pitch +75), `floor` (pitch -75) into
  one timestamped folder. `test_renders.py --manifest <dir>` then REQUIRES all
  6 present AND each to pass the absolute checks (mean_lum 15–245,
  content_frac ≥0.45, magenta ≤0.015, color_std ≥14) + a sky-leak gate
  (sky_frac ≤0.30). A single cherry-picked angle cannot pass this.
- **Evidence dir:** `pipeline/renders/firstroom_sweep_20260601_080757/`
  (6 PNGs, 0.8–1.2 MB each — none are the 17709-byte pure-black signature).
- **Result:** `MANIFEST PASS (room shell coexists)`, exit 0. Per-view metrics:

  | view | mean | content | sky | result |
  |------|------|---------|-----|--------|
  | wall_n | 46.3 | 0.927 | 0.000 | PASS |
  | wall_e | 70.8 | 0.964 | 0.001 | PASS |
  | wall_s | 43.7 | 0.906 | 0.001 | PASS |
  | wall_w | 54.2 | 0.947 | 0.000 | PASS |
  | ceiling | 22.0 | 0.623 | 0.000 | PASS |
  | floor | 43.8 | 0.936 | 0.033 | PASS |

- **Visual match vs answer key** (`~/repos/ac-screenshots/aluvian training
  academy - 01 - *.png`): tan plaster walls + grey stone-brick base band,
  green mossy-stone fireplace with glowing embers, blue-grey stone-tile floor,
  wood-beam ceiling seen through the `NoPos` portal to the adjacent cell
  (`0x...02E2`, ADR-0008). Max sky_frac 0.033 ≪ 0.30 — the "blue sky through
  gaps" problem is gone.
- **Out of scope (Step 3):** untextured furniture statics (white blobs, cones,
  floating swords) appear but issue #1 covers the SHELL only.
- **Repro:**
  ```
  pwsh pipeline/ue-import/render_firstroom_sweep.ps1 -ResX 1280 -ResY 720
  python pipeline/ue-import/test_renders.py --manifest pipeline/renders/firstroom_sweep_20260601_080757
  ```

## Outcome
- **Primary candidate: `0x860201AD`** - documented spawn cell, has the
  reference's floor texture, is heavily furnished, and renders cleanly.
- **Alternate: `0x860201B6`** - more fireplaces but currently renders with a
  magenta error-material on a surface (a binding fault to fix).
- **Not yet 100% confirmed**, because: the candidate walls render **brown**
  (`06003C9C` = brown rock with a stone-brick base band) while the reference
  walls are **grey-blue masonry blocks**. `06003C9A` (the blue-grey blocks)
  appears to map to the *floor* in the current import, not the walls. Until
  the surface->texture/UV assignment is correct (Step 1), the room cannot be
  visually matched to the reference.

## What this vetted in the docs (corrections applied)
1. Step 0 is **coupled to Step 1**: "identify the room" cannot be fully
   confirmed while textures render with the wrong identity. README §3 now tags
   the dependency and the milestone notes the coupling.
2. The "spawn cell `0x860201AD` candidate / NPC" framing was insufficient and
   partly wrong (no NPC in the shot). Replaced with the texture+fixture method.
3. **Texture-identity is a confirmed, blocking defect**, not a footnote: the
   per-polygon `PosUVIndices` gap and/or the surface->texture resolution puts
   the wrong texture on the wrong face. Promoted in methodology §5 and README.
4. New finding: some cells (e.g. `0x860201B6`) render a **magenta error
   material** - a MaterialInstance binding fault to track.
5. Furniture is purged from the level (NaN bounds, earlier session), so the
   room cannot be matched by furniture layout until Step 3 re-imports props.

## Next action
Do Step 1 (texture identity: honor `PosUVIndices`, verify each surf's
texture against source) on the primary candidate `0x860201AD`, then re-render
and confirm walls/floor match the reference. If they do, Step 0 is closed; if
not, escalate to a per-surface render sweep of the `06003C9A`+fireplace cells.

## Commands used (reproducible)
```
# floor-texture cells
grep -l 06003C9A pipeline/dat-extract/out/academy_8602/cell_*.mtl
# rank by warm lights + statics: see the Python in the session / methodology §5
# render a candidate interior:
pwsh pipeline/ue-import/render_academy.ps1 -Name s0 -X -3000 -Y 1000 -Z 250 -Yaw 0
```
