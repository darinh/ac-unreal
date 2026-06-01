# Feature disposition & design-gap analysis

**Status:** requirements/design note (analysis + recommendations; no implementation).
**Date:** 2026-05-31.
**Purpose:** the existing plan ([`../README.md`](../README.md) §2) enumerates the
*extraction categories* well, but it does not (a) state, per feature, whether we
**mirror / improve / remove / add** relative to the retail client, nor (b) design
the **world-scale** systems (streaming, precision, LOD, day-night, runtime
occlusion) that AC's open, seamless, long-view world requires — those sit in
§XV as undesigned bullets. This doc fills both gaps. It subsumes the earlier
`open-world-rendering-considerations.md` note (rendering rows below).

> **Anti-hallucination rule (carried from the open-world note).** Every "the
> retail client did X" claim carries a provenance tag; design phase forbids
> stating an assumption as fact.
> - **[DATA]** confirmed from DAT data / `acdat` extractor / committed artifact (cite).
> - **[REF-IMPL]** documented in ACEmulator `ACE.DatLoader`/`ACE.Server` or ACViewer (confirm exact symbol before coding).
> - **[DOC]** asserted in this repo's own design docs (README/methodology/glossary/ADR).
> - **[COMMUNITY/VERIFY]** widely-held AC knowledge, NOT yet confirmed from data here — must verify before it drives a requirement.
> - **[DESIGN]** our engineering recommendation, not a retail fact.

## Disposition vocabulary
- **MIRROR** — reproduce the retail capability/intent with an equivalent mechanism (same observable behavior). Default for the **simulation** lane.
- **IMPROVE/UPGRADE** — retail had it; we render/run it at higher fidelity with modern tech. Allowed in the **presentation** lane; must be recorded as a deliberate deviation.
- **REMOVE** — retail mechanism we deliberately drop (engine subsumes it, or it is obsolete 1999-era plumbing).
- **ADD** — no retail equivalent; new capability (engine-forced or modern expectation).

**Governing rule** [DOC] (glossary "Two-lane architecture"; README line 30):
the **simulation lane** ([`../../contract/`](../../contract/)) must MIRROR — feel
is parity-tested, not modernized. The **presentation lane** (rendering/audio/UI)
may IMPROVE, but the *data identity* (which texture, which mesh, which timing)
must stay faithful per the tiered acceptance bars (README "Faithful is tiered",
T0–T4).

---

## A. World shell & rendering (presentation lane)

| Feature | Retail baseline (provenance) | Disposition | Rationale / notes |
|---|---|---|---|
| Render pipeline | DX7 fixed-function, sRGB, per-vertex **Gouraud** lighting [DOC] README L14, glossary | **IMPROVE** | UE5 linear-HDR + filmic; pixel-equality explicitly not the bar (tiered T0–T4). Already decided. |
| Indoor geometry (`EnvCell`→`Environment`→`CellStruct`) | explicit polygon cells [DATA] methodology §5 | **MIRROR** | Proven: 568-cell academy extracts/renders (T0). |
| Outdoor terrain (`CellLandblock` 9×9 [DATA] + `LandHeightTable`; 6-UV `LandVertex` [REF-IMPL: ACViewer]) | heightfield + alpha-blended terrain types | **MIRROR** (data); render path **unresolved — see ADR-0009** (per-landblock static mesh *first*, UE Landscape later), NOT a settled Landscape choice | GAP: importer `[OPEN]`; height-table→metres TODO; 8×8 quads don't map cleanly to Landscape sections; OBJ can't carry 6 UVs → glTF (ADR-0004, Proposed). |
| Surfaces / textures | `Surface 0x08`→`SurfaceTexture 0x05`→`Texture 0x06`; flags `Luminosity`/`Translucency`/`Diffuse`/`Type` [DATA] methodology §5 | **MIRROR** identity + **IMPROVE** runtime (master-mat + per-Surface MI, VT, mip-gen) | GAP: surface flags **not consumed yet** `[OPEN]`; mip generation required or distant surfaces shimmer. |
| Palettes / recolor (`Palette 0x04`, `PaletteSet 0x0F`, `OrigPaletteId`) | 256-color tables + palette-range recolor [DATA] methodology §5 | **MIRROR** semantics; **REMOVE** P8/INDEX16 *storage* (decode once to RGBA) | The recolor ranges ARE the dyeing/loot-variance system (cat XII) — keep the semantics, drop the runtime paletted-texture format. |
| Lighting model | per-vertex Gouraud computed live [DATA/REF-IMPL]; per-Setup `LightInfo` [REF-IMPL: ACE `SetupModel.Lights`]; ambient is **global** time-of-day (`RegionDesc->SkyDesc->SkyTimeOfDay` `AmbBright`/`AmbColor`), **NOT** per-cell [REF-IMPL: ACE; corrects an earlier "per-cell ambient" error]; no baked vertex color [DATA] | **IMPROVE** (per-pixel dynamic) | GAP: only the **indoor unlit-emissive expedient** is decided (ADR-0007). Outdoor/day-night lighting model is **undecided** → ADR-0011. |
| Sky / fog / sun-moon / day-night (`RegionDesc 0x13`) | global sky/sun/moon/fog/ambient + "lighting of day" [DATA] methodology §2/§5; glossary | **MIRROR** (data-driven) + **IMPROVE** (SkyAtmosphere/volumetrics) | GAP: extraction `[OPEN]`; **extract real fog/sky values before authoring — do not invent**. |
| Outdoor scatter (`Scene 0x12`) | procedural trees/rocks/bushes per terrain type [DATA] methodology §2 | **MIRROR** via **HISM/Foliage/PCG** | One actor per object does NOT scale (the 1487-actor academy is the cautionary tale). |
| Object LOD (`DegradeInfo 0x11`) | distance GfxObj swaps [DATA] methodology §2/§5 | **MIRROR** → UE Static Mesh LODs | Straightforward; extraction `[OPEN]`. |
| Distant-world proxies (HLOD/impostors) | *none* — AC had no proxy-merge; `RegionDesc` has fog params [DATA], but the retail draw-distance/horizon strategy is [COMMUNITY/VERIFY] | **ADD** | New: World Partition HLOD for distant landblocks. Budget as new work (spike a 4×4 region; HLOD build cost can block CI). |
| Portal / interior visibility (`NoPos` portals, `CellPortals`, `VisibleCells`) | portal-connected cells + per-cell visibility set [DATA/REF-IMPL] ADR-0008; README §II L84 | **MIRROR** | GAP: extraction of openings done (ADR-0008) but **runtime occlusion is undesigned** — current all-cells-in-one-level both hangs `-game` and leaks outdoor sky through openings. |

