// =====================================================================
// CoordTransform.h
//
// Canonical AC <-> UE coordinate / unit / landblock transform.
//
// >>> THIS IS THE ONE PLACE COORD CONVERSION LIVES IN THIS REPO. <<<
// No other module is allowed to hand-roll a transform. If you find
// yourself multiplying by 100 to convert meters to centimetres, you are
// doing it wrong; call this module.
//
// Scope: OUTDOOR / landblock-grid coordinates only. Dungeon/interior
// coordinate spaces in AC are a separate domain (different cell ID
// encoding, different origin model, different portal-transition rules)
// and are NOT handled here. Indoor support is a known Phase 1/2
// requirement and is requested in §0b of
// contract/physics-feel-spec-request.md.
//
// Design rules:
//  * Pure C++17. No UE headers, no STL containers in the interface, no
//    exceptions. This file MUST compile both as part of the AcUnreal
//    UE module AND as part of the standalone test rig built by
//    pipeline/coord-transform/build.ps1.
//  * All world-shaping numbers (handedness, unit length, landblock
//    extent, grid count) live in FAcWorldConventions, NOT as hard-coded
//    literals in functions. Every default value is PLACEHOLDER until
//    confirmed by the decompile agent (see contract/physics-feel-spec-request.md
//    §0).
//  * Round-trip identity holds for any consistent choice of conventions:
//        AcPointToUe(UePointToAc(p)) == p
//        UePointToAc(AcPointToUe(p)) == p
//    (within floating-point epsilon). Tests in
//    pipeline/coord-transform/tests/ prove this.
//  * The landblock encoding (8-bit X, 8-bit Y) constrains
//    LandblockGridCount to <= 255 (0xFF is reserved per AC convention).
//    Public landblock functions cap their output to the encodable
//    range; conventions with LandblockGridCount > 255 are still
//    accepted but silently clamped.
//  * Invalid inputs (NaN, +/-Inf, non-positive LandblockSideMeters /
//    AcUnitMeters) do not produce undefined behavior. Landblock
//    functions return a safe zero ID on invalid conventions; point/
//    vector transforms propagate NaN/Inf arithmetically as the IEEE
//    754 default.
// =====================================================================
#pragma once

#include <cstdint>

namespace ac_coord {

// ---------------------------------------------------------------------
// Plain-data vector types used by the core. They are intentionally
// distinct so the type system catches "I used an AC point in a UE
// context" mistakes at compile time. The UE wrapper in
// AcCoordSubsystem.h converts to/from FVector at the boundary.
// ---------------------------------------------------------------------

struct FAcVec3
{
    double X = 0.0;   // In AC world units (default: metres). Axis meaning
    double Y = 0.0;   // is governed by FAcWorldConventions.
    double Z = 0.0;
};

struct FUeVec3
{
    double X = 0.0;   // Centimetres, UE convention (X = forward,
    double Y = 0.0;   // Y = right, Z = up, left-handed).
    double Z = 0.0;
};

// Landblock IDs in AC are 32-bit:
//   high byte  (bits 24..31): landblock X grid index
//   next byte  (bits 16..23): landblock Y grid index
//   low 16 bits             : intra-landblock cell / object ID (not used
//                             by coord transform; preserved as 0 here).
// The X/Y bit layout above matches the dominant community (ACEmulator)
// convention. PLACEHOLDER (spec): confirm in §0 of the spec request.
using FAcLandblockId = std::uint32_t;

// ---------------------------------------------------------------------
// AC handedness enum. AC is widely *believed* to be right-handed Z-up
// in client storage, with X=east, Y=north. Decompile must confirm.
// ---------------------------------------------------------------------
enum class EAcHandedness : std::uint8_t
{
    RightHanded = 0,  // PLACEHOLDER (spec): default assumption
    LeftHanded  = 1
};

// FAcWorldConventions — the data the transform reads from.
// Every value here is PLACEHOLDER (spec) until ratified by §0 of
// contract/physics-feel-spec-request.md. Round-trip tests prove
// invertibility for ANY consistent choice; absolute correctness against
// the real client requires these to be right.
//
// On handedness: AcHandedness is INFORMATIONAL only — it documents what
// the spec claims AC uses. The transform itself does NOT branch on it;
// chirality is determined by whether bMapAcNorthToUeForward is set
// (the XY swap is an odd permutation, det = -1, so it flips chirality).
//
// For the expected real-world case — AC is right-handed Z-up
// (X=east, Y=north, Z=up) — the default conventions (RightHanded +
// swap=true) produce a left-handed UE basis. That is correct: UE's
// world coordinate system is left-handed, so the chirality flip is
// the right one to apply. An earlier draft of this module ADDITIONALLY
// mirrored Y "to force left-handed UE output", which was wrong because
// the swap already does that — adding a mirror would either double-
// flip (back to right-handed) or no-op depending on convention combo.
//
// What this means for asset import (Phase 1+): because the coord
// transform IS chirality-flipping in the default case, anything pulled
// through this transform that has handedness baked into its data (mesh
// triangle winding, normal direction, joint orientation in skeletons,
// rotation/quaternion conventions) MUST be handled at the asset
// pipeline. A mesh imported via this transform without a winding flip
// will render with inside-out faces; an animation track imported
// without a quaternion remap will play mirrored.
struct FAcWorldConventions
{
    EAcHandedness AcHandedness = EAcHandedness::RightHanded; // PLACEHOLDER (spec); informational

