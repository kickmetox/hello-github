#!/usr/bin/env bash
# ScanTuxio Launcher — Poppler in PATH (Linux/macOS; Windows via Git Bash nutzbar)
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_poppler_bin() {
  local root="$1"
  local c
  for c in \
    "$root/vendor/poppler/Library/bin" \
    "$root/vendor/poppler/bin" \
    "$root/poppler/bin" \
    "$root/vendor/poppler"
  do
    if [[ -x "$c/pdftoppm" || -f "$c/pdftoppm.exe" ]]; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

if POPPLER_BIN="$(find_poppler_bin "$APP_DIR")"; then
  export PATH="$POPPLER_BIN:$PATH"
  export SCANTUXIO_POPPLER="$POPPLER_BIN"
  export POPPLER_PATH="$POPPLER_BIN"
  echo "[ScanTuxio] Poppler: $POPPLER_BIN"
else
  echo "[ScanTuxio] Warnung: gebündeltes Poppler nicht gefunden (system-PATH wird genutzt)." >&2
fi

if [[ -f "$APP_DIR/ScanTuxio.exe" ]]; then
  exec "$APP_DIR/ScanTuxio.exe" "$@"
fi
if [[ -f "$APP_DIR/scantuxio_entry.py" ]]; then
  exec python3 "$APP_DIR/scantuxio_entry.py" "$@"
fi
echo "[ScanTuxio] Weder ScanTuxio.exe noch scantuxio_entry.py gefunden." >&2
exit 1
