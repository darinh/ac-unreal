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
COLOR_MASTER_NAME = "M_AcademyColor"
COLOR_MASTER_PATH = f"{MATERIALS_PACKAGE}/{COLOR_MASTER_NAME}"


def log(msg):
    unreal.log(f"[materials] {msg}")


# ---------------------------------------------------------------------
# Texture asset discovery (the user did the import; we just look up).
# ---------------------------------------------------------------------

def list_existing_textures() -> set:
    """Return {texture_hex_uppercase} that exist under /Game/Academy/Textures/.
    Accepts both naming conventions UE may produce:
      T_06003C9A.uasset  (when user adds the prefix)
      06003C9A.uasset    (when UE uses the source filename verbatim)"""
    out = set()
    if not unreal.EditorAssetLibrary.does_directory_exist(TEXTURES_PACKAGE):
        return out
    for asset_path in unreal.EditorAssetLibrary.list_assets(TEXTURES_PACKAGE, recursive=True, include_folder=False):
        # asset_path looks like "/Game/Academy/Textures/06003C9A.06003C9A" or ".T_06003C9A.T_06003C9A"
        name = asset_path.rsplit("/", 1)[-1].split(".")[0]
        if name.startswith("T_"):
            name = name[2:]
        # Filter to 8-hex-character names (texture IDs); skip anything else.
        if len(name) == 8 and all(c in "0123456789ABCDEFabcdef" for c in name):
            out.add(name.upper())
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


def ensure_color_master_material():
    """A second master material whose BaseColor is a vector parameter
    (no texture sampler). Used by MI_Color_RRGGBB instances."""
    if unreal.EditorAssetLibrary.does_asset_exist(COLOR_MASTER_PATH):
        return unreal.EditorAssetLibrary.load_asset(COLOR_MASTER_PATH)

    unreal.EditorAssetLibrary.make_directory(MATERIALS_PACKAGE)
    at = unreal.AssetToolsHelpers.get_asset_tools()
    material = at.create_asset(
        asset_name=COLOR_MASTER_NAME,
        package_path=MATERIALS_PACKAGE,
        asset_class=unreal.Material,
        factory=unreal.MaterialFactoryNew())
    if material is None:
        unreal.log_error("color master material create_asset returned None")
        return None

    mel = unreal.MaterialEditingLibrary
    try:
        color_param = mel.create_material_expression(
            material, unreal.MaterialExpressionVectorParameter, -400, 0)
        color_param.set_editor_property("parameter_name", unreal.Name("BaseColor"))
        color_param.set_editor_property("default_value", unreal.LinearColor(0.5, 0.5, 0.5, 1.0))

        rough = mel.create_material_expression(
            material, unreal.MaterialExpressionConstant, -150, 200)
        rough.set_editor_property("R", 0.85)

        mel.connect_material_property(color_param, "", unreal.MaterialProperty.MP_BASE_COLOR)
        mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
        # No recompile (crashes Slate).
    except Exception as e:
        unreal.log_error(f"color master material expression wiring failed: {e}")

    unreal.EditorAssetLibrary.save_asset(COLOR_MASTER_PATH)
    log(f"  created {COLOR_MASTER_PATH}")
    return material


# ---------------------------------------------------------------------
# MaterialInstance per texture (only for textures the user imported).
# ---------------------------------------------------------------------

_mi_cache = {}

def ensure_mi_for_color(color_master, rgb):
    """Create (or look up) a MaterialInstance whose BaseColor is set
    to `rgb` (a (r,g,b) tuple in 0..1). Asset name is MI_Color_RRGGBB.
    Uses M_AcademyColor as parent (vector BaseColor parameter, no
    texture sampler).

    Defensive normalization: rejects non-finite inputs (NaN/inf) and
    clamps to [0,1]. Critically, the SAME clamped values are used for
    both the MI's name (which determines cache identity) and the
    BaseColor parameter (which determines what's actually rendered) —
    if these diverge, a slot tagged 'MI_Color_FFFFFF' could silently
    store rgb=(2,2,2) and over-bright at runtime."""
    if rgb is None or color_master is None:
        return None
    # Reject non-finite components — avoids OverflowError on int(round(inf)).
    try:
        if not all(c == c and abs(c) != float('inf') for c in rgb):
            return None
    except TypeError:
        return None
    # Clamp to [0,1] before BOTH quantization and storage. From this
    # point on, only use `clamped` — never the raw rgb.
    clamped = tuple(max(0.0, min(1.0, float(c))) for c in rgb)
    r8 = int(round(clamped[0] * 255))
    g8 = int(round(clamped[1] * 255))
    b8 = int(round(clamped[2] * 255))
    key = ("color", r8, g8, b8)
    if key in _mi_cache:
        return _mi_cache[key]
    asset_name = f"MI_Color_{r8:02X}{g8:02X}{b8:02X}"
    asset_path = f"{MATERIALS_PACKAGE}/{asset_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        mi = unreal.EditorAssetLibrary.load_asset(asset_path)
        _mi_cache[key] = mi
        return mi

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
        mel = unreal.MaterialEditingLibrary
        mel.set_material_instance_parent(mi, color_master)
        # Use clamped values — never the raw rgb. The 8-bit-quantized
        # asset name and the stored color must always represent the
        # same color or runtime appearance won't match the asset name.
        # We use the un-quantized clamped value (not r8/255 etc.) to
        # preserve sub-8bit precision for MIs that share the same name.
        mel.set_material_instance_vector_parameter_value(
            mi, unreal.Name("BaseColor"),
            unreal.LinearColor(clamped[0], clamped[1], clamped[2], 1.0))
        unreal.EditorAssetLibrary.save_asset(asset_path)
        _mi_cache[key] = mi
        return mi
    except Exception as e:
        unreal.log_warning(f"color MI {asset_name} failed: {e}")
        return None


