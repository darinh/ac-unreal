// =====================================================================
// LandblockImporterTests.cpp
//
// Standalone round-trip + edge-case tests for the v1 .aclb parser in
// Source/AcUnreal/{Public,Private}/AssetIngest/AcIntermediateLandblock.{h,cpp}.
//
// Built directly with cl.exe by pipeline/asset-ingest/build.ps1 — no
// UnrealBuildTool, no UE. Same source files are compiled into the UE
// module by UBT. This rig fails fast for parser regressions.
// =====================================================================

#include "AssetIngest/AcIntermediateLandblock.h"

#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <limits>
#include <string>
#include <vector>

using namespace ac_ingest;

namespace {

int gPassed = 0;
int gFailed = 0;

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

// Construct a small valid struct for tests to mutate.
FAcIntermediateLandblock MakeValidLandblock(std::uint32_t Side, std::uint32_t Layers, std::uint32_t Id)
{
    FAcIntermediateLandblock LB;
    LB.Header.Magic              = kAcLbMagic;
    LB.Header.Version            = kAcLbCurrentVersion;
    LB.Header.LandblockId        = Id;
    LB.Header.SamplesPerSide     = Side;
    LB.Header.TextureLayerCount  = Layers;
    LB.Header.Flags              = 0;
    LB.Header.Reserved[0]        = 0;
    LB.Header.Reserved[1]        = 0;

    const std::size_t Cells = static_cast<std::size_t>(Side) * Side;
    LB.Heights.resize(Cells);
    for (std::size_t I = 0; I < Cells; ++I)
    {
        LB.Heights[I] = static_cast<float>(I) * 0.5f - 7.25f; // mix positive + negative
    }
    LB.TextureIndices.resize(Cells * Layers);
    for (std::size_t I = 0; I < LB.TextureIndices.size(); ++I)
    {
        LB.TextureIndices[I] = static_cast<std::uint8_t>(I % 256u);
    }
    return LB;
}

bool LandblocksEqual(const FAcIntermediateLandblock& A, const FAcIntermediateLandblock& B)
{
    if (std::memcmp(&A.Header, &B.Header, sizeof(A.Header)) != 0) return false;
    if (A.Heights.size() != B.Heights.size()) return false;
    for (std::size_t I = 0; I < A.Heights.size(); ++I)
    {
        // Bit-for-bit float equality — these came from the same writer.
        std::uint32_t Au = 0, Bu = 0;
        std::memcpy(&Au, &A.Heights[I], 4);
        std::memcpy(&Bu, &B.Heights[I], 4);
        if (Au != Bu) return false;
    }
    if (A.TextureIndices.size() != B.TextureIndices.size()) return false;
    if (!A.TextureIndices.empty() &&
        std::memcmp(A.TextureIndices.data(), B.TextureIndices.data(), A.TextureIndices.size()) != 0)
    {
        return false;
    }
    return true;
}

// -------- Tests ------------------------------------------------------

void TestHeaderSizeAndConstants()
{
    std::printf("[Header size and magic constants]\n");
    Report(sizeof(FAcIntermediateLandblockHeader) == 32, "header sizeof == 32");
    Report(kAcLbMagic == 0x424C4341u, "magic == 'ACLB' little-endian");
    Report(kAcLbCurrentVersion == 1u, "version == 1");
}

void TestParseSerializeRoundTrip()
{
    std::printf("[Round-trip: 3x3 / no textures]\n");
    const FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0xAA0B0000);
    std::vector<std::uint8_t> Bytes;
    Report(SerializeLandblock(In, Bytes) == EAcLbParseStatus::OK, "serialize ok");
    Report(Bytes.size() == 32u + 9u * 4u, "expected size: 68 bytes (32 + 9*4)");
    FAcIntermediateLandblock Out;
    Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::OK, "parse ok");
    Report(LandblocksEqual(In, Out), "round-trip equality");
}

