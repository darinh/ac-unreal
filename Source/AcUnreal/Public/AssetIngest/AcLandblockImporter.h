// =====================================================================
// AcLandblockImporter.h
//
// UE-side Blueprint wrapper around the pure C++ .aclb parser in
// AssetIngest/AcIntermediateLandblock.h. ALL parsing is delegated to
// the pure core; this file is a boundary, not a re-implementation.
// =====================================================================
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"

#include "AssetIngest/AcIntermediateLandblock.h"

#include "AcLandblockImporter.generated.h"

// ---------------------------------------------------------------------
// UENUM mirror of ac_ingest::EAcLbParseStatus. Kept in sync via the
// converter below; static_asserts on the enum count would help but
// UENUM doesn't expose a count macro, so add new values in BOTH places
// when extending.
// ---------------------------------------------------------------------
UENUM(BlueprintType)
enum class EAcLbParseStatusBP : uint8
{
	OK                       UMETA(DisplayName="OK"),
	BufferTooSmall           UMETA(DisplayName="Buffer Too Small"),
	BadMagic                 UMETA(DisplayName="Bad Magic"),
	UnsupportedVersion       UMETA(DisplayName="Unsupported Version"),
	InvalidSamplesPerSide    UMETA(DisplayName="Invalid Samples Per Side"),
	InvalidTextureLayerCount UMETA(DisplayName="Invalid Texture Layer Count"),
	NonzeroFlagsReserved     UMETA(DisplayName="Nonzero Flags Reserved"),
	NonzeroReservedField     UMETA(DisplayName="Nonzero Reserved Field"),
	SizeMismatch             UMETA(DisplayName="Size Mismatch"),
	NonFiniteHeight          UMETA(DisplayName="Non-Finite Height"),
	InvalidLandblockId       UMETA(DisplayName="Invalid Landblock ID"),
	FileNotFound             UMETA(DisplayName="File Not Found")   // UE-only; the core has no I/O
};

// ---------------------------------------------------------------------
// Header struct (Blueprint-visible).
// ---------------------------------------------------------------------
USTRUCT(BlueprintType)
struct FAcIntermediateLandblockHeaderBP
{
	GENERATED_BODY()

	// Mirrors ac_ingest::FAcIntermediateLandblockHeader. Fields stored
	// as int64 for LandblockId (Blueprint has no uint32; int64 holds
	// the full unsigned range without losing the high bit).
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="AC|AssetIngest")
	int64 LandblockId = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="AC|AssetIngest")
	int32 SamplesPerSide = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="AC|AssetIngest")
	int32 TextureLayerCount = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="AC|AssetIngest")
	int32 FormatVersion = 0;
};

// ---------------------------------------------------------------------
// Parsed landblock (Blueprint-visible).
// ---------------------------------------------------------------------
USTRUCT(BlueprintType)
struct FAcIntermediateLandblockBP
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="AC|AssetIngest")
	FAcIntermediateLandblockHeaderBP Header;

	// size = SamplesPerSide * SamplesPerSide. Row-major (Y outer).
	// Units: metres in the AC world frame.
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="AC|AssetIngest")
	TArray<float> Heights;

	// size = SamplesPerSide * SamplesPerSide * TextureLayerCount.
	// Layers contiguous: layer 0 first, then layer 1, etc.
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="AC|AssetIngest")
	TArray<uint8> TextureIndices;
};

UCLASS()
class ACUNREAL_API UAcLandblockImporter : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:

	// Load a .aclb file from disk and parse it. On parse failure
	// (including missing file, bad format, NaN heights), returns the
	// specific status code; OutLandblock is left default-constructed.
	UFUNCTION(BlueprintCallable, Category="AC|AssetIngest",
		meta=(DisplayName="Load Landblock From File"))
	static EAcLbParseStatusBP LoadLandblockFromFile(const FString& FilePath,
	                                                FAcIntermediateLandblockBP& OutLandblock);

	// Parse a buffer already loaded into memory. Useful if the caller
	// pulled bytes from somewhere other than disk (e.g. a packed PAK
	// or a network stream during decompile-handoff testing).
	UFUNCTION(BlueprintCallable, Category="AC|AssetIngest",
		meta=(DisplayName="Parse Landblock Bytes"))
	static EAcLbParseStatusBP ParseLandblockBytes(const TArray<uint8>& Bytes,
	                                              FAcIntermediateLandblockBP& OutLandblock);

	// Pure-C++ converters (NOT exposed to BP). Other C++ in this
	// module may use them to go between layers without re-implementing
	// the field mapping.
	static EAcLbParseStatusBP StatusToBP(ac_ingest::EAcLbParseStatus Core);
	static FAcIntermediateLandblockBP CoreToBP(const ac_ingest::FAcIntermediateLandblock& Core);
};
