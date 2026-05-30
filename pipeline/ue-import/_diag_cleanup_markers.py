"""Remove the diagnostic sphere/cubes so they don't block view of the academy."""
import unreal

unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")
eas = unreal.EditorActorSubsystem()
removed = 0
for a in list(eas.get_all_level_actors()):
    try:
        label = a.get_actor_label()
    except Exception:
        continue
    if label.startswith("DiagSphere") or label.startswith("DiagCube"):
        unreal.EditorLevelLibrary.destroy_actor(a)
        removed += 1
unreal.log(f"[cleanup] removed {removed} diagnostic markers")
unreal.EditorLevelLibrary.save_current_level()
