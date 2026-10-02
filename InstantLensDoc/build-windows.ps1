# InstantLens Doc — Windows-Build (PyInstaller App + Keygen)
# Eine Zeile:
#   powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
#
# Optionen:
#   -Clean
#   -SkipKeygen
#   -SkipApp

param(
    [switch]$Clean,
    [switch]$SkipApp,
    [switch]$SkipKeygen,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "=== InstantLens Doc Build ==="
Write-Host "Root: $Root"

# PyInstaller verfügbar?
& $Python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installiere PyInstaller…"
    & $Python -m pip install --upgrade pyinstaller
}

if ($Clean) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$Root\build", "$Root\dist"
}

$Icon = Join-Path $Root "assets\app.ico"
if (-not (Test-Path $Icon)) { $Icon = Join-Path $Root "assets\icon.png" }
$IconArgs = @()
if (Test-Path $Icon) { $IconArgs = @("--icon", $Icon) }

$Common = @(
    "--noconfirm",
    "--clean",
    "--paths", $Root,
    "--hidden-import", "pypdfium2",
    "--hidden-import", "pikepdf",
    "--hidden-import", "PIL",
    "--collect-all", "pypdfium2"
)

if (-not $SkipApp) {
    Write-Host "— App InstantLensDoc —"
    $appArgs = $Common + $IconArgs + @(
        "--name", "InstantLensDoc",
        "--windowed",
        "--add-data", "assets;assets",
        "--add-data", "FEATURES.md;.",
        "--add-data", "INFO.md;.",
        (Join-Path $Root "instantlensdoc\__main__.py")
    )
    & $Python -m PyInstaller @appArgs
    if ($LASTEXITCODE -ne 0) { throw "App-Build fehlgeschlagen" }
    Write-Host "OK: dist\InstantLensDoc\"
}

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
}

# Spec-Dateien liegen nach erstem Lauf unter Root — optional behalten
Write-Host "Fertig. Optional Inno: .\installer\build-installer.ps1"
