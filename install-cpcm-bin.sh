#!/usr/bin/env bash
# Kompilierte Linux-Fassung nach ~/AI_Temp/CPCM legen.
# Binary: dist/CPCM (PyInstaller, eine Datei). Quelle ist dieser Ordner.
set -euo pipefail

SOURCE="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-${HOME}/AI_Temp/CPCM}"
BINARY="${SOURCE}/dist/CPCM"

if [[ ! -f "${BINARY}" ]]; then
  echo "Binary fehlt: ${BINARY}" >&2
  echo "Bauen: python3 -m PyInstaller --noconfirm --clean CPCM.spec" >&2
  exit 1
fi

source_real="$(cd "${SOURCE}" && pwd -P)"
mkdir -p "$(dirname "${TARGET}")"
if [[ -d "${TARGET}" ]]; then
  target_real="$(cd "${TARGET}" && pwd -P)"
else
  target_real="$(cd "$(dirname "${TARGET}")" && pwd -P)/$(basename "${TARGET}")"
fi
if [[ "${source_real}" == "${target_real}" ]]; then
  echo "Quelle und Ziel sind identisch (${target_real}). Kopieren entfällt." >&2
  exit 1
fi
if [[ -e "${target_real}/CPCM" && "$(readlink -f "${BINARY}")" == "$(readlink -f "${target_real}/CPCM")" ]]; then
  echo "Quelle und Ziel sind identisch (${target_real}/CPCM). Kopieren entfällt." >&2
  exit 1
fi

mkdir -p "${TARGET}"
install -m 755 "${BINARY}" "${TARGET}/CPCM"
if [[ -f "${SOURCE}/icon.png" ]]; then
  cp -a "${SOURCE}/icon.png" "${TARGET}/icon.png"
fi
if [[ -f "${SOURCE}/cpcm.ico" ]]; then
  cp -a "${SOURCE}/cpcm.ico" "${TARGET}/cpcm.ico"
fi
if [[ -f "${SOURCE}/install-cpcm-bin.sh" ]]; then
  cp -a "${SOURCE}/install-cpcm-bin.sh" "${TARGET}/install-cpcm-bin.sh"
  chmod 755 "${TARGET}/install-cpcm-bin.sh"
fi
if [[ -d "${SOURCE}/docs" ]]; then
  mkdir -p "${TARGET}/docs"
  cp -a "${SOURCE}/docs/." "${TARGET}/docs/"
fi
if [[ -f "${SOURCE}/README.md" ]]; then
  cp -a "${SOURCE}/README.md" "${TARGET}/README.md"
fi

# Vorhandenen vault/ nicht anfassen. Nur anlegen, wenn er fehlt.
mkdir -p "${TARGET}/vault"

cat > "${TARGET}/cpcm.sh" <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
exec "$(dirname "$0")/CPCM" serve "$@"
EOF
chmod 755 "${TARGET}/cpcm.sh"

cat > "${TARGET}/AUTOR.txt" <<EOF
CPCM 1.0.0
Andreas Meyer
ame@sellerbach.de
Rolle: Linux-Nachbau der Windows-Referenz
Pfad: ${TARGET}
Windows-Referenz: D:\\AI_Temp\\CPCM
Binary: ${TARGET}/CPCM
EOF

desktop_body() {
  cat <<EOF
[Desktop Entry]
Name=CPCM
Comment=Cross Platform Config Manager – Andreas Meyer
Exec=${TARGET}/cpcm.sh
Path=${TARGET}
Icon=${TARGET}/icon.png
Terminal=false
Type=Application
Categories=Utility;
StartupNotify=true
EOF
}
desktop_body > "${TARGET}/CPCM.desktop"
chmod 644 "${TARGET}/CPCM.desktop"

APPS="${HOME}/.local/share/applications"
mkdir -p "${APPS}"
desktop_body > "${APPS}/cpcm.desktop"
chmod 644 "${APPS}/cpcm.desktop"

echo "CPCM liegt in ${TARGET}"
echo "Andreas Meyer  ame@sellerbach.de"
echo "Binary: ${TARGET}/CPCM"
echo "Start: ${TARGET}/cpcm.sh"
echo "Menüeintrag: ${APPS}/cpcm.desktop"
