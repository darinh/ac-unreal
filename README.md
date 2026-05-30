# ac-unreal

Asheron's Call simulation parity + modernized presentation in Unreal
Engine 5. Two strictly separate lanes:

- **Simulation parity** (`Source/AcUnreal/`, `Content/Data/`,
  `harness/`) — must reproduce the original client's *feel*: tick rate,
  movement math, collision response, gameplay-event timing. Data-driven
  from the decompile spec; deterministic; fixed-timestep.
- **Presentation** (`Content/Presentation/`) — Lumen + hardware
  ray-tracing + Niagara + PBR. Free to diverge from the original. Must
  never affect a recorded simulation trace.

This repo works **in parallel** with a separate decompile agent that is
extracting behavioral facts from the official AC client. The interface
between the two agents is the document at
[`contract/physics-feel-spec-request.md`](contract/physics-feel-spec-request.md);
that is the single source of truth for all feel-defining values.

---

## Environment

| Component | Version | How verified |
|---|---|---|
| Unreal Engine | **5.7.4** (promoted binary; CL 51494982; branch `++UE5+Release-5.7`) | `Engine/Build/Build.version` on the installed Epic Launcher build |
| Visual Studio Build Tools | **2022 (17.14.36408.4)** with VC.Tools.x86.x64 + MSBuild | `vswhere -latest` |
| .NET SDK | **10.0.300** | `dotnet --list-sdks` |
| GPU | NVIDIA GeForce RTX 4090 (24 GB) — full hardware ray-tracing | `Get-WmiObject Win32_VideoController` |
| OS | Windows 11 Pro 26200 | `Get-CimInstance Win32_OperatingSystem` |
| Git LFS | 3.6.1 | `git lfs version` |

UE5 is installed at `C:\Program Files (x86)\Epic Games\UE_5.7` (or
`C:\Program Files\Epic Games\UE_5.7` — same install).

---

## Repository layout

```
ac-unreal/
├── README.md                      this file
├── AcUnreal.uproject              UE5 project descriptor
├── .gitignore / .gitattributes    UE-tuned ignore + LFS for asset binaries
│
├── contract/                      cross-agent contract
│   ├── physics-feel-spec-request.md   ← the FIRST deliverable; hand to decompile agent
│   └── decompile-artifacts/       landing zone for filled-in spec + reference traces
│
├── Source/
│   ├── AcUnreal.Target.cs         game target
│   ├── AcUnrealEditor.Target.cs   editor target
│   └── AcUnreal/                  primary game module (C++)
│       ├── AcUnreal.Build.cs
│       ├── Public/
│       │   ├── AcUnreal.h
│       │   ├── CoordCore/         AC↔UE coord transform (CANONICAL)
│       │   │   ├── CoordTransform.h         pure C++17 core
│       │   │   └── AcCoordLibrary.h         UE wrapper (UCLASS)
│       │   └── AssetIngest/       intermediate-format readers
│       │       ├── AcIntermediateLandblock.h   pure C++17 .aclb parser
│       │       └── AcLandblockImporter.h       UE wrapper (UCLASS)
│       └── Private/
│           ├── AcUnreal.cpp       IMPLEMENT_PRIMARY_GAME_MODULE
│           ├── CoordCore/
│           │   ├── CoordTransform.cpp
│           │   └── AcCoordLibrary.cpp
│           └── AssetIngest/
│               ├── AcIntermediateLandblock.cpp
│               └── AcLandblockImporter.cpp
│
├── Content/                       UE assets (most via Git LFS)
│   ├── Data/                      tunable DataAssets (movement params, timing tables)
│   ├── Sandbox/                   parity test maps
│   └── Presentation/              materials, Niagara, lighting
│
├── pipeline/
│   ├── coord-transform/           STANDALONE test rig for the coord-transform core
│   │   ├── README.md
│   │   ├── tests/CoordTransformTests.cpp
│   │   └── build.ps1              vcvars64 + cl.exe; no UE required
│   └── asset-ingest/              v1 intermediate-format spec + parser test rig + samples
│       ├── README.md
│       ├── FORMAT.md              .aclb on-disk binary schema (Phase 1)
│       ├── samples/               committed synthetic fixtures (gen_sample.ps1 reproducible)
│       ├── gen_sample.ps1         deterministic generator for samples/
│       ├── tests/LandblockImporterTests.cpp
│       └── build.ps1
│
└── harness/                       parity harness (Phase 3)
    ├── traces/                    recorded reference + UE traces
    └── diff/                      trace comparison tooling
```

