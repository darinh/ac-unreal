// =====================================================================
// CoordTransform.cpp
//
// Implementation of the canonical AC <-> UE coordinate transform.
// See CoordTransform.h for design rationale and constraints.
// =====================================================================
#include "CoordCore/CoordTransform.h"

namespace ac_coord {

namespace {

// Centimetres per metre. The UE convention. Not configurable; UE's
// "1 unit = 1 cm" is hard-baked into the engine.
constexpr double kUeCmPerMeter = 100.0;

// Forward-declared helpers operate in pure-axis space (no unit scaling).
// Splitting "axis remap" from "unit scaling" makes round-trip easier to
// reason about: each step is its own invertible operation.

inline void AcAxesToUeAxesMeters(double AcX, double AcY, double AcZ,
                                 const FAcWorldConventions& Conv,
                                 double& OutUeXm, double& OutUeYm, double& OutUeZm)
{
    // Axis remap stage. Inputs are AC coordinates in metres; outputs are
    // UE-axis coordinates still in metres. Unit scaling happens in the
    // caller.
    //
    // The XY swap below is an odd permutation (det = -1). For the
    // expected real-world case (AC right-handed Z-up: X=east, Y=north,
    // Z=up), this swap produces a left-handed UE basis — which is
    // correct, because UE's world is left-handed. The chirality flip
    // happens HERE, intentionally, via the swap. We do NOT add a
    // separate mirror on top (an earlier draft did; it was wrong
    // because the swap already produces the chirality UE expects).
    //
    // Consequence for asset import: anything with baked-in handedness
    // (mesh winding, normals, quat rotations) needs the matching flip
    // at the ASSET layer. The coord transform's job is to convert
    // coordinates; the asset pipeline's job is to convert geometry
    // representations. Don't conflate the two.
    if (Conv.bMapAcNorthToUeForward)
    {
        // AC.X (east)  -> UE.Y (right)
        // AC.Y (north) -> UE.X (forward)
        OutUeXm = AcY;
        OutUeYm = AcX;
    }
    else
    {
        // 1:1 mapping. Used when the spec confirms AC already uses
        // UE-style X-forward/Y-right (unlikely in practice).
        OutUeXm = AcX;
        OutUeYm = AcY;
    }
    OutUeZm = AcZ;

    // AcHandedness is informational; the transform does not branch on it.
    (void)Conv.AcHandedness;
}

inline void UeAxesToAcAxesMeters(double UeXm, double UeYm, double UeZm,
                                 const FAcWorldConventions& Conv,
                                 double& OutAcX, double& OutAcY, double& OutAcZ)
{
    // Exact inverse of AcAxesToUeAxesMeters — undo the swap. No mirror
    // to undo.
    if (Conv.bMapAcNorthToUeForward)
    {
        // UE.X (forward) <- AC.Y (north)
        // UE.Y (right)   <- AC.X (east)
        OutAcY = UeXm;
        OutAcX = UeYm;
    }
    else
    {
        OutAcX = UeXm;
        OutAcY = UeYm;
    }
    OutAcZ = UeZm;
    (void)Conv.AcHandedness;
}

// Returns true if the given conventions are usable by the landblock
// functions (positive, finite scale factors). Point/vector transforms
// don't need this guard — IEEE 754 propagation of NaN/Inf through
// floating-point arithmetic is well-defined and gives the caller the
// information that something is wrong. The landblock functions DO need
// the guard because they cast doubles to integer indices, and casting
// NaN or out-of-range doubles to unsigned integers is undefined
// behavior per C++17 [conv.fpint]/1.
inline bool AreConventionsLandblockSafe(const FAcWorldConventions& Conv)
{
    // (x > 0) is false for x == NaN, x == 0, x < 0 — so this single
    // check rules out all the bad cases.
    return (Conv.AcUnitMeters > 0.0) && (Conv.LandblockSideMeters > 0.0);
}

} // anonymous namespace

// ---------------------------------------------------------------------

double AcUnitToUeCentimeters(const FAcWorldConventions& Conv)
{
    return Conv.AcUnitMeters * kUeCmPerMeter;
}

FUeVec3 AcPointToUe(const FAcVec3& AcPoint, const FAcWorldConventions& Conv)
{
    // AC stored value -> metres
    const double AcXm = AcPoint.X * Conv.AcUnitMeters;
    const double AcYm = AcPoint.Y * Conv.AcUnitMeters;
    const double AcZm = AcPoint.Z * Conv.AcUnitMeters;

    double UeXm = 0.0, UeYm = 0.0, UeZm = 0.0;
    AcAxesToUeAxesMeters(AcXm, AcYm, AcZm, Conv, UeXm, UeYm, UeZm);

    FUeVec3 Out;
    Out.X = UeXm * kUeCmPerMeter;
    Out.Y = UeYm * kUeCmPerMeter;
    Out.Z = UeZm * kUeCmPerMeter;
    return Out;
}

FAcVec3 UePointToAc(const FUeVec3& UePoint, const FAcWorldConventions& Conv)
{
    // UE cm -> metres
    const double UeXm = UePoint.X / kUeCmPerMeter;
    const double UeYm = UePoint.Y / kUeCmPerMeter;
    const double UeZm = UePoint.Z / kUeCmPerMeter;

    double AcXm = 0.0, AcYm = 0.0, AcZm = 0.0;
    UeAxesToAcAxesMeters(UeXm, UeYm, UeZm, Conv, AcXm, AcYm, AcZm);

    // metres -> AC stored value
    FAcVec3 Out;
    Out.X = AcXm / Conv.AcUnitMeters;
    Out.Y = AcYm / Conv.AcUnitMeters;
    Out.Z = AcZm / Conv.AcUnitMeters;
    return Out;
}

FUeVec3 AcVectorToUe(const FAcVec3& AcVector, const FAcWorldConventions& Conv)
{
    // Vectors are translation-free; same axis/scale math as points,
    // because the conversion has no translation component (the AC and
    // UE origins are coincident by convention).
    return AcPointToUe(AcVector, Conv);
}

FAcVec3 UeVectorToAc(const FUeVec3& UeVector, const FAcWorldConventions& Conv)
{
    return UePointToAc(UeVector, Conv);
}

// ---------------------------------------------------------------------
// Landblock addressing
// ---------------------------------------------------------------------

bool IsAcPointInsideWorld(const FAcVec3& AcPoint, const FAcWorldConventions& Conv)
{
    if (!AreConventionsLandblockSafe(Conv)) { return false; }
    const double Xm = AcPoint.X * Conv.AcUnitMeters;
    const double Ym = AcPoint.Y * Conv.AcUnitMeters;
    // NaN propagates: NaN >= 0.0 is false, so NaN-in returns false.
    const double WorldExtentM = static_cast<double>(Conv.LandblockGridCount) * Conv.LandblockSideMeters;
    return (Xm >= 0.0) && (Xm < WorldExtentM)
        && (Ym >= 0.0) && (Ym < WorldExtentM);
}

FAcLandblockId LandblockIdForAcPoint(const FAcVec3& AcPoint, const FAcWorldConventions& Conv)
{
    // Safe-zero on invalid conventions. Casting NaN or out-of-range
    // doubles to unsigned int is UB per C++17 [conv.fpint]/1; this
    // guard plus the NaN check in ClampedIndex below is the defense.
    if (!AreConventionsLandblockSafe(Conv))
    {
        return EncodeLandblockId(0, 0);
    }

    const double Xm = AcPoint.X * Conv.AcUnitMeters;
    const double Ym = AcPoint.Y * Conv.AcUnitMeters;

    // The encoding uses 8 bits per axis; 0xFF is reserved. Even if the
    // spec gives LandblockGridCount > 255 (which would be wrong per
    // community sources), we must not emit an ID we can't encode.
    constexpr std::uint32_t kEncodableMax = 0xFEu;
    const std::uint32_t SpecMax = (Conv.LandblockGridCount > 0)
        ? (Conv.LandblockGridCount - 1) : 0u;
    const std::uint32_t MaxIdx = (SpecMax < kEncodableMax) ? SpecMax : kEncodableMax;

    auto ClampedIndex = [&](double Coord) -> std::uint32_t
    {
        // NaN guard: NaN fails ALL comparisons. Without this, NaN
        // would fall through both guards and hit the cast below,
        // which is UB.
        if (!(Coord == Coord)) { return 0u; }
        if (Coord < 0.0) { return 0u; }
        const double Idx = Coord / Conv.LandblockSideMeters;
        // (Idx >= MaxIdx) is false for NaN (already filtered) and
        // for +Inf is true so we cap. For finite values in range,
        // the static_cast is well-defined.
        if (Idx >= static_cast<double>(MaxIdx)) { return MaxIdx; }
        return static_cast<std::uint32_t>(Idx);
    };

    const std::uint32_t LbX = ClampedIndex(Xm);
    const std::uint32_t LbY = ClampedIndex(Ym);
    return EncodeLandblockId(static_cast<std::uint8_t>(LbX),
                             static_cast<std::uint8_t>(LbY));
}

FAcVec3 AcOriginOfLandblock(FAcLandblockId LandblockId, const FAcWorldConventions& Conv)
{
    if (!AreConventionsLandblockSafe(Conv))
    {
        return FAcVec3{ 0.0, 0.0, 0.0 };
    }

    std::uint8_t LbX = 0;
    std::uint8_t LbY = 0;
    DecomposeLandblockId(LandblockId, LbX, LbY);

    FAcVec3 Out;
    // Returned in AC stored units (not metres). Divide metres by AcUnitMeters.
    Out.X = (static_cast<double>(LbX) * Conv.LandblockSideMeters) / Conv.AcUnitMeters;
    Out.Y = (static_cast<double>(LbY) * Conv.LandblockSideMeters) / Conv.AcUnitMeters;
    Out.Z = 0.0;
    return Out;
}

void DecomposeLandblockId(FAcLandblockId LandblockId,
                          std::uint8_t& OutLandblockX,
                          std::uint8_t& OutLandblockY)
{
    OutLandblockX = static_cast<std::uint8_t>((LandblockId >> 24) & 0xFFu);
    OutLandblockY = static_cast<std::uint8_t>((LandblockId >> 16) & 0xFFu);
}

FAcLandblockId EncodeLandblockId(std::uint8_t LandblockX, std::uint8_t LandblockY)
{
    return (static_cast<FAcLandblockId>(LandblockX) << 24)
         | (static_cast<FAcLandblockId>(LandblockY) << 16);
}

} // namespace ac_coord
