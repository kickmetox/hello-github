@echo off
setlocal
title ReckonGrid Installation
cd /d "%~dp0"
echo ReckonGrid Installation wird gestartet ...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" (
  echo.
  echo Installation fehlgeschlagen ^(Fehler %ERR%^).
  pause
  exit /b %ERR%
)
endlocal
