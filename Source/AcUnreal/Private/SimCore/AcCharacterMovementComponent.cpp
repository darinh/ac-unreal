#include "SimCore/AcCharacterMovementComponent.h"

#include "SimCore/AcMovementParamsDataAsset.h"
#include "SimCore/AcSimMath.h"

#include <cmath>

UAcCharacterMovementComponent::UAcCharacterMovementComponent(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	// Start with ACE defaults so a freshly-spawned component reports the
	// right numbers even if no DataAsset is assigned.
	const ac_sim::FMovementParams D = ac_sim::DefaultMovementParams();
	ApplyParamsToStockProperties(D);
}

void UAcCharacterMovementComponent::InitializeComponent()
{
	Super::InitializeComponent();
	BindToParamsAsset();
	const ac_sim::FMovementParams Core = GetCoreParams();
	ApplyParamsToStockProperties(Core);

	// Seed SimState from the actor's current location (post-spawn).
	if (AActor* Owner = GetOwner())
	{
		const FVector Pos = Owner->GetActorLocation();
		SimState.Position.X = Pos.X;
		SimState.Position.Y = Pos.Y;
		SimState.Position.Z = Pos.Z;
		SimState.Velocity   = {0.0, 0.0, 0.0};
		SimState.YawRad     = FMath::DegreesToRadians(Owner->GetActorRotation().Yaw);
		SimState.bOnGround  = true;
		SimState.ActionStamp = 0;
	}
}

void UAcCharacterMovementComponent::UninitializeComponent()
{
	UnbindFromParamsAsset();
	Super::UninitializeComponent();
}

void UAcCharacterMovementComponent::SetMovementParams(UAcMovementParamsDataAsset* InParams)
{
	UnbindFromParamsAsset();
	MovementParams = InParams;
	BindToParamsAsset();
	ApplyParamsToStockProperties(GetCoreParams());
}

void UAcCharacterMovementComponent::BindToParamsAsset()
{
	if (MovementParams && !ParamsChangedHandle.IsValid())
	{
		ParamsChangedHandle = MovementParams->OnParamsChanged.AddUObject(
			this, &UAcCharacterMovementComponent::HandleParamsChanged);
	}
}

void UAcCharacterMovementComponent::UnbindFromParamsAsset()
{
	if (MovementParams && ParamsChangedHandle.IsValid())
	{
		MovementParams->OnParamsChanged.Remove(ParamsChangedHandle);
	}
	ParamsChangedHandle.Reset();
}

void UAcCharacterMovementComponent::HandleParamsChanged()
{
	// Designer edited the DataAsset (PIE or runtime) — refresh stock
	// CMC properties from the new values so MaxWalkSpeed etc. reflect
	// the edit without a restart.
	ApplyParamsToStockProperties(GetCoreParams());
}

ac_sim::FMovementParams UAcCharacterMovementComponent::GetCoreParams() const
{
	if (MovementParams) return MovementParams->ToCoreParams();
	return ac_sim::DefaultMovementParams();
}

void UAcCharacterMovementComponent::ApplyParamsToStockProperties(const ac_sim::FMovementParams& Core)
{
	// Push the ACE-derived numbers into UE's stock CMC properties so
	// the editor / debug HUDs at least show the right values. The
	// FEEL is still UE's stock math until we override PhysWalking;
	// surface-area scaffold only.
	MaxWalkSpeed       = static_cast<float>(Core.RunSpeedCmPerSec);
	MaxAcceleration    = 99999.0f; // AC's motion-state model = instant target velocity
	JumpZVelocity      = static_cast<float>(Core.DefaultJumpVzCmPerSec);
	GravityScale       = static_cast<float>(std::fabs(Core.GravityCmPerSecSq) / 980.0); // UE gravity is -980; this is the scale factor
	GroundFriction     = 0.0f;     // we model friction in our own integrator, not CMC's
	BrakingDecelerationWalking = 0.0f; // ditto
	MaxStepHeight      = static_cast<float>(Core.StepHeightCm);
	// WalkableFloorZ is "cos of max slope angle". CMC's default is 0.71 (45°).
	SetWalkableFloorZ(static_cast<float>(Core.WalkableSlopeCosine));

	// TODO Phase 2.x: override PhysWalking / PhysFalling and route the
	// per-tick math through ac_sim::IntegrateMovement instead of CMC's
	// defaults. The DataAsset binding above is necessary but not yet
	// sufficient for "custom CMC" per the brief — the stock math still
	// runs underneath. See RunSimTickDebug for the seam.
}

void UAcCharacterMovementComponent::RunSimTickDebug(float DeltaSec,
                                                    float InForwardAxis,
                                                    float InRightAxis,
                                                    float InTurnAxis,
                                                    bool  bInRunPressed,
                                                    bool  bInJumpPressed,
                                                    FVector& OutNewPositionCm,
                                                    FVector& OutNewVelocityCmPerSec,
                                                    bool& bOutOnGround,
                                                    int32& OutActionStamp)
{
	ac_sim::FMovementInput In;
	In.ForwardAxis  = InForwardAxis;
	In.RightAxis    = InRightAxis;
	In.TurnAxis     = InTurnAxis;
	In.bRunPressed  = bInRunPressed;
	In.bJumpPressed = bInJumpPressed;

	const ac_sim::FMovementParams Core = GetCoreParams();
	SimState = ac_sim::IntegrateMovement(SimState, In, DeltaSec, Core);

	OutNewPositionCm       = FVector(SimState.Position.X, SimState.Position.Y, SimState.Position.Z);
	OutNewVelocityCmPerSec = FVector(SimState.Velocity.X, SimState.Velocity.Y, SimState.Velocity.Z);
	bOutOnGround           = SimState.bOnGround;
	OutActionStamp         = static_cast<int32>(SimState.ActionStamp);
}
