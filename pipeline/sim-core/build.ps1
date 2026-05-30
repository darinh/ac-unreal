# pipeline\sim-core\build.ps1
#
# Builds and runs the STANDALONE tests for the Phase 2 sim core.
# Same dual-build pattern as coord-transform / asset-ingest: compiles
# the SAME .cpp files the UE module compiles (from Source\AcUnreal\
# Private\SimCore\) directly with cl.exe — no UBT, no UE. Catches sim
# regressions fast, independent of UE build state.

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$srcDir   = Join-Path $repoRoot 'Source\AcUnreal\Private\SimCore'
$incRoot  = Join-Path $repoRoot 'Source\AcUnreal\Public'
$testSrc  = Join-Path $PSScriptRoot 'tests\SimCoreTests.cpp'
$buildDir = Join-Path $PSScriptRoot 'build'
$outExe   = Join-Path $buildDir 'SimCoreTests.exe'

if (-not (Test-Path $srcDir))  { throw "Missing source dir: $srcDir" }
if (-not (Test-Path $incRoot)) { throw "Missing include root: $incRoot" }
if (-not (Test-Path $testSrc)) { throw "Missing test source: $testSrc" }
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null

# All .cpp under Source\AcUnreal\Private\SimCore that are pure C++17
# (no UE dependencies). The UE-bound files (AcCharacterMovementComponent,
# AcMovementParamsDataAsset, AcSimulationSubsystem) are excluded — they
# only build under UBT because they include UE headers.
$pureCppFiles = @(
    Join-Path $srcDir 'AcSimMath.cpp'
    Join-Path $srcDir 'AcFixedTimestep.cpp'
)
foreach ($f in $pureCppFiles) {
    if (-not (Test-Path $f)) { throw "Missing pure-C++ source: $f" }
}
$srcArg = ($pureCppFiles | ForEach-Object { "`"$_`"" }) -join ' '

# Locate VS install with VC tools.
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw "vswhere not found at $vswhere" }
$vsInstall = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsInstall) { throw "No VS install with VC.Tools.x86.x64 found." }
$vcvars = Join-Path $vsInstall 'VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path $vcvars)) { throw "vcvars64.bat not found at $vcvars" }

Write-Host "VS install: $vsInstall"
Write-Host "Compiling sim-core standalone tests with cl.exe..."

# /std:c++17 matches the core's portability target.
$compileLine = "cl /nologo /EHsc /std:c++17 /W4 /WX /permissive- /Zi " +
               "/I `"$incRoot`" $srcArg `"$testSrc`" " +
               "/Fo`"$buildDir\\`" /Fd`"$buildDir\\SimCoreTests.pdb`" " +
               "/link /OUT:`"$outExe`""

$cmdScript = "call `"$vcvars`" >nul && $compileLine"
Write-Host ">>> $cmdScript"
& $env:ComSpec /c $cmdScript
if ($LASTEXITCODE -ne 0) { throw "Compile failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Running tests: $outExe"
& $outExe
$testExit = $LASTEXITCODE
Write-Host ""
if ($testExit -ne 0) {
    Write-Host "Tests FAILED with exit code $testExit" -ForegroundColor Red
    exit $testExit
}
Write-Host "Tests PASSED" -ForegroundColor Green
exit 0
