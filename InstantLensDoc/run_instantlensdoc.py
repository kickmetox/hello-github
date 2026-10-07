"""PyInstaller / direct Windows entry — absolute imports only (no relative).

Frozen EXEs run this as a top-level script without package context. Using the
package ``__main__`` with a relative ``.app`` import fails with::

    ImportError: attempted relative import with no known parent package

Build entry (build-windows.ps1 / instantlensdoc.spec) points here.
Also usable: ``python run_instantlensdoc.py`` from the app root.
"""

from __future__ import annotations

from instantlensdoc.app import main

if __name__ == "__main__":
    raise SystemExit(main())
