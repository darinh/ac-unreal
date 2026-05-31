@echo off
REM Runs UE in -game mode and captures a HighResShot of AcademyMap.
REM Bypasses PowerShell argument splitting woes -- .bat handles its
REM own quoting cleanly.
REM
REM Args (positional, optional):
REM   %1 = ResX (default 1280)
REM   %2 = ResY (default 720)
REM
REM Env var (optional):
REM   AC_EXTRA_CMDS = extra console commands to inject before HighResShot,
REM                   COMMA-separated. Read from env to avoid cmd.exe's
REM                   habit of splitting comma-containing positional args.
REM                   Example: "r.DynamicGlobalIlluminationMethod 0, ShowFlag.Lighting 0"
REM
REM Output: Saved\Screenshots\WindowsEditor\HighresScreenshot00000.png

setlocal
set RESX=%1
if "%RESX%"=="" set RESX=1280
set RESY=%2
if "%RESY%"=="" set RESY=720

set UE="C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
REM Derive project path from the .bat file's own location: <repo>\pipeline\ue-import\_run_highresshot.bat
REM -> <repo>\AcUnreal.uproject. This keeps the script portable across machines/checkouts.
set PROJ="%~dp0..\..\AcUnreal.uproject"
REM Map defaults to the academy; override with AC_MAP for isolated-cell inspection.
if "%AC_MAP%"=="" (set MAP=/Game/Academy/Maps/AcademyMap) else (set MAP=%AC_MAP%)

if "%AC_EXTRA_CMDS%"=="" (
    set CMDS=HighResShot %RESX%x%RESY%
) else (
    REM UE -ExecCmds uses COMMA as command separator, not semicolon.
    set CMDS=%AC_EXTRA_CMDS%, HighResShot %RESX%x%RESY%
)

echo [bat] CMDS=%CMDS%

%UE% %PROJ% %MAP% -game -ResX=%RESX% -ResY=%RESY% -ExecCmds="%CMDS%" -RenderOffscreen -NoLoadingScreen -nosplash -nocrashreports
