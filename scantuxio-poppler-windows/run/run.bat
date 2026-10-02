@echo off
setlocal EnableExtensions
REM ScanTuxio Launcher (Windows) — PDF via pypdfium2 (in EXE gebündelt), kein Poppler nötig

set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"

REM Optionaler Fallback: falls jemand lokal Poppler hat (nicht vom Installer)
if exist "%APP_DIR%\vendor\poppler\Library\bin\pdftoppm.exe" (
  set "PATH=%APP_DIR%\vendor\poppler\Library\bin;%PATH%"
  set "SCANTUXIO_POPPLER=%APP_DIR%\vendor\poppler\Library\bin"
)

if exist "%APP_DIR%\ScanTuxio.exe" (
  "%APP_DIR%\ScanTuxio.exe" %*
  exit /b %ERRORLEVEL%
)

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
