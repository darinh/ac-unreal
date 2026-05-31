"""Inspect master material expressions and parameter defaults."""
import unreal

def log(m): unreal.log(f"[graph] {m}")

mel = unreal.MaterialEditingLibrary

for mp in ("/Game/Academy/Materials/M_AcademyBase", "/Game/Academy/Materials/M_AcademyColor"):
    if not unreal.EditorAssetLibrary.does_asset_exist(mp):
        log(f"MISSING {mp}")
        continue
    m = unreal.EditorAssetLibrary.load_asset(mp)
    log(f"=== {mp} ===")
    log(f"  two_sided: {m.get_editor_property('two_sided')}")
    log(f"  blend_mode: {m.get_editor_property('blend_mode')}")
    log(f"  scalar params: {[str(p) for p in mel.get_scalar_parameter_names(m)]}")
    log(f"  vector params: {[str(p) for p in mel.get_vector_parameter_names(m)]}")
    log(f"  texture params: {[str(p) for p in mel.get_texture_parameter_names(m)]}")
    # Defaults on master material
    for p in mel.get_vector_parameter_names(m):
        try:
            default = mel.get_material_default_vector_parameter_value(m, p)
            log(f"    {p} default: ({default.r:.3f}, {default.g:.3f}, {default.b:.3f}, {default.a:.3f})")
        except Exception as e:
            log(f"    {p} default: ERR {e}")
    # Expression list
    try:
        exprs = m.get_editor_property("expressions") or []
        log(f"  expressions ({len(exprs)}):")
        for i, e in enumerate(exprs):
            log(f"    [{i}] {e.get_class().get_name()}")
    except Exception as e:
        log(f"  (no expressions: {e})")
