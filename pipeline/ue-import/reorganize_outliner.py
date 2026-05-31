"""
reorganize_outliner.py

Re-folders every actor in AcademyMap into a logical, room-centric World
Outliner hierarchy so missing pieces are obvious and manual debugging is easy:

    Holtburg_0x8602/
      Section_NN/                 (23 grid-connected structures = buildings/wings)
        Cell_<id>/                (one EnvCell = one room)
          Shell                   (the SM_<cell> walls+floor+ceiling mesh actor)
          Props                   (static furniture/scenery)
          Lights                  (point lights + fire flicker meshes)
          NPCs                    (doors / fixtures / scenery / npcs / portals)
      _WorldLighting/             (sky light, sun, post-process, fire manager)
      _Unsorted/                  (any actor we could not classify -> visible, not lost)

Actor->cell mapping is derived from the deterministic labels written by the
import scripts (no fragile position matching):
    Cell_<CELLHEX>
    Setup_<CELLHEX>_<setup>_<i>      (props)
    Light_<CELLHEX>_<setup>_<i>      (point lights)
    FireMesh_<CELLHEX>_<setup>_<i>   (fire flicker cubes)
    NPC_<wcid>_<GUIDHEX>_<cat>_<kind>   (guid -> cell via npcs json)

Section index comes from connected components of the cell grid (step 1000).

Writes a completeness manifest to pipeline/renders/_outliner_manifest.txt:
per-cell expected (from DAT json) vs present (actors found) counts, flagging
any cell that is missing its shell / props / lights / npcs.

Headless-safe: writes progress to a file (unreal.log does not reach stdout),
saves the level, then the launcher polls-for-file-then-kills UE.
"""
import json
import re
import collections
import unreal

ROOT = r"C:\Users\darin\repos\ac-unreal"
SAMPLES = ROOT + r"\pipeline\dat-extract\samples"
LAYOUT = SAMPLES + r"\academy_8602_layout.json"
STAT = SAMPLES + r"\academy_8602_statics.json"
LIGHT = SAMPLES + r"\academy_8602_lights.json"
NPC = SAMPLES + r"\academy_8602_npcs.json"
MANIFEST = ROOT + r"\pipeline\renders\_outliner_manifest.txt"
PROGRESS = ROOT + r"\pipeline\renders\_reorg_progress.txt"
MAP_PATH = "/Game/Academy/Maps/AcademyMap"

TOP = "Holtburg_0x8602"

