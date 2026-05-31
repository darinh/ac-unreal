# pipeline\coord-transform\build.ps1
#
# Builds and runs the STANDALONE round-trip tests for the canonical
# AC<->UE coordinate transform. Sources the SAME .cpp the UE module
# compiles, from Source\AcUnreal\Private\CoordCore\, so this is the
# authoritative regression gate for the core math — independent of UBT.
#
# Requires: Visual Studio 2022 Build Tools with VC.Tools.x86.x64 +
# Windows 10/11 SDK. Discovered via vswhere; cl.exe is invoked under
# vcvars64.bat in a single cmd.exe process (vcvars sets PATH / INCLUDE /
# LIB that must persist for cl).

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$srcCore  = Join-Path $repoRoot 'Source\AcUnreal\Private\CoordCore\CoordTransform.cpp'
$incRoot  = Join-Path $repoRoot 'Source\AcUnreal\Public'
$testSrc  = Join-Path $PSScriptRoot 'tests\CoordTransformTests.cpp'
$buildDir = Join-Path $PSScriptRoot 'build'
$outExe   = Join-Path $buildDir 'CoordTransformTests.exe'

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

# Build + run in a single cmd.exe process so vcvars's PATH/INCLUDE/LIB persists
# through the cl invocation. Use /std:c++17 to match the core's requirements
# (the core is intentionally pre-C++20 to maximize portability across both
# the UE module build and this standalone build).
$compileLine = "cl /nologo /EHsc /std:c++17 /W4 /WX /permissive- /Zi " +
               "/I `"$incRoot`" `"$srcCore`" `"$testSrc`" " +
               "/Fo`"$buildDir\\`" /Fd`"$buildDir\\CoordTransformTests.pdb`" " +
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
