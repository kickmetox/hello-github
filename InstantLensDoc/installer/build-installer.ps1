# InstantLens Doc 2.6.28 — Inno-Setup-Installer bauen (Setup.exe)
# Voraussetzung: Inno Setup 6 (iscc.exe) auf Windows x64
# Aufruf (Einzeiler):
#   powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1
# Direkt:
#   powershell -ExecutionPolicy Bypass -File .\installer\build-installer.ps1
# Optional:
#   -SourceRoot D:\path\to\pack
#   -PythonLauncher   # Shortcuts auf run.bat statt InstantLensDoc.exe
#   -NoKeygen         # IncludeKeygen=0 (keine Keygen-Shortcuts)
#   -IsccPath PATH
#
# Ergebnis: dist\InstantLensDoc-Setup-<VERSION>.exe
#   Startmenü + optional Desktop + Uninstall + 64-Bit
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
$Hinweis = Join-Path $InstallerDir "installer-hinweis.txt"
$Dist = Join-Path $Root "dist"
$Pack = Join-Path $Dist "InstantLensDoc"
$VersionFile = Join-Path $Root "VERSION.txt"

function Get-IldVersion {
    if (-not (Test-Path $VersionFile)) {
        throw "VERSION.txt fehlt: $VersionFile"
    }
    $v = (Get-Content -LiteralPath $VersionFile -Raw).Trim().Split()[0]
    if ($v -notmatch '^\d+\.\d+\.\d+') {
        throw "VERSION.txt ungültig: $v"
    }
    return $v
}

$Version = Get-IldVersion

if (-not (Test-Path $Iss)) {
    Write-Error "ISS fehlt: $Iss"
}
if (-not (Test-Path $Hinweis)) {
    Write-Host "WARNUNG: installer-hinweis.txt fehlt — InfoAfterFile kann fehlschlagen."
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
    Write-Host "Einzeiler nach Sync: powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1"
    exit 1
}

if (-not $SourceRoot) {
    # Pack-Ordner aus Repo bauen (Python-Launcher-Layout)
    New-Item -ItemType Directory -Force -Path $Pack | Out-Null
    $copyItems = @(
        "instantlensdoc", "ild_pdf", "ild", "keygen", "assets", "scripts",
        "docs", "examples", "requirements.txt", "VERSION.txt",
        "run.bat", "run.ps1", "run-keygen.bat", "run-ild.bat",
        "FEATURES.md", "INFO.md", "README.md", "CHANGELOG.md", "CONTRIBUTING.md"
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

# Preflight: Python-Layout oder EXE-Layout
$hasBat = Test-Path (Join-Path $SourceRoot "run.bat")
$hasExe = Test-Path (Join-Path $SourceRoot "InstantLensDoc.exe")
if (-not $hasBat -and -not $hasExe) {
    Write-Error "SourceRoot enthält weder run.bat noch InstantLensDoc.exe: $SourceRoot"
}
if ($PythonLauncher -and -not $hasBat) {
    Write-Host "WARNUNG: -PythonLauncher gesetzt, aber run.bat fehlt — Shortcuts können fehlschlagen."
}
if ((-not $PythonLauncher) -and (-not $hasExe) -and $hasBat) {
    Write-Host "Hinweis: Keine InstantLensDoc.exe — schalte auf PythonLauncher (run.bat)."
    $PythonLauncher = $true
}
if ((-not $NoKeygen) -and $PythonLauncher) {
    $kgBat = Join-Path $SourceRoot "run-keygen.bat"
    if (-not (Test-Path $kgBat)) {
        Write-Host "WARNUNG: run-keygen.bat fehlt — Keygen-Shortcut im Startmenü kann fehlschlagen."
    }
}

New-Item -ItemType Directory -Force -Path $Dist | Out-Null

$defs = @(
    "/DSourceRoot=$SourceRoot",
    "/DMyAppVersion=$Version"
)
if ($PythonLauncher) {
    $defs += "/DUsePythonLauncher=1"
}
if ($NoKeygen) {
    $defs += "/DIncludeKeygen=0"
} else {
    $defs += "/DIncludeKeygen=1"
}

Write-Host "=== InstantLens Doc build-installer $Version ==="
Write-Host "ISCC: $iscc"
Write-Host "SourceRoot: $SourceRoot"
Write-Host "PythonLauncher: $PythonLauncher"
Write-Host "IncludeKeygen: $(-not $NoKeygen)"
Write-Host "MyAppVersion: $Version"
& $iscc @defs $Iss
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$SetupName = "InstantLensDoc-Setup-$Version.exe"
$SetupPath = Join-Path $Dist $SetupName
Write-Host "Fertig. Setup unter: $Dist"
if (Test-Path $SetupPath) {
    $sz = [math]::Round((Get-Item $SetupPath).Length / 1MB, 2)
    Write-Host "OK: $SetupPath ($sz MB)"
} else {
    Write-Host "Hinweis: Erwartete Datei $SetupName prüfen."
}
Get-ChildItem $Dist -Filter "InstantLensDoc-Setup-*" | Format-Table Name, Length, LastWriteTime
exit 0
