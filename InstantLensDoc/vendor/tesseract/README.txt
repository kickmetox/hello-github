InstantLens Doc 2.6.42 — Tesseract-Runtime (ScanTuxio-Layout)

ScanTuxio-Zip (docs/ScanTuxio-Win.zip) enthaelt NUR Python-Quellen, keine
tesseract.exe. Die Runtime liegt lokal unter:

  D:\AI_Temp\ScanTuxio Win\

Erwartete Dateien (wie scantuxio/ocr.py + platform_utils.bundled_tool_dir):

  tesseract.exe
  tessdata\deu.traineddata
  tessdata\eng.traineddata
  (weitere *.traineddata optional)

Lookup-Reihenfolge in InstantLens Doc:

  1) {App}\vendor\tesseract\tesseract.exe     (dieses Verzeichnis)
  2) {App}\tesseract\tesseract.exe            (neben InstantLensDoc.exe)
  3) D:\AI_Temp\ScanTuxio Win\tesseract\tesseract.exe
     D:\AI_Temp\ScanTuxio Win\vendor\tesseract\tesseract.exe
     D:\AI_Temp\ScanTuxio Win\bin\tesseract.exe
  4) C:\Program Files\Tesseract-OCR\tesseract.exe / PATH

TESSDATA_PREFIX wird auf <exe-dir>\tessdata gesetzt.

Copy-Hint (Windows, nach Sync nach InstantLensDoc-2642):

  xcopy /E /I /Y "D:\AI_Temp\ScanTuxio Win\tesseract" ".\vendor\tesseract"
  xcopy /E /I /Y "D:\AI_Temp\ScanTuxio Win\tesseract" ".\dist\InstantLensDoc\tesseract"

build-windows.ps1 kopiert automatisch, wenn eine der Quellen existiert
(build-keygen Copy-Hint, gleiche Quellen).
