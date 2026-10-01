Poppler Windows binaries go here after running:

  scripts\download-poppler.ps1

Expected layout:

  vendor/poppler/Library/bin/pdftoppm.exe
  vendor/poppler/Library/bin/pdfinfo.exe
  vendor/poppler/LICENSE-POPPLER.txt

Do not commit large binary zips unless intentionally vendoring for offline builds.