void TestParseSerializeRoundTripWithTextures()
{
    std::printf("[Round-trip: 5x5 / 2 texture layers]\n");
    const FAcIntermediateLandblock In = MakeValidLandblock(5, 2, 0x12340000);
    std::vector<std::uint8_t> Bytes;
    Report(SerializeLandblock(In, Bytes) == EAcLbParseStatus::OK, "serialize ok");
    // 32 + 25*4 + 25*2 = 32 + 100 + 50 = 182
    Report(Bytes.size() == 182u, "expected size: 182 bytes");
    FAcIntermediateLandblock Out;
    Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::OK, "parse ok");
    Report(LandblocksEqual(In, Out), "round-trip equality");
}

void TestParseRejectsBadMagic()
{
    std::printf("[Reject: bad magic]\n");
    FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0);
    std::vector<std::uint8_t> Bytes;
    SerializeLandblock(In, Bytes);
    Bytes[0] = 0xFF; // corrupt magic
    FAcIntermediateLandblock Out;
    Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::BadMagic, "bad magic detected");
}

void TestParseRejectsBadVersion()
{
    std::printf("[Reject: unsupported version]\n");
    FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0);
    In.Header.Version = 99;
    std::vector<std::uint8_t> Bytes;
    // SerializeLandblock will refuse to write a bad version; produce bytes manually.
    Bytes.resize(32 + 9 * 4);
    std::memcpy(Bytes.data(), &In.Header, sizeof(In.Header));
    // Heights all zero
    FAcIntermediateLandblock Out;
    Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::UnsupportedVersion, "version 99 rejected");
}

void TestParseRejectsInvalidSamplesPerSide()
{
    std::printf("[Reject: SamplesPerSide out of range]\n");
    {
        FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0);
        In.Header.SamplesPerSide = 1; // below kMin
        std::vector<std::uint8_t> Bytes(32);
        std::memcpy(Bytes.data(), &In.Header, sizeof(In.Header));
        FAcIntermediateLandblock Out;
        Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::InvalidSamplesPerSide,
               "SamplesPerSide=1 rejected");
    }
    {
        FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0);
        In.Header.SamplesPerSide = 100; // above kMax
        std::vector<std::uint8_t> Bytes(32);
        std::memcpy(Bytes.data(), &In.Header, sizeof(In.Header));
        FAcIntermediateLandblock Out;
        Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::InvalidSamplesPerSide,
               "SamplesPerSide=100 rejected");
    }
}

void TestParseRejectsInvalidTextureLayerCount()
{
    std::printf("[Reject: TextureLayerCount > kMax]\n");
    FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0);
    In.Header.TextureLayerCount = 99;
    std::vector<std::uint8_t> Bytes(32);
    std::memcpy(Bytes.data(), &In.Header, sizeof(In.Header));
    FAcIntermediateLandblock Out;
    Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::InvalidTextureLayerCount,
           "TextureLayerCount=99 rejected");
}

void TestParseRejectsNonzeroFlags()
{
    std::printf("[Reject: nonzero Flags]\n");
    FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0);
    In.Header.Flags = 0x1;
    std::vector<std::uint8_t> Bytes(32);
    std::memcpy(Bytes.data(), &In.Header, sizeof(In.Header));
    FAcIntermediateLandblock Out;
    Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::NonzeroFlagsReserved,
           "Flags=1 rejected");
}

void TestParseRejectsNonzeroReserved()
{
    std::printf("[Reject: nonzero Reserved]\n");
    {
        FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0);
        In.Header.Reserved[0] = 0xDEAD;
        std::vector<std::uint8_t> Bytes(32);
        std::memcpy(Bytes.data(), &In.Header, sizeof(In.Header));
        FAcIntermediateLandblock Out;
        Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::NonzeroReservedField,
               "Reserved[0] != 0 rejected");
    }
    {
        FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0);
        In.Header.Reserved[1] = 0xBEEF;
        std::vector<std::uint8_t> Bytes(32);
        std::memcpy(Bytes.data(), &In.Header, sizeof(In.Header));
        FAcIntermediateLandblock Out;
        Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::NonzeroReservedField,
               "Reserved[1] != 0 rejected");
    }
}

