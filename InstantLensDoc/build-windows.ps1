# InstantLens Doc - Windows-Build (PyInstaller App + Keygen) 2.6.55
# Eine Zeile:
#   powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
#
# Voraussetzung: Python 3.10+ **64-Bit** (x64). 32-Bit wird abgelehnt.
#
# Optionen:
#   -Clean
#   -SkipKeygen          # kein InstantLensKeygen.exe
#   -SkipApp
#   -NoKeygenInApp       # Keygen nicht nach dist\InstantLensDoc kopieren
#   -Allow32Bit          # Notfall: 32-Bit Python erlauben (nicht empfohlen)
#   -Python python
#
# Keygen-EXE: dist\InstantLensKeygen\ + optional dist\InstantLensDoc\InstantLensKeygen.exe
# (= Installer-Pfad {app}\InstantLensKeygen.exe)
#
# Ab 2.6.40: nach App-Build wird InstantLensDoc.exe hart geprueft (Pfad + Mindestgroesse).
# Ohne gueltige EXE: Exit != 0 - kein stiller Weiterlauf zum Inno-Installer.
#
# Runnable Python-Pack (ohne PyInstaller): scripts\pack-windows-runnable.ps1

param(
    [switch]$Clean,
    [switch]$SkipApp,
    [switch]$SkipKeygen,
    [switch]$NoKeygenInApp,
    [switch]$Allow32Bit,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "=== InstantLens Doc Build 2.6.55 (Windows x64) ==="
Write-Host "Root: $Root"

# Mindestgroesse: leere/stub EXE und fehlgeschlagenes onedir entlarven (~49 MB Setup)
$script:IldMinAppExeBytes = 5MB

# ScanTuxio Tesseract-Runtime neben EXE / vendor (Binaries oft nicht im Pack-Zip)
function Copy-TesseractVendor {
    param([string]$DestRoot)
    if (-not $DestRoot -or -not (Test-Path -LiteralPath $DestRoot)) { return $false }
    $srcCandidates = @(
        (Join-Path $Root "vendor\tesseract"),
        'D:\AI_Temp\ScanTuxio Win\tesseract',
        'D:\AI_Temp\ScanTuxio Win\vendor\tesseract',
        'D:\AI_Temp\ScanTuxio Win\bin',
        'D:\AI_Temp\ScanTuxio-Win\tesseract',
        'D:\AI_Temp\ScanTuxio-Win\vendor\tesseract'
    )
    foreach ($src in $srcCandidates) {
        $exe = Join-Path $src "tesseract.exe"
        if (-not (Test-Path -LiteralPath $exe)) { continue }
        $destVendor = Join-Path $DestRoot "vendor\tesseract"
        $destBeside = Join-Path $DestRoot "tesseract"
        New-Item -ItemType Directory -Force -Path $destVendor | Out-Null
        New-Item -ItemType Directory -Force -Path $destBeside | Out-Null
        Copy-Item -Recurse -Force -Path (Join-Path $src "*") -Destination $destVendor
        Copy-Item -Recurse -Force -Path (Join-Path $src "*") -Destination $destBeside
        Write-Host "OK: Tesseract-Runtime kopiert: $src -> vendor\tesseract + tesseract\"
        return $true
    }
    Write-Host @"
HINWEIS: Keine tesseract.exe im Pack (ScanTuxio-Zip = Quellen). OCR sucht zur Laufzeit:
  1) {app}\vendor\tesseract\tesseract.exe + tessdata\
  2) {app}\tesseract\tesseract.exe + tessdata\  (ScanTuxio Frozen-Layout)
  3) D:\AI_Temp\ScanTuxio Win\tesseract\tesseract.exe
     D:\AI_Temp\ScanTuxio Win\vendor\tesseract\tesseract.exe
     D:\AI_Temp\ScanTuxio Win\bin\tesseract.exe
  4) C:\Program Files\Tesseract-OCR\tesseract.exe / PATH
build-keygen Copy-Hint:
  xcopy /E /I /Y "D:\AI_Temp\ScanTuxio Win\tesseract" ".\vendor\tesseract"
  xcopy /E /I /Y "D:\AI_Temp\ScanTuxio Win\tesseract" "$DestRoot\tesseract"
Erwartet: tesseract.exe, tessdata\deu.traineddata, tessdata\eng.traineddata
"@
    return $false
}

