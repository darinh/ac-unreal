"""Crank the PostProcessVolume exposure to +15 EV (32,000x brighter).
If THAT doesn't make the academy visible, lighting isn't reaching it
at all — and we'd need to add direct light sources."""
import unreal

unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")
eas = unreal.EditorActorSubsystem()
ppvs = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.PostProcessVolume)]
for ppv in ppvs:
    s = ppv.settings
    s.override_auto_exposure_bias = True
    s.auto_exposure_bias = 15.0
    s.override_auto_exposure_method = True
    s.auto_exposure_method = unreal.AutoExposureMethod.AEM_MANUAL
    s.override_indirect_lighting_intensity = True
    s.indirect_lighting_intensity = 10.0
    ppv.settings = s
    unreal.log(f"[crank-exp] PPV bias=+15 EV, manual exposure, indirect 10x")
unreal.EditorLevelLibrary.save_current_level()

# Also crank SkyLight intensity via set_editor_property (worked before)
sks = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.SkyLight)]
for sl in sks:
    c = sl.light_component
    c.set_editor_property("intensity", 200.0)
    c.set_editor_property("real_time_capture", False)
    unreal.log(f"[crank-exp] SkyLight intensity=200, real_time_capture=False")

unreal.EditorLevelLibrary.save_current_level()
unreal.log("[crank-exp] DONE, saved")
