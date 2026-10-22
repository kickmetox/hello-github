#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
echo "Start: .venv/bin/python run.py"
echo "Oberfläche: http://127.0.0.1:8000  Anmeldung admin / admin"
