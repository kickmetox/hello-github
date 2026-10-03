# InstantLens Doc 2.2.0 — Benutzer-Installer (ohne Admin wenn möglich)
# Startmenü-Shortcut + optional Desktop-Link (User-Profil).
# Idempotent: vorhandene Verknüpfungen werden aktualisiert.
# -Uninstall entfernt Startmenü- und Desktop-Shortcuts.
# Fehlende Shortcuts bei -Uninstall sind kein Fehler (Log-Zeile, Exit 0).
# -Uninstall schreibt Log-Datei und gibt den Pfad aus; -Quiet unterdrückt Prompts.
# -Quiet -Uninstall: Exit 0 auch wenn nichts zu entfernen; Kurz-Summary auf stdout.
#
# Beispiele:
#   powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1 -DesktopLink
#   powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1 -AppDir "D:\AI_Temp\InstantLensDoc" -NoDesktop
#   powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1 -Uninstall
#   powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1 -Uninstall -Quiet
#
# Hinweis Sync (Code aktualisieren):
#   powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"
#   (oder .\scripts\sync-ild.ps1 neben der App / Store-Kopie)
#
# Exit-Codes:
#   0  Erfolg (Install/Update/Uninstall OK; nichts zu entfernen bei -Uninstall = OK; Abbruch Prompt = 0)
#   1  Fehler (App-Ordner fehlt, Shortcut anlegen/entfernen fehlgeschlagen, Parameterkonflikt)

