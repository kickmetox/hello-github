# InstantLens Doc 2.6.50 - Windows-Installer (Inno Setup -> Setup.exe)
#
# Baut InstantLensDoc-Setup-<VERSION>.exe mit:
#   - Startmenue-Gruppe (App, optional Keygen, INFO, Deinstallieren)
#   - optionaler Desktop-Icon (Task desktopicon, checkedonce)
#   - Uninstall-Eintrag (Systemsteuerung / Apps)
#   - 64-Bit (ArchitecturesInstallIn64BitMode=x64compatible)
#   - Version aus VERSION.txt -> ISCC /DMyAppVersion=
#
# Voraussetzung: Windows x64 + Inno Setup 6 (ISCC.exe)
# Vorher: build-windows.ps1 (InstantLensDoc.exe unter dist\InstantLensDoc\)
#
# Einzeiler (nach Sync nach D:\AI_Temp\InstantLensDoc):
#   powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1
#
# Varianten:
#   -PythonLauncher   Python-Layout (run.bat) - nur explizit (kein Auto-Fallback)
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
    throw "VERSION.txt ungueltig: $Version"
}

# ISS-Konsistenz: Default-MyAppVersion sollte zur VERSION.txt passen (Override via /D ok)
$issText = Get-Content -LiteralPath $Iss -Raw
if ($issText -notmatch [regex]::Escape($Version)) {
    Write-Host "WARNUNG: instantlensdoc.iss enthaelt '$Version' nicht - /DMyAppVersion=$Version wird gesetzt."
}
if ($issText -notmatch 'desktopicon') {
    throw "instantlensdoc.iss unvollstaendig: Task desktopicon fehlt"
}
if ($issText -notmatch 'ArchitecturesInstallIn64BitMode') {
    throw "instantlensdoc.iss unvollstaendig: 64-Bit-Architektur fehlt"
}
if ($issText -notmatch 'UninstallDisplayName') {
    throw "instantlensdoc.iss unvollstaendig: UninstallDisplayName fehlt"
}
if ($issText -notmatch 'CustomMessages') {
    Write-Host "WARNUNG: CustomMessages (DE/EN) fehlen im ISS - Task-Texte ggf. nur Default."
}

Write-Host "=== InstantLens Doc build-windows-installer $Version ==="
Write-Host "Einzeiler: powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1"
Write-Host "Wrapper -> installer\build-installer.ps1 (Inno Setup 6, Version $Version)"

# Preflight: EXE muss vor Inno existieren (sonst Setup ~2-3 MB) - 2.6.40
$explicitPython = $PSBoundParameters.ContainsKey("PythonLauncher") -and $PythonLauncher
if (-not $SourceRoot -and -not $explicitPython) {
    $exePre = Join-Path $Root "dist\InstantLensDoc\InstantLensDoc.exe"
    if (-not (Test-Path -LiteralPath $exePre)) {
        throw @"
Preflight: InstantLensDoc.exe fehlt: $exePre
Zuerst: powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
(Dev ohne EXE: -PythonLauncher)
"@
    }
    $exePreLen = (Get-Item -LiteralPath $exePre).Length
    if ($exePreLen -lt 5MB) {
        throw "Preflight: InstantLensDoc.exe zu klein ($exePreLen Bytes) - build-windows.ps1 erneut."
    }
    Write-Host ("Preflight EXE OK: {0} ({1} MB)" -f $exePre, [math]::Round($exePreLen / 1MB, 2))
}

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
    if ((-not $explicitPython) -and ($Setup.Length -lt 15MB)) {
        throw "Setup.exe verdaechtig klein ($([math]::Round($Setup.Length/1MB, 2)) MB) - PyInstaller-Bundle fehlt."
    }
    Write-Host "Kopiere ggf. nach Project-Store docs\InstantLensDoc-$Version-Setup.exe"
} else {
    throw "Erwartete Datei dist\$SetupName fehlt."
}
exit 0
