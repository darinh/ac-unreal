# run_import.ps1
#
# Wrapper that launches UnrealEditor-Cmd.exe with the Python import
# script so you don't have to remember the exact command line. Builds
# the Editor target first (if needed), then runs the script.
#
# Usage:
#   cd C:\Users\darin\repos\ac-unreal
#   pwsh pipeline\ue-import\run_import.ps1
#
# Optional environment overrides (rare):
#   $env:AC_LAYOUT_JSON = "C:\path\to\academy_8602_layout.json"
#   $env:AC_OBJ_DIR     = "C:\path\to\out\academy_8602"
#   $env:UE_EDITOR_CMD  = "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$uproject = Join-Path $repoRoot 'AcUnreal.uproject'
$script   = Join-Path $PSScriptRoot 'import_academy.py'
$logFile  = Join-Path $repoRoot 'pipeline\ue-import\last-run.log'

$ueCmd = if ($env:UE_EDITOR_CMD) { $env:UE_EDITOR_CMD } else {
    'C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
}

if (-not (Test-Path $ueCmd))  { throw "UnrealEditor-Cmd not found at: $ueCmd" }
if (-not (Test-Path $uproject)) { throw "uproject not found at: $uproject" }
if (-not (Test-Path $script))   { throw "python script not found at: $script" }

Write-Host "Launching:"
Write-Host "  $ueCmd"
Write-Host "    `"$uproject`""
Write-Host "    -run=pythonscript -script=`"$script`""
Write-Host "    -log -unattended -nop4 -nosplash -stdout -nullrhi"
Write-Host ""
Write-Host "(log -> $logFile)"
Write-Host ""

# -nullrhi makes the import headless (no GPU/window). Removes interactive
# preview but bulk import doesn't need a viewport. Drop the flag if you
# need to debug visually.
# -RenderOffScreen initializes an offscreen Slate app so headless asset
# creation paths that touch the ContentBrowser don't crash. -nullrhi
# (the more aggressive headless flag) does NOT work — Interchange and
# Material expression creation crash without a Slate app.
# -nocrashreports kills the modal dialog that would otherwise block
# automation when something goes wrong.
& $ueCmd `
    "$uproject" `
    -run=pythonscript `
    "-script=$script" `
    -log `
    -unattended `
    -nop4 `
    -nosplash `
    -stdout `
    -RenderOffScreen `
    -nocrashreports `
    2>&1 | Tee-Object -FilePath $logFile

if ($LASTEXITCODE -ne 0) {
    Write-Warning "UnrealEditor-Cmd exited with code $LASTEXITCODE — see $logFile"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Import script finished. Open the project in UE5 Editor and load:"
Write-Host "  /Game/Academy/Maps/AcademyMap"
