"""Set SkyLight to a constant WHITE ambient (not a cached pink cubemap).
Crank to give the academy bright neutral interior lighting."""
import unreal

unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")
eas = unreal.EditorActorSubsystem()

ppvs = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.PostProcessVolume)]
for ppv in ppvs:
    s = ppv.settings
    s.override_auto_exposure_bias = True
    s.auto_exposure_bias = 5.0
    s.override_auto_exposure_method = True
    s.auto_exposure_method = unreal.AutoExposureMethod.AEM_MANUAL
    s.override_indirect_lighting_intensity = True
    s.indirect_lighting_intensity = 3.0
    ppv.settings = s
    unreal.log(f"[white-sky] PPV bias=+5 EV, manual, indirect 3x")

# SkyLight: SLS_SPECIFIED_CUBEMAP with no cubemap -> defaults to white
sks = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.SkyLight)]
for sl in sks:
    c = sl.light_component
    c.set_editor_property("real_time_capture", False)
    c.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    c.set_editor_property("cubemap", None)
    c.set_editor_property("intensity", 10.0)
    c.set_editor_property("light_color", unreal.Color(255, 255, 255, 255))
    unreal.log(f"[white-sky] SkyLight: specified-cubemap, no cubemap (white), intensity 10")

# DirectionalLight: bright sun pointing down at 60deg
dls = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.DirectionalLight)]
for dl in dls:
    c = dl.light_component
    c.set_editor_property("intensity", 10.0)
    c.set_editor_property("light_color", unreal.Color(255, 252, 240, 255))
    dl.set_actor_rotation(unreal.Rotator(roll=0, pitch=-60, yaw=45), False)
    unreal.log(f"[white-sky] DirectionalLight: intensity 10, warm-white, pitch -60")

unreal.EditorLevelLibrary.save_current_level()
unreal.log("[white-sky] DONE")
