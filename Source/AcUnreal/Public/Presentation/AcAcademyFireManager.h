// =====================================================================
// AcAcademyFireManager.h
//
// Phase 5h: drives the flicker animation for every "FireFlicker"-tagged
// actor in the level. Single actor, scans the world on BeginPlay,
// caches references, animates intensities on Tick.
//
// Cleaner than a per-light component because:
//   1) one Python call places one actor.
//   2) one Tick iterates a flat array — better cache + we can stagger
//      individual phases.
//   3) trivially toggleable via a single bEnabled property.
//
// Note: presentation-only. Not part of the simulation lane.
// =====================================================================

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AcAcademyFireManager.generated.h"

class UPointLightComponent;

USTRUCT()
struct FAcFlickerSource
{
    GENERATED_BODY()

    UPROPERTY()
    UPointLightComponent* Light = nullptr;

    UPROPERTY()
    float BaseIntensity = 0.0f;

    UPROPERTY()
    float PhaseOffset = 0.0f;
};

UCLASS()
class ACUNREAL_API AAcAcademyFireManager : public AActor
{
    GENERATED_BODY()

public:
    AAcAcademyFireManager();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker")
    bool bEnabled = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float FlickerAmplitude = 0.30f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker", meta = (ClampMin = "0.1"))
    float SineHz = 3.5f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker", meta = (ClampMin = "0.1"))
    float NoiseHz = 14.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flicker")
    FName FireTag = FName(TEXT("FireFlicker"));

    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;

private:
    UPROPERTY()
    TArray<FAcFlickerSource> Sources;

    float ElapsedSeconds = 0.0f;
};
