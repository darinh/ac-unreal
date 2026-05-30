# =====================================================================
# import_npcs.py
#
# Phase 5i: spawn placeholder actors for every landblock_instance
# extracted by pipeline/ace-world/extract_landblock_instances.py.
#
# These are the *interactive* entities (NPCs, doors that open, signs
# you can read, portals you can step into) — distinct from the 644
# decorative props in EnvCell.StaticObjects (Phase 5f), which are
# baked into the cell geometry.
#
# Visual placeholders by category (BasicShapes mesh + scale + tag):
#   npc      → cylinder, vertical, ~180cm tall (capsule-ish)
#   portal   → cube, larger, slowly rotating (cosmetic)
#   door     → cube, tall thin (200×40×200)
#   fixture  → cube, small (chest)
#   scenery  → cube, thin (sign/book)
#   weapon   → sphere, small
#   item     → sphere, very small
#   other    → cylinder, tiny
#
# Each placeholder gets:
#   - Actor label NPC_<wcid>_<guid> for World Outliner navigation
#   - Tags: ["AcInstance", "<wcid>", "<category>"]
#   - Optional WCID + display name printed via UTextRenderComponent
#     hovering above (interactivity hint — not the chat window).
#
# All placeholders use the default WorldGridMaterial. Phase 5j will
# replace npc-category placeholders with the actual SetupModel mesh.
# =====================================================================

import unreal
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

NPC_JSON = os.environ.get(
    "AC_NPC_JSON",
    str(REPO_ROOT / "pipeline" / "dat-extract" / "samples" / "academy_8602_npcs.json"),
)
# Same setups directory used by import_statics.py. NPC setups extracted by
# `acdat export-setup ...` land alongside the prop setups.
SETUPS_DIR = os.environ.get(
    "AC_SETUPS_DIR",
    str(REPO_ROOT / "pipeline" / "dat-extract" / "out" / "academy_8602_statics"),
)

LEVEL_PATH = "/Game/Academy/Maps/AcademyMap"

# Reuse the StaticMesh builder from import_statics.py — it parses OBJ
# files and creates SM_Setup_<hex> assets under /Game/Academy/Setups.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_statics import build_setup_mesh  # noqa: E402


def log(msg):
    unreal.log(f"[npcs] {msg}")


# Visual configuration per category for the *placeholder fallback*.
# When a real SetupModel mesh is available the placeholder is skipped.
CATEGORY_CONFIG = {
    "npc":     ("/Engine/BasicShapes/Cylinder", unreal.Vector(0.40, 0.40, 1.80), 90.0),
    "portal":  ("/Engine/BasicShapes/Cube",     unreal.Vector(1.50, 1.50, 2.00), 100.0),
    "door":    ("/Engine/BasicShapes/Cube",     unreal.Vector(0.10, 1.20, 2.20), 110.0),
    "fixture": ("/Engine/BasicShapes/Cube",     unreal.Vector(0.60, 0.60, 0.50), 25.0),
    "scenery": ("/Engine/BasicShapes/Cube",     unreal.Vector(0.05, 0.60, 0.80), 40.0),
    "weapon":  ("/Engine/BasicShapes/Sphere",   unreal.Vector(0.20, 0.20, 0.20), 50.0),
    "item":    ("/Engine/BasicShapes/Sphere",   unreal.Vector(0.10, 0.10, 0.10), 20.0),
    "other":   ("/Engine/BasicShapes/Cylinder", unreal.Vector(0.20, 0.20, 0.30), 15.0),
}


