# =====================================================================
# import_lights.py
#
# Phase 5g + 5h: extract per-setup lights and spawn them in UE.
#
# 5g — for each entry in the academy lights JSON, spawn a PointLight
#      (or SpotLight, if ConeAngle > 0) at the world-space position,
#      coloring it from the LightInfo.Color uint and scaling its
#      intensity from LightInfo.Intensity * LightInfo.Falloff.
#
# 5h — for lights tagged is_warm_for_fire_fx (red-dominant, saturated,
#      bright), add an Unreal actor tag "FireFlicker" so a downstream
#      Blueprint or sequencer can find and animate them, and also spawn
#      a small emissive cube as a stand-in for visible flame geometry.
#      Full Niagara parity is Phase 5h-followup once we have a
#      hand-authored NS_Fire system in /Game/Academy/FX/.
#
# Inputs:
#   AC_LIGHTS_JSON   pipeline/dat-extract/samples/academy_8602_lights.json
# Run:
#   pwsh pipeline\ue-import\run_lights_import.ps1
# =====================================================================

import unreal
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

LIGHTS_JSON = os.environ.get(
    "AC_LIGHTS_JSON",
    str(REPO_ROOT / "pipeline" / "dat-extract" / "samples" / "academy_8602_lights.json"),
)

LEVEL_PATH = "/Game/Academy/Maps/AcademyMap"
FIRE_FLICKER_TAG = unreal.Name("FireFlicker")


def log(msg):
    unreal.log(f"[lights] {msg}")


def main():
    p = Path(LIGHTS_JSON)
    if not p.exists():
        unreal.log_error(f"Lights JSON not found: {p}")
        return 1
    data = json.loads(p.read_text(encoding="utf-8"))
    log(f"loaded {data['light_count']} lights ({data['warm_light_count']} warm)")

    if not unreal.EditorAssetLibrary.does_asset_exist(LEVEL_PATH):
        unreal.log_error(f"Level {LEVEL_PATH} doesn't exist — run import_academy.py first.")
        return 2
    unreal.EditorLevelLibrary.load_level(LEVEL_PATH)

    eas = unreal.EditorActorSubsystem()

    # 1) Clean any lights spawned by prior runs (label prefix Light_).
    existing = [a for a in eas.get_all_level_actors()
                if a.get_actor_label().startswith("Light_") or a.get_actor_label().startswith("FireMesh_")]
    if existing:
        log(f"deleting {len(existing)} prior light/firemesh actors")
        for a in existing:
            eas.destroy_actor(a)

    # 2) Spawn lights.
    point_count = 0
    spot_count = 0
    fire_count = 0
    t0 = time.time()
    for i, L in enumerate(data["lights"]):
        pos = L["position"]
        loc = unreal.Vector(float(pos["x"]), float(pos["y"]), float(pos["z"]))
        rot = unreal.Rotator(0, 0, 0)

        is_point = bool(L.get("is_point_light", True))
        light_class = unreal.PointLight if is_point else unreal.SpotLight
        actor = eas.spawn_actor_from_class(light_class, loc, rot)
        if actor is None:
            continue

        c = L["color_rgb"]
        # AC's per-light Intensity is a flat 100 for every academy light
        # (the dat stores a constant; real brightness is driven by Falloff/
        # radius + the surface's own Luminosity). So scaling that constant is
        # just a global brightness knob. A UNITLESS UE intensity around a few
        # thousand reads like an indoor torch, so the default multiplier maps
        # AC-100 -> ~3000. Override with AC_LIGHT_MULT to retune without
        # re-extracting. (Was a flat *2500 = 250000, which is ~50x too hot now
        # that the 2x-coord bug is fixed and the lights actually sit inside the
        # cells they light.)
        light_mult = float(os.environ.get("AC_LIGHT_MULT", "30.0"))
        ac_intensity = max(float(L.get("intensity", 1.0)), 0.01)
        ac_falloff_m = max(float(L.get("falloff", 5.0)), 0.5)
        ue_intensity = ac_intensity * light_mult
        ue_attenuation_cm = ac_falloff_m * 100.0

        lc = actor.get_editor_property("light_component")
        lc.set_editor_property("intensity", float(ue_intensity))
        lc.set_editor_property("light_color", unreal.Color(
            int(round(c["r"] * 255)),
            int(round(c["g"] * 255)),
            int(round(c["b"] * 255)),
            255))
        lc.set_editor_property("attenuation_radius", float(ue_attenuation_cm))
        lc.set_editor_property("intensity_units", unreal.LightUnits.UNITLESS)
        lc.set_editor_property("cast_shadows", True)
        lc.set_editor_property("affects_world", True)

        if not is_point:
            cone_deg = float(L.get("cone_angle_degrees", 30.0))
            lc.set_editor_property("inner_cone_angle", max(cone_deg * 0.5, 1.0))
            lc.set_editor_property("outer_cone_angle", max(cone_deg, 5.0))
            spot_count += 1
        else:
            point_count += 1

        label_base = f"Light_{L['cell_id'][2:]}_{L['setup_id'][2:]}_{i:04d}"
        actor.set_actor_label(label_base)
        actor.set_folder_path("Academy/Lights")

        # 5h: warm lights get a FireFlicker tag + a small placeholder
        # cube. The actual animation is driven by a single
        # AAcAcademyFireManager actor (spawned at the end of this script)
        # which scans for this tag on BeginPlay and modulates each
        # tagged light's PointLightComponent intensity each frame.
        if L.get("is_warm_for_fire_fx", False):
            actor.tags = [FIRE_FLICKER_TAG]
            lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)

            cube_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube")
            if cube_mesh is not None:
                cube = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
                if cube is not None:
                    cube.set_actor_label(f"FireMesh_{label_base[6:]}")
                    cube.static_mesh_component.set_static_mesh(cube_mesh)
                    cube.set_actor_scale3d(unreal.Vector(0.1, 0.1, 0.15))
                    cube.set_folder_path("Academy/FireMeshes")
                    cube.tags = [FIRE_FLICKER_TAG]
            fire_count += 1

        if (i + 1) % 32 == 0:
            log(f"  spawned {i+1}/{data['light_count']} lights ({time.time() - t0:.1f}s)")

    log(f"lights done: {point_count} point, {spot_count} spot, {fire_count} flagged FireFlicker"
        f" ({time.time() - t0:.1f}s)")

    # Spawn (or re-use) the single AAcAcademyFireManager that drives the
    # FireFlicker animations at runtime.
    existing_mgr = [a for a in eas.get_all_level_actors()
                    if a.get_actor_label() == "AcAcademyFireManager"]
    for a in existing_mgr:
        eas.destroy_actor(a)

    fm_class = unreal.load_class(None, "/Script/AcUnreal.AcAcademyFireManager")
    if fm_class is not None:
        mgr = eas.spawn_actor_from_class(fm_class, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        if mgr is not None:
            mgr.set_actor_label("AcAcademyFireManager")
            mgr.set_folder_path("Academy/Lighting")
            log("spawned AcAcademyFireManager (animates FireFlicker-tagged lights at runtime)")
    else:
        unreal.log_warning("AcAcademyFireManager class not found — fire animation will not run."
                            " Rebuild the AcUnrealEditor target and re-run.")

    unreal.EditorLevelLibrary.save_current_level()
    log("DONE. level saved.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