prog_lines = []
def prog(m):
    prog_lines.append(str(m))
    unreal.log(f"[reorg] {m}")
    try:
        with open(PROGRESS, "w") as f:
            f.write("\n".join(prog_lines) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 1. Load DAT json -> cell membership + section assignment
# ---------------------------------------------------------------------------
def bare(cid):
    """Normalize any cell-id form to bare 8-hex uppercase, e.g. '86020100'."""
    s = str(cid)
    if s.lower().startswith("0x"):
        s = s[2:]
    return s.upper()

cells = json.load(open(LAYOUT))["cells"]
cell_ids = [bare(c["cell_id"]) for c in cells]
pos = {bare(c["cell_id"]): c["position"] for c in cells}

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

seen = set()
comps = []
for k in pos2cell:
    if k in seen:
        continue
    stack = [k]; comp = []
    seen.add(k)
    while stack:
        cur = stack.pop(); comp.append(cur)
        for nk in neighbors(cur):
            if nk not in seen:
                seen.add(nk); stack.append(nk)
    comps.append(comp)

# stable order: largest first, tie-break by min corner
comps.sort(key=lambda comp: (-len(comp), min(comp)))
cell2section = {}
section_info = []
for idx, comp in enumerate(comps, start=1):
    ids = sorted(pos2cell[k] for k in comp)
    for cid in ids:
        cell2section[cid] = idx
    xs = [k[0] for k in comp]; ys = [k[1] for k in comp]; zs = [k[2] for k in comp]
    section_info.append((idx, len(ids), min(xs), min(ys), min(zs), max(zs), ids[0]))

def section_folder(cid):
    s = cell2section.get(cid)
    return f"Section_{s:02d}" if s else "Section_00_unplaced"

# guid(hex upper) -> cell for NPCs
npc_json = json.load(open(NPC))
guid2cell = {}
guid2cat = {}
for inst in npc_json["instances"]:
    g = f"{int(inst['guid']):08X}"
    guid2cell[g] = bare(inst["cell_id"])
    guid2cat[g] = inst.get("category", "other")

# expected counts per cell (for the manifest)
def counts_by_cell(path, key):
    d = json.load(open(path))
    return collections.Counter(bare(i["cell_id"]) for i in d[key])

exp_props = counts_by_cell(STAT, "instances")
exp_lights = counts_by_cell(LIGHT, "lights")
exp_npcs = counts_by_cell(NPC, "instances")

# ---------------------------------------------------------------------------
# 2. Classify + re-folder every actor
# ---------------------------------------------------------------------------
RE_CELL = re.compile(r"^Cell_([0-9A-Fa-f]{8})$")
RE_PROP = re.compile(r"^Setup_([0-9A-Fa-f]{8})_")
RE_LIGHT = re.compile(r"^Light_([0-9A-Fa-f]{8})_")
RE_FIRE = re.compile(r"^FireMesh_([0-9A-Fa-f]{8})_")
RE_NPC = re.compile(r"^NPC_\d+_([0-9A-Fa-f]{8})_")

WORLD_LIGHTING = {"AcademySkyLight", "AcademySun", "AcademyPostProcess",
                  "AcAcademyFireManager", "AcademySkyAtmosphere"}
WORLD_SETUP = {"AcademyPlayerStart"}

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
actors = eas.get_all_level_actors()
prog(f"loaded {MAP_PATH}: {len(actors)} actors")

# present-count trackers keyed by cell
present = collections.defaultdict(lambda: collections.Counter())
unsorted_labels = []
cat_counts = collections.Counter()

def cell_room_folder(cid, category):
    return f"{TOP}/{section_folder(cid)}/Cell_{cid}/{category}"

for a in actors:
    try:
        label = a.get_actor_label()
    except Exception:
        continue
    folder = None
    cid = None
    category = None

    if label in WORLD_LIGHTING:
        folder = f"{TOP}/_WorldLighting"
        cat_counts["world_lighting"] += 1
    elif label in WORLD_SETUP:
        folder = f"{TOP}/_World"
        cat_counts["world_setup"] += 1
    else:
        m = RE_CELL.match(label)
        if m:
            cid = m.group(1).upper(); category = "Shell"
        if cid is None:
            m = RE_PROP.match(label)
            if m:
                cid = m.group(1).upper(); category = "Props"
        if cid is None:
            m = RE_LIGHT.match(label)
            if m:
                cid = m.group(1).upper(); category = "Lights"
        if cid is None:
            m = RE_FIRE.match(label)
            if m:
                cid = m.group(1).upper(); category = "Lights"
        if cid is None:
            m = RE_NPC.match(label)
            if m:
                g = m.group(1).upper()
                cid = guid2cell.get(g)
                category = "NPCs"
        if cid and category:
            folder = cell_room_folder(cid, category)
            present[cid][category] += 1
            cat_counts[category] += 1

    if folder is None:
        folder = f"{TOP}/_Unsorted"
        unsorted_labels.append(label)
        cat_counts["unsorted"] += 1

    try:
        a.set_folder_path(unreal.Name(folder))
    except Exception as e:
        prog(f"  WARN set_folder_path failed for {label}: {e}")

prog(f"classified: {dict(cat_counts)}")
prog(f"unsorted ({len(unsorted_labels)}): " + ", ".join(unsorted_labels[:20]))

# ---------------------------------------------------------------------------
# 3. Save level
# ---------------------------------------------------------------------------
les.save_current_level()
prog("level saved")

# ---------------------------------------------------------------------------
# 4. Completeness manifest
# ---------------------------------------------------------------------------
lines = []
lines.append("ACADEMY OUTLINER MANIFEST  (landblock 0x8602)")
lines.append(f"top folder: {TOP}")
lines.append("")
lines.append("SECTIONS (grid-connected structures):")
lines.append("  idx  cells  minX    minY    zmin   zmax   firstCell")
for (idx, n, mnx, mny, mnz, mxz, first) in section_info:
    lines.append(f"  {idx:>3}  {n:>5}  {mnx:>6}  {mny:>6}  {mnz:>5}  {mxz:>5}   {first}")
lines.append("")
lines.append("PER-CELL COMPLETENESS (expected from DAT vs present in level):")
lines.append("  flags: !SHELL=no shell actor  P=props  L=lights  N=npcs  (exp/found)")
problems = []
for cid in cell_ids:
    pr = present.get(cid, collections.Counter())
    shell = pr.get("Shell", 0)
    ep, el, en = exp_props.get(cid, 0), exp_lights.get(cid, 0), exp_npcs.get(cid, 0)
    fp, fl, fn = pr.get("Props", 0), pr.get("Lights", 0), pr.get("NPCs", 0)
    flag = []
    if shell == 0:
        flag.append("!SHELL")
    if fp < ep:
        flag.append(f"P({ep}/{fp})")
    if fl < el:
        flag.append(f"L({el}/{fl})")
    if fn < en:
        flag.append(f"N({en}/{fn})")
    if flag:
        problems.append(f"  Sec{cell2section.get(cid,0):02d} 0x{cid}: " + " ".join(flag))

if problems:
    lines.append(f"  {len(problems)} cells with mismatches:")
    lines.extend(problems)
else:
    lines.append("  ALL cells match expected counts. Nothing missing.")

lines.append("")
lines.append("TOTALS:")
lines.append(f"  shells present: {sum(1 for c in cell_ids if present.get(c,{}).get('Shell',0))}/{len(cell_ids)}")
lines.append(f"  props present:  {sum(present[c].get('Props',0) for c in present)} (expected {sum(exp_props.values())})")
lines.append(f"  lights present: {sum(present[c].get('Lights',0) for c in present)} (expected {sum(exp_lights.values())} + fire meshes)")
lines.append(f"  npcs present:   {sum(present[c].get('NPCs',0) for c in present)} (expected {sum(exp_npcs.values())})")
lines.append(f"  unsorted actors: {len(unsorted_labels)}")

with open(MANIFEST, "w") as f:
    f.write("\n".join(lines) + "\n")
prog(f"manifest written: {MANIFEST}")
prog("DONE")
