---
name: ac-mmorpg-networking
description: "Use when building the live MMO client layer for AC in Unreal — connecting to an ACEmulator server, the Turbine UDP protocol, login/ISAAC handshake, the GameAction/GameEvent message taxonomy, and mapping AC's server-authoritative prediction/reconciliation onto UE networking + a UCharacterMovementComponent subclass. AC is heavily server-authoritative; the wire protocol must be MIRRORED (we target ACEmulator, which speaks retail)."
metadata:
  category: networking
---

# AC MMO client networking (server-authoritative, ACEmulator-compatible)

The UE client is forward-compatible with **ACEmulator** (open-source AC server),
which implements a **retail-compatible Turbine protocol**. That makes the wire
format a **hard MIRROR**: we cannot "improve" it without losing server
compatibility. Exact byte-for-byte equivalence with the *retail* server is
`[COMMUNITY/VERIFY]` — target ACE and confirm against a recorded session. AC is
**heavily server-authoritative** — copying only server-side math, or predicting
things the server owns, both break feel. See `docs/migration/README.md` §XI/§XII
and `contract/physics-feel-spec-request.md` §10/§10b.

## Layers to mirror (README §XI decomposition)
- **Transport** — Turbine **UDP**: packet headers, fragmentation/reassembly,
  sequencing, ack/retransmit, separate world vs auth channels. `[REF-IMPL]` ACE.
- **Login/handshake** — connect, login auth, **ISAAC** stream cipher seeds,
  session establishment.
- **Character select / enter-world** — char list, selection, world entry,
  portal/teleport transitions.
- **Message taxonomy** — `GameAction` (client->server), `GameEvent` (server->client
  *targeted* events), and `GameMessage` (server->client world/object state), with
  ordered/sequenced (F7B0) flows. `[REF-IMPL]` ACE.
- **Object/state sync** — `GameMessage` object create/update/delete + position
  broadcasts (ACE opcodes `ObjectCreate`/`ObjectDelete`/`UpdatePosition`,
  `GameMessageOpcode.cs:50-53`), visibility (ties to streaming relevance — see
  `ac-world-streaming`).

## The prediction/reconciliation contract (do NOT guess — `contract/` §10)
Replicate the *shape* of AC's client/server split, not a generic one:
- Quantities the client computes locally and shows immediately (no server wait).
- Quantities the client **predicts** then reconciles against server truth.
- Quantities the client **waits** for from the server before any visible change
  (e.g. combat damage is server-authoritative — predicting it shows optimistic
  results the server later contradicts -> wrong feel).
Our movement uses a **`UCharacterMovementComponent` subclass** that must replay
the same predict/reconcile shape: mirroring only server math would force a
round-trip per keypress and feel laggy; predicting server-owned quantities breaks
parity. All of §10/§10b is currently **UNKNOWN** pending the decompile — fill it
from the client binary + confirm against ACE before implementing.

## Wire state to capture (`contract/` §10b)
Player position wire format (cell/landblock id + intra-cell position + heading);
heading encoding + update rate; movement-command input shape; sequence/ack model;
server position-correction payload + snap-vs-smooth threshold; who computes
portal/cell-boundary transitions; indoor<->outdoor domain transitions on the wire;
which collision / line-of-sight checks are client-predicted vs server-only.

## Disposition
- Wire protocol, login/ISAAC, message taxonomy, prediction shape: **MIRROR** (hard
  requirement for ACE compatibility).
- Rules/combat/spell resolution: **MIRROR** (server-authoritative; consume ACE /
  weenie defaults; the client needs only a subset — spell components, fonts,
  strings, char-gen).
- UE transport/replication plumbing implementation: **IMPROVE** internally as long
  as the on-wire bytes and the predict/reconcile *behavior* match.

## Verify before locking
Exact packet shapes + sequencing; ISAAC seed derivation; the §10/§10b wire schema.
Prefer citing the equivalent ACEmulator function/table as provenance, plus a
confirmation it matches the client binary. Treat anything not so confirmed as
`[COMMUNITY/VERIFY]`.
