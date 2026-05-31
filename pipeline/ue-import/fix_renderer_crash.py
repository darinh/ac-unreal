# =====================================================================
# fix_renderer_crash.py
#
# AcademyMap crashes on load with:
#   Assertion failed: IntFitsIn<OutType>(In)
#   File: Engine/Source/Runtime/Core/Public/Templates/UnrealTemplate.h:170
#   Callstack: UnrealEditor-Renderer.dll
#
# Most likely cause: 105 Movable PointLights with cast_shadows=True
# plus a real-time SkyLight + Lumen GI + Lumen Reflections + Hardware
# Ray Tracing = some renderer-side container (shadow atlas pages, RT
# instance buffer, Lumen surface cache, draw call list) overflows a
# narrow int when computing per-frame visibility.
#
# Fix: turn down the lighting cost without changing the LEVEL CONTENT:
#   - PointLights: cast_shadows=False on all of them
#                  (still illuminate — Lumen GI propagates the light)
#   - SkyLight: real_time_capture=False (use static cubemap, refreshed
#               manually if needed)
#   - DirectionalLight: cast_shadows=True kept (only one of these)
#
# Runs headlessly via UnrealEditor-Cmd -run=pythonscript so the
# Renderer doesn't actually render, no assertion fires, save succeeds.
# =====================================================================

import sys
import unreal


def log(m): unreal.log(f"[fixcrash] {m}")


LEVEL = "/Game/Academy/Maps/AcademyMap"


def main():
    log(f"loading level: {LEVEL}")
    unreal.EditorLevelLibrary.load_level(LEVEL)

    eas = unreal.EditorActorSubsystem()
    actors = eas.get_all_level_actors()

    point_lights = [a for a in actors if isinstance(a, unreal.PointLight)]
    spot_lights = [a for a in actors if isinstance(a, unreal.SpotLight)]
    sky_lights = [a for a in actors if isinstance(a, unreal.SkyLight)]
    directional = [a for a in actors if isinstance(a, unreal.DirectionalLight)]

    log(f"  found: {len(point_lights)} point + {len(spot_lights)} spot + "
        f"{len(sky_lights)} sky + {len(directional)} directional lights")

    # 1) Disable shadows on every point + spot light.
    n_disabled = 0
    for light in point_lights + spot_lights:
        lc = light.get_editor_property("light_component")
        if lc is None:
            continue
        if lc.get_editor_property("cast_shadows"):
            lc.set_editor_property("cast_shadows", False)
            n_disabled += 1
        # Also turn off translucent lighting contribution — extra cost
        # we don't need from 132 small fire lights.
        lc.set_editor_property("affect_translucent_lighting", False)
        # Mobility was Movable for warm lights (so AcAcademyFireManager
        # can pulse intensity). Drop to Stationary for the rest — they
        # don't need to update per frame. Stationary lights still
        # accept color/intensity changes between PIE sessions.
        is_fire = unreal.Name("FireFlicker") in (light.tags or [])
        if not is_fire:
            lc.set_editor_property("mobility", unreal.ComponentMobility.STATIONARY)
    log(f"  disabled shadows on {n_disabled} point/spot lights")

    # 2) SkyLight: disable real-time capture (most expensive setting).
    for sl in sky_lights:
        lc = sl.get_editor_property("light_component")
        if lc is None:
            continue
        if lc.get_editor_property("real_time_capture"):
            lc.set_editor_property("real_time_capture", False)
            log(f"  disabled real_time_capture on {sl.get_actor_label()}")
        # Make it stationary so it bakes once.
        lc.set_editor_property("mobility", unreal.ComponentMobility.STATIONARY)

    # 3) Leave the DirectionalLight as-is (only 1, providing main shadow).
    log(f"  left {len(directional)} directional light(s) untouched")

    unreal.EditorLevelLibrary.save_current_level()
    log("DONE. level saved. Try opening AcademyMap again.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