void TestParseRejectsBufferTooSmall()
{
    std::printf("[Reject: buffer too small for header]\n");
    std::vector<std::uint8_t> Tiny(10, 0);
    FAcIntermediateLandblock Out;
    Report(ParseLandblock(Tiny.data(), Tiny.size(), Out) == EAcLbParseStatus::BufferTooSmall,
           "len=10 rejected");
    Report(ParseLandblock(nullptr, 0, Out) == EAcLbParseStatus::BufferTooSmall,
           "null pointer rejected");
}

void TestParseRejectsSizeMismatch()
{
    std::printf("[Reject: header valid but buffer size != expected]\n");
    FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0);
    std::vector<std::uint8_t> Bytes;
    SerializeLandblock(In, Bytes);
    Bytes.push_back(0xFF); // extra trailing byte
    FAcIntermediateLandblock Out;
    Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::SizeMismatch,
           "extra trailing byte rejected");
    Bytes.pop_back();
    Bytes.pop_back();
    Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::SizeMismatch,
           "missing trailing byte rejected");
}

void TestParseRejectsNonFiniteHeight()
{
    std::printf("[Reject: NaN / Inf height]\n");
    FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0);
    {
        In.Heights[4] = std::numeric_limits<float>::quiet_NaN();
        std::vector<std::uint8_t> Bytes;
        // SerializeLandblock should refuse to write NaN.
        Report(SerializeLandblock(In, Bytes) == EAcLbParseStatus::NonFiniteHeight,
               "serialize rejects NaN");
    }
    {
        // Hand-build a buffer with NaN in heights to exercise parser path.
        FAcIntermediateLandblock Good = MakeValidLandblock(3, 0, 0);
        std::vector<std::uint8_t> Bytes;
        SerializeLandblock(Good, Bytes);
        const float kNaN = std::numeric_limits<float>::quiet_NaN();
        std::memcpy(Bytes.data() + 32 + 4 * 4, &kNaN, 4); // sample index 4
        FAcIntermediateLandblock Out;
        Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::NonFiniteHeight,
               "parse rejects NaN");
    }
    {
        // +Inf
        FAcIntermediateLandblock Good = MakeValidLandblock(3, 0, 0);
        std::vector<std::uint8_t> Bytes;
        SerializeLandblock(Good, Bytes);
        const float kInf = std::numeric_limits<float>::infinity();
        std::memcpy(Bytes.data() + 32 + 0 * 4, &kInf, 4);
        FAcIntermediateLandblock Out;
        Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::NonFiniteHeight,
               "parse rejects +Inf");
    }
}

void TestSerializeRejectsInvalidInput()
{
    std::printf("[Serialize: refuses invalid struct]\n");
    {
        FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0);
        In.Header.Magic = 0xBAD;
        std::vector<std::uint8_t> Bytes;
        Report(SerializeLandblock(In, Bytes) == EAcLbParseStatus::BadMagic, "bad magic in struct rejected");
        Report(Bytes.empty(), "  ...output buffer cleared on failure");
    }
    {
        FAcIntermediateLandblock In = MakeValidLandblock(5, 0, 0);
        In.Heights.resize(3); // wrong size for Side=5
        std::vector<std::uint8_t> Bytes;
        Report(SerializeLandblock(In, Bytes) == EAcLbParseStatus::SizeMismatch,
               "Heights vector size mismatch rejected");
    }
    {
        FAcIntermediateLandblock In = MakeValidLandblock(3, 2, 0);
        In.TextureIndices.resize(5); // wrong size for Side=3, Layers=2 (should be 18)
        std::vector<std::uint8_t> Bytes;
        Report(SerializeLandblock(In, Bytes) == EAcLbParseStatus::SizeMismatch,
               "TextureIndices vector size mismatch rejected");
    }
}

