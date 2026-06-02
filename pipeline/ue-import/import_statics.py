# =====================================================================
# import_statics.py
#
# Phase 5f: import EnvCell.StaticObjects ("Stab" list) — the props,
# furniture, fireplaces, signs, training dummies, lecterns. Reads a
# statics JSON produced by `acdat dump-academy-statics`, imports each
# unique setup OBJ as a StaticMesh, then spawns one StaticMeshActor
# per Stab instance at its world-space position/rotation.
#
# Idempotent: re-running won't duplicate assets or actors. Existing
# SM_Setup_* assets are reused; existing "Setup_*" labeled actors get
# deleted before re-spawning (so position fixes propagate).
#
# Inputs (env-var overrides supported):
#   AC_STATICS_JSON   pipeline/dat-extract/samples/academy_8602_statics.json
#   AC_SETUPS_DIR     pipeline/dat-extract/out/academy_8602_statics
#
# Run:
#   pwsh pipeline\ue-import\run_statics_import.ps1
# =====================================================================

import unreal
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

STATICS_JSON = os.environ.get(
    "AC_STATICS_JSON",
    str(REPO_ROOT / "pipeline" / "dat-extract" / "samples" / "academy_8602_statics.json"),
)
SETUPS_DIR = os.environ.get(
    "AC_SETUPS_DIR",
    str(REPO_ROOT / "pipeline" / "dat-extract" / "out" / "academy_8602_statics"),
)

SETUPS_PACKAGE = "/Game/Academy/Setups"
LEVEL_PATH     = "/Game/Academy/Maps/AcademyMap"


def log(msg):
    unreal.log(f"[statics] {msg}")


# Re-use the OBJ + MTL parsers from import_academy.py — same format.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_academy import parse_obj, parse_mtl  # noqa: E402


def _bounds_finite(sm) -> bool:
    """A StaticMesh with NaN / Inf / ~1e48 bounds is frustum-culled by UE and
    renders invisible (the "no walls / collapsed prop" failure). `v == v` is
    False for NaN; `abs(v) < 1e7` rejects Inf and the ~3.7e48 garbage. Used as a
    build-time validation gate so corruption is caught at write time, not later
    by an audit."""
    bb = sm.get_bounding_box()
    vals = [bb.min.x, bb.min.y, bb.min.z, bb.max.x, bb.max.y, bb.max.z]
    return all(v == v and abs(v) < 1e7 for v in vals)


def build_setup_mesh(obj_path: Path, asset_name: str) -> unreal.StaticMesh:
    asset_path = f"{SETUPS_PACKAGE}/{asset_name}"
    # Stale-detection guard (review follow-up): only REUSE an existing asset if
    # its bounds are valid. Blindly returning a cached asset silently keeps
    # corrupt-bounds meshes alive across re-imports (the bug class behind the
    # collapsed props and the culled cell shells). A corrupt/stale existing
    # asset is deleted and rebuilt fresh below.
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        existing = unreal.EditorAssetLibrary.load_asset(asset_path)
        if existing is not None and _bounds_finite(existing):
            return existing
        unreal.EditorAssetLibrary.delete_asset(asset_path)

    unreal.EditorAssetLibrary.make_directory(SETUPS_PACKAGE)
    at = unreal.AssetToolsHelpers.get_asset_tools()
    sm = at.create_asset(
        asset_name=asset_name,
        package_path=SETUPS_PACKAGE,
        asset_class=unreal.StaticMesh,
        factory=None)
    if sm is None:
        return None

    obj_mesh = parse_obj(obj_path)
    desc = unreal.StaticMesh.create_static_mesh_description(sm)
    slot_names = []

    for surf_idx, grp in enumerate(obj_mesh.groups):
        if not grp.triangles:
            continue
        slot_name = unreal.Name(grp.material if grp.material else f"Slot_{surf_idx:03d}")
        pg_id = desc.create_polygon_group()
        desc.set_polygon_group_material_slot_name(pg_id, slot_name)
        slot_names.append(slot_name)

        vid_for_pos: dict = {}
        def vid(pos_idx, _desc=desc, _positions=obj_mesh.positions, _cache=vid_for_pos):
            v = _cache.get(pos_idx)
            if v is None:
                v = _desc.create_vertex()
                _desc.set_vertex_position(v, unreal.Vector(*_positions[pos_idx]))
                _cache[pos_idx] = v
            return v

        for tri in grp.triangles:
            v_ids = [vid(t[0]) for t in tri]
            vi_ids = []
            for (pi, ti, ni), v in zip(tri, v_ids):
                vi = desc.create_vertex_instance(v)
                if 0 <= ti < len(obj_mesh.uvs):
                    u, vv = obj_mesh.uvs[ti]
                    # AC UVs are top-left origin (V down), same as UE: do NOT
                    # flip V. Matches the import_academy.py fix; the old
                    # `1.0 - vv` rendered textures upside-down. (Props still
                    # need a re-import for this to take effect.)
                    desc.set_vertex_instance_uv(vi, unreal.Vector2D(u, vv), 0)
                vi_ids.append(vi)
            desc.create_triangle(pg_id, vi_ids)

    sm.build_from_static_mesh_descriptions([desc])
    if not _bounds_finite(sm):
        unreal.log_error(
            f"[build_setup_mesh] {asset_name}: CORRUPT bounds after build "
            f"({sm.get_bounding_box()}) -> the mesh will be frustum-culled. "
            f"Source OBJ is {obj_path}; re-run, and if it persists the geometry/"
            f"build needs investigation (do not ship a culled asset).")
    sm.set_editor_property("static_materials",
        [unreal.StaticMaterial(material_interface=None, material_slot_name=n)
         for n in slot_names])
    unreal.EditorAssetLibrary.save_asset(asset_path)
    return sm


