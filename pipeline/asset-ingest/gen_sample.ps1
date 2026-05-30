# pipeline\asset-ingest\gen_sample.ps1
#
# Deterministically generates the synthetic landblock test fixture at
# samples\synthetic_landblock_0xAA0B0000.aclb (or to -OutPath). The
# bytes are stable across runs AND across PowerShell runtimes — see
# the heightfield formula below.
#
# This script implements the v1 format (FORMAT.md). If the format
# changes, bump kFormatVersion below, regenerate, and commit the new
# sample alongside the format bump. build.ps1 verifies the committed
# bytes still match the generator output, so format drift is caught in
# the test rig.
#
# Synthetic content: 9x9 heightfield (a saddle shape computed via
# integer + power-of-2 fraction arithmetic — every operation is exact
# in IEEE-754 single precision; no transcendentals, so the output is
# bit-identical regardless of the PS / .NET runtime's libm) plus one
# texture layer with a checkerboard index pattern. Heights are a mix
# of positive and negative values to exercise sign handling.

#requires -Version 7.0

[CmdletBinding()]
param(
    # Optional output path. Defaults to samples/synthetic_landblock_0xAA0B0000.aclb.
    [string] $OutPath = (Join-Path $PSScriptRoot 'samples\synthetic_landblock_0xAA0B0000.aclb')
)

$ErrorActionPreference = "Stop"

$kMagic           = 0x424C4341  # 'ACLB' little-endian
$kFormatVersion   = 1
# PowerShell parses high-bit hex literals as Int32, which overflows for
# 0xAA0B0000. Parse explicitly as UInt32 to avoid the signed conversion.
$kLandblockId     = [UInt32]::Parse('AA0B0000', [System.Globalization.NumberStyles]::HexNumber)  # LBx=0xAA, LBy=0x0B
$kSamplesPerSide  = 9
$kTextureLayers   = 1

$outDir = Split-Path -Parent $OutPath
if (-not [string]::IsNullOrEmpty($outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$ms = [System.IO.MemoryStream]::new()
$bw = [System.IO.BinaryWriter]::new($ms)

# Header (32 bytes). BinaryWriter writes little-endian; static-asserted
# in the C++ parser via the endianness guard.
$bw.Write([uint32]$kMagic)
$bw.Write([uint32]$kFormatVersion)
$bw.Write([uint32]$kLandblockId)
$bw.Write([uint32]$kSamplesPerSide)
$bw.Write([uint32]$kTextureLayers)
$bw.Write([uint32]0)   # Flags
$bw.Write([uint32]0)   # Reserved[0]
$bw.Write([uint32]0)   # Reserved[1]

# Heights: row-major (Y outer, X inner). Saddle shape — closed-form
# polynomial in (dx, dy) using only integer + power-of-2 fraction
# arithmetic. With dx, dy in [-4, 4]:
#   max h ≈ +7.0 at (8, 4); min h ≈ -5.0 at (4, 8).
# Every operand is either an integer or a small power-of-2 fraction
# (0.5, 0.25, 0.125), so the entire computation is exact in IEEE-754
# binary floating point on any conforming runtime.
$mid = [int]([math]::Floor($kSamplesPerSide / 2))
for ($y = 0; $y -lt $kSamplesPerSide; $y++) {
    for ($x = 0; $x -lt $kSamplesPerSide; $x++) {
        $dx = $x - $mid
        $dy = $y - $mid
        $h = ($dx * $dx * 0.5) - ($dy * $dy * 0.25) + ($dx * $dy * 0.125) - 1.0
        $bw.Write([float]$h)
    }
}

# Texture layer 0: checkerboard of indices 0 and 1.
for ($y = 0; $y -lt $kSamplesPerSide; $y++) {
    for ($x = 0; $x -lt $kSamplesPerSide; $x++) {
        $idx = (($x + $y) % 2)
        $bw.Write([byte]$idx)
    }
}

$bw.Flush()
$bytes = $ms.ToArray()
$bw.Dispose()
$ms.Dispose()

# Expected: 32 + 9*9*4 + 9*9*1 = 32 + 324 + 81 = 437
$expectedSize = 32 + ($kSamplesPerSide * $kSamplesPerSide * 4) + ($kSamplesPerSide * $kSamplesPerSide * $kTextureLayers)
if ($bytes.Length -ne $expectedSize) {
    throw "Generated $($bytes.Length) bytes; expected $expectedSize. Format-drift bug."
}

[System.IO.File]::WriteAllBytes($OutPath, $bytes)
Write-Host "Wrote $($bytes.Length) bytes to $OutPath"
Write-Host ("Magic   = 0x{0:X8}" -f $kMagic)
Write-Host "Version = $kFormatVersion"
$lbx = ($kLandblockId -shr 24) -band 0xFF
$lby = ($kLandblockId -shr 16) -band 0xFF
Write-Host ("LbId    = 0x{0:X8} (LBx={1}, LBy={2})" -f $kLandblockId, $lbx, $lby)
Write-Host "Side    = $kSamplesPerSide x $kSamplesPerSide"
Write-Host "Layers  = $kTextureLayers"
