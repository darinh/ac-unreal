// =====================================================================
// AcSimMath.cpp
//
// Implementations for the Phase 2 pure sim core. See header for design
// rules. The ACE-derived constants live in FMovementParams; this file
// has no compile-time literals beyond mathematical identities (0.0,
// 1.0, π).
// =====================================================================
#include "SimCore/AcSimMath.h"

#include <cmath>

namespace ac_sim {

FVec3 ComputeDesiredVelocity(const FMovementInput& Input,
                             double YawRad,
                             const FMovementParams& Params)
{
    // Pick base forward speed: run vs walk.
    const double ForwardBase = Input.bRunPressed
        ? Params.RunSpeedCmPerSec
        : Params.WalkSpeedCmPerSec;

    // Forward component: negative input → backwards (× BackwardsFactor).
    // Positive input → forward at full speed. Linear scale by axis.
    double ForwardComp = 0.0;
    if (Input.ForwardAxis >= 0.0)
    {
        ForwardComp = Input.ForwardAxis * ForwardBase;
    }
    else
    {
        ForwardComp = Input.ForwardAxis * ForwardBase * Params.BackwardsFactor;
    }

    // Sidestep component: ACE's effective sidestep MOVEMENT speed is
    // WalkSpeed * SidestepFactor (NOT SidestepAnimSpeed — that's the
    // animation rate; the conversion via WalkAnimSpeed/SidestepAnimSpeed
    // collapses to WalkSpeed * SidestepFactor for the actual velocity
    // applied). Run does not amplify sidestep in ACE; sidestep speed
    // is independent of run state.
    const double RightComp = Input.RightAxis * Params.WalkSpeedCmPerSec * Params.SidestepFactor;

    // Transform local (forward, right) into world via yaw rotation
    // around UE's +Z axis. At yaw=0: forward=+X, right=+Y.
    const double Cy = std::cos(YawRad);
    const double Sy = std::sin(YawRad);

    FVec3 V;
    V.X = ForwardComp * Cy - RightComp * Sy;
    V.Y = ForwardComp * Sy + RightComp * Cy;
    V.Z = 0.0;
    return V;
}

FVec3 ApplyHorizontalFriction(const FVec3& Velocity,
                              double DeltaSec,
                              const FMovementParams& Params)
{
    // ACE formula: Velocity *= pow(1 - FrictionCoefficient, dt).
    // (ACE PhysicsObj.cs:2139.) Guard against pathological coefficients
    // (>= 1 → log of zero or negative; <= 0 → 1.0 scalar i.e. no friction).
    const double Coef = Params.FrictionCoefficient;
    FVec3 Out = Velocity;
    if (Coef <= 0.0 || Coef >= 1.0 || !(DeltaSec > 0.0))
    {
        return Out;  // no decay (degenerate input — would-be NaN or no-op)
    }
    const double Scalar = std::pow(1.0 - Coef, DeltaSec);
    Out.X *= Scalar;
    Out.Y *= Scalar;
    // Z is gravity's domain; do not touch.
    return Out;
}

double ApplyGravityVz(double Vz, double DeltaSec, const FMovementParams& Params)
{
    return Vz + Params.GravityCmPerSecSq * DeltaSec;
}

FVec3 ApplyJumpImpulse(const FVec3& Velocity,
                       const FMovementParams& Params,
                       double CustomVzCmPerSec)
{
    FVec3 Out = Velocity;
    Out.Z = (CustomVzCmPerSec > 0.0)
        ? CustomVzCmPerSec
        : Params.DefaultJumpVzCmPerSec;
    return Out;
}

FMovementState IntegrateMovement(const FMovementState& In,
                                 const FMovementInput& Input,
                                 double DeltaSec,
                                 const FMovementParams& Params)
{
    FMovementState Out = In;

    // --- Yaw update (turn input × rate, scaled by run multiplier) ----
    const double TurnRate = Input.bRunPressed
        ? Params.TurnRateRadPerSec * Params.RunTurnFactor
        : Params.TurnRateRadPerSec;
    Out.YawRad = In.YawRad + Input.TurnAxis * TurnRate * DeltaSec;

    // --- Compute desired horizontal velocity (from input + new yaw) --
    const FVec3 Desired = ComputeDesiredVelocity(Input, Out.YawRad, Params);
    const bool bHasMoveInput = (Input.ForwardAxis != 0.0) || (Input.RightAxis != 0.0);

    // --- Pre-integration velocity for kinematic position step --------
    // ACE uses pos += v(t)*dt + 0.5*a(t)*dt²; v += a(t)*dt. The "v(t)"
    // is PRE-update velocity; "a(t)" is the acceleration applied this
    // tick. We must capture v BEFORE we mutate it, then integrate
    // position using v_pre and accel, then update v_post.
    FVec3 VelocityPre = In.Velocity;
    FVec3 Acceleration{ 0.0, 0.0, 0.0 };

    if (Out.bOnGround)
    {
        if (bHasMoveInput)
        {
            // Phase 2 simplification: instantly set horizontal velocity
            // to desired (instead of ACE's accel-toward-target model).
            // Known divergence — documented in spec §11.3 and the
            // header comment for IntegrateMovement.
            //
            // Note: we deliberately DON'T apply friction on this branch.
            // ACE applies friction every tick (including during input);
            // combined with its accel-toward-target push, the steady-
            // state velocity converges to the desired. If we applied
            // friction here without the accel push, the visible
            // velocity would be desired × friction_scalar (~90% of
            // configured) — surprising for designers who expect the
            // tuned value to be the visible value. Phase 2.x will
            // implement the full accel ramp and re-enable friction on
            // this branch.
            VelocityPre.X = Desired.X;
            VelocityPre.Y = Desired.Y;
        }
        // Gravity is held off when grounded (CMC's ground constraint).
        Acceleration.Z = 0.0;
    }
    else
    {
        // Airborne: gravity is the only acceleration in this scaffold
        // (no air-control accel — §4 air accel UNKNOWN). Horizontal
        // velocity is preserved.
        Acceleration.Z = Params.GravityCmPerSecSq;
    }

    // --- Jump impulse (replaces Vz with jump velocity, leaves ground) -
    // ACE's order (PhysicsObj.UpdatePhysicsInternal): the motion-state
    // machine sets the leave-ground velocity, THEN the physics tick
    // integrates with both that velocity AND gravity. So if we jump
    // this tick, gravity SHOULD apply to the position step too.
    // Switch Acceleration.Z to g now so the kinematic integrator
    // below sees gravity on the jump frame.
    if (Input.bJumpPressed && Out.bOnGround)
    {
        const FVec3 PostJump = ApplyJumpImpulse(VelocityPre, Params);
        VelocityPre = PostJump;
        Out.bOnGround = false;
        Acceleration.Z = Params.GravityCmPerSecSq;
    }

    // --- Position integration: ACE's kinematic formula ----------------
    // pos(t+dt) = pos(t) + v(t)*dt + 0.5*a(t)*dt²
    const double HalfDtSq = 0.5 * DeltaSec * DeltaSec;
    Out.Position.X = In.Position.X + VelocityPre.X * DeltaSec + Acceleration.X * HalfDtSq;
    Out.Position.Y = In.Position.Y + VelocityPre.Y * DeltaSec + Acceleration.Y * HalfDtSq;
    Out.Position.Z = In.Position.Z + VelocityPre.Z * DeltaSec + Acceleration.Z * HalfDtSq;

    // --- Velocity update: v(t+dt) = v(t) + a(t)*dt --------------------
    Out.Velocity.X = VelocityPre.X + Acceleration.X * DeltaSec;
    Out.Velocity.Y = VelocityPre.Y + Acceleration.Y * DeltaSec;
    Out.Velocity.Z = VelocityPre.Z + Acceleration.Z * DeltaSec;

    // --- Friction (only when no input on ground; see Known divergences) ---
    // Phase 2 simplification: friction applies only when input is
    // absent, so the designer's configured walk/run speed IS the
    // visible steady-state speed. ACE applies friction every tick
    // including during input, but its accel-toward-target push keeps
    // velocity near the configured target. Phase 2.x will implement
    // the full accel-ramp model and re-enable friction on the
    // active-input branch.
    if (Out.bOnGround && !bHasMoveInput)
    {
        const FVec3 Damped = ApplyHorizontalFriction(Out.Velocity, DeltaSec, Params);
        Out.Velocity.X = Damped.X;
        Out.Velocity.Y = Damped.Y;
    }

    // --- Action stamp: NOT mutated here ---
    // ACE compares stamps on queued actions, not per-physics-tick. The
    // network layer (when added) bumps Out.ActionStamp when emitting a
    // movement command. Preserve the input value verbatim so this sim
    // step is action-stamp-agnostic.
    Out.ActionStamp = In.ActionStamp;

    return Out;
}

FMovementState IntegrateMovementWithFlatGround(const FMovementState& In,
                                               const FMovementInput& Input,
                                               double DeltaSec,
                                               const FMovementParams& Params,
                                               double GroundZ)
{
    FMovementState Out = IntegrateMovement(In, Input, DeltaSec, Params);

    // Naive flat-ground clamp — test convenience, NOT production
    // collision. Real collision goes through CMC's PhysWalking/Falling
    // override which inherits UE's swept-collision machinery.
    if (Out.Position.Z <= GroundZ)
    {
        Out.Position.Z = GroundZ;
        if (Out.Velocity.Z < 0.0)
        {
            Out.Velocity.Z = 0.0;
        }
        Out.bOnGround = true;
    }

    return Out;
}

} // namespace ac_sim
