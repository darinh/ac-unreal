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

## 2026-06-01 - Prop UV mapping fixed (per-corner PosUVIndices), user sign-off
Symptom: prop/furniture textures rendered stretched / sometimes reversed; the
framed map-of-Dereth collapsed to a flat "plaster" smear.

Root cause: the prop exporter `ExportSetup` (Program.cs) emitted one `vt` per
vertex from `UVs[0]` and wrote faces `v/v/v`, ignoring per-corner
`poly.PosUVIndices`. Same bug already fixed in `ExportEnvCell` (cells).

Fix:
1. `ExportSetup` now emits one `vt` per (vertex,UV) and indexes faces `p/t/n`,
   selecting `PosUVIndices[corner]` (fallback UV 0); winding swap preserved.
   acdat rebuilt clean.
2. The canonical prop OBJs already carried the fix, so the visible defect was
   stale UE meshes. Rebuilt the 135 stale `SM_Setup_*` meshes in place from the
   current OBJs (those with split UVs, `vt>v`), preserving material bindings, via
   the same delete+recreate mechanism proven on the 430-cell portal fix. The 65
   props with no UV splits (`vt==v`) were left untouched (regression-safe).

Verify:
- `render_firstroom_sweep.ps1` + `test_renders.py --manifest` => MANIFEST PASS
  (shell intact; `AcademyMap.umap` untouched).
- First-room wall renders match the answer key: map-of-Dereth legible +
  gold-framed, red tapestry's full ornate pattern, bookshelves/fireplace/urns/
  helmets/candlesticks correctly textured; no stretching/reversal.

Scope: 135 `Content/Academy/Setups/*.uasset` + `Program.cs`. Adversarially
reviewed (rubber-duck); delete+recreate metadata-loss risk closed by parity with
the original `build_setup_mesh` import path (which set no collision/Nanite/LOD
either) plus material preservation.

Open: `ExportNpc` has the same unfixed bug (Step 4); the 65 `vt==v` props'
uniform-non-zero-UV-index edge case is an unmeasured follow-up (not a regression).

## 2026-06-01 - Setup placement-frame fallback fixed (Resting->Default), user sign-off
Symptom: the academy cave door (`SM_Setup_020005DA`) rendered as a garbled
overlapping cross of a stone post + wood panel, not a door; several furniture
statics were also collapsed onto a single point.

Root cause: `ExportSetup` (Program.cs) read only the Resting (`0x65`) placement
frame. Multi-part setups that ship ONLY a Default (`0x00`) frame got a null
frame, so no per-part transform was applied and every part collapsed onto the
setup origin (parts sharing a GfxObj - e.g. the door's mirrored left/right
jambs - became coincident). Confirmed against ACViewer (`Model/Setup.cs`) and
ACE (`Physics/PartArray.SetPlacementFrame`), whose assembly order is
Resting -> Default -> null.

Fix:
1. `ExportSetup` now prefers Resting (`0x65`), then falls back to Default
   (`0x00`), then null - matching ACViewer/ACE. acdat rebuilt clean. Added a
   read-only `dump-setup <datDir> <hexId>` diagnostic (parts, scales, all
   PlacementFrames keys + per-part origin/orientation) used to derive the
   reference.
2. The fix only moves vertex POSITIONS; topology (parts/tris/slots/materials)
   is unchanged. Affected setups were found in TWO source sets (an adversarial
   review caught that re-exporting the statics alone was incomplete - the door
   is interactive, not a static):
   - Statics: re-exporting the 200 `academy_8602_statics` setups changed 12 -
     the cave door `020005DA` + 11 furniture.
   - Interactive: auditing every setup id in `instances_8602.json` /
     `academy_8602_npcs.json` with `dump-setup` found 8 ids; 7 lack Resting and
     so were re-placed by the fix (only `0200062E` has `0x65` and is unchanged).
     Six besides the cave door were stale/collapsed in committed content:
     `02000001 0200007C 020001B3 0200024F 020005F1 020005F2`. (`020005F1` is the
     practice-area door, `020005F2` the academy portal - both were 800-cubes.)
   Rebuilt all 18 `SM_Setup_*` meshes in place from the fixed OBJs, preserving
   material bindings, via the delete+recreate mechanism proven on the prop-UV fix
   (`_doorfix_rebuild.py` / `_furniturefix_rebuild.py`, the latter now driven by
   an `AC_FIX_SETUPS` id list for reuse). 18/18 verified CLEAN (tris/verts
   identical; bounds now match the fixed OBJ instead of the old collapsed
   800-cube placeholder).

Verify:
- `render_firstroom_sweep.ps1` + `test_renders.py --manifest` => MANIFEST PASS
  (shell intact; `AcademyMap.umap` untouched).
- Isolated renders confirm coherent geometry: the cave door (`020005DA`), the
  practice-area door (`020005F1`, stone jambs + studs + lintel + leaf) and the
  portal (`020005F2`, stone frame around a green vortex); first-room render shows
  the forge, water barrel, torch stand and hanging sign correctly placed.

Scope: 18 `Content/Academy/Setups/*.uasset` + `Program.cs`. Static set:
`0200009E 02000322 02000341 02000384 020003B4 020003B5 020003F9 02000BBD
02000F45 02001149 02001255`. Interactive set: `020005DA 02000001 0200007C
020001B3 0200024F 020005F1 020005F2`. Adversarially reviewed (Sonnet code-review
+ GPT-5.3/GPT-5.5 rubber-ducks); the GPT-5.5 pass caught the incomplete
interactive coverage, which this audit then closed.

Open: `ExportNpc` already has the Resting->Default fallback but still carries
the `UVs[0]` per-corner UV bug (Step 4, tracked).
