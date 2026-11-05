@echo off
setlocal
rem Pack the Ocarina of Time .nup into an iPhone IPA with D:\nxw
rem Finds the .nup in Downloads\*DUMP (no Chinese characters needed in this file)
set "NUP="
for /d %%D in ("%USERPROFILE%\Downloads\*DUMP") do for %%F in ("%%D\*.nup") do set "NUP=%%F"
if not defined NUP (
  echo Could not find the .nup file under %USERPROFILE%\Downloads\*DUMP
  pause
  exit /b 1
)
echo NUP: "%NUP%"

rem Work folder and IPA on C: with an English-only path
set "OUT=C:\Games\OoT"
if not exist "%OUT%" mkdir "%OUT%"

cd /d D:\nxw
echo.
echo === 1/2 Checking tools (doctor.py) ===
python win\doctor.py
if errorlevel 1 (
  echo doctor.py reported a problem. Copy the lines above to Claude.
  pause
  exit /b 1
)

echo.
echo === 2/2 Building IPA ===
python win\build_ipa_windows.py "%NUP%" --work-dir "%OUT%\build" -o "%OUT%\OoT.ipa" --entitlements --split-data --allow-other-metal --progress lines
set "RC=%errorlevel%"
echo.
if "%RC%"=="0" (
  echo Done. IPA and data folder are in %OUT%
) else (
  echo Build failed, exit code %RC%. Logs: %OUT%\build\logs
)
pause
