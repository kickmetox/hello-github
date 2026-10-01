@echo off
setlocal EnableExtensions
REM ScanTuxio Launcher (Windows) — Poppler-Bundle in PATH legen

set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"

REM Bevorzugte Bundle-Pfade (poppler-windows Release-Layout)
set "POPPLER_BIN="
if exist "%APP_DIR%\vendor\poppler\Library\bin\pdftoppm.exe" set "POPPLER_BIN=%APP_DIR%\vendor\poppler\Library\bin"
if not defined POPPLER_BIN if exist "%APP_DIR%\vendor\poppler\bin\pdftoppm.exe" set "POPPLER_BIN=%APP_DIR%\vendor\poppler\bin"
if not defined POPPLER_BIN if exist "%APP_DIR%\poppler\Library\bin\pdftoppm.exe" set "POPPLER_BIN=%APP_DIR%\poppler\Library\bin"

if defined POPPLER_BIN (
  set "PATH=%POPPLER_BIN%;%PATH%"
  set "SCANTUXIO_POPPLER=%POPPLER_BIN%"
  set "POPPLER_PATH=%POPPLER_BIN%"
) else (
  echo [ScanTuxio] Warnung: Poppler nicht unter vendor\poppler gefunden.
  echo             Bitte scripts\download-poppler.ps1 ausfuehren oder Installer nutzen.
)

REM Frozen EXE bevorzugen
if exist "%APP_DIR%\ScanTuxio.exe" (
  "%APP_DIR%\ScanTuxio.exe" %*
  exit /b %ERRORLEVEL%
)

REM Dev-Start
if exist "%APP_DIR%\scantuxio_entry.py" (
  where py >nul 2>&1 && (
    py -3 "%APP_DIR%\scantuxio_entry.py" %*
    exit /b %ERRORLEVEL%
  )
  python "%APP_DIR%\scantuxio_entry.py" %*
  exit /b %ERRORLEVEL%
)

echo [ScanTuxio] Weder ScanTuxio.exe noch scantuxio_entry.py gefunden.
exit /b 1
