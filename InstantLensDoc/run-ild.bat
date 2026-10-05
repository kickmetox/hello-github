@echo off
REM InstantLens Doc - Scripting-CLI (headless) - ASCII-safe
cd /d "%~dp0"
echo InstantLens Doc Scripting 2.6.34
echo python -m ild --help
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m ild %*
) else (
  python -m ild %*
)
