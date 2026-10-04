# InstantLens Doc — Windows-Build (PyInstaller App + Keygen) 2.6.21
# Eine Zeile:
#   powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
#
# Voraussetzung: Python 3.10+ **64-Bit** (x64). 32-Bit wird abgelehnt.
#
# Optionen:
#   -Clean
#   -SkipKeygen          # kein InstantLensKeygen.exe
#   -SkipApp
#   -NoKeygenInApp       # Keygen nicht nach dist\InstantLensDoc kopieren
#   -Allow32Bit          # Notfall: 32-Bit Python erlauben (nicht empfohlen)
#   -Python python
#
# Keygen-EXE: dist\InstantLensKeygen\ + optional dist\InstantLensDoc\InstantLensKeygen.exe
# (= Installer-Pfad {app}\InstantLensKeygen.exe)
#
# Runnable Python-Pack (ohne PyInstaller): scripts\pack-windows-runnable.ps1

param(
    [switch]$Clean,
    [switch]$SkipApp,
    [switch]$SkipKeygen,
    [switch]$NoKeygenInApp,
    [switch]$Allow32Bit,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "=== InstantLens Doc Build 2.6.21 (Windows x64) ==="
Write-Host "Root: $Root"

# 64-Bit Python erzwingen (bevorzugt für Release)
$archLine = & $Python -c "import struct,platform; print(struct.calcsize('P')*8); print(platform.machine())"
if ($LASTEXITCODE -ne 0) {
    throw "Python nicht startbar: $Python"
}
$archLines = @($archLine | Where-Object { $_ -and "$_".Trim() })
$bits = 0
$machine = ""
if ($archLines.Count -ge 1) { [void][int]::TryParse("$($archLines[0])".Trim(), [ref]$bits) }
if ($archLines.Count -ge 2) { $machine = "$($archLines[1])".Trim() }
Write-Host "Python: $bits-Bit · Machine: $machine"
if ($bits -ne 64 -and -not $Allow32Bit) {
    throw "64-Bit-Python erforderlich (gefunden: ${bits}-Bit). Installiere Python x64 oder nutze -Allow32Bit."
}
if ($bits -ne 64 -and $Allow32Bit) {
    Write-Host "WARNUNG: 32-Bit Python (-Allow32Bit) — Release bevorzugt x64." -ForegroundColor Yellow
}

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
    "--hidden-import", "ild",
    "--hidden-import", "keygen",
    "--collect-all", "pypdfium2"
)

$AppDist = Join-Path $Root "dist\InstantLensDoc"

if (-not $SkipApp) {
    Write-Host "— App InstantLensDoc (x64) —"
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
    if (Test-Path (Join-Path $Root "VERSION.txt")) {
        $dataArgs += @("--add-data", "VERSION.txt;.")
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
    foreach ($doc in @("FEATURES.md", "INFO.md", "README.md", "CHANGELOG.md", "VERSION.txt", "run-keygen.bat")) {
        $src = Join-Path $Root $doc
        if (Test-Path $src) { Copy-Item -Force $src (Join-Path $AppDist $doc) }
    }
    Write-Host "OK: dist\InstantLensDoc\"
}

$KeygenDist = Join-Path $Root "dist\InstantLensKeygen"
if (-not $SkipKeygen) {
    Write-Host "— Keygen InstantLensKeygen (x64) —"
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

Write-Host "Fertig (2.6.21). Optional:"
Write-Host '  powershell -ExecutionPolicy Bypass -File .\installer\build-installer.ps1'
Write-Host "  (ohne Keygen: -SkipKeygen bzw. ISCC /DIncludeKeygen=0)"
Write-Host '  python scripts\pack-windows-runnable.py   # Python-Layout-Zip ohne EXE'
