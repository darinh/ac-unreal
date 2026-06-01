# 0018 - Water / liquid surfaces + swim physics
Status: Proposed   Date: 2026-05-31

## Context
README flags animated water `[PARTIAL]`; the aquatic movement spec (`contract/`
§3b) is UNKNOWN. Water is **two concerns**: the visual surface (presentation) and
the volume that changes locomotion (simulation). Without the swim model, §3
ground locomotion is ambiguous near water.

## Candidate (proposed, not decided)
- **Water surfaces** = presentation: IMPROVE (UE water material/mesh), keeping the
  source surface identity.
- **Water volumes** = simulation: a swim movement mode in the `CharacterMovement`
  subclass driven by `contract/` §3b. Detection (depth threshold / volume tag /
  surface-plane test) mirrors how AC decides "in water".

## Assumptions it depends on
- A1 [VERIFY]: how AC detects a water volume (and where that data lives — a terrain
  type? a cell flag? a volume?).
- A2 [VERIFY]: the §3b swim model (horizontal/vertical speeds + accel, buoyancy,
  entry/exit transition, input mapping, breath/drowning — likely none; confirm).

## Evidence required before Accepted
- Identify the water-volume source in the data; fill `contract/` §3b from the
  client.

## Failure mode if an assumption is false
- Wrong detection -> swim mode triggers in the wrong places, or fails to trigger;
  ground locomotion near shorelines feels wrong.

## Alternatives still live
- UE `PhysicsVolume`/Water-system volume (presentation) bridged to the sim swim
  mode (keeps the visual modern while the behavior stays parity-driven).

## Acceptance test
- Entering / exiting / swimming (horizontal + vertical) matches the §3b reference
  traces within tolerance; shoreline transitions match.
