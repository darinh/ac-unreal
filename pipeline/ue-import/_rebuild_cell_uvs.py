# Rebuild cell StaticMesh assets in place with the corrected (un-flipped)
# UVs. Reuses import_academy's parse/build functions but does NOT spawn
# actors or modify the level -- the existing Cell_ actors reference the
# SM_<id> assets by path and pick up the rebuilt geometry automatically.
# build_static_mesh now rebuilds-in-place and preserves material bindings,
# so this needs no follow-up material pass.
#
# AC_REBUILD_ONLY (optional): comma-separated short cell ids (e.g.
# "860201AD,86020100") to rebuild just those for a quick verify.
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal
import import_academy as ia


def log(m): unreal.log(f"[uv-rebuild] {m}")


only = os.environ.get("AC_REBUILD_ONLY", "").strip()
only_set = {s.strip().upper().replace("0X", "") for s in only.split(",") if s.strip()} if only else None

data = ia.load_layout()
cells = data["cells"]
obj_dir = Path(ia.OBJ_DIR)
built = skipped = 0
t0 = time.time()

for i, cell in enumerate(cells):
    cell_id = cell["cell_id"]
    short_id = cell_id[2:]
    if only_set is not None and short_id.upper() not in only_set:
        continue
    obj_path = obj_dir / cell["obj_file"]
    if not obj_path.exists():
        skipped += 1
        continue
    try:
        obj_mesh = ia.parse_obj(obj_path)
        mtl_map = ia.parse_mtl(obj_path.with_suffix(".mtl"))
        ia.build_static_mesh(obj_mesh, mtl_map, f"SM_{short_id}", None)
        built += 1
    except Exception as e:
        unreal.log_error(f"[uv-rebuild] {cell_id} failed: {e}")
        skipped += 1
    if built and built % 64 == 0:
        log(f"  {built} rebuilt ({time.time()-t0:.1f}s)")

log(f"DONE: rebuilt={built} skipped={skipped} ({time.time()-t0:.1f}s)")
