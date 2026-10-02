@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m instantlensdoc %*
) else (
  python -m instantlensdoc %*
)
