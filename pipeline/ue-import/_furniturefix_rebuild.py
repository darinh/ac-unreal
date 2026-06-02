"""_furniturefix_rebuild.py - rebuild the 11 academy furniture statics that the
placement-frame fix (Resting 0x65 -> Default 0x00 fallback in ExportSetup) also
corrected, in place from the placement-fixed OBJs, preserving material bindings.

Same root cause as the academy door (020005DA): these setups ship ONLY a
Default(0x00) placement frame, so the old exporter applied no per-part transform
and their parts collapsed onto the setup origin. The fixed exporter places the
parts correctly. Topology is identical (same parts, tris, slots) - only vertex
positions move - so the door rebuild's preflight/verify logic applies unchanged.

Mechanism mirrors _doorfix_rebuild.py / _propfix_rebuild.py: capture slot
bindings, delete+recreate from the current OBJ, re-stamp slots preserving the
captured material per slot_name, verify topology unchanged + bounds match OBJ.
Does NOT load the level or save the umap; actors resolve the asset path on next
level load.

Writes pipeline/renders/_furniturefix_rebuild.txt.
"""
import sys, math
from pathlib import Path
import unreal

UE_IMPORT_DIR = str(Path(__file__).resolve().parent)
REPO = Path(UE_IMPORT_DIR).parent.parent
OBJ_DIR = REPO / "pipeline" / "dat-extract" / "out" / "academy_8602_statics"
SETUPS_PACKAGE = "/Game/Academy/Setups"
OUT = REPO / "pipeline" / "renders" / "_furniturefix_rebuild.txt"

# Default set = the 11 academy furniture statics the placement fix corrected.
# Override with AC_FIX_SETUPS="hex,hex,..." to rebuild a different set (e.g. the
# interactive setups that go through import_npcs.py and share the same defect).
import os
_DEFAULT_HEXES = [
    "0200009E", "02000322", "02000341", "02000384", "020003B4", "020003B5",
    "020003F9", "02000BBD", "02000F45", "02001149", "02001255",
]
_env = os.environ.get("AC_FIX_SETUPS", "").strip()
HEXES = [h.strip().upper().replace("0X", "") for h in _env.split(",") if h.strip()] if _env else _DEFAULT_HEXES

if UE_IMPORT_DIR not in sys.path:
    sys.path.insert(0, UE_IMPORT_DIR)
import import_academy as IA

EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
lines = []
def out(m):
    lines.append(str(m)); unreal.log(f"[furnfix] {m}")
def flush():
    OUT.write_text("\n".join(lines) + "\n")


def obj_tris(m):
    return sum(len(g.triangles) for g in m.groups)


def obj_slot_set(m):
    return {str(g.material) for g in m.groups if g.triangles}


def bounds_tuple(sm):
    b = sm.get_bounds(); o, e = b.origin, b.box_extent
    return (o.x, o.y, o.z, e.x, e.y, e.z)


def obj_bounds(m):
    refd = set()
    for g in m.groups:
        for tri in g.triangles:
            for corner in tri:
                refd.add(corner[0])
    pts = [m.positions[i] for i in refd]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
    return ((min(xs)+max(xs))/2.0, (min(ys)+max(ys))/2.0, (min(zs)+max(zs))/2.0,
            (max(xs)-min(xs))/2.0, (max(ys)-min(ys))/2.0, (max(zs)-min(zs))/2.0)


def finite(*xs):
    return all(math.isfinite(x) for x in xs)


def build_desc_and_save(obj_mesh, sm, asset_path, prev_mats):
    desc = unreal.StaticMesh.create_static_mesh_description(sm)
    slot_names = []
    for surf_idx, grp in enumerate(obj_mesh.groups):
        if not grp.triangles:
            continue
        slot_name = unreal.Name(grp.material if grp.material else f"Slot_{surf_idx:03d}")
        pg_id = desc.create_polygon_group()
        desc.set_polygon_group_material_slot_name(pg_id, slot_name)
        slot_names.append(slot_name)

        vid_for_pos = {}
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
                    desc.set_vertex_instance_uv(vi, unreal.Vector2D(u, vv), 0)
                vi_ids.append(vi)
            desc.create_triangle(pg_id, vi_ids)

    sm.build_from_static_mesh_descriptions([desc])
    sm.set_editor_property(
        "static_materials",
        [unreal.StaticMaterial(material_interface=prev_mats.get(str(n)), material_slot_name=n)
         for n in slot_names])
    EAL.save_asset(asset_path)
    return [str(n) for n in slot_names]


