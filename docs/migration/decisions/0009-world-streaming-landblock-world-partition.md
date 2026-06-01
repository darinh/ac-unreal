# 0009 - World-scale streaming: landblock grid -> UE World Partition
Status: Proposed   Date: 2026-05-31

## Context
AC is a seamless, zoneless ~49 km world; all world data is keyed **per
landblock** (192 m x 192 m, 8x8 grid of 24 m cells) [DATA: `Program.cs`
`ListLandblocks`/`LandblockInfo`; glossary]. The retail client streamed
landblocks around the player (no zone loads) [COMMUNITY/VERIFY: confirm the
client's active-landblock radius against ACE `LandblockManager` + community
docs]. The current UE project stores **all academy actors inline in one level**
(no streaming), which is the direct cause of the `-game` "Waiting for static
meshes to be ready N/618" hang and does not scale past one zone. See gap doc
[`../notes/feature-disposition-and-design-gaps.md`](../notes/feature-disposition-and-design-gaps.md) §D.

Disposition: **MIRROR** AC's per-landblock streaming intent via a UE mechanism.

## Decision
TBD (Proposed). Candidate [DESIGN]: enable **World Partition** with a streaming
grid aligned to the 192 m landblock boundary (cell-size = 192 m or a divisor),
runtime streaming source on the player; indoor `EnvCell`s grouped as data layers
/ sublevels keyed by landblock. Loading range set from the verified AC radius
(item H1). Deep-dive of the concrete mapping is appended below once drafted.

## Consequences
- Fixes the all-in-one-level hang; required before any outdoor/multi-zone work.
- Forces decisions in ADR-0010 (precision/origin) and ADR-0013 (occlusion) to
  align with the grid; HLOD (an ADD) becomes the mechanism for distant blocks.
- Revisit trigger: if the verified AC load radius or cell size differs from the
  assumed grid, re-tune the WP grid before committing content.

## Alternatives
- Keep one monolithic level: rejected (the current hang; un-scalable).
- Hand-rolled level streaming volumes per landblock: rejected vs World Partition
  unless WP proves unable to honor the landblock grid.

## Verify before locking
- H1: AC client active-landblock load radius (ACE `LandblockManager`).
