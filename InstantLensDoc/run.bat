@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

REM InstantLens Doc 1.2.1 — Start mit Python-/Abhängigkeitsprüfung (DE-Meldungen)
REM Optional: pip install -r requirements.txt per J/N — 1.2.1

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
if not errorlevel 1 goto :start_app

echo.
echo [InstantLens Doc] FEHLER: Erforderliche Pakete fehlen.
echo Benoetigt u. a.: PySide6, pypdfium2, pikepdf, Pillow
echo Optional fuer OCR: pytesseract + Tesseract-Runtime
echo.
if not exist "requirements.txt" (
  echo [InstantLens Doc] requirements.txt nicht gefunden — bitte manuell installieren:
  echo   %PYEXE% -m pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)
echo Fehlende Pakete jetzt mit pip installieren?
echo   %PYEXE% -m pip install -r requirements.txt
set "ILD_PIP="
set /p "ILD_PIP=Jetzt installieren? [J/N]: "
if /i "!ILD_PIP!"=="J" goto :do_pip
if /i "!ILD_PIP!"=="Y" goto :do_pip
if /i "!ILD_PIP!"=="JA" goto :do_pip
echo.
echo Installation abgebrochen. Manuell ausfuehren:
echo   %PYEXE% -m pip install -r requirements.txt
echo.
pause
exit /b 1

:do_pip
echo.
echo [InstantLens Doc] Installiere Abhaengigkeiten …
%PYEXE% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [InstantLens Doc] FEHLER: pip install ist fehlgeschlagen.
  echo Bitte Netzwerk/Rechte pruefen und erneut versuchen.
  echo.
  pause
  exit /b 1
)
echo [InstantLens Doc] Abhaengigkeiten erneut pruefen …
%PYEXE% -c "import PySide6, pypdfium2, pikepdf, PIL" >nul 2>&1
if errorlevel 1 (
  echo.
  echo [InstantLens Doc] FEHLER: Pakete fehlen weiterhin nach der Installation.
  echo.
  pause
  exit /b 1
)

:start_app
echo [InstantLens Doc] Start …
%PYEXE% -m instantlensdoc %*
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo [InstantLens Doc] Die Anwendung wurde mit Fehlercode %EC% beendet.
  pause
)
exit /b %EC%
