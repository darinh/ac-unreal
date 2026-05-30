// =====================================================================
// AcIntermediateLandblock.h
//
// Canonical reader/writer for the v1 intermediate landblock exchange
// format (.aclb). See pipeline/asset-ingest/FORMAT.md for the on-disk
// schema; this header is the C++17 mirror of that schema and is the
// only place either side of the pipeline is allowed to parse the bytes.
//
// Design rules (same as CoordCore):
//  * Pure C++17. No UE headers, no exceptions. This MUST compile both
//    as part of the AcUnreal UE module AND as part of the standalone
//    test rig at pipeline/asset-ingest/build.ps1.
//  * Single std::vector in the result struct is the only STL container
//    in the surface; the rest of the API is POD + plain pointers.
//  * Strict validation. Invalid input produces a typed status code, not
//    UB and not a partial result. Out-of-range integers, NaN heights,
//    nonzero reserved fields, and size mismatches all reject loudly.
//  * Little-endian target. Modern x64 / ARM64 Windows + Linux + macOS
//    all satisfy this. A future big-endian port would byte-swap inside
//    the read/write helpers in the .cpp; the public API would not change.
// =====================================================================
#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace ac_ingest {

// ---------------------------------------------------------------------
// Constants from the format spec. If FORMAT.md and these disagree,
// FORMAT.md is the source of truth and this is wrong.
// ---------------------------------------------------------------------
constexpr std::uint32_t kAcLbMagic                = 0x424C4341u; // 'ACLB' LE
constexpr std::uint32_t kAcLbCurrentVersion       = 1u;
constexpr std::uint32_t kAcLbMinSamplesPerSide    = 2u;
constexpr std::uint32_t kAcLbMaxSamplesPerSide    = 65u; // sanity cap; AC native is 9
constexpr std::uint32_t kAcLbMaxTextureLayerCount = 4u;  // sanity cap

// ---------------------------------------------------------------------
// 32-byte fixed header.
// ---------------------------------------------------------------------
struct FAcIntermediateLandblockHeader
{
    std::uint32_t Magic              = 0;
    std::uint32_t Version            = 0;
    std::uint32_t LandblockId        = 0; // AC encoding: byte3=LBx, byte2=LBy
    std::uint32_t SamplesPerSide     = 0; // AC native = 9
    std::uint32_t TextureLayerCount  = 0; // 0..4
    std::uint32_t Flags              = 0; // v1: must be 0
    std::uint32_t Reserved[2]        = {0, 0};
};
static_assert(sizeof(FAcIntermediateLandblockHeader) == 32,
              "AC intermediate landblock header MUST be 32 bytes (FORMAT.md v1)");

// ---------------------------------------------------------------------
// Parsed result. Heights and TextureIndices are sized per header.
// ---------------------------------------------------------------------
struct FAcIntermediateLandblock
{
    FAcIntermediateLandblockHeader Header;

    // size == SamplesPerSide * SamplesPerSide. Row-major, Y outer.
    // Units: metres (AC world frame).
    std::vector<float> Heights;

    // size == SamplesPerSide * SamplesPerSide * TextureLayerCount.
    // Layers are contiguous: layer 0 first, then layer 1, etc.
    std::vector<std::uint8_t> TextureIndices;
};

// ---------------------------------------------------------------------
// Status codes. Every reader entry point returns one of these; OK is
// the only success value. ToString() gives a stable diagnostic name.
// ---------------------------------------------------------------------
enum class EAcLbParseStatus : std::uint8_t
{
    OK = 0,
    BufferTooSmall,         // buffer smaller than the 32-byte header
    BadMagic,               // first 4 bytes != kAcLbMagic
    UnsupportedVersion,     // Version != kAcLbCurrentVersion
    InvalidSamplesPerSide,  // not in [kMin..kMax]
    InvalidTextureLayerCount, // > kAcLbMaxTextureLayerCount
    NonzeroFlagsReserved,   // v1 writers must set Flags==0
    NonzeroReservedField,   // v1 writers must set Reserved[] == 0
    SizeMismatch,           // buffer length != ComputeExpectedSize(header)
    NonFiniteHeight,        // a sample is NaN or +/-Inf
    InvalidLandblockId      // v1: low 16 bits of LandblockId must be 0
};

const char* ToString(EAcLbParseStatus Status);

// ---------------------------------------------------------------------
// Public API.
// ---------------------------------------------------------------------

// Validate header-only. Useful for tools that want to peek at format
// metadata without paying for the full payload read.
EAcLbParseStatus ValidateHeader(const FAcIntermediateLandblockHeader& H);

// Given a valid header, compute the total expected file size including
// the 32-byte header itself.
std::size_t ComputeExpectedSize(const FAcIntermediateLandblockHeader& H);

// Parse a full buffer. On success, Out is fully populated. On any
// failure Out is left in an unspecified state and the caller MUST NOT
// read it.
EAcLbParseStatus ParseLandblock(const std::uint8_t* Bytes,
                                std::size_t Len,
                                FAcIntermediateLandblock& Out);

// Serialize a struct to bytes matching the FORMAT.md layout. Validates
// the input via the same rules as ParseLandblock and refuses to emit
// invalid bytes. OutBytes is cleared on entry.
EAcLbParseStatus SerializeLandblock(const FAcIntermediateLandblock& In,
                                    std::vector<std::uint8_t>& OutBytes);

} // namespace ac_ingest
