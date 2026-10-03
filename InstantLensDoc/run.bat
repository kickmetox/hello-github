@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

REM InstantLens Doc 1.2.0 — Start mit Python-/Abhängigkeitsprüfung (DE-Meldungen)

set "PYEXE="
if exist ".venv\Scripts\python.exe" (
  set "PYEXE=.venv\Scripts\python.exe"
) else (
  where python >nul 2>&1
  if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
      echo.
      echo [InstantLens Doc] FEHLER: Python wurde nicht gefunden.
      echo.
      echo Bitte Python 3.12+ installieren und erneut versuchen:
      echo   https://www.python.org/downloads/
      echo Beim Installer „Add python.exe to PATH“ aktivieren.
      echo.
      echo Alternativ: virtuelle Umgebung anlegen:
      echo   python -m venv .venv
      echo   .venv\Scripts\pip install -r requirements.txt
      echo.
      pause
      exit /b 1
    )
    set "PYEXE=py -3"
  ) else (
    set "PYEXE=python"
  )
)

echo [InstantLens Doc] Python-Pruefung …
%PYEXE% -c "import sys; v=sys.version_info; raise SystemExit(0 if v.major==3 and v.minor>=10 else 1)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo [InstantLens Doc] FEHLER: Python 3.10 oder neuer ist erforderlich.
  echo Gefundene Python-Version:
  %PYEXE% --version 2>&1
  echo.
  echo Bitte eine passende Version installieren und PATH pruefen.
  echo.
  pause
  exit /b 1
)

echo [InstantLens Doc] Abhaengigkeiten pruefen …
%PYEXE% -c "import PySide6, pypdfium2, pikepdf, PIL" >nul 2>&1
if errorlevel 1 (
  echo.
  echo [InstantLens Doc] FEHLER: Erforderliche Pakete fehlen.
  echo Bitte im App-Ordner ausfuehren:
  echo   %PYEXE% -m pip install -r requirements.txt
  echo.
  echo Benoetigt u. a.: PySide6, pypdfium2, pikepdf, Pillow
  echo Optional fuer OCR: pytesseract + Tesseract-Runtime
  echo.
  pause
  exit /b 1
)

echo [InstantLens Doc] Start …
%PYEXE% -m instantlensdoc %*
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo [InstantLens Doc] Die Anwendung wurde mit Fehlercode %EC% beendet.
  pause
)
exit /b %EC%
