"""Create a HOT PINK EMISSIVE UNLIT material and assign it directly to
the spawn cell's SM_860201AD mesh. If even THIS doesn't render visibly,
the bug is NOT lighting/materials — it's visibility/culling/camera."""

import unreal


def log(m): unreal.log(f"[hotpink] {m}")


# Create a glaringly visible material.
mat_path = "/Game/Academy/Materials/M_HotPinkDiagnostic"
mat_pkg = "/Game/Academy/Materials"

if not unreal.EditorAssetLibrary.does_asset_exist(mat_path):
    at = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.MaterialFactoryNew()
    mat = at.create_asset(
        asset_name="M_HotPinkDiagnostic",
        package_path=mat_pkg,
        asset_class=unreal.Material,
        factory=factory)
    if mat is None:
        unreal.log_error("[hotpink] failed to create M_HotPinkDiagnostic")
        raise SystemExit(1)

    # Hot pink emissive — UNLIT shading so it shows regardless of lighting.
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)

    mel = unreal.MaterialEditingLibrary
    emissive_node = mel.create_material_expression(
        mat, unreal.MaterialExpressionConstant3Vector, -200, 0)
    emissive_node.constant = unreal.LinearColor(1.0, 0.0, 1.0, 1.0)  # hot pink
    mel.connect_material_property(emissive_node, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    unreal.EditorAssetLibrary.save_asset(mat_path)
    log(f"created {mat_path}")
else:
    mat = unreal.EditorAssetLibrary.load_asset(mat_path)
    log(f"reusing {mat_path}")

# Now assign it to SM_860201AD's slot 0.
cell_path = "/Game/Academy/Cells/SM_860201AD"
sm = unreal.EditorAssetLibrary.load_asset(cell_path)
slots = sm.get_editor_property("static_materials") or []
log(f"  {cell_path} has {len(slots)} slots")
# Save original slot 0 material so we can revert later.
orig = slots[0].material_interface if slots else None
log(f"  original slot 0 material: {orig.get_path_name() if orig else None}")
# Build a new static_materials list with slot 0 swapped to hot pink.
new_slots = []
for i, s in enumerate(slots):
    new_slot = unreal.StaticMaterial()
    new_slot.material_slot_name = s.material_slot_name
    new_slot.material_interface = mat if i == 0 else s.material_interface
    new_slots.append(new_slot)
sm.set_editor_property("static_materials", new_slots)
unreal.EditorAssetLibrary.save_asset(cell_path)
log(f"  slot 0 of {cell_path} -> {mat_path}")

# Also make sure the cell actor in the level uses this updated mesh.
unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")
log(f"  level loaded; spawn cell mesh hot-pinked.")
