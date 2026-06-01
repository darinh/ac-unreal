# 0016 - C++ / Blueprint split strategy
Status: Proposed   Date: 2026-05-31

## Context
The design so far is C++-leaning (the sim-core, `CoordTransform`, a
`UCharacterMovementComponent` subclass) and has not addressed Blueprints. AC is a
server-authoritative MMO with **parity** requirements (the simulation lane is
trace-tested against the original). We need a principled boundary so Blueprints
are used where they help (iteration, presentation) without compromising parity or
performance. This aligns with the existing **two-lane architecture** (simulation
must MIRROR; presentation may IMPROVE) [DOC: glossary, README L30].

## Decision
Proposed split (the seam is **data**):
- **C++** for: the **simulation lane** (movement, collision, physics-feel,
  cast/projectile timing, fixed-tick math — `contract/`), **networking/
  replication** (the ACEmulator-compatible protocol + predict/reconcile
  component), **perf-critical/high-count** systems (landblock streaming, Mass-style
  entities, the importers), and **core data types** (`USTRUCT`/`UCLASS`/
  `UDataAsset`). Parity-critical math must NOT live in Blueprint (BP's tick/latent-
  node ordering, VM float/iteration-order behavior, and reduced auditability make
  trace-level parity testing fragile).
- **Blueprint** for: **UI/HUD** (UMG), **designer-tunable gameplay** (ability/
  effect/quest/spawn wiring), **prototyping** (promote hot paths to C++ once
  settled), and **level/content scripting**.
- **Seam:** expose C++ via `UFUNCTION(BlueprintCallable)` /
  `UPROPERTY(EditAnywhere|BlueprintReadWrite)` / `BlueprintNativeEvent`; drive
  behavior from `UDataAsset`/`DataTable` (the contract already forbids magic
  numbers in sim logic — values load from data).

## Consequences
- Designers tune via data/Blueprint without recompiling; parity values stay in
  data, deterministic math in C++.
- Skill `ac-blueprints-vs-cpp` operationalizes this for day-to-day decisions.
- Revisit trigger: if a Blueprint hot path shows up in profiling, promote it to
  C++; if C++ iteration friction blocks designers, push more tuning into data.

## Alternatives
- All-C++: rejected (kills iteration speed for UI/gameplay; over-engineers content).
- Blueprint-heavy gameplay: rejected for the simulation lane (breaks deterministic
  parity testing and per-frame-at-scale performance).
