# InstantLens Doc — Inno-Setup-Installer bauen (eine Datei)
# Voraussetzung: Inno Setup 6 (iscc.exe)
# Aufruf:
#   powershell -ExecutionPolicy Bypass -File .\installer\build-installer.ps1
# Optional:
#   -SourceRoot D:\path\to\pack
#   -PythonLauncher   # Shortcuts auf run.bat statt InstantLensDoc.exe

param(
    [string]$SourceRoot = "",
    [switch]$PythonLauncher,
    [string]$IsccPath = ""
)

$ErrorActionPreference = "Stop"
$InstallerDir = $PSScriptRoot
$Root = Split-Path -Parent $InstallerDir
$Iss = Join-Path $InstallerDir "instantlensdoc.iss"
$Dist = Join-Path $Root "dist"
$Pack = Join-Path $Dist "InstantLensDoc"

if (-not (Test-Path $Iss)) {
    Write-Error "ISS fehlt: $Iss"
}

# iscc finden
function Find-Iscc {
    if ($IsccPath -and (Test-Path $IsccPath)) { return $IsccPath }
    if ($env:ISCC_PATH -and (Test-Path $env:ISCC_PATH)) { return $env:ISCC_PATH }
    $cmd = Get-Command iscc -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

$iscc = Find-Iscc
if (-not $iscc) {
    Write-Host "FEHLER: Inno Setup 6 (ISCC.exe) nicht gefunden."
    Write-Host "Installieren: https://jrsoftware.org/isinfo.php"
    Write-Host "Oder ISCC_PATH setzen / -IsccPath angeben."
    exit 1
}

if (-not $SourceRoot) {
    # Pack-Ordner aus Repo bauen (Python-Launcher-Layout)
    New-Item -ItemType Directory -Force -Path $Pack | Out-Null
    $copyItems = @(
        "instantlensdoc", "ild_pdf", "keygen", "assets", "scripts",
        "requirements.txt", "run.bat", "run.ps1", "run-keygen.bat",
        "FEATURES.md", "INFO.md", "README.md"
    )
    foreach ($name in $copyItems) {
        $src = Join-Path $Root $name
        if (Test-Path $src) {
            Copy-Item -Recurse -Force $src $Pack
        }
    }
    $SourceRoot = $Pack
    if (-not $PSBoundParameters.ContainsKey("PythonLauncher")) {
        $PythonLauncher = $true
    }
}

if (-not (Test-Path $SourceRoot)) {
    Write-Error "SourceRoot fehlt: $SourceRoot"
}

New-Item -ItemType Directory -Force -Path $Dist | Out-Null

$defs = @("/DSourceRoot=$SourceRoot")
if ($PythonLauncher) {
    $defs += "/DUsePythonLauncher=1"
}

Write-Host "ISCC: $iscc"
Write-Host "SourceRoot: $SourceRoot"
Write-Host "PythonLauncher: $PythonLauncher"
& $iscc @defs $Iss
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Fertig. Setup unter: $Dist"
Get-ChildItem $Dist -Filter "InstantLensDoc-Setup-*" | Format-Table Name, Length, LastWriteTime
