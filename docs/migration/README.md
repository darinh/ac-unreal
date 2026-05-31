# Asheron's Call → Unreal Engine: Migration Master Plan

This directory is the **canonical plan and runbook** for recreating the
Asheron's Call retail client in Unreal Engine 5. It exists so that any
agent (or human) can pick up a slice of the work, follow a documented
methodology, and produce results that match the retail client — without
re-deriving how AC's data works each time.

**Guiding principle:** *Get one space faithfully right, document exactly
how, then replay that methodology to scale out the rest of the world.* We
do not "boil the ocean." Every technique proven on the first room becomes
a reusable recipe in [`extraction-methodology.md`](extraction-methodology.md).

**"Faithful" is tiered, not "pixel-perfect."** AC is a DX7 fixed-function
sRGB renderer; UE5 is linear-HDR + filmic tonemap, so pixel equality is
impossible and not the bar. Acceptance is measured in tiers (use the
strictest that applies to the task):
- **T0 Topology** - vertex/face/UV counts round-trip; geometry matches the source cell.
- **T1 Identity** - every surface uses the *correct* texture/Surface id, correctly oriented (no flips/mirrors).
- **T2 Silhouette** - depth/shape matches the reference at a matched camera (e.g. SSIM on a depth render).
- **T3 Color** - sRGB delta-E within an agreed tolerance under matched lighting/ambient.
- **T4 Timing** - animation/effect hook frames match (per the AnimationHook spec) where relevant.

**Companion docs:** [`extraction-methodology.md`](extraction-methodology.md)
(how to extract) - [`glossary.md`](glossary.md) (terms) -
[`decisions/`](decisions/) (ADRs) - [`versions.md`](versions.md) (pins) -
[`recovery.md`](recovery.md) (backup/restore before destructive ops) -
[`../../LEGAL.md`](../../LEGAL.md) (IP posture, read first) - the *simulation*
lane lives in [`../../contract/`](../../contract/) (physics/feel parity is
data-driven there; this plan is the *presentation* lane).

**Current target:** the first room of the Aluvian Training Academy
(reference screenshot lives outside the repo, e.g.
`~/repos/ac-screenshots/aluvian training academy first room.png`; not
committed, see LEGAL.md).

---

## 1. How this plan is organized

- **§2 — Category taxonomy.** *Every* category of work required to port the
  client, so nothing is missed. Each category is a unit we refine and assign.
