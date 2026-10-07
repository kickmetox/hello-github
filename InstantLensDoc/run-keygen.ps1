# InstantLens Doc - Keygenerator (separates Extra)
# UTF-8 with BOM for Windows PowerShell 5.1
# Usage: powershell -ExecutionPolicy Bypass -File .\run-keygen.ps1

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Here

# Prefer InstantLensDoc root (parent) AND this folder (vendored / repo root)
$parent = Split-Path -Parent $Here
$env:PYTHONPATH = (@($Here, $parent) + @(($env:PYTHONPATH -split ';' | Where-Object { $_ }))) -join ';'

Write-Host "InstantLensDoc Keygenerator"
Write-Host "Keys: 32 Tage (30+2). Kontakt: ame@sellerbach.de"
Write-Host ""

$py = $null
if (Test-Path (Join-Path $Here ".venv\Scripts\python.exe")) {
    $py = Join-Path $Here ".venv\Scripts\python.exe"
} elseif (Test-Path (Join-Path $parent ".venv\Scripts\python.exe")) {
    $py = Join-Path $parent ".venv\Scripts\python.exe"
} else {
    $py = "python"
}

& $py -c "import instantlensdoc.license" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "FEHLER: Paket instantlensdoc nicht gefunden."
    Write-Host "Erwartet: ..\instantlensdoc (App-Root) oder .\instantlensdoc (im Keygen-Ordner)."
    Write-Host "Tipp: Keygen unter InstantLensDoc ablegen, Store-Zip mit Vendor nutzen,"
    Write-Host "      oder: `$env:PYTHONPATH='D:\AI_Temp\InstantLensDoc'"
    exit 1
}

& $py -m keygen --gui @args
exit $LASTEXITCODE
