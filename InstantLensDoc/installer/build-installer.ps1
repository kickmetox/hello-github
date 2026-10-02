# InstantLens Doc — Inno-Setup-Installer bauen (eine Datei) 0.2.6
# Voraussetzung: Inno Setup 6 (iscc.exe)
# Aufruf:
#   powershell -ExecutionPolicy Bypass -File .\installer\build-installer.ps1
# Optional:
#   -SourceRoot D:\path\to\pack
#   -PythonLauncher   # Shortcuts auf run.bat statt InstantLensDoc.exe
#   -NoKeygen         # IncludeKeygen=0 (keine Keygen-Shortcuts)
#
# Keygen-EXE: Prefer dist\InstantLensKeygen\InstantLensKeygen.exe,
# Fallback dist\InstantLensDoc\InstantLensKeygen.exe → Pack als InstantLensKeygen.exe
# Installiert: {app}\InstantLensKeygen.exe (+ Startmenü, wenn IncludeKeygen=1)

param(
    [string]$SourceRoot = "",
    [switch]$PythonLauncher,
    [switch]$NoKeygen,
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

# Icon prüfen (SetupIconFile)
$Icon = Join-Path $Root "assets\app.ico"
if (-not (Test-Path $Icon)) {
    Write-Host "WARNUNG: assets\app.ico fehlt — Inno SetupIconFile kann fehlschlagen."
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
        "FEATURES.md", "INFO.md", "README.md", "CHANGELOG.md"
    )
    foreach ($name in $copyItems) {
        $src = Join-Path $Root $name
        if (Test-Path $src) {
            Copy-Item -Recurse -Force $src $Pack
        }
    }
    # Optional: gebauter Keygen aus dist mitnehmen
    $kgExe = Join-Path $Root "dist\InstantLensKeygen\InstantLensKeygen.exe"
    if (-not (Test-Path $kgExe)) {
        $kgExe = Join-Path $Root "dist\InstantLensDoc\InstantLensKeygen.exe"
    }
    if ((-not $NoKeygen) -and (Test-Path $kgExe)) {
        Copy-Item -Force $kgExe (Join-Path $Pack "InstantLensKeygen.exe")
        Write-Host "Keygen EXE mitgepackt."
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
if ($NoKeygen) {
    $defs += "/DIncludeKeygen=0"
} else {
    $defs += "/DIncludeKeygen=1"
}

Write-Host "ISCC: $iscc"
Write-Host "SourceRoot: $SourceRoot"
Write-Host "PythonLauncher: $PythonLauncher"
Write-Host "IncludeKeygen: $(-not $NoKeygen)"
& $iscc @defs $Iss
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Fertig. Setup unter: $Dist"
Get-ChildItem $Dist -Filter "InstantLensDoc-Setup-*" | Format-Table Name, Length, LastWriteTime
