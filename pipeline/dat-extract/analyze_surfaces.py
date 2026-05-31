#!/usr/bin/env python3
"""
analyze_surfaces.py - reusable cell-surface analyzer (the "fishing rod").

For any extracted EnvCell, derive PURELY FROM THE DATA (the exported OBJ
geometry + .mtl surface->texture map + the texture PNGs):
  - which role each surface plays (wall / floor / ceiling), from face normals,
  - the texture (or solid color) each surface resolves to,
  - that texture's average colour (so we can reason about appearance without
    eyeballing every PNG).

This is the method for reproducing ANY room: it tells you, per cell, what
texture belongs on the walls vs floor vs ceiling. The reference screenshots
are only used afterwards to CONFIRM what this reports.

Usage:
  python analyze_surfaces.py <cell_hex> [<cell_hex> ...]
  python analyze_surfaces.py --find-walltex <hex>   # cells with <hex> on walls
  python analyze_surfaces.py --scan                  # summarise all cells
"""
import sys, os, re, glob, math
from collections import defaultdict
from PIL import Image

OBJDIR = os.path.join(os.path.dirname(__file__), "out", "academy_8602")


def parse_obj(path):
    verts, faces_by_surf = [], defaultdict(list)
    cur = None
    for ln in open(path):
        if ln.startswith("v "):
            verts.append(tuple(float(x) for x in ln.split()[1:4]))
        elif ln.startswith("usemtl "):
            cur = ln.split()[1]
        elif ln.startswith("f "):
            idx = [int(tok.split("/")[0]) - 1 for tok in ln.split()[1:]]
            faces_by_surf[cur].append(idx)
    return verts, faces_by_surf


def parse_mtl(path):
    out = {}
    cur = None
    for ln in open(path):
        m = re.match(r"newmtl\s+(\S+)", ln)
        if m:
            cur = m.group(1); out[cur] = {"tex": None, "kd": None}
        elif ln.startswith("map_Kd") and cur:
            t = re.search(r"textures/([0-9A-Fa-f]+)", ln)
            if t: out[cur]["tex"] = t.group(1).upper()
        elif ln.startswith("Kd ") and cur:
            out[cur]["kd"] = tuple(float(x) for x in ln.split()[1:4])
    return out


def face_normal(verts, idx):
    p0, p1, p2 = (verts[idx[0]], verts[idx[1]], verts[idx[2]])
    u = [p1[i] - p0[i] for i in range(3)]
    v = [p2[i] - p0[i] for i in range(3)]
    n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    L = math.sqrt(sum(c*c for c in n)) or 1.0
    return [c/L for c in n]


def tri_area(verts, idx):
    p0, p1, p2 = (verts[idx[0]], verts[idx[1]], verts[idx[2]])
    u = [p1[i]-p0[i] for i in range(3)]; v = [p2[i]-p0[i] for i in range(3)]
    cx = u[1]*v[2]-u[2]*v[1]; cy = u[2]*v[0]-u[0]*v[2]; cz = u[0]*v[1]-u[1]*v[0]
    return 0.5*math.sqrt(cx*cx+cy*cy+cz*cz)


_avgcache = {}
def tex_avg(hexid):
    if hexid in _avgcache: return _avgcache[hexid]
    p = os.path.join(OBJDIR, "textures", f"{hexid}.png")
    if not os.path.exists(p):
        _avgcache[hexid] = None; return None
    im = Image.open(p).convert("RGB").resize((16, 16))
    px = list(im.getdata())
    r = sum(c[0] for c in px)//len(px); g = sum(c[1] for c in px)//len(px); b = sum(c[2] for c in px)//len(px)
    _avgcache[hexid] = (r, g, b); return (r, g, b)


def color_label(rgb):
    if rgb is None: return "?"
    r, g, b = rgb
    if b > r + 10 and b > g - 5: return "blue/grey"
    if r > g + 15 and g > b: return "brown"
    if abs(r-g) < 15 and abs(g-b) < 15: return "grey"
    return f"({r},{g},{b})"


def analyze(cell_hex):
    obj = os.path.join(OBJDIR, f"cell_{cell_hex}.obj")
    mtl = os.path.join(OBJDIR, f"cell_{cell_hex}.mtl")
    if not os.path.exists(obj):
        return None
    verts, faces = parse_obj(obj)
    mat = parse_mtl(mtl)
    rows = []
    for surf, fl in faces.items():
        area = {"floor": 0.0, "ceil": 0.0, "wall": 0.0}
        tot = 0.0
        for idx in fl:
            n = face_normal(verts, idx); a = tri_area(verts, idx); tot += a
            if n[2] > 0.7: area["floor"] += a
            elif n[2] < -0.7: area["ceil"] += a
            else: area["wall"] += a
        role = max(area, key=area.get) if tot else "?"
        info = mat.get(surf, {})
        tex = info.get("tex"); kd = info.get("kd")
        avg = tex_avg(tex) if tex else (tuple(int(c*255) for c in kd) if kd else None)
        rows.append((surf, role, round(tot/10000, 1), tex or (f"solid{tuple(round(c,2) for c in kd)}" if kd else "none"), color_label(avg), avg))
    return rows


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return
    if args[0] == "--find-walltex":
        want = args[1].upper()
        for obj in sorted(glob.glob(os.path.join(OBJDIR, "cell_*.obj"))):
            cid = os.path.basename(obj)[5:-4]
            rows = analyze(cid) or []
            for surf, role, area, tex, lbl, avg in rows:
                if role == "wall" and tex == want:
                    print(f"0x{cid}: {surf} WALL tex={tex} area={area}m^2")
        return
    if args[0] == "--scan":
        for obj in sorted(glob.glob(os.path.join(OBJDIR, "cell_*.obj"))):
            cid = os.path.basename(obj)[5:-4]
            rows = analyze(cid) or []
            wall = [r for r in rows if r[1] == "wall"]
            floor = [r for r in rows if r[1] == "floor"]
            wtex = ",".join(f"{r[3]}:{r[4]}" for r in sorted(wall, key=lambda r:-r[2])[:2])
            ftex = ",".join(f"{r[3]}:{r[4]}" for r in sorted(floor, key=lambda r:-r[2])[:1])
            print(f"0x{cid}  WALL[{wtex}]  FLOOR[{ftex}]")
        return
    for cid in args:
        cid = cid.replace("0x", "").replace("0X", "").upper()
        rows = analyze(cid)
        print(f"\n=== cell 0x{cid} ===")
        if rows is None:
            print("  (no OBJ)"); continue
        for surf, role, area, tex, lbl, avg in sorted(rows, key=lambda r: -r[2]):
            print(f"  {surf:10} {role:6} area={area:6}m^2  tex={tex:12} {lbl:10} avg={avg}")


if __name__ == "__main__":
    main()
