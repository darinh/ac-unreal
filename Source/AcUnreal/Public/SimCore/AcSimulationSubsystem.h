// =====================================================================
// AcSimulationSubsystem.h
//
// UWorldSubsystem that owns the fixed-timestep accumulator and drives
// the per-character sim ticks. Phase 2 scaffold — provides the
// fixed-step Tick path that decouples movement integration from UE's
// variable render frame.
//
// **Brief invariant: fixed-timestep simulation loop decoupled from
// rendering, with interpolation for the visual layer.** This subsystem
// is where that decoupling happens. UE calls our Tick at render rate;
// we advance the accumulator and fire N sim ticks (often 0 or 1, may
// be 2+ on slow frames).
//
// What this scaffold does:
//   - Owns one ac_sim::FFixedStepAccumulator + ac_sim::FMovementParams
//     (sourced from a `DefaultMovementParams` DataAsset if set; else
//     ACE defaults).
//   - Per UE Tick: advances the accumulator and broadcasts an
//     OnSimTick delegate N times. Subscribers (e.g. an
//     UAcCharacterMovementComponent or a future network sender) run
//     their per-tick math from this delegate.
//   - Exposes the alpha [0..1] for the visual layer to interpolate
//     between the previous and current sim state.
//
// What is NOT in this scaffold:
//   - Auto-subscription of CMCs (they'd register themselves in Phase
//     2.x once we override PhysWalking).
//   - Networking. Out of brief scope.
//   - World partition / partial-tick scheduling. Single world, one
//     accumulator.
// =====================================================================
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"

#include "SimCore/AcSimTypes.h"
#include "SimCore/AcFixedTimestep.h"

#include "AcSimulationSubsystem.generated.h"

class UAcMovementParamsDataAsset;

DECLARE_MULTICAST_DELEGATE_OneParam(FAcOnSimTick, double /* DeltaSec */);

UCLASS(DisplayName="AC Simulation Subsystem")
class ACUNREAL_API UAcSimulationSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()
public:

	// --- Subsystem lifecycle ------------------------------------------

	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	// --- Tickable ------------------------------------------------------

	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UAcSimulationSubsystem, STATGROUP_Tickables); }
	virtual bool IsTickable() const override { return true; }

	// --- Public API ----------------------------------------------------

	// Replace the active movement params. Subsequent ticks use the new
	// FixedTimestep / MaxAccumulator immediately.
	UFUNCTION(BlueprintCallable, Category="AC|Sim")
	void SetMovementParams(UAcMovementParamsDataAsset* InParams);

	// Visual-interpolation alpha. Renderers should lerp(prev, curr,
	// GetInterpAlpha()) between sim states for smooth visuals at
	// arbitrary render rate.
	UFUNCTION(BlueprintPure, Category="AC|Sim")
	double GetInterpAlpha() const;

	// How many sim ticks the most recent UE Tick fired. Useful for
	// debug HUDs; 0 most frames at high FPS, 1 typically, higher on
	// slow frames.
	UFUNCTION(BlueprintPure, Category="AC|Sim")
	int32 GetLastTickCount() const { return LastTickCount; }

	// Total sim ticks fired since subsystem init. Monotonic; useful as
	// a free-running sim clock.
	UFUNCTION(BlueprintPure, Category="AC|Sim")
	int64 GetTotalSimTicks() const { return TotalSimTicks; }

	// Native delegate: bind from C++ to run per-sim-tick work. Fires
	// N times per UE Tick (N = ticks the accumulator advanced).
	FAcOnSimTick OnSimTick;

protected:

	UPROPERTY()
	TObjectPtr<UAcMovementParamsDataAsset> MovementParams = nullptr;

	ac_sim::FFixedStepAccumulator Accumulator;
	ac_sim::FMovementParams       CachedParams;
	int32                         LastTickCount  = 0;
	int64                         TotalSimTicks  = 0;

	// Refresh CachedParams from MovementParams (or defaults if null).
	void RefreshCachedParams();
};