def rebuild_one(hexid):
    """Returns 'CLEAN' | 'NEEDS-REVIEW' for one setup."""
    asset_name = f"SM_Setup_{hexid}"
    asset_path = f"{SETUPS_PACKAGE}/{asset_name}"
    obj_path = OBJ_DIR / f"setup_{hexid}.obj"

    out("-" * 50)
    if not EAL.does_asset_exist(asset_path):
        out(f"{hexid}: ABORT asset missing {asset_path}"); return "NEEDS-REVIEW"
    if not obj_path.exists():
        out(f"{hexid}: ABORT OBJ missing {obj_path}"); return "NEEDS-REVIEW"

    old = EAL.load_asset(asset_path)
    old_tris = old.get_num_triangles(0)
    old_verts = old.get_num_vertices(0)
    old_slots_ordered = [str(s.material_slot_name) for s in (old.get_editor_property("static_materials") or [])]
    prev_mats = {str(s.material_slot_name): s.material_interface
                 for s in (old.get_editor_property("static_materials") or [])}
    prev_nonnull = {k for k, v in prev_mats.items() if v is not None}
    old_bounds = bounds_tuple(old)

    obj_mesh = IA.parse_obj(obj_path)
    o_tris = obj_tris(obj_mesh)
    o_slots = obj_slot_set(obj_mesh)
    o_bounds = obj_bounds(obj_mesh)

    out(f"{hexid}: old_tris={old_tris} obj_tris={o_tris} old_verts={old_verts}")
    out(f"  old_bounds={tuple(round(x,1) for x in old_bounds)}")
    out(f"  obj_bounds(new)={tuple(round(x,1) for x in o_bounds)}")

    # Placement fix must NOT change topology, only positions.
    anomalies = []
    if o_tris != old_tris:
        anomalies.append(f"obj_tris {o_tris} != mesh_tris {old_tris}")
    if o_slots != set(old_slots_ordered):
        anomalies.append(f"obj_slots {sorted(o_slots)} != mesh_slots {sorted(set(old_slots_ordered))}")
    if anomalies:
        for a in anomalies:
            out(f"  PREFLIGHT-ANOMALY: {a}")
        out(f"{hexid}: ABORT preflight anomalies - asset NOT modified.")
        return "NEEDS-REVIEW"

    try:
        EAL.delete_asset(asset_path)
        sm = AT.create_asset(asset_name=asset_name, package_path=SETUPS_PACKAGE,
                             asset_class=unreal.StaticMesh, factory=None)
        if sm is None:
            raise RuntimeError("create_asset returned None")
        build_desc_and_save(obj_mesh, sm, asset_path, prev_mats)

        ver = EAL.load_asset(asset_path)
        new_tris = ver.get_num_triangles(0)
        new_verts = ver.get_num_vertices(0)
        new_slots_ordered = [str(s.material_slot_name) for s in (ver.get_editor_property("static_materials") or [])]
        post_nonnull = {str(s.material_slot_name) for s in (ver.get_editor_property("static_materials") or [])
                        if s.material_interface is not None}
        nb = bounds_tuple(ver)

        problems = []
        if new_tris != old_tris:
            problems.append(f"tris {old_tris}->{new_tris}")
        if new_slots_ordered != old_slots_ordered:
            problems.append(f"slots {old_slots_ordered}!={new_slots_ordered}")
        lost = prev_nonnull - post_nonnull
        if lost:
            problems.append(f"lost_materials={sorted(lost)}")
        if not finite(*nb):
            problems.append(f"bad_bounds_nonfinite={nb}")
        else:
            tol = [max(2.0, 0.05 * abs(o_bounds[k])) for k in range(6)]
            if any(abs(nb[k] - o_bounds[k]) > tol[k] for k in range(6)):
                problems.append(f"bounds_vs_obj obj={tuple(round(x,1) for x in o_bounds)} mesh={tuple(round(x,1) for x in nb)}")

        out(f"  REBUILT: tris {old_tris}->{new_tris}, verts {old_verts}->{new_verts}, "
            f"new_bounds={tuple(round(x,1) for x in nb)}")
        if problems:
            out(f"  VERIFY-FAIL: {'; '.join(problems)}")
            return "NEEDS-REVIEW"
        out(f"{hexid}: RESULT CLEAN")
        return "CLEAN"
    except Exception as e:
        out(f"{hexid}: ERROR {e}")
        return "NEEDS-REVIEW"


results = {}
for h in HEXES:
    results[h] = rebuild_one(h)

out("=" * 50)
clean = [h for h, r in results.items() if r == "CLEAN"]
bad = [h for h, r in results.items() if r != "CLEAN"]
for h in HEXES:
    out(f"  {h}: {results[h]}")
out(f"SUMMARY: {len(clean)}/{len(HEXES)} CLEAN")
out("RESULT: CLEAN" if not bad else f"RESULT: NEEDS-REVIEW (failed: {bad})")
out("DONE")
flush()
