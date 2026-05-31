# =====================================================================
# fix_mesh_bounds.py
#
# THE BUG: every procedurally-built StaticMesh under /Game/Academy/Cells
# (and most under /Game/Academy/Setups) has box_extent=(0,0,0) and
# sphere_radius=0. UE then frustum-culls them as if they were
# zero-sized points — so the entire academy is invisible at runtime
# unless you happen to be standing ON the (0,0,0)-extent point.
#
# Root cause: `build_from_static_mesh_descriptions([desc])` in our
# import_academy.py + import_statics.py + import_npcs.py pipeline
# didn't compute proper bounds. UE's procedural build path doesn't
# auto-derive bounds from vertex positions the way the FBX importer
# does.
#
# Symptoms confirmed:
#   - SM_860201AD (spawn cell, 26 tris, 78 verts): box_extent (0,0,0)
#   - SM_86020100 (corridor, 22 tris): box_extent (0,0,0)
#   - SM_Setup_0200007C (chest, 60 tris): box_extent (0, 1.09e25, 0) — bogus
#   - SM_Setup_02000001 (NPC body, 417 tris): origin = NaN-ish floats
#
# The chest + NPC body actually render in the game because their
# bogus huge bounds happen to always be in the camera frustum. Cells
# get culled because (0,0,0) bounds are never in the frustum unless
# the camera is exactly at the cell origin.
#
# FIX: for each StaticMesh under /Game/Academy/, call
# `set_positive_bounds_extension` and `set_negative_bounds_extension`
# to force a generous bounding box. We don't need pixel-perfect bounds
# — just non-zero ones large enough that UE won't cull the mesh.
# Cells are at most 10m × 10m × 6m so ±10m extension is safe.
# Setup meshes (props, NPC bodies, doors) are much smaller; the same
# ±10m extension is wasteful but harmless (slightly worse occlusion
# culling, negligible perf cost for 776 meshes).
#
# This is a band-aid. The proper fix is to rebuild every mesh with
# `recompute_bounds_extension` after the
# build_from_static_mesh_descriptions call in the importers — but
# that requires re-running import_academy/statics/npcs and re-binding
# all 1967 material slots. The band-aid takes ~10s and works on the
# existing assets.
# =====================================================================

import unreal
import sys


def log(m): unreal.log(f"[fixbnd] {m}")


# Modest bounds extension. Smaller than cells (cells are at most 10m =
# 1000cm), so this gives just enough margin to prevent zero-bounds
# frustum culling without overlapping huge boxes that the HZB/occlusion
# system would use to cull each other.
BOUNDS_EXT = unreal.Vector(800.0, 800.0, 800.0)


def fix_mesh(asset_path: str) -> bool:
    if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        return False
    sm = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not isinstance(sm, unreal.StaticMesh):
        return False
    # Bounds extension is exposed in UE 5.7 as editor properties, not
    # via dedicated setters. set_editor_property forces dirty-marking too.
    sm.set_editor_property("positive_bounds_extension", BOUNDS_EXT)
    sm.set_editor_property("negative_bounds_extension", BOUNDS_EXT)
    return True


def main():
    # Walk both academy mesh trees.
    paths = []
    for root in ("/Game/Academy/Cells", "/Game/Academy/Setups"):
        listing = unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False)
        log(f"  {root}: {len(listing)} assets")
        paths.extend(listing)

    fixed = 0
    failed = 0
    for i, p in enumerate(paths):
        # list_assets returns paths like "/Game/Academy/Cells/SM_860201AD.SM_860201AD"
        clean = p.split(".")[0]
        ok = fix_mesh(clean)
        if ok:
            fixed += 1
        else:
            failed += 1
        if (i + 1) % 100 == 0:
            log(f"  progress: {i+1}/{len(paths)} fixed={fixed} failed={failed}")

    log(f"DONE. fixed={fixed} failed={failed}")

    # Save the dirty assets in batch.
    unreal.EditorAssetLibrary.save_directory("/Game/Academy/Cells", recursive=True)
    unreal.EditorAssetLibrary.save_directory("/Game/Academy/Setups", recursive=True)
    log("saved /Game/Academy/Cells + /Game/Academy/Setups")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
