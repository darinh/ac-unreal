"""Re-add SkyAtmosphere + DirectionalLight as atmosphere sun, then
have SkyLight real-time-capture the BLUE SKY (not the pink-tinted
underground extinction). This is the standard UE5 'daylight' rig."""

import unreal

unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")
eas = unreal.EditorActorSubsystem()

# 1. Remove any existing SkyAtmosphere first (we deleted one earlier; this
#    handles re-runs idempotently).
for a in list(eas.get_all_level_actors()):
    if isinstance(a, unreal.SkyAtmosphere):
        unreal.EditorLevelLibrary.destroy_actor(a)

# 2. Spawn fresh SkyAtmosphere
atm = eas.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
atm.set_actor_label("AcAtmosphere")
unreal.log(f"[sky-rig] spawned SkyAtmosphere")

# 3. DirectionalLight: atmosphere sun, intensity tuned for AC dungeon look.
#    Pitch around -45 (sun half above horizon).
for dl in [a for a in eas.get_all_level_actors() if isinstance(a, unreal.DirectionalLight)]:
    c = dl.light_component
    c.set_editor_property("intensity", 10.0)
    c.set_editor_property("atmosphere_sun_light", True)
    dl.set_actor_rotation(unreal.Rotator(roll=0, pitch=-45, yaw=45), False)
    unreal.log(f"[sky-rig] DirectionalLight: 10 lux, atmosphere sun, pitch -45")

# 4. SkyLight: CAPTURED_SCENE (will sample the SkyAtmosphere we just spawned).
for sl in [a for a in eas.get_all_level_actors() if isinstance(a, unreal.SkyLight)]:
    c = sl.light_component
    c.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
    c.set_editor_property("real_time_capture", True)
    c.set_editor_property("intensity", 5.0)
    c.set_editor_property("lower_hemisphere_is_black", False)  # let bottom contribute
    c.set_editor_property("lower_hemisphere_color", unreal.LinearColor(0.3, 0.3, 0.35, 1.0))  # subtle bluish floor bounce
    unreal.log(f"[sky-rig] SkyLight: captured-scene real-time, intensity 5, lower_hemi bluish")

# 5. PPV: histogram auto-exposure tuned for indoor dim->bright.
for ppv in [a for a in eas.get_all_level_actors() if isinstance(a, unreal.PostProcessVolume)]:
    s = ppv.settings
    s.override_auto_exposure_method = True
    s.auto_exposure_method = unreal.AutoExposureMethod.AEM_HISTOGRAM
    s.override_auto_exposure_bias = True
    s.auto_exposure_bias = 2.0
    s.override_auto_exposure_min_brightness = True
    s.auto_exposure_min_brightness = 0.03
    s.override_auto_exposure_max_brightness = True
    s.auto_exposure_max_brightness = 2.0
    s.override_indirect_lighting_intensity = True
    s.indirect_lighting_intensity = 4.0
    ppv.settings = s
    unreal.log(f"[sky-rig] PPV: histogram exposure 0.03..2, bias +2 EV, indirect 4x")

unreal.EditorLevelLibrary.save_current_level()
unreal.log("[sky-rig] DONE, saved")
