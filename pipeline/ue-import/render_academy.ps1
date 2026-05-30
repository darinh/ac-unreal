# =====================================================================
# render_academy.ps1
#
# Captures one screenshot of the AcademyMap from the current PlayerStart
# position, fully automated. Useful for an autonomous agent to verify
# rendering changes without a human in the loop.
#
# How it works:
#   1. Closes any stale UnrealEditor processes (they hold the project
#      file lock).
#   2. Cleans Saved/Screenshots/.
#   3. Launches UE in -game mode with -ExecCmds="HighResShot WxH" and
#      -RenderOffscreen. Roughly 90-120s to first screenshot for the
#      academy (1487 actors).
#   4. Watches Saved/Screenshots/WindowsEditor/ for the PNG to appear.
#   5. Force-kills UE (-game mode doesn't auto-exit after HighResShot).
#   6. Moves the PNG to pipeline/renders/<timestamp>/<name>.png and
#      updates pipeline/renders/latest.txt so the next agent turn can
#      find it.
#
# Tried-and-failed alternatives (documented so the next agent doesn't
# burn time re-attempting them):
#   - SceneCaptureComponent2D + RenderingLibrary.export_render_target:
#     in `-run=pythonscript` commandlet mode the rendering pipeline is
#     NOT ticked, so capture_scene() is a no-op and export silently
#     writes nothing. The function returns success.
#   - AutomationLibrary.take_high_res_screenshot in commandlet mode:
#     crashes inside UnrealEditor-FunctionalTesting.dll because the
#     functional-test subsystem isn't initialized.
#
# Multi-viewpoint capture is the next step — needs either an in-level
# C++ rig actor (AAcAcademyRenderRig that cycles cameras + HighResShots
# on tick) or one launch per viewpoint with PlayerStart moved between
# them (slow: ~2 min per viewpoint).
#
# Usage:
#   pwsh pipeline/ue-import/render_academy.ps1                 # default name
#   pwsh pipeline/ue-import/render_academy.ps1 -Name spawn_view
#   pwsh pipeline/ue-import/render_academy.ps1 -Name top -ResX 1920 -ResY 1080
# =====================================================================