void TestComputeExpectedSize()
{
    std::printf("[ComputeExpectedSize]\n");
    FAcIntermediateLandblockHeader H;
    H.SamplesPerSide = 9;
    H.TextureLayerCount = 0;
    Report(ComputeExpectedSize(H) == 32u + 81u * 4u, "9x9 no tex = 32 + 324 = 356");
    H.TextureLayerCount = 1;
    Report(ComputeExpectedSize(H) == 32u + 81u * 4u + 81u, "9x9 1 tex = 437");
    H.TextureLayerCount = 4;
    Report(ComputeExpectedSize(H) == 32u + 81u * 4u + 81u * 4u, "9x9 4 tex = 32 + 324 + 324 = 680");
}

void TestToStringCoverage()
{
    std::printf("[ToString: all enum values have a name]\n");
    auto Check = [&](EAcLbParseStatus S, const char* Expected)
    {
        const char* Got = ToString(S);
        const bool Ok = Got != nullptr && std::strcmp(Got, Expected) == 0;
        char Name[96];
        std::snprintf(Name, sizeof(Name), "ToString(%s) == \"%s\"", Expected, Expected);
        Report(Ok, Name);
    };
    Check(EAcLbParseStatus::OK,                       "OK");
    Check(EAcLbParseStatus::BufferTooSmall,           "BufferTooSmall");
    Check(EAcLbParseStatus::BadMagic,                 "BadMagic");
    Check(EAcLbParseStatus::UnsupportedVersion,       "UnsupportedVersion");
    Check(EAcLbParseStatus::InvalidSamplesPerSide,    "InvalidSamplesPerSide");
    Check(EAcLbParseStatus::InvalidTextureLayerCount, "InvalidTextureLayerCount");
    Check(EAcLbParseStatus::NonzeroFlagsReserved,     "NonzeroFlagsReserved");
    Check(EAcLbParseStatus::NonzeroReservedField,     "NonzeroReservedField");
    Check(EAcLbParseStatus::SizeMismatch,             "SizeMismatch");
    Check(EAcLbParseStatus::NonFiniteHeight,          "NonFiniteHeight");
}

void TestRealSampleIfPresent(const std::string& RepoRoot, bool bHardFailIfMissing)
{
    std::printf("[Integration: parse the committed synthetic sample]\n");
    const std::string SamplePath = RepoRoot + "\\pipeline\\asset-ingest\\samples\\synthetic_landblock_0xAA0B0000.aclb";
    std::ifstream F(SamplePath, std::ios::binary);
    if (!F.is_open())
    {
        if (bHardFailIfMissing)
        {
            // build.ps1 invoked us with a repo-root argument; the fixture
            // is committed and MUST be present in a normal checkout. A
            // missing file here means a real bug — wrong path, LFS-pointer
            // confusion, accidental deletion — not a "skip".
            char Msg[256];
            std::snprintf(Msg, sizeof(Msg), "committed fixture missing at %s", SamplePath.c_str());
            Report(false, Msg);
        }
        else
        {
            std::printf("  SKIP  sample file not found at %s (run gen_sample.ps1)\n", SamplePath.c_str());
        }
        return;
    }
    F.seekg(0, std::ios::end);
    const std::streamsize Size = F.tellg();
    F.seekg(0, std::ios::beg);
    std::vector<std::uint8_t> Bytes(static_cast<std::size_t>(Size));
    F.read(reinterpret_cast<char*>(Bytes.data()), Size);
    F.close();

    FAcIntermediateLandblock LB;
    const EAcLbParseStatus Status = ParseLandblock(Bytes.data(), Bytes.size(), LB);
    char Name[160];
    std::snprintf(Name, sizeof(Name), "sample parses (%zu bytes): %s", Bytes.size(), ToString(Status));
    Report(Status == EAcLbParseStatus::OK, Name);
    if (Status == EAcLbParseStatus::OK)
    {
        Report(LB.Header.LandblockId == 0xAA0B0000u, "sample LandblockId == 0xAA0B0000");
        Report((LB.Header.LandblockId & 0xFFFFu) == 0u, "sample LandblockId low-16 == 0 (v1 invariant)");
        Report(LB.Header.SamplesPerSide == 9u, "sample SamplesPerSide == 9");
        Report(LB.Header.TextureLayerCount == 1u, "sample TextureLayerCount == 1");
        Report(LB.Heights.size() == 81u, "sample 81 height values");
        Report(LB.TextureIndices.size() == 81u, "sample 81 texture indices");
        bool AnyFinite = false;
        for (float V : LB.Heights) { if (std::isfinite(V)) { AnyFinite = true; break; } }
        Report(AnyFinite, "at least one finite height value");
    }
}

