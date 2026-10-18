#!/usr/bin/env bash
# Baut CPCM-Setup.exe mit NSIS und dem offiziellen Python-3.12-Embed (64-bit).
# Die heruntergeladene Zip bleibt unter build/ und wird nicht versioniert.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="${ROOT}/build/cache"
STAGE="${ROOT}/build/python"
ZIP="${CACHE}/python-3.12.10-embed-amd64.zip"
URL="https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"

mkdir -p "${CACHE}"
if [[ ! -f "${ZIP}" ]]; then
  curl -fL --retry 3 -o "${ZIP}.partial" "${URL}"
  mv "${ZIP}.partial" "${ZIP}"
fi

rm -rf "${STAGE}"
mkdir -p "${STAGE}/Lib"
unzip -q "${ZIP}" -d "${STAGE}"
cp "${ROOT}/installer/python312._pth" "${STAGE}/python312._pth"

makensis "${ROOT}/installer/CPCM.nsi"
echo "Fertig: ${ROOT}/CPCM-Setup.exe"
