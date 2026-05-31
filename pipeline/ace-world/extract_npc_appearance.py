#!/usr/bin/env python3
"""
extract_npc_appearance.py

Step 4 (Category VI): resolve an NPC's full *appearance overlay* from its
ACE-World weenie defaults, so the client-side body Setup can be assembled
the way the retail client renders it.

Why this is needed
------------------
An NPC's geometry comes from a client Setup (0x02) of body-part GfxObjs
(0x01), but its *identity* (which clothed parts, which textures, which
recolors) is NOT in any single client DAT file. It is defined by the
server weenie defaults (ACEmulator). The retail client receives this as
an ObjDesc and applies it over the base Setup. See ACViewer
`Model/ObjDesc.cs::AddBaseModelData` + `Model/Setup.cs` (the authoritative
reference): the body is `setup.Parts[i]` overridden per-index by
`weenie_properties_anim_part`, with `weenie_properties_texture_map`
substituting SurfaceTexture (0x05) ids at each part, plus palette recolors.

This script parses one weenie SQL file and emits a compact appearance JSON
that `acdat export-npc` consumes to assemble the dressed body. Palette
recolors (skin/hair/eyes tint) are emitted for completeness but their
*application* is a deferred T3-color follow-on; geometry + texture identity
is the in-scope deliverable.

The emitted JSON is AC/ACE-derived data and is NOT committed (LEGAL.md /
ADR-0003); it is regenerated from the user's own ACE-World checkout. Only
this script is committed.

Usage:
    python extract_npc_appearance.py <aceworld_dir> <wcid> <out_json>
"""
import argparse
import json
import re
import sys
from pathlib import Path


# --- weenie property type ids we care about (ACE PropertyDataId enum) ----
DID_SETUP = 1
DID_PALETTE_BASE = 6
DID_EYES_TEXTURE = 9
DID_NOSE_TEXTURE = 10
DID_MOUTH_TEXTURE = 11
DID_HAIR_PALETTE = 15
DID_EYES_PALETTE = 16
DID_SKIN_PALETTE = 17

INT_GENDER = 113
INT_HERITAGE = 188
INT_CREATURE_TYPE = 2


def _find_weenie_file(weenie_root: Path, wcid: int) -> Path:
    """Locate '<5-digit wcid> <name>.sql' anywhere under the weenie tree."""
    prefix = f"{wcid:05d} "
    for f in weenie_root.rglob(f"{prefix}*.sql"):
        return f
    # Fallback: scan filenames (covers any odd padding).
    for f in weenie_root.rglob("*.sql"):
        m = re.match(r"(\d+)\s", f.name)
        if m and int(m.group(1)) == wcid:
            return f
    return None


def _insert_block(text: str, table: str) -> str:
    """Return the VALUES...';' body for `INSERT INTO `table` (...) VALUES`.

    Returns '' if the table is absent. The block ends at the first
    semicolon that terminates the statement.
    """
    m = re.search(
        r"INSERT INTO `" + re.escape(table) + r"`[^;]*?VALUES(?P<body>[^;]*);",
        text,
        re.DOTALL,
    )
    return m.group("body") if m else ""


def _rows(block: str):
    """Yield each top-level (...) tuple's inner text from an INSERT body."""
    depth = 0
    buf = []
    for ch in block:
        if ch == "(":
            depth += 1
            if depth == 1:
                buf = []
                continue
        if ch == ")":
            depth -= 1
            if depth == 0:
                yield "".join(buf)
                continue
        if depth >= 1:
            buf.append(ch)


def _num(tok: str) -> int:
    tok = tok.strip()
    if tok.lower().startswith("0x"):
        return int(tok, 16)
    return int(tok)


