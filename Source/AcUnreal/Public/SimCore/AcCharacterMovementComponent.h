// =====================================================================
// AcCharacterMovementComponent.h
//
// Custom UCharacterMovementComponent subclass for Phase 2.
//
// **Brief invariant: do not ship stock CharacterMovementComponent as
// the feel model.** We subclass CMC so we inherit its move-history /
// replication scaffolding (the seam for future server-authoritative
// reconciliation against ACE), but we replace the per-tick movement
// math with the pure-C++ ac_sim core when InitializeComponent fires.
//
// What this scaffold does in Phase 2:
//   - Holds a pointer to a UAcMovementParamsDataAsset (the data-driven
//     feel values; defaults to ACE constants).
//   - On InitializeComponent, syncs CMC's tunable properties
//     (MaxWalkSpeed, JumpZVelocity, GravityScale, GroundFriction, etc.)
//     from the DataAsset so they at least *report* the ACE numbers.
//   - Exposes RunSimTick() that runs one pure-C++ ac_sim integration
//     step. Future Phase 2.x will route CMC's PhysWalking / PhysFalling
//     through this; the scaffold leaves the stock physics in place
//     because a full integration with UE's swept-collision floor-find
//     is non-trivial and gated on a working level + collider setup we
//     don't have yet.
//
// What is NOT in this scaffold:
//   - Override of PhysWalking / PhysFalling / PhysFlying. Documented
//     TODO at the top of those functions.
//   - Server-authoritative reconciliation against ACE position
//     corrections. Out of brief scope ("Out of scope: the network /
//     protocol client"). The seam for it is RunSimTick (deterministic,
//     re-simulatable) + the future IAcPositionUpdateSink.
// =====================================================================
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/CharacterMovementComponent.h"

#include "SimCore/AcSimTypes.h"

#include "AcCharacterMovementComponent.generated.h"

class UAcMovementParamsDataAsset;

UCLASS(ClassGroup=(AC), meta=(BlueprintSpawnableComponent),
       DisplayName="AC Character Movement Component")
class ACUNREAL_API UAcCharacterMovementComponent : public UCharacterMovementComponent
{
	GENERATED_BODY()
public:

	UAcCharacterMovementComponent(const FObjectInitializer& ObjectInitializer);

	// The data-driven feel parameters. Assign in the Blueprint (or via
	// SetMovementParams). If null at InitializeComponent time we fall
	// back to ac_sim::DefaultMovementParams() (ACE defaults).
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim")
	TObjectPtr<UAcMovementParamsDataAsset> MovementParams = nullptr;

	// Replace the DataAsset at runtime. Re-applies the parameters to
	// the stock CMC properties (MaxWalkSpeed, etc.). Useful for
	// switching weenie templates at runtime.
	UFUNCTION(BlueprintCallable, Category="AC|Sim")
	void SetMovementParams(UAcMovementParamsDataAsset* InParams);

protected:

	virtual void InitializeComponent() override;
	virtual void UninitializeComponent() override;

	// Pull the C++ params, with fallback to defaults.
	ac_sim::FMovementParams GetCoreParams() const;

	// Push the DataAsset's values into the stock CMC tunables. So
	// even before we override PhysWalking, MaxWalkSpeed etc. report the
	// ACE-derived numbers.
	void ApplyParamsToStockProperties(const ac_sim::FMovementParams& Core);

	// Handler bound to MovementParams->OnParamsChanged so designer
	// edits in the editor propagate to live CMC instances immediately.
	void HandleParamsChanged();

	// Subscribe/unsubscribe lifecycle for the OnParamsChanged delegate.
	void BindToParamsAsset();
	void UnbindFromParamsAsset();

	FDelegateHandle ParamsChangedHandle;

	// The persistent per-tick sim state for this character. Lives
	// alongside CMC's own state; future override of PhysWalking will
	// keep them in sync.
	ac_sim::FMovementState SimState;

public:

	// Run one pure-C++ ac_sim::IntegrateMovement step from the current
	// CMC state + the given input + dt. Returns the new sim state.
	// This is the seam that the (future) PhysWalking / PhysFalling
	// overrides AND the (future) network reconciliation handler will
	// share. Pure-C++ inside, no UE-collision interaction.
	//
	// Caller is responsible for writing the resulting Position/Velocity
	// back to UE if they want the visible character to move. The
	// scaffold's RunSimTick does NOT do that — it's verification of the
	// sim-core path under UE compilation, not a movement implementation.
	UFUNCTION(BlueprintCallable, Category="AC|Sim")
	void RunSimTickDebug(float DeltaSec,
	                     float InForwardAxis,
	                     float InRightAxis,
	                     float InTurnAxis,
	                     bool  bInRunPressed,
	                     bool  bInJumpPressed,
	                     FVector& OutNewPositionCm,
	                     FVector& OutNewVelocityCmPerSec,
	                     bool& bOutOnGround,
	                     int32& OutActionStamp);
};
