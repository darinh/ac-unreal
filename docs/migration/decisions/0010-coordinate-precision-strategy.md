# 0010 - Coordinate & precision strategy (LWC vs landblock-local; indoor/outdoor domain)
Status: Proposed   Date: 2026-05-31

## Context
A ~49 km world exceeds single-precision float comfort (~20 km) -> jitter. The
proven AC->UE transform is additive (`UE.X=AC.Y*100`, swap X<->Y, reverse winding,
quaternion W,X,Y,Z) [DATA: methodology §4]. UE5 LWC (double precision) is enabled
(`largeworldcoordinates="1"`) [DATA] — but *enabling* LWC is **not** the same as
deciding a coordinate *strategy*. AC's own stored convention (landblock-local vs
global) and the indoor coordinate domain are **UNKNOWN** [DOC: contract §0/§0b].

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

## Assumptions it depends on
- A1 [VERIFY]: AC's stored coordinate convention (landblock-local vs global) — ACE `Position`.
- A2 [VERIFY]: indoor coordinate domain + world origin — contract §0b. **Highest-
  priority decompile item; it also gates ADR-0009 and ADR-0013.** *Partial: the
  EnvCell↔landblock-footprint co-location sub-question is RESOLVED (type-dependent —
  building interiors co-locate, zero-building blocks mostly do not) — see
  [notes/envcell-colocation-findings.md](../notes/envcell-colocation-findings.md). The full
  domain (handedness/up-axis/unit/world origin) still needs the decompile.*

## Evidence required before Accepted
- Contract §0/§0b filled (handedness, up-axis, unit, landblock encoding, indoor
  domain, world origin).
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
