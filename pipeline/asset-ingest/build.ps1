# pipeline\asset-ingest\build.ps1
#
# Builds and runs the STANDALONE round-trip tests for the .aclb parser.
# Same dual-build pattern as pipeline\coord-transform\build.ps1: this
# script compiles the SAME .cpp the UE module compiles (in
# Source\AcUnreal\Private\AssetIngest\) directly with cl.exe — no UBT,
# no UE. That makes parser regressions fail immediately, independently
# of the UE module build state.

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$srcCore  = Join-Path $repoRoot 'Source\AcUnreal\Private\AssetIngest\AcIntermediateLandblock.cpp'
$incRoot  = Join-Path $repoRoot 'Source\AcUnreal\Public'
$testSrc  = Join-Path $PSScriptRoot 'tests\LandblockImporterTests.cpp'
$buildDir = Join-Path $PSScriptRoot 'build'
$outExe   = Join-Path $buildDir 'LandblockImporterTests.exe'

if (-not (Test-Path $srcCore))  { throw "Missing core source: $srcCore" }
if (-not (Test-Path $incRoot))  { throw "Missing include root: $incRoot" }
if (-not (Test-Path $testSrc))  { throw "Missing test source: $testSrc" }
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null

# Locate VS install with VC tools.
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw "vswhere not found at $vswhere; install VS Build Tools." }
$vsInstall = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsInstall) { throw "No VS install with VC.Tools.x86.x64 found." }
$vcvars = Join-Path $vsInstall 'VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path $vcvars)) { throw "vcvars64.bat not found at $vcvars" }

Write-Host "VS install: $vsInstall"
Write-Host "Compiling standalone tests with cl.exe under vcvars64..."

# /std:c++17 matches the core's requirements. The core is intentionally
# pre-C++20 to stay portable between the UE module build and this
# standalone build.
$compileLine = "cl /nologo /EHsc /std:c++17 /W4 /WX /permissive- /Zi " +
               "/I `"$incRoot`" `"$srcCore`" `"$testSrc`" " +
               "/Fo`"$buildDir\\`" /Fd`"$buildDir\\LandblockImporterTests.pdb`" " +
               "/link /OUT:`"$outExe`""

$cmdScript = "call `"$vcvars`" >nul && $compileLine"
Write-Host ">>> $cmdScript"
& $env:ComSpec /c $cmdScript
if ($LASTEXITCODE -ne 0) { throw "Compile failed with exit code $LASTEXITCODE" }

# Fixture determinism gate: regenerate the sample to a temp path and
# verify it byte-matches the committed file. Catches PowerShell-runtime
# drift in gen_sample.ps1 (e.g. floating-point dispatch differences
# between PS 5.1 and PS 7+) AND format-drift between the script and the
# C++ parser. If this fails, EITHER the script changed and the
# committed fixture is stale (re-run gen_sample.ps1 and commit), OR a
# new contributor produced different bytes on their machine and we
# need to investigate determinism.
$committedSample = Join-Path $repoRoot 'pipeline\asset-ingest\samples\synthetic_landblock_0xAA0B0000.aclb'
$genScript       = Join-Path $repoRoot 'pipeline\asset-ingest\gen_sample.ps1'
$tempSample      = Join-Path $buildDir 'regen_sample.aclb'
if ((Test-Path $committedSample) -and (Test-Path $genScript)) {
    Write-Host ""
    Write-Host "Verifying gen_sample.ps1 reproduces the committed fixture..."
    & $genScript -OutPath $tempSample | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "gen_sample.ps1 failed during verification" }
    $hashCommitted = (Get-FileHash -Algorithm SHA256 -Path $committedSample).Hash
    $hashRegen     = (Get-FileHash -Algorithm SHA256 -Path $tempSample).Hash
    if ($hashCommitted -ne $hashRegen) {
        Write-Host "Committed fixture SHA256:   $hashCommitted" -ForegroundColor Red
        Write-Host "Re-generated fixture SHA256: $hashRegen" -ForegroundColor Red
        throw "gen_sample.ps1 output does NOT match committed fixture. Either re-run gen_sample.ps1 and commit the new bytes (if the script change is intentional), or investigate why your runtime produces different bytes (a determinism break)."
    }
    Write-Host "  OK  committed fixture matches gen_sample.ps1 output (SHA256 $hashCommitted)"
    Remove-Item -Path $tempSample -ErrorAction SilentlyContinue
} else {
    Write-Host "  SKIP  fixture or generator missing; skipping determinism gate"
}

Write-Host ""
Write-Host "Running tests: $outExe `"$repoRoot`""
# Pass the repo root so the integration test can find the sample fixture.
& $outExe "$repoRoot"
$testExit = $LASTEXITCODE
Write-Host ""
if ($testExit -ne 0) {
    Write-Host "Tests FAILED with exit code $testExit" -ForegroundColor Red
    exit $testExit
}
Write-Host "Tests PASSED" -ForegroundColor Green
exit 0