---

## B. World contents (mixed lanes)

| Feature | Retail baseline (provenance) | Disposition | Rationale / notes |
|---|---|---|---|
| Props / furniture (`Setup 0x02` of `GfxObj 0x01` + `PlacementFrame`) | multi-part static models; placed via `EnvCell.StaticObjects` Stab | **MIRROR** | `[PARTIAL]` placed; statics doubling fix + material polish pending. |
| NPC / creature bodies (`Setup` + `ObjectHierarchy 0x0E00000D`) | part-based **rigid** GfxObj assembly, **no skinning/bones** [DATA/REF-IMPL] methodology §5 | **MIRROR** body assembly; **DECISION** on animation rep | GAP/fork: keep AC's rigid per-part transforms vs **IMPROVE** to a UE skeletal mesh. Needs ADR (affects animation, perf, tooling). |
| Clothing / equipment (`ClothingTable 0x10`) | **substitution** (replace part GfxObj + swap textures) + palette recolor + `CoverageMask` [DATA/REF-IMPL] methodology §5 | **MIRROR** | The recolor path is shared with dyeing (cat XII). |
| Player appearance (`CharacterGenerator 0x0E000002`) | starting looks/equipment [DATA] methodology §2 | **MIRROR** | |
| Animation (`MotionTable 0x09`, `Animation 0x03`, `AnimationHook`) | per-part rigid keyframes; hooks (`AttackHook` etc.) gate gameplay [REF-IMPL: ACE `Animation.cs`] | **MIRROR timing** (sim) + **IMPROVE rendering** (sim/present split) | Hook *timings* are simulation (contract §7) → MIRROR exactly; visual *interpolation* may be upgraded, but **event-bearing frames stay aligned to hook times** (retime only via a documented, tested offset — ADR-0012). Watch for cast frames in `PhysicsScript`. |
| Particles / FX (`ParticleEmitterInfo 0x32`, `PhysicsScript 0x33/0x34`) | scripted emitters [DATA] methodology §2 | **IMPROVE** → Niagara | Visual re-author OK; any gameplay timing must come from hooks, not the visual (contract §7 note). |
| Audio (`Wave 0x0A`, `SoundTable 0x20`) | samples + event/ambient mapping [DATA] methodology §2 | **MIRROR** (+ optional **ADD**: occlusion/attenuation, ambient zones) | |

---

## C. Live / interactive client

