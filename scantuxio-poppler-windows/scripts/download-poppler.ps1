<#
.SYNOPSIS
  Lädt Poppler für Windows (oschwartz10612/poppler-windows) nach vendor/poppler.

.DESCRIPTION
  Quelle: https://github.com/oschwartz10612/poppler-windows/releases
  Packaging-Repo: MIT — die Poppler-Binaries selbst unterliegen der GPL (Upstream).
  Nach dem Entpacken liegt pdftoppm typischerweise unter:
    vendor\poppler\Library\bin\pdftoppm.exe
  oder vendor\poppler\Release-*\Library\bin\

.PARAMETER Version
  Release-Tag ohne führendes v, z. B. 25.12.0-0 (Default: 25.12.0-0, stabil/bekannt).

.PARAMETER DestRoot
  Zielverzeichnis (App-Root). Default: Parent von scripts\
#>
[CmdletBinding()]
param(
    [string]$Version = "25.12.0-0",
    [string]$DestRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $DestRoot) {
    $DestRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
}

$dest = Join-Path $DestRoot "vendor\poppler"
$zipName = "Release-$Version.zip"
$url = "https://github.com/oschwartz10612/poppler-windows/releases/download/v$Version/$zipName"
$tmp = Join-Path $env:TEMP "scantuxio-poppler-$Version.zip"
$stage = Join-Path $env:TEMP "scantuxio-poppler-stage-$Version"

Write-Host "Download: $url"
Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing

if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Path $stage | Out-Null
Expand-Archive -Path $tmp -DestinationPath $stage -Force

if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
New-Item -ItemType Directory -Path $dest -Force | Out-Null

# Zip enthält oft einen Release-* Ordner — Inhalt nach vendor/poppler spiegeln
$inner = Get-ChildItem $stage | Select-Object -First 1
if ($null -eq $inner) { throw "Leeres Poppler-Archiv" }

if (Test-Path (Join-Path $inner.FullName "Library\bin\pdftoppm.exe")) {
    Copy-Item -Path (Join-Path $inner.FullName "*") -Destination $dest -Recurse -Force
} elseif (Test-Path (Join-Path $stage "Library\bin\pdftoppm.exe")) {
    Copy-Item -Path (Join-Path $stage "*") -Destination $dest -Recurse -Force
} else {
    # Fallback: alles kopieren
    Copy-Item -Path (Join-Path $stage "*") -Destination $dest -Recurse -Force
}

$pdftoppm = Join-Path $dest "Library\bin\pdftoppm.exe"
if (-not (Test-Path $pdftoppm)) {
    $alt = Get-ChildItem -Path $dest -Recurse -Filter "pdftoppm.exe" | Select-Object -First 1
    if ($alt) {
        Write-Host "pdftoppm gefunden: $($alt.FullName)"
    } else {
        throw "pdftoppm.exe nach Extraktion nicht gefunden — Layout prüfen."
    }
} else {
    Write-Host "OK: $pdftoppm"
}

# Lizenzhinweis ablegen
$notice = @"
Poppler (Windows binaries)
Upstream: https://poppler.freedesktop.org/
Windows package: https://github.com/oschwartz10612/poppler-windows (packaging MIT)
Poppler library/tools: GPL-2.0-or-later / GPL-3.0 (siehe Upstream COPYING)

ScanTuxio ruft Poppler-Tools (pdftoppm, pdfinfo, …) als separate Programme auf.
Bei Weitergabe dieser Binaries: GPL-Hinweise beibehalten und Quellcode-Angebot
für Poppler sicherstellen (Upstream-Quellen / korrespondierendes Release).

Version: $Version
Downloaded: $(Get-Date -Format o)
URL: $url
"@
Set-Content -Path (Join-Path $dest "LICENSE-POPPLER.txt") -Value $notice -Encoding UTF8

Write-Host "Fertig: $dest"
Write-Host "Hinweis: Poppler = GPL — siehe LICENSE-POPPLER.txt und docs/poppler-windows.md"
