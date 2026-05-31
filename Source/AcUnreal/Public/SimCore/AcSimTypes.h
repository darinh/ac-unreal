// =====================================================================
// AcSimTypes.h
//
// POD types for the Phase 2 simulation core. Pure C++17, no UE deps —
// dual-build pattern (compiles into both the UE module via UBT AND the
// standalone test rig at pipeline/sim-core/build.ps1).
//
// **Units convention (UE-native):** centimetres, centimetres/second,
// centimetres/second². The constants in FMovementParams default to
// the ACE values from contract/decompile-artifacts/physics-feel-spec-response.md
// converted m→cm (×100). Conversion lives in the DataAsset constructor
// or in this struct's defaults — never inside math functions, so the
// math reads naturally with consistent units.
//
// **Why doubles, not floats?** UE5 Large World Coordinates uses double
// precision for FVector; matching that here means lossless conversion
// at the UE boundary. Movement-tick math doesn't care about the perf
// cost either way (a 30 Hz tick is ~33 ms; we have time).
// =====================================================================
#pragma once

#include <cstdint>

namespace ac_sim {

// 3D vector in UE-native coordinates (centimetres).
struct FVec3
{
    double X = 0.0;
    double Y = 0.0;
    double Z = 0.0;
};

// Movement parameters — single source of truth for the feel. UE-side
// these are mirrored by UAcMovementParamsDataAsset and surfaced as a
// UDataAsset so designers can tune without recompile.
//
// Defaults are the ACE values (see contract/decompile-artifacts/
// physics-feel-spec-response.md). Where ACE has no explicit value (e.g.
// turn rate, ground accel), we pick a sensible placeholder and tag it.
struct FMovementParams
{
    // --- §1 timestep ---
    double FixedTimestepSec    = 1.0 / 30.0;  // matches ACE MinQuantum
    double MaxAccumulatorSec   = 2.0;          // matches ACE HugeQuantum (catch-up cap)

    // --- §2 gravity & global ---
    double GravityCmPerSecSq   = -980.0;       // -9.8 m/s² × 100 (ACE PhysicsGlobals.cs:13)

    // --- §3 ground locomotion (ACE MotionInterp.cs:26-31) ---
    double WalkSpeedCmPerSec      = 312.0;     // ACE WalkAnimSpeed 3.12 × 100
    double RunSpeedCmPerSec       = 400.0;     // ACE RunAnimSpeed 4.0 × 100
    double SidestepSpeedCmPerSec  = 125.0;     // ACE SidestepAnimSpeed 1.25 × 100 (animation rate; effective sidestep movement = WalkSpeed * SidestepFactor)
    double BackwardsFactor        = 0.65;      // ACE BackwardsFactor
    double SidestepFactor         = 0.5;       // ACE SidestepFactor — effective sidestep speed = WalkSpeed * this
    double RunTurnFactor          = 1.5;       // ACE RunTurnFactor
    // ACE friction coefficient. The per-tick scalar applied to velocity is
    // pow(1 - FrictionCoefficient, dt), NOT FrictionCoefficient itself.
    // ACE PhysicsObj.cs:2139: var scalar = Math.Pow(1.0f - friction, quantum); Velocity *= scalar.
    // With this default 0.95 and dt=1/30, the per-30Hz multiplier is pow(0.05, 1/30) ≈ 0.9046.
    double FrictionCoefficient    = 0.95;      // ACE PhysicsObj default

    // Turn rate. ACE doesn't expose this as a deg/s; we use 180°/s as a
    // sensible Quake-ish default, multiplied by RunTurnFactor when
    // running. PLACEHOLDER pending spec round.
    double TurnRateRadPerSec      = 3.14159265358979323846; // π rad/s = 180°/s

    // --- §4 jumping ---
    double DefaultJumpVzCmPerSec  = 1000.0;    // ACE 10.0 m/s × 100 (fallback when no weenie)

    // --- §5 collision ---
    double StepHeightCm           = 1.0;       // ACE DefaultStepHeight 0.01 m × 100
    // Min normal.Z for a surface to be considered walkable. ACE
    // PhysicsGlobals.FloorZ = 0.66417414618662751 = cos(48.41°). This is
    // the actual walkable threshold (PhysicsObj.is_valid_walkable). Do
    // NOT confuse with PhysicsGlobals.LandingZ = sin(5°) ≈ 0.0872 — that
    // is a collision/landing TOLERANCE, not a slope threshold (used in
    // BSPTree.cs / Transition.cs / Sphere.cs / CylSphere.cs).
    double WalkableSlopeCosine    = 0.66417414618662751;

    // --- §10 reconciliation ---
    double ServerCorrectionThresholdCm = 5.0;  // ACE 0.05 m × 100 (CheckPositionInternal XY tolerance)
};

constexpr FMovementParams DefaultMovementParams() { return {}; }

// Per-tick input. Axes are clamped [-1, 1] by the caller; the math
// trusts the caller's clamping.
struct FMovementInput
{
    double ForwardAxis     = 0.0;  // [-1, 1], positive = forward
    double RightAxis       = 0.0;  // [-1, 1], positive = right (strafe)
    double TurnAxis        = 0.0;  // [-1, 1], positive = turn right
    bool   bRunPressed     = false;
    bool   bJumpPressed    = false;
};

// Per-character physics state. The sim is stateless — given a state +
// input + dt, produces a new state. This is the property the
// determinism tests verify.
//
// Note: ActionStamp lives on FMovementState for downstream convenience
// but the pure sim integrator does NOT mutate it. Action stamps are
// bumped per-action (when a movement command is queued for the
// network layer), not per-physics-tick. See §10 of the spec response;
// ACE compares stamps on queued actions, not integration steps.
struct FMovementState
{
    FVec3       Position;             // UE world position (cm)
    FVec3       Velocity;             // UE world velocity (cm/s)
    double      YawRad        = 0.0;  // facing yaw (radians, +Z right-hand convention)
    bool        bOnGround     = true;
    std::uint32_t ActionStamp = 0;    // §10 sequencing (wraps at 0x7FFF per ACE MotionInterp.cs:789-824). Bumped per-action by the network-layer caller, NOT per integration tick.
};

} // namespace ac_sim
