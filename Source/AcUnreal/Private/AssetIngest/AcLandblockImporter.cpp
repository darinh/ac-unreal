// =====================================================================
// AcLandblockImporter.cpp
//
// UE-side thin wrapper. All parsing logic lives in
// AssetIngest/AcIntermediateLandblock.h/.cpp. Field mapping only.
// =====================================================================
#include "AssetIngest/AcLandblockImporter.h"

#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

EAcLbParseStatusBP UAcLandblockImporter::StatusToBP(ac_ingest::EAcLbParseStatus Core)
{
	switch (Core)
	{
		case ac_ingest::EAcLbParseStatus::OK:                       return EAcLbParseStatusBP::OK;
		case ac_ingest::EAcLbParseStatus::BufferTooSmall:           return EAcLbParseStatusBP::BufferTooSmall;
		case ac_ingest::EAcLbParseStatus::BadMagic:                 return EAcLbParseStatusBP::BadMagic;
		case ac_ingest::EAcLbParseStatus::UnsupportedVersion:       return EAcLbParseStatusBP::UnsupportedVersion;
		case ac_ingest::EAcLbParseStatus::InvalidSamplesPerSide:    return EAcLbParseStatusBP::InvalidSamplesPerSide;
		case ac_ingest::EAcLbParseStatus::InvalidTextureLayerCount: return EAcLbParseStatusBP::InvalidTextureLayerCount;
		case ac_ingest::EAcLbParseStatus::NonzeroFlagsReserved:     return EAcLbParseStatusBP::NonzeroFlagsReserved;
		case ac_ingest::EAcLbParseStatus::NonzeroReservedField:     return EAcLbParseStatusBP::NonzeroReservedField;
		case ac_ingest::EAcLbParseStatus::SizeMismatch:             return EAcLbParseStatusBP::SizeMismatch;
		case ac_ingest::EAcLbParseStatus::NonFiniteHeight:          return EAcLbParseStatusBP::NonFiniteHeight;
		case ac_ingest::EAcLbParseStatus::InvalidLandblockId:       return EAcLbParseStatusBP::InvalidLandblockId;
	}
	// New core enum value not yet mirrored — log loudly so the next
	// developer fixes the mapping.
	UE_LOG(LogTemp, Error,
		TEXT("UAcLandblockImporter::StatusToBP: unknown core status %d; treating as BadMagic"),
		static_cast<int32>(Core));
	return EAcLbParseStatusBP::BadMagic;
}

FAcIntermediateLandblockBP UAcLandblockImporter::CoreToBP(const ac_ingest::FAcIntermediateLandblock& Core)
{
	FAcIntermediateLandblockBP Out;
	// LandblockId is uint32 in the core; widen to int64 so the high bit
	// round-trips losslessly through Blueprint integer types.
	Out.Header.LandblockId       = static_cast<int64>(Core.Header.LandblockId);
	Out.Header.SamplesPerSide    = static_cast<int32>(Core.Header.SamplesPerSide);
	Out.Header.TextureLayerCount = static_cast<int32>(Core.Header.TextureLayerCount);
	Out.Header.FormatVersion     = static_cast<int32>(Core.Header.Version);

	Out.Heights.SetNumUninitialized(static_cast<int32>(Core.Heights.size()));
	if (!Core.Heights.empty())
	{
		FMemory::Memcpy(Out.Heights.GetData(),
		                Core.Heights.data(),
		                Core.Heights.size() * sizeof(float));
	}

	Out.TextureIndices.SetNumUninitialized(static_cast<int32>(Core.TextureIndices.size()));
	if (!Core.TextureIndices.empty())
	{
		FMemory::Memcpy(Out.TextureIndices.GetData(),
		                Core.TextureIndices.data(),
		                Core.TextureIndices.size());
	}
	return Out;
}

EAcLbParseStatusBP UAcLandblockImporter::ParseLandblockBytes(const TArray<uint8>& Bytes,
                                                             FAcIntermediateLandblockBP& OutLandblock)
{
	OutLandblock = FAcIntermediateLandblockBP{};

	ac_ingest::FAcIntermediateLandblock CoreLb;
	const ac_ingest::EAcLbParseStatus CoreStatus = ac_ingest::ParseLandblock(
		Bytes.GetData(),
		static_cast<std::size_t>(Bytes.Num()),
		CoreLb);

	const EAcLbParseStatusBP BPStatus = StatusToBP(CoreStatus);
	if (BPStatus == EAcLbParseStatusBP::OK)
	{
		OutLandblock = CoreToBP(CoreLb);
	}
	else
	{
		UE_LOG(LogTemp, Warning,
			TEXT("UAcLandblockImporter::ParseLandblockBytes: parse failed (%s)"),
			*FString(ac_ingest::ToString(CoreStatus)));
	}
	return BPStatus;
}

EAcLbParseStatusBP UAcLandblockImporter::LoadLandblockFromFile(const FString& FilePath,
                                                                FAcIntermediateLandblockBP& OutLandblock)
{
	OutLandblock = FAcIntermediateLandblockBP{};

	if (!FPaths::FileExists(FilePath))
	{
		UE_LOG(LogTemp, Warning,
			TEXT("UAcLandblockImporter::LoadLandblockFromFile: file not found: %s"),
			*FilePath);
		return EAcLbParseStatusBP::FileNotFound;
	}

	TArray<uint8> Bytes;
	if (!FFileHelper::LoadFileToArray(Bytes, *FilePath))
	{
		UE_LOG(LogTemp, Warning,
			TEXT("UAcLandblockImporter::LoadLandblockFromFile: FFileHelper failed: %s"),
			*FilePath);
		return EAcLbParseStatusBP::FileNotFound;
	}

	return ParseLandblockBytes(Bytes, OutLandblock);
}