[CmdletBinding()]
param(
    [string]$AppDir = "",
    [switch]$DesktopLink,
    [switch]$NoDesktop,
    [switch]$SkipStartMenu,
    [switch]$Uninstall,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$Version = "2.2.0"
$AppName = "InstantLens Doc"

function Write-IldInfo([string]$msg) { Write-Host "[ILD $Version] $msg" }
function Write-IldWarn([string]$msg) { Write-Host "[ILD $Version] Hinweis: $msg" -ForegroundColor Yellow }
function Write-IldErr([string]$msg) { Write-Host "[ILD $Version] FEHLER: $msg" -ForegroundColor Red }

function Get-IldLogDir {
    $base = $env:LOCALAPPDATA
    if (-not $base) { $base = $env:TEMP }
    if (-not $base) { $base = $env:TMP }
    if (-not $base) { $base = "." }
    $dir = Join-Path $base "InstantLensDoc\logs"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    return $dir
}

function New-IldUninstallLogPath {
    $dir = Get-IldLogDir
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    return (Join-Path $dir "install-ild-uninstall-$stamp.log")
}

function Write-IldLogLine {
    param(
        [Parameter(Mandatory = $true)][string]$LogPath,
        [Parameter(Mandatory = $true)][string]$Message
    )
    $line = "{0:yyyy-MM-dd HH:mm:ss}  {1}" -f (Get-Date), $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

function Get-IldShortcutPaths {
    $paths = @()
    $startPrograms = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    $paths += Join-Path $startPrograms "$AppName.lnk"
    $desktop = [Environment]::GetFolderPath("Desktop")
    if (-not $desktop) { $desktop = Join-Path $env:USERPROFILE "Desktop" }
    $paths += Join-Path $desktop "$AppName.lnk"
    return $paths
}

# --- Uninstall: Shortcuts entfernen ---
if ($Uninstall) {
    if ($DesktopLink -or $NoDesktop -or $SkipStartMenu) {
        Write-IldWarn "-Uninstall ignoriert -DesktopLink/-NoDesktop/-SkipStartMenu (entfernt Startmenü + Desktop)."
    }

    $logPath = New-IldUninstallLogPath
    if (-not $Quiet) {
        Write-IldInfo "Log-Datei: $logPath"
    }
    Write-IldLogLine -LogPath $logPath -Message "Uninstall gestartet (Version $Version; Quiet=$Quiet)"

    if (-not $Quiet) {
        Write-Host ""
        Write-Host "InstantLens Doc — Shortcuts entfernen (Startmenü + Desktop)." -ForegroundColor Yellow
        $answer = Read-Host "Fortfahren? (J/N)"
        if ($answer -notmatch '^[jJyY]') {
            Write-IldInfo "Uninstall abgebrochen (Prompt). Exit 0."
            Write-IldLogLine -LogPath $logPath -Message "Uninstall abgebrochen durch Prompt"
            Write-IldInfo "Log-Datei: $logPath"
            exit 0
        }
    } else {
        Write-IldLogLine -LogPath $logPath -Message "Quiet: Prompt übersprungen"
    }

    $removed = @()
    $missing = @()
    $failed = @()
    foreach ($link in Get-IldShortcutPaths) {
        if (Test-Path -LiteralPath $link) {
            try {
                Remove-Item -LiteralPath $link -Force
                $removed += $link
                if (-not $Quiet) {
                    Write-IldInfo "Shortcut entfernt: $link"
                }
                Write-IldLogLine -LogPath $logPath -Message "entfernt: $link"
            } catch {
                $failed += $link
                Write-IldErr "Entfernen fehlgeschlagen: $link — $_"
                Write-IldLogLine -LogPath $logPath -Message "FEHLER: $link — $_"
            }
        } else {
            $missing += $link
            if (-not $Quiet) {
                Write-IldInfo "Shortcut fehlt bereits (kein Fehler): $link"
            }
            Write-IldLogLine -LogPath $logPath -Message "fehlt bereits: $link"
        }
    }
    if ($failed.Count -gt 0) {
        Write-IldErr "Uninstall unvollständig ($($failed.Count) Fehler)."
        Write-IldLogLine -LogPath $logPath -Message "Uninstall unvollständig ($($failed.Count) Fehler)"
        # Kurz-Summary auch bei Fehler — 2.0.5
        Write-Host "Uninstall: entfernt=$($removed.Count) fehlend=$($missing.Count) fehler=$($failed.Count) Exit=1"
        Write-IldInfo "Log-Datei: $logPath"
        exit 1
    }
    # Nichts zu entfernen (alles fehlte bereits) = Exit 0 — 2.0.5
    if ($removed.Count -eq 0) {
        Write-IldLogLine -LogPath $logPath -Message "nichts zu entfernen ($($missing.Count) fehlten bereits) — Exit 0"
    }
    if (-not $Quiet) {
        if ($missing.Count -gt 0) {
            Write-IldInfo "fehlende Shortcuts kein Fehler ($($missing.Count) fehlten bereits)."
        }
        Write-IldInfo "Uninstall fertig: $($removed.Count) entfernt, $($missing.Count) fehlten bereits. Exit 0."
        Write-IldInfo "Log-Datei: $logPath"
    }
    Write-IldLogLine -LogPath $logPath -Message "Uninstall fertig: $($removed.Count) entfernt, $($missing.Count) fehlten bereits"
    # Kurz-Summary immer auf stdout (Quiet: einzige Erfolgszeile) — 2.0.5
    Write-Host "Uninstall: entfernt=$($removed.Count) fehlend=$($missing.Count) Exit=0"
    if ($Quiet) {
        Write-Host "Log: $logPath"
    }
    exit 0
}

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
    Write-IldInfo "Tipp: -AppDir `"D:\AI_Temp\InstantLensDoc`" setzen oder zuerst sync-ild.ps1 ausführen."
    Write-IldInfo "Exit-Code 1 = Fehler; 0 = OK. -Uninstall braucht keinen App-Ordner."
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
    $existed = Test-Path -LiteralPath $LinkPath
    $wsh = New-Object -ComObject WScript.Shell
    $sc = $wsh.CreateShortcut($LinkPath)
    $sc.TargetPath = $TargetPath
    if ($WorkingDirectory) { $sc.WorkingDirectory = $WorkingDirectory }
    if ($IconLocation) { $sc.IconLocation = $IconLocation }
    if ($Description) { $sc.Description = $Description }
    $sc.Save()
    return [pscustomobject]@{
        Path = $LinkPath
        Updated = [bool]$existed
    }
}

$created = @()
$updated = @()

# Startmenü (Benutzer, kein Admin) — %APPDATA%\Microsoft\Windows\Start Menu\Programs
if (-not $SkipStartMenu) {
    $startPrograms = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    $startLink = Join-Path $startPrograms "$AppName.lnk"
    try {
        $r = New-UserShortcut -LinkPath $startLink -TargetPath $runBat `
            -WorkingDirectory $AppDir -IconLocation $iconPath `
            -Description "$AppName $Version"
        if ($r.Updated) {
            $updated += $r.Path
            Write-IldInfo "Startmenü-Shortcut aktualisiert (idempotent): $($r.Path)"
        } else {
            $created += $r.Path
            Write-IldInfo "Startmenü-Shortcut angelegt: $($r.Path)"
        }
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
        $r = New-UserShortcut -LinkPath $deskLink -TargetPath $runBat `
            -WorkingDirectory $AppDir -IconLocation $iconPath `
            -Description "$AppName $Version"
        if ($r.Updated) {
            $updated += $r.Path
            Write-IldInfo "Desktop-Link aktualisiert (idempotent): $($r.Path)"
        } else {
            $created += $r.Path
            Write-IldInfo "Desktop-Link angelegt: $($r.Path)"
        }
    } catch {
        Write-IldErr "Desktop-Link fehlgeschlagen: $_"
        # Desktop optional — kein harter Abbruch wenn Startmenü schon ok
        if (($created.Count + $updated.Count) -eq 0) { exit 1 }
    }
} else {
    Write-IldInfo "Desktop-Link übersprungen (-NoDesktop)."
}

$total = $created.Count + $updated.Count
Write-IldInfo "Fertig ($total Verknüpfung(en): $($created.Count) neu, $($updated.Count) aktualisiert). Ohne Admin (User-Profil)."
Write-IldInfo "App: $AppDir"
Write-IldWarn "Code aktualisieren mit sync-ild.ps1, z. B.:"
Write-Host '  powershell -ExecutionPolicy Bypass -File "D:\AI_Temp\sync-ild.ps1"'
$syncLocal = Join-Path $AppDir "scripts\sync-ild.ps1"
if (Test-Path $syncLocal) {
    Write-Host ("  powershell -ExecutionPolicy Bypass -File `"{0}`"" -f $syncLocal)
}
Write-IldInfo "Exit-Codes: 0 OK · 1 Fehler. Deinstallieren: -Uninstall [-Quiet]"
exit 0
