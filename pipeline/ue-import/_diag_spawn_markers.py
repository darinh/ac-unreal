"""Place a GIANT GLOWING SPHERE at PlayerStart. If we don't see it in
the render, the camera isn't where we think — the entire diagnostic
chain has been based on a false premise.

Also spawn 4 colored cubes 500cm in each cardinal direction so we
can tell which way the camera is facing."""

import unreal

unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")
eas = unreal.EditorActorSubsystem()

# Find PlayerStart's actual location.
ps = next((a for a in eas.get_all_level_actors() if isinstance(a, unreal.PlayerStart)), None)
if ps is None:
    raise SystemExit("No PlayerStart found")
loc = ps.get_actor_location()
rot = ps.get_actor_rotation()
unreal.log(f"[diag-sphere] PlayerStart at {loc} rot={rot}")

# Delete any prior diagnostic actors so re-runs don't pile them up.
for a in list(eas.get_all_level_actors()):
    try:
        if a.get_actor_label().startswith("DiagSphere") or a.get_actor_label().startswith("DiagCube"):
            unreal.EditorLevelLibrary.destroy_actor(a)
    except Exception:
        pass

# Create a hot-pink UNLIT EMISSIVE material if not already there.
mat_path = "/Game/Academy/Materials/M_HotPinkDiagnostic"
mat = unreal.EditorAssetLibrary.load_asset(mat_path)
if mat is None:
    raise SystemExit("M_HotPinkDiagnostic missing")

# Bright cyan (different from hot pink to differentiate from the spawn-cell material)
cyan_path = "/Game/Academy/Materials/M_BrightCyanDiagnostic"
if not unreal.EditorAssetLibrary.does_asset_exist(cyan_path):
    at = unreal.AssetToolsHelpers.get_asset_tools()
    cm = at.create_asset("M_BrightCyanDiagnostic", "/Game/Academy/Materials",
                         unreal.Material, unreal.MaterialFactoryNew())
    cm.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    cm.set_editor_property("two_sided", True)
    mel = unreal.MaterialEditingLibrary
    emi = mel.create_material_expression(cm, unreal.MaterialExpressionConstant3Vector, -200, 0)
    emi.constant = unreal.LinearColor(0.0, 5.0, 5.0, 1.0)
    mel.connect_material_property(emi, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(cm)
    unreal.EditorAssetLibrary.save_asset(cyan_path)
cyan_mat = unreal.EditorAssetLibrary.load_asset(cyan_path)

sphere_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Sphere")
cube_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube")

def spawn_marker(label, mesh, location, scale, mat):
    actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, location, unreal.Rotator(0, 0, 0))
    if actor is None:
        return None
    actor.set_actor_label(label)
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_material(0, mat)
    actor.set_actor_scale3d(scale)
    actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return actor

# Giant PINK sphere AT player spawn (3m radius)
spawn_marker("DiagSphere_AtPlayer", sphere_mesh,
             unreal.Vector(loc.x, loc.y, loc.z), unreal.Vector(3, 3, 3), mat)

# 4 CYAN cubes 5m away in cardinal directions
spawn_marker("DiagCube_East",  cube_mesh, unreal.Vector(loc.x + 500, loc.y, loc.z),       unreal.Vector(1, 1, 1), cyan_mat)
spawn_marker("DiagCube_North", cube_mesh, unreal.Vector(loc.x, loc.y + 500, loc.z),       unreal.Vector(1, 1, 1), cyan_mat)
spawn_marker("DiagCube_West",  cube_mesh, unreal.Vector(loc.x - 500, loc.y, loc.z),       unreal.Vector(1, 1, 1), cyan_mat)
spawn_marker("DiagCube_South", cube_mesh, unreal.Vector(loc.x, loc.y - 500, loc.z),       unreal.Vector(1, 1, 1), cyan_mat)

unreal.EditorLevelLibrary.save_current_level()
unreal.log("[diag-sphere] spawned 1 pink sphere + 4 cyan cubes around PlayerStart, saved level")
