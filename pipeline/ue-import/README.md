# pipeline/ue-import — Aluvian Academy assembly pipeline

Headless UE5 Python scripts that consume the extracted JSON + OBJ data
from `pipeline/dat-extract/` and `pipeline/ace-world/` to populate
`/Game/Academy/Maps/AcademyMap` with the full Aluvian Training Academy.

## Run order (one-time setup)

1. **Phase 5e — cell geometry** (568 EnvCell static meshes + spawn actors)

   ```pwsh
   UnrealEditor-Cmd.exe AcUnreal.uproject `
     -run=pythonscript -script="pipeline\ue-import\import_academy.py" `
     -RenderOffScreen -nocrashreports -nop4 -nosplash -stdout
   ```

2. **Phase 5f — props** (the 644 baked-in Stab objects: fireplaces,
   chairs, signs visible at runtime as decorative furniture)

   ```pwsh
   UnrealEditor-Cmd.exe AcUnreal.uproject `
     -run=pythonscript -script="pipeline\ue-import\import_statics.py" `
     -RenderOffScreen -nocrashreports -nop4 -nosplash -stdout
   ```

3. **Phase 5g+5h — lights + fire flicker**

   ```pwsh
   UnrealEditor-Cmd.exe AcUnreal.uproject `
     -run=pythonscript -script="pipeline\ue-import\import_lights.py" `
     -RenderOffScreen -nocrashreports -nop4 -nosplash -stdout
   ```

4. **Phase 5i+5j — NPCs / doors / signs / portals / chests** (the 22
   interactive entities that ACE spawns from `landblock_instance`)

   ```pwsh
   UnrealEditor-Cmd.exe AcUnreal.uproject `
     -run=pythonscript -script="pipeline\ue-import\import_npcs.py" `
     -RenderOffScreen -nocrashreports -nop4 -nosplash -stdout
   ```

Each script is **idempotent** — re-running deletes any actors with the
relevant label prefix before respawning. Safe to iterate.

## Smoke testing

`smoke_import.py` runs `import_academy.py` with `AC_LAYOUT_LIMIT=3` for
a fast 3-cell sanity check before kicking off the 568-cell run.

## Flags that matter

- `-RenderOffScreen` initializes an offscreen Slate app. Required —
  `-nullrhi` is more aggressive but crashes any code path that touches
  the ContentBrowser.
- `-nocrashreports` suppresses the modal crash dialog (also disabled
  project-wide via `Config/DefaultEngine.ini [CrashReportClient]`).
- `-unattended` would normally suppress dialogs but Interchange's
  importer ignores it. Use `-RenderOffScreen` instead.

## Data sources

| Script | Input | Source |
|--------|-------|--------|
| `import_academy.py` | `samples/academy_8602_layout.json` + `out/academy_8602/cell_*.obj` | `acdat dump-academy-layout` + `acdat export-academy` |
| `import_statics.py` | `samples/academy_8602_statics.json` + `out/academy_8602_statics/setup_*.obj` | `acdat dump-academy-statics` + `acdat export-academy-statics` |
| `import_lights.py`  | `samples/academy_8602_lights.json` | `acdat dump-academy-lights` |
| `import_npcs.py`    | `samples/academy_8602_npcs.json` + `out/academy_8602_statics/setup_*.obj` | `pipeline/ace-world/extract_landblock_instances.py` |

## What's in the level

| Folder | Count | Source |
|--------|-------|--------|
| `Academy/Floor_-12m` ... `Floor_+18m` | 568 | Cell prefab meshes |
| `Academy/Props` | 644 | Stab list per EnvCell |
| `Academy/Lights` | 132 | Setup.Lights per Stab |
| `Academy/FireMeshes` | 105 | Visible flame placeholders |
| `Academy/Instances/door` | 7 | Server-spawned doors |
| `Academy/Instances/scenery` | 7 | Sign books |
| `Academy/Instances/fixture` | 6 | Treasure chests |
| `Academy/Instances/portal` | 1 | Central Courtyard portal |
| `Academy/Instances/npc` | 1 | Academy Researcher |
| `Academy/Lighting` | 4 | SkyLight, DirectionalLight, PostProcessVolume, AcAcademyFireManager |

## Materials note

Cell + setup meshes ship without bound materials (slot names are
preserved as e.g. `surf_0`, `part00_surf3`, but `material_interface`
is `None`). UE falls back to `WorldGridMaterial` so the gray geometry
is visible immediately. A future `assign_materials.py` will populate
slots from the per-cell `.mtl` files and per-setup textures in
`pipeline/dat-extract/out/academy_8602/textures/`. Doing materials at
the same time as geometry import crashed Slate; deferred to a separate
interactive-Editor pass.

## What this is *not*

- No player interactivity wired up. Double-clicking a sign / NPC does
  nothing. That requires Phase 6 (Turbine UDP protocol + ACE server
  connection) + Phase 7 (input → Use packet → server response).
- No NPC animations. Bodies render in T-pose; AC MotionTables not yet
  consumed.
- No HUD / UMG widgets.

See `contract/physics-feel-spec-request.md` and the project README for
the larger-picture phase plan.
