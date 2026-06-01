# 0020 - Network object lifecycle / replication of other players & creatures
Status: Proposed   Date: 2026-05-31

## Context
The disposition matrix dispositions networking as "MIRROR" in one word but gives
no **mechanism** for how dynamic objects (other players, creatures, items) appear,
move, and disappear. AC is server-authoritative: the server broadcasts object
create/update/delete and position updates (`GameEvent CreateObject` etc.)
[REF-IMPL: ACE — relayed from the multi-LLM review; confirm the message set], and
spawns are defined server-side (ACE `landblock_instance`). Critically, **the
server is ACEmulator, not a UE dedicated server**, so UE's native replication
graph does not apply — relevance/authority come from the AC protocol.

## Candidate (proposed, not decided)
A **network object manager** that maps the AC object-lifecycle messages to UE
actor spawn / update / destroy: `CreateObject -> spawn` (resolve appearance via
the asset pipeline), position broadcasts -> movement/interp, `DeleteObject ->
destroy`. **Relevance is server-driven** (we consume AC's visibility/range), then
reconciled with World-Partition streaming (ADR-0009) so a server-relevant object
in a not-yet-streamed cell is handled deliberately (force-load vs defer).

## Assumptions it depends on
- A1 [VERIFY]: the GameEvent object-lifecycle message set + position-update cadence
  (`contract/` §10/§10b); the wire schema for create/update/delete.
- A2 [VERIFY]: AC's relevance/visibility rules and how they relate to landblock.

## Evidence required before Accepted
- Fill `contract/` §10b (wire state); map the relevant ACE GameEvent catalog;
  confirm against a recorded session.

## Failure mode if an assumption is false
- Actors leak / duplicate / desync; server-relevant objects fall outside the WP
  streaming radius and never spawn (or spawn into an unloaded cell).

## Alternatives still live
- UE replication graph / native UE networking: **not applicable** — there is no UE
  authoritative server here; ACE is authoritative. We mirror AC relevance, not UE's.

## Acceptance test
- Against a recorded ACE session: a `CreateObject` spawns the correct actor at the
  correct place; updates track position; `DeleteObject` cleans up; relevance
  matches the server within the streaming reconciliation rules.

## Relationships
Depends on `contract/` §10/§10b and ADR-0009 (streaming relevance); the
determinism risk note applies (streaming must not perturb the fixed-entity sim tick).