# 64-Bit Python erzwingen (bevorzugt fuer Release)
$archLine = & $Python -c "import struct,platform; print(struct.calcsize('P')*8); print(platform.machine())"
if ($LASTEXITCODE -ne 0) {
    throw "Python nicht startbar: $Python"
}
$archLines = @($archLine | Where-Object { $_ -and "$_".Trim() })
$bits = 0
$machine = ""
if ($archLines.Count -ge 1) { [void][int]::TryParse("$($archLines[0])".Trim(), [ref]$bits) }
if ($archLines.Count -ge 2) { $machine = "$($archLines[1])".Trim() }
Write-Host "Python: $bits-Bit  /  Machine: $machine"
if ($bits -ne 64 -and -not $Allow32Bit) {
    throw "64-Bit-Python erforderlich (gefunden: ${bits}-Bit). Installiere Python x64 oder nutze -Allow32Bit."
}
if ($bits -ne 64 -and $Allow32Bit) {
    Write-Host "WARNUNG: 32-Bit Python (-Allow32Bit) - Release bevorzugt x64." -ForegroundColor Yellow
}

# Icon Pflicht fuer Release-Build (Fallback PNG)
$IconIco = Join-Path $Root "assets\app.ico"
$IconPng = Join-Path $Root "assets\icon.png"
$Icon = $null
if (Test-Path $IconIco) {
    $Icon = $IconIco
} elseif (Test-Path $IconPng) {
    $Icon = $IconPng
    Write-Host "WARNUNG: assets\app.ico fehlt - nutze icon.png"
} else {
    Write-Host "WARNUNG: Kein Icon unter assets\app.ico / icon.png - EXE ohne Icon"
}
$IconArgs = @()
if ($Icon) { $IconArgs = @("--icon", $Icon) }

function Test-PyInstallerImport {
    param([string]$Py)
    # stderr darf bei Stop nicht als NativeCommandError abbrechen
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & $Py -c "import PyInstaller; print(getattr(PyInstaller, '__version__', 'ok'))" 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    $text = (($out | ForEach-Object { "$_" }) -join "`n").Trim()
    return [pscustomobject]@{ Ok = ($code -eq 0); Code = $code; Text = $text }
}

# PyInstaller verfuegbar? (klare Meldung + pip install)
$probe = Test-PyInstallerImport -Py $Python
if (-not $probe.Ok) {
    Write-Host "PyInstaller Import fehlgeschlagen (exit $($probe.Code))." -ForegroundColor Yellow
    if ($probe.Text) {
        Write-Host "Import-Fehler:" -ForegroundColor Yellow
        Write-Host $probe.Text
    } else {
        Write-Host "(keine stderr/stdout vom Import-Check)" -ForegroundColor DarkYellow
    }
    Write-Host "Installiere PyInstaller: $Python -m pip install --upgrade pyinstaller"
    $prevPip = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $pipOut = & $Python -m pip install --upgrade pyinstaller 2>&1
    $pipCode = $LASTEXITCODE
    $ErrorActionPreference = $prevPip
    Write-Host (($pipOut | ForEach-Object { "$_" }) -join "`n")
    if ($pipCode -ne 0) {
        throw "pip install pyinstaller fehlgeschlagen (exit $pipCode). Bitte manuell: $Python -m pip install --upgrade pyinstaller"
    }
    $probe2 = Test-PyInstallerImport -Py $Python
    if (-not $probe2.Ok) {
        Write-Host "Import nach pip weiterhin fehlgeschlagen:" -ForegroundColor Red
        Write-Host $probe2.Text
        throw "PyInstaller nach pip install nicht importierbar. Siehe Fehlermeldung oben."
    }
    Write-Host "PyInstaller OK: $($probe2.Text)"
} else {
    Write-Host "PyInstaller OK: $($probe.Text)"
}

if ($Clean) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$Root\build", "$Root\dist"
}

$Common = @(
    "--noconfirm",
    "--clean",
    "--paths", $Root,
    "--hidden-import", "pypdfium2",
    "--hidden-import", "pypdfium2_raw",
    "--hidden-import", "pikepdf",
    "--hidden-import", "PIL",
    "--hidden-import", "pytesseract",
    "--hidden-import", "PySide6.QtPrintSupport",
    "--hidden-import", "instantlensdoc",
    "--hidden-import", "instantlensdoc.app",
    "--hidden-import", "instantlensdoc.core.devices",
    "--hidden-import", "instantlensdoc.core.scan",
    "--hidden-import", "instantlensdoc.core.ocr",
    "--hidden-import", "instantlensdoc.core.scantuxio_ui",
    "--hidden-import", "instantlensdoc.core.scantuxio",
    "--hidden-import", "instantlensdoc.core.scantuxio.scanner",
    "--hidden-import", "instantlensdoc.core.scantuxio.scanner_naps2",
    "--hidden-import", "instantlensdoc.core.scantuxio.scanner_escl",
    "--hidden-import", "instantlensdoc.core.scantuxio.discovery",
    "--hidden-import", "instantlensdoc.core.scantuxio.printing",
    "--hidden-import", "instantlensdoc.core.scantuxio.printing_windows",
    "--hidden-import", "instantlensdoc.ui.scan_dialog",
    "--hidden-import", "ild_pdf",
    "--hidden-import", "ild",
    "--hidden-import", "keygen",
    "--collect-all", "pypdfium2",
    # pdfium.dll + version.json liegen in pypdfium2_raw (eigenes Top-Level-Paket) - 2.6.53
    "--collect-all", "pypdfium2_raw",
    "--collect-all", "pikepdf",
    "--collect-submodules", "instantlensdoc"
)

