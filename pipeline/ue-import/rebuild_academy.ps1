# =====================================================================
# rebuild_academy.ps1
#
# Re-runs all the spawn scripts in sequence to rebuild AcademyMap
# after the move_player_start.py disaster wiped 1487 actors.
#
# Each script is run in its own headless UE commandlet. Between runs
# we kill any lingering UE process (some hang on shutdown due to
# LiveCoding pipe errors). Total wall-clock: ~5-15 min depending on
# cache warmth.
#
# Safe to re-run: every spawn script is idempotent (skips assets that
# already exist + clears prior actors with matching label/tag prefix).
# =====================================================================

[CmdletBinding()]
param(
    [int]$ScriptTimeoutSec = 600
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$UeCmd = "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
$Project = Join-Path $RepoRoot "AcUnreal.uproject"

# Order matters: cells first (level skeleton), then everything that
# attaches to cells, then lighting/PPV, then PlayerStart.
$Scripts = @(
    "import_academy.py",       # 568 cells + baseline lighting (DL, SL, PPV)
    "import_statics.py",       # 644 props
    "import_lights.py",        # 132 PointLights + FireFlicker tags
    "import_npcs.py",          # 22 NPC/door/sign/chest/portal instances
    "add_player_start.py",     # PlayerStart at canonical spawn
    "add_sky_atmosphere.py",   # SkyAtmosphere actor (needs to exist for SkyLight capture)
    "restore_lighting.py",     # tune SkyLight + DirectionalLight after baseline
    "brighten_academy.py"      # 10x PointLight intensity + manual exposure
)

$Results = @()
foreach ($script in $Scripts) {
    Write-Host ""
    Write-Host "================================================================"
    Write-Host "=== Running $script ==="
    Write-Host "================================================================"
    $scriptPath = Join-Path $PSScriptRoot $script
    if (-not (Test-Path $scriptPath)) {
        Write-Host "MISSING: $scriptPath"
        $Results += [PSCustomObject]@{Script=$script; Status="MISSING"; Seconds=0}
        continue
    }
    Get-Process -Name "UnrealEditor*" -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
    $start = Get-Date
    $p = Start-Process -FilePath $UeCmd -ArgumentList @(
        $Project,
        "-run=pythonscript",
        "-script=$scriptPath",
        "-nop4",
        "-nosplash",
        "-stdout",
        "-RenderOffScreen",
        "-nocrashreports"
    ) -PassThru -NoNewWindow
    $waited = 0
    while ($waited -lt $ScriptTimeoutSec -and -not $p.HasExited) {
        Start-Sleep -Seconds 10
        $waited += 10
        Write-Host "  [${waited}s] $script still running..."
    }
    $elapsed = ((Get-Date) - $start).TotalSeconds
    $status = "OK"
    if (-not $p.HasExited) {
        Write-Host "  TIMEOUT after ${waited}s — force-killing"
        $status = "TIMEOUT"
    }
    Get-Process -Name "UnrealEditor*" -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
    # Heuristic: check the log for any LogPython errors from this script.
    $logFile = Join-Path $RepoRoot "Saved\Logs\AcUnreal.log"
    $errors = Select-String -Path $logFile -Pattern "LogPython: Error" -ErrorAction SilentlyContinue | Select-Object -Last 5
    if ($errors -and $status -eq "OK") {
        $status = "PYTHON_ERROR"
        Write-Host "  Python errors detected:"
        $errors | ForEach-Object { Write-Host "    $($_.Line)" }
    }
    Write-Host "  $script finished in ${elapsed}s status=$status"
    $Results += [PSCustomObject]@{Script=$script; Status=$status; Seconds=[int]$elapsed}
}

Write-Host ""
Write-Host "================================================================"
Write-Host "=== Recovery summary ==="
Write-Host "================================================================"
$Results | Format-Table -AutoSize
