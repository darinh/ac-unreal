# Physics & Feel Specification Request

**Status:** OPEN — awaiting fill from the decompile agent.
**Audience:** The agent decompiling the official Asheron's Call (AC) client.
**Purpose:** This is the data contract that the UE5 simulation core in this
repo will consume. Every value below is loaded at runtime from a
`UDataAsset`; no value in this spec is allowed to be hard-coded in
simulation logic. The UE5 side currently uses PLACEHOLDER values tagged
`// PLACEHOLDER (spec)` that must be replaced once this document is filled
in.

> **One principle that governs this document:**
> **Feel is simulation, not rendering.** Everything in this request is a
> *behavioral* quantity — the math that decides where the player is and
> what state they are in on a given simulation tick. Visual/rendering
> values do not belong in this document.

---

## How to fill this in

1. For every field marked `UNKNOWN`, replace it with the decompiled value
   and the **provenance** (source file/function/offset and a short
   excerpt, or the disassembly evidence).
2. If a field has no analogue in the original client (e.g., the original
   computes something purely server-side), say so explicitly with
   `N/A (server-authoritative — see §10)` rather than leaving blank.
3. If a field's value depends on context (e.g., movement speed depends on
   character archetype, encumbrance, or species), provide the **function**
   or **lookup table** rather than a single scalar, and note the inputs.
4. Specify **units** for every numeric value. Default AC unit is meters,
   seconds, radians unless otherwise noted (confirm in §0).
5. Where a value was empirically tuned in the original client (no clean
   formula), note that and supply a sampled table.

Hand back the filled document at
`contract/decompile-artifacts/physics-feel-spec-response.md` (or edit this
file in place on a feature branch — either is fine, just be explicit).

---

## §0. Conventions (resolve these first; everything else depends on them)

| Field | Value | Provenance |
|---|---|---|
| AC coordinate handedness (left- or right-handed) | UNKNOWN | |
| AC up-axis (X, Y, or Z) | UNKNOWN — assumed Z-up in UE-side stub | |
| AC linear unit | UNKNOWN — assumed meters in UE-side stub | |
| AC angular unit (radians vs degrees in client storage) | UNKNOWN | |
| AC time unit for sim tick (seconds, or a fixed-point representation) | UNKNOWN | |
| Landblock physical extent (meters per side) | UNKNOWN — community sources cite 192 m × 192 m; confirm | |
| Landblock grid dimensions (count × count of landblocks per world) | UNKNOWN — community sources cite 255 × 255; confirm | |
| Landblock ID encoding (bit layout, byte order, which bits are X vs Y, which bits are intra-LB position) | UNKNOWN | |
| Height-sample grid resolution within a landblock | UNKNOWN — community sources cite 9 × 9; confirm | |
| World origin in AC coordinates (which corner of which landblock is (0,0,0)) | UNKNOWN | |

**Why this section exists first:** The Phase 0 coordinate-transform module
in `Source/AcUnreal/Public/CoordCore/CoordTransform.h` encodes these as
parameters in `FAcWorldConventions`. Round-trip unit tests pass regardless
of which choice you make, but every downstream system assumes one
consistent choice. Pick the one the client actually uses.

---

## §0b. Indoor / dungeon coordinate domain

AC's outdoor world is a 2D landblock grid (covered in §0). Dungeons and
interior cells live in a **separate coordinate domain** with different
ID encoding and origin rules. The Phase 0 `CoordTransform` module
intentionally handles outdoor only; this section is the spec for the
indoor case so Phase 1/2 can extend (or fork) the transform.

| Field | Value | Provenance |
|---|---|---|
| How are indoor positions stored in the client? (local-to-cell origin? global? other?) | UNKNOWN | |
| What is the cell ID encoding for interior cells, and how does it relate to the outdoor 32-bit landblock ID? | UNKNOWN | |
| Does the high byte distinguish outdoor (0x00–0xFD) from interior (0xFE–0xFF reserved? or another scheme)? | UNKNOWN | |
| Within a dungeon, what does an intra-cell coordinate frame look like? (local origin, axis convention) | UNKNOWN | |
| Convention for portal transitions (does the client perform an origin shift when crossing a portal?) | UNKNOWN | |
| Is there a single world-space coord system that spans outdoor + indoor, or are they strictly separate? | UNKNOWN | |
| How are indoor cells streamed (entire cell? sub-cells? always-loaded?) | UNKNOWN | |

