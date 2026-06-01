# 0024 - NPC / crowd / creature LOD & density
Status: Proposed   Date: 2026-05-31

## Context
`DegradeInfo (0x11)` gives **per-object distance LOD** (swap a Setup's GfxObjs by
distance) [DATA: methodology §2; dispositioned MIRROR in the matrix]. But that
covers static/object LOD only — it does **not** address **crowds of creatures**
(towns, spawn clusters) where the cost is many animated, part-based actors at once.
The review flagged this gap ("DegradeInfo covers static LOD, not skeletal/
impostor"). It intersects three existing decisions: ADR-0012 (animation rep —
part-based actors are component-heavy), ADR-0020 (many server-replicated objects),
and ADR-0021 (determinism — presentation LOD must not change the sim entity set).

## Candidate (proposed, not decided)
- **Object visual LOD** from `DegradeInfo` -> UE Static Mesh LODs (**MIRROR**).
- **Crowd-scale presentation LOD (ADD):** distance/significance-based **animation
  update-rate throttling** (UE significance manager / URO), **impostors or merged
  proxies** for distant creature clusters, and for the rigid part-based animation
  (ADR-0012) a far-distance drop to a single static pose / merged mesh.
- **Hard rule:** all of this is **presentation-only** — it must NOT change the
  simulation entity set or tick membership/order (ADR-0021). A throttled or
  impostored creature is still a full sim/server entity (ADR-0020).

## Assumptions it depends on
- A1 [VERIFY]: realistic peak creature/crowd counts in dense areas (towns, event
  spawns) — drives whether impostors are needed vs LOD+throttle alone.
- A2: the animation representation chosen in ADR-0012 (rigid components vs skeletal)
  — determines the cheapest far-LOD form.

## Evidence required before Accepted
- A perf capture of a representative dense scene (N creatures) with/without
  animation throttling + impostors; confirm the sim trace is unchanged across LOD
  settings (the ADR-0021 determinism test).

## Failure mode if an assumption is false
- Crowds tank frame time (per-actor animation + draw), or a presentation LOD path
  accidentally alters sim state (e.g., culling that also despawns the sim entity)
  -> parity break.

## Alternatives still live
- LOD + animation-throttle only (no impostors): sufficient if peak counts are
  modest.
- Mass/ISM-driven crowd rendering for very dense cases (ties to the Mass-entity
  note in ADR-0016's C++ scope).

## Disposition
**MIRROR** (`DegradeInfo` object LOD) **+ ADD** (crowd/animation/impostor LOD —
no retail analogue at UE fidelity).

## Acceptance test
- A dense-creature scene holds the frame-time budget with LOD/throttle/impostors
  on; the recorded sim trace is identical with LOD on vs off (ADR-0021).

## Relationships
ADR-0012 (animation rep), ADR-0020 (server entity lifecycle), ADR-0021
(determinism: LOD is presentation-only), ADR-0014 (Nanite as an alternative LOD
mechanism once safe).
