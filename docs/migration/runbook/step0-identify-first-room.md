# Runbook - Step 0: identify the first-room cell(s)

Goal: name the exact EnvCell id(s) of the reference screenshot's first room
(`~/repos/ac-screenshots/aluvian training academy first room.png`).

Status: **candidate identified, visual confirmation BLOCKED on Step 1**
(texture identity). See "Outcome" + "What this vetted in the docs".

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
