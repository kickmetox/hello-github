"""Setzt die Tcl/Tk-Pfade, bevor die installierte Windows-Fassung startet."""

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable)))
os.environ.setdefault("TCL_LIBRARY", os.path.join(_root, "lib", "tcl8.6"))
os.environ.setdefault("TK_LIBRARY", os.path.join(_root, "lib", "tk8.6"))
