// =====================================================================
// AcIntermediateLandblock.cpp
//
// Implementation of the v1 intermediate landblock reader/writer.
// See header for design rules; see pipeline/asset-ingest/FORMAT.md for
// the on-disk schema.
// =====================================================================
#include "AssetIngest/AcIntermediateLandblock.h"

#include <cmath>
#include <cstring>
#include <limits>

// ---------------------------------------------------------------------
// Endianness guard. The .aclb format is documented as little-endian.
// The ReadU32LE / ReadF32LE helpers below assume host == LE and do
// raw memcpy (no byte swap). If you port this to a big-endian target,
// you MUST either implement byte-swapping in those helpers or carry
// the host-LE assumption forward via a real conversion path.
// Detect at compile time where possible so a hypothetical BE build
// fails to compile rather than producing silently-wrong bytes.
// ---------------------------------------------------------------------
#if defined(__BYTE_ORDER__) && defined(__ORDER_LITTLE_ENDIAN__)
    static_assert(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__,
                  "AcIntermediateLandblock: little-endian host required (BE port must add byte swap)");
#elif defined(_MSC_VER)
    // MSVC doesn't define __BYTE_ORDER__ but its supported architectures
    // (x86, x64, ARM, ARM64) all run in little-endian mode.
    #if !defined(_M_IX86) && !defined(_M_X64) && !defined(_M_ARM) && !defined(_M_ARM64)
        #error "AcIntermediateLandblock: unrecognised MSVC target — verify endianness and remove this guard if LE"
    #endif
#else
    // Unknown compiler. Fall through; at runtime any byte-order issue
    // will manifest as BadMagic on the first .aclb read.
#endif

