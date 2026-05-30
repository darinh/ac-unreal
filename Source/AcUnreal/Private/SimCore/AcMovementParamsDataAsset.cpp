#include "SimCore/AcMovementParamsDataAsset.h"

#if WITH_EDITOR
void UAcMovementParamsDataAsset::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	Super::PostEditChangeProperty(PropertyChangedEvent);
	OnParamsChanged.Broadcast();
}
#endif

ac_sim::FMovementParams UAcMovementParamsDataAsset::ToCoreParams() const
{
	ac_sim::FMovementParams P;
	P.FixedTimestepSec            = FixedTimestepSec;
	P.MaxAccumulatorSec           = MaxAccumulatorSec;
	P.GravityCmPerSecSq           = GravityCmPerSecSq;
	P.WalkSpeedCmPerSec           = WalkSpeedCmPerSec;
	P.RunSpeedCmPerSec            = RunSpeedCmPerSec;
	P.SidestepSpeedCmPerSec       = SidestepSpeedCmPerSec;
	P.BackwardsFactor             = BackwardsFactor;
	P.SidestepFactor              = SidestepFactor;
	P.RunTurnFactor               = RunTurnFactor;
	P.FrictionCoefficient         = FrictionCoefficient;
	P.TurnRateRadPerSec           = TurnRateRadPerSec;
	P.DefaultJumpVzCmPerSec       = DefaultJumpVzCmPerSec;
	P.StepHeightCm                = StepHeightCm;
	P.WalkableSlopeCosine         = WalkableSlopeCosine;
	P.ServerCorrectionThresholdCm = ServerCorrectionThresholdCm;
	return P;
}
