# InstantLens Doc 2.6.40 - Windows-Runnable-Paket (Python-Layout + Keygen)
# Eine Zeile:
#   powershell -ExecutionPolicy Bypass -File .\scripts\pack-windows-runnable.ps1
#
# Erzeugt dist\InstantLensDoc-<VERSION>-windows-runnable.zip
# Optional: -OutPath D:\path\to\out.zip

param(
    [string]$OutPath = "",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$packPy = Join-Path $Root "scripts\pack-windows-runnable.py"
if (-not (Test-Path $packPy)) {
    throw "pack-windows-runnable.py fehlt: $packPy"
}

$args = @($packPy)
if ($OutPath) {
    $args += @("--out", $OutPath)
}

Write-Host "=== InstantLens Doc pack-windows-runnable 2.6.40 ==="
& $Python @args
if ($LASTEXITCODE -ne 0) { throw "Pack fehlgeschlagen (Exit $LASTEXITCODE)" }