namespace ac_ingest {

namespace {

// std::memcpy a uint32 out of the buffer. Avoids type-pun /
// strict-aliasing UB; works on any alignment.
inline std::uint32_t ReadU32LE(const std::uint8_t* P)
{
    std::uint32_t V = 0;
    std::memcpy(&V, P, 4);
    return V;
}

inline void WriteU32LE(std::uint8_t* P, std::uint32_t V)
{
    std::memcpy(P, &V, 4);
}

inline float ReadF32LE(const std::uint8_t* P)
{
    float V = 0.0f;
    std::memcpy(&V, P, 4);
    return V;
}

inline void WriteF32LE(std::uint8_t* P, float V)
{
    std::memcpy(P, &V, 4);
}

} // anonymous namespace

const char* ToString(EAcLbParseStatus Status)
{
    switch (Status)
    {
        case EAcLbParseStatus::OK:                       return "OK";
        case EAcLbParseStatus::BufferTooSmall:           return "BufferTooSmall";
        case EAcLbParseStatus::BadMagic:                 return "BadMagic";
        case EAcLbParseStatus::UnsupportedVersion:       return "UnsupportedVersion";
        case EAcLbParseStatus::InvalidSamplesPerSide:    return "InvalidSamplesPerSide";
        case EAcLbParseStatus::InvalidTextureLayerCount: return "InvalidTextureLayerCount";
        case EAcLbParseStatus::NonzeroFlagsReserved:     return "NonzeroFlagsReserved";
        case EAcLbParseStatus::NonzeroReservedField:     return "NonzeroReservedField";
        case EAcLbParseStatus::SizeMismatch:             return "SizeMismatch";
        case EAcLbParseStatus::NonFiniteHeight:          return "NonFiniteHeight";
        case EAcLbParseStatus::InvalidLandblockId:       return "InvalidLandblockId";
    }
    return "Unknown";
}

EAcLbParseStatus ValidateHeader(const FAcIntermediateLandblockHeader& H)
{
    if (H.Magic != kAcLbMagic) return EAcLbParseStatus::BadMagic;
    if (H.Version != kAcLbCurrentVersion) return EAcLbParseStatus::UnsupportedVersion;
    if (H.SamplesPerSide < kAcLbMinSamplesPerSide ||
        H.SamplesPerSide > kAcLbMaxSamplesPerSide)
    {
        return EAcLbParseStatus::InvalidSamplesPerSide;
    }
    if (H.TextureLayerCount > kAcLbMaxTextureLayerCount)
    {
        return EAcLbParseStatus::InvalidTextureLayerCount;
    }
    if (H.Flags != 0u) return EAcLbParseStatus::NonzeroFlagsReserved;
    if (H.Reserved[0] != 0u || H.Reserved[1] != 0u)
    {
        return EAcLbParseStatus::NonzeroReservedField;
    }
    // v1 represents outdoor landblock surface only; the low 16 bits of
    // the AC LandblockId are intra-LB cell data, which is not carried
    // here. See FORMAT.md "LandblockId semantics" — exporters that read
    // raw AC values must mask the low 16 bits before emitting.
    if ((H.LandblockId & 0xFFFFu) != 0u) return EAcLbParseStatus::InvalidLandblockId;
    return EAcLbParseStatus::OK;
}

std::size_t ComputeExpectedSize(const FAcIntermediateLandblockHeader& H)
{
    const std::size_t Side  = static_cast<std::size_t>(H.SamplesPerSide);
    const std::size_t Cells = Side * Side;
    return sizeof(FAcIntermediateLandblockHeader)
         + Cells * sizeof(float)
         + Cells * static_cast<std::size_t>(H.TextureLayerCount);
}

EAcLbParseStatus ParseLandblock(const std::uint8_t* Bytes,
                                std::size_t Len,
                                FAcIntermediateLandblock& Out)
{
    if (Bytes == nullptr || Len < sizeof(FAcIntermediateLandblockHeader))
    {
        return EAcLbParseStatus::BufferTooSmall;
    }

    FAcIntermediateLandblockHeader H;
    H.Magic              = ReadU32LE(Bytes + 0);
    H.Version            = ReadU32LE(Bytes + 4);
    H.LandblockId        = ReadU32LE(Bytes + 8);
    H.SamplesPerSide     = ReadU32LE(Bytes + 12);
    H.TextureLayerCount  = ReadU32LE(Bytes + 16);
    H.Flags              = ReadU32LE(Bytes + 20);
    H.Reserved[0]        = ReadU32LE(Bytes + 24);
    H.Reserved[1]        = ReadU32LE(Bytes + 28);

    const EAcLbParseStatus HdrStatus = ValidateHeader(H);
    if (HdrStatus != EAcLbParseStatus::OK) return HdrStatus;

    const std::size_t Expected = ComputeExpectedSize(H);
    if (Len != Expected) return EAcLbParseStatus::SizeMismatch;

    Out.Header = H;

    const std::size_t Side  = static_cast<std::size_t>(H.SamplesPerSide);
    const std::size_t Cells = Side * Side;

    Out.Heights.resize(Cells);
    const std::uint8_t* HeightBytes = Bytes + sizeof(FAcIntermediateLandblockHeader);
    for (std::size_t I = 0; I < Cells; ++I)
    {
        const float V = ReadF32LE(HeightBytes + I * sizeof(float));
        // Reject NaN / +/-Inf. Either indicates a corrupt or
        // mistakenly-written file; we'd rather fail loudly than
        // propagate non-finite heights into UE physics or rendering.
        if (!std::isfinite(V))
        {
            return EAcLbParseStatus::NonFiniteHeight;
        }
        Out.Heights[I] = V;
    }

    const std::size_t TexBytes = Cells * static_cast<std::size_t>(H.TextureLayerCount);
    Out.TextureIndices.resize(TexBytes);
    if (TexBytes > 0)
    {
        const std::uint8_t* TexSrc = HeightBytes + Cells * sizeof(float);
        std::memcpy(Out.TextureIndices.data(), TexSrc, TexBytes);
    }

    return EAcLbParseStatus::OK;
}

EAcLbParseStatus SerializeLandblock(const FAcIntermediateLandblock& In,
                                    std::vector<std::uint8_t>& OutBytes)
{
    OutBytes.clear();

    const EAcLbParseStatus HdrStatus = ValidateHeader(In.Header);
    if (HdrStatus != EAcLbParseStatus::OK) return HdrStatus;

    const std::size_t Side  = static_cast<std::size_t>(In.Header.SamplesPerSide);
    const std::size_t Cells = Side * Side;
    const std::size_t TexBytes = Cells * static_cast<std::size_t>(In.Header.TextureLayerCount);

    if (In.Heights.size() != Cells)           return EAcLbParseStatus::SizeMismatch;
    if (In.TextureIndices.size() != TexBytes) return EAcLbParseStatus::SizeMismatch;

    for (float V : In.Heights)
    {
        if (!std::isfinite(V)) return EAcLbParseStatus::NonFiniteHeight;
    }

    const std::size_t Total = ComputeExpectedSize(In.Header);
    OutBytes.resize(Total);
    std::uint8_t* P = OutBytes.data();

    WriteU32LE(P + 0,  In.Header.Magic);
    WriteU32LE(P + 4,  In.Header.Version);
    WriteU32LE(P + 8,  In.Header.LandblockId);
    WriteU32LE(P + 12, In.Header.SamplesPerSide);
    WriteU32LE(P + 16, In.Header.TextureLayerCount);
    WriteU32LE(P + 20, In.Header.Flags);
    WriteU32LE(P + 24, In.Header.Reserved[0]);
    WriteU32LE(P + 28, In.Header.Reserved[1]);

    std::uint8_t* HeightDst = P + sizeof(FAcIntermediateLandblockHeader);
    for (std::size_t I = 0; I < Cells; ++I)
    {
        WriteF32LE(HeightDst + I * sizeof(float), In.Heights[I]);
    }

    if (TexBytes > 0)
    {
        std::uint8_t* TexDst = HeightDst + Cells * sizeof(float);
        std::memcpy(TexDst, In.TextureIndices.data(), TexBytes);
    }

    return EAcLbParseStatus::OK;
}

} // namespace ac_ingest
