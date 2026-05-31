"""
place_missing_shells.py

Repairs AcademyMap: some cell shell actors (one StaticMeshActor per EnvCell,
labeled Cell_<8hex>, mesh /Game/Academy/Cells/SM_<8hex>) are missing from the
level even though every SM_ mesh asset exists on disk -- the symptom of an
import pass that was cancelled before the level was saved with all actors.

This script places ONLY the missing shells, reusing the already-built SM_
assets (never rebuilding from OBJ), at the exact layout position/orientation
used by import_academy.py. It is idempotent and SAFE:

  PREFLIGHT (no level mutation):
    - validate every existing Cell_ actor's transform against the layout json
      (location + rotation). If existing shells don't match the json basis,
      ABORT without spawning -- we'd otherwise place new shells on a different
      coordinate basis.
    - detect duplicate mesh references.
  PLACEMENT (only if preflight passes):
    - for each cell with no existing actor (by canonical label OR by mesh ref),
      load SM_<id>, spawn StaticMeshActor at layout xform, label Cell_<ID>,
      assert the label was not uniquified, fold into the section hierarchy.
    - save the level.

Writes a report to pipeline/renders/_place_shells_report.txt.
"""
import json
import re
import math
import collections
import unreal

ROOT = r"C:\Users\darin\repos\ac-unreal"
SAMPLES = ROOT + r"\pipeline\dat-extract\samples"
LAYOUT = SAMPLES + r"\academy_8602_layout.json"
REPORT = ROOT + r"\pipeline\renders\_place_shells_report.txt"
MAP_PATH = "/Game/Academy/Maps/AcademyMap"
CELLS_PACKAGE = "/Game/Academy/Cells"
TOP = "Holtburg_0x8602"

# tolerances for "existing shells match the layout basis"
LOC_TOL = 1.0      # cm
ROT_TOL = 0.5      # degrees

report_lines = []
def rep(m):
    report_lines.append(str(m))
    unreal.log(f"[place] {m}")
    try:
        with open(REPORT, "w") as f:
            f.write("\n".join(report_lines) + "\n")
    except Exception:
        pass


def bare(cid):
    s = str(cid)
    if s.lower().startswith("0x"):
        s = s[2:]
    return s.upper()


# ---------------------------------------------------------------------------
# Load layout + compute section assignment (same logic as reorganize_outliner)
# ---------------------------------------------------------------------------
cells = json.load(open(LAYOUT))["cells"]
cell_by_id = {bare(c["cell_id"]): c for c in cells}
cell_ids = list(cell_by_id.keys())

STEP = 1000
pos2cell = {}
for c in cells:
    p = c["position"]
    pos2cell[(round(p["x"]), round(p["y"]), round(p["z"]))] = bare(c["cell_id"])

def neighbors(k):
    x, y, z = k
    for dx, dy, dz in [(STEP,0,0),(-STEP,0,0),(0,STEP,0),(0,-STEP,0),(0,0,STEP),(0,0,-STEP)]:
        nk = (x+dx, y+dy, z+dz)
        if nk in pos2cell:
            yield nk

seen = set(); comps = []
for k in pos2cell:
    if k in seen:
        continue
    stack = [k]; comp = []; seen.add(k)
    while stack:
        cur = stack.pop(); comp.append(cur)
        for nk in neighbors(cur):
            if nk not in seen:
                seen.add(nk); stack.append(nk)
    comps.append(comp)
comps.sort(key=lambda comp: (-len(comp), min(comp)))
cell2section = {}
for idx, comp in enumerate(comps, start=1):
    for k in comp:
        cell2section[pos2cell[k]] = idx

def section_folder(cid):
    s = cell2section.get(cid)
    return f"Section_{s:02d}" if s else "Section_00_unplaced"

def shell_folder(cid):
    return f"{TOP}/{section_folder(cid)}/Cell_{cid}/Shell"


# ---------------------------------------------------------------------------
# Helpers to read existing actors
# ---------------------------------------------------------------------------
RE_CELL = re.compile(r"^Cell_([0-9A-Fa-f]{8})", re.IGNORECASE)
RE_SM = re.compile(r"SM_([0-9A-Fa-f]{8})", re.IGNORECASE)

def actor_mesh_cell(a):
    """Return bare cell id from the actor's static mesh asset, else None."""
    try:
        comp = a.static_mesh_component
        sm = comp.get_static_mesh() if comp else None
        if sm is None:
            return None
        m = RE_SM.search(sm.get_path_name())
        return m.group(1).upper() if m else None
    except Exception:
        return None

def quat_rot(c):
    q = c["orientation"]
    return unreal.Quat(float(q["x"]), float(q["y"]),
                       float(q["z"]), float(q["w"])).rotator()

def layout_loc(c):
    p = c["position"]
    return unreal.Vector(float(p["x"]), float(p["y"]), float(p["z"]))

def ang_diff(a, b):
    d = (a - b) % 360.0
    return min(d, 360.0 - d)


