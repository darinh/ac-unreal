# 0022 - Audio (samples, event/ambient mapping, spatialization)
Status: Proposed   Date: 2026-05-31

## Context
AC audio = `Wave (0x0A)` samples + `SoundTable (0x20)` event/ambient -> sound
mappings [DATA: methodology §2 taxonomy]. The feature-disposition matrix gives
audio a one-line MIRROR with **no mechanism**: emitter placement, ambient-zone
volumes, music/ambience transitions, and portal occlusion are uncovered, yet the
ambient soundscape is feel-adjacent (it shapes presence). Audio is predominantly
**presentation** (may IMPROVE), except where a sound is gated by an
`AnimationHook` (`SoundHook`) — that timing is **simulation** (`contract/` §7) and
must MIRROR.

## Candidate (proposed, not decided)
- **Samples:** `Wave 0x0A` -> `USoundWave` (decode once at import). Identity MIRROR.
- **Event/ambient mapping:** `SoundTable 0x20` -> a data asset mapping AC sound
  events/ambience to sounds. Mapping MIRROR.
- **Spatialization (IMPROVE/ADD):** positional emitters placed from object/cell
  data; per-cell/region **ambient-zone** volumes; **portal-aware** occlusion +
  attenuation (modern UE attenuation/submix/MetaSound); music/ambience transitions
  on cell/region change.

## Assumptions it depends on
- A1 [VERIFY]: `SoundTable` structure + how events/ambience resolve to `Wave`s.
- A2 [VERIFY]: where emitter placement + ambient-zone data live (object? cell?
  region/`RegionDesc`?).
- A3 [VERIFY/REF-IMPL]: which sounds are `SoundHook`-gated (sim timing) vs free
  ambience (presentation).

## Evidence required before Accepted
- Extract a `SoundTable` + a few `Wave`s and confirm the mapping; identify the
  emitter/zone source in the data.

## Failure mode if an assumption is false
- Wrong event->sound mapping; ambient zones in the wrong places; a gameplay sound
  (hit/cast) drifts from its hook frame -> feel breaks (see ADR-0012 M13 rule).

## Alternatives still live
- UE MetaSound for procedural/adaptive audio (a presentation upgrade over straight
  sample playback) — evaluate after the faithful mapping works.

## Acceptance test
- An AC sound event triggers the correct `Wave`; positional attenuation behaves;
  the ambient soundscape matches the reference zone; `SoundHook`-gated sounds fire
  on the extracted hook frame.

## Relationships
`contract/` §7 (`SoundHook` timing is simulation); particles/FX (ADR re: Niagara)
share the "gameplay timing comes from hooks, not the asset" rule.
