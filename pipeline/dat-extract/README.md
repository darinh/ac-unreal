# pipeline/dat-extract

C# CLI that extracts content from Asheron's Call DAT files via the
ACEmulator community's `ACE.DatLoader` library. **Phase 5** — the
bridge between AC's `client_*.dat` and our intermediate exchange
formats (`.aclb` for landblock surfaces; Wavefront `.obj` for indoor
cell geometry; JSON layout for cell placement).

## Why C#

The DAT format is solved by `ACE.DatLoader` (years of community work,
~5k lines of C#). Re-implementing it in C++ would be weeks of effort
with high regression risk. Wrapping it via a small C# CLI is cheap and
keeps the canonical reader where the community maintains it.

The CLI emits language-neutral intermediate files (`.aclb` binary for
landblock heightfields; `.obj` text for indoor geometry; JSON for
layout) that the UE5 side consumes — no .NET runtime dependency at
game time.

## Prerequisites

- **.NET 8 SDK** (or later) — `dotnet --version` to check.
- **Local ACE clone** at `~/repos/ACE/` (specifically
  `~/repos/ACE/Source/ACE.DatLoader/ACE.DatLoader.csproj`). The
  `AcDatExtract.csproj` references it via relative path.
- **AC DAT files**. Canonical location: `C:\Turbine\Asheron's Call\`
  (a live AC install).
  **⚠ Close `acclient.exe` before extracting** — the running client
  holds exclusive locks on the DATs.

## Build

```powershell
cd pipeline\dat-extract
dotnet build -c Release
```

The built `acdat.exe` lands at `bin\Release\net8.0\acdat.exe`.

## Commands

```powershell
$dat = "C:\Turbine\Asheron's Call"
$acdat = ".\bin\Release\net8.0\acdat.exe"

# --- Discovery / metadata --------------------------------------------

# Open all DATs, print iteration + record counts.
& $acdat info $dat

# Walk the Cell DAT and list every landblock surface entry.
& $acdat list-landblocks $dat

# Dump the canonical AC starter-town landblocks (Holtburg, Shoushi,
# Yaraq, Sanamar, OlthoiLair) from CharGen in PortalDat.
& $acdat dump-starterareas $dat

# Print a summary of one landblock by its high-16 hex ID.
# (LandblockX is the top byte, LandblockY the next byte.)
& $acdat landblock-info $dat 8602   # Aluvian Training Academy

# List indoor EnvCell IDs in a landblock (cell IDs with high byte of
# low-16 != 0 are indoor; 0x0001..0x00FE are outdoor cells).
& $acdat list-envcells $dat 8602

# Print one cell's metadata (position, portals, static objects).
& $acdat envcell-info $dat 860201AD   # Academy spawn cell

# --- Extraction -------------------------------------------------------

# Export ONE indoor cell to a Wavefront OBJ file.
& $acdat export-envcell $dat 860201AD .\out\cell_860201AD.obj

# Bulk-export EVERY indoor cell in a landblock to per-cell OBJs.
# For the Aluvian Academy (568 cells, ~0.8 MB total, ~30 sec):
& $acdat export-academy $dat 8602 .\out\academy_8602

# Dump per-cell world-space layout JSON. Pair with export-academy:
# UE-side import uses the OBJ for geometry + this JSON for placement.
& $acdat dump-academy-layout $dat 8602 .\out\academy_8602\layout.json

# Export a landblock SURFACE (outdoor heightfield) to v1 .aclb.
# Useful for landblocks with outdoor terrain; indoor-only landblocks
# (like the academy) have a degenerate surface, so prefer the
# export-academy/dump-academy-layout pair for those.
& $acdat export-landblock $dat A9B4 .\out\holtburg-a9b4.aclb
```

## What's exported today

### Outdoor landblock (`export-landblock`)
- 9×9 heightfield + 1 texture-layer (terrain-type indices).
- **TODO**: heights currently written as raw ACE byte-indices cast to
  float; a follow-up pass will resolve them through
  `PortalDat.RegionDesc.LandDefs.LandHeightTable` into real metres.

### Indoor EnvCell (`export-envcell`, `export-academy`)
- Triangulated Wavefront OBJ with positions + normals + UV0.
- One OBJ group per material surface (`g surf_<idx>` / `usemtl surf_<idx>`).
- **UE-ready coordinates** — left-handed Z-up, centimetres. The Phase 0
  coord transform is baked in at export time: `UE.X = AC.Y * 100`,
  `UE.Y = AC.X * 100`, `UE.Z = AC.Z * 100`. Triangle winding is flipped
  to compensate for the chirality reversal so outward normals stay
  outward. **Drop straight into UE5 at Import Uniform Scale = 1.0** —
  no per-import dialog tweaks needed.
- **Verified Phase 5**: full Aluvian Training Academy (landblock
  `0x8602`, 568 EnvCells) extracts cleanly in ~30s — 7,396 vertices /
  5,756 polygons total.

### Layout (`dump-academy-layout`)
- JSON per-cell metadata (schema_version 2): position (XYZ in UE cm),
  orientation (quaternion — currently raw AC values, see TODO below),
  environment ID, portal count, static object count, OBJ filename.
- UE-side import reads this and instantiates a StaticMeshActor per cell
  at the right transform.
- **TODO (Phase 5d)**: the quaternion is still in AC's right-handed
  basis. Most academy cells use identity / axis-aligned 90° rotations so
  placement is approximately correct without the conjugation, but
  arbitrary orientations need the full transform.

## Committed sample fixtures

- `samples/cell_860201AD.obj` — the Aluvian Academy spawn cell
  (16 verts, 14 polys, 3 surfaces). Generated by
  `export-envcell` against `client_cell_1.dat` iteration 982 /
  `client_portal.dat` iteration 2072 (the end-of-retail / current ACE-
  compatible DAT versions). Reproducible from the live DATs via the
  CLI. Open in any 3D viewer (Blender, MeshLab, UE5) to inspect.

- `samples/academy_8602_layout.json` — full 568-cell layout for the
  Aluvian Academy. Same provenance as above. Same reproducibility.

## What's planned next

- Material extraction: resolve each `surf_N` reference to its actual
  `Surface` / `SurfaceTexture` / `Texture` in PortalDat, decode the
  AC palette + DXT compression, and emit PNG/EXR alongside.
- glTF output (alternative to OBJ): better material binding, embedded
  textures, supported by UE Interchange more cleanly.
- `export-mesh <gfxObjId> <out.gltf>`: extract a GfxObj (object meshes
  — props, weapons, armor, character bodies).
- `export-envcell` should also emit per-cell `static_objects` (Stab
  entries — torches, tables, lamps) as separate small meshes referenced
  in the layout JSON.
- UE-side: an Editor commandlet that consumes the layout JSON and
  bulk-imports the OBJs as StaticMeshAssets, placing one
  StaticMeshActor per cell.

## Why a separate CLI vs. a UE plugin

UE's editor scripting goes through Python or Blueprint commandlets, and
re-implementing DAT parsing inside the editor would duplicate
ACE.DatLoader's work. By emitting intermediate files, we keep the
extraction reproducible and editor-independent — same files can feed
the UE Editor's Interchange importer, a CLI batch import, or future
non-UE tools.
