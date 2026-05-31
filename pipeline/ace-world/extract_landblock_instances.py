#!/usr/bin/env python3
"""
extract_landblock_instances.py

Phase 5i: pull every static spawn (NPC, sign, door, portal, item) for
a given landblock out of the ACE-World repo, look up each weenie's
name + WeenieType + Setup ID + Heritage, and emit a UE-ready JSON.

ACE-World layout (https://github.com/ACEmulator/ACE-World):
    Database/3-Core/6 LandBlockExtendedData/SQL/<LB>.sql
        -- one file per landblock; INSERT INTO landblock_instance ...
    Database/3-Core/9 WeenieDefaults/SQL/<Category>/<wcid> <name>.sql
        -- one file per weenie; filename prefix = zero-padded class_Id.

Each weenie file has:
    INSERT INTO weenie (class_Id, class_Name, type, ...) VALUES (N, '...', T, ...)
    INSERT INTO weenie_properties_d_i_d (object_Id, type, value)
        VALUES (N, 1, 0x02xxxxxx) -- type 1 = Setup ID (DataIDs table)
    INSERT INTO weenie_properties_string (object_Id, type, value)
        VALUES (N, 1, 'display name')

Usage:
    python extract_landblock_instances.py
        <aceworld_dir>
        <landblock_hex>
        <out_json>
"""
import argparse
import json
import re
import sys
from pathlib import Path


WEENIE_TYPES = {
    0: "Undef", 1: "Generic", 2: "Clothing", 3: "MissileLauncher",
    4: "Missile", 5: "Ammunition", 6: "MeleeWeapon", 7: "Portal",
    8: "Book", 9: "Coin", 10: "Creature", 11: "Admin",
    12: "Vendor", 13: "HotSpot", 14: "Corpse", 15: "Cow",
    16: "AI", 17: "Machine", 18: "Food", 19: "Door", 20: "Chest",
    21: "Container", 22: "Key", 23: "Lockpick", 24: "PressurePlate",
    25: "LifeStone", 26: "Switch", 27: "PKModifier", 28: "Healer",
    29: "LightSource", 30: "Allegiance", 32: "SpellComponent",
    33: "ProjectileSpell", 34: "Scroll", 35: "Caster", 36: "Channel",
    37: "ManaStone", 38: "Gem", 44: "CraftTool", 50: "Entity",
    51: "Stackable", 52: "HUD", 53: "House", 54: "Deed", 55: "SlumLord",
    56: "Hook", 57: "Storage", 58: "BootSpot", 59: "HousePortal",
    60: "Game", 68: "Pet", 69: "PetDevice", 70: "CombatPet",
}


def categorize(t):
    """Map WeenieType -> a coarse category for the UE placeholder visual."""
    if t in (10, 11, 12, 15, 16, 28, 68, 69, 70): return "npc"
    if t in (7, 59): return "portal"
    if t == 19: return "door"
    if t in (20, 21, 25, 26, 56, 57, 13): return "fixture"
    if t in (1, 8, 33, 34): return "scenery"
    if t in (2, 3, 4, 5, 6, 35): return "weapon"
    if t in (9, 22, 23, 32, 37, 38, 44): return "item"
    return "other"


CM_PER_M = 100.0


def ac_to_ue_pos(ac_xyz):
    x, y, z = ac_xyz
    return (y * CM_PER_M, x * CM_PER_M, z * CM_PER_M)


def ac_to_ue_quat(q):
    x, y, z, w = q
    return (-y, -x, -z, w)


# --- Landblock SQL parsing -------------------------------------------

