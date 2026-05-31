# Extraction Methodology - where & how to pull AC world data

Technical reference behind the [master plan](README.md). It documents where
each kind of data lives in the retail DAT files, how to extract it, how to
transform it to Unreal's conventions, and the gotchas learned so far.
Recipes here are meant to be replayed for any zone.

> Read [LEGAL.md](../../LEGAL.md) first: no AC assets are committed; each user
> extracts from their own client. Terms used here are defined in
> [glossary.md](glossary.md). Facts below are tagged PROVEN / PARTIAL / OPEN
> and, where verified against source, cite it. Source-of-truth for AC data
> semantics is the ACEmulator `ACE.DatLoader` / `ACE.Server` code.

---

## 1. Data sources - the retail DAT files

A retail install (canonical path `C:\Turbine\Asheron's Call\`) ships three
content databases. Close `acclient.exe` first; a running client holds
exclusive file locks.

| File | DatDatabaseType | Holds |
|------|-----------------|-------|
| `client_portal.dat` | Portal | Almost everything: models, textures, surfaces, environments, animations, sounds, particles, fonts, rules tables. |
| `client_cell_1.dat` | Cell | World spatial data: outdoor landblock heightfields, indoor EnvCells, LandblockInfo. |
| `client_highres.dat` | Portal | High-resolution texture overrides (same ID scheme as portal textures). |
| `client_local_English.dat` | Language | Localized strings, UI layouts, fonts-local, string state. |

**Provenance, not spec:** the install we tested reads as portal iteration
2072 / cell iteration 982. These are *the versions we validated against*, not
enforceable constants. ACE reads the iteration from each DAT header at load
time and never hardcodes it. Record the iteration with any export so results
are reproducible; do not treat the numbers as a requirement.

We do not re-implement the DAT reader. ACEmulator's `ACE.DatLoader` (C#) is
the canonical parser; `acdat` wraps it.

---

## 2. The file-type taxonomy (what ID range backs what)

Each DAT record's 32-bit ID encodes its type in the high bits (`DB`: P =
Portal, C = Cell, L = Language). Values below are read directly from
`ACE.DatLoader.DatFileType` attributes.

| Type | ID range | DB | Relevance |
|------|----------|----|-----------|
| GfxObj | `0x01000000-0x0100FFFF` | P | Meshes - geometry of parts/props/items/body pieces. |
| Setup (SetupModel) | `0x02000000-0x0200FFFF` | P | Multi-part models (parts + PlacementFrames + scale). |
| Animation | `0x03000000-0x0300FFFF` | P | Keyframes; `PosFrames` carry root motion. |
| Palette | `0x04000000-0x0400FFFF` | P | 256-color tables for paletted textures + recolors. |
| SurfaceTexture | `0x05000000-0x05FFFFFF` | P | Indirection: Surface -> its Texture list. |
| Texture (RenderSurface) | `0x06000000-0x07FFFFFF` | P | Texture image pixels. |
| Surface | `0x08000000-0x0800FFFF` | P | Material def: texture or solid color + flags. |
| MotionTable | `0x09000000-0x0900FFFF` | P | Motion command -> AnimData (anim id, frame range, framerate). |
| Wave | `0x0A000000-0x0A00FFFF` | P | Sound samples. |
| Environment | `0x0D000000-0x0D00FFFF` | P | Indoor geometry templates (`Cells[CellStructure]`). |
| ChatPoseTable | `0x0E000007` | P | Chat-emote animation mappings. |
| ObjectHierarchy | `0x0E00000D` | P | Singleton body-part parent/child hierarchy. |
| CharacterGenerator | `0x0E000002` | P | Player starting appearance/equipment + per-sex CombatTable ref. |
| Rules tables (Skill/Spell/Xp/Combat/etc.) | `0x0E0000xx`, `0x30…`, `0x38…` | P | Mostly server-authoritative via ACE. |
| PaletteSet | `0x0F000000-0x0F00FFFF` | P | Palette collections (recolor ranges). |
| Clothing (ClothingTable) | `0x10000000-0x1000FFFF` | P | Equipment/clothing substitution + recolor (see §5). |
| DegradeInfo | `0x11000000-0x1100FFFF` | P | GfxObj LOD chain (maps to UE Static Mesh LODs). |
| Scene | `0x12000000-0x1200FFFF` | P | Procedural outdoor scatter (trees/rocks) by terrain type. |
| Region (RegionDesc) | `0x13000000-0x1300FFFF` | P | Global sky/sun/moon/fog/ambient + land height table + terrain types. |
| KeyMap | `0x14000000-0x1400FFFF` | P | Keyboard -> action bindings. |
| RenderTexture | `0x15000000-0x15FFFFFF` | P | Newer render-layer types (mostly post-retail). |
| RenderMaterial | `0x16000000-0x16FFFFFF` | P | " |
| MaterialModifier | `0x17000000-0x17FFFFFF` | P | " |
| MaterialInstance | `0x18000000-0x18FFFFFF` | P | " |
| RenderMesh | `0x19000000-0x19FFFFFF` | P | " |
| SoundTable | `0x20000000-0x2000FFFF` | P | Event/ambient -> Wave mappings. |
| UiLayout | `0x21000000-0x21FFFFFF` | L | UI panel layouts (HUD). |
| EnumMapper | `0x22000000-0x22FFFFFF` | P | String-name -> enum-id lookup. |
| StringTable | `0x23000000-0x24FFFFFF` | L | Localized text tables. |
| DidMapper / DualDidMapper | `0x25…` / `0x27…` | P | Id remapping. |
| ActionMap | `0x26000000-0x2600FFFF` | P | Action descriptors. |
| CombatTable | `0x30000000-0x3000FFFF` | P | Per-stance attack/defense animation pairing (melee depends on this). |
| String | `0x31000000-0x3100FFFF` | P | Localized string objects (distinct from StringTable). |
| ParticleEmitterInfo | `0x32000000-0x3200FFFF` | P | Particle emitters (fire, magic). |
| PhysicsScript / PhysicsScriptTable | `0x33…` / `0x34…` | P | Scripted effect sequences (flame flicker, spell motions). |
| ItemMutation | `0x38000000-0x3800FFFF` | P | Item randomization rules. |
| MasterProperty | `0x39000000-0x39FFFFFF` | P | Property descriptors. |
| Font | `0x40000000-0x40000FFF` | P | HUD fonts. |
| FontLocal | `0x40001000-0x400FFFFF` | P | Localized font variants. |
| StringState | `0x41000000-0x41FFFFFF` | L | Per-string UI state (the main non-table Language content). |
| DbProperties | `0x78000000-0x7FFFFFFF` | P | Misc DB properties. |

**Cell DB IDs are spatial, not type-prefixed.** Landblock id = `(X << 8) | Y`
in the high 16 bits (e.g. `0x8602`). Within a landblock's low 16 bits:
- `0x0001-0x0040` -> the 8x8 = 64 outdoor **land cells**. There is no `0x0000`; `0x0041-0x00FF` are unused. (ACE `LandDefs`: FirstLandCellID=1, LastLandCellID=64; BlockLength=192 m, CellLength=24 m.)
- `0x0100-0xFFFD` -> indoor **EnvCell**s.
- `0xFFFE` -> LandblockInfo; `0xFFFF` -> the landblock surface.

---

## 3. Tooling - the `acdat` CLI

Built from `pipeline/dat-extract` (`dotnet build -c Release` ->
`bin/Release/net8.0-windows/acdat.exe`). Emits engine-neutral intermediates
(OBJ/PNG/JSON) consumed by the UE-side Python importers in `pipeline/ue-import`.

Registered commands (verify a signature against `Program.cs` before scripting
it; the dispatch switch is near the top):

```
acdat info <dat>
acdat list-landblocks <dat>
acdat landblock-info <dat> <LLLL>
acdat list-envcells <dat> <LLLL>
acdat envcell-info <dat> <fullCellId>
acdat dump-starterareas <dat>
acdat export-envcell <dat> <fullCellId> <out.obj>
acdat export-academy <dat> <LLLL> <outDir>                # all indoor cells -> per-cell OBJ/MTL
acdat dump-academy-layout <dat> <LLLL> <out.json>         # per-cell world transforms
acdat dump-academy-statics <dat> <LLLL> <out.json>        # StaticObjects (props) per cell
acdat dump-academy-lights  <dat> <LLLL> <out.json>        # lights per cell (see §6)
acdat export-academy-statics <dat> <statics.json> <outDir># NB: middle arg is the statics JSON, not a landblock id
acdat export-setup <dat> <setupId> ...
acdat export-landblock <dat> <LLLL> <out.aclb>            # outdoor heightfield
```

**Analysis / verification tools** (downstream of export):
- `analyze_surfaces.py <cell_hex>` (in `pipeline/dat-extract/`) - the reusable
  "fishing rod": from the exported OBJ+MTL+textures it derives, per surface, the
  **role** (wall/floor/ceiling, from face normals), the **resolved texture**, and
  that texture's **average colour**. Tells you what texture belongs on which
  faces of any cell. `--scan` summarises all cells; `--find-walltex <hex>` finds
  cells using a texture on their walls. Use it to identify a room and to verify
  extraction, *then* confirm against the answer-key screenshot.

**Commands still to add** (per category): `export-texture` (Surface -> PNG with
palette applied), `export-gfxobj`, `dump-clothing`, `export-particle`,
`dump-motiontable`, `export-region`, `export-scene`, `export-ui-layout`, and a
`dump-poly-uvs <cell>` to expose `PosUVIndices` for UV verification.

> `Program.cs` is ~1900 lines with no section map yet (tracked in the
> remediation backlog). Search the command switch for the entry point, then the
> `Commands.<Name>` method.

---

## 4. Coordinate & orientation transform (AC -> UE) `[PROVEN]`

AC on-disk / ACE math: right-handed, Z-up, metres. (The original D3D7 client
rendered left-handed; we treat the data as RH end-to-end and convert once.)
UE: left-handed, Z-up, centimetres. The exporter bakes this in so OBJs drop
into UE at Import Scale = 1.0.

- **Position:** `UE.X = AC.Y * 100`, `UE.Y = AC.X * 100`, `UE.Z = AC.Z * 100` (swap X<->Y, m->cm).
- **Normals:** same X<->Y swap, no scale.
- **Triangle winding:** reverse (emit `v0, v2, v1`); the X<->Y swap flips chirality, reversing keeps outward normals outward.
- **Orientation (quaternion):**
  - On disk a Frame serializes its quaternion as **W, X, Y, Z** (W first; ACE `Frame.cs` reads qw,qx,qy,qz in that order). In-memory .NET `Quaternion` is `(X,Y,Z,W)`.
  - Our layout JSON emits keys `{w,x,y,z}` with values `{W_ac, -Y_ac, -X_ac, -Z_ac}` to land in UE's basis (see `DumpAcademyLayout`). State this when consuming the JSON so the next reader does not guess.
- **UVs:** AC uses a **top-left origin** (V increases downward), same as UE, so do **not** flip V. Use `vv` directly. (Confirmed: ACViewer negates V only when exporting to OBJ, which is bottom-left.) `[PROVEN]` for cells (`import_academy.py`); `import_statics.py` was fixed to match but props still need a re-import to take effect.

---

## 5. Per-asset extraction recipes

### Indoor room geometry (the room shell) `[PROVEN]`
1. `EnvCell (cell DB)` -> `EnvironmentId`, `CellStructure` index, world `Position` (Frame).
2. `Environment (0x0D)` -> `Cells[CellStructure]` -> `CellStruct`.
3. `CellStruct.VertexArray.Vertices` -> `SWVertex{ Origin, Normal, UVs[] }`. No color (confirmed: `SWVertex` is position/normal/UV only). AC paints surfaces via runtime per-vertex Gouraud (`dot(N,-L)+ambient`) multiplied into the texture, so pure-black surfaces are invisible without light/ambient. `[PROVEN, ACViewer shader]`
4. `CellStruct.Polygons` -> each `Polygon{ NumPts, VertexIds, PosUVIndices, NegUVIndices, PosSurface, NegSurface, CullMode }`.
   - Triangulate as a **fan from vertex 0** (`v0, vi, vi+1`).
   - `PosSurface` / `NegSurface` are signed indices into `EnvCell.Surfaces` (front / back face). Honor `CullMode` for one- vs two-sided faces.
   - UVs come from `PosUVIndices[k]` selecting which entry of vertex `VertexIds[k]`'s UV list to use (NOT vertex-index = UV-index). A single `SWVertex` can carry several UVs, so the exporter emits one `vt` per (vertex, UV-index) and each polygon corner references `PosUVIndices[k]`, falling back to index 0 only when the array is absent (`NoPos` stippling). This mirrors ACViewer `FileExport.cs` (`vertexUVs[(v, i < PosUVIndices.Count ? PosUVIndices[i] : 0)]`). `[PROVEN]` cell `0x86020100`: 13 verts but 20 UVs, and faces now decouple the position index from the UV index. The earlier collapse to `UVs[0]` (vertex-index = UV-index) was a confirmed bug, now fixed in `ExportEnvCell`.
   - **Confirmed blocking symptom (Step 0, 2026-05-30):** in the first-room candidate `0x860201AD` the walls render the wrong texture identity (brown `06003C9C` where the reference shows grey-blue masonry; `06003C9A` blue-grey blocks appear mapped to the floor). This must be resolved before any room can be visually matched to a reference. Suspects to check in order: (1) per-surface `surf_N -> EnvCell.Surfaces[]` resolution and the `Textures[last]` mip pick; (2) `PosUVIndices` per-face UV selection; (3) which polygon group is wall vs floor. Verify against the source PNGs in `out/academy_8602/textures/`.
5. Emit OBJ (transform per §4) + `.mtl` mapping `surf_N` -> texture/color.

### Textures & materials `[PARTIAL]`
- `Surface (0x08)`: textured -> `OrigTextureId -> SurfaceTexture (0x05) -> Textures[...]`; solid -> `ColorValue` (BGRA). Carries `Luminosity`, `Translucency`, `Diffuse`, `Type`.
- **Mip selection:** `SurfaceTexture.Textures` is ordered low-detail -> high; use `Textures[Count-1]` (the **last**) for full resolution. (The code does this; an earlier comment saying `Textures[0]` is wrong.)
- **Texture decode** by PFID (`SurfacePixelFormat`): DXT1/3/5; raw `R8G8B8 (20)`, `A8R8G8B8 (21)`, `R5G6B5 (23)`, `A4R4G4B4 (26)`, `A8 (28, clipmap alpha)`; paletted `P8 (41)`, `INDEX16 (101)`; landscape `CUSTOM_LSCAPE_R8G8B8 (243)`, `CUSTOM_LSCAPE_ALPHA (244)`; `CUSTOM_RAW_JPEG`. **P8 and INDEX16 serialize a trailing `DefaultPaletteId` after the pixel data** - a reader that skips it desyncs every subsequent record. Apply `Palette (0x04)`; `OrigPaletteId` / `PaletteSet (0x0F)` give recolor overrides.
- **Mipmaps:** the DAT stores a single full-res image; D3D7 generated mips at load. The UE importer must generate mips or distant surfaces shimmer.
- **UE translation:** master material per shading class + one MaterialInstance per Surface. **Surface flags `Luminosity` / `Translucency` / `Diffuse` / `Type` are NOT consumed yet** (the importer currently substitutes warm grey for pure-black solid surfaces as a **temporary** stand-in until runtime-lighting honoring lands). Treat the "honor these flags" recipe as planned, not implemented. `[OPEN]`

### Props / furniture (Setups) `[PARTIAL]`
- `EnvCell.StaticObjects[]` = `Stab{ Id = Setup(0x02), Frame }`. `Frame` is **landblock-absolute** (see §6).
- `Setup` -> part `GfxObj (0x01)` list + per-part `PlacementFrame` + scale -> assemble. **Static props** vs **animated actors** differ: animated setups carry `DefaultAnimation` / `DefaultMotionTable` and need an animation path; statics do not.
- `DegradeInfo (0x11)` gives the LOD chain (`MinDist`/`IdealDist`/`MaxDist` -> alternate GfxObjs) -> UE Static Mesh LODs.

### Lights `[PARTIAL]`
- A Setup may carry `LightInfo{ ViewerSpaceLocation, Color, Intensity, Falloff, ConeAngle }`. `ViewerSpaceLocation` is a **Frame** (position + quaternion); spot/cone lights need the orientation for direction. World light pose = `Stab.Frame` (absolute) composed with the light's local Frame.

### NPCs / creatures `[OPEN]`
- Body = `Setup` of body-part `GfxObj`s wired by `ObjectHierarchy (0x0E00000D, singleton)`. Animation is **part-based rigid transforms, no skinning/bones** (confirmed for all creatures). `[PROVEN, source]`
- Equipment/clothing via `ClothingTable (0x10)` as **substitution, not overlay**: `ClothingBaseEffects[setupId] -> CloObjectEffect[]` replaces the GfxObj at a part index and swaps old SurfaceTexture ids for new (`CloTextureEffect`); `ClothingSubPalEffects` applies palette-range recolors on top; `CoverageMask` priority hides occluded parts when items stack.
- Player base looks from `CharacterGenerator`; NPC looks from server weenie defaults (ACE).

### World - outdoor (distinct pipeline) `[OPEN]`
Indoor (explicit polygon EnvCells) and outdoor are **structurally different
importers**; do not assume the indoor recipe scales to terrain.
- `CellLandblock` 9x9 height + terrain-type indices; resolve heights via `RegionDesc.LandDefs.LandHeightTable` to metres.
- Terrain rendering uses alpha-blended terrain types; `LandVertex` carries 6 UV channels (base + 3 overlay + 2 road). OBJ cannot hold these; outdoor needs glTF or a custom intermediate.
- `Scene (0x12)` scatters vegetation/rocks by terrain type; `RegionDesc (0x13)` drives sky/fog/sun/ambient and day-night.

### Animation / particles / audio / UI `[OPEN]`
- `MotionTable (0x09)` -> per-command `AnimData{ AnimId, LowFrame, HighFrame, Framerate }`; `Animation (0x03)` keyframes + `PosFrames` root motion; `AnimationHook`s fire timed events: `AttackHook` (damage frames - gates combat), `SoundHook`, `EffectHook`, `EtherealHook` (collision toggle), `SetOmegaHook`, etc. These are the gameplay-timing source the `contract/physics-feel-spec-request.md` cares about.
- `ParticleEmitterInfo (0x32)` + `PhysicsScript (0x33)`; `Wave (0x0A)` + `SoundTable (0x20)`; `UiLayout (0x21)` + `Font (0x40)` + `StringTable`.

### Exchange-format note
OBJ is a **transitional** intermediate: it carries position/normal/UV0 only -
fine for AC indoor cells (no vertex color, no skinning) but it cannot express
outdoor multi-UV terrain or animated rigs. Plan to move those categories to
glTF (or a custom format). Do not treat OBJ as permanent.

---

## 6. The light/static coordinate fix (worked example)

Template for "verify against known-good geometry, then fix the exporter."

- **Symptom:** placed torch lights rendered far outside their cells.
- **Cause:** the dump treated `Stab.Frame.Origin` as cell-local and computed `world = cellPos + rotate(cellOrient, stabLocal)`. But `EnvCell.StaticObjects[].Frame` is already **landblock-absolute** (ACE assigns `Stab.Frame` directly as the object's `Position.Frame` with no composition against the cell frame), so adding `cellPos` doubled every coordinate.
- **Fix:** use `Stab.Frame` directly (no `cellPos` add, no `cellOrient` re-rotation).
- **Status:** `DumpAcademyLights` is fixed; the **canonical** artifact `pipeline/dat-extract/samples/academy_8602_lights.json` (sha `e2ab7553…`) has median light-to-cell-origin **2.7 m, 125/132 within 6 m**. `[PARTIAL]` (placement only; the lit *render* is not done, and see caveats below).
  - **Regression note (do not repeat):** the canonical file silently regressed to the doubled-coord data twice during iteration; the correct data only survived in a `_fixed` sibling. Always **recompute** the median against `samples/academy_8602_layout.json` after touching this file; do not trust the prose. Regenerate cleanly with `acdat dump-academy-lights`. (Git-ignored `out/*` copies are not canonical and were stale ~232 m off.)
  - **Garbage field:** `cone_angle_degrees` reads ~-2.5e10 for every entry (uninitialized/leaked ConeAngle). Ignore it; gate spot-cone emission on `is_point_light == false` and fix the decode before using cone angles.
- **Still OPEN:** `DumpAcademyStatics` (props) has the *same* doubling bug unfixed (`Program.cs` ~line 828-833: `cellPos + RotateAcVec(cellOrient, localPos)`). Apply the identical fix, then rebuild `acdat` and re-export before the furniture milestone.

---

## 7. Verifying extraction is correct AND UE-compatible (trust nothing)

The exported intermediates and import scripts were written by a prior agent and
have already shipped real bugs: a UV V-flip (textures upside-down), light-coord
doubling (lights 140 m outside cells), NaN mesh bounds, per-polygon UVs ignored,
and a leftover diagnostic material left bound to a wall. **Treat every layer as
suspect until confirmed against ground truth.** The DAT structures are the
source of truth for the data; the reference screenshots are the answer key for
the final visual confirm (never the input).

Per-layer verification (status as of 2026-05-30, exemplar cell `0x860201AD`):

| Layer | How to verify | Status |
|-------|---------------|--------|
| Geometry + coord transform | vertex/poly counts vs `EnvCell.CellStruct`; cell lands at the right world pos | CONFIRMED (renders coherent, correct place) |
| Surface->texture identity | `analyze_surfaces.py` derives role+texture per surface; confirm vs answer key | CONFIRMED (`860201AD`: walls `06003C9C` brown, floor `06003C9A` blue = starting-view screenshot) |
| UV orientation | top-left origin, no V-flip | CONFIRMED (fixed + face-on test) |
| UV per-face selection (`PosUVIndices`) | exporter emits one `vt` per (vertex, UV-index) and indexes faces by `PosUVIndices[k]` | CONFIRMED (cell `0x86020100`: 13 verts -> 20 UVs; old `UVs[0]` collapse fixed, matches ACViewer) |
| Texture decode (format/palette) | PNGs plausible; audit P8/INDEX16 + palette overrides | PARTIAL |
| Two-sided / `CullMode` / `NegSurface` | not consumed by importer | UNVERIFIED |
| Ceiling surface | `0x08000034` solid-black sentinel; real ceiling is wood-beam **statics** | needs the statics pass |
| UE material binding | each slot -> correct MI | CONFIRMED for `860201AD` (caught + removed a leftover `M_HotPinkDiagnostic` on the wall slot) |
| Mesh bounds / NaN | bounds non-zero, finite | CONFIRMED for cells (fixed earlier); setups still suspect |

Independence note: re-running `acdat` is *not* independent of itself. For a
true second opinion, cross-check counts/surfaces against ACViewer or a manual
DAT read. At minimum: `analyze_surfaces.py` + answer-key confirm for textures,
and a face-on render compared to the screenshot at tier T1/T3 for UV/decode.

**Lesson (the "fish"):** identify and reproduce a room by deriving its
surfaces/textures/UVs from the data with `analyze_surfaces.py`, *verify each
layer*, then confirm against the answer key. The earlier "walls are the wrong
texture" panic was a **false alarm** - a reference misread plus a stale UE
binding, not an extraction error. Verification caught that.

## 8. Known gotchas (operational)

- **Project lock:** a stale `UnrealEditor-Cmd.exe` holds the `.uproject` lock; headless scripts then fail silently (exit 1/255, no output). Kill all `UnrealEditor*` processes before any run.
- **Never delete+recreate master materials** that have MaterialInstances: new params get new GUIDs and every instance's overrides fall back to defaults (grey). Modify masters in place, or re-apply overrides by name afterward.
- **Auto-exposure off** for deterministic renders: `DefaultEngine.ini` `r.DefaultFeature.AutoExposure=False` + `[SystemSettings] r.EyeAdaptationQuality=0`. Otherwise eye-adaptation latches onto a bright element and crushes the rest to black.
- **Lumen / Nanite / HW-RT are currently DISABLED** in `Config/DefaultEngine.ini` (procedural meshes + large instance counts crashed the RT/Nanite paths; `r.DynamicGlobalIlluminationMethod=0`, `r.Nanite=0`, `r.RayTracing=False`). This is the live project state. The root `README.md` decision log (#19) still describes Lumen as enabled - that entry is **stale**; the ini is authoritative. A decision record should resolve whether to re-enable Lumen once meshes are Nanite-safe.
- **Headless material edits** must avoid `recompile_material` (crashes Slate under `-RenderOffScreen`); UE compiles lazily on load.
- **Texture import** through Interchange crashes headless (ContentBrowser refresh asserts); import textures once in the interactive editor, then bind headlessly.
- **`-ExecCmds` separator is a comma**, not a semicolon; pass via env var to dodge cmd.exe arg-splitting.
- **No em-dashes in code, scripts, or PowerShell string literals**: they have caused cp1252/PowerShell parsing failures here. Prose markdown is exempt (it never goes through PowerShell), but prefer hyphens for consistency.
