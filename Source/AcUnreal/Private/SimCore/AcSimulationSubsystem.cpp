#include "SimCore/AcSimulationSubsystem.h"

#include "SimCore/AcMovementParamsDataAsset.h"

void UAcSimulationSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	RefreshCachedParams();
	Accumulator.AccumulatedSec = 0.0;
	LastTickCount = 0;
	TotalSimTicks = 0;
}

void UAcSimulationSubsystem::Deinitialize()
{
	OnSimTick.Clear();
	Super::Deinitialize();
}

void UAcSimulationSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (DeltaTime <= 0.0f) { LastTickCount = 0; return; }

	const int Ticks = Accumulator.Advance(static_cast<double>(DeltaTime), CachedParams);
	LastTickCount = Ticks;
	if (Ticks <= 0) return;

	const double TickDt = CachedParams.FixedTimestepSec;
	for (int i = 0; i < Ticks; ++i)
	{
		// Broadcast in order. Subscribers run their pure-C++ sim step
		// from this delegate (deterministic; same dt every tick).
		OnSimTick.Broadcast(TickDt);
		++TotalSimTicks;
	}
}

void UAcSimulationSubsystem::SetMovementParams(UAcMovementParamsDataAsset* InParams)
{
	MovementParams = InParams;
	RefreshCachedParams();
}

double UAcSimulationSubsystem::GetInterpAlpha() const
{
	return Accumulator.Alpha(CachedParams);
}

void UAcSimulationSubsystem::RefreshCachedParams()
{
	if (MovementParams)
	{
		CachedParams = MovementParams->ToCoreParams();
	}
	else
	{
		CachedParams = ac_sim::DefaultMovementParams();
	}
}
