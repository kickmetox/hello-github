#!/bin/sh
# ReckonGrid lokal installieren. Andreas Meyer, ame@sellerbach.de
set -eu
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
DEST="${HOME}/.local/share/reckongrid"
mkdir -p "$DEST" "${HOME}/.local/share/applications" "${HOME}/.local/bin"
rm -rf "$DEST/app"
cp -a "$HERE/app" "$DEST/app"
cp "$HERE/start.sh" "$DEST/start.sh"
chmod +x "$DEST/start.sh"
if [ -f "$HERE/../public/icon.png" ]; then
  cp "$HERE/../public/icon.png" "$DEST/icon.png"
elif [ -f "$DEST/app/icon.png" ]; then
  cp "$DEST/app/icon.png" "$DEST/icon.png"
fi
cat > "${HOME}/.local/share/applications/reckongrid.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=ReckonGrid
Comment=Tabellenkalkulation mit Datenbankfunktion
Exec=${DEST}/start.sh
Icon=${DEST}/icon.png
Terminal=false
Categories=Office;
EOF
ln -sfn "$DEST/start.sh" "${HOME}/.local/bin/reckongrid"
echo "Installiert nach $DEST"
"$DEST/start.sh"
