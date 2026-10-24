#!/usr/bin/env bash
# Baut Flare.exe mit Windows-Python unter Wine und danach den NSIS-Installer.
set -euo pipefail

# Wine-Python bricht ab, wenn stdout eine Pipe ist (WinError 6). Dann ein Pty holen.
if [[ ! -t 1 && -z "${FLARE_BUILD_PTY:-}" ]]; then
  export FLARE_BUILD_PTY=1
  exec script -qefc "bash $(printf '%q' "$0")" /dev/null
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PY_VER="${PY_VER:-3.12.10}"
CACHE="${CACHE:-/tmp/flare-winbuild}"
WINEPREFIX="${WINEPREFIX:-/tmp/flare-wine}"
export WINEPREFIX WINEARCH=win64 WINEDEBUG="${WINEDEBUG:--all}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-mscoree,mshtml=}"

mkdir -p "$CACHE" "$ROOT/dist/windows" packaging/windows
python3 packaging/windows/make_icon.py

EMBED="$CACHE/python-${PY_VER}-embed-amd64.zip"
if [[ ! -f "$EMBED" ]]; then
  curl -fL --retry 3 -o "$EMBED" \
    "https://www.python.org/ftp/python/${PY_VER}/python-${PY_VER}-embed-amd64.zip"
fi

WINPY="$WINEPREFIX/drive_c/flare-python"
if [[ ! -x "$WINPY/python.exe" ]]; then
  mkdir -p "$WINPY"
  unzip -q -o "$EMBED" -d "$WINPY"
  # site-packages zulassen, sonst sieht Python weder pip noch Flare.
  pth="$(echo "$WINPY"/python*._pth)"
  zipname="$(basename "$WINPY"/python*.zip)"
  printf '%s\n.\nLib\\site-packages\nimport site\n' "$zipname" > "$pth"
fi

if ! wineboot -u >/tmp/flare-wineboot.log 2>&1; then
  echo "wineboot fehlgeschlagen, Log:" >&2
  cat /tmp/flare-wineboot.log >&2
  exit 1
fi

wine "$WINPY/python.exe" -c "import sys; print(sys.version)"

if ! wine "$WINPY/python.exe" -m pip --version >/tmp/flare-pip.log 2>&1; then
  curl -fL --retry 3 -o "$CACHE/get-pip.py" https://bootstrap.pypa.io/get-pip.py
  wine "$WINPY/python.exe" "$(winepath -w "$CACHE/get-pip.py")"
fi

wine "$WINPY/python.exe" -m pip install --disable-pip-version-check "pyinstaller==6.16.0"
wine "$WINPY/python.exe" -m PyInstaller \
  --noconfirm \
  --clean \
  --distpath "$(winepath -w "$ROOT/dist")" \
  --workpath "$(winepath -w "$ROOT/build/pyinstaller")" \
  "$(winepath -w "$ROOT/packaging/windows/flare.spec")"

test -f "$ROOT/dist/Flare/Flare.exe"
OUT="$ROOT/dist/windows/Flare-Setup-1.0.0.exe"
makensis \
  -DVERSION=1.0.0 \
  -DPAYLOAD="$ROOT/dist/Flare" \
  -DOUTFILE="$OUT" \
  "$ROOT/packaging/windows/flare.nsi"
test -f "$OUT"
echo "Installer: $OUT"
