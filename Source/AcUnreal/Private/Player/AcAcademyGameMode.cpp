// =====================================================================
// AcAcademyGameMode.cpp — see header.
// =====================================================================

#include "Player/AcAcademyGameMode.h"

#include "Player/AcAcademyCharacter.h"
#include "UObject/ConstructorHelpers.h"


AAcAcademyGameMode::AAcAcademyGameMode()
{
    DefaultPawnClass = AAcAcademyCharacter::StaticClass();
    // PlayerControllerClass left at APlayerController default; we don't
    // need a custom one until input handling needs to dispatch to UI
    // (chat box, hotbar, vitals) — future phase.
}
