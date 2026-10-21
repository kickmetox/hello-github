@echo off
setlocal
title ReckonGrid
cd /d "%~dp0"
echo ReckonGrid wird gestartet ...
if not exist "%~dp0installer\ReckonGrid.ps1" (
  echo installer\ReckonGrid.ps1 fehlt.
  pause
  exit /b 1
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\ReckonGrid.ps1" %*
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" (
  echo.
  echo Start fehlgeschlagen ^(Fehler %ERR%^).
  echo Dieses Fenster bleibt offen, damit die Meldung lesbar ist.
  echo Entwicklung ohne fertigen Build: npm install und danach npm run dev
  pause
  exit /b %ERR%
)
endlocal
