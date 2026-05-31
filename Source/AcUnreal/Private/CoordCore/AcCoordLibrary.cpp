// =====================================================================
// AcCoordLibrary.cpp
//
// Thin UE-side wrapper. ALL math is delegated to ac_coord:: in
// CoordCore/CoordTransform.{h,cpp}. This file is intentionally boring.
// =====================================================================
#include "CoordCore/AcCoordLibrary.h"

namespace
{
	// FVector in UE5 is double-precision via Large World Coordinates, so
	// these conversions are lossless. If UE ever flips back to float,
	// these are the single point we'd need to revisit.
	FORCEINLINE ac_coord::FAcVec3 AcVec3FromFVector(const FVector& V)
	{
		return { V.X, V.Y, V.Z };
	}

	FORCEINLINE ac_coord::FUeVec3 UeVec3FromFVector(const FVector& V)
	{
		return { V.X, V.Y, V.Z };
	}

	FORCEINLINE FVector FVectorFromAcVec3(const ac_coord::FAcVec3& V)
	{
		return FVector(V.X, V.Y, V.Z);
	}

	FORCEINLINE FVector FVectorFromUeVec3(const ac_coord::FUeVec3& V)
	{
		return FVector(V.X, V.Y, V.Z);
	}
}

ac_coord::FAcWorldConventions UAcCoordLibrary::FromBP(const FAcWorldConventionsBP& BP)
{
	ac_coord::FAcWorldConventions Out;
	Out.AcHandedness = BP.bAcRightHanded
		? ac_coord::EAcHandedness::RightHanded
		: ac_coord::EAcHandedness::LeftHanded;
	Out.AcUnitMeters           = BP.AcUnitMeters;
	Out.LandblockSideMeters    = BP.LandblockSideMeters;
	Out.LandblockGridCount     = static_cast<uint32>(FMath::Max(0, BP.LandblockGridCount));
	Out.bMapAcNorthToUeForward = BP.bMapAcNorthToUeForward;
	return Out;
}

FAcWorldConventionsBP UAcCoordLibrary::ToBP(const ac_coord::FAcWorldConventions& Core)
{
	FAcWorldConventionsBP Out;
	Out.bAcRightHanded         = (Core.AcHandedness == ac_coord::EAcHandedness::RightHanded);
	Out.AcUnitMeters           = Core.AcUnitMeters;
	Out.LandblockSideMeters    = Core.LandblockSideMeters;
	Out.LandblockGridCount     = static_cast<int32>(Core.LandblockGridCount);
	Out.bMapAcNorthToUeForward = Core.bMapAcNorthToUeForward;
	return Out;
}

FVector UAcCoordLibrary::AcPointToUe(const FVector& AcPoint, const FAcWorldConventionsBP& Conv)
{
	return FVectorFromUeVec3(
		ac_coord::AcPointToUe(AcVec3FromFVector(AcPoint), FromBP(Conv)));
}

FVector UAcCoordLibrary::UePointToAc(const FVector& UePoint, const FAcWorldConventionsBP& Conv)
{
	return FVectorFromAcVec3(
		ac_coord::UePointToAc(UeVec3FromFVector(UePoint), FromBP(Conv)));
}

FVector UAcCoordLibrary::AcVectorToUe(const FVector& AcVector, const FAcWorldConventionsBP& Conv)
{
	return FVectorFromUeVec3(
		ac_coord::AcVectorToUe(AcVec3FromFVector(AcVector), FromBP(Conv)));
}

FVector UAcCoordLibrary::UeVectorToAc(const FVector& UeVector, const FAcWorldConventionsBP& Conv)
{
	return FVectorFromAcVec3(
		ac_coord::UeVectorToAc(UeVec3FromFVector(UeVector), FromBP(Conv)));
}

int32 UAcCoordLibrary::LandblockIdForAcPoint(const FVector& AcPoint, const FAcWorldConventionsBP& Conv)
{
	const ac_coord::FAcLandblockId Id =
		ac_coord::LandblockIdForAcPoint(AcVec3FromFVector(AcPoint), FromBP(Conv));
	// Reinterpret as int32; high bit fits because lbX/lbY <= 0xFE.
	return static_cast<int32>(Id);
}

FVector UAcCoordLibrary::AcOriginOfLandblock(int32 LandblockId, const FAcWorldConventionsBP& Conv)
{
    // Validate the BP-supplied ID. Negative int32 would reinterpret to a
    // uint32 with the high byte set, which decomposes to a landblock
    // outside the encodable 0x00..0xFE grid — silently surprising.
    if (LandblockId < 0)
    {
        UE_LOG(LogTemp, Warning,
            TEXT("AcOriginOfLandblock: rejecting negative landblock id %d; returning origin."),
            LandblockId);
        return FVector::ZeroVector;
    }
    // Validate that lbX/lbY are within the spec's grid count (not just
    // within the 0xFE encoding limit). Out-of-grid ids are typically
    // a programming mistake at the call site.
    const uint32 RawId = static_cast<uint32>(LandblockId);
    const uint32 LbX = (RawId >> 24) & 0xFFu;
    const uint32 LbY = (RawId >> 16) & 0xFFu;
    const uint32 GridMax = static_cast<uint32>(FMath::Max(0, Conv.LandblockGridCount));
    if ((GridMax > 0) && ((LbX >= GridMax) || (LbY >= GridMax)))
    {
        UE_LOG(LogTemp, Warning,
            TEXT("AcOriginOfLandblock: landblock (%u,%u) outside grid count %u; returning origin."),
            LbX, LbY, GridMax);
        return FVector::ZeroVector;
    }
    const ac_coord::FAcLandblockId Id = static_cast<ac_coord::FAcLandblockId>(RawId);
    return FVectorFromAcVec3(ac_coord::AcOriginOfLandblock(Id, FromBP(Conv)));
}

bool UAcCoordLibrary::IsAcPointInsideWorld(const FVector& AcPoint, const FAcWorldConventionsBP& Conv)
{
	return ac_coord::IsAcPointInsideWorld(AcVec3FromFVector(AcPoint), FromBP(Conv));
}

double UAcCoordLibrary::AcUnitToUeCentimeters(const FAcWorldConventionsBP& Conv)
{
	return ac_coord::AcUnitToUeCentimeters(FromBP(Conv));
}