[CmdletBinding()]
param(
    [string]$Name = "screenshot",
    [int]$ResX = 1280,
    [int]$ResY = 720,
    [int]$TimeoutSec = 180,
    # Optional viewpoint override. If provided, the PlayerStart is moved
    # to this UE world position + rotation before rendering. Otherwise
    # the existing PlayerStart is used.
    [Nullable[double]]$X = $null,
    [Nullable[double]]$Y = $null,
    [Nullable[double]]$Z = $null,
    [double]$Pitch = 0.0,
    [double]$Yaw = 0.0,
    [double]$Roll = 0.0,
    # Extra console commands to inject before HighResShot. Useful for
    # forcing exposure (e.g. "r.EyeAdaptationQuality 0, r.HDR.EnableHDROutput 0").
    # NOTE: separator is COMMA, not semicolon — UE -ExecCmds requires it.
    [string]$ExtraCmds = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$UeCmd = "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
$Project = Join-Path $RepoRoot "AcUnreal.uproject"
$MapPath = "/Game/Academy/Maps/AcademyMap"
$ScreenshotsDir = Join-Path $RepoRoot "Saved\Screenshots\WindowsEditor"
$RendersDir = Join-Path $RepoRoot "pipeline\renders"
$Timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
$OutDir = Join-Path $RendersDir $Timestamp

# Ensure ALL UE processes are terminated even if the script exits
# abnormally (terminating error / Ctrl-C / pipeline failure). Without
# this trap the .bat wrapper can leave UnrealEditor-Cmd.exe running
# in the background holding the project file lock.
function Stop-AllUE {
    Get-Process -Name "UnrealEditor*" -ErrorAction SilentlyContinue | ForEach-Object {
        try { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
}
trap {
    Write-Host "TRAP: script terminating — cleaning up any UE processes"
    Stop-AllUE
    break
}

# 1. Kill stale UE
Stop-AllUE
Start-Sleep -Seconds 1

# 2. Clean prior screenshots
if (Test-Path $ScreenshotsDir) {
    Remove-Item (Join-Path $ScreenshotsDir "*") -Force -Recurse -ErrorAction SilentlyContinue
}

# 2b. If a viewpoint override was supplied, move PlayerStart to that
#    position before rendering. Uses a Python commandlet (~5-15s).
if ($null -ne $X -and $null -ne $Y -and $null -ne $Z) {
    Write-Host "moving PlayerStart to ($X, $Y, $Z) pitch=$Pitch yaw=$Yaw..."
    $env:AC_VP_X = "$X"
    $env:AC_VP_Y = "$Y"
    $env:AC_VP_Z = "$Z"
    $env:AC_VP_PITCH = "$Pitch"
    $env:AC_VP_YAW = "$Yaw"
    $env:AC_VP_ROLL = "$Roll"
    $moveScript = Join-Path $PSScriptRoot "move_player_start.py"
    $UeCmdExe = "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
    # Capture log size BEFORE the move so we can scope the log scan
    # to lines added during this run — prevents picking up an old
    # "[move-ps] level saved" from a previous successful invocation.
    $logFile = Join-Path $RepoRoot "Saved\Logs\AcUnreal.log"
    $logSizeBefore = if (Test-Path $logFile) { (Get-Item $logFile).Length } else { 0 }
    $moveProc = Start-Process -FilePath $UeCmdExe -ArgumentList @(
        $Project, "-run=pythonscript", "-script=$moveScript",
        "-nop4", "-nosplash", "-stdout", "-RenderOffScreen", "-nocrashreports"
    ) -PassThru -NoNewWindow -Wait
    Stop-AllUE
    Start-Sleep -Seconds 1
    # Scope log scan to bytes written after the run started.
    $moveOk = $false
    if (Test-Path $logFile) {
        $logSizeAfter = (Get-Item $logFile).Length
        if ($logSizeAfter -gt $logSizeBefore) {
            $stream = [System.IO.File]::Open($logFile, 'Open', 'Read', 'ReadWrite')
            try {
                $stream.Seek($logSizeBefore, 'Begin') | Out-Null
                $reader = New-Object System.IO.StreamReader($stream)
                $newLogText = $reader.ReadToEnd()
                if ($newLogText -match '\[move-ps\] level saved') { $moveOk = $true }
            } finally { $stream.Dispose() }
        }
    }
    if ($moveProc.ExitCode -ne 0 -or -not $moveOk) {
        Write-Host "ERROR: move_player_start failed (exit=$($moveProc.ExitCode) logOk=$moveOk)"
        exit 2
    }
    Write-Host "PlayerStart moved + level saved"
}

# 3. Launch the .bat. PowerShell's argument splitter mangles UE's
#    `-ExecCmds="HighResShot 1280x720"` (it sees the space and splits).
#    A .bat sidesteps this — cmd.exe parses %1 %2 ... correctly.
$bat = Join-Path $PSScriptRoot "_run_highresshot.bat"
Write-Host "launching UE -game via $bat (timeout ${TimeoutSec}s)..."
$batArgs = @($ResX.ToString(), $ResY.ToString())
if ($ExtraCmds -ne "") { $batArgs += $ExtraCmds }
$proc = Start-Process -FilePath $bat -ArgumentList $batArgs -PassThru -NoNewWindow

# 4. Watch for the screenshot to appear and finish writing. UE writes
#    HighresScreenshot00000.png to Saved/Screenshots/WindowsEditor/.
#    We require TWO consecutive identical sizes ≥1KB before considering
#    the file complete — otherwise we can kill UE mid-write and end up
#    with a truncated PNG.
$found = $null
$elapsed = 0
$lastSize = -1
$stableCount = 0
while ($elapsed -lt $TimeoutSec) {
    Start-Sleep -Seconds 5
    $elapsed += 5
    if (Test-Path $ScreenshotsDir) {
        $candidate = Get-ChildItem $ScreenshotsDir -Filter "HighresScreenshot*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($candidate -and $candidate.Length -ge 1024) {
            if ($candidate.Length -eq $lastSize) {
                $stableCount++
                if ($stableCount -ge 2) {
                    $found = $candidate
                    Write-Host "[${elapsed}s] screenshot stable: $($found.Name) ($($found.Length) bytes)"
                    break
                }
                Write-Host "[${elapsed}s] screenshot present + stable poll $stableCount/2 ($($candidate.Length) bytes)"
            } else {
                Write-Host "[${elapsed}s] screenshot growing: $($candidate.Length) bytes (was $lastSize)"
                $lastSize = $candidate.Length
                $stableCount = 0
            }
            continue
        }
    }
    Write-Host "[${elapsed}s] waiting for screenshot..."
}

# 5. Kill UE — -game mode doesn't auto-exit after HighResShot.
Stop-AllUE
if (-not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}

if (-not $found) {
    Write-Host "ERROR: no stable screenshot produced in ${TimeoutSec}s"
    exit 1
}

# 6. Move screenshot to timestamped output dir.
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$target = Join-Path $OutDir "$Name.png"
Move-Item $found.FullName $target -Force
Write-Host "wrote $target"

# Update latest pointer so the agent can find the most recent batch.
$relTarget = (Resolve-Path -Path $target -Relative).TrimStart(".\")
Set-Content -Path (Join-Path $RendersDir "latest.txt") -Value $relTarget.Replace("\", "/") -NoNewline
exit 0
