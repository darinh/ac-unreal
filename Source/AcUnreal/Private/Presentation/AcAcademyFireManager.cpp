// =====================================================================
// AcAcademyFireManager.cpp — see header for rationale.
// =====================================================================

#include "Presentation/AcAcademyFireManager.h"

#include "Components/PointLightComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Math/UnrealMathUtility.h"

AAcAcademyFireManager::AAcAcademyFireManager()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PostUpdateWork;
}

void AAcAcademyFireManager::BeginPlay()
{
    Super::BeginPlay();

    Sources.Reset();
    if (UWorld* W = GetWorld())
    {
        for (TActorIterator<AActor> It(W); It; ++It)
        {
            AActor* A = *It;
            if (!A || !A->ActorHasTag(FireTag)) continue;
            UPointLightComponent* PL = A->FindComponentByClass<UPointLightComponent>();
            if (!PL) continue;

            FAcFlickerSource S;
            S.Light = PL;
            S.BaseIntensity = PL->Intensity;
            S.PhaseOffset = FMath::FRandRange(0.0f, 1000.0f);
            Sources.Add(S);
        }
    }
    UE_LOG(LogTemp, Display, TEXT("AcAcademyFireManager: tracking %d flicker sources"),
            Sources.Num());

    ElapsedSeconds = 0.0f;
}

void AAcAcademyFireManager::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bEnabled || Sources.Num() == 0) return;

    ElapsedSeconds += DeltaSeconds;

    for (const FAcFlickerSource& S : Sources)
    {
        if (!S.Light || S.BaseIntensity <= 0.0f) continue;

        const float T = ElapsedSeconds + S.PhaseOffset;
        const float Sine = FMath::Sin(2.0f * PI * SineHz * T);
        const float Noise = FMath::PerlinNoise1D(NoiseHz * T);
        const float Combined = 0.5f * Sine + 0.5f * Noise;   // [-1, 1]

        const float NewIntensity = S.BaseIntensity * (1.0f + FlickerAmplitude * Combined);
        S.Light->SetIntensity(NewIntensity);
    }
}
