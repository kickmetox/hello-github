# ReckonGrid lokal installieren (ohne Administrator). Andreas Meyer, ame@sellerbach.de
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest = Join-Path $env:LOCALAPPDATA 'ReckonGrid'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path (Join-Path $here 'app') -Destination $dest -Recurse -Force
Copy-Item -Path (Join-Path $here 'ReckonGrid.ps1') -Destination $dest -Force
Copy-Item -Path (Join-Path $here 'icon.ico') -Destination $dest -Force -ErrorAction SilentlyContinue

$shell = New-Object -ComObject WScript.Shell
$targets = @(
  (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\ReckonGrid.lnk'),
  (Join-Path ([Environment]::GetFolderPath('Desktop')) 'ReckonGrid.lnk')
)
foreach ($lnk in $targets) {
  $shortcut = $shell.CreateShortcut($lnk)
  $shortcut.TargetPath = 'powershell.exe'
  $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$(Join-Path $dest 'ReckonGrid.ps1')`""
  $shortcut.WorkingDirectory = $dest
  $shortcut.Description = 'ReckonGrid – Tabellenkalkulation'
  $icon = Join-Path $dest 'icon.ico'
  if (Test-Path $icon) { $shortcut.IconLocation = $icon }
  $shortcut.Save()
}

Write-Host "Installiert nach $dest"
Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$(Join-Path $dest 'ReckonGrid.ps1')`""
