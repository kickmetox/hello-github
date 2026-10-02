# InstantLens Doc — Sync nach D:\AI_Temp\InstantLensDoc (eine Datei)
# Lädt Branch von GitHub oder nutzt lokales Pack / Pack-Zip, kopiert, pip, optional Start.
# Eigenes Nutzer-Icon in assets wird NICHT überschrieben (neuer/local bleibt).
#
# Eine Zeile:
#   powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1
#
# Optionen:
#   -Branch cursor/instantlensdoc-2108
#   -LocalPack C:\path\to\InstantLensDoc          # Ordner mit App-Quellen
#   -LocalPack C:\path\to\InstantLensDoc-pack.zip # Pack-Zip (wird nach WorkDir entpackt)
#   -NoStart
#   -SkipPip
#
# Fallback wenn Git-Clone/Fetch fehlschlägt (z. B. 401/Auth):
#   1) -LocalPack auf entpackten Ordner oder InstantLensDoc-pack.zip setzen
#   2) oder Zip neben dem Skript ablegen: InstantLensDoc-pack.zip
#   Beispiel:
#     powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1 -LocalPack D:\AI_Temp\InstantLensDoc-pack.zip

param(
    [string]$Destination = "D:\AI_Temp\InstantLensDoc",
    [string]$Branch = "cursor/instantlensdoc-2108",
    [string]$RepoUrl = "https://github.com/kickmetox/hello-github.git",
    [string]$LocalPack = "",
    [string]$WorkDir = "D:\AI_Temp\InstantLensDoc-src",
    [switch]$NoStart,
    [switch]$SkipPip
)

$ErrorActionPreference = "Stop"

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
        if (Test-Path $p) {
            $target = Join-Path $backup ($rel -replace "[\\/]", "__")
            Copy-Item -Force $p $target
            $saved += [pscustomobject]@{ Rel = $rel; Backup = $target; SrcTime = (Get-Item $p).LastWriteTimeUtc }
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
        Copy-Item -Force $item.Backup $destPath
        Write-Host "Icon behalten: $($item.Rel)"
    }
    Remove-Item -Recurse -Force $BackupInfo.Dir -ErrorAction SilentlyContinue
}

function Resolve-PackSource {
    param([string]$PackPath, [string]$UnpackRoot)
    if (-not $PackPath -or -not (Test-Path $PackPath)) { return $null }
    $item = Get-Item $PackPath
    if ($item.PSIsContainer) {
        return (Resolve-Path $PackPath).Path
    }
    if ($item.Extension -ieq ".zip") {
        $unpack = Join-Path $UnpackRoot ("pack-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
        New-Item -ItemType Directory -Force -Path $unpack | Out-Null
        Write-Host "Entpacke Pack-Zip: $($item.FullName) → $unpack"
        Expand-Archive -Force -Path $item.FullName -DestinationPath $unpack
        $nested = Join-Path $unpack "InstantLensDoc"
        if (Test-Path $nested) { return (Resolve-Path $nested).Path }
        if (Test-Path (Join-Path $unpack "instantlensdoc")) { return (Resolve-Path $unpack).Path }
        # Zip enthält Dateien direkt
        return (Resolve-Path $unpack).Path
    }
    Write-Warning "LocalPack ist weder Ordner noch .zip: $PackPath"
    return $null
}

function Write-LocalPackHint {
    param([string]$Reason)
    Write-Host ""
    Write-Host "=== Git-Sync fehlgeschlagen ($Reason) ===" -ForegroundColor Yellow
    Write-Host "Fallback: lokales Pack nutzen:"
    Write-Host '  powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1 -LocalPack D:\AI_Temp\InstantLensDoc-pack.zip'
    Write-Host "oder entpackten Ordner:"
    Write-Host '  powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1 -LocalPack D:\AI_Temp\InstantLensDoc-pack'
    Write-Host "Pack-Zip: InstantLensDoc-pack.zip (Store artifacts / Agent-Ausgabe)."
    Write-Host ""
}

Write-Host "=== InstantLens Doc Sync ==="
Write-Host "Ziel: $Destination"

New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$iconBackup = Backup-UserIcons -Dest $Destination

$appSrc = $null

# 1) Explizites -LocalPack (Ordner oder Zip)
if ($LocalPack) {
    $appSrc = Resolve-PackSource -PackPath $LocalPack -UnpackRoot (Split-Path $WorkDir -Parent)
    if (-not $appSrc) {
        Write-Error "LocalPack nicht nutzbar: $LocalPack"
    }
    Write-Host "Lokal: $appSrc"
}

# 2) Zip neben dem Skript (Fallback ohne Parameter)
if (-not $appSrc) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $sideZip = Join-Path $scriptDir "InstantLensDoc-pack.zip"
    $sideZipAlt = Join-Path (Split-Path $scriptDir -Parent) "InstantLensDoc-pack.zip"
    foreach ($z in @($sideZip, $sideZipAlt, "D:\AI_Temp\InstantLensDoc-pack.zip")) {
        if (Test-Path $z) {
            Write-Host "Pack-Zip gefunden: $z"
            $appSrc = Resolve-PackSource -PackPath $z -UnpackRoot (Split-Path $WorkDir -Parent)
            if ($appSrc) { break }
        }
    }
}

