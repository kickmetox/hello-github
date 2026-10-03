# InstantLens Doc 2.0 — Benutzer-Installer (ohne Admin wenn möglich)
# Startmenü-Shortcut + optional Desktop-Link (User-Profil).
#
# Beispiele:
#   powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1 -DesktopLink
#   powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1 -AppDir "D:\AI_Temp\InstantLensDoc" -NoDesktop
#
# Exit: 0 OK · 1 Fehler

[CmdletBinding()]
param(
    [string]$AppDir = "",
    [switch]$DesktopLink,
    [switch]$NoDesktop,
    [switch]$SkipStartMenu
)

$ErrorActionPreference = "Stop"
$Version = "2.0.0"
$AppName = "InstantLens Doc"

function Write-IldInfo([string]$msg) { Write-Host "[ILD $Version] $msg" }
function Write-IldErr([string]$msg) { Write-Host "[ILD $Version] FEHLER: $msg" -ForegroundColor Red }

# App-Wurzel ermitteln (Skript liegt unter …/InstantLensDoc/scripts/)
if (-not $AppDir) {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $candidate = Split-Path -Parent $scriptRoot
    if (Test-Path (Join-Path $candidate "run.bat")) {
        $AppDir = $candidate
    } elseif (Test-Path "D:\AI_Temp\InstantLensDoc\run.bat") {
        $AppDir = "D:\AI_Temp\InstantLensDoc"
    } else {
        $AppDir = $candidate
    }
}
try {
    $AppDir = (Resolve-Path -LiteralPath $AppDir).Path
} catch {
    $AppDir = $null
}
if (-not $AppDir -or -not (Test-Path (Join-Path $AppDir "run.bat"))) {
    Write-IldErr "App-Ordner mit run.bat nicht gefunden: $AppDir"
    exit 1
}

$runBat = Join-Path $AppDir "run.bat"
$iconIco = Join-Path $AppDir "assets\app.ico"
$iconPng = Join-Path $AppDir "assets\icon.png"
$iconPath = if (Test-Path $iconIco) { $iconIco } elseif (Test-Path $iconPng) { $iconPng } else { $runBat }

function New-UserShortcut {
    param(
        [Parameter(Mandatory = $true)][string]$LinkPath,
        [Parameter(Mandatory = $true)][string]$TargetPath,
        [string]$WorkingDirectory = "",
        [string]$IconLocation = "",
        [string]$Description = ""
    )
    $dir = Split-Path -Parent $LinkPath
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $wsh = New-Object -ComObject WScript.Shell
    $sc = $wsh.CreateShortcut($LinkPath)
    $sc.TargetPath = $TargetPath
    if ($WorkingDirectory) { $sc.WorkingDirectory = $WorkingDirectory }
    if ($IconLocation) { $sc.IconLocation = $IconLocation }
    if ($Description) { $sc.Description = $Description }
    $sc.Save()
    return $LinkPath
}

$created = @()

# Startmenü (Benutzer, kein Admin) — %APPDATA%\Microsoft\Windows\Start Menu\Programs
if (-not $SkipStartMenu) {
    $startPrograms = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    $startLink = Join-Path $startPrograms "$AppName.lnk"
    try {
        $p = New-UserShortcut -LinkPath $startLink -TargetPath $runBat `
            -WorkingDirectory $AppDir -IconLocation $iconPath `
            -Description "$AppName $Version"
        $created += $p
        Write-IldInfo "Startmenü-Shortcut: $p"
    } catch {
        Write-IldErr "Startmenü-Shortcut fehlgeschlagen: $_"
        exit 1
    }
}

# Desktop optional (Standard: an, außer -NoDesktop; -DesktopLink erzwingt)
$wantDesktop = $true
if ($NoDesktop) { $wantDesktop = $false }
if ($DesktopLink) { $wantDesktop = $true }
if ($wantDesktop) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    if (-not $desktop) { $desktop = Join-Path $env:USERPROFILE "Desktop" }
    $deskLink = Join-Path $desktop "$AppName.lnk"
    try {
        $p = New-UserShortcut -LinkPath $deskLink -TargetPath $runBat `
            -WorkingDirectory $AppDir -IconLocation $iconPath `
            -Description "$AppName $Version"
        $created += $p
        Write-IldInfo "Desktop-Link: $p"
    } catch {
        Write-IldErr "Desktop-Link fehlgeschlagen: $_"
        # Desktop optional — kein harter Abbruch wenn Startmenü schon ok
        if ($created.Count -eq 0) { exit 1 }
    }
}

Write-IldInfo "Fertig ($($created.Count) Verknüpfung(en)). Ohne Admin (User-Profil)."
Write-IldInfo "App: $AppDir"
exit 0
