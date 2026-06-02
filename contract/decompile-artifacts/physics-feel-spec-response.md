# Physics & Feel Specification — Response (Phase 2)

**Status:** PARTIAL — populated from ACE (server emulator) + AC client
Ghidra decomp, current as of 2026-06-02 (issue #3 added the client-confirmed
§0 world origin + axes / encoding; client load-radius lives in ADR-0009).
Sources cited per field.
**Companion to:** [`contract/physics-feel-spec-request.md`](../physics-feel-spec-request.md).
**Authority of values:** ACE is the **authoritative server** the UE
client will talk to. Where ACE has a value, that value is what the
client MUST predict to. The decompile is consulted to determine
**what the client predicted locally vs what it waited on the server
for** (the §10 client/server split).

> **Sources cited inline:**
> - `[ACE: <file>:<line>]` — file under `C:\Users\darin\repos\ACE\Source\`
> - `[acclient: <addr>]` — function at that address in
>   `C:\Users\darin\repos\ac-client\decomp\_baseline\by_addr\<addr>__*.c`
> - `[community: <source>]` — Asheron's Call community / wiki convention
>   (no in-source citation; treat as "best-known" until verified)

---

## §0. Conventions

| Field | Value | Source |
|---|---|---|
| AC handedness | axis **triad confirmed from the client**: +X **East**, +Y **North**, +Z **up** (NE-of-viewer = both max). The left/right-handed *label* is still UNKNOWN (needs the client's matrix/winding code — issue #4); UE-side design assumption: right-handed. | `[acclient: get_block_orient 0x504F90]` |
| Up-axis | **Z-up** (ACE uses `point.Z`, `vz`, terrain `Z` everywhere; **client** per-block render frame Z origin = 0, height carried on +Z) | `ACE.Server\Physics\Common\Landblock.cs:125-137`; `Position.cs`; `[acclient: calc_frame 0x505460]` |
| Linear unit | **metres** | `LandDefs.BlockLength = 192.0f` is m | `[ACE: LandDefs.cs:102-105]` |
| Angular unit | **radians** (assumed; quaternions used in `Position`) | `[ACE: ACE.Entity\Position.cs:251-264]` |
| Sim time unit | **seconds (float)**; variable-step | `[ACE: MotionInterp / PhysicsObj]` |
| Landblock side | **192 m** (`LandDefs.BlockLength`) | `[ACE: LandDefs.cs:102-105]` |
| Landblock grid count | **255 per axis** (`LandLength=2040`, `LandblockShift=3` → 2040/8=255). **Client-corroborated:** cell-coord guard `≤ 0x7f7` (=2039=255·8−1). | `[ACE: LandDefs.cs:99-105]`; `[acclient: update_block 0x5063A0]` |
| Landblock ID encoding | **`block_high16 \| (cell+1)_low16`**, where `block = (x>>3<<8) \| (y>>3)` and `cell = (x&7)<<3 \| (y&7)`. Note: cell index is **+1**, so low-16 is always non-zero for an addressed cell. **Client-corroborated:** the landscape builds the whole-block id as `((LbX<<8)\|LbY)<<16 \| 0xffff` (high byte = LbX/East, low byte = LbY/North; `0xffff` = whole-block sentinel). | `[ACE: LandDefs.cs:227-239]`; `[ACE: Position.cs:379-390]`; `[acclient: update_block 0x5063A0]` |
| Height-sample grid | **9 × 9 per landblock** (`VertexDim = 9`) | `[ACE: LandDefs.cs:102-107]` |
| Cell side length | **24 m** (192 / 8) | derived from `BlockLength / 8` |
| World origin | **`(0,0,0)` = south-west (min-East, min-North) corner of landblock `(LbX=0, LbY=0)`**, +X East / +Y North / +Z up. A block `(LbX,LbY)` spans AC-m `X∈[LbX·192,(LbX+1)·192]`, `Y∈[LbY·192,…]`; intra-block local coords `[0,192)` from that SW corner. Positions are stored **landblock-LOCAL** (`objcell_id`+local frame), composed to world — never stored global. The client's *render* frame additionally floats around the viewer's block (`calc_frame`). **Client-confirmed (issue #3).** | `[acclient: get_block_orient 0x504F90, calc_frame 0x505460, update_block 0x5063A0]`; see [`notes/client-landblock-load-radius-findings.md`](../../docs/migration/notes/client-landblock-load-radius-findings.md) |

> **⚠ Phase 1 follow-up:** ACE's LandblockId low-16 contains `cell+1`,
> not zero. Our `.aclb` intermediate format requires **low-16 = 0**
> because it represents the *outdoor landblock surface* (the whole
> landblock as a unit, not a cell). Exporters converting from an
> ACE Position to a `.aclb` LandblockId MUST mask the low 16 bits.
> `FORMAT.md` "LandblockId semantics" is being updated accordingly.

---

## §1. Simulation timestep

| Field | Value | Source |
|---|---|---|
| **Fixed sim tick rate** | **Neither AC client nor ACE use a strict fixed-Hz loop.** Both integrate with caller-supplied `dt`. ACE clamps to `[MinQuantum=1/30, MaxQuantum=0.1]`. | `[ACE: PhysicsGlobals.cs:37-43]`; `[acclient: 00510700 UpdatePhysicsInternal]` |
| **Our client choice** | **Fixed 30 Hz (1/30 s) decoupled from render** — matches ACE's `MinQuantum` lower bound so updates we send match ACE's smallest expected integration step | brief Phase 2 requirement + ACE alignment |
| Integration method | semi-implicit Euler (assumed; AC client integrates `pos += v*dt`, `v += a*dt` style) | `[acclient: 00510700]` |
| Per-tick substep count | 1 (no nested substeps in either source) | — |
| Framerate-locked? | **No**, decoupled per brief. Accumulator pattern in `AcSimulationSubsystem`. | brief Phase 2 |
| Max tick catch-up per frame | matches ACE's `HugeQuantum = 2.0 s` (i.e. drop accumulated lag beyond 2 s rather than spiral) | `[ACE: PhysicsGlobals.cs:37-43]` |

---

## §2. Gravity & global constants

| Field | Value | Source |
|---|---|---|
| Gravity | **-9.8 m/s²** (vertical, Z-down) | `[ACE: PhysicsGlobals.cs:13]` |
| Terminal vertical velocity (falling) | **UNKNOWN** — not found in ACE | — |
| Terminal vertical velocity (rising) | **UNKNOWN** | — |
| Max survivable fall velocity | **UNKNOWN** — likely server-authoritative (damage application is) | — |
| Fall-damage formula | **UNKNOWN** | — |

---

## §3. Ground locomotion

| Field | Value | Source |
|---|---|---|
| Movement model (free-form) | Motion-command driven, not force-accel based in the way modern engines integrate. Input → motion command → `MotionInterp` resolves into a velocity → `PhysicsObj` integrates. | `[ACE: MotionInterp.cs:26-31, 394-562]` |
| Run anim speed (base) | **4.0** | `[ACE: MotionInterp.cs:26-31]` |
| Walk anim speed (base) | **3.12** | `[ACE: MotionInterp.cs:26-31]` |
| Sidestep anim speed | **1.25** | `[ACE: MotionInterp.cs:26-31]` |
| Max sidestep anim rate | **3.0** | `[ACE: MotionInterp.cs:26-31]` |
| Backward speed factor | **0.65** of forward | `[ACE: MotionInterp.cs:394-428]` |
| Strafe speed factor | **0.5** of forward | `[ACE: MotionInterp.cs:525-562]` |
| Run-turn factor | **1.5** | `[ACE: MotionInterp.cs:546-549]` |
| Max adjusted speed multiplier | **4.0×** rate cap | `[ACE: MotionInterp.cs:618-632]` |
| Max run speed | `RunAnimSpeed * runRate` (variable per weenie) | `[ACE: MotionInterp.cs:665-699]` |
| Ground acceleration | **UNKNOWN as explicit accel value**; ACE uses an `Acceleration` field on PhysicsObj and integrates `Velocity += Acceleration * quantum` continuously (`PhysicsObj.cs:1854-1858`). Motion commands set the accel target via `MovementManager`; the raw value isn't a single published constant. | inferred from `[ACE: PhysicsObj.UpdatePhysicsInternal]` |
| Friction / deceleration | **ACE coefficient = 0.95 (default); per-tick scalar = `pow(1 - 0.95, dt) = pow(0.05, dt)`** applied every tick on walkable ground (`Velocity *= scalar`). NOT `Velocity *= 0.95`. At our 30 Hz dt=1/30, per-tick scalar ≈ 0.9046. | `[ACE: PhysicsObj.cs:2120-2141 calc_friction]` |
| Turn rate (deg/s) | **UNKNOWN as explicit angular velocity**; turn is a motion command scaled by `RunTurnFactor` when running | `[ACE: MotionInterp.cs:409-428]` |
| Facing snap vs interpolate | **state-driven**; motion-state machine sets facing target, exact interpolation not in extracted code | `[ACE: MotionInterp.cs]` |
| Run-speed dependencies (stamina/encumbrance/species) | `runRate` factor varies per weenie (`WeenieObj`-derived); the formula is server-resolved per character | `[ACE: MotionInterp.cs:665-699]` |
| Sneak / walk-toggle | **UNKNOWN** in extracted code | — |

---

## §3b. Aquatic / swimming movement

**UNKNOWN across the board** — neither the ACE explore nor the acclient
slice surfaced water-specific physics. Likely lives in a separate
state-machine branch we haven't read. Tag for future spec round.

---

## §4. Jumping & airborne

| Field | Value | Source |
|---|---|---|
| Jump trigger | Charge/commit state machine: `charge_jump` sets `StandingLongJump` when standing on walkable ground; `DoJump` commits at powerbar-release time. Local-only prediction. | `[ACE: MotionInterp.cs:564-582, 710-727]`; `[acclient: 0056AF90 CommenceJump]`, `[acclient: 0056B110 DoJump]` |
| Jump impulse (initial Vz) | per-weenie via `WeenieObj.InqJumpVelocity(extent, out vz)`; **fallback 10.0 m/s upward** when no weenie | `[ACE: MotionInterp.cs:634-652]` |
| Jump charge mechanic | `JumpExtent` (0..1) set at `jump(extent, ...)`; `CommenceJump` starts powerbar, `DoJump` consumes powerbar level at commit | `[ACE: MotionInterp.cs:564-582]`; `[acclient: 0056AF90, 0056B110]` |
| Horizontal carry-over | **yes** — `get_leave_ground_velocity()` preserves `get_state_velocity()` and replaces Z with jump Vz | `[ACE: MotionInterp.cs:654-663]` |
| Air control | **partial**; airborne state rejects many motion changes but some still apply | `[ACE: MotionInterp.cs:584-602, 742-767]` |
| Air acceleration | **UNKNOWN as explicit value** | — |
| Max air speed cap | **UNKNOWN as explicit value** | — |
| Landing behavior | `HitGround()` removes link animations and reapplies the active movement | `[ACE: MotionInterp.cs:175-185]` |
| Coyote-time | **none confirmed** — strict on-ground check | inferred |
| Double-jump | **no** (gated by `motion_allows_jump` returning `0x48`) | `[acclient: 005279E0]` |
| Wire packet for jump commit | `0x1bf6` (autonomous) / `0xc9f7` (non-autonomous) via `Proto_UI::SendToWeenie` | `[acclient: 006AFA70, 006AFB30]` |

---

## §5. Collision response

| Field | Value | Source |
|---|---|---|
| Capsule / cylinder dimensions | **UNKNOWN as fixed avatar constants** — likely per-species in weenie data | — |
| Step-up height | **0.01 m** (`DefaultStepHeight`) | `[ACE: PhysicsGlobals.cs:58-59]`; `[acclient: 005180F0 GetStepDownHeight = 0x3c23d70a = 0.01f]` |
| Max walkable slope | **`FloorZ = 0.66417414618662751`** (= cos 48.41°). This is the actual walkable-normal-Z threshold (`PhysicsObj.is_valid_walkable: normal.Z >= FloorZ`). The `LandingZ = 0.0871557` (= sin 5°) is a **separate collision tolerance** used in `BSPTree.cs` / `Transition.cs` / `Sphere.cs` / `CylSphere.cs` — NOT a slope angle. An earlier draft of this spec confused the two; the standalone-tests' default `WalkableSlopeCosine = 0.996` would have made every meaningful incline non-walkable. | `[ACE: PhysicsGlobals.cs:48-50 FloorZ]`; `[ACE: PhysicsObj.cs:2863 is_valid_walkable]` |
| Slide-down behavior | `EdgeSlide` is in the default physics state; `LandingZ` is the *landing-snap tolerance* (you "stick" to a surface within this angle of horizontal on landing). Not a slope-walkability threshold. | `[ACE: PhysicsGlobals.cs:25-27, 45-50]` |
| Wall response | **slide-aware**: `SetPositionFlags.Slide`, `PlacementAllowsSliding=false` unless set | `[ACE: PhysicsObj.cs:302-322]` |
| Ceiling response | **UNKNOWN** | — |
| Character-vs-character | **UNKNOWN** | — |
| Heightfield interpolation | plane-of-terrain-polygon via `GetZ()`; terrain cell selection by `point.X / 24, point.Y / 24` | `[ACE: Landblock.cs:125-149]` |

---

## §6. Input → simulation mapping

| Field | Value | Source |
|---|---|---|
| Input poll rate vs sim tick | client polls DirectInput8 + WIN32 messages; semantic action dispatch via `CInputManager_WIN32::FireInputEvent` (1972 bytes) | `[acclient: notes/input.md]`; `[acclient: 00688800]` |
| Input buffering | **UNKNOWN** as a frames-of-grace value; `PriorityHash<ControlSpecification, ButtonHistoryEntry>` tracks recent button history (size unknown) | `[acclient: 00688800]` |
| Mouselook → yaw | **UNKNOWN as sensitivity curve**; lives in `CInputManager_WIN32` / `CommandInterpreter` | — |
| Keyboard turn-rate | **UNKNOWN as deg/s**; commands `CommandInterpreter::SetHoldRun` / `ToggleAutoRun` set state, not rate | `[acclient: notes/input.md]` |
| Client-side input prediction? | **YES** — jump initial velocity, motion commands, and position updates are applied locally and queued for server | `[acclient: 0056B110 DoJump]`; `[acclient: 00513770 queue_netblob]` |

---

## §7. Animation events that gate gameplay

**Mostly UNKNOWN from this extraction round.** ACE's `MotionInterp`
uses motion-state codes (`0x48` allowed jump, etc.) but doesn't expose
per-action frame timings; those live in ACE's separate combat /
casting systems we haven't deep-dived. AC client's `Hook_AnimDone`,
`MotionDone`, and `PlayerModule` UI/movement handlers are
known-to-exist but not yet read. Tag for future spec round.

Known: jump uses a powerbar gate — `CommenceJump` starts powerbar,
`DoJump` consumes level at commit. The powerbar duration is the
"jump charge window".

---

## §8. Projectiles

**UNKNOWN** — `PhysicsObj.ProjectileTarget` exists but no projectile
kinematics found in the extracted slice.

---

## §9. Casting subsystem timing

**Out of scope** for the Phase 2 sim-core; the cast subsystem is its
own state machine. Tag for a later spec round.

---

## §10. Client/server split — what the client predicts vs waits for

This is the section that most directly informs Phase 2's CMC design.

| Quantity | Client behavior | Server behavior |
|---|---|---|
| Movement input → position | **Predicted locally** at integration time | Server re-integrates, sends correction if drift > threshold |
| Jump | **Predicted locally** (`CommenceJump`/`DoJump` apply Vz immediately) | Server confirms via `unpack_movement`; corrects if invalid |
| Position-update wire format | `uint32 LandblockId, float X/Y/Z, float W/X/Y/Z (quat)` | `[ACE: Position.cs:251-264, 325-359]` |
| Position correction threshold | client accepts server correction if `\|diff.X\| < 0.05 && \|diff.Y\| < 0.05` AND same cell | `[ACE: PhysicsObj.cs:302-322]` |
| Snap vs smooth on correction | tiny drift → accept silently; larger → snap (no smoothing path found) | `[ACE: PhysicsObj.cs:302-322]` |
| Movement command sequence/ack | `action.Stamp & 0x7FFF` vs `ServerActionStamp & 0x7FFFF` with wrap handling | `[ACE: MotionInterp.cs:789-824]` |
| Server-side speed-cheat checks | `CheckPositionInternal` + `FindObjCollisions` validate; details server-side | `[ACE: PhysicsObj.cs:302-322, 381-476]` |
| Cell / portal transitions | server resolves; `LandDefs.AdjustToOutside` + `Position.SetLandblock/SetLandCell` + `AdjustPosition` | `[ACE: LandDefs.cs:120-147]`; `[ACE: Position.cs:117-205]`; `[ACE: PhysicsObj.cs:232-261]` |
| Combat damage | **UNKNOWN from this slice** — almost certainly server-authoritative | — |
| Loot pickup success | **UNKNOWN** — likely server-confirmed | — |
| Level-up / quality changes | **UNKNOWN** — server-driven via `RecvNotice_*` handlers | `[acclient: notes/02-structure.md]` |

### Phase 2 implications

1. **Client predicts position locally** using gravity + friction + jump
   impulse from §2/§3/§4. The 0.05 m XY tolerance is generous enough
   that a correctly-implemented prediction never visibly corrects.
2. **Client must time-stamp every motion update** with the
   wrap-handling stamp model (`& 0x7FFF`).
3. **Wire format** for position is fixed by ACE — when the network
   layer lands (later phase), it serializes the same struct.
4. **No mid-frame interpolation of corrections** — when ACE sends a
   correction outside the 0.05 m tolerance, the client snaps. We can
   *optionally* add visual smoothing on top (presentation-layer
   concern) without affecting the sim trace.

---

## §11. Free-form / spec gaps to fill in subsequent rounds

§11.1 — **Capsule dimensions per species.** ACE doesn't ship these as
fixed constants in the physics core; they're per-weenie. Need to
either extract from `WeenieObj` template data or read the AC client's
character-creation code.

§11.2 — **RESOLVED in §5 above.** ACE's `FloorZ = 0.66417...`
(= cos 48.41°) is the walkable-normal-Z threshold. The earlier
`LandingZ`-based PLACEHOLDER was incorrect; `LandingZ` is a separate
collision-tolerance constant.

§11.3 — **Ground acceleration model — HONEST FRAMING.** ACE does
**not** use "set target velocity directly." It uses forward Euler with
an explicit `Acceleration` field: `Velocity += Acceleration * quantum`
(`PhysicsObj.cs:1854-1858`), with `Acceleration` set by motion
commands via `MovementManager`, and `calc_friction` applied every tick
on walkable ground. The Phase 2 scaffold deliberately simplifies this
to "set horizontal velocity = desired" on input (instead of running
an accel ramp), because the actual ACE accel constants aren't
published as a single number — they emerge from the motion-state
machine. The simplification is a **known divergence from ACE** with
two consequences:
1. The visible velocity steps instantly to the configured run/walk
   speed (no acceleration ramp). ACE would ramp over a few ticks.
2. To preserve designer-expected steady-state speeds, the scaffold
   does NOT apply friction during active input — ACE does. Both
   divergences are within the server's 5 cm XY correction tolerance
   for steady-state motion; transient mismatches (input change, jump
   release) may exceed the threshold and trigger snap-corrections.

Phase 2.x will replace this with a true accel-toward-target model and
enable friction-every-tick, matching ACE's structure. Estimated effort
is small (~30 lines in `IntegrateMovement`) but blocked on either
extracting a representative accel value from ACE motion-state code or
deriving one empirically.

§11.4 — **Animation-event-gates-gameplay timings** (melee swing frame
that applies damage, cast commit frame, projectile launch frame).
Server-authoritative in ACE; client needs to know them only for
prediction. Defer to a combat-focused spec round.

§11.5 — **Projectile speeds and arcs.** Defer.

§11.6 — **Aquatic / swimming model.** Defer.

§11.7 — **Cast subsystem windup/release/fizzle rules.** Defer.

---

## Provenance summary

This response was synthesized from two parallel deep-dives:
- `explore-ace-physics` over `C:\Users\darin\repos\ACE\Source\` (Aug 2026 ACE source — gpt-5.4-mini, ~85 s)
- `explore-acclient-physics` over `C:\Users\darin\repos\ac-client\decomp\_baseline\by_addr\` (Ghidra pseudo-C, gpt-5.4-mini, ~284 s)

The ACE values are normative for the UE client (ACE is the server of
record). The AC client decomp values are advisory (they show what the
original predicted vs waited on the server for, which informs the
seam design).
