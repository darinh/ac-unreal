// =====================================================================
// AcFixedTimestep.h
//
// The accumulator pattern that decouples our fixed-timestep simulation
// from UE's variable render frame. Same idea as Glenn Fiedler's "Fix
// Your Timestep" — accumulate real time, fire sim ticks at a fixed dt,
// expose an interpolation alpha for the visual layer to smooth between
// the last and current sim states.
//
// Pure C++17, no UE deps. The UE subsystem (UAcSimulationSubsystem)
// owns one of these and calls Advance() from its UE Tick().
//
// **Determinism note:** the accumulator is stateful (it has the
// remaining-time field), so it's NOT itself a deterministic input. The
// determinism property is "given the SAME sequence of (frameDelta)
// values, the SAME sequence of sim ticks fires." That holds.
// =====================================================================
#pragma once

#include "SimCore/AcSimTypes.h"

namespace ac_sim {

struct FFixedStepAccumulator
{
    double AccumulatedSec = 0.0;

    // Advance the accumulator by FrameDeltaSec. Returns the number of
    // fixed-dt sim ticks that should fire this frame. The accumulator
    // is clamped at MaxAccumulatorSec to prevent the "spiral of death"
    // (a long pause shouldn't try to replay hours of sim).
    int Advance(double FrameDeltaSec, const FMovementParams& Params);

    // Interpolation alpha in [0, 1] for visual smoothing between the
    // previous and current sim state. Render lerps:
    //   visual = lerp(prevSimState, currSimState, Alpha())
    // Caller passes the same Params used in Advance() to compute the
    // same denominator.
    double Alpha(const FMovementParams& Params) const;
};

} // namespace ac_sim
