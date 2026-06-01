# 0010 - Coordinate & precision strategy (LWC vs landblock-local; indoor/outdoor domain)
Status: Proposed   Date: 2026-05-31

## Context
A ~49 km world exceeds single-precision float comfort (~20 km) -> jitter. AC
managed this with **landblock-local** coordinates (global = landblock origin +
local) [COMMUNITY/VERIFY: confirm against ACE `Position`/`Frame`]. UE5 **Large
World Coordinates** (double precision) is active here (engine log
`largeworldcoordinates="1"`). The simulation lane's coordinate conventions are
still UNKNOWN in the contract ([`../../contract/physics-feel-spec-request.md`](../../contract/physics-feel-spec-request.md)
§0/§0b: handedness, up-axis, unit, landblock encoding, indoor domain, world
origin). The proven AC->UE transform (`UE.X=AC.Y*100`, swap X<->Y, reverse
winding, quaternion W,X,Y,Z) is documented [DATA: methodology §4].

Disposition: **MIRROR** the capability (render a 49 km world without artifacts);
**REPLACE** the mechanism (LWC) — or keep landblock-local to pair with WP cells.

## Decision
TBD (Proposed). Two candidate strategies [DESIGN]:
(a) **LWC-global** double-precision world coords for everything; simplest, lets
WP place blocks at true world positions. (b) **Landblock-local + per-cell
origin** (rebase per WP cell), closer to AC and bounded-precision per block.
Must also fix the **indoor<->outdoor domain** (contract §0b): one unified world
space vs separate domains with a portal-transition origin shift.

## Consequences
- Drives ADR-0009 (WP cell origins) and the sim-core transform; whatever is
  chosen must be the single `FAcWorldConventions` used by both lanes.
- Revisit trigger: contract §0/§0b answers from the decompile/ACE may force (b).

## Alternatives
- Single-precision global: rejected (jitter at AC scale).

## Verify before locking
- H2: landblock-local vs global convention; indoor domain + world origin
  (ACE `Position`; contract §0/§0b).
