"""Verify the bounds fix actually took. Reload mesh and re-check."""
import unreal

def log(m): unreal.log(f"[verify] {m}")

samples = [
    "/Game/Academy/Cells/SM_860201AD",
    "/Game/Academy/Setups/SM_Setup_0200007C",
]
for path in samples:
    sm = unreal.EditorAssetLibrary.load_asset(path)
    if not sm: continue
    pbe = sm.get_editor_property("positive_bounds_extension")
    nbe = sm.get_editor_property("negative_bounds_extension")
    b = sm.get_bounds()
    bb = sm.get_bounding_box()
    log(f"  {sm.get_name()}:")
    log(f"    positive_bounds_extension: ({pbe.x:.1f}, {pbe.y:.1f}, {pbe.z:.1f})")
    log(f"    negative_bounds_extension: ({nbe.x:.1f}, {nbe.y:.1f}, {nbe.z:.1f})")
    log(f"    get_bounds().box_extent: ({b.box_extent.x:.1f}, {b.box_extent.y:.1f}, {b.box_extent.z:.1f})")
    log(f"    get_bounds().sphere_radius: {b.sphere_radius:.1f}")
    log(f"    get_bounding_box().min: ({bb.min.x:.1f}, {bb.min.y:.1f}, {bb.min.z:.1f})")
    log(f"    get_bounding_box().max: ({bb.max.x:.1f}, {bb.max.y:.1f}, {bb.max.z:.1f})")

# Also check level + actor count
unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")
all_actors = unreal.EditorActorSubsystem().get_all_level_actors()
log(f"  level actors: {len(all_actors)}")
# Get the Cell_860201AD actor's component bounds
spawn = next((a for a in all_actors if a.get_actor_label() == "Cell_860201AD"), None)
if spawn:
    smc = spawn.static_mesh_component
    log(f"  Cell_860201AD actor location: {spawn.get_actor_location()}")
    log(f"  Cell_860201AD component bounds: {smc.bounds}")
