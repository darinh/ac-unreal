// =====================================================================
// AcFixedTimestep.cpp
//
// Accumulator pattern implementation. See header for the contract.
// =====================================================================
#include "SimCore/AcFixedTimestep.h"

#include <cmath>

namespace ac_sim {

int FFixedStepAccumulator::Advance(double FrameDeltaSec, const FMovementParams& Params)
{
    // Reject pathological inputs: NaN, negative dt, infinite dt.
    if (!(FrameDeltaSec > 0.0) || !(FrameDeltaSec == FrameDeltaSec))
    {
        return 0;
    }
    // Reject pathological params: non-positive fixed timestep would
    // make the loop below either spin forever (dt=0) or run backwards
    // (dt<0). Guard at the entrance.
    if (!(Params.FixedTimestepSec > 0.0) || !(Params.FixedTimestepSec == Params.FixedTimestepSec))
    {
        return 0;
    }

    AccumulatedSec += FrameDeltaSec;

    // Spiral-of-death guard: if too much real time has accumulated
    // (long stall, debugger pause, OS sleep), drop the excess rather
    // than try to replay hours of sim. ACE calls this catch-up cap
    // HugeQuantum; we use the same default.
    if (AccumulatedSec > Params.MaxAccumulatorSec)
    {
        AccumulatedSec = Params.MaxAccumulatorSec;
    }

    int Ticks = 0;
    while (AccumulatedSec >= Params.FixedTimestepSec)
    {
        AccumulatedSec -= Params.FixedTimestepSec;
        ++Ticks;
    }
    return Ticks;
}

double FFixedStepAccumulator::Alpha(const FMovementParams& Params) const
{
    if (Params.FixedTimestepSec <= 0.0) return 0.0;
    const double A = AccumulatedSec / Params.FixedTimestepSec;
    if (A < 0.0) return 0.0;
    if (A > 1.0) return 1.0;
    return A;
}

} // namespace ac_sim