# Each row in 8602.sql:
#   INSERT INTO `landblock_instance` (...) VALUES
#   (0x78602003, 4451, 0x86020114, 190.068, -225.037, -12,
#    -0.002074, 0, 0, -0.999998, False, '2019-02-10 00:00:00'); /* Door */
LB_ROW_RE = re.compile(
    r"VALUES\s*\(\s*"
    r"(0x[0-9A-Fa-f]+),\s*"               # guid
    r"(\d+),\s*"                           # weenie_Class_Id
    r"(0x[0-9A-Fa-f]+),\s*"               # obj_Cell_Id
    r"(-?[\d.eE+-]+),\s*(-?[\d.eE+-]+),\s*(-?[\d.eE+-]+),\s*"   # origin X Y Z
    r"(-?[\d.eE+-]+),\s*(-?[\d.eE+-]+),\s*(-?[\d.eE+-]+),\s*(-?[\d.eE+-]+),\s*"  # angles W X Y Z
    r"(True|False)\s*,\s*'[^']*'\s*\)"     # is_link_child, datetime
    r"(?:\s*;\s*/\*\s*(?P<comment>.*?)\s*\*/)?",
    re.DOTALL,
)


def find_landblock_instances(sql_text, landblock_hi16):
    out = []
    target = int(landblock_hi16)
    for m in LB_ROW_RE.finditer(sql_text):
        guid_hex = m.group(1)
        wcid = int(m.group(2))
        obj_cell = int(m.group(3), 16)
        if (obj_cell >> 16) != target:
            continue
        ox, oy, oz = float(m.group(4)), float(m.group(5)), float(m.group(6))
        aw, ax, ay, az = float(m.group(7)), float(m.group(8)), float(m.group(9)), float(m.group(10))
        comment = m.group("comment") or ""
        out.append({
            "guid": int(guid_hex, 16),
            "wcid": wcid,
            "cell_id": obj_cell,
            "origin": (ox, oy, oz),
            "orient": (ax, ay, az, aw),       # AC order x,y,z,w
            "comment": comment.strip(),
        })
    return out


# --- Weenie file lookup ----------------------------------------------

# `INSERT INTO weenie (class_Id, class_Name, type, last_Modified)`
WEENIE_DEF_RE = re.compile(
    r"INSERT INTO `weenie` \([^)]*\)\s*VALUES\s*"
    r"\(\d+,\s*'((?:[^'\\]|\\.)*)',\s*(\d+),"
)
# `INSERT INTO weenie_properties_d_i_d` row with type=1 (Setup)
WEENIE_SETUP_RE = re.compile(
    r"\(\s*\d+,\s*1,\s*(0x[0-9A-Fa-f]+|\d+)\s*\)\s*"
    r"/\*\s*Setup\s*\*/"
)
# Display name from weenie_properties_string with type=1 (Name)
WEENIE_NAME_RE = re.compile(
    r"\(\s*\d+,\s*1,\s*'((?:[^'\\]|\\.)*)'\s*\)\s*"
    r"/\*\s*Name\s*\*/"
)


class WeenieIndex:
    """Lazy lookup of weenie SQL files by wcid."""
    def __init__(self, weenie_root: Path):
        self.root = weenie_root
        # Build wcid -> path map via filename prefix (5-digit decimal).
        # Glob all SQL files once; ~26k files but ~few seconds.
        self.by_wcid = {}
        for f in weenie_root.rglob("*.sql"):
            m = re.match(r"(\d{5})\s", f.name)
            if not m:
                continue
            wcid = int(m.group(1), 10)
            # Files have leading 5 digits but no leading zero pad in
            # filename for some early wcids — actually we saw "00004 +Moosier"
            # so format is always 5-digit zero-padded.
            self.by_wcid[wcid] = f

    def lookup(self, wcid: int) -> dict:
        path = self.by_wcid.get(wcid)
        if path is None:
            return {}
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return {}
        result = {"file": str(path.relative_to(self.root))}
        m = WEENIE_DEF_RE.search(text)
        if m:
            result["class_name"] = m.group(1)
            result["type"] = int(m.group(2))
        m = WEENIE_SETUP_RE.search(text)
        if m:
            v = m.group(1)
            result["setup_id"] = int(v, 16) if v.startswith("0x") else int(v) & 0xFFFFFFFF
        m = WEENIE_NAME_RE.search(text)
        if m:
            result["display_name"] = m.group(1).replace("\\'", "'").replace('\\"', '"')
        return result


