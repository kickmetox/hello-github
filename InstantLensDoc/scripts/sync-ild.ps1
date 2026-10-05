# InstantLens Doc - Sync nach D:\AI_Temp\InstantLensDoc (eine Datei)
# Laedt Branch von GitHub oder nutzt lokales Pack / Pack-Zip, kopiert, pip, optional Start.
# Eigenes Nutzer-Icon in assets wird NICHT ueberschrieben (neuer/local bleibt).
#
# Eine Zeile:
#   powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1
#
# Optionen:
#   -Branch cursor/instantlensdoc-2108
#   -LocalPack C:\path\to\InstantLensDoc          # Ordner mit App-Quellen
#   -LocalPack C:\path\to\InstantLensDoc-pack.zip # Pack-Zip (wird nach WorkDir entpackt)
#   -Dest / -Destination D:\AI_Temp\InstantLensDoc-2636   # Alias -Dest; frischer Ordner
#   -Swap                 # nach Sync: altes InstantLensDoc -> .bak, Dest -> InstantLensDoc
#   -NoStart / -SkipStart   # App nach Sync nicht starten (synonym)
#   -SkipPip
#   -ForceClean             # Zielinhalt vor Copy leeren (Icons bleiben); Default: an
#   -NoForceClean           # Merge/Overwrite ohne vorheriges Leeren (alte Reste moeglich)
#   -BuildInstaller         # optional: nach Sync Inno-Setup.exe bauen (braucht ISCC)
#   -SkipInstallHints       # keine DE-Hinweise zu install-ild / Setup.exe nach Sync
#
# Pack-Layouts (Zip oder Ordner):
#   - flat: VERSION.txt / build-windows.ps1 / requirements.txt am Extract-Root
#   - nested: ...\InstantLensDoc\ mit denselben Markern (nicht der Python-Ordner instantlensdoc\)
#   Windows ist case-insensitive - Marker-Check verhindert Verwechslung mit dem Paketordner.
#
# Exit-Codes:
#   0  Erfolg (Sync fertig; optional App gestartet; Installer-Build optional)
#   1  Allgemeiner Fehler (LocalPack ungueltig, Ziel gesperrt/in use, requirements fehlen, pip, Installer)
#   2  Git-Sync fehlgeschlagen (Clone/Fetch/Checkout) - Fallback: -LocalPack nutzen
#
# Fallback wenn Git-Clone/Fetch fehlschlaegt (z. B. 401/Auth):
#   1) -LocalPack auf entpackten Ordner oder InstantLensDoc-pack.zip setzen
#   2) oder Zip neben dem Skript ablegen: InstantLensDoc-pack.zip
#   Beispiel:
#     powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1 -LocalPack D:\AI_Temp\InstantLensDoc-pack.zip -SkipStart
#
# Ordner gesperrt (keygen/python/cmd haelt InstantLensDoc-keygen):
#   cd D:\AI_Temp
#   # Keygen-Fenster schliessen, dann:
#   Get-Process python,cmd -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*InstantLens*' }
#   taskkill /F /IM python.exe
#   taskkill /F /IM cmd.exe
#   # optional Sysinternals: handle.exe D:\AI_Temp\InstantLensDoc
#   # Frischer Ordner + Swap:
#   powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1 -LocalPack .\InstantLensDoc-2.6.51-pack.zip -Dest D:\AI_Temp\InstantLensDoc-2636 -Swap -SkipStart
#
# Nach Sync (manuell, ohne -BuildInstaller):
#   cd D:\AI_Temp\InstantLensDoc
#   powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1   # optional, Inno Setup 6

param(
    [Alias("Dest")]
    [string]$Destination = "D:\AI_Temp\InstantLensDoc",
    [string]$Branch = "cursor/instantlensdoc-2108",
    [string]$RepoUrl = "https://github.com/kickmetox/hello-github.git",
    [string]$LocalPack = "",
    [string]$WorkDir = "D:\AI_Temp\InstantLensDoc-src",
    [switch]$Swap,
    [switch]$NoStart,
    [switch]$SkipStart,
    [switch]$SkipPip,
    [switch]$ForceClean,
    [switch]$NoForceClean,
    [switch]$BuildInstaller,
    [switch]$SkipInstallHints
)

