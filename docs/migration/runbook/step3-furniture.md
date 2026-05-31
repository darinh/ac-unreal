# Runbook - Step 3: furniture / decorations (statics)

Goal: place the room's `Setup`/`GfxObj` props (bookshelf, cabinets, barrel,
rug, wall pieces, fireplace, etc.) at correct positions, textured.

Status: **core done** for the academy - 644 statics placed at corrected
coords, setup meshes built clean, materials bound. Refinement (exact object
orientation/identity audit vs answer key, the fireplace as an emitter) pending.

## Data path
`EnvCell.StaticObjects[]` = `Stab{ Id, Frame }` where `Id` is a `Setup (0x02)`
or `GfxObj (0x01)` and `Frame` is the placement. A `Setup` assembles part
`GfxObj`s by `PlacementFrame` + scale. Textures via the same
`Surface -> SurfaceTexture -> Texture` chain as cells.

## What was wrong (and fixed)
1. **Coordinate doubling** - `DumpAcademyStatics` composed `cellPos +
   RotateAcVec(cellOrient, localPos)`, but `Stab.Frame` is landblock-absolute
   (identical bug + fix as the lights). Fixed to use `stab.Frame` directly.
   Verified: median static->cell-origin distance 4.1 m, 598/644 within 6 m
   (was hundreds of metres).
2. **NaN bounds (earlier purge) = stale state, not the meshes.** Re-exporting
   with the rebuilt `acdat` produced 0/208 setup OBJs with NaN/Inf verts; all
   first-room setups have clean furniture-sized ranges. No bounds hack needed.
3. **UV V-flip** - `import_statics.py` was fixed to use `vv` (matches cells).

## Pipeline (reproducible)
```
acdat dump-academy-statics     <dat> 8602 samples/academy_8602_statics.json   # positions (fixed)
acdat export-academy-statics   <dat> samples/academy_8602_statics.json out/academy_8602_statics  # setup meshes (+mtl,textures)
# UE (headless):
import_statics.py     # build SM_Setup_* meshes + spawn 644 StaticMeshActors at positions
import_materials.py   # bind cell + setup slots to MIs (unlit masters per ADR-0007)
```
Result on `0x860201AD`: textured stone walls + blue floor + rug, barrel,
cabinets, wall pieces placed in the room (render
`pipeline/renders/.../step3_textured_v2.png`), matching the answer-key
academy's furnished look.

## Verify (the "fishing" discipline)
- Positions: recompute each static's distance to its cell origin (should be
  within the cell, not 2x out).
- Identity/orientation: `analyze_surfaces.py` per setup + compare object
  shapes/placement to the answer-key corner views. (Open: a precise per-object
  audit; some objects' rotations not yet confirmed.)

## Known follow-ups
- The red/green diamond placeholders in renders are `import_npcs.py` markers
  (door/scenery/portal/npc/fixture), not statics - addressed in Step 4/5.
- The fireplace is currently static geometry; flames/embers are Step 6.
- A per-object orientation audit vs the answer key is not yet done.
- `DumpAcademyStatics` orientation now uses `stab.Frame.Orientation` directly;
  confirm rotated props read correctly (rotated-cell case).
