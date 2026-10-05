@echo off
REM InstantLens Doc - Keygenerator (separates Extra) - ASCII-safe
cd /d "%~dp0"
echo InstantLensDoc Keygenerator
echo Keys: 32 Tage (30+2). Kontakt: ame@sellerbach.de
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m keygen --gui %*
) else (
  python -m keygen --gui %*
)
