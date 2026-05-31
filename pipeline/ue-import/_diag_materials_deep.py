"""Deeper material diagnostic: inspect MI texture parameters, master
material expressions, and check if a sample MI actually has a Texture2D
bound to BaseColorTex."""

import unreal

def log(m): unreal.log(f"[matprobe] {m}")

# Sample a textured MI bound to a cell slot.
MIS_TO_CHECK = [
    "/Game/Academy/Materials/MI_06003C9C",  # spawn cell wall
    "/Game/Academy/Materials/MI_06003C9A",  # spawn cell floor
    "/Game/Academy/Materials/MI_Color_000000",  # the previously-black sentinel (should now be grey)
]

mel = unreal.MaterialEditingLibrary

for mip in MIS_TO_CHECK:
    if not unreal.EditorAssetLibrary.does_asset_exist(mip):
        log(f"  MISSING: {mip}")
        continue
    mi = unreal.EditorAssetLibrary.load_asset(mip)
    log(f"  {mip}:")
    parent = mi.get_editor_property("parent")
    log(f"    parent: {parent.get_path_name() if parent else None}")
    # Texture parameter
    try:
        tex = mel.get_material_instance_texture_parameter_value(mi, unreal.Name("BaseColorTex"))
        log(f"    BaseColorTex texture: {tex.get_path_name() if tex else None}")
        if tex:
            log(f"      size: {tex.blueprint_get_size_x()}x{tex.blueprint_get_size_y()}")
    except Exception as e:
        log(f"    (no BaseColorTex param: {e})")
    # Vector parameter (for color MIs)
    try:
        c = mel.get_material_instance_vector_parameter_value(mi, unreal.Name("BaseColor"))
        log(f"    BaseColor vector: ({c.r:.3f}, {c.g:.3f}, {c.b:.3f}, {c.a:.3f})")
    except Exception as e:
        log(f"    (no BaseColor param: {e})")

# Master material expression inspection
MASTERS = ("/Game/Academy/Materials/M_AcademyBase",
           "/Game/Academy/Materials/M_AcademyColor")
for mp in MASTERS:
    if not unreal.EditorAssetLibrary.does_asset_exist(mp):
        continue
    m = unreal.EditorAssetLibrary.load_asset(mp)
    log(f"  {mp}:")
    log(f"    two_sided={m.two_sided} blend_mode={m.blend_mode} shading_model={m.shading_model}")
    # List parameters
    scalar_params = mel.get_scalar_parameter_names(m)
    vec_params = mel.get_vector_parameter_names(m)
    tex_params = mel.get_texture_parameter_names(m)
    log(f"    scalar params: {[str(p) for p in scalar_params]}")
    log(f"    vector params: {[str(p) for p in vec_params]}")
    log(f"    texture params: {[str(p) for p in tex_params]}")
