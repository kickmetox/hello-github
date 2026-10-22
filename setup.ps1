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
if (Get-Command tesseract -ErrorAction SilentlyContinue) {
    Write-Host "Tesseract gefunden. Bilder und textlose PDF-Seiten werden beim Import gelesen."
} else {
    Write-Host "Für Scans und Fotos: winget install UB-Mannheim.TesseractOCR"
    Write-Host "Deutsch braucht die Sprache deu. tesseract.exe muss im PATH liegen oder unter C:\Program Files\Tesseract-OCR\."
    Write-Host "PDF, Word und Text mit vorhandener Textebene sind auch ohne Tesseract durchsuchbar."
}
