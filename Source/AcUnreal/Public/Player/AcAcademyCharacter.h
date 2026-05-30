// =====================================================================
// AcAcademyCharacter.h
//
// The default player Pawn for the academy slice. An ACharacter
// subclass that:
//   1) Uses UAcCharacterMovementComponent as its CMC (drop-in
//      replacement for the stock UCharacterMovementComponent — set
//      via SetDefaultSubobjectClass in the constructor).
//   2) Provides a third-person camera via USpringArmComponent +
//      UCameraComponent so you can see the academy interior around
//      you while walking.
//   3) Implements legacy BindAxis input wiring so WASD + mouse +
//      space "just work" against UE5's input system. (Project also
//      enables EnhancedInput; this character intentionally uses the
//      simpler axis-binding API so input works without authored
//      IA_/IMC_ uassets — that's a follow-up if/when the project
//      needs context-switching, modifier keys, etc.)
//
// Note: this is presentation-side movement. The simulation-parity
// lane lives in UAcCharacterMovementComponent / ac_sim::IntegrateMovement.
// =====================================================================

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "AcAcademyCharacter.generated.h"

class USpringArmComponent;
class UCameraComponent;
class UAcMovementParamsDataAsset;

UCLASS()
class ACUNREAL_API AAcAcademyCharacter : public ACharacter
{
    GENERATED_BODY()

public:
    AAcAcademyCharacter(const FObjectInitializer& ObjectInitializer);

    /** Third-person camera boom. Owned by RootComponent (the capsule). */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Camera")
    USpringArmComponent* SpringArm = nullptr;

    /** Third-person camera at the end of the boom. */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Camera")
    UCameraComponent* Camera = nullptr;

    /** Optional Movement Params data asset; if set, fed to our CMC at BeginPlay. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Sim")
    TObjectPtr<UAcMovementParamsDataAsset> DefaultMovementParams = nullptr;

    /** Mouse look sensitivity scalar (deg per mouse-delta unit) — tune to taste. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Input", meta=(ClampMin="0.01"))
    float LookSensitivity = 1.0f;

    /**
     * Turn rate in degrees-per-second for the "rate" axes (arrow keys,
     * gamepad stick). Multiplied by DeltaSeconds so turn speed is
     * frame-rate independent. NOT applied to MouseX/Y — those are
     * already per-frame deltas and don't need scaling.
     */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Input", meta=(ClampMin="1.0"))
    float TurnRateDegPerSec = 120.0f;

    /** Same as TurnRateDegPerSec but for pitch (LookUp). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Input", meta=(ClampMin="1.0"))
    float LookUpRateDegPerSec = 90.0f;

protected:
    virtual void BeginPlay() override;
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

    // ---- Legacy axis handlers --------------------------------------
    void OnMoveForward(float Value);
    void OnMoveRight(float Value);
    /** Mouse yaw (per-frame delta; no DeltaSeconds scaling). */
    void OnTurn(float Value);
    /** Mouse pitch (per-frame delta; no DeltaSeconds scaling). */
    void OnLookUp(float Value);
    /** Keyboard / gamepad yaw (held rate, in [-1,1]; scaled by DeltaSeconds). */
    void OnTurnRate(float Value);
    /** Keyboard / gamepad pitch (held rate, in [-1,1]; scaled by DeltaSeconds). */
    void OnLookUpRate(float Value);
    // (Jump is bound directly to ACharacter::Jump / StopJumping.)
};
