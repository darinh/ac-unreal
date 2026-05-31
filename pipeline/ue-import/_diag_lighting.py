"""Diagnostic: dump the lighting state of AcademyMap.
What this tells us:
  - PostProcessVolume settings (exposure mode, bias, indirect lighting)
  - SkyLight intensity + real-time capture
  - DirectionalLight intensity + rotation
  - PointLight count + a sample of their intensity/attenuation
  - SkyAtmosphere existence
"""
import unreal


def log(m): unreal.log(f"[diag-lights] {m}")


LEVEL = "/Game/Academy/Maps/AcademyMap"
unreal.EditorLevelLibrary.load_level(LEVEL)

eas = unreal.EditorActorSubsystem()
actors = eas.get_all_level_actors()
log(f"loaded {LEVEL} with {len(actors)} actors")

ppvs = [a for a in actors if isinstance(a, unreal.PostProcessVolume)]
log(f"PostProcessVolumes: {len(ppvs)}")
for i, ppv in enumerate(ppvs):
    s = ppv.settings
    log(f"  PPV[{i}] enabled={ppv.enabled} unbound={ppv.unbound}")
    log(f"    AutoExposureMethod override={s.override_auto_exposure_method} value={s.auto_exposure_method}")
    log(f"    AutoExposureBias    override={s.override_auto_exposure_bias} value={s.auto_exposure_bias}")
    log(f"    IndirectLightingIntensity override={s.override_indirect_lighting_intensity} value={s.indirect_lighting_intensity}")
    log(f"    IndirectLightingColor override={s.override_indirect_lighting_color} value={s.indirect_lighting_color}")
    log(f"    AutoExposureMinBrightness override={s.override_auto_exposure_min_brightness} value={s.auto_exposure_min_brightness}")
    log(f"    AutoExposureMaxBrightness override={s.override_auto_exposure_max_brightness} value={s.auto_exposure_max_brightness}")

skylights = [a for a in actors if isinstance(a, unreal.SkyLight)]
log(f"SkyLights: {len(skylights)}")
for sl in skylights:
    c = sl.light_component
    log(f"  SkyLight intensity={c.intensity} real_time_capture={c.real_time_capture} source_type={c.source_type}")
    log(f"           mobility={sl.root_component.mobility}")

dirlights = [a for a in actors if isinstance(a, unreal.DirectionalLight)]
log(f"DirectionalLights: {len(dirlights)}")
for dl in dirlights:
    c = dl.light_component
    log(f"  DirectionalLight intensity={c.intensity} rotation={dl.get_actor_rotation()}")
    log(f"                   atmosphere_sun_light={c.atmosphere_sun_light} mobility={dl.root_component.mobility}")

points = [a for a in actors if isinstance(a, unreal.PointLight)]
log(f"PointLights: {len(points)}")
for i, pl in enumerate(points[:3]):
    c = pl.light_component
    log(f"  PointLight[{i}] intensity={c.intensity} attenuation_radius={c.attenuation_radius} casts_shadows={c.cast_shadows} mobility={pl.root_component.mobility}")
log(f"  ... (showing 3 of {len(points)})")

atmospheres = [a for a in actors if isinstance(a, unreal.SkyAtmosphere)]
log(f"SkyAtmospheres: {len(atmospheres)}")
