"""InstantLens Doc — Einstieg."""

from __future__ import annotations

import sys
from pathlib import Path

# Repo-Root auf sys.path (python -m instantlensdoc aus InstantLensDoc/)
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)

    from PySide6.QtWidgets import QApplication

    from instantlensdoc.config import DISPLAY_NAME, icon_path
    from instantlensdoc.license import LicenseManager
    from instantlensdoc.ui.main_window import MainWindow

    app = QApplication(argv)
    app.setApplicationName(DISPLAY_NAME)
    app.setOrganizationName("Andreas Meyer")
    app.setOrganizationDomain("sellerbach.de")

    ic = icon_path()
    if ic:
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(ic)))

    lm = LicenseManager()
    lm.ensure_trial_started()

    win = MainWindow(lm)
    win.show()

    # Optionale Datei als Argument
    if len(argv) > 1 and not argv[1].startswith("-"):
        p = Path(argv[1])
        if p.exists():
            win.open_path(str(p))

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
