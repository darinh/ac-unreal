---
name: ac-dat-extraction
description: "Use when extracting any asset or data from the Asheron's Call client DAT files in this repo — via the acdat CLI. Covers the DAT file-type taxonomy, the acdat commands, the AC->UE coordinate transform, the engine-neutral intermediates (OBJ/PNG/JSON), and the trust-nothing verification discipline (provenance, analyze_surfaces, answer-key confirm). Also covers indoor EnvCell geometry, surfaces/textures, props, and lights extraction."
metadata:
  category: extraction
---

# Extracting AC data with `acdat`

Bridge from `client_*.dat` to engine-neutral intermediates. We **do not
re-implement the DAT reader** — `acdat` (`pipeline/dat-extract`, C#) wraps
ACEmulator's `ACE.DatLoader`, the canonical parser. The UE side consumes only the
intermediates (OBJ/PNG/JSON), no .NET at runtime. Full reference:
`docs/migration/extraction-methodology.md`.

## DAT databases
- `client_portal.dat` — almost everything (models, textures, surfaces,
  environments, animations, sounds, particles, fonts, rules tables).
- `client_cell_1.dat` — world spatial data (outdoor landblock heightfields,
  indoor EnvCells, LandblockInfo).
- `client_highres.dat` — hi-res texture overrides. `client_local_English.dat` —
  localized strings/UI/fonts.
Record the DAT **iteration** with every export (provenance, not a constant).
Close `acclient.exe` first — a running client locks the files.

## File-type taxonomy (high bits = type; see methodology §2 for the table)
Key types: GfxObj `0x01` (meshes) · Setup `0x02` (multi-part models) · Animation
`0x03` · Palette `0x04` · SurfaceTexture `0x05` · Texture `0x06/0x07` · Surface
`0x08` · MotionTable `0x09` · Environment `0x0D` (indoor templates) · DegradeInfo
`0x11` (LOD) · Scene `0x12` (outdoor scatter) · RegionDesc `0x13` (sky/fog/
day-night/terrain) · ClothingTable `0x10` · ParticleEmitterInfo `0x32`.
**Cell DB IDs are spatial:** landblock = `(X<<8)|Y` high-16; low-16 `0x0001-0x0040`
= outdoor land cells, `0x0100-0xFFFD` = indoor EnvCells, `0xFFFE` = LandblockInfo.

## acdat commands (verify a signature in `Program.cs` before scripting)
`info` · `list-landblocks` · `landblock-info <LLLL>` · `list-envcells <LLLL>` ·
`envcell-info <id>` · `export-envcell <id> <out.obj>` · `export-academy <LLLL>
<dir>` · `dump-academy-layout/-statics/-lights <LLLL> <out.json>` ·
`export-setup` · `export-landblock <LLLL> <out.aclb>` · `dump-poly-uvs` ·
`audit-portals`. Analysis: `analyze_surfaces.py <cell_hex>` derives per-surface
role (wall/floor/ceiling)+texture+avg-color from the exported OBJ/MTL.

## Coordinate & orientation transform (PROVEN for the exporter's OBJ/import convention — methodology §4)
The exporter treats AC as right-handed, Z-up, metres and UE as left-handed, Z-up,
cm, and bakes the transform so OBJs import at scale 1.0. **This is verified for the
repo's render/import path.** The retail *simulation/wire* coordinate convention
(handedness, up-axis, units, landblock extent) remains `contract/` §0 `[VERIFY]`
(ADR-0010) — do not assume the exporter convention equals the sim convention.
- Position: `UE.X = AC.Y*100`, `UE.Y = AC.X*100`, `UE.Z = AC.Z*100` (swap X<->Y).
- Winding: **reverse** (the X<->Y swap flips chirality).
- Quaternion: serialized **W,X,Y,Z** on disk; layout JSON emits `{W, -Y, -X, -Z}`.
- UVs: AC origin is **top-left**, same as UE — **do NOT flip V**.
- Indoor polys: triangulate as a fan from vertex 0; `PosUVIndices[k]` selects the
  UV per corner (a vertex can carry several UVs — emit one `vt` per (vertex,UV)).
- Portal openings (`Stippling == NoPos`) are skipped (ADR-0008) so you see through
  to the neighbouring cell, not an opaque placeholder.

## Verification discipline (trust nothing — methodology §7)
Prior exports shipped real bugs (UV flip, light-coord doubling, NaN bounds,
ignored per-poly UVs, stale diagnostic material). For each layer: derive from the
DAT, verify (counts vs `CellStruct`; `analyze_surfaces.py` for texture identity;
face-on render for UV/decode), THEN confirm against the answer-key screenshot.
Re-running `acdat` is NOT an independent check — cross-check against ACViewer /
a manual DAT read. **Recompute metrics; do not trust prose** (the lights JSON
silently regressed twice). Distinguish texture *identity* (which surf->which
texture) from texture *mapping* (which UV per corner) — separate failure modes.

## Gotchas
P8/INDEX16 textures serialize a trailing `DefaultPaletteId` after pixels — a
reader that skips it desyncs everything after. Mip = `Textures[Count-1]` (last,
full-res). Generate mips in UE or distant surfaces shimmer. `Stab.Frame` is
**landblock-absolute** (do not compose with the cell frame — that doubling bug
hit lights and statics).
