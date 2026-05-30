# =====================================================================
# restore_lighting.py
#
# After the crash investigation we disabled aggressively:
#   - shadows on all 132 PointLights (HARMLESS to keep off for perf;
#     leaving disabled)
#   - SkyLight real_time_capture (this was a MAJOR hit to indoor
#     ambient — restoring)
#   - SkyLight intensity left at 1.0 (default; bumping to 3.0 for
#     better indoor ambient with no other bounce sources)
#
# The crash was caused by Nanite (commit 9401f9b) — confirmed by the
# user successfully loading AcademyMap after we disabled it. So we
# can safely restore the lighting changes that were collateral damage.
#
# What we DON'T re-enable here:
#   - Nanite (root cause; stays off until we add a Nanite-safety pass
#     to the Python mesh build pipeline)
#   - HW Ray Tracing (incidentally disabled; was not the cause but
#     leaving off as it was the cumulative-but-unnecessary change)
#   - PointLight shadows (132 of them; would be very expensive
#     without solving the actual GI problem)
# =====================================================================

import sys
import unreal


def log(m): unreal.log(f"[restorelight] {m}")


LEVEL = "/Game/Academy/Maps/AcademyMap"


def main():
    log(f"loading level: {LEVEL}")
    unreal.EditorLevelLibrary.load_level(LEVEL)
    eas = unreal.EditorActorSubsystem()
    actors = eas.get_all_level_actors()

    # 1) SkyLight: re-enable real_time_capture + bump intensity.
    sky_lights = [a for a in actors if isinstance(a, unreal.SkyLight)]
    for sl in sky_lights:
        lc = sl.get_editor_property("light_component")
        if lc is None:
            continue
        lc.set_editor_property("real_time_capture", True)
        lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)  # required for real-time
        lc.set_editor_property("intensity", 3.0)
        log(f"  {sl.get_actor_label()}: real_time_capture=ON, mobility=Movable, intensity=3.0")

    # 2) DirectionalLight: ensure it's bright enough for indoor bounce.
    dir_lights = [a for a in actors if isinstance(a, unreal.DirectionalLight)]
    for dl in dir_lights:
        lc = dl.get_editor_property("light_component")
        if lc is None:
            continue
        cur_intensity = lc.get_editor_property("intensity")
        if cur_intensity < 5.0:
            lc.set_editor_property("intensity", 5.0)
            log(f"  {dl.get_actor_label()}: intensity {cur_intensity} -> 5.0")

    # 3) Add a small ambient fill via the PostProcessVolume.
    ppvs = [a for a in actors if isinstance(a, unreal.PostProcessVolume)]
    for ppv in ppvs:
        settings = ppv.get_editor_property("settings")
        # Indirect Lighting Intensity boost (Lumen GI amplifier).
        settings.set_editor_property("indirect_lighting_intensity", 2.5)
        settings.set_editor_property("override_indirect_lighting_intensity", True)
        # Auto-exposure compensation up a bit so dark rooms aren't crushed.
        settings.set_editor_property("auto_exposure_bias", 1.5)
        settings.set_editor_property("override_auto_exposure_bias", True)
        ppv.set_editor_property("settings", settings)
        log(f"  {ppv.get_actor_label()}: IndirectLightingIntensity=2.5, AutoExpBias=+1.5")

    unreal.EditorLevelLibrary.save_current_level()
    log("DONE. Reopen the level or hit Play — should be much brighter inside.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
