"""Check current PlayerStart location."""
import unreal

unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")
ps_list = [a for a in unreal.EditorActorSubsystem().get_all_level_actors() if isinstance(a, unreal.PlayerStart)]
unreal.log(f"[ps] {len(ps_list)} PlayerStart actors")
for ps in ps_list:
    loc = ps.get_actor_location()
    rot = ps.get_actor_rotation()
    unreal.log(f"[ps]   {ps.get_actor_label()} at ({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f}) pitch={rot.pitch} yaw={rot.yaw}")
