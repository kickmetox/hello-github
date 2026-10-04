# InstantLens Doc 2.6.27 — Windows-Installer (Inno Setup → Setup.exe)
#
# Baut InstantLensDoc-Setup-<VERSION>.exe mit:
#   - Startmenü-Gruppe (App, optional Keygen, INFO, Deinstallieren)
#   - optionaler Desktop-Icon (Task desktopicon, checkedonce)
#   - Uninstall-Eintrag (Systemsteuerung / Apps)
#   - 64-Bit (ArchitecturesInstallIn64BitMode=x64compatible)
#   - Version aus VERSION.txt → ISCC /DMyAppVersion=
#
# Voraussetzung: Windows x64 + Inno Setup 6 (ISCC.exe)
#
# Einzeiler (nach Sync nach D:\AI_Temp\InstantLensDoc):
#   powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1
#
# Varianten:
#   -PythonLauncher   Python-Layout (run.bat) — Default wenn kein dist\EXE
#   -NoKeygen         ohne Keygenerator-Shortcuts
#   -SourceRoot PATH  fertiges Pack als Quelle
#   -IsccPath PATH    ISCC.exe explizit

param(
    [string]$SourceRoot = "",
    [switch]$PythonLauncher,
    [switch]$NoKeygen,
    [string]$IsccPath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Builder = Join-Path $Root "installer\build-installer.ps1"
$Iss = Join-Path $Root "installer\instantlensdoc.iss"
$VersionFile = Join-Path $Root "VERSION.txt"

if (-not (Test-Path $Builder)) {
    throw "installer\build-installer.ps1 fehlt: $Builder"
}
if (-not (Test-Path $Iss)) {
    throw "installer\instantlensdoc.iss fehlt: $Iss"
}
if (-not (Test-Path $VersionFile)) {
    throw "VERSION.txt fehlt: $VersionFile"
}

$Version = (Get-Content -LiteralPath $VersionFile -Raw).Trim().Split()[0]
if ($Version -notmatch '^\d+\.\d+\.\d+') {
    throw "VERSION.txt ungültig: $Version"
}

# ISS-Konsistenz: Default-MyAppVersion sollte zur VERSION.txt passen (Override via /D ok)
$issText = Get-Content -LiteralPath $Iss -Raw
if ($issText -notmatch [regex]::Escape($Version)) {
    Write-Host "WARNUNG: instantlensdoc.iss enthält '$Version' nicht — /DMyAppVersion=$Version wird gesetzt."
}
if ($issText -notmatch 'desktopicon') {
    throw "instantlensdoc.iss unvollständig: Task desktopicon fehlt"
}
if ($issText -notmatch 'ArchitecturesInstallIn64BitMode') {
    throw "instantlensdoc.iss unvollständig: 64-Bit-Architektur fehlt"
}
if ($issText -notmatch 'UninstallDisplayName') {
    throw "instantlensdoc.iss unvollständig: UninstallDisplayName fehlt"
}
if ($issText -notmatch 'CustomMessages') {
    Write-Host "WARNUNG: CustomMessages (DE/EN) fehlen im ISS — Task-Texte ggf. nur Default."
}

Write-Host "=== InstantLens Doc build-windows-installer $Version ==="
Write-Host "Einzeiler: powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1"
Write-Host "Wrapper → installer\build-installer.ps1 (Inno Setup 6, Version $Version)"

$passArgs = @()
if ($SourceRoot) { $passArgs += @("-SourceRoot", $SourceRoot) }
if ($PythonLauncher) { $passArgs += "-PythonLauncher" }
if ($NoKeygen) { $passArgs += "-NoKeygen" }
if ($IsccPath) { $passArgs += @("-IsccPath", $IsccPath) }

& powershell -ExecutionPolicy Bypass -File $Builder @passArgs
$code = $LASTEXITCODE
if ($code -ne 0) { exit $code }

$Dist = Join-Path $Root "dist"
$SetupName = "InstantLensDoc-Setup-$Version.exe"
$Setup = Get-ChildItem $Dist -Filter $SetupName -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $Setup) {
    $Setup = Get-ChildItem $Dist -Filter "InstantLensDoc-Setup-*.exe" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
}
if ($Setup) {
    Write-Host "Setup.exe: $($Setup.FullName) ($([math]::Round($Setup.Length/1MB, 2)) MB)"
    Write-Host "Kopiere ggf. nach Project-Store docs\InstantLensDoc-$Version-Setup.exe"
} else {
    Write-Host "Hinweis: Erwartete Datei dist\$SetupName prüfen."
}
exit 0