---

## §1. Simulation timestep

| Field | Value | Provenance |
|---|---|---|
| Fixed simulation tick rate (Hz) | UNKNOWN | |
| Equivalent fixed timestep (seconds) | UNKNOWN | |
| Integration method (semi-implicit Euler / Verlet / RK / …) | UNKNOWN | |
| Per-tick substep count for collision (if any) | UNKNOWN | |
| Is the simulation framerate-locked or decoupled from render? | UNKNOWN | |
| Maximum tick catch-up per frame (clamp on accumulated lag) | UNKNOWN | |

**Why we need this:** the UE-side simulation is fixed-timestep and
decoupled from render. The timestep value defines what "1 tick of feel"
is and is the canonical clock for the entire spec.

---

## §2. Gravity and global constants

| Field | Value | Provenance |
|---|---|---|
| Gravity vector / scalar | UNKNOWN | |
| Terminal vertical velocity (falling) | UNKNOWN | |
| Terminal vertical velocity (rising, e.g. caps on launch) | UNKNOWN | |
| Maximum survivable fall velocity before damage threshold | UNKNOWN | |
| Fall-damage formula (input → HP loss, or piecewise table) | UNKNOWN | |

---

## §2b. Vital regeneration

Regen rates are core feel-defining quantities (combat pacing, cast
cadence, recovery loops). All AC vitals are attribute-derived; the
underlying formulas are what we need, not just sampled rates.

| Field | Value | Provenance |
|---|---|---|
| Health regen formula (rate, attribute dependencies, buff/debuff modifiers) | UNKNOWN | |
| Stamina regen formula | UNKNOWN | |
| Mana regen formula | UNKNOWN | |
| Regen tick model (continuous vs discrete ticks; if discrete, tick interval) | UNKNOWN | |
| Combat-state vs non-combat-state regen modulation (multiplier, suppression, or other) | UNKNOWN | |
| Meditation / sit-to-regen multiplier (and conditions for it to apply) | UNKNOWN | |
| Encumbrance / pack-weight impact on regen | UNKNOWN | |

---

## §3. Ground locomotion

State the **model** first (e.g., "Quake-style accelerate-and-clamp",
"velocity = direction × speed", "force-based with explicit friction"),
then the numbers.

| Field | Value | Provenance |
|---|---|---|
| Movement model (free-form: equations or pseudocode) | UNKNOWN | |
| Max walk speed | UNKNOWN | |
| Max run speed | UNKNOWN | |
| Backward speed multiplier | UNKNOWN | |
| Strafe speed multiplier | UNKNOWN | |
| Ground acceleration (units/s²) | UNKNOWN | |
| Ground deceleration / friction model + coefficients | UNKNOWN | |
| Turn rate (max yaw degrees/s while standing, while moving) | UNKNOWN | |
| Does the avatar instantly snap to facing direction or interpolate? | UNKNOWN | |
| Does run speed depend on stamina/encumbrance/species/buffs? Provide formula or table. | UNKNOWN | |
| Sneak / walk-toggle behavior (speed factor + state transitions) | UNKNOWN | |

---

## §3b. Aquatic / swimming movement

Water volumes change locomotion fundamentally; we need a separate model
for them. Even if AC's water handling is minimal, document that as the
answer rather than leaving §3 ambiguous.

| Field | Value | Provenance |
|---|---|---|
| How is a water volume detected (depth threshold, volume tag, surface plane test)? | UNKNOWN | |
| Water entry / exit transition (instant state flip, interpolated, position snap) | UNKNOWN | |
| Swim speed — horizontal (max, accel, decel) | UNKNOWN | |
| Swim speed — vertical (max, accel, decel) | UNKNOWN | |
| Input mapping while swimming (does jump = ascend? does crouch = descend?) | UNKNOWN | |
| Can the avatar jump out of water (auto-mantle on shoreline)? | UNKNOWN | |
| Buoyancy / passive vertical drift when no input is applied | UNKNOWN | |
| Breath / drowning mechanic (timer, damage rate, surface-required) — likely none in AC; confirm | UNKNOWN | |
| Collision response in water vs on ground (does collision shape change? does step-up apply?) | UNKNOWN | |

