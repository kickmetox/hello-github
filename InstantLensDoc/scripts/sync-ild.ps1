# InstantLens Doc — Sync nach D:\AI_Temp\InstantLensDoc (eine Datei)
# Lädt Branch von GitHub oder nutzt lokales Pack, kopiert, pip, optional Start.
# Eigenes Nutzer-Icon in assets wird NICHT überschrieben (neuer/local bleibt).
#
# Eine Zeile:
#   powershell -ExecutionPolicy Bypass -File .\sync-ild.ps1
#
# Optionen:
#   -Branch cursor/instantlensdoc-30dc
#   -LocalPack C:\path\to\InstantLensDoc
#   -NoStart
#   -SkipPip

param(
    [string]$Destination = "D:\AI_Temp\InstantLensDoc",
    [string]$Branch = "cursor/instantlensdoc-30dc",
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

Write-Host "=== InstantLens Doc Sync ==="
Write-Host "Ziel: $Destination"

New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$iconBackup = Backup-UserIcons -Dest $Destination

$appSrc = $null
if ($LocalPack -and (Test-Path $LocalPack)) {
    $appSrc = (Resolve-Path $LocalPack).Path
    Write-Host "Lokal: $appSrc"
} else {
    if (-not (Test-Path $WorkDir)) {
        Write-Host "Clone $RepoUrl ($Branch) → $WorkDir"
        git clone --branch $Branch --single-branch $RepoUrl $WorkDir
    } else {
        Write-Host "Fetch/Reset $WorkDir @ $Branch"
        Push-Location $WorkDir
        git fetch origin $Branch
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
        Write-Error "App-Quellordner nicht gefunden unter $WorkDir"
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
