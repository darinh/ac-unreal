# =====================================================================
# brighten_academy.py
#
# Diagnosis: indoor academy + ceilings block SkyLight/Sun + extracted
# PointLight intensities are tiny + auto-exposure can't adapt to a
# scene with no bright pixels = pure black indoors.
#
# Fix in 3 parts:
#   1. Crank PointLight intensities 10x and triple the attenuation
#      radius so they actually illuminate the rooms they're in.
#   2. Switch the PostProcessVolume to MANUAL exposure (instead of
#      auto-histogram) at a bright bias so we always see SOMETHING.
#      Auto-exposure is preferable long-term but it's gaslighting us
#      right now.
#   3. Drop a high-intensity SkyLight intensity boost for the few
#      cells that have openings to the sky (atrium / courtyard).
# =====================================================================

import sys
import unreal


def log(m): unreal.log(f"[bright] {m}")


LEVEL = "/Game/Academy/Maps/AcademyMap"


def main():
    log(f"loading level: {LEVEL}")
    unreal.EditorLevelLibrary.load_level(LEVEL)
    eas = unreal.EditorActorSubsystem()
    actors = eas.get_all_level_actors()

    # 1) PointLights — crank intensity + attenuation.
    pls = [a for a in actors if isinstance(a, unreal.PointLight)]
    for pl in pls:
        lc = pl.get_editor_property("light_component")
        if lc is None:
            continue
        # 10x intensity (we previously set ~2500; AC's intensity scalar
        # was tiny so we under-scaled).
        cur_i = lc.get_editor_property("intensity")
        lc.set_editor_property("intensity", cur_i * 10.0)
        # Triple the attenuation radius (AC falloff values are small;
        # original was *100 from metres which gave ~500cm; want ~1500cm).
        cur_atten = lc.get_editor_property("attenuation_radius")
        lc.set_editor_property("attenuation_radius", max(cur_atten * 3.0, 800.0))
        # Source radius gives a soft falloff (less hard hot-spot at the
        # light origin) — better for indoor cosmetic lighting.
        lc.set_editor_property("source_radius", 5.0)
    log(f"  bumped {len(pls)} PointLights: intensity x10, attenuation_radius x3 (min 800cm)")

    # 2) PostProcessVolume — switch to MANUAL exposure.
    ppvs = [a for a in actors if isinstance(a, unreal.PostProcessVolume)]
    for ppv in ppvs:
        settings = ppv.get_editor_property("settings")
        # Manual exposure at a bright value (lower EV = brighter scene).
        settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
        settings.set_editor_property("override_auto_exposure_method", True)
        # ManualExposure key (the property is actually 'auto_exposure_bias'
        # in UE 5.x; UE applies it regardless of method).
        # Also force a very low manual exposure (= bright result).
        try:
            settings.set_editor_property("auto_exposure_bias", 5.0)
            settings.set_editor_property("override_auto_exposure_bias", True)
        except Exception:
            pass
        # Indirect lighting amplifier (cranked).
        settings.set_editor_property("indirect_lighting_intensity", 5.0)
        settings.set_editor_property("override_indirect_lighting_intensity", True)
        ppv.set_editor_property("settings", settings)
    log(f"  PPV: manual exposure +5.0 EV, IndirectLightingIntensity=5.0 on {len(ppvs)} volumes")

    # 3) SkyLight — bump intensity for outside-facing rooms.
    sls = [a for a in actors if isinstance(a, unreal.SkyLight)]
    for sl in sls:
        lc = sl.get_editor_property("light_component")
        if lc is None:
            continue
        lc.set_editor_property("intensity", 10.0)
        log(f"  {sl.get_actor_label()}: intensity = 10.0")

    unreal.EditorLevelLibrary.save_current_level()
    log("DONE. Reopen the level — should be much brighter.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
