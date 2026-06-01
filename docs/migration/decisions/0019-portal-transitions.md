# 0019 - Portal transitions / recall / teleport
Status: Proposed   Date: 2026-05-31

## Context
AC interiors are reached through **portals**; recall/teleport move the player
across the world. Whether the client performs a **coordinate-domain shift** on a
portal crossing is UNKNOWN (`contract/` §0b), and who computes the transition
(client-predicted vs server-only) is UNKNOWN (`contract/` §10b). This ADR sits at
the intersection of ADR-0010 (coords/domain), ADR-0009 (streaming the
destination), and ADR-0013 (destination cell visibility).

## Candidate (proposed, not decided)
A portal-transition system that handles three things together:
1. **Coordinate-domain switch** — only if interiors are a separate domain
   (resolved by ADR-0010); otherwise a normal in-world move.
2. **Destination streaming** — ensure the target cell/landblock is resident before
   the player is placed (ADR-0009 / ADR-0013).
3. **Authority** — mirror whether the server owns the transition (`contract/`
   §10b); if the client predicts it, reconcile against the server.

## Assumptions it depends on
- A1 [VERIFY]: does the client origin-shift on a portal crossing? (`contract/` §0b)
- A2 [VERIFY]: client-predicted vs server-authoritative transitions (`contract/` §10b)
- A3: ADR-0010 has resolved the indoor/outdoor coordinate domain.

## Evidence required before Accepted
- Fill `contract/` §0b (portal-transition origin shift) and §10b (who computes the
  transition); confirm against the client + ACE.

## Failure mode if an assumption is false
- Wrong origin handling -> position desync or precision break exactly at
  transitions (the worst place for it); double-rebase (see ADR-0010 invariant).

## Alternatives still live
- Treat all space as one unified domain (valid ONLY if ADR-0010 confirms unified
  coords; then transitions are ordinary streamed moves).

## Acceptance test
- Cross a portal in both directions and recall/teleport: position, destination
  streaming, and server reconciliation are all correct; no jitter at the seam.