# ---------------------------------------------------------------------------
# Load level
# ---------------------------------------------------------------------------
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
actors = eas.get_all_level_actors()
rep(f"loaded {MAP_PATH}: {len(actors)} actors")

# index existing shell actors by cell (prefer mesh ref, fall back to label)
existing_by_cell = collections.defaultdict(list)   # cid -> [actor,...]
for a in actors:
    if not isinstance(a, unreal.StaticMeshActor):
        continue
    cid = actor_mesh_cell(a)
    if cid is None:
        try:
            m = RE_CELL.match(a.get_actor_label())
            cid = m.group(1).upper() if m else None
        except Exception:
            cid = None
    if cid:
        existing_by_cell[cid].append(a)

dup_cells = {cid: acts for cid, acts in existing_by_cell.items() if len(acts) > 1}
rep(f"existing shell actors: {sum(len(v) for v in existing_by_cell.values())} "
    f"covering {len(existing_by_cell)} cells; duplicates: {len(dup_cells)}")

# ---------------------------------------------------------------------------
# PREFLIGHT: validate existing shell transforms against the layout basis
# ---------------------------------------------------------------------------
checked = 0
loc_mismatch = []
rot_mismatch = []
max_loc = 0.0
max_rot = 0.0
for cid, acts in existing_by_cell.items():
    c = cell_by_id.get(cid)
    if c is None:
        continue
    a = acts[0]
    exp_loc = layout_loc(c)
    got_loc = a.get_actor_location()
    dl = math.sqrt((exp_loc.x-got_loc.x)**2 + (exp_loc.y-got_loc.y)**2 + (exp_loc.z-got_loc.z)**2)
    exp_rot = quat_rot(c)
    got_rot = a.get_actor_rotation()
    dr = max(ang_diff(exp_rot.roll, got_rot.roll),
             ang_diff(exp_rot.pitch, got_rot.pitch),
             ang_diff(exp_rot.yaw, got_rot.yaw))
    max_loc = max(max_loc, dl); max_rot = max(max_rot, dr)
    if dl > LOC_TOL:
        loc_mismatch.append((cid, round(dl, 2)))
    if dr > ROT_TOL:
        rot_mismatch.append((cid, round(dr, 3)))
    checked += 1

rep(f"PREFLIGHT: checked {checked} existing shells against layout; "
    f"max_loc_delta={max_loc:.3f}cm max_rot_delta={max_rot:.3f}deg; "
    f"loc_mismatch={len(loc_mismatch)} rot_mismatch={len(rot_mismatch)}")
if loc_mismatch[:10]:
    rep(f"  loc mismatches (first 10): {loc_mismatch[:10]}")
if rot_mismatch[:10]:
    rep(f"  rot mismatches (first 10): {rot_mismatch[:10]}")

abort = False
if not existing_by_cell:
    rep("ABORT: no existing shells to validate against -- refusing to guess basis.")
    abort = True
if len(loc_mismatch) > 0 or len(rot_mismatch) > 0:
    rep("ABORT: existing shells do not match the layout basis within tolerance. "
        "Not spawning -- the layout json may differ from what built the level.")
    abort = True
if dup_cells:
    rep(f"WARNING: {len(dup_cells)} cells already have duplicate shell actors: "
        f"{list(dup_cells.keys())[:10]}")

# ---------------------------------------------------------------------------
# PLACEMENT
# ---------------------------------------------------------------------------
missing = [cid for cid in cell_ids if cid not in existing_by_cell]
rep(f"cells total={len(cell_ids)} present={len(existing_by_cell)} missing={len(missing)}")

placed = 0
no_asset = []
label_uniquified = []
if not abort:
    for cid in missing:
        c = cell_by_id[cid]
        asset_path = f"{CELLS_PACKAGE}/SM_{cid}"
        if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
            no_asset.append(cid)
            continue
        sm = unreal.EditorAssetLibrary.load_asset(asset_path)
        if sm is None:
            no_asset.append(cid)
            continue
        actor = eas.spawn_actor_from_class(unreal.StaticMeshActor,
                                           layout_loc(c), quat_rot(c))
        if actor is None:
            rep(f"  WARN spawn returned None for {cid}")
            continue
        expected_label = f"Cell_{cid}"
        actor.set_actor_label(expected_label)
        actor.static_mesh_component.set_static_mesh(sm)
        if actor.get_actor_label() != expected_label:
            label_uniquified.append((cid, actor.get_actor_label()))
        actor.set_folder_path(unreal.Name(shell_folder(cid)))
        placed += 1
        if placed % 32 == 0:
            rep(f"  placed {placed}/{len(missing)} ...")

    les.save_current_level()
    rep("level saved")
else:
    rep("placement skipped due to ABORT")

rep(f"DONE: placed={placed} missing_asset={len(no_asset)} "
    f"label_uniquified={len(label_uniquified)}")
if no_asset:
    rep(f"  cells with no SM asset: {no_asset}")
if label_uniquified:
    rep(f"  uniquified labels (regex will miss these!): {label_uniquified}")
