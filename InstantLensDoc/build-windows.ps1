# InstantLens Doc — Windows-Build (PyInstaller App + Keygen) 0.2.0
# Eine Zeile:
#   powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
#
# Optionen:
#   -Clean
#   -SkipKeygen          # kein InstantLensKeygen.exe
#   -SkipApp
#   -NoKeygenInApp       # Keygen nicht nach dist\InstantLensDoc kopieren
#   -Python python

param(
    [switch]$Clean,
    [switch]$SkipApp,
    [switch]$SkipKeygen,
    [switch]$NoKeygenInApp,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "=== InstantLens Doc Build 0.2.0 ==="
Write-Host "Root: $Root"

# Icon Pflicht für Release-Build (Fallback PNG)
$IconIco = Join-Path $Root "assets\app.ico"
$IconPng = Join-Path $Root "assets\icon.png"
$Icon = $null
if (Test-Path $IconIco) {
    $Icon = $IconIco
} elseif (Test-Path $IconPng) {
    $Icon = $IconPng
    Write-Host "WARNUNG: assets\app.ico fehlt — nutze icon.png"
} else {
    Write-Host "WARNUNG: Kein Icon unter assets\app.ico / icon.png — EXE ohne Icon"
}
$IconArgs = @()
if ($Icon) { $IconArgs = @("--icon", $Icon) }

# PyInstaller verfügbar?
& $Python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installiere PyInstaller…"
    & $Python -m pip install --upgrade pyinstaller
}

if ($Clean) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$Root\build", "$Root\dist"
}

$Common = @(
    "--noconfirm",
    "--clean",
    "--paths", $Root,
    "--hidden-import", "pypdfium2",
    "--hidden-import", "pikepdf",
    "--hidden-import", "PIL",
    "--hidden-import", "instantlensdoc",
    "--hidden-import", "ild_pdf",
    "--collect-all", "pypdfium2"
)

$AppDist = Join-Path $Root "dist\InstantLensDoc"

if (-not $SkipApp) {
    Write-Host "— App InstantLensDoc —"
    $dataArgs = @(
        "--add-data", "assets;assets",
        "--add-data", "FEATURES.md;.",
        "--add-data", "INFO.md;."
    )
    if (Test-Path (Join-Path $Root "CHANGELOG.md")) {
        $dataArgs += @("--add-data", "CHANGELOG.md;.")
    }
    if (Test-Path (Join-Path $Root "README.md")) {
        $dataArgs += @("--add-data", "README.md;.")
    }
    $appArgs = $Common + $IconArgs + $dataArgs + @(
        "--name", "InstantLensDoc",
        "--windowed",
        (Join-Path $Root "instantlensdoc\__main__.py")
    )
    & $Python -m PyInstaller @appArgs
    if ($LASTEXITCODE -ne 0) { throw "App-Build fehlgeschlagen" }
    # Assets/Docs zusätzlich absichern (falls --add-data auf Host anders mappt)
    New-Item -ItemType Directory -Force -Path (Join-Path $AppDist "assets") | Out-Null
    if (Test-Path $IconIco) {
        Copy-Item -Force $IconIco (Join-Path $AppDist "assets\app.ico")
    }
    if (Test-Path $IconPng) {
        Copy-Item -Force $IconPng (Join-Path $AppDist "assets\icon.png")
    }
    foreach ($doc in @("FEATURES.md", "INFO.md", "README.md", "CHANGELOG.md")) {
        $src = Join-Path $Root $doc
        if (Test-Path $src) { Copy-Item -Force $src (Join-Path $AppDist $doc) }
    }
    Write-Host "OK: dist\InstantLensDoc\"
}

$KeygenDist = Join-Path $Root "dist\InstantLensKeygen"
if (-not $SkipKeygen) {
    Write-Host "— Keygen InstantLensKeygen —"
    $kgArgs = $Common + $IconArgs + @(
        "--name", "InstantLensKeygen",
        "--windowed",
        (Join-Path $Root "keygen\__main__.py")
    )
    & $Python -m PyInstaller @kgArgs
    if ($LASTEXITCODE -ne 0) { throw "Keygen-Build fehlgeschlagen" }
    Write-Host "OK: dist\InstantLensKeygen\"

    # Optional: Keygen in App-Dist legen (Installer findet InstantLensKeygen.exe)
    if (-not $NoKeygenInApp -and (Test-Path $AppDist)) {
        $kgExe = Join-Path $KeygenDist "InstantLensKeygen.exe"
        if (-not (Test-Path $kgExe)) {
            # onedir vs. flat
            $alt = Get-ChildItem -Path $KeygenDist -Filter "InstantLensKeygen.exe" -Recurse -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($alt) { $kgExe = $alt.FullName }
        }
        if (Test-Path $kgExe) {
            Copy-Item -Force $kgExe (Join-Path $AppDist "InstantLensKeygen.exe")
            Write-Host "Keygen mitgepackt: dist\InstantLensDoc\InstantLensKeygen.exe"
        } else {
            Write-Host "WARNUNG: InstantLensKeygen.exe nicht gefunden — Installer-Keygen ggf. ohne EXE"
        }
    }
} else {
    Write-Host "Keygen übersprungen (-SkipKeygen)"
}

Write-Host "Fertig. Optional Inno:"
Write-Host '  powershell -ExecutionPolicy Bypass -File .\installer\build-installer.ps1'
Write-Host "  (ohne Keygen: -SkipKeygen bzw. ISCC /DIncludeKeygen=0)"