def parse_appearance(text: str, wcid: int) -> dict:
    # class_name + type
    name = None
    wtype = None
    m = re.search(
        r"INSERT INTO `weenie`[^;]*?VALUES\s*\(\s*\d+,\s*'((?:[^'\\]|\\.)*)',\s*(\d+)",
        text, re.DOTALL)
    if m:
        name = m.group(1)
        wtype = int(m.group(2))

    # DataIDs (Setup, head textures, palettes)
    dids = {}
    for row in _rows(_insert_block(text, "weenie_properties_d_i_d")):
        parts = [p.strip() for p in row.split(",")]
        if len(parts) >= 3:
            dids[_num(parts[1])] = _num(parts[2])

    # Ints (gender / heritage / creature type)
    ints = {}
    for row in _rows(_insert_block(text, "weenie_properties_int")):
        parts = [p.strip() for p in row.split(",")]
        if len(parts) >= 3:
            ints[_num(parts[1])] = _num(parts[2])

    # Display name
    disp = name
    for row in _rows(_insert_block(text, "weenie_properties_string")):
        parts = [p.strip() for p in row.split(",", 2)]
        if len(parts) >= 3 and _num(parts[1]) == 1:
            disp = parts[2].strip().strip("'").replace("\\'", "'")
            break

    # AnimParts: index -> GfxObj (0x01) id. These override the base
    # setup parts at the given index (ACE PropertiesAnimPart.AnimationId).
    anim_parts = {}
    for row in _rows(_insert_block(text, "weenie_properties_anim_part")):
        parts = [p.strip() for p in row.split(",")]
        if len(parts) >= 3:
            anim_parts[_num(parts[1])] = _num(parts[2])

    # TextureMaps: per part index, old SurfaceTexture (0x05) -> new (0x05).
    texture_map = []
    for row in _rows(_insert_block(text, "weenie_properties_texture_map")):
        parts = [p.strip() for p in row.split(",")]
        if len(parts) >= 4:
            texture_map.append({
                "index": _num(parts[1]),
                "old": _num(parts[2]),
                "new": _num(parts[3]),
            })

    # Palette recolor ranges (deferred application; emitted for completeness).
    palettes = []
    for row in _rows(_insert_block(text, "weenie_properties_palette")):
        parts = [p.strip() for p in row.split(",")]
        if len(parts) >= 4:
            palettes.append({
                "sub_palette_id": _num(parts[1]),
                "offset": _num(parts[2]),
                "length": _num(parts[3]),
            })

    setup_id = dids.get(DID_SETUP)
    appearance = {
        "schema_version": 1,
        "wcid": wcid,
        "name": disp or name,
        "class_name": name,
        "weenie_type": wtype,
        "gender": ints.get(INT_GENDER),
        "heritage": ints.get(INT_HERITAGE),
        "creature_type": ints.get(INT_CREATURE_TYPE),
        "setup_id": f"0x{setup_id:08X}" if setup_id is not None else None,
        # index -> gfxobj hex (the dressed body parts)
        "anim_parts": {str(i): f"0x{g:08X}" for i, g in sorted(anim_parts.items())},
        # per-part SurfaceTexture substitution (texture identity)
        "texture_map": [
            {"index": t["index"], "old": f"0x{t['old']:08X}", "new": f"0x{t['new']:08X}"}
            for t in texture_map
        ],
        # head detail textures (applied to the head part, index 16, as
        # part of texture identity)
        "head": {
            "palette_base": _hex(dids.get(DID_PALETTE_BASE)),
            "eyes_texture": _hex(dids.get(DID_EYES_TEXTURE)),
            "nose_texture": _hex(dids.get(DID_NOSE_TEXTURE)),
            "mouth_texture": _hex(dids.get(DID_MOUTH_TEXTURE)),
            "hair_palette": _hex(dids.get(DID_HAIR_PALETTE)),
            "eyes_palette": _hex(dids.get(DID_EYES_PALETTE)),
            "skin_palette": _hex(dids.get(DID_SKIN_PALETTE)),
        },
        # deferred: palette recolor (T3 color follow-on)
        "palettes_deferred": palettes,
    }
    return appearance


def _hex(v):
    return f"0x{v:08X}" if v is not None else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("aceworld", help="Path to the ACE-World repo root")
    ap.add_argument("wcid", type=int)
    ap.add_argument("out_json")
    args = ap.parse_args()

    root = Path(args.aceworld)
    weenie_root = root / "Database" / "3-Core" / "9 WeenieDefaults" / "SQL"
    if not weenie_root.exists():
        print(f"Weenie root not found: {weenie_root}", file=sys.stderr)
        return 1

    wfile = _find_weenie_file(weenie_root, args.wcid)
    if wfile is None:
        print(f"No weenie SQL for wcid {args.wcid} under {weenie_root}", file=sys.stderr)
        return 2

    print(f"Parsing {wfile.relative_to(root)} ...", flush=True)
    text = wfile.read_text(encoding="utf-8", errors="replace")
    appearance = parse_appearance(text, args.wcid)
    appearance["source_sql"] = str(wfile.relative_to(root))

    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(appearance, indent=2), encoding="utf-8")

    np = len(appearance["anim_parts"])
    nt = len(appearance["texture_map"])
    print(f"Wrote {out}")
    print(f"  setup={appearance['setup_id']} anim_parts={np} "
          f"texture_map={nt} palettes_deferred={len(appearance['palettes_deferred'])}")
    if appearance["setup_id"] is None:
        print("  WARN: no Setup DID found; cannot assemble body.", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
