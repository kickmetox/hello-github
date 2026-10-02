# ScanTuxio Launcher — PDF via pypdfium2 (Frozen), Poppler nur optionaler lokaler Fallback
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArgs
)

$ErrorActionPreference = "Continue"
$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $AppDir) { $AppDir = Get-Location }

$legacyPoppler = Join-Path $AppDir "vendor\poppler\Library\bin\pdftoppm.exe"
if (Test-Path $legacyPoppler) {
    $bin = Split-Path $legacyPoppler -Parent
    $env:PATH = "$bin;$env:PATH"
    $env:SCANTUXIO_POPPLER = $bin
    Write-Warning "[ScanTuxio] Legacy-Poppler im PATH (nicht Installer-Standard; GPL)."
}

$exe = Join-Path $AppDir "ScanTuxio.exe"
$entry = Join-Path $AppDir "scantuxio_entry.py"

if (Test-Path $exe) {
    & $exe @AppArgs
    exit $LASTEXITCODE
}
if (Test-Path $entry) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 $entry @AppArgs
    } else {
        & python $entry @AppArgs
    }
    exit $LASTEXITCODE
}

Write-Error "Weder ScanTuxio.exe noch scantuxio_entry.py gefunden."
exit 1
