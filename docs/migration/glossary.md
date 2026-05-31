# Glossary — AC / DAT / migration terms

Terms used across the migration docs and the `acdat` / `pipeline` code.
AC-engine terms follow ACEmulator (`ACE.DatLoader` / `ACE.Server`) naming,
which is the de-facto reference vocabulary for the retail data.

## DAT / data structures

- **DAT files** — Asheron's Call's content databases: `client_portal.dat`
  (assets/rules), `client_cell_1.dat` (world space), `client_highres.dat`
  (hi-res texture overrides), `client_local_English.dat` (localized UI/strings).
- **PFID** — pixel-format ID on a `Texture` (DXT1/3/5, P8, INDEX16, A8, etc.).
- **Landblock** — a 192 m × 192 m world tile, addressed by an `XY` byte pair
  (e.g. `0x8602`). Subdivided into an 8×8 grid of 24 m **land cells**.
- **Land cell** — an outdoor cell within a landblock (cell IDs `0x0001–0x0040`).
- **EnvCell** — an *indoor* cell (dungeon/building interior), cell IDs
  `0x0100–0xFFFD` within a landblock. Has explicit polygon geometry.
- **LandblockInfo** — per-landblock record (`0xLLLLFFFE`) of buildings,
  EnvCell count, and embedded objects.
- **Environment** — `0x0D` portal-DB record holding indoor geometry templates
  (`Cells[CellStructure]` → CellStruct). Referenced by an EnvCell.
- **CellStruct** — one indoor cell's mesh: a vertex array + polygons + portals.
- **SWVertex** — a CellStruct vertex: position + normal + UV list. **No color.**
- **GfxObj** — `0x01` a single mesh (the actual geometry of a part).
- **Setup (SetupModel)** — `0x02` a multi-part model: a list of GfxObj parts,
  each with a **PlacementFrame** and scale. Furniture, items, creatures.
- **Stab** — an entry in `EnvCell.StaticObjects`: a `Setup` ID + a **Frame**.
  The placed props/lights in a room. (Frame is landblock-absolute.)
- **Surface** — `0x08` a material definition: texture *or* solid color, plus
  flags `Luminosity`, `Translucency`, `Diffuse`, `Type`.
- **SurfaceTexture** — `0x05` indirection from a Surface to its `Texture` list.
- **Texture (RenderSurface)** — `0x06`/`0x07` the actual image pixels.
- **Palette / PaletteSet** — `0x04` / `0x0F` color tables for paletted textures
  and recolors.
- **PosSurface / NegSurface** — a polygon's surface index for its front
  (positive) and back (negative) faces; signed indices into `EnvCell.Surfaces`.
- **PosUVIndices / NegUVIndices** — per-polygon arrays selecting which UV (from
  each vertex's UV list) to use on the positive/negative face.
- **CullMode** — a polygon's face-culling flag (front/back/none).
- **MotionTable** — `0x09` maps motion commands → `Animation` IDs (per object).
- **Animation** — `0x03` keyframe data (`PosFrames` carry root motion).
- **AnimationHook** — a timed event on an animation (attack/sound/effect/
  ethereal-collision frame). Gameplay timing comes from these.
- **ParticleEmitterInfo / PhysicsScript(Table)** — `0x32` / `0x33` / `0x34`
  emitters and scripted effect sequences (fire, spells).
- **ClothingTable** — `0x10` equipment/clothing as **substitution** (replace a
  body part's GfxObj + swap its textures) + palette-range recolors.
- **CoverageMask** — clothing priority bits deciding which occluded body parts
  to hide when items stack.
- **ObjectHierarchy** — singleton `0x0E00000D` body-part parent/child hierarchy.
- **RegionDesc** — `0x13` global sky/sun/moon/fog/ambient + land height table +
  terrain types ("lighting of day").
- **Scene** — `0x12` procedural scatter of trees/rocks/etc. across terrain.
- **DegradeInfo** — `0x11` LOD chain swapping a Setup's GfxObjs by distance.
- **ChatPoseTable** — `0x0E000007` chat-emote animation mappings.
- **StringState / StringTable / String** — localized text records (Language DB
  for StringState/StringTable; `0x31` String is Portal).
- **Weenie / WeenieDefaults** — server-side object templates (NPCs, items). The
  *appearance* of NPCs derives from these (via ACE), not from a client file.

## Transform / rendering terms

- **Frame / AFrame** — a position + orientation (quaternion). On disk the
  quaternion serializes **W, X, Y, Z** (W first).
- **Gouraud lighting** — per-vertex lighting AC computes at runtime
  (`dot(N, -L) + ambient`), then multiplies into the texture. There is no
  baked vertex color; black surfaces are invisible without light/ambient.
- **Right-handed (RH) vs left-handed (LH)** — AC's on-disk/ACE math is RH Z-up
  in metres; the original D3D7 client rendered LH. We treat the data as RH and
  convert to UE's LH Z-up centimetres at export.

## Project / tooling terms

- **acdat** — our C# CLI (`pipeline/dat-extract`) wrapping `ACE.DatLoader`.
- **ACEmulator (ACE)** — community open-source AC server + DAT loader; our
  reference for data semantics and (eventually) the live server. See
  [LEGAL.md](../../LEGAL.md) for usage stance.
- **ACViewer** — community DAT viewer; reference documentation only.
- **Two-lane architecture** — *simulation* (data-driven parity, in
  `pipeline/sim-core` + `contract/`) vs *presentation* (free to modernize, the
  UE render). See `contract/physics-feel-spec-request.md`.
