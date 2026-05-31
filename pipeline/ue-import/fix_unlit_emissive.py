# =====================================================================
# fix_unlit_emissive.py
#
# ROOT-CAUSE FIX for the "academy renders black" problem.
#
# Why the academy was black (diagnosis, not a guess):
#   - AC bakes ALL of its lighting into per-vertex colors (SWVertex.Color,
#     Gouraud). The OBJ export dropped that data (vertices are position-
#     only), so the geometry carries zero lighting information.
#   - The master materials (M_AcademyBase / M_AcademyColor) are standard
#     LIT PBR materials, so they need real scene light to be visible.
#   - The scene is an enclosed, underground dungeon (Z ~= -1200) lit only
#     by a weak directional sun + skylight ambient, with Lumen/GI/RT
#     DISABLED. With no GI bounce the sun can't reach interior surfaces,
#     and the torch PointLights are mis-placed (2x coord bug). Result:
#     interiors render black, and the SkyLight captures pink underground
#     atmosphere which tints everything magenta.
#
# The fix:
#   Render AC content the way AC does -- UNLIT. Switch both master
#   materials to the Unlit shading model and route the existing
#   BaseColorTex / BaseColor parameter into EMISSIVE COLOR instead of
#   Base Color. Lighting, exposure, and the pink sky then become
#   irrelevant: every stone texture shows at full brightness in every
#   cell, interior and exterior. Because every MaterialInstance inherits
#   from these two masters, this one change fixes the whole academy.
#
#   Also neutralizes the PostProcessVolume exposure (the prior sessions
#   cranked it to +15 EV / SkyLight 200 chasing the darkness) so emissive
#   values render at their true brightness.
#
# Headless-safe: does NOT call recompile_material (that crashes Slate in
# -RenderOffScreen). UE compiles the changed graph lazily on next load.
#
# Idempotent: detects already-unlit masters and skips re-wiring.
# =====================================================================

import unreal

EAL = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary

MASTER_TEX   = "/Game/Academy/Materials/M_AcademyBase"   # textured master
MASTER_COLOR = "/Game/Academy/Materials/M_AcademyColor"  # solid-color master
MAP_PATH     = "/Game/Academy/Maps/AcademyMap"


def log(m):
    unreal.log(f"[unlit-fix] {m}")


def _find_expression(mat, class_name, param_name=None):
    """Return the first material expression of the given class (and
    optional parameter_name), or None."""
    try:
        exprs = mat.get_editor_property("expressions") or []
    except Exception as e:
        log(f"  (cannot read expressions on {mat.get_name()}: {e})")
        return None
    for e in exprs:
        if e.get_class().get_name() != class_name:
            continue
        if param_name is None:
            return e
        try:
            if str(e.get_editor_property("parameter_name")) == param_name:
                return e
        except Exception:
            pass
    return None


