# =====================================================================
# rebuild_academy_masters.py
#
# Deterministic, from-scratch rebuild of the two master materials. The
# earlier iterative edits (unlit fix -> hybrid -> retunes) left orphan
# expression nodes that made the emissive wiring unreliable. This deletes
# both masters and recreates a single known-good graph, then re-points
# every MaterialInstance back to the right master.
#
# Graph (both masters), Default-Lit:
#   BaseColor = <source>                          (lit -> torch response)
#   Roughness = 0.85
#   Emissive  = <source> * SCALE  +  LIFT         (ambient floor; the
#               constant LIFT guarantees even pitch-dark textures/colors
#               read as a dim glow instead of pure black -- the texture-
#               only term was leaving the dark stone floor at ~0)
#
#   <source> = TextureSampleParameter2D "BaseColorTex"  (M_AcademyBase)
#            = VectorParameter        "BaseColor"       (M_AcademyColor)
#
# Tunables (env):  AC_EMISSIVE_SCALE (default 0.35), AC_EMISSIVE_LIFT (0.05)
# Headless-safe (no recompile_material).
# =====================================================================
import os
import unreal

EAL = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty
PKG = "/Game/Academy/Materials"
MASTER_TEX = f"{PKG}/M_AcademyBase"
MASTER_COLOR = f"{PKG}/M_AcademyColor"
SCALE = float(os.environ.get("AC_EMISSIVE_SCALE", "0.35"))
LIFT = float(os.environ.get("AC_EMISSIVE_LIFT", "0.05"))


def log(m): unreal.log(f"[rebuild] {m}")


# Shading mode: "unlit" (default) renders the AC textures at full, even
# brightness -- which matches the real academy (a bright, evenly-lit stone
# room), not a dark dungeon. "lit" keeps the dynamic-torch hybrid.
SHADING = os.environ.get("AC_SHADING", "unlit").lower()


def make_master(path, name, kind):
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    at = unreal.AssetToolsHelpers.get_asset_tools()
    mat = at.create_asset(name, PKG, unreal.Material, unreal.MaterialFactoryNew())
    sm = (unreal.MaterialShadingModel.MSM_UNLIT if SHADING == "unlit"
          else unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property("shading_model", sm)
    mat.set_editor_property("two_sided", True)

    if kind == "tex":
        src = mel.create_material_expression(
            mat, unreal.MaterialExpressionTextureSampleParameter2D, -800, 0)
        src.set_editor_property("parameter_name", unreal.Name("BaseColorTex"))
        out = "RGB"
    else:
        src = mel.create_material_expression(
            mat, unreal.MaterialExpressionVectorParameter, -800, 0)
        src.set_editor_property("parameter_name", unreal.Name("BaseColor"))
        src.set_editor_property("default_value", unreal.LinearColor(0.5, 0.5, 0.5, 1.0))
        out = ""

    mel.connect_material_property(src, out, MP.MP_BASE_COLOR)

    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 250)
    rough.set_editor_property("r", 0.85)
    mel.connect_material_property(rough, "", MP.MP_ROUGHNESS)

    # Emissive = src*SCALE + LIFT
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -400, 450)
    sc = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -650, 540)
    sc.set_editor_property("r", SCALE)
    a1 = mel.connect_material_expressions(src, out, mul, "A")
    b1 = mel.connect_material_expressions(sc, "", mul, "B")

    add = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -200, 450)
    lift = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 600)
    lift.set_editor_property("r", LIFT)
    a2 = mel.connect_material_expressions(mul, "", add, "A")
    b2 = mel.connect_material_expressions(lift, "", add, "B")
    em = mel.connect_material_property(add, "", MP.MP_EMISSIVE_COLOR)

    EAL.save_asset(path)
    log(f"{path}: rebuilt LIT  emissive=src*{SCALE}+{LIFT}  "
        f"(mulA={a1} mulB={b1} addA={a2} addB={b2} em={em})")
    return mat


def repoint_instances(tex_master, color_master):
    n_tex = n_col = 0
    for ap in EAL.list_assets(PKG, recursive=False, include_folder=False):
        a = EAL.load_asset(ap)
        if not isinstance(a, unreal.MaterialInstanceConstant):
            continue
        nm = a.get_name()
        if nm.startswith("MI_Color_"):
            mel.set_material_instance_parent(a, color_master); n_col += 1
        elif nm.startswith("MI_"):
            mel.set_material_instance_parent(a, tex_master); n_tex += 1
        else:
            continue
        EAL.save_asset(ap)
    log(f"re-pointed instances: {n_tex} -> M_AcademyBase, {n_col} -> M_AcademyColor")


log(f"SCALE={SCALE} LIFT={LIFT}")
tex_master = make_master(MASTER_TEX, "M_AcademyBase", "tex")
color_master = make_master(MASTER_COLOR, "M_AcademyColor", "color")
repoint_instances(tex_master, color_master)
log("DONE.")
