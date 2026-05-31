// =====================================================================
// AcAcademyGameMode.h
//
// The GameMode that the AcademyMap uses. Sets DefaultPawnClass to our
// AAcAcademyCharacter so hitting Play spawns a properly-CMC-equipped
// character at the PlayerStart instead of the engine's DefaultPawn
// (free-fly camera). Also leaves PlayerControllerClass at its default
// (APlayerController) for now — a future input-handler phase will
// likely subclass it to dispatch UI / interaction events.
// =====================================================================

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "AcAcademyGameMode.generated.h"

UCLASS()
class ACUNREAL_API AAcAcademyGameMode : public AGameModeBase
{
    GENERATED_BODY()

public:
    AAcAcademyGameMode();
};
