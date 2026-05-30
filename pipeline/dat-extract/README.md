# pipeline/dat-extract

C# CLI that extracts content from Asheron's Call DAT files via the
ACEmulator community's `ACE.DatLoader` library. **Phase 5 scaffold** —
the bridge between AC's `client_*.dat` and our `.aclb` / future
intermediate formats (mesh glTF, texture PNG, etc.).

## Why C#

The DAT format is solved by `ACE.DatLoader` (years of community work,
~5k lines of C#). Re-implementing it in C++ would be weeks of effort
with high regression risk. Wrapping it via a small C# CLI is cheap and
keeps the canonical reader where the community maintains it.

The CLI emits language-neutral intermediate files (binary `.aclb` for
landblocks; future glTF for meshes; PNG/EXR for textures) that the UE5
side consumes — no .NET runtime dependency at game time.

## Prerequisites

- **.NET 8 SDK** (or later) — `dotnet --version` to check.
- **Local ACE clone** at `~/repos/ACE/` (specifically
  `~/repos/ACE/Source/ACE.DatLoader/ACE.DatLoader.csproj`). The
  `AcDatExtract.csproj` references it via relative path. If your ACE
  checkout is elsewhere, edit the `ProjectReference` in
  `AcDatExtract.csproj`.
- **Staged AC DAT files**. The decompile workspace at
  `~/repos/ac-client/binary/original/` is the canonical location
  (`client_portal.dat`, `client_cell_1.dat`, `client_highres.dat`,
  `client_local_English.dat`). The `ac-client/scripts/01-stage-binary.ps1`
  script stages these from the operator's RAR archive.

## Build

```powershell
cd pipeline\dat-extract
dotnet build -c Release
```

The built `acdat.exe` lands at `bin\Release\net8.0\acdat.exe`.

## Commands

```powershell
$dat = "C:\Users\darin\repos\ac-client\binary\original"
$acdat = ".\bin\Release\net8.0\acdat.exe"

# Open all DATs, print iteration + record counts.
& $acdat info $dat

# Walk the Cell DAT and list every landblock surface entry.
# (Useful for discovering valid landblock IDs.)
& $acdat list-landblocks $dat

# Print a summary of one landblock by its high-16 hex ID.
# (LandblockX is the top byte, LandblockY the next byte.)
& $acdat landblock-info $dat A9B4

# Export one landblock to our .aclb v1 intermediate format.
& $acdat export-landblock $dat A9B4 .\out\holtburg-a9b4.aclb
```

## What's exported today (Phase 5 scaffold)

- **Landblock surface**: 9×9 heightfield + 1 texture-layer (terrain-type
  indices). The heights are currently emitted as raw ACE indices cast
  to float; a follow-up pass will resolve them through
  `PortalDat.RegionDesc.LandDefs.LandHeightTable` into real metres.

## What's planned next

- `export-landblock` height-table resolution (real metres, not indices).
- `landblock-list-envcells <hexId>` — find indoor environment cells
  associated with a landblock (for Holtburg-area dungeons + the
  Aluvian Academy interior).
- `export-envcell <hexId>` — dump indoor cell geometry to the same
  intermediate format (FORMAT.md will need an EnvCell extension).
- `export-mesh <gfxObjId> <out.gltf>` — extract a GfxObj as glTF.
- `export-texture <surfaceTextureId> <out.png>` — extract a texture
  (decodes the AC palette + DXT compression to standard PNG).
- `find-academy` — heuristic search for the Aluvian Training Academy
  landblock + interior cell IDs by walking weenie references in
  ACE's WorldData SQL.

## Why this is a separate CLI vs. a UE plugin

UE's editor scripting goes through Python or Blueprint commandlets, and
re-implementing DAT parsing inside the editor would duplicate
ACE.DatLoader's work. By emitting intermediate files, we keep the
extraction reproducible and editor-independent — same files can feed
the UE Editor's Interchange importer, a CLI batch import, or future
non-UE tools.
