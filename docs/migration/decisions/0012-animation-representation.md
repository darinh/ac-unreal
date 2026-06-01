# 0012 - Animation representation: rigid part-based vs skeletal mesh
Status: Proposed   Date: 2026-05-31

## Context
AC bodies are a `Setup (0x02)` of body-part `GfxObj`s wired by `ObjectHierarchy
(0x0E00000D)`, animated as **part-based rigid transforms - no skinning/bones**
[DATA/REF-IMPL: methodology §5, "confirmed for all creatures"]. Motion comes from
`MotionTable (0x09)` -> `AnimData` -> `Animation (0x03)` keyframes;
`AnimationHook`s fire gameplay-timed events (`AttackHook` gates combat, etc.)
[DATA: methodology §5]. Those **hook timings are simulation** and are owed to the
parity contract ([`../../contract/physics-feel-spec-request.md`](../../contract/physics-feel-spec-request.md) §7).

Disposition: **MIRROR** the gameplay *timing* exactly; the *rendering*
representation is a presentation-lane choice (a genuine fork).

## Decision
TBD (Proposed). Two candidate representations [DESIGN]:
(a) **Faithful rigid part hierarchy** - import each part as a component, drive
per-part rigid transforms from `Animation` keyframes (closest to AC; no retarget
risk; many components per actor). (b) **Convert to a UE Skeletal Mesh** - bake
the part hierarchy into a skeleton, keyframes into anim sequences (better UE
tooling/perf/animation features; conversion + validation cost). Either way the
**hook frame timings** are extracted and fed to the sim, not the visuals.

## Consequences
- Affects NPCs/creatures, particles attachment, perf (component count), and the
  importer (OBJ cannot carry rigs -> glTF, ADR-0004).
- Revisit trigger: if rigid-part perf or animation fidelity is unacceptable at
  creature counts, switch to (b).

## Alternatives
- Skinned import assuming bones exist: rejected (AC has none; would fabricate data).

## Verify before locking
- Hook frame semantics per action (contract §7); part counts on representative creatures.