def ensure_mi_for_texture(master, tex_hex):
    if tex_hex in _mi_cache:
        return _mi_cache[tex_hex]
    asset_name = "MI_" + tex_hex
    asset_path = f"{MATERIALS_PACKAGE}/{asset_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        mi = unreal.EditorAssetLibrary.load_asset(asset_path)
        _mi_cache[tex_hex] = mi
        return mi

    # Try both UE naming conventions: T_<hex> (when user added the
    # prefix at import time) and bare <hex> (UE's default — derived
    # straight from the source filename).
    tex = None
    for candidate in (f"{TEXTURES_PACKAGE}/T_{tex_hex}", f"{TEXTURES_PACKAGE}/{tex_hex}"):
        if unreal.EditorAssetLibrary.does_asset_exist(candidate):
            tex = unreal.EditorAssetLibrary.load_asset(candidate)
            if tex is not None:
                break
    if tex is None:
        _mi_cache[tex_hex] = None
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
KD_LINE_RE  = re.compile(r"^Kd\s+(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\s*$", re.M)


def parse_mtl(path: Path) -> dict:
    """Return {slot_name: (texture_hex or None, kd_rgb or None)}.
    Walks each `newmtl` block; within a block, the LAST `Kd` line wins
    (acdat emits a default 'Kd 1 1 1' for every material, then overrides
    it with the BGRA-decoded color for solid surfaces). `map_Kd` takes
    precedence over Kd — if a texture is present, color is ignored."""
    out = {}
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8", errors="replace")
    current = None
    tex = None
    rgb = None
    def flush():
        if current is not None:
            out[current] = (tex, rgb)
    for line in text.splitlines():
        line = line.rstrip()
        m = MTL_NAME_RE.match(line)
        if m:
            flush()
            current = m.group(1)
            tex = None
            rgb = None
            continue
        if current is None:
            continue
        t = TEX_LINE_RE.match(line)
        if t:
            tex = t.group(1).upper()
            continue
        k = KD_LINE_RE.match(line)
        if k:
            # LAST Kd wins — overwrites the default 1.0/1.0/1.0.
            rgb = (float(k.group(1)), float(k.group(2)), float(k.group(3)))
    flush()
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

def rebind_meshes(master, color_master):
    cells_done = setups_done = 0
    slots_bound_tex = slots_bound_color = slots_unbound = 0
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
                tex_hex, rgb = slot_map.get(slot_name, (None, None))

                # 1) Prefer textured MI.
                mi = ensure_mi_for_texture(master, tex_hex) if tex_hex else None
                if mi is not None:
                    chosen = mi
                    slots_bound_tex += 1
                else:
                    # 2) Fall back to solid-color MI, but skip the
                    #    acdat-emitted default "Kd 1.0 1.0 1.0" which
                    #    just means "no override" — we don't create an
                    #    MI for those, otherwise every untextured slot
                    #    would render plain white.
                    is_default_white = (
                        rgb is not None
                        and all(abs(c - 1.0) < 1e-3 for c in rgb))
                    color_mi = (ensure_mi_for_color(color_master, rgb)
                                if rgb is not None and not is_default_white
                                else None)
                    if color_mi is not None:
                        chosen = color_mi
                        slots_bound_color += 1
                    else:
                        # 3) Preserve whatever was already in the slot
                        #    (manual editor fixes, other pipeline output).
                        #    Never clobber with None.
                        chosen = slot.material_interface
                        slots_unbound += 1

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
    log(f"  slots: bound_tex={slots_bound_tex} bound_color={slots_bound_color} unbound={slots_unbound}")
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
        # Still proceed to create color MIs even without textures — solid
        # surfaces don't need any texture import.

    log("step 2a: ensuring textured master material ...")
    master = ensure_master_material()
    log("step 2b: ensuring color master material ...")
    color_master = ensure_color_master_material()
    if master is None or color_master is None:
        unreal.log_error("master material(s) unavailable; aborting.")
        return 2

    log("step 3+4: building MaterialInstances + rebinding mesh slots ...")
    rebind_meshes(master, color_master)

    log("DONE.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