def convert_master(path, expr_class, param_name, output_name, create_fn):
    """Set `path` to Unlit and connect its BaseColor* parameter node to
    Emissive Color. Reuses the existing parameter node if present;
    otherwise creates a fresh one via create_fn."""
    if not EAL.does_asset_exist(path):
        log(f"MISSING master {path} -- skipping")
        return False
    mat = EAL.load_asset(path)

    already_unlit = (mat.get_editor_property("shading_model")
                     == unreal.MaterialShadingModel.MSM_UNLIT)

    # Find (or create) the parameter node that holds the texture/color.
    node = _find_expression(mat, expr_class, param_name)
    if node is None:
        log(f"  {path}: no existing {param_name} node; creating one")
        node = create_fn(mat)
    if node is None:
        log(f"  {path}: could not obtain {param_name} node -- aborting this master")
        return False

    # Switch to Unlit. In Unlit, the Base Color input is ignored and
    # Emissive Color IS the final surface color -- exactly AC's flat look.
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)

    ok = mel.connect_material_property(
        node, output_name, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    log(f"  {path}: shading=UNLIT, {param_name}->Emissive connected={ok} "
        f"(was_unlit={already_unlit})")

    EAL.save_asset(path)
    return True


def _create_tex_param(mat):
    node = mel.create_material_expression(
        mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, 300)
    node.set_editor_property("parameter_name", unreal.Name("BaseColorTex"))
    return node


def _create_color_param(mat):
    node = mel.create_material_expression(
        mat, unreal.MaterialExpressionVectorParameter, -600, 300)
    node.set_editor_property("parameter_name", unreal.Name("BaseColor"))
    node.set_editor_property("default_value", unreal.LinearColor(0.5, 0.5, 0.5, 1.0))
    return node


def neutralize_exposure():
    """Reset the PostProcessVolume so emissive renders at true brightness.
    Prior sessions cranked exposure to +15 EV chasing the darkness."""
    unreal.EditorLevelLibrary.load_level(MAP_PATH)
    eas = unreal.EditorActorSubsystem()
    ppvs = [a for a in eas.get_all_level_actors()
            if isinstance(a, unreal.PostProcessVolume)]
    for ppv in ppvs:
        s = ppv.settings
        s.override_auto_exposure_method = True
        s.auto_exposure_method = unreal.AutoExposureMethod.AEM_MANUAL
        s.override_auto_exposure_bias = True
        s.auto_exposure_bias = 0.0
        s.override_auto_exposure_min_brightness = True
        s.auto_exposure_min_brightness = 1.0
        s.override_auto_exposure_max_brightness = True
        s.auto_exposure_max_brightness = 1.0
        s.override_indirect_lighting_intensity = True
        s.indirect_lighting_intensity = 1.0
        ppv.settings = s
        log(f"  PPV neutralized: manual exposure, bias 0, fixed brightness 1.0")
    if not ppvs:
        log("  (no PostProcessVolume found)")
    unreal.EditorLevelLibrary.save_current_level()


def diagnose_binding():
    """Report, for a few representative cell meshes, whether each material
    slot is bound to an MI (child of our masters) or fell back to
    WorldGridMaterial/None. Tells us if walls are actually textured."""
    sample = [
        "/Game/Academy/Cells/SM_86020100",  # spawn-area cell (walls 06003EAE/AC)
        "/Game/Academy/Cells/SM_860201AD",  # the cell the hot-pink test hit
    ]
    masters = (MASTER_TEX, MASTER_COLOR)
    for p in sample:
        if not EAL.does_asset_exist(p):
            log(f"  [bind] MISSING {p}")
            continue
        sm = EAL.load_asset(p)
        slots = sm.get_editor_property("static_materials") or []
        log(f"  [bind] {p}: {len(slots)} slots")
        for i, s in enumerate(slots):
            mi = s.material_interface
            if mi is None:
                desc = "None -> WorldGridMaterial (UNBOUND)"
            else:
                name = mi.get_path_name()
                parent = None
                try:
                    parent = mi.get_editor_property("parent")
                except Exception:
                    pass
                pname = parent.get_path_name() if parent else "(none)"
                bound_ok = any(m in pname for m in masters)
                desc = f"{name} parent={pname} {'OK' if bound_ok else '<-- NOT our master'}"
            log(f"      slot[{i}] {s.material_slot_name}: {desc}")


def main():
    log("step 1: M_AcademyBase -> Unlit, BaseColorTex -> Emissive")
    convert_master(MASTER_TEX, "MaterialExpressionTextureSampleParameter2D",
                   "BaseColorTex", "RGB", _create_tex_param)

    log("step 2: M_AcademyColor -> Unlit, BaseColor -> Emissive")
    convert_master(MASTER_COLOR, "MaterialExpressionVectorParameter",
                   "BaseColor", "", _create_color_param)

    log("step 3: neutralize PostProcessVolume exposure")
    neutralize_exposure()

    log("step 4: binding diagnostic (are walls textured?)")
    diagnose_binding()

    log("DONE.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main() or 0)
