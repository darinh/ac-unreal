# 0015 - Indoor-first expedients are temporary (revisit triggers)
Status: Proposed   Date: 2026-05-31

## Context
Several decisions were made to unblock the **first indoor room** that are
correct there but would be wrong if silently inherited as **world-scale**
defaults. They are tuned for a small, static, flat-lit scene - the opposite of a
streamed, day-night, long-view open world. This ADR records them as scaffolding
with explicit revisit triggers so the outdoor/landscape work does not treat them
as settled. [DATA: `Config/DefaultEngine.ini`; ADRs cited.]

## Decision
The following are **temporary**, each owned by the noted future ADR:
| Expedient | Where | Revisit trigger / owner |
|---|---|---|
| Lumen/Nanite/HW-RT disabled | ADR-0002 / ini | Meshes Nanite-safe + perf pass -> ADR-0014 |
| Unlit emissive materials | ADR-0007 | Outdoor/day-night lighting -> ADR-0011 |
| All actors inline in one level (no streaming) | level state | Outdoor/multi-zone -> ADR-0009 |
| Auto-exposure off / fixed exposure | ini (methodology §8) | When a dynamic-lighting look is adopted (ADR-0011) |
| Warm-grey stand-in for black solid surfaces; surface flags not consumed | importer (methodology §5) | When runtime-lighting honoring lands (ADR-0011) |

## Consequences
- Anyone starting outdoor/world-scale work reads this first and knows which
  current settings are *not* endorsed at scale.
- Each row is closed by flipping its owning ADR to Accepted, not by silent edits.

## Alternatives
- Leave expedients undocumented: rejected (the regression risk this whole repo
  keeps hitting - "done" work silently reverts because the why was not recorded).
