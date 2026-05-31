"""Pure-python analysis of the academy layout to inform the outliner hierarchy.
Finds Z-levels and connected-component clusters (cells adjacent on the ~1000-unit
grid = a contiguous structure/section). No UE required."""
import json, collections

LAYOUT = r"C:\Users\darin\repos\ac-unreal\pipeline\dat-extract\samples\academy_8602_layout.json"
STAT = r"C:\Users\darin\repos\ac-unreal\pipeline\dat-extract\samples\academy_8602_statics.json"
LIGHT = r"C:\Users\darin\repos\ac-unreal\pipeline\dat-extract\samples\academy_8602_lights.json"
NPC = r"C:\Users\darin\repos\ac-unreal\pipeline\dat-extract\samples\academy_8602_npcs.json"

cells = json.load(open(LAYOUT))["cells"]
print("cell_count:", len(cells))

# Z levels
zlevels = collections.Counter(round(c["position"]["z"]) for c in cells)
print("Z levels (z->count):", dict(sorted(zlevels.items())))

# Grid step detection
xs = sorted(set(round(c["position"]["x"]) for c in cells))
ys = sorted(set(round(c["position"]["y"]) for c in cells))
print("X range:", xs[0], xs[-1], "distinct X:", len(xs))
print("Y range:", ys[0], ys[-1], "distinct Y:", len(ys))

# Connected components on grid (step 1000) within same Z (+ vertical link if same x,y)
STEP = 1000
pos2cell = {}
for c in cells:
    p = c["position"]
    key = (round(p["x"]), round(p["y"]), round(p["z"]))
    pos2cell[key] = c["cell_id"]

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

comps.sort(key=len, reverse=True)
print("connected components (grid-adjacent):", len(comps))
print("component sizes (top 15):", [len(c) for c in comps[:15]])

# instances per cell
def count_by_cell(path, key):
    d = json.load(open(path))
    items = d[key]
    cc = collections.Counter(i["cell_id"] for i in items)
    return cc, len(items)

stat_cc, stat_n = count_by_cell(STAT, "instances")
light_cc, light_n = count_by_cell(LIGHT, "lights")
npc_cc, npc_n = count_by_cell(NPC, "instances")
print("statics:", stat_n, "in", len(stat_cc), "cells")
print("lights:", light_n, "in", len(light_cc), "cells")
print("npcs:", npc_n, "in", len(npc_cc), "cells")

# cells that have content vs empty
content_cells = set(stat_cc) | set(light_cc) | set(npc_cc)
print("cells with any prop/light/npc:", len(content_cells))

# first room
fr = "0x860201AD"
print("FIRST ROOM", fr, "-> statics:", stat_cc.get(fr,0), "lights:", light_cc.get(fr,0), "npcs:", npc_cc.get(fr,0))
