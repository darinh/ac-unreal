---
name: ac-rendering-materials
description: "Use when working on AC surfaces -> UE materials, lighting, or the headless render/verification harness in this repo. Covers the Surface resolution chain, palettes/recolor, the indoor unlit-emissive interim, the outdoor day-night plan, Nanite/Lumen status, and the render-harness footguns (kill UnrealEditor first, /Game path mangling, isolated-level-renders-black, commandlet log capture)."
metadata:
  category: rendering
---

# AC surfaces/materials, lighting, and the render harness

## Surface -> material (presentation lane; IMPROVE, keep identity)
Resolution chain: `Surface (0x08)` -> textured: `OrigTextureId -> SurfaceTexture
(0x05) -> Textures[last]` (last = full-res mip); or solid: `ColorValue` (BGRA).
Surface flags `Luminosity` (emissive) / `Translucency` / `Diffuse` / `Type` are
**not consumed yet** (planned). Palettes (`0x04`/`PaletteSet 0x0F`) drive
**recolor ranges = the dye / loot-variance system** — decode paletted textures to
RGBA once at import but **keep the recolor semantics**. UE side: master material
per shading class + one MaterialInstance per Surface. **Never delete+recreate a
master that has instances** — new param GUIDs drop every instance's overrides to
grey; modify in place or re-apply by name.

## Lighting (presentation; the live state)
AC uses **per-vertex (Gouraud-style) lighting** at runtime with **no baked vertex
color** (`SWVertex` carries only Origin/Normal/UVs) `[REF-IMPL:
`SWVertex.cs:12-15`]`; ambient is a **global** time-of-day term (`SkyTimeOfDay.
AmbBright`/`AmbColor`) `[REF-IMPL: `SkyTimeOfDay.cs:15-21`]`. The exact combine
equation (e.g. `dot(N,-L)+ambient` x texture) is **`[VERIFY]`** — confirm it from
the client render path before baking it into materials/tests. Consequence either
way: pure-black surfaces are invisible without light/ambient.
Current decisions:
- **Indoor interim = unlit emissive textures** (ADR-0007): bright, even,
  deterministic; this is a step-0 expedient, NOT the world model.
- **Outdoor / day-night = dynamic sun+sky+fog from `RegionDesc`** (ADR-0011,
  proposed) — extract `RegionDesc.SkyDesc` first; do not invent fog/sky values.
- **Lumen/Nanite/HW-RT are OFF** (ADR-0002) due to procedural-mesh crashes;
  revisit at world scale once meshes are Nanite-safe (ADR-0014).
- These expedients are tracked as temporary in ADR-0015.

## Render / verification harness (`pipeline/ue-import`)
`render_academy.ps1 -Name X [-Level /Game/...] -X -Y -Z -Yaw -Pitch [-ExtraCmds]`
moves PlayerStart then captures a `-game` HighResShot. Evaluate with
`test_renders.py` (black/void/magenta/flat/blown + baseline regression).

**Footguns (each has cost real time here):**
- **Kill all `UnrealEditor*` before every run** — a stale process holds the
  project lock; commandlets then exit 1/255 silently. Also kill `CrashReport*`/
  `WerFault*` if a crash dialog appears.
- **Do NOT pass `/Game/...` paths through Git Bash** — MSYS rewrites the leading
  slash to `C:/Program Files/Git/Game/...`. Invoke render scripts via **PowerShell**.
- **A 17709-byte PNG is pure black.** Isolated/minimal `-game` levels currently
  render black regardless of camera (a world/render-setup issue, not the camera);
  prefer the populated academy level, or fix the minimal-level setup first.
- **`unreal.log()` (Display) does not reach piped stdout** in commandlets — only
  Warnings/Errors do. Write diagnostics to a text file from the Python script.
- **The full academy (1487 actors) hangs `-game`** on async static-mesh streaming
  ("Waiting for static meshes to be ready N/618") — the real fix is streaming
  (see `ac-world-streaming`), not retrying the render.
- `-ExecCmds` separator is a **comma**, not a semicolon; pass via env var to dodge
  cmd.exe arg-splitting. Auto-exposure is off for deterministic renders.
- Headless material edits must avoid `recompile_material` (crashes Slate under
  `-RenderOffScreen`); import textures once interactively, then bind headlessly.
- **No em-dashes in scripts/PowerShell** (cp1252 parse failures).

## Disposition summary
Render pipeline DX7->UE5: IMPROVE (tiered, not pixel-perfect). Surface identity +
palette recolor semantics: MIRROR. Paletted-texture runtime storage: REMOVE
(decode to RGBA). Gouraud per-vertex: IMPROVE to per-pixel dynamic.
