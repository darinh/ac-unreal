// =====================================================================
// AcMovementParamsDataAsset.h
//
// UDataAsset wrapping the pure C++ ac_sim::FMovementParams so designers
// can tune feel values from the editor without recompile. Defaults
// match the ACE-derived constants from
// contract/decompile-artifacts/physics-feel-spec-response.md.
//
// Brief invariant: feel parameters live in DATA, not in code. This
// file is the data-binding for that invariant.
// =====================================================================
#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"

#include "SimCore/AcSimTypes.h"

#include "AcMovementParamsDataAsset.generated.h"

UCLASS(BlueprintType)
class ACUNREAL_API UAcMovementParamsDataAsset : public UDataAsset
{
	GENERATED_BODY()
public:

	// Fired whenever a property on this DataAsset is edited (editor) or
	// after a programmatic UpdateAndNotify(). Subscribers (the CMC,
	// the simulation subsystem) refresh their cached params on this
	// signal so designer tuning takes effect mid-PIE without a restart.
	DECLARE_MULTICAST_DELEGATE(FAcOnMovementParamsChanged);
	FAcOnMovementParamsChanged OnParamsChanged;

	// Trigger OnParamsChanged after programmatic mutation (the editor
	// PostEditChangeProperty path fires it automatically).
	UFUNCTION(BlueprintCallable, Category="AC|Sim")
	void NotifyParamsChanged() { OnParamsChanged.Broadcast(); }

#if WITH_EDITOR
	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
#endif

	// --- §1 timestep ---------------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Timestep", meta=(ClampMin="0.001"))
	double FixedTimestepSec = 1.0 / 30.0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Timestep", meta=(ClampMin="0.001"))
	double MaxAccumulatorSec = 2.0;

	// --- §2 gravity ----------------------------------------------------

	// Negative = downward. ACE PhysicsGlobals.cs:13 → -9.8 m/s² → -980 cm/s².
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Gravity")
	double GravityCmPerSecSq = -980.0;

	// --- §3 ground locomotion (ACE MotionInterp.cs:26-31) -------------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Locomotion", meta=(ClampMin="0.0"))
	double WalkSpeedCmPerSec = 312.0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Locomotion", meta=(ClampMin="0.0"))
	double RunSpeedCmPerSec = 400.0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Locomotion", meta=(ClampMin="0.0"))
	double SidestepSpeedCmPerSec = 125.0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Locomotion", meta=(ClampMin="0.0", ClampMax="1.0"))
	double BackwardsFactor = 0.65;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Locomotion", meta=(ClampMin="0.0", ClampMax="1.0"))
	double SidestepFactor = 0.5;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Locomotion", meta=(ClampMin="0.0"))
	double RunTurnFactor = 1.5;

	// ACE friction coefficient. The per-tick scalar applied to velocity
	// is pow(1 - FrictionCoefficient, dt), NOT FrictionCoefficient
	// itself. ACE PhysicsObj.cs:2139. With 0.95 and dt=1/30, the
	// per-30Hz multiplier is pow(0.05, 1/30) ≈ 0.9046.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Locomotion", meta=(ClampMin="0.0", ClampMax="0.99"))
	double FrictionCoefficient = 0.95;

	// PLACEHOLDER — see spec response §3 "Turn rate UNKNOWN".
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Locomotion", meta=(ClampMin="0.0"))
	double TurnRateRadPerSec = 3.14159265358979323846;

	// --- §4 jumping ---------------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Jump", meta=(ClampMin="0.0"))
	double DefaultJumpVzCmPerSec = 1000.0;

	// --- §5 collision -------------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Collision", meta=(ClampMin="0.0"))
	double StepHeightCm = 1.0;

	// Min walkable normal.Z. ACE PhysicsGlobals.FloorZ = 0.66417... =
	// cos(48.41°). Do NOT confuse with PhysicsGlobals.LandingZ (sin(5°))
	// which is a collision tolerance, not a slope threshold.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Collision", meta=(ClampMin="0.0", ClampMax="1.0"))
	double WalkableSlopeCosine = 0.66417414618662751;

	// --- §10 reconciliation -------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim|Reconciliation", meta=(ClampMin="0.0"))
	double ServerCorrectionThresholdCm = 5.0;

	// Convert this UDataAsset into the pure C++ FMovementParams the sim
	// core consumes. Single chokepoint so the field mapping lives in
	// one place; if you add a field to FMovementParams, mirror it here
	// AND extend ToCoreParams().
	ac_sim::FMovementParams ToCoreParams() const;
};
