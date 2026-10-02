#!/usr/bin/env bash
# Poppler-für-Windows Zip laden (auf Build-Host / CI). Unter Linux nur Download+Unzip.
set -euo pipefail
VERSION="${1:-25.12.0-0}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/vendor/poppler"
URL="https://github.com/oschwartz10612/poppler-windows/releases/download/v${VERSION}/Release-${VERSION}.zip"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Download: $URL"
curl -fsSL -o "$TMP/poppler.zip" "$URL"
rm -rf "$DEST"
mkdir -p "$DEST"
unzip -q "$TMP/poppler.zip" -d "$TMP/out"
# Inhalt nach vendor/poppler
if [[ -d "$TMP/out"/Release-* ]]; then
  cp -a "$TMP/out"/Release-*/* "$DEST/"
else
  cp -a "$TMP/out"/* "$DEST/"
fi

if [[ ! -f "$DEST/Library/bin/pdftoppm.exe" ]]; then
  echo "Warnung: Library/bin/pdftoppm.exe nicht am Standardpfad — Suche:" >&2
  find "$DEST" -name 'pdftoppm.exe' | head
fi

cat > "$DEST/LICENSE-POPPLER.txt" <<EOF
Poppler (Windows binaries) — Version $VERSION
Upstream GPL: https://poppler.freedesktop.org/
Package: https://github.com/oschwartz10612/poppler-windows
URL: $URL
EOF

echo "OK: $DEST"
