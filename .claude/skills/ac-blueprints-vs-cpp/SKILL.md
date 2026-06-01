---
name: ac-blueprints-vs-cpp
description: "Use when deciding whether to implement something in C++ or Blueprint in the ac-unreal project, or when wiring C++/Blueprint integration. Encodes the project's C++/Blueprint split (ADR-0016) aligned to the two-lane simulation/presentation architecture: C++ for parity-tested simulation, networking, and perf-critical systems; Blueprint for UI, designer-tunable gameplay, prototyping, and content wiring."
metadata:
  category: engineering
---

# C++ vs Blueprint in this project

The split follows the **two-lane architecture** (see `ac-migration-overview`).
Decision record: ADR-0016. The short rule: **parity and performance go in C++;
iteration and presentation go in Blueprint; the seam is data.**

## Use C++ for
- **The simulation lane** — anything parity-tested against the original: movement
  (`UCharacterMovementComponent` subclass), collision, physics-feel, projectile/
  cast timing, the fixed-tick math (`contract/`). Blueprint's tick/latent-node
  ordering, VM float/iteration-order behavior, and weaker auditability make
  trace-level parity testing fragile, so parity-critical math must NOT live in
  Blueprint.
- **Networking / replication** — the ACEmulator-compatible protocol layer and the
  predict/reconcile component (see `ac-mmorpg-networking`).
- **Perf-critical / high-count systems** — landblock streaming, Mass-style entity
  processing, the DAT-driven importers, anything touched per-frame at scale.
- **Core data types** — `USTRUCT`/`UCLASS`/`UDataAsset` definitions that data and
  Blueprints build on.

## Use Blueprint for
- **UI / HUD** (UMG; chat box first per the milestone), menus, MVVM view-models.
- **Designer-tunable gameplay** — ability/effect wiring, encounter/quest logic,
  spawn rules — where fast iteration beats raw performance.
- **Prototyping** — stand up a mechanic in Blueprint, promote hot paths to C++ once
  the design settles.
- **Level / content scripting** — per-level triggers, sequencer hookups, cosmetic
  reactions.

## The seam = data (so designers tune without recompiling)
Expose C++ to Blueprint deliberately: `UFUNCTION(BlueprintCallable)`,
`UPROPERTY(EditAnywhere|BlueprintReadWrite)`, `BlueprintImplementableEvent` /
`BlueprintNativeEvent` for override points. Drive behavior from `UDataAsset` /
`DataTable` (the contract already mandates: no magic numbers in sim logic — values
load from a `UDataAsset`). This keeps the faithful/parity values in data, the
deterministic math in C++, and the tunable/visual glue in Blueprint.

## Anti-patterns
- Parity-critical or per-frame-at-scale math in Blueprint (harder to make
  tick-deterministic, slower, hard to trace-test).
- Hard-coded gameplay constants in C++ that designers need to tune (put them in a
  `UDataAsset`/`DataTable` instead).
- A monolithic "God" Blueprint — keep Blueprint thin over C++ components.

## Accommodation note (why this skill exists)
The design so far has been C++-leaning (sim-core, `CoordTransform`,
`CharacterMovement` subclass). Blueprints are a first-class part of the plan for
the presentation/iteration side; ADR-0016 records the boundary so neither lane
silently absorbs the other.