| Feature | Retail baseline (provenance) | Disposition | Rationale / notes |
|---|---|---|---|
| HUD / UI (`UiLayout 0x21`, `Font 0x40`, `StringTable`) | DAT-defined panel layouts [DATA] methodology §2 | **IMPROVE** → UMG (faithful layout, modern widgets) | Order: chat box first (README §3 step 7). |
| Network transport (Turbine UDP: headers, fragmentation, sequencing, ISAAC) | server-authoritative wire protocol [DOC] README §XI; [COMMUNITY/VERIFY] exact packet shapes | **MIRROR (hard requirement)** | Target server is **ACEmulator**, which speaks the retail protocol — we cannot "improve" the wire format without losing server compat. |
| Login / handshake / char-select | retail auth + ISAAC seeds [DOC] README §XI | **MIRROR** | Forward-compat with ACE. |
| Message taxonomy (`GameAction`→`GameEvent`) | ordered/sequenced flows [DOC] README §XI; [REF-IMPL] ACE | **MIRROR** | |
| Movement prediction/reconciliation | client predicts + server reconciles (TBD) [COMMUNITY/VERIFY] contract §10/§10b | **MIRROR** | Must replay the same predict/reconcile shape or feel breaks; contract §10 is the spec (UNKNOWN, awaiting decompile). |
| Rules tables (`Skill/Spell/Xp/Combat/Treasure/Contract/...`) | server-authoritative [DOC] README §XII; [REF-IMPL] ACE | **MIRROR** (consume ACE/weenie); client needs only a subset (spell components, fonts, strings, char-gen) | |
| Keyboard "turn" (legacy WASD turn) (`KeyMap 0x14`) | legacy turn-rate locomotion [DATA] methodology §2 | **IMPROVE** (modern mouselook default; legacy as option) | Keep remappable bindings from `KeyMap`. |

---

## D. World-scale architecture (the open-world gaps — mostly §XV today)

| Concern | Retail baseline (provenance) | Disposition | Rationale / GAP |
|---|---|---|---|
| Spatial streaming | all world data keyed **per-landblock** (192 m); seamless/zoneless client streamed landblocks around the player [DATA] per-landblock keying; [REF-IMPL] ACE `LandblockManager`; [COMMUNITY/VERIFY] client load radius | **MIRROR** (intent) via **World Partition** | GAP: **no WP/streaming config exists**; all actors inline in one level → the `-game` hang. Highest-leverage missing design. |
| Coordinate precision over ~49 km | landblock-local coords (global = LB origin + local) [COMMUNITY/VERIFY] confirm vs ACE `Position`/`Frame` | **MIRROR capability**, **REPLACE mechanism** with UE **LWC** (double precision, already `=1`) | GAP: decide LWC-global vs keep landblock-local (pairs with WP cell origins). Contract §0/§0b has this UNKNOWN. |
| Terrain + object LOD | `DegradeInfo` object LOD; terrain LOD (TBD) [DATA]/[COMMUNITY/VERIFY] | **MIRROR** object LOD; **ADD** HLOD | See A rows. |
| Day-night / weather | `RegionDesc.SkyDesc` "lighting of day"; weather [DATA] methodology; [DOC] README §XV | **MIRROR** (data-driven) + **IMPROVE** (volumetrics) | GAP: extraction + a time-of-day drive system are unbuilt. |
| Runtime occlusion | portal/cell `VisibleCells` (interior PVS); fog far-clip outdoors [DATA] ADR-0008; README §II | **MIRROR** | GAP: no runtime culling design; needed for both perf and to stop sky-leak indoors. |
| Asset/object relevance (creatures/items entering view) | server broadcasts object create/update/delete in range [DOC] README §XI.e | **MIRROR** | Ties to network relevance + streaming radius. |
| Performance budgets (draw calls / VRAM / memory) | 1999 hardware budget [COMMUNITY] | **ADD** (modern budgets) | §XV bullet; undesigned. |
| Packaging / CI / telemetry / settings persistence | client installer + registry settings [COMMUNITY] | **ADD/IMPROVE** | §XV bullets; undesigned. |

---

## E. Things to REMOVE (obsolete 1999 plumbing — do not port)
- **DX7 fixed-function specifics** (software/hardware T&L paths, fixed pipeline state) — subsumed by UE [DOC] README L14. **REMOVE.**
- **Load-time mip generation** — UE does this via VT/streaming. **REMOVE** (but DO generate mips, methodology §5). 
- **Paletted-texture runtime storage (P8/INDEX16)** — decode to RGBA once at import; **keep palette *recolor* semantics** for dyeing. **REMOVE storage / KEEP semantics.**
- **1999-tuned draw distance/fog constants** as hard limits — re-tune for modern GPUs; **keep the RegionDesc values as the faithful baseline**, not the cap. **IMPROVE.**
- **Newer DAT render types** (`RenderTexture 0x15`–`RenderMesh 0x19`): "mostly post-retail" is **[COMMUNITY/VERIFY]**, not [DATA] (ACE defines the id-ranges with no such marker). Before any REMOVE, **count records in the target Portal DAT iteration**; only REMOVE if empty/unused.

