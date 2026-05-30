"""Aggressive lighting overhaul. We've been chasing diagnostic
rabbit holes; let's just FORCE brightness.

Plan:
  1. Delete SkyAtmosphere (it's likely darkening below-Z=0 cells).
  2. Replace SkyLight with a SPECIFIED-cubemap-equivalent fixed ambient
     (high constant intensity, no real-time capture).
  3. Crank DirectionalLight to a high intensity, point straight down
     so EVERY cell receives some direct light.
  4. PostProcessVolume manual exposure 0 (no boost — high direct light
     should be enough).

If THIS doesn't make the academy bright, the issue is cell visibility,
not lighting tuning.
"""

import unreal


def log(m): unreal.log(f"[brute-light] {m}")


unreal.EditorLevelLibrary.load_level("/Game/Academy/Maps/AcademyMap")
eas = unreal.EditorActorSubsystem()
all_actors = eas.get_all_level_actors()
log(f"loaded with {len(all_actors)} actors")

# 1. Delete SkyAtmosphere — its planet-ground extinction may be killing
#    everything below world Z=0 (most of our academy is at Z=-1200..0).
removed_atm = 0
for a in all_actors:
    if isinstance(a, unreal.SkyAtmosphere):
        unreal.EditorLevelLibrary.destroy_actor(a)
        removed_atm += 1
log(f"removed {removed_atm} SkyAtmosphere actor(s)")

# 2. Beef up SkyLight: source_type CUBEMAP with high intensity, no
#    real-time capture (the captured scene is dark indoor environment).
for sl in [a for a in all_actors if isinstance(a, unreal.SkyLight)]:
    c = sl.light_component
    c.real_time_capture = False
    c.intensity = 50.0  # was 10
    c.light_color = unreal.LinearColor(1.0, 0.95, 0.85, 1.0)  # warm white
    log(f"  SkyLight: intensity=50, real_time_capture=False, warm white")

# 3. DirectionalLight: HIGH intensity, straight down. Indoor scenes
#    normally don't see sun, but for diagnostic purposes we want every
#    upward-facing surface lit.
for dl in [a for a in all_actors if isinstance(a, unreal.DirectionalLight)]:
    c = dl.light_component
    c.intensity = 30.0  # was 5; way brighter sun
    c.light_color = unreal.LinearColor(1.0, 1.0, 1.0, 1.0)
    dl.set_actor_rotation(unreal.Rotator(roll=0, pitch=-90, yaw=0), False)  # straight down
    c.atmosphere_sun_light = False  # no longer relevant (atm deleted)
    log(f"  DirectionalLight: intensity=30, pointing straight down")

# 4. PostProcessVolume: set auto-exposure to a sensible auto-histogram
#    with reasonable min/max. The manual +5 EV was fighting against
#    real darkness; with brighter lights we shouldn't need it.
for ppv in [a for a in all_actors if isinstance(a, unreal.PostProcessVolume)]:
    s = ppv.settings
    s.override_auto_exposure_method = True
    s.auto_exposure_method = unreal.AutoExposureMethod.AEM_HISTOGRAM
    s.override_auto_exposure_bias = True
    s.auto_exposure_bias = 1.0  # mild positive bias
    s.override_auto_exposure_min_brightness = True
    s.auto_exposure_min_brightness = 0.1
    s.override_auto_exposure_max_brightness = True
    s.auto_exposure_max_brightness = 2.0
    s.override_indirect_lighting_intensity = True
    s.indirect_lighting_intensity = 3.0
    ppv.settings = s
    log(f"  PPV: histogram exposure 0.1..2.0, bias +1, indirect 3x")

unreal.EditorLevelLibrary.save_current_level()
log("DONE. level saved.")
