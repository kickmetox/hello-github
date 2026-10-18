@echo off
setlocal
cd /d "%~dp0"
set "PYEXE="
set "PYARGS="
if exist "%~dp0python\python.exe" set "PYEXE=%~dp0python\python.exe"
if not defined PYEXE where py >nul 2>&1 && set "PYEXE=py" && set "PYARGS=-3"
if not defined PYEXE where python >nul 2>&1 && set "PYEXE=python"
if not defined PYEXE (
  echo Python 3 wurde nicht gefunden. Bitte von https://www.python.org installieren.
  pause
  exit /b 1
)
"%PYEXE%" %PYARGS% "%~dp0cpcm.py" serve
if errorlevel 1 pause
