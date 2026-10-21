# ReckonGrid lokal installieren (ohne Administrator). Andreas Meyer, ame@sellerbach.de
# Fehler bleiben in diesem Fenster stehen. Der Start selbst läuft sichtbar, nicht versteckt.
$ErrorActionPreference = 'Stop'

function Wait-Key([string]$message) {
  Write-Host ''
  Write-Host $message
  try { Read-Host 'Enter drücken' | Out-Null } catch { Start-Sleep -Seconds 8 }
}

try {
  $here = Split-Path -Parent $MyInvocation.MyCommand.Path
  $appSrc = Join-Path $here 'app'
  if (-not (Test-Path -LiteralPath (Join-Path $appSrc 'index.html'))) {
    throw "App-Dateien fehlen: $appSrc`nDas Setup-Archiv muss den Ordner app\ enthalten. index.html nicht direkt öffnen."
  }

  Write-Host 'ReckonGrid wird installiert ...'
  $dest = Join-Path $env:LOCALAPPDATA 'ReckonGrid'
  New-Item -ItemType Directory -Force -Path $dest | Out-Null

  $appDest = Join-Path $dest 'app'
  if (Test-Path -LiteralPath $appDest) {
    Remove-Item -LiteralPath $appDest -Recurse -Force
  }
  Copy-Item -LiteralPath $appSrc -Destination $dest -Recurse -Force
  foreach ($name in @('ReckonGrid.ps1', 'Start-ReckonGrid.bat', 'icon.ico')) {
    $src = Join-Path $here $name
    if ($name -eq 'icon.ico' -and -not (Test-Path -LiteralPath $src)) { continue }
    Copy-Item -LiteralPath $src -Destination (Join-Path $dest $name) -Force
  }

  $bat = Join-Path $dest 'Start-ReckonGrid.bat'
  try {
    $shell = New-Object -ComObject WScript.Shell
    $targets = @(
      (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\ReckonGrid.lnk'),
      (Join-Path ([Environment]::GetFolderPath('Desktop')) 'ReckonGrid.lnk')
    )
    foreach ($lnk in $targets) {
      $shortcut = $shell.CreateShortcut($lnk)
      $shortcut.TargetPath = $bat
      $shortcut.Arguments = ''
      $shortcut.WorkingDirectory = $dest
      $shortcut.WindowStyle = 1
      $shortcut.Description = 'ReckonGrid – Tabellenkalkulation'
      $icon = Join-Path $dest 'icon.ico'
      if (Test-Path -LiteralPath $icon) { $shortcut.IconLocation = $icon }
      $shortcut.Save()
    }
    Write-Host 'Verknüpfung auf dem Desktop und im Startmenü angelegt.'
  } catch {
    Write-Host "Verknüpfung konnte nicht angelegt werden: $($_.Exception.Message)"
    Write-Host "Start danach direkt über $bat"
  }

  Write-Host "Installiert nach $dest"
  Write-Host 'ReckonGrid wird im Browser geöffnet. Das zweite Fenster muss offen bleiben.'
  Start-Process -FilePath $bat -WorkingDirectory $dest
  Wait-Key 'Installation fertig. Dieses Fenster kann geschlossen werden. Das Startfenster beendet die App.'
} catch {
  Write-Host ''
  Write-Host "FEHLER: $($_.Exception.Message)" -ForegroundColor Red
  if ($_.ScriptStackTrace) { Write-Host $_.ScriptStackTrace }
  Wait-Key 'Die Installation ist fehlgeschlagen. Die Meldung oben steht, bis Enter gedrückt wird.'
  exit 1
}
