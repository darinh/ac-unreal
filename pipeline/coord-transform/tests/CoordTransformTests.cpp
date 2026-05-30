// =====================================================================
// CoordTransformTests.cpp
//
// Standalone round-trip + invariant tests for the canonical AC <-> UE
// coordinate transform in Source/AcUnreal/{Public,Private}/CoordCore/.
//
// This file is compiled by pipeline/coord-transform/build.ps1 directly
// with cl.exe — NO UnrealBuildTool, NO UE headers. The whole point is
// to prove the core math is correct independently of the UE editor
// build, so a regression in the math fails fast.
//
// Same source files are also compiled into the UE module by UBT.
// =====================================================================

#include "CoordCore/CoordTransform.h"

#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <utility>

using namespace ac_coord;

namespace {

int gPassed = 0;
int gFailed = 0;

bool NearlyEqual(double A, double B, double Eps = 1e-9)
{
    const double D = std::fabs(A - B);
    if (D <= Eps) return true;
    // Relative epsilon for large magnitudes (landblock coords go up to ~49000 m).
    const double M = std::fmax(std::fabs(A), std::fabs(B));
    return D <= Eps * std::fmax(1.0, M);
}

bool NearlyEqual(const FAcVec3& A, const FAcVec3& B, double Eps = 1e-9)
{
    return NearlyEqual(A.X, B.X, Eps) && NearlyEqual(A.Y, B.Y, Eps) && NearlyEqual(A.Z, B.Z, Eps);
}

bool NearlyEqual(const FUeVec3& A, const FUeVec3& B, double Eps = 1e-9)
{
    return NearlyEqual(A.X, B.X, Eps) && NearlyEqual(A.Y, B.Y, Eps) && NearlyEqual(A.Z, B.Z, Eps);
}

void Report(bool Ok, const char* Name)
{
    if (Ok)
    {
        ++gPassed;
        std::printf("  PASS  %s\n", Name);
    }
    else
    {
        ++gFailed;
        std::printf("  FAIL  %s\n", Name);
    }
}

// All four legal combinations of (handedness, swap). Round-trip must
// hold for ALL of them; that property is what makes the transform safe
// to use before the decompile agent ratifies §0.
const FAcWorldConventions kConventionSet[] = {
    // RightHanded + swap (default; most likely real-world AC)
    [](){ FAcWorldConventions C; C.AcHandedness = EAcHandedness::RightHanded; C.bMapAcNorthToUeForward = true;  return C; }(),
    // RightHanded + no swap
    [](){ FAcWorldConventions C; C.AcHandedness = EAcHandedness::RightHanded; C.bMapAcNorthToUeForward = false; return C; }(),
    // LeftHanded + swap
    [](){ FAcWorldConventions C; C.AcHandedness = EAcHandedness::LeftHanded;  C.bMapAcNorthToUeForward = true;  return C; }(),
    // LeftHanded + no swap
    [](){ FAcWorldConventions C; C.AcHandedness = EAcHandedness::LeftHanded;  C.bMapAcNorthToUeForward = false; return C; }(),
};

const FAcVec3 kSamplePointsAc[] = {
    {  0.0,    0.0,    0.0 },
    {  1.0,    0.0,    0.0 },
    {  0.0,    1.0,    0.0 },
    {  0.0,    0.0,    1.0 },
    { 17.3,  -42.0,    9.5 },
    { -1.0,   -1.0,   -1.0 },
    { 12345.678, 9876.543, 100.25 },
    // Realistic landblock-scale coordinate (mid-world).
    { 24576.0, 24576.0, 75.0 },
};

void TestRoundTripPointsAllConventions()
{
    std::printf("[Round-trip POINTS across all 4 conventions]\n");
    for (size_t ci = 0; ci < sizeof(kConventionSet)/sizeof(kConventionSet[0]); ++ci)
    {
        const FAcWorldConventions& C = kConventionSet[ci];
        for (size_t pi = 0; pi < sizeof(kSamplePointsAc)/sizeof(kSamplePointsAc[0]); ++pi)
        {
            const FAcVec3 P = kSamplePointsAc[pi];
            const FUeVec3 U = AcPointToUe(P, C);
            const FAcVec3 Back = UePointToAc(U, C);
            char Name[128];
            std::snprintf(Name, sizeof(Name),
                "Ac->Ue->Ac conv#%zu pt#%zu (%.3g,%.3g,%.3g)",
                ci, pi, P.X, P.Y, P.Z);
            Report(NearlyEqual(P, Back), Name);
        }
    }
}

void TestRoundTripUePointsAllConventions()
{
    std::printf("[Round-trip UE POINTS across all 4 conventions]\n");
    const FUeVec3 kSamplePointsUe[] = {
        {     0.0,    0.0,    0.0 },
        {   100.0,    0.0,    0.0 },
        {     0.0,  100.0,    0.0 },
        {     0.0,    0.0,  100.0 },
        {  -500.0, 2500.0, 1234.5 },
        { 1234567.0, -890.0, 42.0 },
    };
    for (size_t ci = 0; ci < sizeof(kConventionSet)/sizeof(kConventionSet[0]); ++ci)
    {
        const FAcWorldConventions& C = kConventionSet[ci];
        for (size_t pi = 0; pi < sizeof(kSamplePointsUe)/sizeof(kSamplePointsUe[0]); ++pi)
        {
            const FUeVec3 P = kSamplePointsUe[pi];
            const FAcVec3 A = UePointToAc(P, C);
            const FUeVec3 Back = AcPointToUe(A, C);
            char Name[128];
            std::snprintf(Name, sizeof(Name),
                "Ue->Ac->Ue conv#%zu pt#%zu (%.3g,%.3g,%.3g)",
                ci, pi, P.X, P.Y, P.Z);
            Report(NearlyEqual(P, Back), Name);
        }
    }
}

void TestRoundTripVectors()
{
    std::printf("[Round-trip VECTORS (no translation component)]\n");
    for (size_t ci = 0; ci < sizeof(kConventionSet)/sizeof(kConventionSet[0]); ++ci)
    {
        const FAcWorldConventions& C = kConventionSet[ci];
        for (size_t pi = 0; pi < sizeof(kSamplePointsAc)/sizeof(kSamplePointsAc[0]); ++pi)
        {
            const FAcVec3 V = kSamplePointsAc[pi];
            const FUeVec3 U = AcVectorToUe(V, C);
            const FAcVec3 Back = UeVectorToAc(U, C);
            char Name[96];
            std::snprintf(Name, sizeof(Name), "Vec round-trip conv#%zu vec#%zu", ci, pi);
            Report(NearlyEqual(V, Back), Name);
        }
    }
}

void TestUnitScale()
{
    std::printf("[Unit scaling]\n");
    // Default convention: 1 AC unit = 1 m. UE = 100 cm. So 1 AC = 100 UE.
    FAcWorldConventions C; // defaults
    Report(NearlyEqual(AcUnitToUeCentimeters(C), 100.0), "default unit = 100 cm");

    // 1 m in AC.X under default conv (swap on) -> 100 cm in UE.Y.
    FUeVec3 U = AcPointToUe({1.0, 0.0, 0.0}, C);
    // bMapAcNorthToUeForward=true: AC.X(east) -> UE.Y(right); +
    // bNeedExtraMirror false (right-handed + swapped). So UE = (0, 100, 0).
    Report(NearlyEqual(U, {0.0, 100.0, 0.0}), "AC(1,0,0) -> UE(0,100,0) default conv");

    // Half-metre AC unit: 2 AC units = 1 m = 100 cm in UE.
    C.AcUnitMeters = 0.5;
    U = AcPointToUe({2.0, 0.0, 0.0}, C);
    Report(NearlyEqual(U, {0.0, 100.0, 0.0}), "AC(2,0,0) with 0.5m unit -> UE(0,100,0)");
    Report(NearlyEqual(AcUnitToUeCentimeters(C), 50.0), "0.5m unit = 50 cm");
}

void TestLandblockEncodeDecode()
{
    std::printf("[Landblock encode/decode round-trip]\n");
    const std::uint8_t Samples[] = { 0, 1, 0x7F, 0xFE };
    for (auto X : Samples)
    {
        for (auto Y : Samples)
        {
            const FAcLandblockId Id = EncodeLandblockId(X, Y);
            std::uint8_t OutX = 0, OutY = 0;
            DecomposeLandblockId(Id, OutX, OutY);
            char Name[64];
            std::snprintf(Name, sizeof(Name), "encode/decode (%u,%u)", X, Y);
            Report(OutX == X && OutY == Y, Name);
        }
    }
}

void TestLandblockForAcPoint()
{
    std::printf("[Landblock id for AC point]\n");
    const FAcWorldConventions C; // defaults: 192 m side, 255 grid
    auto LbXY = [](FAcLandblockId Id) -> std::pair<std::uint8_t, std::uint8_t>
    {
        std::uint8_t X = 0, Y = 0;
        DecomposeLandblockId(Id, X, Y);
        return {X, Y};
    };

    {
        auto [X, Y] = LbXY(LandblockIdForAcPoint({0.0, 0.0, 0.0}, C));
        Report(X == 0 && Y == 0, "origin -> lb(0,0)");
    }
    {
        auto [X, Y] = LbXY(LandblockIdForAcPoint({191.999, 0.0, 0.0}, C));
        Report(X == 0 && Y == 0, "X=191.999 (just inside lb 0) -> lb(0,0)");
    }
    {
        auto [X, Y] = LbXY(LandblockIdForAcPoint({192.0, 0.0, 0.0}, C));
        Report(X == 1 && Y == 0, "X=192.0 (start of lb 1) -> lb(1,0)");
    }
    {
        auto [X, Y] = LbXY(LandblockIdForAcPoint({192.0 * 100 + 50, 192.0 * 5 + 1.0, 0.0}, C));
        Report(X == 100 && Y == 5, "deep interior -> lb(100,5)");
    }
    {
        // Out-of-world high -> clamps to max grid index (254 with default).
        auto [X, Y] = LbXY(LandblockIdForAcPoint({1e9, 1e9, 0.0}, C));
        Report(X == 254 && Y == 254, "far OOB high clamps to (254,254)");
    }
    {
        // Out-of-world low -> clamps to (0,0).
        auto [X, Y] = LbXY(LandblockIdForAcPoint({-1e9, -1e9, 0.0}, C));
        Report(X == 0 && Y == 0, "far OOB low clamps to (0,0)");
    }
}

void TestLandblockOriginConsistency()
{
    std::printf("[Landblock origin consistency]\n");
    const FAcWorldConventions C;
    const std::uint8_t LbXs[] = { 0u, 1u, 100u, 254u };
    const std::uint8_t LbYs[] = { 0u, 1u,  50u, 200u };
    for (std::uint8_t LbX : LbXs)
    {
        for (std::uint8_t LbY : LbYs)
        {
            const FAcLandblockId Id = EncodeLandblockId(LbX, LbY);
            const FAcVec3 Origin = AcOriginOfLandblock(Id, C);
            // Origin must round-trip to the same landblock.
            const FAcLandblockId Id2 = LandblockIdForAcPoint(Origin, C);
            // A point strictly inside the named landblock must also resolve to it.
            const FAcVec3 Interior {
                Origin.X + (C.LandblockSideMeters * 0.5),
                Origin.Y + (C.LandblockSideMeters * 0.5),
                0.0
            };
            const FAcLandblockId Id3 = LandblockIdForAcPoint(Interior, C);
            char Name[96];
            std::snprintf(Name, sizeof(Name), "origin and interior of lb(%u,%u) resolve to lb(%u,%u)", LbX, LbY, LbX, LbY);
            Report(Id == Id2 && Id == Id3, Name);
        }
    }
}

void TestIsInsideWorld()
{
    std::printf("[IsAcPointInsideWorld]\n");
    const FAcWorldConventions C;
    Report( IsAcPointInsideWorld({0.0, 0.0, 0.0}, C), "(0,0,0) inside");
    Report( IsAcPointInsideWorld({100.0, 100.0, 0.0}, C), "(100,100,0) inside");
    Report(!IsAcPointInsideWorld({-1.0, 0.0, 0.0}, C), "(-1,0,0) outside");
    Report(!IsAcPointInsideWorld({0.0, -1.0, 0.0}, C), "(0,-1,0) outside");
    // World extent = 255 * 192 = 48960 m.
    Report( IsAcPointInsideWorld({48959.99, 48959.99, 0.0}, C), "just-inside far corner");
    Report(!IsAcPointInsideWorld({48960.0, 0.0, 0.0}, C), "exactly at far edge X is OUT (half-open interval)");
    Report(!IsAcPointInsideWorld({1e6, 0.0, 0.0}, C), "way out X");
}

void TestBasisOrthogonalityAndUniformScale()
{
    std::printf("[Basis: orthogonality + uniform scale preserved]\n");
    // After transforming the AC unit basis, the three UE output vectors
    // must be mutually orthogonal AND have identical magnitude (the
    // transform is a permutation + uniform scaling, no shear, no
    // anisotropic scale). This is a stronger property than round-trip
    // and catches accidental anisotropy / shear regressions.
    for (size_t ci = 0; ci < sizeof(kConventionSet)/sizeof(kConventionSet[0]); ++ci)
    {
        const FAcWorldConventions& C = kConventionSet[ci];
        const FUeVec3 Ex = AcVectorToUe({1.0, 0.0, 0.0}, C);
        const FUeVec3 Ey = AcVectorToUe({0.0, 1.0, 0.0}, C);
        const FUeVec3 Ez = AcVectorToUe({0.0, 0.0, 1.0}, C);

        auto Dot = [](const FUeVec3& A, const FUeVec3& B) {
            return A.X*B.X + A.Y*B.Y + A.Z*B.Z;
        };
        auto Len = [&](const FUeVec3& V) { return std::sqrt(Dot(V, V)); };

        const double Lx = Len(Ex), Ly = Len(Ey), Lz = Len(Ez);
        const double ExpectedLen = C.AcUnitMeters * 100.0; // m -> cm

        char Name[160];

        std::snprintf(Name, sizeof(Name), "conv#%zu Ex.Ey orthogonal", ci);
        Report(NearlyEqual(Dot(Ex, Ey), 0.0), Name);

        std::snprintf(Name, sizeof(Name), "conv#%zu Ex.Ez orthogonal", ci);
        Report(NearlyEqual(Dot(Ex, Ez), 0.0), Name);

        std::snprintf(Name, sizeof(Name), "conv#%zu Ey.Ez orthogonal", ci);
        Report(NearlyEqual(Dot(Ey, Ez), 0.0), Name);

        std::snprintf(Name, sizeof(Name),
            "conv#%zu uniform scale Lx=Ly=Lz=%.1f (got %.3f, %.3f, %.3f)",
            ci, ExpectedLen, Lx, Ly, Lz);
        Report(NearlyEqual(Lx, ExpectedLen) && NearlyEqual(Ly, ExpectedLen) && NearlyEqual(Lz, ExpectedLen), Name);

        // Informational only: print the chirality the transform produced
        // for this convention. The transform is chirality-preserving, so
        // this exposes the AC chirality as-mapped into UE axis labels.
        // (Not a pass/fail — just observable for debugging the spec.)
        const FUeVec3 Cross {
            Ex.Y * Ey.Z - Ex.Z * Ey.Y,
            Ex.Z * Ey.X - Ex.X * Ey.Z,
            Ex.X * Ey.Y - Ex.Y * Ey.X
        };
        const char* Chirality = (Cross.Z * Ez.Z > 0.0) ? "right-handed (mathematical)"
                                                       : "left-handed (mathematical)";
        std::printf("       (conv#%zu output UE basis is %s; cross.Z=%.1f Ez.Z=%.1f)\n",
                    ci, Chirality, Cross.Z, Ez.Z);
    }
}

void TestZeroAcUnitDoesNotCrashIfWellGuarded()
{
    std::printf("[Edge: AC unit = 0 -> handled (NaN/inf is acceptable, crash is not)]\n");
    // We don't define behavior for unit=0 in the point/vector transforms;
    // just confirm we don't crash. IEEE 754 NaN/inf propagation is the
    // intended signal-to-caller.
    FAcWorldConventions C; C.AcUnitMeters = 0.0;
    const FAcVec3 P {1.0, 0.0, 0.0};
    const FUeVec3 U = AcPointToUe(P, C);
    (void)U;
    Report(true, "no crash on AcUnitMeters=0 (point transform)");
}

void TestLandblockSafetyGuards()
{
    std::printf("[Landblock functions: invalid conventions -> safe zero, NaN inputs do not UB]\n");

    // Helper: extract lbX, lbY from an ID.
    auto LbXY = [](FAcLandblockId Id) -> std::pair<std::uint8_t, std::uint8_t>
    {
        std::uint8_t X = 0, Y = 0;
        DecomposeLandblockId(Id, X, Y);
        return {X, Y};
    };

    // 1) Invalid conventions: non-positive side / unit / both
    {
        FAcWorldConventions Bad; Bad.LandblockSideMeters = 0.0;
        const auto [X, Y] = LbXY(LandblockIdForAcPoint({100.0, 200.0, 0.0}, Bad));
        Report(X == 0 && Y == 0, "LandblockSideMeters=0 -> id (0,0)");
        const FAcVec3 Origin = AcOriginOfLandblock(EncodeLandblockId(5, 7), Bad);
        Report(Origin.X == 0.0 && Origin.Y == 0.0 && Origin.Z == 0.0, "LandblockSideMeters=0 -> origin (0,0,0)");
        Report(!IsAcPointInsideWorld({100.0, 200.0, 0.0}, Bad), "LandblockSideMeters=0 -> inside=false");
    }
    {
        FAcWorldConventions Bad; Bad.AcUnitMeters = 0.0;
        const auto [X, Y] = LbXY(LandblockIdForAcPoint({100.0, 200.0, 0.0}, Bad));
        Report(X == 0 && Y == 0, "AcUnitMeters=0 -> id (0,0)");
        Report(!IsAcPointInsideWorld({100.0, 200.0, 0.0}, Bad), "AcUnitMeters=0 -> inside=false");
    }
    {
        FAcWorldConventions Bad; Bad.LandblockSideMeters = -1.0;
        const auto [X, Y] = LbXY(LandblockIdForAcPoint({100.0, 200.0, 0.0}, Bad));
        Report(X == 0 && Y == 0, "LandblockSideMeters=-1 -> id (0,0)");
    }
    {
        FAcWorldConventions Bad; Bad.LandblockSideMeters = std::nan("");
        const auto [X, Y] = LbXY(LandblockIdForAcPoint({100.0, 200.0, 0.0}, Bad));
        Report(X == 0 && Y == 0, "LandblockSideMeters=NaN -> id (0,0)");
    }

    // 2) NaN input coordinates with valid conventions: must not UB.
    {
        const FAcWorldConventions C;
        const double kNaN = std::nan("");
        const auto [X, Y] = LbXY(LandblockIdForAcPoint({kNaN, 0.0, 0.0}, C));
        Report(X == 0 && Y == 0, "NaN X coord -> id (0,0) (no UB)");
        const auto [X2, Y2] = LbXY(LandblockIdForAcPoint({0.0, kNaN, 0.0}, C));
        Report(X2 == 0 && Y2 == 0, "NaN Y coord -> id (0,0) (no UB)");
        const auto [X3, Y3] = LbXY(LandblockIdForAcPoint({kNaN, kNaN, kNaN}, C));
        Report(X3 == 0 && Y3 == 0, "all-NaN -> id (0,0) (no UB)");
        Report(!IsAcPointInsideWorld({kNaN, kNaN, 0.0}, C), "all-NaN -> inside=false");
    }
    {
        // +Inf input: must be clamped to MaxIdx, not UB.
        const FAcWorldConventions C;
        const double kInf = std::numeric_limits<double>::infinity();
        const auto [X, Y] = LbXY(LandblockIdForAcPoint({kInf, kInf, 0.0}, C));
        Report(X == 254 && Y == 254, "+Inf coord -> clamped to (254,254)");
    }

    // 3) LandblockGridCount > 255 must clamp at the encoding limit (254),
    //    not silently truncate via uint8 wraparound.
    {
        FAcWorldConventions C; C.LandblockGridCount = 1000;
        // A point that would be in "landblock 500" if the grid were really 1000
        // wide. It must clamp at 254, not wrap to (500 mod 256 = 244).
        const FAcVec3 Pt { 500.5 * C.LandblockSideMeters, 0.0, 0.0 };
        const auto [X, Y] = LbXY(LandblockIdForAcPoint(Pt, C));
        Report(X == 254, "LandblockGridCount=1000 with point in lb 500 -> clamps to X=254 (not wrap to 244)");
        Report(Y == 0, "  ...Y stays 0");
    }
    {
        // LandblockGridCount=0 -> MaxIdx=0 -> all points -> id (0,0)
        FAcWorldConventions C; C.LandblockGridCount = 0;
        const auto [X, Y] = LbXY(LandblockIdForAcPoint({100.0, 200.0, 0.0}, C));
        Report(X == 0 && Y == 0, "LandblockGridCount=0 -> id (0,0)");
    }
}

void TestLandblockNonDefaultConventions()
{
    std::printf("[Landblock functions: non-default conventions exercise the data path]\n");
    // The prior landblock tests used only default conventions. The
    // production code is data-driven; non-default unit/side/grid must
    // also round-trip through the same functions.
    auto LbXY = [](FAcLandblockId Id) -> std::pair<std::uint8_t, std::uint8_t>
    {
        std::uint8_t X = 0, Y = 0;
        DecomposeLandblockId(Id, X, Y);
        return {X, Y};
    };

    // 1) Non-default unit: AC unit = 0.5 m. Landblock side stays 192 m,
    //    so a landblock spans 384 AC units. Point at AC.X = 385 units
    //    (= 192.5 m) is in landblock X=1.
    {
        FAcWorldConventions C; C.AcUnitMeters = 0.5;
        const auto [X, Y] = LbXY(LandblockIdForAcPoint({385.0, 0.0, 0.0}, C));
        Report(X == 1 && Y == 0, "AcUnitMeters=0.5, point at 385 units -> lb(1,0)");
    }

    // 2) Non-default landblock side: 100 m per side, default unit (1 m).
    //    Point at (250, 99.9) -> lb(2, 0).
    {
        FAcWorldConventions C; C.LandblockSideMeters = 100.0;
        const auto [X, Y] = LbXY(LandblockIdForAcPoint({250.0, 99.9, 0.0}, C));
        Report(X == 2 && Y == 0, "LandblockSideMeters=100, point (250, 99.9) -> lb(2,0)");
    }

    // 3) Non-default grid count: 10 x 10 world (very small).
    //    Point at (1000, 1000) clamps to lb(9, 9) (the max valid index
    //    given LandblockGridCount=10 is index 9, well below the
    //    encoding cap of 254).
    {
        FAcWorldConventions C; C.LandblockGridCount = 10;
        const auto [X, Y] = LbXY(LandblockIdForAcPoint({1e6, 1e6, 0.0}, C));
        Report(X == 9 && Y == 9, "LandblockGridCount=10, far OOB -> clamps to lb(9,9)");
        Report( IsAcPointInsideWorld({100.0, 100.0, 0.0}, C), "  ...in-world (100,100) inside");
        Report(!IsAcPointInsideWorld({2000.0, 100.0, 0.0}, C), "  ...out-of-world (2000,100) outside");
    }

    // 4) Origin round-trip with non-default conventions.
    {
        FAcWorldConventions C; C.AcUnitMeters = 2.0; C.LandblockSideMeters = 50.0;
        // 1 AC unit = 2 m. Landblock side = 50 m = 25 AC units.
        const FAcLandblockId Id = EncodeLandblockId(3, 4);
        const FAcVec3 Origin = AcOriginOfLandblock(Id, C);
        // Expected: lb 3 starts at 3*50 = 150 m = 75 AC units; lb 4 starts at 200 m = 100 AC units.
        Report(NearlyEqual(Origin.X, 75.0) && NearlyEqual(Origin.Y, 100.0),
            "AcOriginOfLandblock(3,4) with 50m/2m conv -> (75, 100) AC units");
        // The origin point should resolve back to the same landblock.
        const auto [X2, Y2] = LbXY(LandblockIdForAcPoint(Origin, C));
        Report(X2 == 3 && Y2 == 4, "  ...origin re-resolves to lb(3,4)");
        // A point in the interior must too.
        const FAcVec3 Interior { Origin.X + 5.0, Origin.Y + 5.0, 0.0 };
        const auto [X3, Y3] = LbXY(LandblockIdForAcPoint(Interior, C));
        Report(X3 == 3 && Y3 == 4, "  ...interior also resolves to lb(3,4)");
    }
}

} // anonymous namespace

int main()
{
    std::printf("=== CoordTransform standalone tests ===\n");
    TestRoundTripPointsAllConventions();
    TestRoundTripUePointsAllConventions();
    TestRoundTripVectors();
    TestUnitScale();
    TestLandblockEncodeDecode();
    TestLandblockForAcPoint();
    TestLandblockOriginConsistency();
    TestLandblockNonDefaultConventions();
    TestLandblockSafetyGuards();
    TestIsInsideWorld();
    TestBasisOrthogonalityAndUniformScale();
    TestZeroAcUnitDoesNotCrashIfWellGuarded();
    std::printf("---\n%d passed, %d failed.\n", gPassed, gFailed);
    return (gFailed == 0) ? 0 : 1;
}
