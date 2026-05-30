# =====================================================================
# move_player_start.py    -- ⚠️ DANGER — DO NOT USE ⚠️
#
# CATASTROPHIC BUG: in a headless `-run=pythonscript` commandlet the
# editor world does NOT auto-load World Partition / External Actor
# files. `load_level()` brings in the .umap stub (132 bytes) but
# leaves the ExternalActors/ uassets on disk unloaded. The subsequent
# `save_current_level()` then writes back ONLY the few actors that
# were loaded, deleting the External Actor files for everything that
# wasn't in memory.
#
# Symptom: 1487 academy actors silently vanish from
# Content/Academy/Maps/__ExternalActors__/AcademyMap/.../*.uasset.
# Since those files were never committed to git (only the umap stub
# was), the loss is unrecoverable except by re-running every spawn
# script (import_academy.py, import_statics.py, import_lights.py,
# import_npcs.py, restore_lighting.py, add_sky_atmosphere.py,
# brighten_academy.py).
#
# Hit this once on 2026-05-30 mid-render-iteration. Hours of work lost.
#
# Safe replacements for "move where the screenshot is taken from":
#   1. Add a C++ AAcAcademyRenderRig actor that on BeginPlay sets the
#      player camera through a list of viewpoints + HighResShots each.
#      Multi-shot per -game launch. No level mutation needed.
#   2. Add a cheat-manager `teleport X Y Z` console command, then chain
#      it via -ExecCmds before HighResShot.
#   3. Spawn multiple PlayerStarts with PlayerStartTags and pick via
#      -ExecCmds=Open AcademyMap?PlayerStartTag=foo before HighResShot.
#
# All three keep the level itself read-only at runtime.
# =====================================================================

import sys
import unreal

unreal.log_error(
    "move_player_start.py is DISABLED. It silently wipes the level "
    "in commandlet mode (World Partition + save_current_level). "
    "See the file header for safe alternatives.")
sys.exit(99)
