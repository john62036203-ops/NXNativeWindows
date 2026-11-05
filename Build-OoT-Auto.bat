@echo off
setlocal EnableDelayedExpansion
rem Auto build of Ocarina of Time. Output goes to C:\Games\OoT\console.log, state to status.txt.
rem After a failure it waits; a file C:\Games\OoT\retry.flag makes it build again. stop.flag ends it.
set "NUP="
for /d %%D in ("%USERPROFILE%\Downloads\*DUMP") do for %%F in ("%%D\*.nup") do set "NUP=%%F"
if not defined NUP (
  echo Could not find the .nup file under %USERPROFILE%\Downloads\*DUMP
  pause
  exit /b 1
)
set "OUT=C:\Games\OoT"
if not exist "%OUT%" mkdir "%OUT%"
cd /d D:\nxw
set /a RUN=0

:build
set /a RUN+=1
if exist "%OUT%\console.log" copy /y "%OUT%\console.log" "%OUT%\console.prev.log" >nul
echo running run=!RUN! start=%date% %time%> "%OUT%\status.txt"
echo [%time%] Build run !RUN! started. Output: %OUT%\console.log
python win\build_ipa_windows.py "%NUP%" --work-dir "%OUT%\build" -o "%OUT%\OoT.ipa" --entitlements --split-data --allow-other-metal --progress lines > "%OUT%\console.log" 2>&1
set "RC=!errorlevel!"
if "!RC!"=="0" (
  echo done run=!RUN! end=%date% %time%> "%OUT%\status.txt"
  echo [%time%] Done. IPA and data folder are in %OUT%
  pause
  exit /b 0
)
echo [%time%] Build run !RUN! failed, exit code !RC!. Waiting for Claude to fix it...

:wait
echo failed run=!RUN! rc=!RC! waiting=%date% %time%> "%OUT%\status.txt"
if exist "%OUT%\stop.flag" (
  del "%OUT%\stop.flag"
  echo stopped run=!RUN! rc=!RC! at=%date% %time%> "%OUT%\status.txt"
  echo [%time%] Stopped.
  pause
  exit /b !RC!
)
if exist "%OUT%\retry.flag" (
  del "%OUT%\retry.flag"
  goto build
)
timeout /t 60 /nobreak >nul
goto wait
