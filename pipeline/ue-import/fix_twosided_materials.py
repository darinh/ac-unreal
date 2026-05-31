# =====================================================================
# fix_twosided_materials.py
#
# Diagnosis: walls are invisible from inside cells because the
# chirality-flip compensation in the OBJ exporter (Phase 5c) gave
# walls outward-facing normals when they should be inward-facing.
# Props render fine (you view them from the outside; backface culling
# behaves normally) but cells appear pitch-black from inside.
#
# Quick fix: enable two_sided=True on both master materials. UE
# renders both sides of every triangle, so wall normals don't matter.
#
# Proper fix later: re-flip the cell-OBJ triangle winding so wall
# normals point INWARD (the player view direction inside a room).
# Until that re-extraction lands, two-sided rendering is the path.
# Performance cost is minimal at this poly count (~1500 actors with
# ~5000 polys each = 7.5M tris doubled = 15M, still very manageable).
# =====================================================================

import sys
import unreal


def log(m): unreal.log(f"[twoside] {m}")


def main():
    for mat_path in ("/Game/Academy/Materials/M_AcademyBase",
                     "/Game/Academy/Materials/M_AcademyColor"):
        if not unreal.EditorAssetLibrary.does_asset_exist(mat_path):
            log(f"  SKIP: {mat_path} doesn't exist")
            continue
        mat = unreal.EditorAssetLibrary.load_asset(mat_path)
        if mat is None:
            continue
        try:
            mat.set_editor_property("two_sided", True)
            unreal.EditorAssetLibrary.save_asset(mat_path)
            log(f"  set two_sided=True on {mat_path}")
        except Exception as e:
            unreal.log_error(f"  FAILED on {mat_path}: {e}")
    log("DONE.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
