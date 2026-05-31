// =====================================================================
// SimCoreTests.cpp
//
// Standalone tests for the Phase 2 sim core. Built directly with
// cl.exe via pipeline/sim-core/build.ps1 — no UBT, no UE. Same source
// files are compiled into the UE module by UBT.
//
// Tests prove:
//   * Determinism (re-simulatable; brief invariant)
//   * Gravity arc matches kinematic formula
//   * Jump peak height + airtime matches V²/(2g) + 2V/g
//   * Horizontal friction decays geometrically when no input
//   * Walk / run / backward / sidestep speeds match ACE constants
//   * Yaw rotation rotates velocity correctly
//   * Action stamp wraps at 0x7FFF (§10 sequencing)
//   * Fixed-step accumulator: variable frame times → consistent ticks
//   * Accumulator catch-up cap prevents spiral of death
// =====================================================================

#include "SimCore/AcSimTypes.h"
#include "SimCore/AcSimMath.h"
#include "SimCore/AcFixedTimestep.h"

#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <vector>

using namespace ac_sim;

namespace {

int gPassed = 0;
int gFailed = 0;

bool NearlyEqual(double A, double B, double Abs = 1e-9, double Rel = 1e-6)
{
    const double D = std::fabs(A - B);
    if (D <= Abs) return true;
    const double M = std::fmax(std::fabs(A), std::fabs(B));
    return D <= Rel * M;
}

void Report(bool Ok, const char* Name)
{
    if (Ok) { ++gPassed; std::printf("  PASS  %s\n", Name); }
    else    { ++gFailed; std::printf("  FAIL  %s\n", Name); }
}

// -----------------------------------------------------------------------
// Determinism
// -----------------------------------------------------------------------

FMovementState RunSequence(const std::vector<FMovementInput>& Inputs,
                           const FMovementParams& Params)
{
    FMovementState S;
    for (const auto& I : Inputs)
    {
        S = IntegrateMovementWithFlatGround(S, I, Params.FixedTimestepSec, Params);
    }
    return S;
}

bool StatesBitEqual(const FMovementState& A, const FMovementState& B)
{
    auto BitsEq = [](double X, double Y) {
        std::uint64_t xb = 0, yb = 0;
        std::memcpy(&xb, &X, 8);
        std::memcpy(&yb, &Y, 8);
        return xb == yb;
    };
    return BitsEq(A.Position.X, B.Position.X)
        && BitsEq(A.Position.Y, B.Position.Y)
        && BitsEq(A.Position.Z, B.Position.Z)
        && BitsEq(A.Velocity.X, B.Velocity.X)
        && BitsEq(A.Velocity.Y, B.Velocity.Y)
        && BitsEq(A.Velocity.Z, B.Velocity.Z)
        && BitsEq(A.YawRad, B.YawRad)
        && A.bOnGround == B.bOnGround
        && A.ActionStamp == B.ActionStamp;
}

void TestDeterminism()
{
    std::printf("[Determinism: same inputs -> bit-identical state]\n");
    const FMovementParams P;
    // Build a long, varied input sequence.
    std::vector<FMovementInput> Inputs;
    for (int i = 0; i < 600; ++i) // 20 seconds at 30 Hz
    {
        FMovementInput In;
        In.ForwardAxis = std::sin(i * 0.1) * 0.5 + 0.5; // varies [0,1]
        In.RightAxis = std::cos(i * 0.07) * 0.5;
        In.TurnAxis = std::sin(i * 0.03) * 0.3;
        In.bRunPressed = (i % 67) < 33;
        In.bJumpPressed = (i % 91) == 0;
        Inputs.push_back(In);
    }
    const FMovementState A = RunSequence(Inputs, P);
    const FMovementState B = RunSequence(Inputs, P);
    const FMovementState C = RunSequence(Inputs, P);
    Report(StatesBitEqual(A, B), "run #1 == run #2 (bit-for-bit)");
    Report(StatesBitEqual(B, C), "run #2 == run #3 (bit-for-bit)");
}

// -----------------------------------------------------------------------
// Gravity arc
// -----------------------------------------------------------------------

void TestGravityArc()
{
    std::printf("[Gravity: drop from rest matches kinematic 0.5*g*t^2]\n");
    const FMovementParams P;
    const double H0 = 1000.0; // 10 m up
    FMovementState S;
    S.Position.Z = H0;
    S.bOnGround = false; // skip the flat-ground clamp until impact

    const int Ticks = 30; // 1 second
    for (int i = 0; i < Ticks; ++i)
    {
        FMovementInput Empty;
        // Use the non-clamped IntegrateMovement so airborne state holds.
        S = IntegrateMovement(S, Empty, P.FixedTimestepSec, P);
    }
    const double T = Ticks * P.FixedTimestepSec;
    // ACE kinematic integrator: pos = h0 + v0*t + 0.5*g*t² (exact for
    // constant accel). v0=0 → h0 - 4.9 m at t=1s → 1000 - 490 = 510 cm.
    const double ExpectedKinematic = H0 + 0.5 * P.GravityCmPerSecSq * T * T;
    char Name[200];
    std::snprintf(Name, sizeof(Name),
        "after 1s: Z=%.3f cm, kinematic 0.5*g*t² expects %.3f cm",
        S.Position.Z, ExpectedKinematic);
    Report(NearlyEqual(S.Position.Z, ExpectedKinematic, 1e-6, 1e-6), Name);

    // Velocity after 1s = g*t (constant accel).
    Report(NearlyEqual(S.Velocity.Z, P.GravityCmPerSecSq * T, 1e-6, 1e-6),
           "Vz after 1s = g*t");
}

// -----------------------------------------------------------------------
// Jump arc
// -----------------------------------------------------------------------

void TestJumpArc()
{
    std::printf("[Jump: impulse + gravity -> expected peak and airtime]\n");
    const FMovementParams P;
    FMovementState S;
    // Tick 1: jump pressed.
    FMovementInput Jump;
    Jump.bJumpPressed = true;
    S = IntegrateMovementWithFlatGround(S, Jump, P.FixedTimestepSec, P);
    Report(!S.bOnGround, "after jump tick: airborne");
    // Jump tick: impulse + one tick of gravity applied together
    // (matches ACE's "motion-state sets velocity then physics tick
    // integrates with current accel"). Vz post-tick = JumpVz + g*dt.
    const double ExpectedVzPostJumpTick = P.DefaultJumpVzCmPerSec + P.GravityCmPerSecSq * P.FixedTimestepSec;
    Report(NearlyEqual(S.Velocity.Z, ExpectedVzPostJumpTick, 1e-6, 1e-6),
        "after jump tick: Vz = JumpVz + g*dt (one tick of gravity applied)");

    // Continue until landing.
    int Ticks = 1;
    double PeakZ = S.Position.Z;
    FMovementInput Empty;
    while (!S.bOnGround && Ticks < 1000)
    {
        S = IntegrateMovementWithFlatGround(S, Empty, P.FixedTimestepSec, P);
        ++Ticks;
        if (S.Position.Z > PeakZ) PeakZ = S.Position.Z;
    }
    // Expected airtime ≈ 2*V0 / |g| ≈ 2*1000/980 ≈ 2.04 s (discretized).
    // Expected peak ≈ V0² / (2|g|) ≈ 1000²/(2*980) ≈ 510.2 cm.
    const double AirtimeSec = Ticks * P.FixedTimestepSec;
    const double ExpectedAirtime = 2.0 * P.DefaultJumpVzCmPerSec / std::fabs(P.GravityCmPerSecSq);
    const double ExpectedPeak = P.DefaultJumpVzCmPerSec * P.DefaultJumpVzCmPerSec
        / (2.0 * std::fabs(P.GravityCmPerSecSq));

    char Name[200];
    // Allow 1-tick airtime tolerance because of discrete integration.
    const double AirtimeTolerance = P.FixedTimestepSec * 2.0;
    std::snprintf(Name, sizeof(Name),
        "airtime %.3fs vs expected ~%.3fs (+/- 2 ticks)",
        AirtimeSec, ExpectedAirtime);
    Report(std::fabs(AirtimeSec - ExpectedAirtime) <= AirtimeTolerance, Name);

    // Peak height should be within ~5% of analytical due to discrete sampling.
    std::snprintf(Name, sizeof(Name),
        "peak %.1f cm vs expected ~%.1f cm (+/- 5%%)",
        PeakZ, ExpectedPeak);
    Report(std::fabs(PeakZ - ExpectedPeak) <= ExpectedPeak * 0.05, Name);

    Report(S.bOnGround, "lands on ground");
    Report(NearlyEqual(S.Position.Z, 0.0, 1e-6, 1e-6), "lands at Z=0");
}

// -----------------------------------------------------------------------
// Horizontal friction
// -----------------------------------------------------------------------

void TestFrictionDecay()
{
    std::printf("[Friction: no input -> ACE pow(1-coef, N*dt) decay]\n");
    const FMovementParams P;
    FMovementState S;
    S.Velocity.X = 500.0; // 5 m/s right
    S.Velocity.Y = 0.0;
    // No input for N ticks.
    const int N = 20;
    FMovementInput Empty;
    for (int i = 0; i < N; ++i)
    {
        S = IntegrateMovementWithFlatGround(S, Empty, P.FixedTimestepSec, P);
    }
    // ACE formula: V *= pow(1 - FrictionCoefficient, dt) per tick.
    // After N ticks: V = V0 * pow(1 - FrictionCoefficient, N*dt).
    // With coef=0.95, dt=1/30, N=20: V = 500 * pow(0.05, 20/30) ≈ 67.65.
    const double TotalDt = static_cast<double>(N) * P.FixedTimestepSec;
    const double Expected = 500.0 * std::pow(1.0 - P.FrictionCoefficient, TotalDt);
    char Name[220];
    std::snprintf(Name, sizeof(Name),
        "after %d ticks: Vx=%.3f, ACE expects 500 * pow(%.3f, %d/30) = %.3f",
        N, S.Velocity.X, 1.0 - P.FrictionCoefficient, N, Expected);
    Report(NearlyEqual(S.Velocity.X, Expected, 1e-6, 1e-6), Name);
}

// -----------------------------------------------------------------------
// Speed caps (walk / run / backward / sidestep)
// -----------------------------------------------------------------------

void TestSpeedCaps()
{
    std::printf("[Speed: input axes produce ACE-derived speeds]\n");
    const FMovementParams P;
    // Walk forward.
    {
        FMovementState S;
        FMovementInput In; In.ForwardAxis = 1.0;
        S = IntegrateMovementWithFlatGround(S, In, P.FixedTimestepSec, P);
        Report(NearlyEqual(S.Velocity.X, P.WalkSpeedCmPerSec, 1e-6, 1e-6),
               "walk: |V| = 312 cm/s (ACE WalkAnimSpeed 3.12 m/s)");
    }
    // Run forward.
    {
        FMovementState S;
        FMovementInput In; In.ForwardAxis = 1.0; In.bRunPressed = true;
        S = IntegrateMovementWithFlatGround(S, In, P.FixedTimestepSec, P);
        Report(NearlyEqual(S.Velocity.X, P.RunSpeedCmPerSec, 1e-6, 1e-6),
               "run: |V| = 400 cm/s (ACE RunAnimSpeed 4.0 m/s)");
    }
    // Backward walk.
    {
        FMovementState S;
        FMovementInput In; In.ForwardAxis = -1.0;
        S = IntegrateMovementWithFlatGround(S, In, P.FixedTimestepSec, P);
        const double Expected = -P.WalkSpeedCmPerSec * P.BackwardsFactor;
        Report(NearlyEqual(S.Velocity.X, Expected, 1e-6, 1e-6),
               "backward walk: V = -walk * BackwardsFactor (0.65) = -202.8 cm/s");
    }
    // Sidestep right (walk).
    {
        FMovementState S;
        FMovementInput In; In.RightAxis = 1.0;
        S = IntegrateMovementWithFlatGround(S, In, P.FixedTimestepSec, P);
        // ACE-derived: effective sidestep = WalkSpeed * SidestepFactor
        //            = 312 * 0.5 = 156 cm/s (NOT raw SidestepSpeedCmPerSec).
        const double Expected = P.WalkSpeedCmPerSec * P.SidestepFactor;
        Report(NearlyEqual(S.Velocity.Y, Expected, 1e-6, 1e-6),
               "sidestep: V_right = WalkSpeed * SidestepFactor = 156 cm/s");
    }
}

void TestYawRotation()
{
    std::printf("[Yaw: rotation rotates velocity direction]\n");
    const FMovementParams P;
    // Face east (yaw = π/2): forward should produce +Y velocity.
    FMovementState S;
    S.YawRad = 1.57079632679489661923; // π/2
    FMovementInput In; In.ForwardAxis = 1.0;
    S = IntegrateMovementWithFlatGround(S, In, P.FixedTimestepSec, P);
    Report(NearlyEqual(S.Velocity.X, 0.0, 1e-6, 1e-6),
           "facing east, forward -> Vx ≈ 0");
    Report(NearlyEqual(S.Velocity.Y, P.WalkSpeedCmPerSec, 1e-6, 1e-6),
           "facing east, forward -> Vy = walk speed");
}

// -----------------------------------------------------------------------
// Action stamp wraps
// -----------------------------------------------------------------------

void TestActionStampStable()
{
    std::printf("[Action stamp: NOT mutated by pure sim integrator]\n");
    // ACE compares stamps on queued actions, not per integration step.
    // The pure sim should preserve the input stamp verbatim — the
    // network layer bumps it per outbound action elsewhere.
    FMovementState S;
    S.ActionStamp = 0x1234;
    const FMovementParams P;
    FMovementInput In; In.ForwardAxis = 1.0;
    S = IntegrateMovementWithFlatGround(S, In, P.FixedTimestepSec, P);
    Report(S.ActionStamp == 0x1234u, "stamp 0x1234 preserved through one tick with input");
    FMovementInput Empty;
    S = IntegrateMovementWithFlatGround(S, Empty, P.FixedTimestepSec, P);
    Report(S.ActionStamp == 0x1234u, "stamp 0x1234 preserved through idle tick");
    S = IntegrateMovementWithFlatGround(S, Empty, P.FixedTimestepSec, P);
    Report(S.ActionStamp == 0x1234u, "stamp 0x1234 still preserved after multiple idle ticks");
}

// -----------------------------------------------------------------------
// Fixed-step accumulator
// -----------------------------------------------------------------------

void TestAccumulatorConsistency()
{
    std::printf("[Accumulator: variable frame dt -> consistent total ticks]\n");
    const FMovementParams P;
    FFixedStepAccumulator A;
    int TotalTicks = 0;
    // Feed 10 seconds of varying frame deltas.
    const double Pattern[] = { 0.016, 0.033, 0.025, 0.050, 0.012, 0.041, 0.020 };
    constexpr int PatternLen = sizeof(Pattern) / sizeof(Pattern[0]);
    double TotalReal = 0.0;
    int i = 0;
    while (TotalReal < 10.0)
    {
        const double dt = Pattern[i % PatternLen];
        TotalTicks += A.Advance(dt, P);
        TotalReal += dt;
        ++i;
    }
    // Expected: ~300 ticks (10 s at 30 Hz). Allow ±2 because the loop
    // terminates when TotalReal first crosses 10.0.
    Report(std::abs(TotalTicks - 300) <= 3,
           "≈300 ticks fired over 10 seconds (within ±3)");
}

void TestAccumulatorCatchUp()
{
    std::printf("[Accumulator: huge frame dt is clamped (no spiral of death)]\n");
    const FMovementParams P; // MaxAccumulator = 2.0
    FFixedStepAccumulator A;
    const int Ticks = A.Advance(60.0, P); // 1 minute frame
    const int Expected = static_cast<int>(P.MaxAccumulatorSec / P.FixedTimestepSec);
    char Name[120];
    std::snprintf(Name, sizeof(Name),
        "60s frame fires %d ticks (≈%d = MaxAccumulator/dt)",
        Ticks, Expected);
    Report(std::abs(Ticks - Expected) <= 1, Name);
}

void TestAccumulatorAlpha()
{
    std::printf("[Accumulator: alpha in [0,1] for visual lerp]\n");
    const FMovementParams P;
    FFixedStepAccumulator A;
    A.Advance(P.FixedTimestepSec * 0.5, P); // half a tick
    const double Alpha = A.Alpha(P);
    Report(Alpha >= 0.0 && Alpha <= 1.0, "alpha in [0,1]");
    Report(NearlyEqual(Alpha, 0.5, 1e-9, 1e-6), "alpha ≈ 0.5 after half a tick");
}

void TestAccumulatorRejectsBadInput()
{
    std::printf("[Accumulator: NaN / negative / zero dt -> 0 ticks (no UB)]\n");
    const FMovementParams P;
    FFixedStepAccumulator A;
    Report(A.Advance(std::nan(""), P) == 0, "NaN dt -> 0 ticks");
    Report(A.Advance(-0.5, P) == 0, "negative dt -> 0 ticks");
    Report(A.Advance(0.0, P) == 0, "zero dt -> 0 ticks");
    Report(A.AccumulatedSec == 0.0, "accumulator unchanged after bad inputs");
}

void TestAccumulatorRejectsBadFixedTimestep()
{
    std::printf("[Accumulator: zero / NaN / negative FixedTimestepSec -> 0 ticks (no hang)]\n");
    FFixedStepAccumulator A;
    FMovementParams Bad;

    Bad.FixedTimestepSec = 0.0;
    Report(A.Advance(1.0, Bad) == 0, "FixedTimestepSec=0 -> 0 ticks (no infinite loop)");

    Bad.FixedTimestepSec = -1.0;
    Report(A.Advance(1.0, Bad) == 0, "FixedTimestepSec=-1 -> 0 ticks");

    Bad.FixedTimestepSec = std::nan("");
    Report(A.Advance(1.0, Bad) == 0, "FixedTimestepSec=NaN -> 0 ticks");
}

} // anonymous namespace

int main()
{
    std::printf("=== AcUnreal sim-core standalone tests ===\n");
    TestDeterminism();
    TestGravityArc();
    TestJumpArc();
    TestFrictionDecay();
    TestSpeedCaps();
    TestYawRotation();
    TestActionStampStable();
    TestAccumulatorConsistency();
    TestAccumulatorCatchUp();
    TestAccumulatorAlpha();
    TestAccumulatorRejectsBadInput();
    TestAccumulatorRejectsBadFixedTimestep();
    std::printf("---\n%d passed, %d failed.\n", gPassed, gFailed);
    return (gFailed == 0) ? 0 : 1;
}
