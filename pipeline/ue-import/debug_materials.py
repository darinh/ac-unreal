# =====================================================================
# debug_materials.py
#
# AcademyMap loads but interior walls are invisible despite materials
# being set, two-sided enabled, lights at 25000 intensity, exposure
# manually held bright, and props in the same cells rendering fine
# with their textures visible.
#
# Diagnostic + remediation:
#   1. Inspect M_AcademyBase: is two_sided actually True? Does it
#      have valid expressions wired to BaseColor?
#   2. List the slot bindings on a representative cell. Is its slot
#      pointing at an MI? Is the MI pointing at M_AcademyBase?
#   3. Call recompile_material on both masters.
# =====================================================================

import sys
import unreal


def log(m): unreal.log(f"[debugmat] {m}")


MASTERS = ("/Game/Academy/Materials/M_AcademyBase",
           "/Game/Academy/Materials/M_AcademyColor")
SAMPLE_CELL = "/Game/Academy/Cells/SM_860201AD"


def main():
    # 1) Master material inspection.
    for mp in MASTERS:
        if not unreal.EditorAssetLibrary.does_asset_exist(mp):
            log(f"  MISSING: {mp}")
            continue
        m = unreal.EditorAssetLibrary.load_asset(mp)
        ts = m.get_editor_property("two_sided")
        bm = m.get_editor_property("blend_mode")
        sm = m.get_editor_property("shading_model")
        log(f"  {mp}: two_sided={ts}, blend_mode={bm}, shading_model={sm}")

    # 2) Sample cell slot inspection.
    if unreal.EditorAssetLibrary.does_asset_exist(SAMPLE_CELL):
        sm = unreal.EditorAssetLibrary.load_asset(SAMPLE_CELL)
        slots = sm.get_editor_property("static_materials") or []
        log(f"  {SAMPLE_CELL}: {len(slots)} material slot(s)")
        for i, s in enumerate(slots):
            mi = s.material_interface
            log(f"    slot[{i}] name={s.material_slot_name} -> "
                f"{mi.get_path_name() if mi else 'None'}")
            if mi is not None:
                # Walk to the parent
                try:
                    parent = mi.get_editor_property("parent")
                    log(f"      parent: {parent.get_path_name() if parent else None}")
                except Exception as e:
                    log(f"      (couldn't read parent: {e})")

    # 3) Recompile both masters — this is what crashed earlier when done
    #    alongside Slate-fragile asset creation, but in isolation should
    #    be safe.
    mel = unreal.MaterialEditingLibrary
    for mp in MASTERS:
        if not unreal.EditorAssetLibrary.does_asset_exist(mp):
            continue
        m = unreal.EditorAssetLibrary.load_asset(mp)
        try:
            mel.recompile_material(m)
            log(f"  recompiled {mp}")
        except Exception as e:
            unreal.log_error(f"  recompile of {mp} FAILED: {e}")
    log("DONE.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