$AppDist = Join-Path $Root "dist\InstantLensDoc"

if (-not $SkipApp) {
    Write-Host "- App InstantLensDoc (x64) -"
    $AppEntry = Join-Path $Root "run_instantlensdoc.py"
    if (-not (Test-Path -LiteralPath $AppEntry)) {
        throw @"
App-Entry fehlt: $AppEntry
Ohne run_instantlensdoc.py kann PyInstaller keine InstantLensDoc.exe bauen (Setup sonst ~2-3 MB).
Pack/Sync pruefen - Datei muss im App-Root liegen (ab 2.6.36/2.6.40).
"@
    }
    $dataArgs = @(
        "--add-data", "assets;assets",
        "--add-data", "FEATURES.md;.",
        "--add-data", "INFO.md;."
    )
    if (Test-Path (Join-Path $Root "CHANGELOG.md")) {
        $dataArgs += @("--add-data", "CHANGELOG.md;.")
    }
    if (Test-Path (Join-Path $Root "README.md")) {
        $dataArgs += @("--add-data", "README.md;.")
    }
    if (Test-Path (Join-Path $Root "VERSION.txt")) {
        $dataArgs += @("--add-data", "VERSION.txt;.")
    }
    $appArgs = $Common + $IconArgs + $dataArgs + @(
        "--name", "InstantLensDoc",
        "--windowed",
        $AppEntry
    )
    & $Python -m PyInstaller @appArgs
    if ($LASTEXITCODE -ne 0) { throw "App-Build fehlgeschlagen (PyInstaller exit $LASTEXITCODE)" }
    # Assets/Docs zusaetzlich absichern (falls --add-data auf Host anders mappt)
    New-Item -ItemType Directory -Force -Path (Join-Path $AppDist "assets") | Out-Null
    if (Test-Path $IconIco) {
        Copy-Item -Force $IconIco (Join-Path $AppDist "assets\app.ico")
    }
    if (Test-Path $IconPng) {
        Copy-Item -Force $IconPng (Join-Path $AppDist "assets\icon.png")
    }
    foreach ($doc in @("FEATURES.md", "INFO.md", "README.md", "CHANGELOG.md", "VERSION.txt", "run-keygen.bat")) {
        $src = Join-Path $Root $doc
        if (Test-Path $src) { Copy-Item -Force $src (Join-Path $AppDist $doc) }
    }
    # Hart: InstantLensDoc.exe muss existieren und plausibel gross sein - 2.6.40
    $appExe = Join-Path $AppDist "InstantLensDoc.exe"
    if (-not (Test-Path -LiteralPath $appExe)) {
        $alt = Get-ChildItem -Path $AppDist -Filter "InstantLensDoc.exe" -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($alt) { $appExe = $alt.FullName }
    }
    if (-not (Test-Path -LiteralPath $appExe)) {
        throw @"
App-Build: InstantLensDoc.exe fehlt unter dist\InstantLensDoc\.
Inno-Setup darf NICHT mit leerem/Python-Fallback laufen (Setup sonst ~2-3 MB).
Pruefe PyInstaller-Log oben. Erwartet: dist\InstantLensDoc\InstantLensDoc.exe
"@
    }
    $exeLen = (Get-Item -LiteralPath $appExe).Length
    if ($exeLen -lt $script:IldMinAppExeBytes) {
        throw "App-Build: InstantLensDoc.exe zu klein ($exeLen Bytes < $script:IldMinAppExeBytes) - Output unvollstaendig."
    }
    Write-Host ("OK: {0} ({1} MB)" -f $appExe, [math]::Round($exeLen / 1MB, 2))
    # PDFium-Binary muss im onedir-Output liegen — sonst weisse Canvas/Thumbs — 2.6.51
    $pdfiumHits = @(Get-ChildItem -Path $AppDist -Recurse -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match '(?i)^pdfium(\.dll|\.so|\.dylib)?$' -or
            $_.Name -match '(?i)pdfium.*\.(dll|so|dylib)$' -or
            ($_.Name -match '(?i)pypdfium2' -and $_.Extension -match '(?i)\.(dll|pyd|so)$')
        })
    if ($pdfiumHits.Count -lt 1) {
        throw @"
App-Build: PDFium/pypdfium2-Binary fehlt unter dist\InstantLensDoc\.
PyInstaller muss --collect-all pypdfium2 nutzen (build-windows.ps1 / Spec).
Ohne dll bleibt die PDF-Hauptansicht weiss und Thumbs grau.
"@
    }
    Write-Host ("OK: PDFium-Binary vorhanden ({0})" -f $pdfiumHits[0].FullName)
    # pypdfium2 5.x laedt ausschliesslich <pkg>\pypdfium2_raw\pdfium.dll (bindings.py: './pdfium.dll',
    # search_sys=False). Liegt die DLL woanders, startet die EXE, aber jedes PDF schlaegt fehl - 2.6.53
    $rawDirs = @(Get-ChildItem -Path $AppDist -Recurse -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq 'pypdfium2_raw' })
    $rawOk = $false
    foreach ($rd in $rawDirs) {
        if ((Test-Path -LiteralPath (Join-Path $rd.FullName 'pdfium.dll')) -and
            (Test-Path -LiteralPath (Join-Path $rd.FullName 'version.json'))) {
            $rawOk = $true
            Write-Host ("OK: pypdfium2_raw komplett ({0})" -f $rd.FullName)
            break
        }
    }
    if (-not $rawOk) {
        throw @"
App-Build: pypdfium2_raw\pdfium.dll + version.json fehlen unter dist\InstantLensDoc\.
PyInstaller muss --collect-all pypdfium2_raw nutzen (build-windows.ps1 / Spec, 2.6.53).
Ohne diese Dateien meldet jedes PDF 'Failed to load document' bzw. ImportError pdfium.
"@
    }
    $qpdfHits = @(Get-ChildItem -Path $AppDist -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '(?i)^qpdf.*\.dll$' -or $_.Name -match '(?i)^_core.*\.pyd$' })
    if ($qpdfHits.Count -lt 1) {
        Write-Warning "pikepdf/qpdf-Binary nicht gefunden - PDF-Reparatur-Fallback (Schritt 3) steht in der EXE nicht zur Verfuegung."
    } else {
        Write-Host ("OK: pikepdf/qpdf-Binary vorhanden ({0})" -f $qpdfHits[0].FullName)
    }
    Write-Host "OK: dist\InstantLensDoc\"
    [void](Copy-TesseractVendor -DestRoot $AppDist)
}

