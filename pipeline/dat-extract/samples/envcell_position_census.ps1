# Reproducible EnvCell.Position census for ADR-0009 evidence.
# Enumerates EVERY indoor EnvCell in each sampled landblock (full census,
# not a biased first-N slice) and records its landblock-local Frame.Origin.
# World placement is composed per ACViewer PositionExtensions.GetWorldPos:
#   world = (lbX * 192 + Frame.X, lbY * 192 + Frame.Y, Frame.Z)
# Output is raw acdat data so every row in ADR-0009 is auditable.
#
# Usage:
#   ./envcell_position_census.ps1 -AcDat <path\acdat.exe> -DatDir "<dir>" -Out <file>
param(
    [string]$AcDat = "C:\Users\darin\repos\ac-unreal\pipeline\dat-extract\bin\Release\net8.0-windows\acdat.exe",
    [string]$DatDir = "C:\Turbine\Asheron's Call",
    [string[]]$Landblocks = @("8602", "A9B4", "01AE", "00D6"),
    [string]$Out = "$PSScriptRoot\envcell_position_census.txt"
)

$BlockLength = 192
$sb = New-Object System.Text.StringBuilder
function W($s) { [void]$sb.AppendLine($s) }

W "# EnvCell.Position full census - ADR-0009 auditable artifact"
W "# Generated: $(Get-Date -Format o)"
W "# acdat: $AcDat"
W "# DatDir: $DatDir"
W ""

foreach ($lb in $Landblocks) {
    $lbU = $lb.ToUpper()
    $lbX = [Convert]::ToInt32($lbU.Substring(0, 2), 16)
    $lbY = [Convert]::ToInt32($lbU.Substring(2, 2), 16)

    W "================================================================"
    W "LANDBLOCK 0x$lbU  (LbX=$lbX, LbY=$lbY)"
    W "----------------------------------------------------------------"

    # landblock classification (buildings/heights => dungeon vs interior)
    $info = & $AcDat landblock-info $DatDir $lb 2>$null | Where-Object { $_ -notmatch '^\[INFO\]' }
    $info | ForEach-Object { W "  $_" }

    # full enumeration: EnvCell ids are contiguous from 0x0100; probe upward
    # until we hit a run of misses (robust to small gaps). One query per cell,
    # reused for both existence and Position -> no biased "first-N" slice.
    W ""
    W "  Per-cell Frame.Origin (landblock-local) and composed world position:"
    W ("  {0,-12} {1,28} {2,30} {3}" -f "CellId", "Frame.Origin(x,y,z)", "World(x,y,z)", "InFootprint?")

    $minX = [double]::PositiveInfinity; $maxX = [double]::NegativeInfinity
    $minY = [double]::PositiveInfinity; $maxY = [double]::NegativeInfinity
    $minZ = [double]::PositiveInfinity; $maxZ = [double]::NegativeInfinity
    $inFoot = 0; $outFoot = 0; $n = 0
    $idx = 0x100; $misses = 0
    while ($misses -lt 32 -and $idx -le 0xFFFD) {
        $id = $lbU + ('{0:X4}' -f $idx)
        $cellOut = & $AcDat envcell-info $DatDir $id 2>$null
        $posLine = $cellOut | Where-Object { $_ -match 'Position:' } | Select-Object -First 1
        if ($posLine -match 'Position:\s*\(\s*([-0-9.]+),\s*([-0-9.]+),\s*([-0-9.]+)\)') {
            $misses = 0
            $fx = [double]$matches[1]; $fy = [double]$matches[2]; $fz = [double]$matches[3]
            $wx = $lbX * $BlockLength + $fx
            $wy = $lbY * $BlockLength + $fy
            $wz = $fz
            $isIn = ($fx -ge 0 -and $fx -le $BlockLength -and $fy -ge 0 -and $fy -le $BlockLength)
            if ($isIn) { $inFoot++ } else { $outFoot++ }
            if ($fx -lt $minX) { $minX = $fx }; if ($fx -gt $maxX) { $maxX = $fx }
            if ($fy -lt $minY) { $minY = $fy }; if ($fy -gt $maxY) { $maxY = $fy }
            if ($fz -lt $minZ) { $minZ = $fz }; if ($fz -gt $maxZ) { $maxZ = $fz }
            $n++
            W ("  {0,-12} ({1,8:F2},{2,9:F2},{3,8:F2})   ({4,10:F2},{5,11:F2},{6,8:F2})   {7}" -f "0x$id", $fx, $fy, $fz, $wx, $wy, $wz, $(if ($isIn) { "IN" } else { "OUT" }))
        }
        else {
            $misses++
        }
        $idx++
    }

    W ""
    W "  SUMMARY 0x${lbU}: cells_with_position=$n"
    W ("  Frame.Origin bbox: X[{0:F2}..{1:F2}] Y[{2:F2}..{3:F2}] Z[{4:F2}..{5:F2}]" -f $minX, $maxX, $minY, $maxY, $minZ, $maxZ)
    W "  Cells with Frame.Origin inside [0,$BlockLength] on BOTH X and Y: $inFoot"
    W "  Cells with Frame.Origin OUTSIDE that footprint: $outFoot"
    W ""
}

$sb.ToString() | Set-Content -Path $Out -Encoding UTF8
Write-Output "Wrote census to $Out"