void TestParseRejectsInvalidLandblockIdLowBits()
{
    std::printf("[Reject: LandblockId low-16 bits != 0 (v1 invariant)]\n");
    FAcIntermediateLandblock In = MakeValidLandblock(3, 0, 0);
    In.Header.LandblockId = 0xAA0BFFFFu; // canonical AC outdoor-surface ID — must be masked
    std::vector<std::uint8_t> Bytes(32);
    std::memcpy(Bytes.data(), &In.Header, sizeof(In.Header));
    FAcIntermediateLandblock Out;
    Report(ParseLandblock(Bytes.data(), Bytes.size(), Out) == EAcLbParseStatus::InvalidLandblockId,
           "0xAA0BFFFF rejected (low-16 = 0xFFFF)");
    {
        FAcIntermediateLandblock In2 = MakeValidLandblock(3, 0, 0);
        In2.Header.LandblockId = 0xAA0B0001u; // any nonzero low-16 must fail
        std::vector<std::uint8_t> Bytes2(32);
        std::memcpy(Bytes2.data(), &In2.Header, sizeof(In2.Header));
        FAcIntermediateLandblock Out2;
        Report(ParseLandblock(Bytes2.data(), Bytes2.size(), Out2) == EAcLbParseStatus::InvalidLandblockId,
               "0xAA0B0001 rejected (low-16 = 1)");
    }
    {
        // Serializer must also refuse it (symmetry).
        FAcIntermediateLandblock In3 = MakeValidLandblock(3, 0, 0);
        In3.Header.LandblockId = 0x12340042u;
        std::vector<std::uint8_t> Bytes3;
        Report(SerializeLandblock(In3, Bytes3) == EAcLbParseStatus::InvalidLandblockId,
               "serialize rejects low-16 != 0");
    }
}

} // anonymous namespace

int main(int argc, char** argv)
{
    std::printf("=== Landblock importer standalone tests ===\n");
    TestHeaderSizeAndConstants();
    TestParseSerializeRoundTrip();
    TestParseSerializeRoundTripWithTextures();
    TestParseRejectsBadMagic();
    TestParseRejectsBadVersion();
    TestParseRejectsInvalidSamplesPerSide();
    TestParseRejectsInvalidTextureLayerCount();
    TestParseRejectsNonzeroFlags();
    TestParseRejectsNonzeroReserved();
    TestParseRejectsBufferTooSmall();
    TestParseRejectsSizeMismatch();
    TestParseRejectsNonFiniteHeight();
    TestSerializeRejectsInvalidInput();
    TestComputeExpectedSize();
    TestToStringCoverage();
    TestParseRejectsInvalidLandblockIdLowBits();

    // build.ps1 passes the repo root as argv[1]. When invoked from
    // build.ps1, the committed fixture MUST be present; missing means
    // a real bug. When invoked by hand without argv[1], skip silently.
    if (argc >= 2)
    {
        TestRealSampleIfPresent(argv[1], /*bHardFailIfMissing=*/true);
    }
    else
    {
        std::printf("[Integration]\n  SKIP  no repo root passed (argv[1]) — pass a repo path to run integration tests\n");
    }

    // Also test ToString coverage for the new InvalidLandblockId value.
    {
        const char* S = ToString(EAcLbParseStatus::InvalidLandblockId);
        Report(S != nullptr && std::strcmp(S, "InvalidLandblockId") == 0, "ToString(InvalidLandblockId) == \"InvalidLandblockId\"");
    }

    std::printf("---\n%d passed, %d failed.\n", gPassed, gFailed);
    return (gFailed == 0) ? 0 : 1;
}
