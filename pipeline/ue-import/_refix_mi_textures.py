# Re-apply texture/color parameter overrides to every MaterialInstance.
# The master rebuild (delete+recreate) gave the master parameters new
# GUIDs, so the instances' stored overrides no longer matched and fell
# back to the default grey texture. Re-setting the override by NAME
# against the current masters fixes it without touching the masters or
# the mesh slot bindings.
import unreal

EAL = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
PKG = "/Game/Academy/Materials"
TEX = "/Game/Academy/Textures"


def log(m): unreal.log(f"[refix] {m}")


def find_texture(hexid):
    for cand in (f"{TEX}/T_{hexid}", f"{TEX}/{hexid}"):
        if EAL.does_asset_exist(cand):
            return EAL.load_asset(cand)
    return None


n_tex = n_col = n_miss = 0
for ap in EAL.list_assets(PKG, recursive=False, include_folder=False):
    a = EAL.load_asset(ap)
    if not isinstance(a, unreal.MaterialInstanceConstant):
        continue
    nm = a.get_name()
    if nm.startswith("MI_Color_"):
        hexrgb = nm[len("MI_Color_"):]
        try:
            r = int(hexrgb[0:2], 16) / 255.0
            g = int(hexrgb[2:4], 16) / 255.0
            b = int(hexrgb[4:6], 16) / 255.0
        except Exception:
            continue
        # AC pure-black sentinel -> warm stone grey (matches import_materials).
        if (r, g, b) == (0.0, 0.0, 0.0):
            r, g, b = 0.60, 0.50, 0.45
        mel.set_material_instance_vector_parameter_value(
            a, unreal.Name("BaseColor"), unreal.LinearColor(r, g, b, 1.0))
        EAL.save_asset(ap); n_col += 1
    elif nm.startswith("MI_") and len(nm) == 11:  # MI_06003C9C
        hexid = nm[3:]
        tex = find_texture(hexid)
        if tex is None:
            n_miss += 1
            continue
        mel.set_material_instance_texture_parameter_value(
            a, unreal.Name("BaseColorTex"), tex)
        EAL.save_asset(ap); n_tex += 1

log(f"re-applied: {n_tex} texture MIs, {n_col} color MIs, {n_miss} missing-texture")
