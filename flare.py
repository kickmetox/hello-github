#!/usr/bin/env python3
"""Flare starten, ohne das Paket installieren zu müssen."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flare.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
