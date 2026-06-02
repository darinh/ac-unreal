"""SYSTEM-WIDE repair: rebuild every academy cell mesh whose serialized bounding
box is corrupt (NaN / Inf / ~1e48), via the canonical fresh build_static_mesh
(proven to produce correct finite bounds; preserves material slot bindings).
Corrupt bounds -> frustum-cull -> the room shows no walls/floor. Source OBJs are
clean; the corruption is a build-pipeline artifact (an old in-place rebuild path).
Idempotent: only touches cells still corrupt. Pair with audit_cell_bounds.py as
the verification gate. Writes pipeline/renders/_repair_bounds.txt"""
import os, sys, math
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
import unreal
import import_academy as ia

EAL = unreal.EditorAssetLibrary
OUT = "C:/Users/darin/repos/ac-unreal/pipeline/renders/_repair_bounds.txt"
fh = open(OUT, "w", encoding="utf-8")
def w(m):
    unreal.log(f"[repair] {m}")
    fh.write(str(m) + "\n"); fh.flush()

def corrupt(sm):
    bb = sm.get_bounding_box()
    vals = [bb.min.x, bb.min.y, bb.min.z, bb.max.x, bb.max.y, bb.max.z]
    return any(math.isnan(v) or math.isinf(v) for v in vals) or any(abs(v) > 1e7 for v in vals)

expected = sorted(
    nm[3:] for nm in (ap.split("/")[-1].split(".")[0]
        for ap in EAL.list_assets("/Game/Academy/Cells", recursive=False, include_folder=False))
    if nm.startswith("SM_"))
w(f"cells: {len(expected)}")

to_fix = [cid for cid in expected
          if (sm := EAL.load_asset(f"/Game/Academy/Cells/SM_{cid}")) is not None and corrupt(sm)]
w(f"corrupt (to rebuild): {len(to_fix)}")

fixed, still, missing_obj = 0, [], []
for i, cid in enumerate(to_fix):
    obj = Path(ia.OBJ_DIR) / f"cell_{cid}.obj"
    if not obj.exists():
        missing_obj.append(cid); continue
    om = ia.parse_obj(obj); mm = ia.parse_mtl(obj.with_suffix(".mtl"))
    sm = ia.build_static_mesh(om, mm, f"SM_{cid}", None)
    if sm is not None and not corrupt(sm): fixed += 1
    else: still.append(cid)
    if (i + 1) % 50 == 0: w(f"  ...{i+1}/{len(to_fix)} (fixed={fixed})")

w(f"\n=== RESULT ===")
w(f"  rebuilt+fixed: {fixed}")
w(f"  still corrupt: {len(still)} {still[:20]}")
w(f"  missing OBJ: {len(missing_obj)} {missing_obj[:20]}")
w("DONE")
fh.close()
