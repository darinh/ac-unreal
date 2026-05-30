@echo off
REM Runs UE in -game mode and captures a HighResShot of AcademyMap.
REM Bypasses PowerShell argument splitting woes — .bat handles its
REM own quoting cleanly.
REM
REM Args (positional, optional):
REM   %1 = ResX (default 1280)
REM   %2 = ResY (default 720)
REM   %3 = extra console commands prepended to HighResShot, COMMA-separated
REM        e.g. "r.EyeAdaptationQuality 0, r.HDR.EnableHDROutput 0"
REM
REM Output: Saved\Screenshots\WindowsEditor\HighresScreenshot00000.png

setlocal
set RESX=%1
if "%RESX%"=="" set RESX=1280
set RESY=%2
if "%RESY%"=="" set RESY=720
set EXTRA=%~3

set UE="C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
REM Derive project path from the .bat file's own location: <repo>\pipeline\ue-import\_run_highresshot.bat
REM -> <repo>\AcUnreal.uproject. This keeps the script portable across machines/checkouts.
set PROJ="%~dp0..\..\AcUnreal.uproject"
set MAP=/Game/Academy/Maps/AcademyMap

if "%EXTRA%"=="" (
    set CMDS=HighResShot %RESX%x%RESY%
) else (
    REM UE -ExecCmds uses COMMA as command separator, not semicolon.
    set CMDS=%EXTRA%, HighResShot %RESX%x%RESY%
)

%UE% %PROJ% %MAP% -game -ResX=%RESX% -ResY=%RESY% -ExecCmds="%CMDS%" -RenderOffscreen -NoLoadingScreen -nosplash -nocrashreports
