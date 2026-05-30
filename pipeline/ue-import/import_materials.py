# =====================================================================
# import_materials.py
#
# Phase 5e-side polish: assign Material Instances + textures to the
# StaticMesh material slots that import_academy.py / import_statics.py
# left empty. Without this pass everything renders gray (the default
# WorldGridMaterial). With it, the actual AC textures show up.
#
# WHY THIS IS A TWO-STEP PROCESS (manual + automated)
# ----------------------------------------------------
# UE's AssetImportTask path for textures goes through Interchange,
# which refreshes the ContentBrowser on each import. The ContentBrowser
# refresh asserts CurrentApplication.IsValid() on Slate — and that
# assertion fails fatally even with -RenderOffScreen + -nocrashreports.
# So texture import is NOT safe to do via headless Python.
#
# The user does this ONCE in the editor:
#   1. Open AcUnreal in UE5.7.
#   2. In the Content Browser, navigate to /Game/Academy/Textures (create
#      if missing). Right-click empty area → Import to /Game/Academy/Textures.
#   3. Multi-select the entire contents of BOTH of these directories on disk:
#        pipeline/dat-extract/out/academy_8602/textures/         (37 PNGs)
#        pipeline/dat-extract/out/academy_8602_statics/textures/ (253 PNGs)
#      and import (defaults are fine; sRGB on, BC1/BC3 compression).
#   4. Save All. Close the editor.
#
# THIS SCRIPT then does the headless-safe bits:
#   - Create master material /Game/Academy/Materials/M_AcademyBase
#     (parameterized: BaseColorTex).
#   - For every Texture2D that already exists under /Game/Academy/Textures,
#     create a MaterialInstanceConstant /Game/Academy/Materials/MI_<hex>.
#   - Walk every cell .mtl / setup .mtl, parse the slot_name -> texture_id
#     mapping, and rebind each StaticMesh's static_materials list.
#
# Idempotent: re-running reuses existing assets.
# =====================================================================

import unreal
import os
import sys
import time
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CELL_OBJ_DIR    = REPO_ROOT / "pipeline" / "dat-extract" / "out" / "academy_8602"
SETUP_OBJ_DIR   = REPO_ROOT / "pipeline" / "dat-extract" / "out" / "academy_8602_statics"

TEXTURES_PACKAGE  = "/Game/Academy/Textures"
MATERIALS_PACKAGE = "/Game/Academy/Materials"
CELLS_PACKAGE     = "/Game/Academy/Cells"
SETUPS_PACKAGE    = "/Game/Academy/Setups"

MASTER_NAME = "M_AcademyBase"
MASTER_PATH = f"{MATERIALS_PACKAGE}/{MASTER_NAME}"


def log(msg):
    unreal.log(f"[materials] {msg}")


# ---------------------------------------------------------------------
# Texture asset discovery (the user did the import; we just look up).
# ---------------------------------------------------------------------

def list_existing_textures() -> set:
    """Return {texture_hex_uppercase} that exist under /Game/Academy/Textures/."""
    out = set()
    if not unreal.EditorAssetLibrary.does_directory_exist(TEXTURES_PACKAGE):
        return out
    for asset_path in unreal.EditorAssetLibrary.list_assets(TEXTURES_PACKAGE, recursive=True, include_folder=False):
        # asset_path looks like "/Game/Academy/Textures/T_06003C9A.T_06003C9A"
        name = asset_path.rsplit("/", 1)[-1].split(".")[0]
        if name.startswith("T_"):
            out.add(name[2:].upper())
    return out


# ---------------------------------------------------------------------
# Master material — no recompile_material (that crashes Slate).
# ---------------------------------------------------------------------

def ensure_master_material():
    if unreal.EditorAssetLibrary.does_asset_exist(MASTER_PATH):
        return unreal.EditorAssetLibrary.load_asset(MASTER_PATH)

    unreal.EditorAssetLibrary.make_directory(MATERIALS_PACKAGE)
    at = unreal.AssetToolsHelpers.get_asset_tools()
    material = at.create_asset(
        asset_name=MASTER_NAME,
        package_path=MATERIALS_PACKAGE,
        asset_class=unreal.Material,
        factory=unreal.MaterialFactoryNew())
    if material is None:
        unreal.log_error("master material create_asset returned None")
        return None

    mel = unreal.MaterialEditingLibrary
    try:
        tex_param = mel.create_material_expression(
            material, unreal.MaterialExpressionTextureSampleParameter2D, -400, 0)
        tex_param.set_editor_property("parameter_name", unreal.Name("BaseColorTex"))

        rough = mel.create_material_expression(
            material, unreal.MaterialExpressionConstant, -150, 200)
        rough.set_editor_property("R", 0.85)

        mel.connect_material_property(tex_param, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
        mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
        # NB: do not call mel.recompile_material(material) — UE compiles
        # shaders lazily on first use; the explicit recompile triggers a
        # Slate-dependent path that crashes in -RenderOffScreen mode.
    except Exception as e:
        unreal.log_error(f"master material expression wiring failed: {e}")

    unreal.EditorAssetLibrary.save_asset(MASTER_PATH)
    log(f"  created {MASTER_PATH}")
    return material


# ---------------------------------------------------------------------
# MaterialInstance per texture (only for textures the user imported).
# ---------------------------------------------------------------------

_mi_cache = {}

def ensure_mi_for_texture(master, tex_hex):
    if tex_hex in _mi_cache:
        return _mi_cache[tex_hex]
    asset_name = "MI_" + tex_hex
    asset_path = f"{MATERIALS_PACKAGE}/{asset_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        mi = unreal.EditorAssetLibrary.load_asset(asset_path)
        _mi_cache[tex_hex] = mi
        return mi

    tex_path = f"{TEXTURES_PACKAGE}/T_{tex_hex}"
    if not unreal.EditorAssetLibrary.does_asset_exist(tex_path):
        _mi_cache[tex_hex] = None
        return None
    tex = unreal.EditorAssetLibrary.load_asset(tex_path)
    if tex is None:
        return None

    at = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.MaterialInstanceConstantFactoryNew()
    try:
        mi = at.create_asset(
            asset_name=asset_name,
            package_path=MATERIALS_PACKAGE,
            asset_class=unreal.MaterialInstanceConstant,
            factory=factory)
        if mi is None:
            return None
        # Set the parent on the MI itself — the factory's Python binding
        # doesn't expose an 'initial_parent' property in UE 5.7.
        unreal.MaterialEditingLibrary.set_material_instance_parent(mi, master)
        unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
            mi, unreal.Name("BaseColorTex"), tex)
        unreal.EditorAssetLibrary.save_asset(asset_path)
        _mi_cache[tex_hex] = mi
        return mi
    except Exception as e:
        unreal.log_warning(f"MI for {tex_hex} failed: {e}")
        return None


