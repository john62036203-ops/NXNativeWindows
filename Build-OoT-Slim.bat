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
rem The old IPA is replaced at the end of the pack: a program holding it open (Sideloadly, iTunes, Explorer's preview pane) makes that fail after minutes of work, so try now
if exist "%OUT%\OoT-slim.ipa" (
  del "%OUT%\OoT-slim.ipa" 2>nul
  if exist "%OUT%\OoT-slim.ipa" (
    echo OoT-slim.ipa is open in another program (Sideloadly, iTunes, Explorer preview...). Close it and run this again.
    pause
    exit /b 1
  )
  del "%OUT%\OoT-slim.ipa.idx" 2>nul
)
cd /d D:\nxw
echo [%time%] Slim build started. Output: %OUT%\console-slim.log
python win\build_ipa_windows.py "%NUP%" --work-dir "%OUT%\build" -o "%OUT%\OoT-slim.ipa" --entitlements --romfs separate --keep-extracted --allow-other-metal --progress lines > "%OUT%\console-slim.log" 2>&1
set "RC=%errorlevel%"
if "%RC%"=="0" (
  echo [%time%] Done: %OUT%\OoT-slim.ipa
  echo Game files to copy into the app's Documents: %OUT%\build\extract\v131072\RomFS.img
) else (
  echo [%time%] Build failed, exit code %RC%. Log: %OUT%\console-slim.log
)
pause