def main():
    p = Path(NPC_JSON)
    if not p.exists():
        unreal.log_error(f"NPC JSON not found: {p}")
        return 1
    data = json.loads(p.read_text(encoding="utf-8"))
    log(f"loaded {data['instance_count']} instances "
        f"({data['weenies_resolved']}/{data['weenies_resolved']+data['weenies_missing']} resolved)")

    if not unreal.EditorAssetLibrary.does_asset_exist(LEVEL_PATH):
        unreal.log_error(f"Level {LEVEL_PATH} doesn't exist — run import_academy.py first.")
        return 2
    unreal.EditorLevelLibrary.load_level(LEVEL_PATH)

    eas = unreal.EditorActorSubsystem()

    # 1) Clean prior runs.
    existing = [a for a in eas.get_all_level_actors()
                if a.get_actor_label().startswith("NPC_")]
    if existing:
        log(f"deleting {len(existing)} prior NPC actors")
        for a in existing:
            eas.destroy_actor(a)

    # Pre-load placeholder meshes once.
    placeholders = {}
    for cat, (path, *_rest) in CATEGORY_CONFIG.items():
        placeholders[cat] = unreal.EditorAssetLibrary.load_asset(path)

    # Build/cache one StaticMesh per unique Setup ID referenced by an NPC.
    # Sources from the OBJ files extracted by `acdat export-setup ...` into
    # SETUPS_DIR. Falls back to placeholder if the OBJ isn't on disk.
    setups_dir = Path(SETUPS_DIR)
    setup_mesh_cache = {}
    def get_real_mesh(setup_hex):
        if setup_hex in setup_mesh_cache:
            return setup_mesh_cache[setup_hex]
        clean = setup_hex[2:] if setup_hex.startswith("0x") else setup_hex
        obj_path = setups_dir / f"setup_{clean}.obj"
        if not obj_path.exists():
            setup_mesh_cache[setup_hex] = None
            return None
        sm = build_setup_mesh(obj_path, f"SM_Setup_{clean}")
        setup_mesh_cache[setup_hex] = sm
        return sm

    spawned_real = 0
    spawned_placeholder = 0
    by_category = {}
    t0 = time.time()
    for inst in data["instances"]:
        if "position" not in inst:
            continue
        cat = inst["category"]
        wcid = inst["wcid"]
        pos = inst["position"]
        q = inst["orientation"]

        # Try to get a real mesh first; falls back to placeholder.
        real_mesh = get_real_mesh(inst["setup_id"]) if inst.get("setup_id") else None
        use_real = real_mesh is not None

        if use_real:
            loc = unreal.Vector(float(pos["x"]), float(pos["y"]), float(pos["z"]))
            scale = unreal.Vector(1, 1, 1)
        else:
            cfg = CATEGORY_CONFIG.get(cat, CATEGORY_CONFIG["other"])
            real_mesh = placeholders.get(cat) or placeholders["other"]
            scale = cfg[1]
            z_off = cfg[2]
            loc = unreal.Vector(float(pos["x"]), float(pos["y"]),
                                float(pos["z"]) + float(z_off))

        rot = unreal.Quat(float(q["x"]), float(q["y"]),
                          float(q["z"]), float(q["w"])).rotator()

        actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
        if actor is None:
            continue
        actor.static_mesh_component.set_static_mesh(real_mesh)
        actor.set_actor_scale3d(scale)

        actor.tags = [
            unreal.Name("AcInstance"),
            unreal.Name(f"wcid:{wcid}"),
            unreal.Name(f"cat:{cat}"),
            unreal.Name(f"wtype:{inst['weenie_type_name']}"),
        ]
        if inst.get("class_name"):
            actor.tags.append(unreal.Name(f"class:{inst['class_name']}"))
        if use_real:
            actor.tags.append(unreal.Name("HasRealMesh"))

        kind = "real" if use_real else "placeholder"
        label = f"NPC_{wcid:05d}_{inst['guid']:08X}_{cat}_{kind}"
        actor.set_actor_label(label)
        actor.set_folder_path(f"Academy/Instances/{cat}")

        if use_real:
            spawned_real += 1
        else:
            spawned_placeholder += 1
        by_category[cat] = by_category.get(cat, 0) + 1

    log(f"spawned {spawned_real + spawned_placeholder} instances in {time.time()-t0:.1f}s")
    log(f"  real meshes:  {spawned_real}")
    log(f"  placeholders: {spawned_placeholder}")
    log(f"  by category:  {by_category}")

    unreal.EditorLevelLibrary.save_current_level()
    log("DONE. level saved.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
