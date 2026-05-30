# =====================================================================
# add_player_start.py
#
# Adds a PlayerStart actor to AcademyMap at the canonical Aluvian
# Training Academy spawn position, so hitting Play drops you inside
# the academy rather than at world origin (where there is nothing).
#
# Spawn data (sourced from ACE-bots\Source\ACE.Entity\CharacterPositionExtensions.cs
# and confirmed by the user agent):
#   Cell:     0x860201AD  (the academy spawn cell — the room where
#             new Aluvian characters land after character creation)
#   Local AC: pos=(12.32, -28.48, 0.005)  facing=(w=-0.34, x=0, y=0, z=-0.94)
#
# We compose with the cell's world frame from the layout JSON, then apply
# the standard AC→UE transform (X↔Y swap + cm scale, plus the quaternion
# (w, -y, -x, -z) basis-swap).
# =====================================================================

import unreal
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_JSON = REPO_ROOT / "pipeline" / "dat-extract" / "samples" / "academy_8602_layout.json"
LEVEL_PATH  = "/Game/Academy/Maps/AcademyMap"
SPAWN_CELL  = "0x860201AD"

# Cell-local AC-space spawn (from ACE.Entity.CharacterPositionExtensions:13-36)
LOCAL_POS_AC    = (12.32, -28.48, 0.005)         # (x, y, z) metres
LOCAL_ORIENT_AC = (0.0, 0.0, -0.94, -0.34)       # (x, y, z, w)


def log(m): unreal.log(f"[playerstart] {m}")


def quat_mul_ac(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (
        aw*bx + ax*bw + ay*bz - az*by,
        aw*by - ax*bz + ay*bw + az*bx,
        aw*bz + ax*by - ay*bx + az*bw,
        aw*bw - ax*bx - ay*by - az*bz,
    )


def rotate_ac_vec(q, v):
    qx, qy, qz, qw = q; vx, vy, vz = v
    tx = 2 * (qy * vz - qz * vy)
    ty = 2 * (qz * vx - qx * vz)
    tz = 2 * (qx * vy - qy * vx)
    return (
        vx + qw * tx + (qy * tz - qz * ty),
        vy + qw * ty + (qz * tx - qx * tz),
        vz + qw * tz + (qx * ty - qy * tx),
    )


def main():
    data = json.loads(LAYOUT_JSON.read_text(encoding="utf-8"))
    cell = next((c for c in data["cells"] if c["cell_id"].lower() == SPAWN_CELL.lower()), None)
    if cell is None:
        unreal.log_error(f"spawn cell {SPAWN_CELL} not in layout JSON")
        return 1

    # Reverse layout JSON's UE-space cell frame back into AC space so we
    # can compose with the cell-local spawn frame in AC, then re-transform.
    ue_pos = cell["position"]
    cell_pos_ac = (ue_pos["y"] / 100.0, ue_pos["x"] / 100.0, ue_pos["z"] / 100.0)
    ue_q = cell["orientation"]
    cell_orient_ac = (-ue_q["y"], -ue_q["x"], -ue_q["z"], ue_q["w"])

    # Compose stab.world = cell ⊕ local (AC space).
    rotated_local = rotate_ac_vec(cell_orient_ac, LOCAL_POS_AC)
    world_pos_ac = (cell_pos_ac[0] + rotated_local[0],
                     cell_pos_ac[1] + rotated_local[1],
                     cell_pos_ac[2] + rotated_local[2])
    world_orient_ac = quat_mul_ac(cell_orient_ac, LOCAL_ORIENT_AC)

    # AC -> UE.
    ue_x = world_pos_ac[1] * 100.0
    ue_y = world_pos_ac[0] * 100.0
    # +90cm so the player capsule's pivot (root) sits at floor level
    # plus half-height (UE Character default capsule half-height = 88cm).
    ue_z = world_pos_ac[2] * 100.0 + 90.0
    ue_q_x = -world_orient_ac[1]
    ue_q_y = -world_orient_ac[0]
    ue_q_z = -world_orient_ac[2]
    ue_q_w =  world_orient_ac[3]

    log(f"spawn world pos (UE cm): ({ue_x:.2f}, {ue_y:.2f}, {ue_z:.2f})")
    log(f"spawn world rot (UE quat x,y,z,w): ({ue_q_x:.4f}, {ue_q_y:.4f}, {ue_q_z:.4f}, {ue_q_w:.4f})")

    if not unreal.EditorAssetLibrary.does_asset_exist(LEVEL_PATH):
        unreal.log_error(f"Level {LEVEL_PATH} doesn't exist — run import_academy.py first.")
        return 2
    unreal.EditorLevelLibrary.load_level(LEVEL_PATH)

    eas = unreal.EditorActorSubsystem()

    # Idempotent: kill prior PlayerStart actors we added.
    existing = [a for a in eas.get_all_level_actors()
                if a.get_actor_label() == "AcademyPlayerStart"]
    if existing:
        log(f"deleting {len(existing)} prior PlayerStart actor(s)")
        for a in existing:
            eas.destroy_actor(a)

    loc = unreal.Vector(ue_x, ue_y, ue_z)
    rot = unreal.Quat(ue_q_x, ue_q_y, ue_q_z, ue_q_w).rotator()
    actor = eas.spawn_actor_from_class(unreal.PlayerStart, loc, rot)
    if actor is None:
        unreal.log_error("spawn_actor_from_class(PlayerStart) returned None")
        return 3
    actor.set_actor_label("AcademyPlayerStart")
    actor.set_folder_path("Academy/PlayerStart")

    unreal.EditorLevelLibrary.save_current_level()
    log("DONE. level saved. Hit Play and you should spawn inside cell 0x860201AD.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main() or 0)
