# =====================================================================
# debug_black_walls.py
#
# Hypothesis: cell walls are invisible because the dominant surface
# (surf_2 in the spawn cell, MI_Color_000000) renders as pure black,
# which is indistinguishable from the unlit-fallback background.
#
# Real AC probably modulates these "base" surfaces with per-vertex
# lighting or an environment map we never extracted. The 0xFF000000
# we read from Surface.ColorValue is the AC "use vertex color / env
# texture, not the constant" sentinel.
#
# Debug move: paint MI_Color_000000 a clearly-visible debug grey.
# If walls become visible after this, the diagnosis is confirmed
# and the proper fix is to either:
#   (a) Detect 0xFF000000 in the extractor and emit a sensible
#       default (light grey) instead of black.
#   (b) Extract and apply AC's per-vertex lighting (SWVertex.Color
#       field — we skipped it in Phase 5b).
#   (c) Map these surfaces to a different master material that
#       samples an environment cube.
# =====================================================================

import sys
import unreal


def log(m): unreal.log(f"[blackwalls] {m}")


MI_BLACK = "/Game/Academy/Materials/MI_Color_000000"
DEBUG_COLOR = unreal.LinearColor(0.6, 0.5, 0.45, 1.0)  # warm stone grey


def main():
    if not unreal.EditorAssetLibrary.does_asset_exist(MI_BLACK):
        log(f"  MISSING: {MI_BLACK}")
        return 1
    mi = unreal.EditorAssetLibrary.load_asset(MI_BLACK)
    mel = unreal.MaterialEditingLibrary
    mel.set_material_instance_vector_parameter_value(
        mi, unreal.Name("BaseColor"), DEBUG_COLOR)
    unreal.EditorAssetLibrary.save_asset(MI_BLACK)
    log(f"  painted {MI_BLACK} -> warm stone grey ({DEBUG_COLOR.r:.2f}, {DEBUG_COLOR.g:.2f}, {DEBUG_COLOR.b:.2f})")
    log("DONE. Reopen the academy — if walls appear, hypothesis confirmed.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
