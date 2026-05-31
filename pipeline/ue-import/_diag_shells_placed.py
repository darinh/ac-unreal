"""
_diag_shells_placed.py

Verifies that every Cell_<id> actor in AcademyMap actually has its static mesh
assigned (an empty StaticMeshActor would still satisfy a label-based count but
render NOTHING). Reports:
  - total Cell_ actors, how many have a non-null mesh, how many are EMPTY
  - the empty ones (these are the real failures)
  - a focused dump of the first room 0x860201AD and its grid neighbors:
    for each, whether an actor exists, has a mesh, its location + mesh name.
Writes pipeline/renders/_diag_shells_placed.txt
"""
import re
import unreal

OUT = r"C:\Users\darin\repos\ac-unreal\pipeline\renders\_diag_shells_placed.txt"
MAP_PATH = "/Game/Academy/Maps/AcademyMap"
RE_CELL = re.compile(r"^Cell_([0-9A-Fa-f]{8})", re.IGNORECASE)

FOCUS = ["860201AD",  # first room
         "860201B1", "860201B2", "860201B3", "860201B4", "860201B5",  # +Y neighbors
         "860202E2"]  # +Z neighbor

lines = []
def out(m):
    lines.append(str(m)); unreal.log(f"[diag] {m}")
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
actors = eas.get_all_level_actors()
out(f"loaded {MAP_PATH}: {len(actors)} actors")

cell_actors = {}   # cid -> actor
for a in actors:
    try:
        lbl = a.get_actor_label()
    except Exception:
        continue
    m = RE_CELL.match(lbl)
    if m:
        cell_actors.setdefault(m.group(1).upper(), a)

def mesh_of(a):
    # Robust accessor: enumerate StaticMeshComponents and read the
    # 'static_mesh' editor property. The convenience property
    # `static_mesh_component.get_static_mesh()` returns None in some
    # commandlet contexts even when a mesh IS assigned, so don't trust it.
    try:
        comps = a.get_components_by_class(unreal.StaticMeshComponent)
    except Exception:
        comps = []
    for c in comps:
        try:
            sm = c.get_editor_property("static_mesh")
        except Exception:
            sm = None
        if sm is not None:
            return sm
    return None

empty = []
with_mesh = 0
for cid, a in cell_actors.items():
    sm = mesh_of(a)
    if sm is None:
        empty.append(cid)
    else:
        with_mesh += 1

out(f"Cell_ actors: {len(cell_actors)}  with_mesh: {with_mesh}  EMPTY(no mesh): {len(empty)}")
if empty:
    out(f"EMPTY cell actors (render nothing): {sorted(empty)}")

out("")
out("FOCUS: first room + neighbors")
for cid in FOCUS:
    a = cell_actors.get(cid)
    if a is None:
        out(f"  {cid}: NO ACTOR IN LEVEL")
        continue
    sm = mesh_of(a)
    loc = a.get_actor_location()
    smname = sm.get_name() if sm else "<NONE>"
    out(f"  {cid}: actor OK  mesh={smname}  loc=({loc.x:.0f},{loc.y:.0f},{loc.z:.0f})  "
        f"hidden={a.is_hidden_ed()}")
out("DONE")
