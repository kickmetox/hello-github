#!/usr/bin/env bash
# Richtet Office Display im Programmordner ein. Anwendungslogik bleibt unberührt.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1 || ! python3 --version >/dev/null 2>&1; then
  echo "Python 3 wurde nicht gefunden."
  echo "Bitte Python 3.12 installieren: https://www.python.org/downloads/"
  exit 1
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  if ! python3 -m venv "$ROOT/.venv"; then
    echo "Die Umgebung .venv ließ sich nicht anlegen."
    exit 1
  fi
fi

if ! "$ROOT/.venv/bin/python" -m pip install -r "$ROOT/requirements.txt"; then
  echo "Die Pakete aus requirements.txt ließen sich nicht installieren."
  exit 1
fi

cat > "$ROOT/Office Display.sh" << 'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$(pwd)/.venv/bin/python" -m officedisplay "$@"
EOF
chmod +x "$ROOT/Office Display.sh"

if command -v cmake >/dev/null 2>&1; then
  if cmake -S "$ROOT/native/cpp" -B "$ROOT/native/cpp/build" && cmake --build "$ROOT/native/cpp/build"; then
    echo "native/cpp wurde gebaut."
  else
    echo "native/cpp wurde nicht gebaut. Die Python-Farbrechnung wird genutzt."
  fi
else
  echo "CMake wurde nicht gefunden. Die Python-Farbrechnung wird genutzt."
fi

echo "Installation fertig. Start über ./Office Display.sh"