# ---------------------------------------------------------------------
# MTL parsing (slot_name -> texture_hex).
# ---------------------------------------------------------------------

TEX_LINE_RE = re.compile(r"^map_Kd\s+textures/([0-9A-Fa-f]+)\.\w+\s*$", re.M)
MTL_NAME_RE = re.compile(r"^newmtl\s+(\S+)\s*$", re.M)


def parse_mtl(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8", errors="replace")
    current = None
    for line in text.splitlines():
        line = line.rstrip()
        m = MTL_NAME_RE.match(line)
        if m:
            current = m.group(1)
            out.setdefault(current, None)
            continue
        if current and line.startswith("map_Kd"):
            t = TEX_LINE_RE.match(line)
            if t:
                out[current] = t.group(1).upper()
    return out


def asset_name_for_obj(obj_path: Path) -> str:
    """cell_86020100.obj  -> SM_86020100
       setup_02000001.obj -> SM_Setup_02000001"""
    stem = obj_path.stem
    if stem.startswith("cell_"):
        return "SM_" + stem[len("cell_"):]
    if stem.startswith("setup_"):
        return "SM_Setup_" + stem[len("setup_"):]
    return "SM_" + stem


# ---------------------------------------------------------------------
# Rebind StaticMesh material slots.
# ---------------------------------------------------------------------

def rebind_meshes(master):
    cells_done = setups_done = 0
    slots_bound = slots_unbound_no_tex = slots_unbound_no_mi = 0
    t0 = time.time()

    for mtl_iter, package in [
        (sorted(CELL_OBJ_DIR.glob("cell_*.mtl")),   CELLS_PACKAGE),
        (sorted(SETUP_OBJ_DIR.glob("setup_*.mtl")), SETUPS_PACKAGE),
    ]:
        for p in mtl_iter:
            obj_path = p.with_suffix(".obj")
            asset_name = asset_name_for_obj(obj_path)
            asset_path = f"{package}/{asset_name}"
            if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
                continue
            sm = unreal.EditorAssetLibrary.load_asset(asset_path)
            if sm is None or not isinstance(sm, unreal.StaticMesh):
                continue

            slot_map = parse_mtl(p)
            existing = sm.get_editor_property("static_materials") or []
            new_list = []
            for slot in existing:
                slot_name = str(slot.material_slot_name)
                tex_hex = slot_map.get(slot_name)
                mi = ensure_mi_for_texture(master, tex_hex) if tex_hex else None
                if mi is not None:
                    slots_bound += 1
                    chosen = mi
                else:
                    # No replacement available — preserve whatever was
                    # already in the slot (could be None, could be a
                    # manual editor fix, could be another pipeline's
                    # output). Never clobber with None.
                    chosen = slot.material_interface
                    if tex_hex is None:
                        slots_unbound_no_tex += 1
                    else:
                        slots_unbound_no_mi += 1
                new_list.append(unreal.StaticMaterial(
                    material_interface=chosen,
                    material_slot_name=unreal.Name(slot_name)))
            sm.set_editor_property("static_materials", new_list)
            unreal.EditorAssetLibrary.save_asset(asset_path)

            if package == CELLS_PACKAGE:
                cells_done += 1
                if cells_done % 64 == 0:
                    log(f"  cells re-bound: {cells_done}  ({time.time()-t0:.1f}s)")
            else:
                setups_done += 1
                if setups_done % 32 == 0:
                    log(f"  setups re-bound: {setups_done}  ({time.time()-t0:.1f}s)")

    log(f"rebind done: cells={cells_done} setups={setups_done}")
    log(f"  slots: bound_to_MI={slots_bound}, unbound_no_tex_in_mtl={slots_unbound_no_tex}, unbound_no_imported_texture={slots_unbound_no_mi}")
    log(f"  ({time.time()-t0:.1f}s)")


def main():
    log("step 1: scanning /Game/Academy/Textures for imported Texture2D assets ...")
    tex_hexes = list_existing_textures()
    log(f"  found {len(tex_hexes)} imported textures")
    if not tex_hexes:
        unreal.log_warning(
            "No textures imported under /Game/Academy/Textures yet. "
            "Open the editor once, drag the contents of "
            "pipeline/dat-extract/out/academy_8602/textures and "
            "pipeline/dat-extract/out/academy_8602_statics/textures "
            "into /Game/Academy/Textures, save, then re-run this script."
        )
        return 0

    log("step 2: ensuring master material ...")
    master = ensure_master_material()
    if master is None:
        unreal.log_error("master material unavailable; aborting.")
        return 2

    log("step 3+4: building MaterialInstances + rebinding mesh slots ...")
    rebind_meshes(master)

    log("DONE.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