- **§3 — The "first room" milestone.** The categories, sequenced into a
  concrete dependency-ordered build for one room (the user's order).
- **§4 — Runbook model.** How an agent executes a task from this plan.
- **§5 — Status ledger.** What is proven, in progress, or open.
- **[`extraction-methodology.md`](extraction-methodology.md)** — the
  technical "where/how to extract" reference (DAT file taxonomy, tooling,
  coordinate transforms, per-asset recipes, known gotchas).

> Status tags used throughout: `[PROVEN]` demonstrated working this far ·
> `[PARTIAL]` works with caveats · `[OPEN]` not yet attempted · `[BLOCKED]`
> needs a dependency first.

---

## 2. Category taxonomy — everything we will need to do

Recreating an MMO client decomposes into these categories. Each is
independently refine-able into tasks. Categories I–IV are the *world
shell*; V–IX are *world contents*; X–XII are the *live/interactive
client*; XIII–XIV are *cross-cutting*.

### I. Extraction & tooling foundation `[PARTIAL]`
The bridge from `client_*.dat` to engine-ready intermediates. Geometry/
texture/layout/light extraction is exercised end-to-end; many declared
file types (WeenieDefaults, CombatTable, TreasureTable, ContractTable, etc.)
have **not** been pulled yet, so this is partial, not proven.
- DAT access via ACE.DatLoader, wrapped by the `acdat` C# CLI (`pipeline/dat-extract`).
- The complete DAT **file-type taxonomy** (which ID range backs which asset) — see methodology doc.
- Intermediate exchange formats (OBJ for geometry, PNG for textures, JSON for layout/metadata).
- Coordinate-system transform (AC right-handed Z-up metres → UE left-handed Z-up cm).
- Headless UE import scripts (`pipeline/ue-import`) + render-verification harness.

### II. World geometry `[PARTIAL]`
> Indoor and outdoor are **two structurally different importers** of comparable
> size; the academy (indoor) methodology does **not** scale to terrain as-is.
- **Indoor cells (EnvCell):** `EnvCell -> EnvironmentId -> Environment -> CellStruct` (vertices/polygons). *Proven: 568-cell academy extracts + renders.*
- **Outdoor terrain:** `CellLandblock` 9x9 heightfield + alpha-blended terrain types; resolve heights via `RegionDesc.LandDefs.LandHeightTable`; `LandVertex` has 6 UV channels (OBJ can't hold these -> glTF). `[OPEN]`
- **Region / sky (`RegionDesc` 0x13):** global sky/sun/moon/fog/ambient + day-night ("lighting of day"). Without it outdoor sky/fog/light are wrong. `[OPEN]`
- **Outdoor scatter (`Scene` 0x12):** procedural trees/rocks/bushes per terrain type; without it every outdoor block is bare. `[OPEN]`
- **LOD (`DegradeInfo` 0x11):** distance-based GfxObj swaps -> UE Static Mesh LODs. `[OPEN]`
- **Buildings & static structures:** `LandblockInfo` building outlines/portals. `[OPEN]`
- **Cell connectivity:** `CellPortals` / `VisibleCells` for stitching + occlusion. `[OPEN]`

### XV. Strategic / client-platform categories `[OPEN]`
Whole areas that are not asset extraction but are required for a real client:
authentication & login flow; character creation & selection; portal/zone
transitions; asset streaming & load policy; LOD policy; packaging &
distribution; CI/CD; telemetry & crash reporting; performance budgets
(memory / draw-calls / VRAM); input remapping (`KeyMap`); settings
persistence; social systems (allegiance / fellowship / chat channels);
weather + day-night cycle (`RegionDesc.SkyDesc`); NPC AI; the dyeing /
recolor / loot-variance system; accessibility; localization beyond
`StringTable`. Each becomes its own decomposition when reached.

### III. Surfaces, textures & materials `[PARTIAL]`
- Resolution chain: `Surface (0x08) → OrigTextureId → SurfaceTexture (0x05) → Texture (0x06)`.
- Texture decode: DXT1/3/5, raw, custom-JPEG; **palettes** (`Palette 0x04`, `PaletteSet 0x0F`) and palette-index overrides.
- **UV mapping:** AC UVs are top-left origin (no V-flip); per-polygon `PosUVIndices` select which UV per face. *Proven: V-flip bug fixed; per-poly indices still `[OPEN]`.*
- Surface attributes to honor: `Luminosity` (emissive), `Translucency`, `Diffuse`, surface type (opaque / alpha / clipmap).
- UE translation: master-material + per-surface MaterialInstance strategy; animated/scrolling surfaces (water/lava). `[PARTIAL]`

### IV. Lighting `[OPEN]`
- AC lighting model: light sources defined per-Setup (`LightInfo`, a Frame + color/intensity/falloff/cone); AC computes per-vertex (Gouraud) lighting at runtime, `dot(N,-L)+ambient` multiplied into the texture - **there is no baked per-vertex color in the data** (verified: `SWVertex` is position/normal/UV only; confirmed against ACViewer shader). Pure-black surfaces are invisible without light/ambient.
- Per-cell ambient + the placed point/spot lights (torches, braziers).
- UE translation: decide and **document** the faithful approach (baked Lightmass vs. dynamic + emissive surfaces). This is the category most needing a recorded decision (ADR).
- **Reality check:** the light-*placement* coordinate fix is proven only for the canonical `samples/academy_8602_lights.json` (lights inside their cells, ~2.7 m median). The statics doubling bug is still unfixed in `DumpAcademyStatics`. The rendered *look* of a lit room is not yet achieved - this category stays OPEN.

### V. Static objects / props / furniture / decoration `[PARTIAL]`
- `Setup (0x02)` = multi-part placeable models; `GfxObj (0x01)` = the meshes; per-part `PlacementFrame`s + scale.
- Placement: `EnvCell.StaticObjects` (the "Stab" list — tables, chairs, signs, braziers).
- *Proven: extraction + placement attempted (`export-academy-statics`); needs bounds/material polish.*

### VI. Characters / NPCs / creatures `[OPEN]`
- Body = `Setup` of body-part `GfxObj`s; part hierarchy via `ObjectHierarchy (0x0E00000D)`.
- Equipment/clothing overlays via `ClothingTable (0x10)`; recolors via palettes.
- Player appearance from `CharacterGenerator (0x0E000002)`; NPC appearance from server weenie defaults (ACE).

### VII. Animation `[OPEN]`
- `MotionTable (0x09)` maps motion commands → animation IDs; `Animation (0x03)` holds keyframes; `AnimationHook` for events.
- AC uses part-based (per-GfxObj-piece) animation, not a single skinned skeleton — translation strategy needed for UE.

### VIII. Particles & effects `[OPEN]`
- `ParticleEmitterInfo (0x32)`, `PhysicsScript (0x33)`, `PhysicsScriptTable (0x34)`.
- Fireplace flames/embers, spell visuals, environmental FX → UE Niagara.

### IX. Audio `[OPEN]`
- `Wave (0x0A)` samples; `SoundTable (0x20)` maps events/ambience → sounds → UE audio + attenuation.

### X. UI / HUD `[OPEN]`
- `UiLayout (0x21)`, `Font (0x40)`, `StringTable (0x23/0x24)`.
- Recreate in UMG. **Order: chat box first**, then vitals, radar, panels (inventory/character/spellbook).

### XI. Interaction & network protocol (the live client) `[OPEN]`
*This is the longest-tail, highest-risk category. It is many months of work,
not one bullet.* Sub-decomposed:
- **XI.a Transport** - Turbine UDP: packet headers, fragmentation/reassembly, sequencing, ack/retransmit, the world-vs-auth channels.
- **XI.b Login/handshake** - connect, login auth, encryption/ISAAC seeds, session establishment.
- **XI.c Character select / enter-world** - char list, selection, world entry, portal/teleport transitions.
- **XI.d Message taxonomy** - the GameAction (client->server) and GameEvent (server->client) message catalog, ordered/sequenced (F7B0) flows.
- **XI.e Object/state sync** - object create/update/delete, position broadcasts, visibility.
- **XI.f Interaction verbs** - select + `Use`/`Appraise`; double-click apple/NPC -> GameAction -> server -> GameEvent -> chat/inventory result.
- Target server is **ACEmulator** (open source; see LEGAL.md for usage stance). Player movement/physics is prototyped in `pipeline/sim-core` (the simulation lane; see `contract/`).

### XII. Game-data / rules tables `[OPEN]`
- `WeenieDefaults`, `SpellTable`, `SpellComponentTable`, `SkillTable`, `XpTable`, `TreasureTable`, `CraftTable`, `ContractTable`, etc.
- Mostly server-authoritative (ACE owns these); client needs a subset (spell components, fonts, string tables, char-gen).

### XIII. Asset pipeline / build / integration `[PARTIAL]`
- Idempotent headless import scripts; asset naming (`SM_<hex>`, `MI_<hex>`, `T_<hex>`); content-folder layout; Git LFS for binaries.
- Render-verification harness (`render_academy.ps1`) for human-free visual checks (has known footguns: identical-hash screenshot dedupe can false-positive; PlayerStart-move path is finicky).
- Caveats keeping this PARTIAL: `pipeline/ue-import/` holds ~14 undocumented `_diag_*`/`_fix_*`/probe scripts whose purposes are not recorded, and `pipeline/dat-extract/Program.cs` is a ~1900-line monolith with no section map.

### XIV. Verification & fidelity `[PARTIAL]`
- Reference-screenshot capture + side-by-side comparison; per-category acceptance criteria; provenance (DAT iteration numbers) recorded.

---

## 3. The "first room" milestone (dependency-ordered)

One room, every detail accurate. Each step has an acceptance bar and
produces a reusable recipe. **Step 0 must happen first** — we cannot
build the room until we know which cell(s) it is.

| # | Step | Categories | Acceptance bar | Status |
|---|------|-----------|----------------|--------|
| 0 | **Identify the room** — match the reference's texture signature (blue-grey floor `06003C9A`) + a warm fire light + furniture density. Candidate set found: **`0x860201AD`** (primary; documented spawn, 2 fires, 30 statics) and `0x860201B6`. The green object in the shot is an urn, **not** an NPC. Method + evidence: [`runbook/step0-identify-first-room.md`](runbook/step0-identify-first-room.md). | I, II, III | Cell id named ✓; render matches reference walls/floor — **pending Step 1** (walls currently render the wrong texture identity). | `[PARTIAL]` cell identified; visual match `[BLOCKED on 1]` |
| 1 | **Room bounds + correct textures** — floor, walls, ceiling geometry with every surface's correct texture, correctly oriented (UVs), no light dependence yet. | II, III | **T0** geometry round-trips + **T1** every surface = correct texture id, correct orientation (no flip/mirror). | `[PARTIAL]` UV V-flip fixed; per-poly `PosUVIndices` + texture-identity audit pending |
| 2 | **Lighting** — reproduce the room's lit look; document the chosen UE approach. | IV | Brightness/character matches reference; method written down. | `[OPEN]` |
| 3 | **Furniture & decorations** — bookshelf, desk, cabinets, rugs, the wooden archway (the room's Stab/Setup objects), placed + textured. | V, III | Each prop present at correct transform with correct texture. | `[OPEN]` |
| 4 | **NPC model + clothing** — the academy NPC body, equipment, palettes; T-pose acceptable initially. | VI | Recognizable NPC standing in correct spot. | `[OPEN]` |
| 5 | **Interactive objects** — the apple on the desk (and similar) as discrete, selectable actors. | V, XI(setup) | Apple present as its own actor, hover/selectable. | `[OPEN]` |
| 6 | **Particles / animation** — fireplace flames + glowing embers (close-enough is fine), idle NPC motion. | VIII, VII | Fire reads as fire; embers animate. | `[OPEN]` |
| 7 | **HUD — chat box only** — a working UMG chat panel. | X | Chat box renders; can display text lines. | `[OPEN]` |
| 8 | **Interaction wiring** — double-click apple / double-click NPC → text in the chat box, driven by a **real ACE round-trip** (connect → login → enter the cell → client GameAction → server GameEvent → chat). | XI.a–f | A live server event (not a local stub) reaches the client and prints the expected chat line. | `[OPEN]` |

**The milestone is two phases.** Steps 0–7 are **M1-Visual** (the room looks
right, no live server). Step 8 is **M2-Networked** and deliberately forces the
highest-risk category (XI) to land real code — *a local stub does not pass the
milestone*, because the point of "one room, fully real" is to prove every
category end-to-end. If M2 must be deferred, mark M1-Visual complete and M2 as
a separate milestone; do not mark Step 8 "done" with a stub.

Everything beyond step 8 (combat, magic, inventory, full world, outdoor
terrain, other zones) is explicitly **out of scope for this milestone**
and lives in the category backlog (§2, incl. category XV) for later.

---

## 4. Runbook model (how an agent executes)

For each task an agent should:
1. **Read** this plan + [`extraction-methodology.md`](extraction-methodology.md); confirm the task's category + milestone step.
2. **Extract** the needed data with `acdat` (or note a new command to add), writing intermediates under `pipeline/dat-extract/out/`.
3. **Import** into UE via a headless script under `pipeline/ue-import/` (idempotent; re-runnable).
4. **Verify** with `render_academy.ps1` against the reference; capture the render under `pipeline/renders/`.
5. **Document** the recipe: append the technique + any new gotcha to the methodology doc; update the §5 status ledger.
6. **Never** start unrelated categories opportunistically — finish the current milestone step or hand it back.
7. **Stop the line.** If you discover a blocker that lives in *another* category, file it in §5/§7 and stop — do **not** fix it in place. Re-sequence at the next planning pass. (The lighting investigation derailing the geometry work is exactly the failure this prevents.)
8. **Guard destructive ops.** Before any bulk delete/regenerate, follow [`recovery.md`](recovery.md) (stash + restore tag). This project has lost work before.

A future `runbook/` will hold one step-by-step file per milestone step as it
is executed, so the *next* zone can be built by replay.

---

## 5. Status ledger

**Promotion rule:** `[OPEN] -> [PARTIAL]` once code exists and runs;
`[PARTIAL] -> [PROVEN]` only with a committed artifact + a verification render
at the relevant acceptance tier, cited here. "It looked right once" is not
PROVEN.

**Verified working:**
- EnvCell geometry extraction + UE import of the full 568-cell academy (II) - T0.
- Coordinate transform AC->UE (see methodology) - geometry lands in the right place (I).
- **UV orientation fix** (cells): AC UVs are top-left origin; `import_academy.py`'s `1.0 - vv` rendered walls upside-down - corrected to `vv`, all 568 cells rebuilt, verified on a wall face-on (T1 orientation). `import_statics.py` has the same fix now but props need a re-import to take effect. (III)
- **Light-position fix** (lights only): `EnvCell.StaticObjects[].Frame` is landblock-absolute; the dump was doubling coordinates. Fixed in `DumpAcademyLights`. **Canonical artifact = `pipeline/dat-extract/samples/academy_8602_lights.json`** (sha `e2ab7553…`): median light->cell-origin **2.7 m, 125/132 within 6 m** (recompute to verify, do not trust the prose). Regenerate via `acdat dump-academy-lights`. Two known caveats in this artifact: (a) the `cone_angle_degrees` field is **garbage** (~-2.5e10) and must be ignored until the decode is fixed; (b) it is AC-derived data committed under the grandfather clause (see [LEGAL.md](../../LEGAL.md) / ADR-0003), not a new asset. (IV)
- Bright **unlit** textured materials render the academy clearly (interim look; not the final lit look). (III)
- Headless render-verification harness, with caveats (XIII).

**Step 0 result (2026-05-30) — CONFIRMED:** first room = **`0x860201AD`**
(spawn) / `0x860201B6` (same room template), by the texture+fixture method
([runbook](runbook/step0-identify-first-room.md)). **Textures verified correct
against the answer key:** the room's shell is brown stone walls (`06003C9C`) +
blue tile floor (`06003C9A`) + dark ceiling — exactly what the data produces
(confirmed via `analyze_surfaces.py` + the starting-view screenshot). The
earlier "walls are the wrong (grey-blue) texture" entry was a **false alarm**:
a reference misread of the low-res original *plus* a stale `M_HotPinkDiagnostic`
bound to the wall slot (which made it render magenta). Both corrected; the
diagnostic material is deleted.

**Open / next (Step 1 finish + Step 3 prep):**
- **Verify the remaining extraction layers** (see methodology §7): dump `PosUVIndices` to confirm UV per-face selection (exporter still uses `UVs[0]`); audit texture decode/palette; `CullMode`/`NegSurface`. T1/T3 face-on compare vs the answer key.
- Step 3 prep: re-import statics (the wood ceiling beams, bookshelf, tapestry, map are **furniture/decoration**, not the cell shell) — needs the `DumpAcademyStatics` doubling fix first.
- Step 2: choose + record (ADR) the lighting approach (room currently renders dark under LIT masters; see notes/lighting-options).

**Known gotchas** (full list in [`extraction-methodology.md`](extraction-methodology.md) §7):
stale `UnrealEditor-Cmd.exe` holds the project lock and makes scripts fail
silently; never delete+recreate master materials (breaks MaterialInstance
overrides via new param GUIDs); auto-exposure off for deterministic renders;
Lumen/Nanite/HW-RT currently disabled in the ini (root README #19 is stale).

## 6. Changelog (chronological; newest first)

- **2026-05-31 (Step 1 UV fix, independently verified)** Installed **ACViewer** (`~/repos/ACViewer`, sha `ef94ce6`) as the independent reference; its `FileExport.cs` confirmed the correct UV interpretation (`vt` per vertex-UV; faces indexed by `PosUVIndices`). Built **`acdat dump-poly-uvs`** and proved from the data that the bug *mattered* for `0x860201AD` (12/54 wall corners use a non-zero `PosUVIndex`, 6 verts carry >1 UV). **Fixed `ExportEnvCell`** to emit per-(vertex,UV) `vt` and select per corner via `PosUVIndices`; re-exported + re-imported `0x860201AD`; the room shell now renders faithfully (brown stone walls + masonry baseboard + blue tile floor) vs the answer-key starting view. Corrected the stale "wrong texture identity" note - that was a false alarm (reference misread + hot-pink binding leftover), not an extraction error. Texture *identity* was always right; the defect was UV *mapping*.
- **2026-05-30 (Step 1 + verification mandate)** Built `analyze_surfaces.py` (reusable per-cell wall/floor/ceiling texture derivation from data). Used it to **verify** rather than trust the extraction: confirmed `0x860201AD`'s shell textures (brown walls `06003C9C` + blue floor `06003C9A`) match the answer key — the prior "wrong texture" finding was a false alarm (reference misread + a stale `M_HotPinkDiagnostic` bound to the wall slot, now fixed and the diagnostic deleted). Added methodology §7 "Verifying extraction is correct AND UE-compatible" (per-layer checklist; trust nothing). Open verification: per-face `PosUVIndices`, texture decode/palette, CullMode.
- **2026-05-30 (Step 0 executed, doc-vetting)** Ran Step 0 against the docs. Identified the first room to `0x860201AD`/`0x860201B6` by a texture+fixture method (not the assumed "spawn cell"/"NPC cell"; the screenshot has no NPC, the green object is an urn). Surfaced that **Step 0 is coupled to Step 1** (walls render wrong texture identity, so the room can't be visually confirmed yet) and that texture-identity is a **confirmed blocking defect** (not a footnote); logged a magenta error-material in `0x860201B6`. Added [`runbook/step0-identify-first-room.md`](runbook/step0-identify-first-room.md); updated §3 step 0, §5, methodology §5.
- **2026-05-30 (review round 2)** Verified first-hand that the canonical lights JSON had **regressed** to the doubled-coord data (median 140 m); promoted the correct data back (median 2.7 m, 125/132 within 6 m, sha `e2ab7553…`), removed the `_fixed`/`.bak_2x` siblings, flagged the `cone_angle_degrees` garbage. Governance: added [`recovery.md`](recovery.md) (backup/restore) and ADR-0006 (ACE linking stance) per LEGAL rule #3; reconciled LEGAL rule #1 to an explicit grandfather clause naming `Content/**` + `samples/`; ADR-0003 names `samples/`; demoted lighting "ADR-0005" to [`notes/lighting-options.md`](notes/lighting-options.md). Mechanical: root README #19 marked SUPERSEDED inline; fixed the `r.AllowStaticLighting` "Lumen handles it" comment; pinned UE 5.7.4 + dropped the self-stale branch row in versions.md; `AC_LIGHT_MULT` parse made crash-safe; em-dash gotcha rescoped to code/PowerShell. **Still open (user decision):** strict purge + history scrub of grandfathered AC assets; `DumpAcademyStatics` doubling fix; owners on `[OPEN]`s.
- **2026-05-30 (review round 1)** Multi-agent review of these docs. Fixed this pass: legal posture ([`../../LEGAL.md`](../../LEGAL.md)); glossary; tiered acceptance bars; corrected DAT taxonomy (cell range `0x0001-0x0040`, Font=Portal, mip=`Textures[last]`, quaternion order `W,X,Y,Z`, ClothingTable=substitution, added KeyMap/String/EnumMapper/StringState/CombatTable/ItemMutation/MasterProperty/ChatPoseTable + RegionDesc/Scene/DegradeInfo + texture formats incl. P8/INDEX16 trailing-palette caveat); Cat XI network decomposed; Step 8 reframed (no stub); status downgrades (I, IX, XIII -> PARTIAL/OPEN); `import_statics.py` UV bug fixed; stale `out/` lights artifact deleted; Lumen contradiction reconciled (ini authoritative).
- **2026-05-30** UV V-flip discovered + fixed; all 568 cell meshes rebuilt.
- **2026-05-30** Light doubling-bug found + fixed in `DumpAcademyLights`; lights re-exported.
- *(Earlier session incidents to fold in from git history: the ~387-actor NaN-bounds purge, the ~1487-actor false-alarm wipe scare, two data-loss events. See §7.)*

## 7. Remediation backlog (from the review; not yet done)

Tracked so the next agent does not rediscover. Each needs an owner + tier.
- **Governance:** ADR directory (`decisions/`) for the open decisions (Lumen on/off once Nanite-safe; OBJ vs glTF; ACE link vs clean-room per LEGAL.md; two-master-material strategy); a version-pin table (UE patch, ACE SHA, ACViewer SHA, DAT iteration, .NET, Python, GPU driver); owner + acceptance tier on every `[OPEN]`.
- **Backup/recovery procedure** (this project has had data-loss events; document checkpoint/restore before destructive ops).
- **Code:** fix the same doubling bug in `DumpAcademyStatics` (`Program.cs` ~828-833), rebuild `acdat`, re-export + re-import props; add a section map to / split `Program.cs`; document the ~14 `pipeline/ue-import/_diag_*` scripts or delete the dead ones.
- **Onboarding:** prerequisites/version table + a clone-to-first-render "start here"; map git "Phase 5e/5g/5h" terminology to milestone steps; cross-link this dir from the root `README.md`.
- **Outdoor pipeline** (terrain + Scene + RegionDesc + 6-channel LandVertex) spec, distinct from indoor.
- **"Stop the line" rule** for the runbook (file cross-category blockers in §5 and halt; do not fix in place) - the lighting investigation derailing geometry is the cautionary tale.
