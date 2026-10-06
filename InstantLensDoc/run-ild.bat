@echo off
REM InstantLens Doc - Scripting-CLI (headless) - ASCII-safe
cd /d "%~dp0"
set "ILD_VER="
if exist "%~dp0VERSION.txt" (
  set /p ILD_VER=<"%~dp0VERSION.txt"
)
if not defined ILD_VER set "ILD_VER=unknown"
echo InstantLens Doc Scripting %ILD_VER%
echo python -m ild --help
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m ild %*
) else (
  python -m ild %*
)
