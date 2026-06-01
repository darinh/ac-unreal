# =====================================================================
# render_firstroom_sweep.ps1
#
# THE FIRST-ROOM VERIFICATION FORMULA.
#
# Renders the Aluvian Training Academy first room (EnvCell 0x860201AD,
# UE world origin -3000,1000,0; interior ~ X[-3500,-2500] Y[500,1500]
# Z[0,600]) from a FIXED, documented set of viewpoints that together
# cover EVERY surface of the room shell:
#
#   wall_n / wall_e / wall_s / wall_w  - the four walls (yaw 0/90/180/270)
#   ceiling                            - look up   (pitch +75)
#   floor                              - look down (pitch -75)
#
# All six land in ONE timestamped folder so the room can be evaluated as
# a composed whole and diffed against the reference answer key in
# ~/repos/ac-screenshots/ (the "view from center room facing <corner>"
# set). This is intentionally re-runnable: same cameras every time, so a
# regression in any surface is visible by comparing the same-named file.
#
# Each viewpoint is one render_academy.ps1 invocation (move PlayerStart +
# -game HighResShot, ~2 min each). Sequential by necessity: render_academy
# kills all UnrealEditor processes on entry, so they cannot overlap.
#
# Usage:
#   pwsh pipeline/ue-import/render_firstroom_sweep.ps1
#   pwsh pipeline/ue-import/render_firstroom_sweep.ps1 -ResX 1920 -ResY 1080
# =====================================================================
[CmdletBinding()]
param(
    [int]$ResX = 1280,
    [int]$ResY = 720,
    # Level to render + room-center camera position. Defaults to the first
    # room's location inside the full academy; pass the isolated shell level
    # (/Game/Academy/Maps/FirstRoomTest, centered at origin) for fast renders.
    [string]$Level = "/Game/Academy/Maps/AcademyMap",
    [double]$CX = -3000,
    [double]$CY = 1000,
    [double]$CZ = 250
)
$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$RendersDir = Join-Path $RepoRoot "pipeline\renders"
$Render = Join-Path $PSScriptRoot "render_academy.ps1"
$Stamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
$SweepDir = Join-Path $RendersDir "firstroom_sweep_$Stamp"
New-Item -ItemType Directory -Force -Path $SweepDir | Out-Null

# Eye at room center, Z=250 (~2.5m) so floor (Z0) and ceiling (Z600) are
# both reachable in the pitched views.
$cx = -3000; $cy = 1000; $cz = 250
$views = @(
    @{ n = "wall_n";  yaw = 0;   pitch = 0   },
    @{ n = "wall_e";  yaw = 90;  pitch = 0   },
    @{ n = "wall_s";  yaw = 180; pitch = 0   },
    @{ n = "wall_w";  yaw = 270; pitch = 0   },
    @{ n = "ceiling"; yaw = 0;   pitch = 75  },
    @{ n = "floor";   yaw = 0;   pitch = -75 }
)

$results = @()
foreach ($v in $views) {
    Write-Host "=== rendering $($v.n) (yaw=$($v.yaw) pitch=$($v.pitch)) ==="
    & pwsh -NoProfile -File $Render -Name $v.n -ResX $ResX -ResY $ResY `
        -X $cx -Y $cy -Z $cz -Yaw $v.yaw -Pitch $v.pitch
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: render of $($v.n) exited $LASTEXITCODE"
        $results += [pscustomobject]@{ view = $v.n; ok = $false; path = "" }
        continue
    }
    # render_academy writes the path of the produced PNG to latest.txt.
    $latest = (Get-Content (Join-Path $RendersDir "latest.txt") -Raw).Trim()
    $src = Join-Path $RepoRoot ($latest -replace "/", "\")
    $dst = Join-Path $SweepDir "$($v.n).png"
    if (Test-Path $src) {
        Copy-Item $src $dst -Force
        Write-Host "  -> $dst"
        $results += [pscustomobject]@{ view = $v.n; ok = $true; path = $dst }
    } else {
        Write-Host "  WARN: expected $src not found"
        $results += [pscustomobject]@{ view = $v.n; ok = $false; path = "" }
    }
}

Write-Host ""
Write-Host "=== SWEEP COMPLETE: $SweepDir ==="
$results | ForEach-Object { Write-Host ("  {0,-8} ok={1} {2}" -f $_.view, $_.ok, $_.path) }
Set-Content -Path (Join-Path $RendersDir "latest_sweep.txt") -Value $SweepDir -NoNewline
