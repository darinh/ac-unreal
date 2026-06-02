# 0010 - Coordinate & precision strategy (LWC vs landblock-local; indoor/outdoor domain)
Status: Proposed   Date: 2026-05-31

## Context
A ~49 km world exceeds single-precision float comfort (~20 km) -> jitter. The
proven AC->UE transform is additive (`UE.X=AC.Y*100`, swap X<->Y, reverse winding,
quaternion W,X,Y,Z) [DATA: methodology §4]. UE5 LWC (double precision) is enabled
(`largeworldcoordinates="1"`) [DATA] — but *enabling* LWC is **not** the same as
deciding a coordinate *strategy*. AC's own stored convention is now known to be
**landblock-LOCAL** (`objcell_id` + intra-cell frame; world coords are composed,
never stored global) [DATA: acclient — A1, resolved below]; the **indoor**
coordinate domain (cell-id encoding, portal origin-shift) remains **UNKNOWN**
[DOC: contract §0b — issue #4].

## Candidate (proposed, not decided)
Define ONE canonical conversion boundary in `FAcWorldConventions`:
`AC-source -> sim-canonical -> UE-absolute`, keeping the **four layers distinct**
(M11): AC source convention / simulation canonical / UE render storage / network
wire. UE render storage uses **LWC-global** absolute coords; the simulation lane
may use landblock-local internally. The decompiled client convention fixes the
*sim/data* transform — it does **not** dictate UE's presentation storage.

## Invariant (hard rule, not a footnote — M10)
**Exactly one layer applies origin rebasing.** Never compose a WP per-cell origin
shift AND a landblock-local offset on the same value. One helper performs all
conversions, with round-trip tests.
> **Precedent [DATA: acclient `LScape::calc_frame` 0x505460].** The retail client
> already did exactly this: it rebases the entire landscape **relative to the
> viewer's landblock** (`block_frame.origin = (block_idx − viewer_b_off)·block_length`)
> — a single floating-origin layer that kept float precision across the ~49 km
> world. UE5 reproduces it with WP origin-shifting + LWC; do **not** also apply a
> landblock-local offset on top. See [notes/client-landblock-load-radius-findings.md](../notes/client-landblock-load-radius-findings.md) §3.

## Assumptions it depends on
- A1 [RESOLVED 2026-06-02 — [notes/client-landblock-load-radius-findings.md](../notes/client-landblock-load-radius-findings.md)]:
  AC's stored coordinate convention is **landblock-LOCAL** — a position is
  `(objcell_id, intra-cell frame)`, not a global vector; world coords are *composed*
  from the cell id [DATA: acclient `CPhysicsObj::m_position.objcell_id`; consistent
  with the ACE wire `Position` = `LandblockId + local X/Y/Z + quat`]. **Outdoor
  world origin/axes also resolved**: `(0,0,0)` = SW corner of LB(0,0), +X East,
  +Y North, +Z up; 255 landblocks/axis; `block_length = square_length·8 = 192 m`.
- A2 [PARTIAL]: **outdoor** world origin/axes RESOLVED (see A1); the **indoor**
  coordinate domain (cell-id encoding, intra-cell axis frame, portal origin-shift)
  remains the **highest-priority decompile item — issue #4** (gates ADR-0013/0019).
  *The EnvCell↔landblock-footprint co-location sub-question is separately RESOLVED
  (type-dependent — building interiors co-locate, zero-building blocks mostly do
  not) — see [notes/envcell-colocation-findings.md](../notes/envcell-colocation-findings.md).
  Remaining for §0b: handedness sign-label and the indoor domain.*

## Evidence required before Accepted
- Contract §0/§0b filled. **Done (issue #3):** up-axis (Z), unit (m), landblock
  encoding ((LbX<<8)|LbY, 255/axis), extent (192 m), **world origin** (SW corner of
  LB(0,0), +X E/+Y N). **Remaining (issue #4):** handedness sign-label and the full
  **§0b indoor** domain (cell-id encoding, intra-cell frame, portal origin-shift).
- The conversion helper exists with round-trip tests at: landblock (0,0); academy
  `0x8602`; far corner (255,255); a co-located indoor cell.

## Failure mode if an assumption is false
- If interiors are a *separate* domain (not landblock-local under the block), the
  single-boundary model needs an explicit domain switch at portal transitions
  (see ADR-0019 Portal transitions).
- If per-landblock origin + local offset accumulate in **float** before promotion
  to double, jitter returns at ~25 km (promote to double before accumulation).

## Alternatives still live
- Landblock-local everywhere (incl. UE storage), per-cell rebased: viable if LWC
  proves insufficient or parity demands bit-identical local coords.
- Single-precision global: not selected (jitter at AC scale).

## Acceptance test
- Place + render at the far corner (255,255): no positional jitter; round-trip
  AC-source <-> UE-absolute is exact within tolerance at all four test points.
