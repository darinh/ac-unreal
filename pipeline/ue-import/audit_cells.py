"""SYSTEM-WIDE cell-shell wiring audit for AcademyMap. For every cell it reports,
from the live level, whether the room shell can render: is there a Cell_<id>
actor? does its mesh ref point at SM_<id>? does the mesh have triangles? are the
material slots bound? Compares the whole population (no per-room screenshots).
Pairs with audit_cell_bounds.py (which covers the frustum-cull/bounds failure
mode). Read-only. Writes pipeline/renders/_audit_cells.txt"""
import unreal, collections
EAL = unreal.EditorAssetLibrary
OUT = "C:/Users/darin/repos/ac-unreal/pipeline/renders/_audit_cells.txt"
fh = open(OUT, "w", encoding="utf-8")
def w(m):
    unreal.log(f"[audit] {m}")
    fh.write(str(m) + "\n"); fh.flush()

expected = set(nm[3:] for nm in (ap.split("/")[-1].split(".")[0]
    for ap in EAL.list_assets("/Game/Academy/Cells", recursive=False, include_folder=False))
    if nm.startswith("SM_"))
w(f"expected cell meshes: {len(expected)}")

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/Academy/Maps/AcademyMap")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cell_actors = {}
for a in eas.get_all_level_actors():
    lbl = a.get_actor_label()
    if lbl.startswith("Cell_"):
        cell_actors[lbl[len("Cell_"):]] = a
w(f"Cell_ actors in level: {len(cell_actors)}")

def detail(cid):
    a = cell_actors.get(cid)
    if a is None: return ("no_actor", None, None, None)
    smc = a.static_mesh_component if hasattr(a, "static_mesh_component") else a.get_component_by_class(unreal.StaticMeshComponent)
    mesh = smc.get_editor_property("static_mesh") if smc else None
    if mesh is None: return ("null_mesh", None, None, None)
    try: tris = mesh.get_num_triangles(0)
    except Exception: tris = -1
    bound = total = 0
    for s in (mesh.get_editor_property("static_materials") or []):
        total += 1
        if s.material_interface is not None: bound += 1
    return ("ok", mesh.get_name(), tris, f"{bound}/{total}")

stat = collections.Counter(); broken = []
for cid in sorted(expected):
    status, mname, tris, mats = detail(cid)
    if status != "ok": stat[status] += 1; broken.append((cid, status))
    elif tris is None or tris <= 0: stat["zero_tris"] += 1; broken.append((cid, f"zero_tris {mname}"))
    elif mname != f"SM_{cid}": stat["wrong_mesh"] += 1; broken.append((cid, f"wrong_mesh={mname}"))
    elif mats.split("/")[0] == "0": stat["unbound_mats"] += 1; broken.append((cid, f"unbound_mats {mats}"))
    else: stat["ok"] += 1

w(f"\n=== SUMMARY ===")
for k, v in stat.most_common(): w(f"  {k}: {v}")
w(f"  broken total: {len(broken)}")
for cid, why in broken[:40]: w(f"  {cid}: {why}")
w("DONE")
fh.close()
