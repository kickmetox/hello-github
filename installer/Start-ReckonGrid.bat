@echo off
setlocal
title ReckonGrid
cd /d "%~dp0"
echo ReckonGrid wird gestartet ...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0ReckonGrid.ps1" %*
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" (
  echo.
  echo Start fehlgeschlagen ^(Fehler %ERR%^).
  echo Dieses Fenster bleibt offen, damit die Meldung lesbar ist.
  pause
  exit /b %ERR%
)
endlocal
