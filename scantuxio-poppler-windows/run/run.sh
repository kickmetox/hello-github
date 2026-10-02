#!/usr/bin/env bash
# ScanTuxio Launcher — pypdfium2 in App; Poppler nur optional lokal
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -x "$APP_DIR/vendor/poppler/bin/pdftoppm" || -f "$APP_DIR/vendor/poppler/Library/bin/pdftoppm.exe" ]]; then
  for c in "$APP_DIR/vendor/poppler/Library/bin" "$APP_DIR/vendor/poppler/bin"; do
    if [[ -e "$c/pdftoppm" || -e "$c/pdftoppm.exe" ]]; then
      export PATH="$c:$PATH"
      export SCANTUXIO_POPPLER="$c"
      echo "[ScanTuxio] Legacy-Poppler (optional): $c" >&2
      break
    fi
  done
fi

if [[ -f "$APP_DIR/ScanTuxio.exe" ]]; then
  exec "$APP_DIR/ScanTuxio.exe" "$@"
fi
if [[ -f "$APP_DIR/scantuxio_entry.py" ]]; then
  exec python3 "$APP_DIR/scantuxio_entry.py" "$@"
fi
echo "[ScanTuxio] Weder ScanTuxio.exe noch scantuxio_entry.py gefunden." >&2
exit 1
