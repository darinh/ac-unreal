# 0021 - Determinism at world scale (simulation vs streaming)
Status: Proposed   Date: 2026-05-31

## Context
The simulation lane is a **fixed-tick, parity-tested** model (`contract/` §1): the
parity harness compares recorded UE traces against reference traces, and closeness
is the acceptance criterion. World streaming (ADR-0009) loads/unloads UE actors by
player position. **Risk (flagged by both adversarial reviews):** if the sim's
per-tick **entity membership or iteration order** depends on which UE actors are
currently streamed/resident, the sim becomes **non-deterministic at world scale**
— it can pass parity on a small single-cell scene yet diverge once streaming
changes what is loaded, producing non-reproducible bugs. [DESIGN; grounded in
`contract/` §1 fixed-tick + ADR-0009 streaming.]

## Candidate (proposed, not decided)
The simulation lane runs on its **own authoritative entity set** (the
server-relevant object set from ACE — see ADR-0020 — and the sim's own registry),
**not** on UE's streamed-actor set. Concretely:
- **Streaming is presentation-only:** WP load/unload of meshes/actors must never
  change sim tick membership or order. A streamed-out object that is still
  server-relevant remains in the sim; a streamed-in mesh with no sim entity is
  cosmetic.
- **Stable ordering:** the sim iterates entities by a **stable entity ID**, never
  by UE actor-array index or spawn order.
- **Clock:** a fixed-timestep accumulator decoupled from render/stream rate
  (`contract/` §1).

## Assumptions it depends on
- A1 [DESIGN/VERIFY]: the sim entity set is definable independently of WP residency
  (driven by ADR-0020 server relevance, not UE streaming).
- A2 [VERIFY]: `contract/` §1 fixed-tick params (rate, integration, catch-up clamp).

## Evidence required before Accepted
- A parity test that replays identical recorded input under **>=2 distinct
  streaming states** (e.g. different load radii / cell residency) and produces
  **identical** sim traces.

## Failure mode if violated
- Parity passes on small scenes, diverges in the open world; heisenbugs that move
  with the player's streaming footprint.

## Alternatives still live
- Tie the sim to currently-streamed actors: not selected (non-deterministic).
- Keep the whole world resident: not selected (the scale/hang problem ADR-0009 solves).

## Acceptance test
- Identical sim trace for identical inputs under at least two streaming
  configurations; entity iteration order provably independent of load order.

## Relationships
ADR-0009 (streaming is presentation-only), ADR-0020 (server relevance defines the
sim entity set), `contract/` §1/§10. This ADR is the explicit statement of the
"determinism vs streaming" risk both reviews raised.
