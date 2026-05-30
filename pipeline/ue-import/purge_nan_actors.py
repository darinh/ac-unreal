"""Detect StaticMeshActors that reference meshes with NaN/Inf bounds
and DELETE them. UE's renderer asserts on these and the asserts can
silently break lighting calculations for the rest of the scene.

We lose props (chest, NPC, doors) but gain a clean scene where lights
actually work. Props can be re-imported later after fixing the C#
extractor's coord bug + adding proper bounds computation."""

import math
import unreal


def log(m): unreal.log(f"[purge-nan] {m}")


unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")
eas = unreal.EditorActorSubsystem()

actors = eas.get_all_level_actors()
log(f"loaded {len(actors)} actors")

# Build a set of mesh paths with bad bounds.
bad_meshes = set()
checked = 0
for a in actors:
    if not isinstance(a, unreal.StaticMeshActor):
        continue
    smc = a.static_mesh_component
    if smc is None: continue
    sm = smc.static_mesh
    if sm is None: continue
    path = sm.get_path_name()
    if path in bad_meshes:
        continue  # already known bad; skip re-check
    try:
        b = sm.get_bounds()
        ex = b.box_extent
        sr = b.sphere_radius
        bad = (
            math.isnan(ex.x) or math.isnan(ex.y) or math.isnan(ex.z) or
            math.isinf(ex.x) or math.isinf(ex.y) or math.isinf(ex.z) or
            math.isnan(sr) or math.isinf(sr) or
            # Huge bounds (e.g. > 1e10) are also corrupt
            abs(ex.x) > 1e10 or abs(ex.y) > 1e10 or abs(ex.z) > 1e10
        )
        if bad:
            bad_meshes.add(path)
    except Exception as e:
        bad_meshes.add(path)
    checked += 1
log(f"checked {checked} actors, found {len(bad_meshes)} unique meshes with bad bounds")

# Delete every actor referencing a bad-bounds mesh.
deleted = 0
for a in list(eas.get_all_level_actors()):
    if not isinstance(a, unreal.StaticMeshActor):
        continue
    smc = a.static_mesh_component
    if smc is None: continue
    sm = smc.static_mesh
    if sm is None: continue
    if sm.get_path_name() in bad_meshes:
        try:
            label = a.get_actor_label()
        except Exception:
            label = "<?>"
        unreal.EditorLevelLibrary.destroy_actor(a)
        deleted += 1
log(f"deleted {deleted} actors with NaN/Inf bounds")

unreal.EditorLevelLibrary.save_current_level()
log("level saved")
