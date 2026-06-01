# Reproducible EnvCell.Position census for ADR-0009 evidence.
# For each sampled landblock this calls `acdat dump-envcell-positions`, which in
# a SINGLE process enumerates EVERY indoor EnvCell that actually exists in the
# Cell DAT (real file keys 0x0100..0xFFFD — full census, not a biased first-N
# slice, not a probe) and records its landblock-local Frame.Origin.
# World placement is composed per ACViewer PositionExtensions.GetWorldPos:
#   world = (lbX * 192 + Frame.X, lbY * 192 + Frame.Y, Frame.Z)
# The footprint test (Frame.X,Y in [0,192]) is computed in C# so every row in
# ADR-0009 is auditable from raw acdat output.
#
# Sample is stratified by landblock type:
#   * building-interior blocks (LandblockInfo.Buildings > 0): A9B4, 1203, DA55,
#     8851, C6A9, 0503, 0408, 0604  (span 1..49 buildings, 2..251 cells)
#   * zero-building blocks (Buildings == 0; necessary-not-sufficient for an
#     ACViewer "dungeon"): 8602, 01AE, 00D6
# Building-interior candidates were found with `acdat find-building-blocks`.
#
# Usage:
#   ./envcell_position_census.ps1 -AcDat <path\acdat.exe> -DatDir "<dir>" -Out <file>
param(
    [string]$AcDat = "C:\Users\darin\repos\ac-unreal\pipeline\dat-extract\bin\Release\net8.0-windows\acdat.exe",
    [string]$DatDir = "C:\Turbine\Asheron's Call",
    [string[]]$Landblocks = @("A9B4", "1203", "DA55", "8851", "C6A9", "0503", "0408", "0604", "8602", "01AE", "00D6"),
    [string]$Out = "$PSScriptRoot\envcell_position_census.txt"
)

$sb = New-Object System.Text.StringBuilder
function W($s) { [void]$sb.AppendLine($s) }

W "# EnvCell.Position full census - ADR-0009 auditable artifact"
W "# Generated: $(Get-Date -Format o)"
W "# acdat: $AcDat"
W "# DatDir: $DatDir"
W "# One 'acdat dump-envcell-positions' call per landblock (single-process full census)."
W ""

foreach ($lb in $Landblocks) {
    $blockOut = & $AcDat dump-envcell-positions $DatDir $lb 2>$null | Where-Object { $_ -notmatch '^\[INFO\]' }
    $blockOut | ForEach-Object { W $_ }
}

[System.IO.File]::WriteAllText($Out, $sb.ToString(), [System.Text.Encoding]::UTF8)
Write-Output "Wrote census to $Out"