# 3) Git clone/fetch
if (-not $appSrc) {
    try {
        if (-not (Test-Path $WorkDir)) {
            Write-Host "Clone $RepoUrl ($Branch) → $WorkDir"
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
        if (Test-Path $candidate) {
            $appSrc = $candidate
        } elseif (Test-Path (Join-Path $WorkDir "instantlensdoc")) {
            $appSrc = $WorkDir
        } else {
            throw "App-Quellordner nicht gefunden unter $WorkDir"
        }
    } catch {
        Write-LocalPackHint -Reason $_.Exception.Message
        throw
    }
}

Write-Host "Kopiere von $appSrc → $Destination"
# Inhalt kopieren; .venv und Nutzer-Caches nicht anfassen wenn möglich
Get-ChildItem $appSrc -Force | ForEach-Object {
    if ($_.Name -in @(".venv", "__pycache__", ".git", ".smoke_license.json")) {
        return
    }
    Copy-Item -Recurse -Force $_.FullName $Destination
}

Restore-UserIcons -BackupInfo $iconBackup -Dest $Destination

# Falls Nutzer-Icon im Root liegt → nach assets spiegeln (ohne vorhandenes neueres assets zu zerstören — Restore schon gemacht)
$rootJpg = Join-Path $Destination "lensDoc.jpg"
$assetsIco = Join-Path $Destination "assets\app.ico"
$assetsPng = Join-Path $Destination "assets\icon.png"
New-Item -ItemType Directory -Force -Path (Join-Path $Destination "assets") | Out-Null
if ((Test-Path $rootJpg) -and -not (Test-Path $assetsPng)) {
    Copy-Item -Force $rootJpg $assetsPng
    Write-Host "Icon aus lensDoc.jpg → assets\icon.png"
}

Set-Location $Destination
Write-Host "=== Inhalt ==="
Get-ChildItem $Destination | Select-Object Name, Length | Format-Table -AutoSize

if (-not (Test-Path (Join-Path $Destination "requirements.txt"))) {
    Write-Error "requirements.txt fehlt nach Sync."
}

if (-not $SkipPip) {
    Write-Host "pip install -r requirements.txt …"
    python -m pip install -r requirements.txt
}

if (-not $NoStart) {
    Write-Host "Starte InstantLens Doc…"
    $run = Join-Path $Destination "run.bat"
    if (Test-Path $run) {
        & $run
    } else {
        python -m instantlensdoc
    }
}

Write-Host "Sync fertig."
