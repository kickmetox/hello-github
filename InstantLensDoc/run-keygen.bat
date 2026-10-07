@echo off
REM InstantLens Doc - Keygenerator (separates Extra) - ASCII-safe
setlocal EnableExtensions
cd /d "%~dp0"

REM PYTHONPATH: this folder (repo/pack root OR standalone with vendored package)
REM plus parent (nested InstantLensDoc-keygen under InstantLensDoc root)
set "PYTHONPATH=%CD%;%CD%\..;%PYTHONPATH%"

echo InstantLensDoc Keygenerator
echo Keys: 32 Tage (30+2). Kontakt: ame@sellerbach.de
echo.

set "PYEXE=python"
if exist ".venv\Scripts\python.exe" set "PYEXE=.venv\Scripts\python.exe"
if exist "..\.venv\Scripts\python.exe" if not exist ".venv\Scripts\python.exe" set "PYEXE=..\.venv\Scripts\python.exe"

"%PYEXE%" -c "import instantlensdoc.license" 1>nul 2>nul
if errorlevel 1 (
  echo FEHLER: Paket instantlensdoc nicht gefunden.
  echo Erwartet: ..\instantlensdoc  ^(App-Root^) oder .\instantlensdoc ^(im Keygen-Ordner^).
  echo Tipp: Keygen unter InstantLensDoc ablegen, Store-Zip mit Vendor nutzen,
  echo       oder: set PYTHONPATH=D:\AI_Temp\InstantLensDoc
  exit /b 1
)

"%PYEXE%" -m keygen --gui %*
set "EC=%ERRORLEVEL%"
endlocal & exit /b %EC%
