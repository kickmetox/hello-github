# ScanTuxio Launcher (Windows PowerShell) — Poppler-Bundle in PATH
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArgs
)

$ErrorActionPreference = "Continue"
$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $AppDir) { $AppDir = Get-Location }

function Find-PopplerBin {
    param([string]$Root)
    $candidates = @(
        (Join-Path $Root "vendor\poppler\Library\bin"),
        (Join-Path $Root "vendor\poppler\bin"),
        (Join-Path $Root "poppler\Library\bin"),
        (Join-Path $Root "poppler\bin")
    )
    foreach ($dir in $candidates) {
        if (Test-Path (Join-Path $dir "pdftoppm.exe")) { return $dir }
    }
    # Release-* Unterordner
    $vendor = Join-Path $Root "vendor\poppler"
    if (Test-Path $vendor) {
        Get-ChildItem -Path $vendor -Directory -Filter "Release-*" -ErrorAction SilentlyContinue |
            ForEach-Object {
                foreach ($sub in @("Library\bin", "bin")) {
                    $bin = Join-Path $_.FullName $sub
                    if (Test-Path (Join-Path $bin "pdftoppm.exe")) { return $bin }
                }
            }
    }
    return $null
}

$popplerBin = Find-PopplerBin -Root $AppDir
if ($popplerBin) {
    $env:PATH = "$popplerBin;$env:PATH"
    $env:SCANTUXIO_POPPLER = $popplerBin
    $env:POPPLER_PATH = $popplerBin
    Write-Host "[ScanTuxio] Poppler: $popplerBin"
} else {
    Write-Warning "[ScanTuxio] Poppler nicht unter vendor\poppler gefunden. scripts\download-poppler.ps1 ausführen."
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
