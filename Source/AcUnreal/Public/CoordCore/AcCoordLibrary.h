// =====================================================================
// AcCoordLibrary.h
//
// UE-side Blueprint-callable wrapper around the pure C++ coordinate
// transform in CoordCore/CoordTransform.h.
//
// Design constraint: ZERO math lives here. Every function is a thin
// adapter: convert UE types (FVector, FAcWorldConventionsBP) to/from
// the ac_coord types, call the core function, return. The wrapper is a
// boundary, not a re-implementation. If you find yourself doing
// arithmetic in this file, you are working in the wrong layer.
// =====================================================================
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"

#include "CoordCore/CoordTransform.h"

#include "AcCoordLibrary.generated.h"

// ---------------------------------------------------------------------
// FAcWorldConventionsBP — Blueprint-visible mirror of
// ac_coord::FAcWorldConventions. Stays in sync with the pure C++ struct
// via the explicit converters below; if you add a field to the core
// struct, add it here and update FromBP / ToBP.
// ---------------------------------------------------------------------
USTRUCT(BlueprintType)
struct FAcWorldConventionsBP
{
	GENERATED_BODY()

	// PLACEHOLDER (spec): informational only — the transform itself is
	// chirality-preserving (no mirror). See CoordTransform.h.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Coord")
	bool bAcRightHanded = true;

	// PLACEHOLDER (spec): metres per AC linear unit (default 1.0).
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Coord", meta=(ClampMin="0.0001"))
	double AcUnitMeters = 1.0;

	// PLACEHOLDER (spec): physical landblock side length in metres.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Coord", meta=(ClampMin="0.0001"))
	double LandblockSideMeters = 192.0;

	// PLACEHOLDER (spec): landblock grid count per axis.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Coord", meta=(ClampMin="1"))
	int32 LandblockGridCount = 255;

	// PLACEHOLDER (spec): if true, AC.X(east) -> UE.Y(right) and
	// AC.Y(north) -> UE.X(forward).
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AC|Coord")
	bool bMapAcNorthToUeForward = true;
};

UCLASS()
class ACUNREAL_API UAcCoordLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:

	// --- Point and vector transforms ---------------------------------

	UFUNCTION(BlueprintPure, Category="AC|Coord", meta=(DisplayName="AC Point -> UE Point"))
	static FVector AcPointToUe(const FVector& AcPoint, const FAcWorldConventionsBP& Conv);

	UFUNCTION(BlueprintPure, Category="AC|Coord", meta=(DisplayName="UE Point -> AC Point"))
	static FVector UePointToAc(const FVector& UePoint, const FAcWorldConventionsBP& Conv);

	UFUNCTION(BlueprintPure, Category="AC|Coord", meta=(DisplayName="AC Vector -> UE Vector"))
	static FVector AcVectorToUe(const FVector& AcVector, const FAcWorldConventionsBP& Conv);

	UFUNCTION(BlueprintPure, Category="AC|Coord", meta=(DisplayName="UE Vector -> AC Vector"))
	static FVector UeVectorToAc(const FVector& UeVector, const FAcWorldConventionsBP& Conv);

	// --- Landblock addressing ----------------------------------------

	// Returns the landblock ID for the given AC point. Note: returned as
	// int32 because Blueprints have no uint32 type; the low 16 bits of
	// the ID are always 0 (no intra-landblock cell info), and the high
	// 16 bits encode the (X, Y) grid indices.
	UFUNCTION(BlueprintPure, Category="AC|Coord")
	static int32 LandblockIdForAcPoint(const FVector& AcPoint, const FAcWorldConventionsBP& Conv);

	UFUNCTION(BlueprintPure, Category="AC|Coord")
	static FVector AcOriginOfLandblock(int32 LandblockId, const FAcWorldConventionsBP& Conv);

	UFUNCTION(BlueprintPure, Category="AC|Coord")
	static bool IsAcPointInsideWorld(const FVector& AcPoint, const FAcWorldConventionsBP& Conv);

	// --- Diagnostics --------------------------------------------------

	UFUNCTION(BlueprintPure, Category="AC|Coord")
	static double AcUnitToUeCentimeters(const FAcWorldConventionsBP& Conv);

	// --- Convention conversion (exposed for tooling/tests) -----------

	// Pure C++ helper, NOT exposed to Blueprint. Lives here so UE
	// callers in this module can convert without re-implementing the
	// mapping in each call site.
	static ac_coord::FAcWorldConventions FromBP(const FAcWorldConventionsBP& BP);
	static FAcWorldConventionsBP        ToBP(const ac_coord::FAcWorldConventions& Core);
};
