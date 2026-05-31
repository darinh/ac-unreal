// =====================================================================
// AcSimMath.h
//
// Pure functional movement math for the Phase 2 sim core. Every
// function is:
//   - input → output (no globals, no side effects)
//   - deterministic (same args → same result, bit-for-bit)
//   - testable standalone (no UE deps)
//
// The brief invariant "Keep movement deterministic and re-simulatable"
// drives the no-state / no-globals design.
// =====================================================================
#pragma once

#include "SimCore/AcSimTypes.h"

namespace ac_sim {

// Compute the desired horizontal velocity from input + facing.
// Implements the ACE locomotion model: walk/run base speeds scaled by
// backward / sidestep factors, transformed into world space via yaw.
// Vertical component (Z) is always zero — gravity / jump handle Z.
FVec3 ComputeDesiredVelocity(const FMovementInput& Input,
                             double YawRad,
                             const FMovementParams& Params);

// Apply the per-tick friction scalar to horizontal velocity using
// ACE's formula: scalar = pow(1 - FrictionCoefficient, dt). Applied
// every tick the character is on walkable ground (ACE applies it
// unconditionally when on a walkable surface, regardless of input).
// Vertical velocity is NOT damped (gravity handles vertical decay).
FVec3 ApplyHorizontalFriction(const FVec3& Velocity,
                              double DeltaSec,
                              const FMovementParams& Params);

// Apply gravity to vertical velocity for one tick.
double ApplyGravityVz(double Vz, double DeltaSec, const FMovementParams& Params);

// Replace vertical velocity with the jump impulse. Caller is
// responsible for the "on ground" precondition — this function just
// does the velocity replacement, matching ACE's get_leave_ground_velocity()
// (preserve horizontal, replace Z).
FVec3 ApplyJumpImpulse(const FVec3& Velocity,
                       const FMovementParams& Params,
                       double CustomVzCmPerSec = 0.0);

// One full simulation tick: state + input + dt → new state. This is
// the per-tick entry point the UE subsystem calls. The accumulator in
// AcFixedTimestep.h decides HOW MANY times per render frame to call
// this; this function itself is stateless and only knows about a
// single tick.
//
// Behavior summary (Phase 2 scaffold; see "Known divergences" below):
//   - Yaw updated from turn input (rate scaled by RunTurnFactor when running).
//   - Desired horizontal velocity computed from input + new yaw. Forward
//     scaled by WalkSpeed (or RunSpeed if running); backward by
//     WalkSpeed * BackwardsFactor; sidestep by WalkSpeed * SidestepFactor
//     (matches ACE's effective sidestep movement speed).
//   - If on ground + input present: horizontal velocity set directly
//     to desired (PHASE 2 SIMPLIFICATION; see Known divergences).
//     Gravity Vz held at 0.
//   - If on ground + no input: apply ACE friction formula
//     pow(1 - FrictionCoefficient, dt) to horizontal velocity.
//   - If airborne: integrate Vz via gravity. Horizontal velocity is
//     preserved (no air-control accel; §4 air accel UNKNOWN).
//   - Jump input + on ground → upward impulse, leaves ground.
//   - Position integrated using ACE's kinematic formula:
//        pos(t+dt) = pos(t) + v(t)*dt + 0.5*a(t)*dt²
//        v(t+dt)   = v(t) + a(t)*dt
//     (Matches ACE PhysicsObj.UpdatePhysicsInternal:1854-1858. Forward
//     Euler with a half-accel term — exact for constant accel like
//     gravity; matches analytical 0.5*g*t² and 2*V0/|g| airtime.)
//   - ActionStamp is NOT mutated by this function. The network layer
//     (when added) bumps it per outbound action.
//
// **Known divergences from ACE in this Phase 2 scaffold:**
//   1. Set-velocity-directly on input vs ACE's accel-toward-target
//      (ACE: `Velocity += Acceleration * quantum`, where Acceleration
//      is set by motion commands via MovementManager). Implication:
//      our velocity steps instantly to the run/walk speed; ACE ramps.
//      This is a deliberate Phase 2 simplification while we lack a
//      published ACE accel value. Spec §11.3.
//   2. Friction is gated to no-input ticks. ACE applies friction every
//      tick on walkable ground; its accel-toward-target keeps velocity
//      near target despite friction. Without the accel ramp, applying
//      friction during input would visibly slow the character below
//      the configured speed (~10% at 30Hz). The gate preserves
//      designer-expected speeds at the cost of slight ACE divergence
//      during steady-state motion — well within the server's 5 cm
//      correction tolerance for short windows.
//
// **No collision** in this layer. Position will pass through ground.
// The naive Z >= 0 check is in IntegrateMovementWithFlatGround below
// (test convenience only). Real collision goes through the UE CMC
// subclass that wraps this function.
FMovementState IntegrateMovement(const FMovementState& In,
                                 const FMovementInput& Input,
                                 double DeltaSec,
                                 const FMovementParams& Params);

// Test-convenience wrapper: applies IntegrateMovement plus a flat-
// ground clamp at Z=GroundZ. Real production code uses CMC's collision
// instead. NOT exported through the UE wrapper.
FMovementState IntegrateMovementWithFlatGround(const FMovementState& In,
                                               const FMovementInput& Input,
                                               double DeltaSec,
                                               const FMovementParams& Params,
                                               double GroundZ = 0.0);

} // namespace ac_sim
