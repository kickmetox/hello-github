#!/usr/bin/env bash
# Nachbau der fertigen Windows-Fassung unter Linux.
# Quelle ist dieser Ordner. Ziel ist standardmäßig ~/AI_Temp/CPCM.
set -euo pipefail

SOURCE="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-${HOME}/AI_Temp/CPCM}"

if [[ ! -f "${SOURCE}/cpcm.py" || ! -d "${SOURCE}/cpcm" || ! -d "${SOURCE}/web" ]]; then
  echo "Unvollständige Quelle: ${SOURCE}" >&2
  echo "Erwartet werden cpcm.py, cpcm/ und web/ aus der Windows-Fassung D:\\AI_Temp\\CPCM." >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || {
  echo "Python 3 fehlt. Unter Debian/Ubuntu: sudo apt-get install -y python3" >&2
  exit 1
}

python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 oder neuer wird gebraucht, vorhanden ist %s.%s" % sys.version_info[:2])
PY

if [[ "${SOURCE}" == "${TARGET}" ]]; then
  echo "Quelle und Ziel sind identisch (${TARGET}). Kopieren entfällt." >&2
  exit 1
fi

mkdir -p "${TARGET}"
for name in cpcm.py cpcm.sh CPCM.bat CPCM.exe CPCM.desktop icon.png cpcm.ico Install-CPCM.ps1 Create-Shortcut.ps1 install-cpcm.sh README.md pyproject.toml; do
  if [[ -f "${SOURCE}/${name}" ]]; then
    cp -a "${SOURCE}/${name}" "${TARGET}/${name}"
  fi
done
for name in cpcm web examples tests docs; do
  if [[ -d "${SOURCE}/${name}" ]]; then
    rm -rf "${TARGET}/${name}"
    cp -a "${SOURCE}/${name}" "${TARGET}/${name}"
  fi
done

chmod 755 "${TARGET}/cpcm.py" "${TARGET}/cpcm.sh" "${TARGET}/install-cpcm.sh"
mkdir -p "${TARGET}/vault"

cat > "${TARGET}/AUTOR.txt" <<EOF
CPCM 1.0.0
Andreas Meyer
ame@sellerbach.de
Rolle: Linux-Nachbau der Windows-Referenz
Pfad: ${TARGET}
Windows-Referenz: D:\\AI_Temp\\CPCM
EOF

APPS="${HOME}/.local/share/applications"
mkdir -p "${APPS}"
cat > "${APPS}/cpcm.desktop" <<EOF
[Desktop Entry]
Name=CPCM
Comment=Cross Platform Config Manager – Andreas Meyer
Exec=python3 "${TARGET}/cpcm.py" serve
Path=${TARGET}
Icon=${TARGET}/icon.png
Terminal=false
Type=Application
Categories=Utility;
StartupNotify=true
EOF
chmod 644 "${APPS}/cpcm.desktop"

echo "CPCM liegt in ${TARGET}"
echo "Andreas Meyer  ame@sellerbach.de"
echo "Start: ${TARGET}/cpcm.sh"
echo "Menüeintrag: ${APPS}/cpcm.desktop"