def main():
    if not Path(STATICS_JSON).exists():
        unreal.log_error(f"Statics JSON not found: {STATICS_JSON}")
        return 1
    if not Path(SETUPS_DIR).exists():
        unreal.log_error(f"Setups OBJ dir not found: {SETUPS_DIR}")
        return 1

    data = json.loads(Path(STATICS_JSON).read_text(encoding="utf-8"))
    log(f"loaded {data['instance_count']} instances across {data['cells_with_statics']} cells")
    log(f"  {data['unique_setup_count']} unique setups")

    if not unreal.EditorAssetLibrary.does_asset_exist(LEVEL_PATH):
        unreal.log_error(f"Level {LEVEL_PATH} doesn't exist — run import_academy.py first.")
        return 2
    unreal.EditorLevelLibrary.load_level(LEVEL_PATH)

    # 1) Import each unique setup OBJ as a StaticMesh.
    log(f"importing {data['unique_setup_count']} unique setup meshes from {SETUPS_DIR}")
    setups_dir = Path(SETUPS_DIR)
    imported_meshes = {}      # setup_id_hex -> StaticMesh
    missing = []
    t0 = time.time()
    for i, setup_hex in enumerate(data["unique_setups"]):
        clean = setup_hex[2:] if setup_hex.startswith("0x") else setup_hex
        obj_path = setups_dir / f"setup_{clean}.obj"
        if not obj_path.exists():
            missing.append(setup_hex)
            continue
        asset_name = f"SM_Setup_{clean}"
        sm = build_setup_mesh(obj_path, asset_name)
        if sm is None:
            missing.append(setup_hex)
            continue
        imported_meshes[setup_hex] = sm
        if (i + 1) % 25 == 0:
            log(f"  imported {len(imported_meshes)}/{data['unique_setup_count']} setup meshes "
                f"({time.time() - t0:.1f}s)")
    log(f"setup-mesh import done: {len(imported_meshes)} ok, {len(missing)} missing/failed "
        f"({time.time() - t0:.1f}s)")

    # 2) Delete any existing Stab actors from prior runs (label prefix Setup_).
    eas = unreal.EditorActorSubsystem()
    existing = [a for a in eas.get_all_level_actors()
                if a.get_actor_label().startswith("Setup_")]
    if existing:
        log(f"deleting {len(existing)} existing Stab actors from prior runs")
        for a in existing:
            eas.destroy_actor(a)

    # 3) Spawn one StaticMeshActor per Stab instance.
    log(f"spawning {data['instance_count']} Stab actors")
    spawned = 0
    skipped = 0
    t0 = time.time()
    for i, inst in enumerate(data["instances"]):
        setup_id = inst["setup_id"]
        sm = imported_meshes.get(setup_id)
        if sm is None:
            skipped += 1
            continue
        pos = inst["position"]
        loc = unreal.Vector(float(pos["x"]), float(pos["y"]), float(pos["z"]))
        q = inst["orientation"]
        rot = unreal.Quat(float(q["x"]), float(q["y"]),
                          float(q["z"]), float(q["w"])).rotator()
        actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
        if actor is None:
            skipped += 1
            continue
        # Each Stab is identified by (cell, setup, sequence within cell).
        # We append "_NNN" so labels are unique even when one cell has
        # several copies of the same setup.
        actor.set_actor_label(f"Setup_{inst['cell_id'][2:]}_{setup_id[2:]}_{i:04d}")
        actor.static_mesh_component.set_static_mesh(sm)
        actor.set_folder_path("Academy/Props")
        spawned += 1
        if (i + 1) % 128 == 0:
            log(f"  spawned {spawned}/{data['instance_count']} Stab actors "
                f"({time.time() - t0:.1f}s)")

    log(f"spawn done: {spawned} spawned, {skipped} skipped ({time.time() - t0:.1f}s)")

    unreal.EditorLevelLibrary.save_current_level()
    log(f"DONE. {len(imported_meshes)} unique setup meshes, {spawned} actors. Level saved.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
