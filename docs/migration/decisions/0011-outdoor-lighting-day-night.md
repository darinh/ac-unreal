# 0011 - Outdoor lighting & day-night model (RegionDesc-driven)
Status: Proposed   Date: 2026-05-31

## Context
AC computes per-vertex Gouraud lighting at runtime; **ambient is global
time-of-day** (`RegionDesc->SkyDesc->SkyTimeOfDay` `AmbBright`/`AmbColor`), NOT
per-cell [REF-IMPL: ACE]. Sky/sun/moon/fog + day-night ("lighting of day") live in
`RegionDesc 0x13` [DATA: methodology §2]. ADR-0007 chose unlit emissive textures
as an **indoor-only** interim; it cannot do day-night. `RegionDesc.SkyDesc` is now
**extracted** (2026-06-02, portal iteration 2072) →
`pipeline/dat-extract/samples/region_dereth.json` (via `acdat export-region`).

## Candidate (proposed, not decided)
A time-of-day system driving a dynamic directional **sun + SkyLight +
SkyAtmosphere + ExponentialHeightFog** from extracted `RegionDesc` curves;
surfaces move to a lit material set (keeping `Luminosity` emissive). Day-night
does **not** require Lumen (M14) — dynamic sun+sky+fog suffices; Lumen (ADR-0014)
is a separate GI quality upgrade.

## Assumptions it depends on
- A1 [RESOLVED 2026-06-02]: the actual contents of `RegionDesc.SkyDesc` — extracted
  to `pipeline/dat-extract/samples/region_dereth.json`. Raw `[DATA]`: day-night
  period `DayLength=7620s` over `DaysPerYear=360`; `TickSize=0.8`; **20 weather
  `DayGroup`s** (Sunny/Rainy/Clear/Cloudy — each with a `ChanceOfOccur` weight, sky
  objects, and 11–13 per-`SkyTimeOfDay` steps carrying `AmbBright`/`AmbColor`,
  directional `DirBright`/`DirHeading`/`DirPitch`/`DirColor`, and fog
  `MinWorldFog`/`MaxWorldFog`/`WorldFogColor`/`WorldFog`). Interpretations to confirm
  before authoring (NOT raw data): `DayLength=7620s` ≈ 127 min `[DOC]`; times read as
  0..1 day fractions `[DOC: times_of_day.start steps 1/16]`; colour byte order
  0xAARRGGBB `[DOC: matches ACE decode]`; and **angle units (`DirHeading`/`DirPitch`)
  are `[VERIFY]`** — do not assume radians/degrees (resolve via contract §0, ADR-0010).
- A2 [VERIFY]: AC's retail draw-distance/horizon treatment (so fog is the
  *fidelity baseline*, not just present data — M4).

## Evidence required before Accepted (blocking task)
- ✅ **DONE (2026-06-02, issue #2):** `acdat export-region <datDir> <out.json>`
  now exists and `RegionDesc.SkyDesc` is extracted to
  `pipeline/dat-extract/samples/region_dereth.json`. Real fog/ambient/sky values
  are recorded; sky/fog authoring must read those (do **not** invent).
- ⛔ **Still blocking Accepted:** A2 — AC's retail draw-distance/horizon treatment
  (so the extracted fog is the *fidelity baseline*, not just present data). Needs
  the client-decompile contract §0/§0b (issue #4). The acceptance test (render
  matches the extracted values) is also not yet run, so Status stays **Proposed**.

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
