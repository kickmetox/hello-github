# Kopiert CPCM nach D:\AI_Temp\CPCM und legt eine Verknüpfung mit Icon an.
$ErrorActionPreference = "Stop"
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = "D:\AI_Temp\CPCM"
New-Item -ItemType Directory -Force -Path $Target | Out-Null
& robocopy $Source $Target /E /NFL /NDL /NJH /NJS /XD .git vault __pycache__ .venv /XF cpcm-settings.json
if ($LASTEXITCODE -ge 8) {
    throw "Kopieren nach $Target fehlgeschlagen (robocopy $LASTEXITCODE)"
}
@'
CPCM 1.0.0
Andreas Meyer
ame@sellerbach.de
Rolle: Windows-Referenz
Pfad: D:\AI_Temp\CPCM
'@ | Set-Content -Encoding utf8 -Path (Join-Path $Target "AUTOR.txt")
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Target "Create-Shortcut.ps1")
Write-Host "CPCM liegt in $Target"
Write-Host "Andreas Meyer  ame@sellerbach.de"