## F. Things to ADD (no retail analogue)
- **World Partition HLOD / impostors** for the long view distance.
- **LWC double-precision** world coords (enabled for ~49 km). NB: LWC being
  *enabled* is not a decided coordinate *strategy* — that is **open in ADR-0010**
  (LWC-global vs landblock-local).
- **Modern AA (TSR)** — already `r.AntiAliasingMethod=4`; **Virtual Textures / VSM** already on.
- **Nanite** (DECISION pending — disabled due to procedural-mesh crash; methodology §8).
- **Modern input** (gamepad), accessibility, a settings UI beyond AC's.
- **CI/packaging/crash-telemetry/perf budgets** (§XV).

---

## G. The biggest design gaps → recommended new ADRs / specs
Ordered by leverage. Each should become an ADR in [`../decisions/`](../decisions/)
or a spec, *before* the corresponding build work — and grounded by a verification
extraction, not assumption. **These are now `Proposed` ADR stubs:**
1→[ADR-0009](../decisions/0009-world-streaming-landblock-world-partition.md) ·
2→[ADR-0010](../decisions/0010-coordinate-precision-strategy.md) ·
3→[ADR-0011](../decisions/0011-outdoor-lighting-day-night.md) ·
4→[ADR-0012](../decisions/0012-animation-representation.md) ·
5→[ADR-0013](../decisions/0013-runtime-occlusion-portal-culling.md) ·
6→[ADR-0014](../decisions/0014-reenable-nanite-lumen-world-scale.md) ·
7→[ADR-0015](../decisions/0015-indoor-first-expedients-are-temporary.md).

1. **World-scale streaming architecture** — map the 192 m landblock grid to a UE
   World Partition grid; loading range vs AC's active-landblock radius; indoor
   cells as data layers/sublevels. *Verify AC's client load radius first
   ([COMMUNITY/VERIFY]).* — fixes the `-game` hang; unblocks all outdoor work.
2. **Coordinate & precision strategy** — LWC-global vs landblock-local; the
   indoor↔outdoor domain unification. *Resolves contract §0/§0b UNKNOWNs.*
3. **Outdoor lighting & day-night model** — extend ADR-0007 (indoor-only) to a
   real dynamic sun+sky+fog driven by `RegionDesc`. *Extract `RegionDesc.SkyDesc`
   first.*
4. **Animation representation** — AC rigid part-based vs UE skeletal mesh
   (affects NPCs, particles timing, perf, tooling). 
5. **Runtime occlusion / portal culling** — drive UE visibility from
   `CellPortals`/`VisibleCells`; occlude outdoor sky inside cells.
6. **Re-enable Nanite/Lumen at world scale** — the standing open decision
   (methodology §8 explicitly asks for this record) once procedural meshes are
   Nanite-safe.
7. **"Indoor-first expedients are temporary"** — record that ADR-0002 (Nanite/
   Lumen/RT off), ADR-0007 (unlit), all-in-one-level, and auto-exposure-off are
   step-0 scaffolding with explicit revisit triggers, so the landscape work does
   not inherit them as settled world-scale decisions.

## H. Verification-before-lock checklist (do NOT guess these)
[VERIFY] before any requirement above is locked:
1. AC client active-landblock load radius (drives WP range) — ACE `LandblockManager` + community docs.
2. Landblock-local vs global coordinate convention — ACE `Position`.
3. `RegionDesc.SkyDesc` contents (fog start/end, sky/ambient colors, sun/moon path, day-night period) — extract.
4. `EnvCell.VisibleCells` exact field/semantics (PVS vs adjacency) — ACE `EnvCell`.
5. Whether outdoor terrain LOD is distinct from `DegradeInfo`.
6. Whether `RenderTexture/RenderMesh` (0x15–0x19) are populated in the target DAT iteration (else REMOVE).

## Provenance index
- DAT taxonomy, recipes, gotchas, coordinate transform: [`../extraction-methodology.md`](../extraction-methodology.md) §2/§4/§5/§8.
- Category plan + tiered acceptance + two-lane note: [`../README.md`](../README.md) §2/§3, L14/L30.
- Terms / records: [`../glossary.md`](../glossary.md).
- Portals/visibility: [`../decisions/0008-skip-portal-polygons-on-export.md`](../decisions/0008-skip-portal-polygons-on-export.md).
- Engine state (Nanite/Lumen/RT off, exposure): `Config/DefaultEngine.ini`, ADR-0002, ADR-0007.
- Simulation/feel parity contract (movement, collision, timing, wire state): [`../../contract/physics-feel-spec-request.md`](../../contract/physics-feel-spec-request.md).
- Authoritative data semantics: ACEmulator `ACE.DatLoader`/`ACE.Server` (ADR-0001); ACViewer (ADR-0008).