    // How long, in metres, one AC linear unit is. If AC stores positions
    // directly in metres this is 1.0. MUST be > 0; landblock functions
    // return safe zero output on non-positive or NaN values.
    double AcUnitMeters = 1.0;                               // PLACEHOLDER (spec)

    // Physical side length of one landblock, in metres. Community
    // sources cite 192 m; needs spec confirmation. MUST be > 0; landblock
    // functions return safe zero output on non-positive or NaN values.
    double LandblockSideMeters = 192.0;                      // PLACEHOLDER (spec)

    // Grid count per axis. Community sources cite 255 (0x00..0xFE
    // usable; 0xFF reserved). Values > 255 are silently clamped to 255
    // by landblock functions because the ID encoding only fits 8 bits
    // per axis. PLACEHOLDER (spec): confirm.
    std::uint32_t LandblockGridCount = 255;                  // PLACEHOLDER (spec)

    // How AC's X and Y compass meaning maps to UE's forward/right.
    // Default: AC.X=east -> UE.Y=right; AC.Y=north -> UE.X=forward.
    // The swap is an odd permutation (det = -1), so flipping this flag
    // flips the chirality of the output basis. PLACEHOLDER (spec).
    bool bMapAcNorthToUeForward = true;
};

// Sane default — pure function, no globals. Pass this around explicitly
// so tests can vary it.
constexpr FAcWorldConventions DefaultAcWorldConventions() { return {}; }

// ---------------------------------------------------------------------
// Point transforms (positions: translation + scale + axis remap).
// ---------------------------------------------------------------------
FUeVec3 AcPointToUe(const FAcVec3& AcPoint,
                    const FAcWorldConventions& Conv);

FAcVec3 UePointToAc(const FUeVec3& UePoint,
                    const FAcWorldConventions& Conv);

// ---------------------------------------------------------------------
// Vector transforms (velocities, normals, deltas: scale + axis remap,
// NO translation). Implemented separately so we can't accidentally
// translate a velocity by adding a world origin.
// ---------------------------------------------------------------------
FUeVec3 AcVectorToUe(const FAcVec3& AcVector,
                     const FAcWorldConventions& Conv);

FAcVec3 UeVectorToAc(const FUeVec3& UeVector,
                     const FAcWorldConventions& Conv);

// ---------------------------------------------------------------------
// Landblock addressing.
//   * LandblockIdForAcPoint clamps to the grid; out-of-world points
//     resolve to the nearest border landblock. Callers that care about
//     out-of-world detection should check ahead of time using
//     IsAcPointInsideWorld().
//   * AcOriginOfLandblock returns the (minimum-X, minimum-Y, Z=0) corner
//     of the named landblock in AC world coordinates.
// ---------------------------------------------------------------------
bool IsAcPointInsideWorld(const FAcVec3& AcPoint,
                          const FAcWorldConventions& Conv);

FAcLandblockId LandblockIdForAcPoint(const FAcVec3& AcPoint,
                                     const FAcWorldConventions& Conv);

FAcVec3 AcOriginOfLandblock(FAcLandblockId LandblockId,
                            const FAcWorldConventions& Conv);

// Extracts (lbX, lbY) grid indices from an encoded ID. Low 16 bits are
// the intra-landblock cell/object ID; this function ignores them.
void DecomposeLandblockId(FAcLandblockId LandblockId,
                          std::uint8_t& OutLandblockX,
                          std::uint8_t& OutLandblockY);

FAcLandblockId EncodeLandblockId(std::uint8_t LandblockX,
                                 std::uint8_t LandblockY);

// ---------------------------------------------------------------------
// Convenience: convert an AC world unit (1 unit) into UE centimetres.
// Useful when configuring UE physics scales from AC data.
// ---------------------------------------------------------------------
double AcUnitToUeCentimeters(const FAcWorldConventions& Conv);

} // namespace ac_coord
