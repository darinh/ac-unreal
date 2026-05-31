"""Fix the 2x coordinate bug in lights/statics JSONs.

C# DumpAcademyLights/DumpAcademyStatics did:
    stabWorldPos = cellPos + RotateAcVec(cellOrient, stab.Frame.Origin)

But Stab.Frame.Origin in AC's DAT format is ALREADY landblock-local
(verified empirically — stab positions exactly equal 2 * cellPos),
so the cellPos addition double-counts and puts every prop/light at
2x the correct world coordinates.

Fix: for each instance in the JSON, look up its cell's UE position
in layout.json and subtract it.

Inputs:
  pipeline/dat-extract/out/academy_8602/layout.json
  pipeline/dat-extract/out/academy_8602_lights.json
  pipeline/dat-extract/out/academy_8602_statics/statics.json

Outputs (in place): the same two JSONs, with corrected positions
and a note in coordinate_system explaining the fix.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAYOUT_JSON   = ROOT / "pipeline" / "dat-extract" / "out" / "academy_8602" / "layout.json"
LIGHTS_JSON   = ROOT / "pipeline" / "dat-extract" / "out" / "academy_8602_lights.json"
STATICS_JSON  = ROOT / "pipeline" / "dat-extract" / "out" / "academy_8602_statics" / "statics.json"


def load_cell_positions():
    """Returns dict cell_id_hex_upper -> {x, y, z} (UE cm)."""
    data = json.loads(LAYOUT_JSON.read_text(encoding="utf-8"))
    out = {}
    for c in data["cells"]:
        cid = c["cell_id"].upper().replace("0X", "0x")  # normalize "0xABCD..."
        out[cid] = c["position"]
    return out


def fix_json(path: Path, instances_key: str, label: str):
    if not path.exists():
        print(f"  MISSING: {path}")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get(instances_key, [])
    cells = load_cell_positions()
    fixed = 0
    missing_cell = 0
    for item in items:
        cell_id = item.get("cell_id", "").upper().replace("0X", "0x")
        if cell_id not in cells:
            missing_cell += 1
            continue
        cp = cells[cell_id]
        old = item["position"]
        item["position"] = {
            "x": old["x"] - cp["x"],
            "y": old["y"] - cp["y"],
            "z": old["z"] - cp["z"],
        }
        fixed += 1
    data["coordinate_system"] = (
        "UE-ready: left-handed Z-up, centimetres. World-space. "
        "Note: positions have been re-derived by subtracting cellPos from the "
        "original C# extractor output, which double-counted cellPos because "
        "Stab.Frame.Origin in AC's DAT format is already landblock-absolute. "
        "See pipeline/ue-import/fix_lights_statics_coords.py."
    )
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  {label}: fixed {fixed} {instances_key} entries ({missing_cell} cell-id misses)")


print("Loading layout to get cell positions...")
print(f"  {len(load_cell_positions())} cells in layout")
print()
print("Fixing lights JSON...")
fix_json(LIGHTS_JSON, "lights", "lights")
print()
print("Fixing statics JSON...")
fix_json(STATICS_JSON, "instances", "statics")
