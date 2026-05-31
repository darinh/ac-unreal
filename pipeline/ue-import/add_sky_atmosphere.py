# =====================================================================
# add_sky_atmosphere.py
#
# UE warning on AcademyMap:
#   "A sky light with real-time capture enable is in the scene. It
#    requires at least a SkyAtmosphere component, a VolumetricCloud
#    component or a mesh with a material tagged as IsSky. Otherwise
#    it will be black."
#
# Our SkyLight has nothing to capture because the academy is a
# self-contained indoor map with no sky source. Fix: add a
# SkyAtmosphere actor. The atmosphere provides procedural sky
# colour that the SkyLight can capture, which Lumen then bounces
# into indoor cells via GI.
#
# Idempotent: re-running won't double-spawn.
# =====================================================================

import sys
import unreal


def log(m): unreal.log(f"[sky] {m}")


LEVEL = "/Game/Academy/Maps/AcademyMap"


def main():
    log(f"loading level: {LEVEL}")
    unreal.EditorLevelLibrary.load_level(LEVEL)
    eas = unreal.EditorActorSubsystem()
    actors = eas.get_all_level_actors()

    # 1) Spawn SkyAtmosphere if not already present.
    existing_atmo = [a for a in actors if isinstance(a, unreal.SkyAtmosphere)]
    if existing_atmo:
        log(f"  SkyAtmosphere already present ({len(existing_atmo)}); skipping spawn")
    else:
        atmo = eas.spawn_actor_from_class(
            unreal.SkyAtmosphere,
            unreal.Vector(0, 0, 0),
            unreal.Rotator(0, 0, 0))
        if atmo is None:
            unreal.log_error("spawn_actor_from_class(SkyAtmosphere) returned None")
            return 1
        atmo.set_actor_label("AcademySkyAtmosphere")
        atmo.set_folder_path("Academy/Lighting")
        log("  spawned SkyAtmosphere at world origin")

    # 2) Make sure the DirectionalLight is set as "Atmosphere Sun Light"
    #    so it drives the atmospheric scattering colour (sun disc + sky tint).
    dir_lights = [a for a in actors if isinstance(a, unreal.DirectionalLight)]
    for dl in dir_lights:
        lc = dl.get_editor_property("light_component")
        if lc is None:
            continue
        # bAtmosphereSunLight + AtmosphereSunLightIndex=0 marks this as
        # THE sun for the SkyAtmosphere component to use.
        try:
            lc.set_editor_property("atmosphere_sun_light", True)
            lc.set_editor_property("atmosphere_sun_light_index", 0)
            log(f"  {dl.get_actor_label()}: atmosphere_sun_light=ON")
        except Exception as e:
            unreal.log_warning(f"  couldn't set atmosphere sun-light props on "
                                f"{dl.get_actor_label()}: {e}")

    # 3) Quick sanity check on the SkyLight — confirm it's still set the
    #    way restore_lighting.py left it.
    sky_lights = [a for a in actors if isinstance(a, unreal.SkyLight)]
    for sl in sky_lights:
        lc = sl.get_editor_property("light_component")
        if lc is None:
            continue
        if not lc.get_editor_property("real_time_capture"):
            log(f"  {sl.get_actor_label()}: real_time_capture was OFF, re-enabling")
            lc.set_editor_property("real_time_capture", True)
            lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)

    unreal.EditorLevelLibrary.save_current_level()
    log("DONE. Reopen the level — SkyAtmosphere now feeds the SkyLight.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
