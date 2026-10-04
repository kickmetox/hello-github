# InstantLens Doc 2.6.25 — Windows-Installer (Inno Setup → Setup.exe)
#
# Baut InstantLensDoc-Setup-2.6.25.exe mit:
#   - Startmenü-Gruppe (App, optional Keygen, INFO, Deinstallieren)
#   - optionaler Desktop-Icon (Task desktopicon, checkedonce)
#   - Uninstall-Eintrag (Systemsteuerung / Apps)
#   - 64-Bit (ArchitecturesInstallIn64BitMode=x64compatible)
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
if (-not (Test-Path $Builder)) {
    throw "installer\build-installer.ps1 fehlt: $Builder"
}

Write-Host "=== InstantLens Doc build-windows-installer 2.6.25 ==="
Write-Host "Wrapper → installer\build-installer.ps1 (Inno Setup 6)"

$args = @()
if ($SourceRoot) { $args += @("-SourceRoot", $SourceRoot) }
if ($PythonLauncher) { $args += "-PythonLauncher" }
if ($NoKeygen) { $args += "-NoKeygen" }
if ($IsccPath) { $args += @("-IsccPath", $IsccPath) }

& powershell -ExecutionPolicy Bypass -File $Builder @args
$code = $LASTEXITCODE
if ($code -ne 0) { exit $code }

$Dist = Join-Path $Root "dist"
$Setup = Get-ChildItem $Dist -Filter "InstantLensDoc-Setup-2.6.25.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($Setup) {
    Write-Host "Setup.exe: $($Setup.FullName) ($([math]::Round($Setup.Length/1MB, 2)) MB)"
    Write-Host "Kopiere ggf. nach Project-Store docs\InstantLensDoc-2.6.25-Setup.exe"
} else {
    Write-Host "Hinweis: Erwartete Datei dist\InstantLensDoc-Setup-2.6.25.exe prüfen."
}
exit 0
