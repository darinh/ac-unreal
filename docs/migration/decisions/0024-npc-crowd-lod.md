# 0024 - NPC / crowd / creature LOD & density
Status: Proposed   Date: 2026-06-01

## Context
`DegradeInfo (0x11)` is a per-**GfxObj** distance-LOD chain: alternate GfxObjs
selected by `MinDist`/`IdealDist`/`MaxDist`, attached at the **`PhysicsPart`**
(per-GfxObj) level, **not** per `Setup` (`SetupModel` has `Parts`/`PlacementFrames`/
`Lights` and has no DegradeInfo field [REF-IMPL: ACE.DatLoader
`FileTypes/SetupModel.cs:23,28,37`]) [REF-IMPL: ACE.DatLoader `Entity/GfxObjInfo.cs:7-11`
(Id/DegradeMode/MinDist/IdealDist/MaxDist), `FileTypes/GfxObjDegradeInfo.cs:13-15`
(the `Degrades` list); methodology §2/§5].

**The retail runtime LOD *behavior* is unverified.** The distance-based GfxObj
selection is **commented out in BOTH reference implementations** — `ACE.Server
Physics/PhysicsPart.cs:19-21,96,99` ("// degrades omitted") and `ACViewer
Physics/PhysicsPart.cs:25-27,164,167`. So only the *struct* is `[REF-IMPL]`; the
retail runtime LOD policy is `[COMMUNITY-VERIFY]`, not a confirmed baseline.

Regardless, per-GfxObj visual LOD does not by itself define **crowd-density,
animation update-rate, impostor, or sim-cull** policy for dense areas (towns,
spawn clusters), where the cost is many animated, part-based actors at once
[DESIGN]. This intersects ADR-0012 (animation rep), ADR-0020 (server-driven
object lifecycle/relevance), and ADR-0021 (determinism).

## Candidate (proposed, not decided)
- **Object visual LOD** from `DegradeInfo` -> UE Static Mesh LODs — **MIRROR**,
  *pending verification of the retail runtime selection behavior* (it is "degrades
  omitted" in ACE/ACViewer today).
- **Crowd-scale presentation LOD — ADD [DESIGN]:** distance/significance-based
  animation update-rate throttling (UE significance manager / URO); impostors or
  merged proxies for distant creature clusters; for the rigid part-hierarchy
  animation option, a far-distance drop to a static pose / merged mesh.
- **Hard rule:** presentation-only — must NOT change the sim entity set or tick
  membership/order (ADR-0021); a throttled/impostored creature is still a full
  sim/server entity (ADR-0020).

## Assumptions it depends on
- A1 [COMMUNITY-VERIFY]: realistic peak creature/crowd counts in dense areas
  (towns, event spawns) — drives impostors-vs-throttle.
- A2 [DESIGN]: the animation representation chosen in ADR-0012 determines the
  cheapest far-LOD form.

## Evidence required before Accepted
- Confirm the retail `DegradeInfo` runtime behavior (currently "degrades omitted"
  in ACE/ACViewer) before the MIRROR half is treated as a real baseline.
- A perf capture of a representative dense scene with/without throttle+impostors;
  confirm the sim trace is unchanged across LOD settings (the ADR-0021 test).

## Failure mode if an assumption is false
- Crowds tank frame time; or a presentation-LOD path alters sim state (e.g. a cull
  that also despawns the sim entity) -> parity break.

## Alternatives still live
- LOD + animation-throttle only (no impostors), if peak counts are modest.
- Mass/ISM-driven crowd rendering for very dense cases.

## Disposition
**MIRROR** (`DegradeInfo` object LOD — pending runtime-behavior verification)
**+ ADD [DESIGN]** (crowd/animation/impostor LOD — no documented retail analogue
in current sources; verify before treating absence as proven).

## Acceptance test
- A dense-creature scene holds the frame-time budget with the **selected**
  presentation-LOD policy enabled (impostors only if that option is selected);
  the recorded sim trace is identical with LOD on vs off (ADR-0021).

## Relationships
ADR-0012 (animation rep; worst-case per-actor cost only if the rigid
part-hierarchy option is chosen), ADR-0020 (server-driven object
lifecycle/relevance; peak counts remain [COMMUNITY-VERIFY]), ADR-0021
(determinism: LOD is presentation-only), ADR-0014 (Nanite as an alternative LOD
mechanism once safe).