# --- Main ------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("aceworld", help="Path to the ACE-World repo root")
    ap.add_argument("landblock_hex")
    ap.add_argument("out_json")
    args = ap.parse_args()

    lb_hi16 = int(args.landblock_hex, 16)
    root = Path(args.aceworld)
    lb_sql = root / "Database" / "3-Core" / "6 LandBlockExtendedData" / "SQL" / f"{lb_hi16:04X}.sql"
    if not lb_sql.exists():
        print(f"Landblock SQL not found: {lb_sql}", file=sys.stderr)
        return 1

    print(f"Parsing {lb_sql.name} ...", flush=True)
    text = lb_sql.read_text(encoding="utf-8")
    instances = find_landblock_instances(text, lb_hi16)
    print(f"  found {len(instances)} instances", flush=True)

    wcid_set = {i["wcid"] for i in instances}
    print(f"  unique wcids: {len(wcid_set)}", flush=True)

    weenie_root = root / "Database" / "3-Core" / "9 WeenieDefaults" / "SQL"
    print(f"Indexing weenies under {weenie_root} ...", flush=True)
    idx = WeenieIndex(weenie_root)
    print(f"  indexed {len(idx.by_wcid)} weenie files", flush=True)

    out = []
    missing = 0
    for inst in instances:
        wcid = inst["wcid"]
        w = idx.lookup(wcid)
        if not w:
            missing += 1
        wtype = w.get("type", 0)
        entry = {
            "guid": inst["guid"],
            "wcid": wcid,
            "class_name": w.get("class_name", ""),
            "display_name": w.get("display_name", "") or inst["comment"],
            "weenie_type": wtype,
            "weenie_type_name": WEENIE_TYPES.get(wtype, f"Type_{wtype}") if wtype else "",
            "category": categorize(wtype),
            "setup_id": f"0x{w['setup_id']:08X}" if "setup_id" in w else None,
            "cell_id": f"0x{inst['cell_id']:08X}",
            "landblock_comment": inst["comment"],
        }
        # ACE landblock_instance origin/angles semantics (verified against
        # ACE.Entity.Position):
        #   - For INDOOR cells (EnvCells; cell_id low-16 >= 0x100), origin
        #     is LANDBLOCK-LOCAL metres. Position.cs line 410 confirms
        #     this — it uses `LandblockX*192 + PositionX` for cross-
        #     landblock distance. The cell_id is just a visibility/physics
        #     index; it does NOT define an additional frame to rotate by.
        #   - For OUTDOOR cells (low-16 < 0x100), origin is ALSO landblock-
        #     local (the cell is just a 24m x 24m sub-grid of the 192m
        #     landblock).
        # So we never apply a cell-local rotation. The cell-frame Stab
        # transform in our Phase 5f extractor is for the .dat-side Stab
        # records (which ARE cell-local) — these landblock_instance rows
        # are a different thing entirely, despite living "in" a cell.
        ox, oy, oz = inst["origin"]
        ax, ay, az, aw = inst["orient"]
        ue_x, ue_y, ue_z = ac_to_ue_pos((ox, oy, oz))
        qx, qy, qz, qw = ac_to_ue_quat((ax, ay, az, aw))
        entry["position"] = {"x": ue_x, "y": ue_y, "z": ue_z}
        entry["orientation"] = {"x": qx, "y": qy, "z": qz, "w": qw}
        entry["origin_ac_landblock"] = {"x": ox, "y": oy, "z": oz}
        out.append(entry)

    cats = {cat: sum(1 for e in out if e["category"] == cat)
            for cat in ("npc", "portal", "door", "fixture", "scenery", "weapon", "other")}

    doc = {
        "schema_version": 1,
        "landblock_id": f"0x{lb_hi16:04X}",
        "source_sql": str(lb_sql.relative_to(root)),
        "instance_count": len(out),
        "weenies_resolved": len(wcid_set) - missing,
        "weenies_missing": missing,
        "category_counts": cats,
        "instances": out,
    }
    Path(args.out_json).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"Wrote {args.out_json}")
    print(f"  categories: {cats}")
    print(f"  weenie metadata: {len(wcid_set) - missing}/{len(wcid_set)} resolved")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)