---

## §4. Jumping and airborne movement

| Field | Value | Provenance |
|---|---|---|
| Jump trigger (impulse vs upward velocity set) | UNKNOWN | |
| Jump impulse / initial upward velocity | UNKNOWN | |
| Jump charge mechanic (if any) — input window, charge curve, max charge | UNKNOWN | |
| Horizontal velocity carry-over from ground velocity at jump frame | UNKNOWN | |
| Air control model (none / partial / full) | UNKNOWN | |
| Air acceleration (units/s² while airborne) | UNKNOWN | |
| Max air speed cap (if different from ground cap) | UNKNOWN | |
| Behavior on landing (velocity zero, preserve horizontal, etc.) | UNKNOWN | |
| Coyote-time / late-jump tolerance (frames or seconds) | UNKNOWN — likely none in original; confirm | |
| Double-jump support | UNKNOWN — likely no in original; confirm | |

---

## §5. Collision response

| Field | Value | Provenance |
|---|---|---|
| Capsule / cylinder radius and height (per species/avatar) | UNKNOWN | |
| Step-up height (max vertical climb without jumping) | UNKNOWN | |
| Max walkable slope angle (degrees) | UNKNOWN | |
| Slide-down behavior on too-steep slopes (slide vector / friction) | UNKNOWN | |
| Wall response (slide along / stop dead / bounce) | UNKNOWN | |
| Ceiling response (velocity clamp / bounce) | UNKNOWN | |
| Movement against another character (push / block / pass-through) | UNKNOWN | |
| Movement against environment props (push / block) | UNKNOWN | |
| How is the heightfield within a landblock interpolated between samples? | UNKNOWN — bilinear is most likely | |

---

## §6. Input → simulation mapping

| Field | Value | Provenance |
|---|---|---|
| Input poll rate vs sim tick rate (1:1, oversample, etc.) | UNKNOWN | |
| Input buffering / queuing window (frames of grace) | UNKNOWN | |
| Mouselook → yaw conversion (sensitivity curve, integration vs delta) | UNKNOWN | |
| Keyboard turn-rate (legacy WASD turn) — degrees/s | UNKNOWN | |
| Is there client-side prediction of input → motion before server ack? | UNKNOWN | |

---

## §7. Animation events that gate gameplay

The visuals are presentation; the *timings at which an animation makes
something happen* are simulation. We need the gameplay-relevant frames,
not the visual frames.

For each animated action below, provide:
- Total animation length (in client ticks or seconds)
- The "gameplay moment" frame(s) and what they trigger
- Whether the action is interruptible and at which frames
- The recovery window before another action can start

| Action | Total length | Gameplay frame(s) | Interruptible | Recovery |
|---|---|---|---|---|
| Melee swing (light) | UNKNOWN | UNKNOWN — frame where hit-check fires | UNKNOWN | UNKNOWN |
| Melee swing (medium) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Melee swing (heavy) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Bow draw | UNKNOWN | UNKNOWN — release / launch frame | UNKNOWN | UNKNOWN |
| Crossbow / thrown | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| War-magic cast | UNKNOWN | UNKNOWN — start / commit / release | UNKNOWN | UNKNOWN |
| Life-magic cast | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Item-magic cast | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Use-item (potions, food) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Loot / pickup | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Stance change (combat ↔ peace) | UNKNOWN | UNKNOWN — when stance flag flips | UNKNOWN | UNKNOWN |
| Sit / get-up | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Death / corpse | UNKNOWN | UNKNOWN — when corpse spawns | UNKNOWN | UNKNOWN |

**Note for Niagara re-authoring:** the Niagara replacements for visual FX
may be retimed to look better. The values in this table must come from
the *gameplay* path, not from the matching visual asset.

---

## §8. Projectiles

| Field | Value | Provenance |
|---|---|---|
| Projectile types and per-type initial speed | UNKNOWN | |
| Arc model (ballistic with gravity / straight-line / homing) | UNKNOWN | |
| Gravity applied to projectiles (same as §2 or different) | UNKNOWN | |
| Lifetime cap / max travel distance | UNKNOWN | |
| Collision hull (point / sphere / capsule) | UNKNOWN | |
| Visual-vs-hit-position offset (is the visible mesh the hit-test mesh?) | UNKNOWN | |

