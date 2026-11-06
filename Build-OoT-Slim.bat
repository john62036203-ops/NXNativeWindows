@echo off
setlocal
rem Slim IPA of Ocarina of Time: the app and shaders only, no game files (RomFS).
rem The game files (RomFS.img) are copied into the app's Documents once; later updates only need this small IPA.
set "NUP="
for /d %%D in ("%USERPROFILE%\Downloads\*DUMP") do for %%F in ("%%D\*.nup") do set "NUP=%%F"
if not defined NUP (
  echo Could not find the .nup file under %USERPROFILE%\Downloads\*DUMP
  pause
  exit /b 1
)
set "OUT=C:\Games\OoT"
rem The IPA is replaced at the end of the pack. If another program holds the old one open (an indexer, a preview, a sideloading tool),
rem it cannot be replaced: then this build writes OoT-slim-new.ipa instead of failing after minutes of work
set "IPA=%OUT%\OoT-slim.ipa"
if exist "%IPA%" del "%IPA%" 2>nul
if exist "%IPA%" (
  echo OoT-slim.ipa is in use by another program: this build writes OoT-slim-new.ipa instead
  set "IPA=%OUT%\OoT-slim-new.ipa"
)
if exist "%OUT%\OoT-slim-new.ipa" if "%IPA%"=="%OUT%\OoT-slim-new.ipa" del "%OUT%\OoT-slim-new.ipa" 2>nul
cd /d D:\nxw
echo [%time%] Slim build started: %IPA%. Output: %OUT%\console-slim.log
python win\build_ipa_windows.py "%NUP%" --work-dir "%OUT%\build" -o "%IPA%" --entitlements --romfs separate --keep-extracted --allow-other-metal --progress lines > "%OUT%\console-slim.log" 2>&1
set "RC=%errorlevel%"
if "%RC%"=="0" (
  echo [%time%] Done: %IPA%
  echo Game files to copy into the app's Documents: %OUT%\build\extract\v131072\RomFS.img
) else (
  echo [%time%] Build failed, exit code %RC%. Log: %OUT%\console-slim.log
)
pause