$KeygenDist = Join-Path $Root "dist\InstantLensKeygen"
if (-not $SkipKeygen) {
    Write-Host "- Keygen InstantLensKeygen (x64) -"
    $kgArgs = $Common + $IconArgs + @(
        "--name", "InstantLensKeygen",
        "--windowed",
        (Join-Path $Root "keygen\__main__.py")
    )
    & $Python -m PyInstaller @kgArgs
    if ($LASTEXITCODE -ne 0) { throw "Keygen-Build fehlgeschlagen" }
    Write-Host "OK: dist\InstantLensKeygen\"
    # build-keygen Copy-Hint: gleiche Tesseract-Runtime wie App (OCR unabhaengig vom Keygen)
    Write-Host "build-keygen: Tesseract-Runtime Copy-Hint (ScanTuxio Win -> vendor\\tesseract)"
    if (Test-Path $AppDist) {
        [void](Copy-TesseractVendor -DestRoot $AppDist)
    }

    # Optional: Keygen in App-Dist legen (Installer findet InstantLensKeygen.exe)
    if (-not $NoKeygenInApp -and (Test-Path $AppDist)) {
        $kgExe = Join-Path $KeygenDist "InstantLensKeygen.exe"
        if (-not (Test-Path $kgExe)) {
            # onedir vs. flat
            $alt = Get-ChildItem -Path $KeygenDist -Filter "InstantLensKeygen.exe" -Recurse -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($alt) { $kgExe = $alt.FullName }
        }
        if (Test-Path $kgExe) {
            Copy-Item -Force $kgExe (Join-Path $AppDist "InstantLensKeygen.exe")
            Write-Host "Keygen mitgepackt: dist\InstantLensDoc\InstantLensKeygen.exe"
        } else {
            Write-Host "WARNUNG: InstantLensKeygen.exe nicht gefunden - Installer-Keygen ggf. ohne EXE"
        }
    }
} else {
    Write-Host "Keygen uebersprungen (-SkipKeygen)"
}

Write-Host "Fertig (2.6.55). Optional:"
Write-Host '  powershell -ExecutionPolicy Bypass -File .\installer\build-installer.ps1'
Write-Host "  (ohne Keygen: -SkipKeygen bzw. ISCC /DIncludeKeygen=0)"
Write-Host '  python scripts\pack-windows-runnable.py   # Python-Layout-Zip ohne EXE'
