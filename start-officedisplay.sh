#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="${PWD}/src${PYTHONPATH:+:$PYTHONPATH}"
PY="${PWD}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi
exec "$PY" -m officedisplay "$@"