$ErrorActionPreference = "Stop"
# -SkipStart ist Alias fuer -NoStart (beide unterdruecken den App-Start)
if ($SkipStart) { $NoStart = $true }
# Clean Sync ist Default (alte Layouts/Reste weg); -NoForceClean deaktiviert
$doClean = $true
if ($NoForceClean) { $doClean = $false }
elseif ($ForceClean) { $doClean = $true }

$script:KeygenFolderNames = @(
    "keygen",
    "InstantLensDoc-keygen",
    "InstantLensKeygen"
)

function Test-AppRoot {
    param([string]$Path)
    if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Container)) { return $false }
    foreach ($marker in @("VERSION.txt", "build-windows.ps1", "requirements.txt")) {
        if (Test-Path -LiteralPath (Join-Path $Path $marker) -PathType Leaf) { return $true }
    }
    return $false
}

function Test-IsKeygenName {
    param([string]$Name)
    if (-not $Name) { return $false }
    foreach ($k in $script:KeygenFolderNames) {
        if ($Name -ieq $k) { return $true }
    }
    if ($Name -like "*keygen*") { return $true }
    return $false
}

function Backup-UserIcons {
    param([string]$Dest)
    $backup = Join-Path $env:TEMP ("ild-icon-backup-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $backup | Out-Null
    $names = @(
        "assets\app.ico", "assets\icon.png", "assets\app.png",
        "assets\lensDoc.jpg", "assets\lensDoc.jpeg", "assets\lensDoc.png",
        "app.ico", "icon.png", "lensDoc.jpg", "lensDoc.jpeg", "lensDoc.png"
    )
    $saved = @()
    foreach ($rel in $names) {
        $p = Join-Path $Dest $rel
        if (Test-Path -LiteralPath $p) {
            $target = Join-Path $backup ($rel -replace "[\\/]", "__")
            Copy-Item -Force -LiteralPath $p -Destination $target
            $saved += [pscustomobject]@{ Rel = $rel; Backup = $target; SrcTime = (Get-Item -LiteralPath $p).LastWriteTimeUtc }
        }
    }
    return [pscustomobject]@{ Dir = $backup; Items = $saved }
}

function Restore-UserIcons {
    param($BackupInfo, [string]$Dest)
    if (-not $BackupInfo -or -not $BackupInfo.Items) { return }
    foreach ($item in $BackupInfo.Items) {
        $destPath = Join-Path $Dest $item.Rel
        $destDir = Split-Path -Parent $destPath
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        # Nutzer-Icon wiederherstellen wenn vorhanden (nie durch Sync ersetzen)
        Copy-Item -Force -LiteralPath $item.Backup -Destination $destPath
        Write-Host "Icon behalten: $($item.Rel)"
    }
    Remove-Item -Recurse -Force -LiteralPath $BackupInfo.Dir -ErrorAction SilentlyContinue
}

function Write-DestinationLockedHint {
    param([string]$Dest, [string]$Detail = "")
    $safe = "D:\AI_Temp"
    $parent = Split-Path -Parent $Dest
    if (-not $parent) { $parent = $safe }
    Write-Host ""
    Write-Host "=== Ordner gesperrt / in Verwendung ===" -ForegroundColor Red
    Write-Host "Ordner: $Dest"
    if ($Detail) { Write-Host "Detail: $Detail" -ForegroundColor DarkYellow }
    Write-Host "Haeufig: Keygen-Fenster (run-keygen.bat), Explorer, oder PowerShell mit cwd IN diesem Ordner."
    Write-Host "Oft gesperrt: InstantLensDoc-keygen / keygen (python.exe oder cmd.exe)."
    Write-Host ""
    Write-Host "1) Ordner verlassen:"
    Write-Host "  cd $safe"
    Write-Host ""
    Write-Host "2) Keygen/Python/cmd mit diesem CWD beenden:"
    Write-Host "  # Fenster schliessen ODER:"
    Write-Host "  taskkill /F /IM python.exe"
    Write-Host "  taskkill /F /IM cmd.exe"
    Write-Host "  # gezielter (Titel):"
    Write-Host '  taskkill /F /IM cmd.exe /FI "WINDOWTITLE eq *keygen*"'
    Write-Host '  taskkill /F /IM python.exe /FI "WINDOWTITLE eq *InstantLens*"'
    Write-Host "  # Prozesse auflisten:"
    Write-Host "  Get-CimInstance Win32_Process -Filter `"Name='python.exe' OR Name='cmd.exe'`" |"
    Write-Host "    Select-Object ProcessId, Name, CommandLine | Format-List"
    Write-Host "  # optional Sysinternals Handle:"
    Write-Host "  # handle.exe `"$Dest`""
    Write-Host ""
    Write-Host "3) Sync erneut (Pack 2.6.38), oder frischer Ordner + Swap:"
    Write-Host "  cd $safe"
    Write-Host '  powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1 -LocalPack D:\AI_Temp\InstantLensDoc-2.6.51-pack.zip -SkipStart'
    Write-Host "  # wenn InstantLensDoc weiter gesperrt:"
    Write-Host '  powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1 -LocalPack D:\AI_Temp\InstantLensDoc-2.6.51-pack.zip -Dest D:\AI_Temp\InstantLensDoc-2636 -Swap -SkipStart'
    Write-Host "Exit-Code 1 = Ziel gesperrt oder Sync-Fehler."
    Write-Host ""
}

function Assert-DestinationWritable {
    param([string]$Dest)
    # Wenn CWD unter Ziel liegt: rauswechseln (sonst Remove/Rename "in use")
    try {
        $cwd = (Get-Location).Path
        $destFull = [System.IO.Path]::GetFullPath($Dest)
        if ($cwd -and $destFull -and $cwd.StartsWith($destFull, [StringComparison]::OrdinalIgnoreCase)) {
            $parent = Split-Path -Parent $destFull
            if (-not $parent) { $parent = "D:\AI_Temp" }
            Write-Host "CWD liegt im Ziel - wechsle nach $parent"
            Set-Location $parent
        }
    } catch {
        Write-DestinationLockedHint -Dest $Dest -Detail $_.Exception.Message
        throw "Zielordner in Verwendung (CWD). Bitte zuerst verlassen: cd D:\AI_Temp"
    }

    if (-not (Test-Path -LiteralPath $Dest)) { return }

    $probe = Join-Path $Dest (".ild-sync-probe-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
    try {
        New-Item -ItemType File -Path $probe -Force | Out-Null
        Remove-Item -LiteralPath $probe -Force
    } catch {
        Write-DestinationLockedHint -Dest $Dest -Detail $_.Exception.Message
        throw "Zielordner gesperrt/in Verwendung. Bitte zuerst verlassen: cd D:\AI_Temp"
    }
}

function Test-PathLikelyLocked {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    try {
        $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
        if ($item.PSIsContainer) {
            $probe = Join-Path $Path (".ild-lock-probe-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
            New-Item -ItemType File -Path $probe -Force -ErrorAction Stop | Out-Null
            Remove-Item -LiteralPath $probe -Force -ErrorAction Stop
            return $false
        } else {
            $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
            $fs.Close()
            return $false
        }
    } catch {
        return $true
    }
}

function Remove-TreeHardened {
    param(
        [string]$Path,
        [int]$Retries = 2,
        [switch]$AllowSkipKeygen
    )
    if (-not (Test-Path -LiteralPath $Path)) { return $true }
    $name = Split-Path -Leaf $Path
    $isKeygen = Test-IsKeygenName $name

    for ($attempt = 1; $attempt -le ($Retries + 1); $attempt++) {
        try {
            if ((Test-Path -LiteralPath $Path -PathType Container)) {
                # Kinder einzeln zuerst (oft sperrt nur eine Datei den Parent)
                $children = @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue)
                foreach ($child in $children) {
                    $okChild = Remove-TreeHardened -Path $child.FullName -Retries 1 -AllowSkipKeygen:$AllowSkipKeygen
                    if (-not $okChild -and -not ($AllowSkipKeygen -and (Test-IsKeygenName $child.Name))) {
                        throw "Kind gesperrt: $($child.FullName)"
                    }
                }
            }
            Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
            return $true
        } catch {
            $err = $_.Exception.Message
            if ($attempt -le $Retries) {
                Write-Host "Remove Retry $attempt/$Retries : $name ($err)" -ForegroundColor DarkYellow
                Start-Sleep -Milliseconds (400 * $attempt)
                continue
            }
            if ($isKeygen -and $AllowSkipKeygen) {
                Write-Host "WARNUNG: Keygen-Ordner gesperrt - ueberspringe (spaeter Sync/Swap): $Path" -ForegroundColor Yellow
                Write-Host "  Detail: $err" -ForegroundColor DarkYellow
                return $false
            }
            throw
        }
    }
    return $false
}

function Clear-DestinationContents {
    param([string]$Dest)
    if (-not (Test-Path -LiteralPath $Dest)) { return }
    Write-Host "ForceClean: leere Zielinhalt (Icons bereits gesichert)..."
    $skipped = @()
    $failed = @()
    Get-ChildItem -LiteralPath $Dest -Force | ForEach-Object {
        if ($_.Name -in @(".venv", "__pycache__", ".git", ".smoke_license.json")) {
            return
        }
        $full = $_.FullName
        $nm = $_.Name
        if (Test-PathLikelyLocked -Path $full) {
            Write-Host "Gesperrt erkannt: $nm" -ForegroundColor DarkYellow
        }
        try {
            $ok = Remove-TreeHardened -Path $full -Retries 2 -AllowSkipKeygen
            if (-not $ok) {
                $skipped += $nm
            }
        } catch {
            $failed += [pscustomobject]@{ Name = $nm; Error = $_.Exception.Message }
        }
    }
    if ($failed.Count -gt 0) {
        $detail = ($failed | ForEach-Object { "$($_.Name): $($_.Error)" }) -join "; "
        Write-DestinationLockedHint -Dest $Dest -Detail $detail
        throw "Zielordner in Verwendung - kann '$($failed[0].Name)' nicht entfernen. Bitte Keygen/python/cmd schliessen: cd D:\AI_Temp"
    }
    if ($skipped.Count -gt 0) {
        Write-Host "ForceClean: Keygen-Reste uebersprungen (gesperrt): $($skipped -join ', ')" -ForegroundColor Yellow
        Write-Host "Tipp: -Dest InstantLensDoc-2636 -Swap  ODER Keygen-Fenster schliessen und Sync erneut." -ForegroundColor Yellow
    }
}

function Invoke-DestinationSwap {
    param(
        [string]$SyncedPath,
        [string]$FinalName = "InstantLensDoc"
    )
    $parent = Split-Path -Parent $SyncedPath
    if (-not $parent) { $parent = "D:\AI_Temp" }
    $finalPath = Join-Path $parent $FinalName
    $syncedFull = [System.IO.Path]::GetFullPath($SyncedPath)
    $finalFull = [System.IO.Path]::GetFullPath($finalPath)
    if ($syncedFull -ieq $finalFull) {
        Write-Host "Swap: Dest ist bereits $FinalName - kein Rename noetig."
        return $finalPath
    }
    # CWD raus
    try {
        $cwd = (Get-Location).Path
        if ($cwd -and ($cwd.StartsWith($finalFull, [StringComparison]::OrdinalIgnoreCase) -or $cwd.StartsWith($syncedFull, [StringComparison]::OrdinalIgnoreCase))) {
            Set-Location $parent
        }
    } catch { Set-Location $parent }

    if (Test-Path -LiteralPath $finalPath) {
        $bak = Join-Path $parent ("${FinalName}.bak-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
        Write-Host "Swap: benenne $finalPath -> $bak"
        try {
            Rename-Item -LiteralPath $finalPath -NewName (Split-Path -Leaf $bak) -ErrorAction Stop
        } catch {
            Write-DestinationLockedHint -Dest $finalPath -Detail $_.Exception.Message
            throw "Swap fehlgeschlagen (altes Ziel gesperrt). Dest bleibt: $SyncedPath. Manuell: Keygen schliessen, dann Rename."
        }
    }
    Write-Host "Swap: benenne $SyncedPath -> $finalPath"
    try {
        Rename-Item -LiteralPath $SyncedPath -NewName $FinalName -ErrorAction Stop
    } catch {
        Write-DestinationLockedHint -Dest $SyncedPath -Detail $_.Exception.Message
        throw "Swap Rename Dest->InstantLensDoc fehlgeschlagen. Frischer Tree liegt unter: $SyncedPath"
    }
    return $finalPath
}

function Resolve-PackSource {
    param([string]$PackPath, [string]$UnpackRoot)
    if (-not $PackPath -or -not (Test-Path -LiteralPath $PackPath)) { return $null }
    $item = Get-Item -LiteralPath $PackPath

    if ($item.PSIsContainer) {
        $folder = (Resolve-Path -LiteralPath $PackPath).Path
        if (Test-AppRoot $folder) {
            Write-Host "Pack-Root (Ordner, flat/app): $folder"
            return $folder
        }
        $nested = Join-Path $folder "InstantLensDoc"
        if ((Test-Path -LiteralPath $nested -PathType Container) -and (Test-AppRoot $nested)) {
            Write-Host "Pack-Root (Ordner, nested InstantLensDoc/): $nested"
            return (Resolve-Path -LiteralPath $nested).Path
        }
        Write-Warning "LocalPack-Ordner ohne App-Marker (VERSION.txt / build-windows.ps1 / requirements.txt): $folder"
        return $null
    }

    if ($item.Extension -ieq ".zip") {
        $unpack = Join-Path $UnpackRoot ("pack-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
        New-Item -ItemType Directory -Force -Path $unpack | Out-Null
        Write-Host "Entpacke Pack-Zip: $($item.FullName) -> $unpack"
        Expand-Archive -Force -Path $item.FullName -DestinationPath $unpack

        # 1) Flat: Marker am Extract-Root (auch wenn instantlensdoc\ Python-Paket daneben liegt)
        if (Test-AppRoot $unpack) {
            Write-Host "Pack-Layout: flat (Marker am Zip-Root)"
            return (Resolve-Path -LiteralPath $unpack).Path
        }

        # 2) Nested: InstantLensDoc\ mit App-Markern (nicht bloss Python-Paket)
        $nestedCandidates = @(
            (Join-Path $unpack "InstantLensDoc"),
            (Join-Path $unpack "instantlensdoc")
        )
        foreach ($cand in $nestedCandidates) {
            if ((Test-Path -LiteralPath $cand -PathType Container) -and (Test-AppRoot $cand)) {
                Write-Host "Pack-Layout: nested -> $cand"
                return (Resolve-Path -LiteralPath $cand).Path
            }
        }

        # 3) Eine Ebene tiefer suchen (manchmal Zip/Zip)
        $dirs = Get-ChildItem -LiteralPath $unpack -Directory -ErrorAction SilentlyContinue
        foreach ($d in $dirs) {
            if (Test-AppRoot $d.FullName) {
                Write-Host "Pack-Layout: Unterordner mit Markern -> $($d.FullName)"
                return (Resolve-Path -LiteralPath $d.FullName).Path
            }
            $inner = Join-Path $d.FullName "InstantLensDoc"
            if ((Test-Path -LiteralPath $inner -PathType Container) -and (Test-AppRoot $inner)) {
                Write-Host "Pack-Layout: nested unter $($d.Name) -> $inner"
                return (Resolve-Path -LiteralPath $inner).Path
            }
        }

        Write-Warning "Pack-Zip ohne App-Root (weder flat noch nested InstantLensDoc/ mit VERSION.txt|build-windows.ps1|requirements.txt): $($item.FullName)"
        return $null
    }

    Write-Warning "LocalPack ist weder Ordner noch .zip: $PackPath"
    return $null
}

function Write-LocalPackHint {
    param([string]$Reason)
    Write-Host ""
    Write-Host "=== Git-Sync fehlgeschlagen ($Reason) ===" -ForegroundColor Yellow
    Write-Host "Fallback: lokales Pack nutzen:"
    Write-Host '  powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1 -LocalPack D:\AI_Temp\InstantLensDoc-2.6.51-pack.zip -SkipStart'
    Write-Host "oder frischer Ordner + Swap bei Sperre:"
    Write-Host '  powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1 -LocalPack D:\AI_Temp\InstantLensDoc-2.6.51-pack.zip -Dest D:\AI_Temp\InstantLensDoc-2636 -Swap -SkipStart'
    Write-Host "oder entpackten Ordner:"
    Write-Host '  powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1 -LocalPack D:\AI_Temp\InstantLensDoc-pack -SkipStart'
    Write-Host "Pack-Zip: InstantLensDoc-*-pack.zip (Store docs / Agent-Ausgabe)."
    Write-Host "Exit-Code 2 = Git-Fehler; Exit-Code 1 = sonstiger Fehler; 0 = OK."
    Write-Host ""
}

try {
    Write-Host "=== InstantLens Doc Sync ==="
    Write-Host "Ziel: $Destination"
    if ($Swap) { Write-Host "Swap: nach Sync -> InstantLensDoc (altes Ziel wird .bak)" }
    if ($NoStart) { Write-Host "Start: uebersprungen (-NoStart/-SkipStart)" }
    if ($doClean) { Write-Host "Clean: ForceClean (Zielinhalt leeren, Icons behalten; Keygen skip-or-retry)" }
    else { Write-Host "Clean: aus (-NoForceClean) - Merge/Overwrite" }

    Assert-DestinationWritable -Dest $Destination
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $iconBackup = Backup-UserIcons -Dest $Destination

    $appSrc = $null

    # 1) Explizites -LocalPack (Ordner oder Zip)
    if ($LocalPack) {
        $appSrc = Resolve-PackSource -PackPath $LocalPack -UnpackRoot (Split-Path $WorkDir -Parent)
        if (-not $appSrc) {
            Write-Error "LocalPack nicht nutzbar: $LocalPack"
            exit 1
        }
        Write-Host "Lokal: $appSrc"
    }

    # 2) Zip neben dem Skript (Fallback ohne Parameter)
    if (-not $appSrc) {
        $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
        $parentDir = Split-Path $scriptDir -Parent
        $sideCandidates = @(
            (Join-Path $scriptDir "InstantLensDoc-pack.zip"),
            (Join-Path $parentDir "InstantLensDoc-pack.zip"),
            (Join-Path $parentDir "InstantLensDoc-2.6.51-pack.zip"),
            (Join-Path $parentDir "InstantLensDoc-2.6.45-pack.zip"),
            (Join-Path $parentDir "InstantLensDoc-2.6.44-pack.zip"),            (Join-Path $parentDir "InstantLensDoc-2.6.43-pack.zip"),
            (Join-Path $parentDir "InstantLensDoc-2.6.42-pack.zip"),
            (Join-Path $parentDir "InstantLensDoc-2.6.41-pack.zip"),
            (Join-Path $parentDir "InstantLensDoc-2.6.35-pack.zip"),
            (Join-Path $parentDir "InstantLensDoc-2.6.34-pack.zip"),
            "D:\AI_Temp\InstantLensDoc-2.6.51-pack.zip",
            "D:\AI_Temp\InstantLensDoc-2.6.45-pack.zip",
            "D:\AI_Temp\InstantLensDoc-2.6.44-pack.zip",            "D:\AI_Temp\InstantLensDoc-2.6.43-pack.zip",
            "D:\AI_Temp\InstantLensDoc-2.6.42-pack.zip",
            "D:\AI_Temp\InstantLensDoc-2.6.41-pack.zip",
            "D:\AI_Temp\InstantLensDoc-2.6.35-pack.zip",
            "D:\AI_Temp\InstantLensDoc-2.6.34-pack.zip",
            "D:\AI_Temp\InstantLensDoc-pack.zip"
        )
        foreach ($z in $sideCandidates) {
            if (Test-Path -LiteralPath $z) {
                Write-Host "Pack-Zip gefunden: $z"
                $appSrc = Resolve-PackSource -PackPath $z -UnpackRoot (Split-Path $WorkDir -Parent)
                if ($appSrc) { break }
            }
        }
    }

    # 3) Git clone/fetch
    if (-not $appSrc) {
        try {
            if (-not (Test-Path -LiteralPath $WorkDir)) {
                Write-Host "Clone $RepoUrl ($Branch) -> $WorkDir"
                git clone --branch $Branch --single-branch $RepoUrl $WorkDir
                if ($LASTEXITCODE -ne 0) { throw "git clone exit $LASTEXITCODE" }
            } else {
                Write-Host "Fetch/Reset $WorkDir @ $Branch"
                Push-Location $WorkDir
                git fetch origin $Branch
                if ($LASTEXITCODE -ne 0) { Pop-Location; throw "git fetch exit $LASTEXITCODE" }
                git checkout $Branch
                git reset --hard "origin/$Branch"
                Pop-Location
            }
            $candidate = Join-Path $WorkDir "InstantLensDoc"
            if (Test-AppRoot $candidate) {
                $appSrc = $candidate
            } elseif (Test-AppRoot $WorkDir) {
                $appSrc = $WorkDir
            } else {
                throw "App-Quellordner nicht gefunden unter $WorkDir (Marker VERSION.txt|build-windows.ps1|requirements.txt)"
            }
        } catch {
            Write-LocalPackHint -Reason $_.Exception.Message
            exit 2
        }
    }

    if (-not (Test-AppRoot $appSrc)) {
        Write-Error "Quelle ist kein App-Root (fehlende Marker): $appSrc"
        exit 1
    }

    if ($doClean) {
        Assert-DestinationWritable -Dest $Destination
        Clear-DestinationContents -Dest $Destination
    }

    Write-Host "Kopiere von $appSrc -> $Destination"
    Get-ChildItem -LiteralPath $appSrc -Force | ForEach-Object {
        if ($_.Name -in @(".venv", "__pycache__", ".git", ".smoke_license.json")) {
            return
        }
        # Alte Pack-Zips im Tree nicht mitkopieren
        if ($_.Name -like "InstantLensDoc-*-pack.zip") { return }
        $destChild = Join-Path $Destination $_.Name
        # Wenn Keygen-Ziel noch gesperrt (Skip bei ForceClean): nicht ueberschreiben-erzwingen
        if ((Test-IsKeygenName $_.Name) -and (Test-Path -LiteralPath $destChild) -and (Test-PathLikelyLocked -Path $destChild)) {
            Write-Host "WARNUNG: ueberspringe Kopie von '$($_.Name)' - Ziel gesperrt. Nutze -Dest ... -Swap." -ForegroundColor Yellow
            return
        }
        try {
            Copy-Item -Recurse -Force -LiteralPath $_.FullName -Destination $Destination
        } catch {
            if (Test-IsKeygenName $_.Name) {
                Write-Host "WARNUNG: Keygen-Kopie fehlgeschlagen (gesperrt): $($_.Exception.Message)" -ForegroundColor Yellow
                return
            }
            Write-DestinationLockedHint -Dest $Destination -Detail $_.Exception.Message
            throw "Kopieren fehlgeschlagen (Ziel gesperrt?): $($_.Exception.Message)"
        }
    }

    Restore-UserIcons -BackupInfo $iconBackup -Dest $Destination

    # Falls Nutzer-Icon im Root liegt -> nach assets spiegeln
    $rootJpg = Join-Path $Destination "lensDoc.jpg"
    $assetsPng = Join-Path $Destination "assets\icon.png"
    New-Item -ItemType Directory -Force -Path (Join-Path $Destination "assets") | Out-Null
    if ((Test-Path -LiteralPath $rootJpg) -and -not (Test-Path -LiteralPath $assetsPng)) {
        Copy-Item -Force -LiteralPath $rootJpg -Destination $assetsPng
        Write-Host "Icon aus lensDoc.jpg -> assets\icon.png"
    }

    # Listing ohne dauerhaftes Set-Location ins Ziel (vermeidet "in use" bei spaeterem Rename)
    $prevLoc = Get-Location
    try {
        Set-Location $Destination
        Write-Host "=== Inhalt ==="
        Get-ChildItem $Destination | Select-Object Name, Length | Format-Table -AutoSize
    } finally {
        try { Set-Location $prevLoc } catch { Set-Location (Split-Path -Parent $Destination) }
    }

    foreach ($must in @("requirements.txt", "VERSION.txt", "build-windows.ps1", "scripts\build-windows-installer.ps1")) {
        if (-not (Test-Path -LiteralPath (Join-Path $Destination $must))) {
            Write-Error "$must fehlt nach Sync. Pack-Layout/Clean pruefen. Quelle war: $appSrc"
            exit 1
        }
    }

    if (-not $SkipPip) {
        Write-Host "pip install -r requirements.txt ..."
        Push-Location $Destination
        try {
            python -m pip install -r requirements.txt
            if ($LASTEXITCODE -ne 0) {
                Write-Error "pip install fehlgeschlagen (exit $LASTEXITCODE)"
                exit 1
            }
        } finally {
            Pop-Location
        }
    }

    # Optional: Inno Setup.exe nach Sync (Windows x64 + ISCC)
    if ($BuildInstaller) {
        $buildInst = Join-Path $Destination "scripts\build-windows-installer.ps1"
        if (-not (Test-Path -LiteralPath $buildInst)) {
            Write-Error "build-windows-installer.ps1 fehlt: $buildInst"
            exit 1
        }
        Write-Host "=== Optional: Windows-Installer bauen (-BuildInstaller) ===" -ForegroundColor Cyan
        Write-Host "Voraussetzung: Inno Setup 6 (ISCC.exe). Bei Fehler ohne ISCC: Exit 1."
        Push-Location $Destination
        try {
            & powershell -ExecutionPolicy Bypass -File $buildInst
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Installer-Build fehlgeschlagen (exit $LASTEXITCODE). Ohne -BuildInstaller syncen und ISCC pruefen."
                exit 1
            }
        } finally {
            Pop-Location
        }
    }

    if ($Swap) {
        $Destination = Invoke-DestinationSwap -SyncedPath $Destination -FinalName "InstantLensDoc"
        Write-Host "Swap fertig. Aktives Ziel: $Destination"
    }

    if (-not $SkipInstallHints) {
        Write-Host ""
        Write-Host "=== Nach Sync (Windows) ===" -ForegroundColor Cyan
        Write-Host "Shortcuts (User-Profil, ohne Admin):"
        Write-Host '  powershell -ExecutionPolicy Bypass -File .\scripts\install-ild.ps1'
        Write-Host "Setup.exe (optional, Inno Setup 6):"
        Write-Host '  powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-installer.ps1'
        Write-Host "Oder Sync mit Installer-Build:"
        Write-Host '  powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1 -BuildInstaller -SkipStart'
        Write-Host "Bei Ordner-Sperre: -Dest D:\AI_Temp\InstantLensDoc-2636 -Swap"
        Write-Host "Keygen: run-keygen.bat | Scripting: python -m ild --help | .\scripts\ild.ps1"
        Write-Host "Verify: Test-Path D:\AI_Temp\InstantLensDoc\build-windows.ps1"
        Write-Host "Verify: Test-Path D:\AI_Temp\InstantLensDoc\scripts\build-windows-installer.ps1"
        Write-Host ""
    }

    if (-not $NoStart) {
        Write-Host "Starte InstantLens Doc..."
        $run = Join-Path $Destination "run.bat"
        if (Test-Path -LiteralPath $run) {
            Push-Location $Destination
            try { & $run } finally { Pop-Location }
        } else {
            Push-Location $Destination
            try { python -m instantlensdoc } finally { Pop-Location }
        }
    }

    Write-Host "Sync fertig. (exit 0)"
    exit 0
} catch {
    $msg = $_.Exception.Message
    Write-Host "Sync-Fehler: $msg" -ForegroundColor Red
    if ($msg -match "in Verwendung|gesperrt|in use|cannot remove|being used|cannot access|Access is denied") {
        Write-DestinationLockedHint -Dest $Destination -Detail $msg
    }
    exit 1
}
