// =====================================================================
// AcAcademyCharacter.cpp — see header for rationale.
// =====================================================================

#include "Player/AcAcademyCharacter.h"

#include "Camera/CameraComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/SpringArmComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"

#include "SimCore/AcCharacterMovementComponent.h"
#include "SimCore/AcMovementParamsDataAsset.h"


AAcAcademyCharacter::AAcAcademyCharacter(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer
        // Swap the stock CMC for our subclass at construction time.
        .SetDefaultSubobjectClass<UAcCharacterMovementComponent>(
            ACharacter::CharacterMovementComponentName))
{
    PrimaryActorTick.bCanEverTick = true;

    // Default capsule sizing — typical UE Character defaults are fine
    // for a humanoid in an indoor dungeon. Refine when the real AC
    // body mesh is wired in (Phase 5j follow-up).
    GetCapsuleComponent()->InitCapsuleSize(42.0f, 88.0f);

    // Controller rotates the character on yaw input. Pitch only
    // affects the camera (no head-tilt on the body).
    bUseControllerRotationPitch = false;
    bUseControllerRotationYaw   = true;
    bUseControllerRotationRoll  = false;

    // Spring arm: pulls the camera back behind+above the character.
    SpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("SpringArm"));
    SpringArm->SetupAttachment(RootComponent);
    SpringArm->TargetArmLength = 400.0f;                  // ~4 m
    SpringArm->SocketOffset    = FVector(0.0f, 0.0f, 50.0f);
    SpringArm->bUsePawnControlRotation = true;            // mouse rotates the arm
    SpringArm->bDoCollisionTest        = true;            // pulls in when wall behind

    // Camera at the end of the spring arm.
    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
    Camera->SetupAttachment(SpringArm, USpringArmComponent::SocketName);
    Camera->bUsePawnControlRotation = false;              // arm already does it

    // Reasonable CMC defaults; these get overwritten from MovementParams.
    if (UCharacterMovementComponent* CMC = GetCharacterMovement())
    {
        CMC->bOrientRotationToMovement   = false;        // facing controlled by yaw
        CMC->JumpZVelocity               = 600.0f;
        CMC->AirControl                  = 0.35f;
        CMC->MaxWalkSpeed                = 500.0f;
        CMC->MinAnalogWalkSpeed          = 20.0f;
        CMC->BrakingDecelerationWalking  = 2000.0f;
    }
}


void AAcAcademyCharacter::BeginPlay()
{
    Super::BeginPlay();

    // Push our Movement Params asset into the CMC so feel values
    // (gravity, friction, walk speed) come from the data asset rather
    // than the C++ defaults above.
    if (DefaultMovementParams != nullptr)
    {
        if (UAcCharacterMovementComponent* AcCmc =
                Cast<UAcCharacterMovementComponent>(GetCharacterMovement()))
        {
            AcCmc->SetMovementParams(DefaultMovementParams);
        }
        else
        {
            UE_LOG(LogTemp, Warning,
                TEXT("AcAcademyCharacter: GetCharacterMovement is not UAcCharacterMovementComponent; "
                     "MovementParams will not be applied."));
        }
    }
}


void AAcAcademyCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    check(PlayerInputComponent != nullptr);

    // Movement axes — bound to axis mappings declared in Config/DefaultInput.ini.
    PlayerInputComponent->BindAxis(TEXT("MoveForward"), this, &AAcAcademyCharacter::OnMoveForward);
    PlayerInputComponent->BindAxis(TEXT("MoveRight"),   this, &AAcAcademyCharacter::OnMoveRight);
    // Mouse yaw/pitch — per-frame deltas, not scaled by DeltaSeconds.
    PlayerInputComponent->BindAxis(TEXT("Turn"),        this, &AAcAcademyCharacter::OnTurn);
    PlayerInputComponent->BindAxis(TEXT("LookUp"),      this, &AAcAcademyCharacter::OnLookUp);
    // Keyboard arrows / gamepad sticks — held rates, scaled by DeltaSeconds
    // inside the handler so turn speed is frame-rate independent.
    PlayerInputComponent->BindAxis(TEXT("TurnRate"),    this, &AAcAcademyCharacter::OnTurnRate);
    PlayerInputComponent->BindAxis(TEXT("LookUpRate"),  this, &AAcAcademyCharacter::OnLookUpRate);

    // Jump — straight-through to ACharacter's built-in handlers.
    PlayerInputComponent->BindAction(TEXT("Jump"), IE_Pressed,  this, &ACharacter::Jump);
    PlayerInputComponent->BindAction(TEXT("Jump"), IE_Released, this, &ACharacter::StopJumping);
}


void AAcAcademyCharacter::OnMoveForward(float Value)
{
    if (Controller == nullptr || FMath::IsNearlyZero(Value)) return;
    // Project the controller's forward onto the horizontal plane so
    // we move along the floor, not up/down with the camera pitch.
    const FRotator Yaw(0.0f, Controller->GetControlRotation().Yaw, 0.0f);
    const FVector Forward = FRotationMatrix(Yaw).GetUnitAxis(EAxis::X);
    AddMovementInput(Forward, Value);
}


void AAcAcademyCharacter::OnMoveRight(float Value)
{
    if (Controller == nullptr || FMath::IsNearlyZero(Value)) return;
    const FRotator Yaw(0.0f, Controller->GetControlRotation().Yaw, 0.0f);
    const FVector Right = FRotationMatrix(Yaw).GetUnitAxis(EAxis::Y);
    AddMovementInput(Right, Value);
}


void AAcAcademyCharacter::OnTurn(float Value)
{
    // Mouse delta — already per-frame, do NOT multiply by DeltaSeconds.
    if (FMath::IsNearlyZero(Value)) return;
    AddControllerYawInput(Value * LookSensitivity);
}


void AAcAcademyCharacter::OnLookUp(float Value)
{
    // Mouse delta — already per-frame, do NOT multiply by DeltaSeconds.
    if (FMath::IsNearlyZero(Value)) return;
    AddControllerPitchInput(Value * LookSensitivity);
}


void AAcAcademyCharacter::OnTurnRate(float Value)
{
    // Held rate from arrow keys / gamepad stick — scale by DeltaSeconds
    // so turn speed is frame-rate independent.
    if (FMath::IsNearlyZero(Value)) return;
    const UWorld* W = GetWorld();
    const float Dt = W ? W->GetDeltaSeconds() : 0.0f;
    AddControllerYawInput(Value * TurnRateDegPerSec * Dt);
}


void AAcAcademyCharacter::OnLookUpRate(float Value)
{
    if (FMath::IsNearlyZero(Value)) return;
    const UWorld* W = GetWorld();
    const float Dt = W ? W->GetDeltaSeconds() : 0.0f;
    AddControllerPitchInput(Value * LookUpRateDegPerSec * Dt);
}
