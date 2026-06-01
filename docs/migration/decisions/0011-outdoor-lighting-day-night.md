# 0011 - Outdoor lighting & day-night model (RegionDesc-driven)
Status: Proposed   Date: 2026-05-31

## Context
AC computes per-vertex Gouraud lighting at runtime; **ambient is global
time-of-day** (`RegionDesc->SkyDesc->SkyTimeOfDay` `AmbBright`/`AmbColor`), NOT
per-cell [REF-IMPL: ACE]. Sky/sun/moon/fog + day-night ("lighting of day") live in
`RegionDesc 0x13` [DATA: methodology §2]. ADR-0007 chose unlit emissive textures
as an **indoor-only** interim; it cannot do day-night. `RegionDesc.SkyDesc` has
**not been extracted**.

## Candidate (proposed, not decided)
A time-of-day system driving a dynamic directional **sun + SkyLight +
SkyAtmosphere + ExponentialHeightFog** from extracted `RegionDesc` curves;
surfaces move to a lit material set (keeping `Luminosity` emissive). Day-night
does **not** require Lumen (M14) — dynamic sun+sky+fog suffices; Lumen (ADR-0014)
is a separate GI quality upgrade.

## Assumptions it depends on
- A1 [VERIFY]: the actual contents of `RegionDesc.SkyDesc` (fog start/end,
  sky/ambient colors, sun/moon path, day-night period).
- A2 [VERIFY]: AC's retail draw-distance/horizon treatment (so fog is the
  *fidelity baseline*, not just present data — M4).

## Evidence required before Accepted (blocking task)
- **Build an `export-region` command** — it does **not** exist in `Program.cs`
  today (sequencing blocker). Extract `RegionDesc.SkyDesc` and confirm values
  before authoring sky/fog. **Do not invent fog distances or a day-night period.**

## Failure mode if an assumption is false
- Authoring sky/fog from guessed values yields an unfaithful world and rework.

## Alternatives still live
- Keep unlit emissive world-wide: not selected (no day-night; flat; unfaithful outdoors).
- Baked Lightmass: not selected (incompatible with a dynamic day-night cycle).

## Acceptance test
- Rendered sky/fog/ambient at representative times-of-day matches the extracted
  `RegionDesc` values within the agreed tier (T3 color under matched conditions).

## Relationships
- Supersedes the *scope* of ADR-0007 outdoors; ADR-0007 remains the indoor interim.
- Indoor sky suppression is ADR-0013 problem (2); GI is ADR-0014; weather beyond
  day-night is out of this ADR's scope (see disposition gap "weather").