---

## Decisions log

These are the binding decisions for this project. Update by appending; do
not edit history.

### 2026-05-29 — Initial scaffold (Phase 0)

1. **Pinned UE version: 5.7.4.** Promoted binary build is already
   installed and verified working with UnrealBuildTool. Confirmed via
   Wikipedia that 5.7 is current stable. Upgrade only on a deliberate
   migration branch.
2. **Binary install, not source build.** No engine modifications planned
   in Phase 0–3. Revisit only if a feel-defining behavior requires
   engine-internal change. Source builds add ~30 GB and a ~1 h initial
   compile per developer.
3. **C++ project, not Blueprint-only.** Required for the custom
   movement component, fixed-timestep simulation loop, and deterministic
   physics. Confirmed by the brief.
4. **Module name `AcUnreal`.** Single primary game module to start. New
   modules (parity harness runner, asset-ingest editor module) will be
   added as needed; no pre-emptive splitting.
5. **Coord-transform core is pure C++17 (no UE deps).** The math lives in
   `Source/AcUnreal/Public/CoordCore/CoordTransform.h` /
   `Private/CoordCore/CoordTransform.cpp` so UBT picks it up. The UE
   wrapper at `AcCoordLibrary.h` exposes the same functions through
   `UCLASS` / `BlueprintCallable`. The **same source files** are compiled
   into a standalone test executable by `pipeline/coord-transform/build.ps1`
   (which #includes them from the Source/ tree), so the core has *one*
   canonical implementation and *one* set of tests, runnable both inside
   and outside the editor.
6. **Default AC world conventions in `FAcWorldConventions` are
   PLACEHOLDER values** (right-handed, Z-up, 1 unit = 1 m, landblock side
   = 192 m, grid = 255×255). Round-trip tests pass for any consistent
   choice of conventions, but the values must be ratified by the
   decompile agent (§0 of the spec request).
7. **No `CharacterMovementComponent` decisions yet.** Phase 2 will
   *subclass* `UCharacterMovementComponent` and override the per-tick
   physics — preserving CMC's move-history scaffolding for future
   server-authoritative reconciliation while replacing the feel math
   entirely. Documented now to avoid revisiting.
8. **Git LFS for asset binaries** (`*.uasset`, `*.umap`, `*.fbx`, …).
   Trace recordings in `harness/traces/` are LFS-tracked because
   reference traces from the original client can be megabytes per scene.
9. **The coord transform is intentionally chirality-flipping in the
   default case — and it should be.** AC is right-handed Z-up
   (X=east, Y=north, Z=up); UE is left-handed (X=forward, Y=right,
   Z=up). The default XY swap in `AcAxesToUeAxesMeters` is an odd
   permutation (det = −1), so it converts AC right-handed input into UE
   left-handed output in one step — which is the correct mapping.
   **An earlier draft of this module ADDITIONALLY mirrored Y** "to
   force left-handed UE output", which was wrong: the swap already
   does that, so adding a mirror either double-flipped (back to
   right-handed) or no-op'd depending on convention combo. The mirror
   was removed; the swap stays. **Asset-pipeline implication (Phase
   1+):** because the coord transform flips chirality, anything pulled
   through it that has baked-in handedness — mesh triangle winding,
   normal directions, joint orientation in skeletons,
   rotation/quaternion conventions — needs the matching flip at the
   ASSET layer. A mesh imported via this transform without a winding
   flip will render with inside-out faces; an animation track imported
   without a quaternion remap will play mirrored. The transform
   doesn't hide the flip — it makes it loud — but Phase 1 importers
   must do their share.

### Open questions blocking later phases

- Spec §0 conventions (handedness, units) — must arrive before
  Phase 1 (asset import) lands, otherwise imported geometry will need
  re-running.
- Spec §1 (timestep) — must arrive before Phase 2.
- Phase 1 intermediate format choice (FBX vs glTF) — leaning glTF for
  skeletal + animation fidelity in modern PBR pipelines; revisit when
  sample assets arrive.

### 2026-05-29 — Phase 1 (asset-ingest scaffolding)

10. **Landblock intermediate format is binary, not JSON or glTF.** A
    landblock heightfield is a dense regular numeric grid. JSON would
    bloat a 437-byte payload to several KB; glTF would impose a graph
    representation that doesn't fit a regular grid. The v1 `.aclb`
    format is a 32-byte header + raw `float32[]` heights + raw `uint8[]`
    texture-layer indices. Full spec at
    [`pipeline/asset-ingest/FORMAT.md`](pipeline/asset-ingest/FORMAT.md).
    Mesh import (when added) WILL use glTF — different asset class,
    different right tool.
11. **Sample fixtures are synthetic, not "hand-exported" per the
    brief.** In an autonomous setup there is no human to do a hand
    export, and shipping AC binary content from the original client
    would be a copyright risk. `pipeline/asset-ingest/gen_sample.ps1`
    procedurally generates a 9×9 synthetic landblock conforming to the
    v1 format. The bytes are deterministic and committed. When the
    decompile agent starts dropping real exports, the parser tests
    will accept those too — the format is the contract, not the
    fixture origin.
12. **`.aclb` parser uses typed status enum, not bool / exception.**
    Every reader entry point returns an `EAcLbParseStatus`. Invalid
    input (bad magic, unsupported version, out-of-range fields,
    NaN/Inf heights, size mismatch) produces a specific status code so
    callers can react meaningfully. No silent fallback; no UB.
13. **Asset-ingest module deferrals (called out, not skipped).** v1
    covers the landblock heightfield path only. Skeletal meshes
    (glTF), textures (PNG/EXR — standard, no custom format),
    particle definitions (Phase 4 timing concern), and the texture
    table mapping (byte → asset path) are forward-declared in
    `FORMAT.md` as `Pending formats`. The mesh path specifically
    requires UE's Interchange framework, which is editor-side; that
    work is gated on installing NetFxSDK 4.6+ for the Editor target
    build.

---

## Reproduce from a clean checkout

Assumes the *Environment* table above is satisfied.

> **LFS note:** if you `git clone` without running `git lfs install`
> first, you will get *pointer files* (a few KB of text) instead of the
> actual binary assets in `Content/`. The C++ build will still succeed
> (Phase 0 has no binary assets yet) but the editor will fail to load
> assets later. Always `git lfs install` first.

```powershell
# 1. Clone with LFS
git lfs install
git clone <repo> ac-unreal
cd ac-unreal

# 2. Verify the standalone coord-transform tests build and pass
#    (proves the canonical math is intact independent of UE).
cd pipeline\coord-transform
.\build.ps1
cd ..\..

# 3. Generate VS solution + build UE5 module
&"C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" `
    AcUnrealEditor Win64 Development -Project="$(Resolve-Path .\AcUnreal.uproject)" -WaitMutex

# 4. Open in the editor (optional)
&"C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" `
    "$(Resolve-Path .\AcUnreal.uproject)"
```

The brief is intent; this README + the actual scripts are truth. When a
real invocation differs from the brief, update this README and the
scripts, not the other way around.

---

## Working with the decompile agent

The two agents communicate **only through files**:

- This agent writes `contract/physics-feel-spec-request.md` (done) and
  consumes whatever the decompile agent drops in
  `contract/decompile-artifacts/`.
- The decompile agent fills in the request (in place, or as a sibling
  response document) with provenance.
- Once §0–§5 of the spec are filled, this repo's Phase 2 simulation core
  can replace its PLACEHOLDER values and the parity harness becomes
  meaningful.

Do not begin Phase 2 tuning against PLACEHOLDER values; the diff against
PLACEHOLDER reference traces would be vacuous.
