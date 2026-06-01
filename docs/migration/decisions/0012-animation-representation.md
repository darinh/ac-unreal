# 0012 - Animation representation: rigid part-based vs skeletal mesh
Status: Proposed   Date: 2026-05-31

## Context
AC bodies are a `Setup (0x02)` of part `GfxObj`s wired by `ObjectHierarchy
(0x0E00000D)`, animated as **part-based rigid transforms** (per-part keyframes; no
skinning) [REF-IMPL: ACE `Animation.cs`]. "No skinning" is confirmed for **all
creatures examined so far**, not proven universal (M7). Gameplay-timed
`AnimationHook`s (`AttackHook`, etc.) are **simulation** (contract §7). Some
cast/commit frames may live in `PhysicsScript` rather than `AnimationHook` — a
risk to verify. OBJ cannot carry rigs; rigged assets need glTF (ADR-0004, still
**Proposed** — do not treat glTF as decided).

## Candidate representations (proposed; evaluate all three)
- (a) **Faithful rigid part hierarchy** — each part a component, per-part rigid
  transforms from keyframes. Closest to AC; many components per actor.
- (b) **UE SkeletalMesh, baked** — part hierarchy -> skeleton, keyframes -> anim
  sequences. Better UE tooling/perf; conversion + validation cost.
- (c) **SkeletalMesh, one bone per part + rigid (non-smooth) weights** (M12) —
  faithfully encodes AC's per-part transforms as a *transport representation*
  WITHOUT fabricating smooth deformation. Gets UE animation tooling while staying
  rigid. (This is NOT the strawman "assume bones exist with smooth skinning".)
Evaluate (a)/(b)/(c) against: hook-time alignment, attachments, clothing
substitution, per-part palette swaps, LOD, and perf at creature counts.

## Simulation invariant (M13)
Hook **event-bearing frames** (damage/sound/FX/collision toggles) must stay
aligned to the extracted hook times. Visual interpolation may be upgraded, but an
independent visual retime is allowed **only** via a documented, tested
presentation offset.

## Assumptions it depends on
- A1 [VERIFY]: "no skinning" holds across a representative creature **survey**, not
  just the creatures examined so far.
- A2 [VERIFY]: all gameplay-bearing frames originate from `AnimationHook` (not
  `PhysicsScript`).

## Evidence required before Accepted
- A creature-survey artifact; a hook-vs-`PhysicsScript` audit; a prototype of (a)
  and (c) showing hook-aligned playback.

## Failure mode if an assumption is false
- If some creatures DO use skinning, (a) misrenders them; if cast frames live in
  `PhysicsScript`, ignoring them breaks combat feel.

## Alternatives still live
All of (a)/(b)/(c) until the survey + prototype decide. Plain (b) without rigid
weights risks implying smooth skinning AC lacks — avoid unless (c)'s constraints
apply.

## Acceptance test
- T4 timing: event frames fire at the extracted hook times within tolerance, for
  each representation under evaluation.
