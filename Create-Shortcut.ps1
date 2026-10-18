# Desktop-Verknüpfung mit cpcm.ico
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = $null
$Arguments = "`"$Root\cpcm.py`" serve"
$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    $Python = $py.Source
    $Arguments = "-3 $Arguments"
} else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { throw "Python 3 wurde nicht gefunden." }
    $Python = $python.Source
}
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut((Join-Path $env:USERPROFILE "Desktop\CPCM.lnk"))
$Shortcut.TargetPath = $Python
$Shortcut.Arguments = $Arguments
$Shortcut.WorkingDirectory = $Root
$Shortcut.IconLocation = Join-Path $Root "cpcm.ico"
$Shortcut.Description = "CPCM – Andreas Meyer, ame@sellerbach.de"
$Shortcut.Save()
Write-Host "Verknüpfung: $env:USERPROFILE\Desktop\CPCM.lnk"
