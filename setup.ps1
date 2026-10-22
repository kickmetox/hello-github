$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Error "Python wurde nicht gefunden. Visual Studio Python-Workload oder python.org installieren."
}
if (-not (Test-Path .venv)) {
    py -3 -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
Write-Host "DocMan ist installiert."
Write-Host "Visual Studio: DocMan.sln öffnen, .venv als Umgebung wählen, F5."
Write-Host "Oder: .\.venv\Scripts\python.exe run.py"
Write-Host "Oberfläche: http://127.0.0.1:8000  Anmeldung admin / admin"