---

## §9. Casting subsystem timing

| Field | Value | Provenance |
|---|---|---|
| Cast windup formula (per spell tier / level) | UNKNOWN | |
| Stamina / mana drain timing within cast | UNKNOWN | |
| Fizzle / interrupt rules (movement, damage, line-of-sight) | UNKNOWN | |
| Cooldown / global-cooldown model | UNKNOWN | |
| Cast-while-moving allowed? | UNKNOWN | |

---

## §10. Client/server split (critical for parity model)

AC is heavily server-authoritative. To preserve the original feel
*and* be honest about what the client computes locally, we need:

| Field | Value | Provenance |
|---|---|---|
| Which quantities does the client compute locally and present immediately (no server wait)? | UNKNOWN | |
| Which quantities does the client *predict* and later reconcile against server truth? | UNKNOWN | |
| Which quantities does the client wait for from the server before any visible change? | UNKNOWN | |
| What does the server send back on reconciliation (full state vs corrections vs deltas)? | UNKNOWN | |
| Typical reconciliation cadence (Hz or per-event) | UNKNOWN | |
| Position-correction smoothing (snap / lerp / discard if within ε) | UNKNOWN | |

### §10b. AC-specific position/movement wire state

The Phase 2 movement component subclasses `UCharacterMovementComponent`
and must replay the same prediction/reconciliation shape as the
original client. We need the wire-state schema, not just generic
prediction Q&A.

| Field | Value | Provenance |
|---|---|---|
| Exact wire format for player position (cell/landblock ID + intra-cell position + heading?) | UNKNOWN | |
| Heading/orientation encoding (quaternion / Euler / packed byte) and update frequency | UNKNOWN | |
| Movement-command input shape (key states, mouse delta, action flags) | UNKNOWN | |
| Sequencing / ack model (sequence number, timestamp, ack window) | UNKNOWN | |
| Server position-correction payload (snap target, smoothing window, expected reconciliation tick) | UNKNOWN | |
| Threshold above which the server forces a snap vs a smooth correction | UNKNOWN | |
| Portal / cell-boundary transitions: who computes (client predicts? server-only?) | UNKNOWN | |
| Indoor-vs-outdoor coordinate domain transitions in the wire protocol | UNKNOWN | |
| What collision/cell-boundary checks are predicted client-side vs server-only? | UNKNOWN | |
| Are line-of-sight checks for combat/cast targeting client- or server-authoritative? | UNKNOWN | |

**Why this matters:** The UE client is forward-compatible with talking to
ACEmulator (or equivalent server-authoritative backend). If the original
client predicts movement locally and reconciles, our `CharacterMovement`
subclass must do the same — copying only the server-side math would feel
wrong because it would force a round-trip on every keypress. If the
original client waits on the server for a particular quantity (e.g.
combat damage), we must too — predicting it would *break* feel by showing
optimistic results that the server later disagrees with.

---

## §11. Anything we did not ask about

Free-form section. If during decompilation you encounter a behavior that
demonstrably affects feel and is not covered above, append a numbered
sub-section here describing it.

| | |
|---|---|
| §11.1 | UNKNOWN |
| §11.2 | UNKNOWN |

---

## Open questions back to the decompile agent

- Is the client a fixed-tick simulation, or is it event-driven with
  variable-dt motion integration? (This determines whether §1 is even a
  meaningful question.)
- Are any of the §3 values stored in a data file (DAT / packed table) or
  are they baked into code? If in data, point us at the table so we can
  ingest it directly; do not transcribe by hand.
- Is there a public reference implementation in the ACEmulator codebase
  that already mirrors these values? If yes, citing the equivalent
  function/table is acceptable provenance (plus a confirmation that the
  ACE value matches the client binary).

---

*Once filled, this document defines the truth that the UE5 sim must
match. The parity harness in `harness/diff/` compares recorded UE traces
against reference traces; the closeness of that match — not subjective
judgment — is the parity acceptance criterion.*
