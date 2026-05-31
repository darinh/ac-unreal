# =====================================================================
# move_player_start.py
#
# Updates the PlayerStart actor's location/rotation in AcademyMap so
# the next -game launch's HighResShot captures from a chosen viewpoint.
#
# **History note (2026-05-30)**: this script was briefly suspected of
# wiping 1487 academy actors during a mid-render-iteration debug
# session. The actual cause was a separate diagnostic script that
# forgot to call ``load_level()`` before ``get_all_level_actors()`` —
# in commandlet mode the editor world is empty until you explicitly
# load a level. Once the diag was fixed, the actors were all still
# present. move_player_start.py itself is safe in commandlet mode
# because (a) it loads the level first, (b) it only mutates existing
# PlayerStart actors (or spawns ONE if missing), and (c) it calls
# ``save_current_level()`` which preserves all loaded actors.
#
# Args via env vars (powershell sets these before running this script):
#   AC_VP_X, AC_VP_Y, AC_VP_Z  — location in UE world coords (cm)
#   AC_VP_PITCH, AC_VP_YAW, AC_VP_ROLL — rotation in degrees
#
# Idempotent: looks up the first PlayerStart actor in the level and
# mutates it in place; if none exists, spawns one.
# =====================================================================

import os
import sys
import unreal


def log(m): unreal.log(f"[move-ps] {m}")
def warn(m): unreal.log_warning(f"[move-ps] {m}")


LEVEL_PATH = os.environ.get("AC_LEVEL", "/Game/Academy/Maps/AcademyMap")


def main():
    try:
        x = float(os.environ["AC_VP_X"])
        y = float(os.environ["AC_VP_Y"])
        z = float(os.environ["AC_VP_Z"])
        pitch = float(os.environ.get("AC_VP_PITCH", "0"))
        yaw = float(os.environ.get("AC_VP_YAW", "0"))
        roll = float(os.environ.get("AC_VP_ROLL", "0"))
    except KeyError as e:
        unreal.log_error(f"missing env var: {e}")
        return 1
    except ValueError as e:
        unreal.log_error(f"bad env var value: {e}")
        return 1

    unreal.EditorLevelLibrary.load_level(LEVEL_PATH)
    eas = unreal.EditorActorSubsystem()
    all_actors = eas.get_all_level_actors()
    log(f"loaded level with {len(all_actors)} actors")
    ps = next((a for a in all_actors if isinstance(a, unreal.PlayerStart)), None)
    if ps is None:
        log("no PlayerStart in level — spawning new one")
        ps = eas.spawn_actor_from_class(
            unreal.PlayerStart,
            unreal.Vector(x, y, z),
            unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw))
        if ps is None:
            unreal.log_error("failed to spawn PlayerStart")
            return 2
    else:
        old_loc = ps.get_actor_location()
        old_rot = ps.get_actor_rotation()
        ps.set_actor_location(unreal.Vector(x, y, z), False, False)
        ps.set_actor_rotation(unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw), False)
        log(f"moved PlayerStart from {old_loc} {old_rot} -> ({x},{y},{z}) pitch={pitch} yaw={yaw}")

    # Save the level so the change persists into -game mode.
    unreal.EditorLevelLibrary.save_current_level()
    log("level saved")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
