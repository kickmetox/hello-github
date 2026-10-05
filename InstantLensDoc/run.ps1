# InstantLens Doc starten
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$py = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $py) {
  & $py -m instantlensdoc @args
} else {
  python -m instantlensdoc @args
}
