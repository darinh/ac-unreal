"""Bounds audit across ALL cell meshes: load each SM_<id> asset and classify its
serialized bounding box (what the renderer culls against). A mesh with NaN/Inf or
~1e48 bounds is frustum-culled by UE and the room shows no shell. Source OBJs are
clean, so corrupt bounds are a build-pipeline defect. Run this after ANY bulk cell
operation as the verification gate. Loads assets only (no level).
Writes pipeline/renders/_audit_bounds.txt"""
import unreal, math, collections

EAL = unreal.EditorAssetLibrary
OUT = "C:/Users/darin/repos/ac-unreal/pipeline/renders/_audit_bounds.txt"
fh = open(OUT, "w", encoding="utf-8")
def w(m):
    unreal.log(f"[bnds] {m}")
    fh.write(str(m) + "\n"); fh.flush()

expected = sorted(
    nm[3:] for nm in (ap.split("/")[-1].split(".")[0]
        for ap in EAL.list_assets("/Game/Academy/Cells", recursive=False, include_folder=False))
    if nm.startswith("SM_"))
w(f"cell meshes: {len(expected)}")

def classify(sm):
    bb = sm.get_bounding_box()
    vals = [bb.min.x, bb.min.y, bb.min.z, bb.max.x, bb.max.y, bb.max.z]
    if any(math.isnan(v) or math.isinf(v) for v in vals): return "nan_inf", vals
    if any(abs(v) > 1e7 for v in vals): return "huge", vals
    ext = max(bb.max.x - bb.min.x, bb.max.y - bb.min.y, bb.max.z - bb.min.z)
    if ext < 1.0: return "zero", vals
    return "finite", vals

stat = collections.Counter(); examples = {}; corrupt_ids = []
for cid in expected:
    sm = EAL.load_asset(f"/Game/Academy/Cells/SM_{cid}")
    if sm is None: stat["missing"] += 1; continue
    cat, vals = classify(sm); stat[cat] += 1
    if cat not in examples: examples[cat] = (cid, [round(v, 1) for v in vals])
    if cat in ("nan_inf", "huge", "zero"): corrupt_ids.append(cid)

w(f"\n=== bounds classification (of {len(expected)}) ===")
for k, v in stat.most_common(): w(f"  {k}: {v}")
w("\n=== one example per category ===")
for cat, (cid, vals) in examples.items(): w(f"  {cat}: {cid} {vals}")
if corrupt_ids:
    w(f"\n=== {len(corrupt_ids)} CORRUPT (frustum-culled) cells ===")
    w("  " + " ".join(corrupt_ids))
else:
    w("\n=== ALL CELLS FINITE — no frustum-cull culprits ===")
w("DONE")
fh.close()
