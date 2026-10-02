"""InstantLens Doc — Einstieg."""

from __future__ import annotations

import sys
from pathlib import Path

# Repo-Root auf sys.path (python -m instantlensdoc aus InstantLensDoc/)
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _apply_icon(app) -> None:
    """Fenster-/Taskleisten-Icon aus assets/ (robuste Pfadauflösung)."""
    from PySide6.QtGui import QIcon

    from instantlensdoc.config import icon_path, icon_paths_for_qt

    icon = QIcon()
    paths = icon_paths_for_qt()
    if not paths:
        single = icon_path()
        if single:
            paths = [single]
    for p in paths:
        icon.addFile(str(p))
    if not icon.isNull():
        app.setWindowIcon(icon)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)

    from PySide6.QtWidgets import QApplication

    from instantlensdoc.config import DISPLAY_NAME
    from instantlensdoc.core.logging_setup import setup_logging
    from instantlensdoc.license import LicenseManager
    from instantlensdoc.ui.main_window import MainWindow
    from instantlensdoc.ui.theme import apply_theme

    log_path = setup_logging()

    app = QApplication(argv)
    apply_theme(app)
    app.setApplicationName(DISPLAY_NAME)
    app.setOrganizationName("Andreas Meyer")
    app.setOrganizationDomain("sellerbach.de")
    _apply_icon(app)

    lm = LicenseManager()
    lm.ensure_trial_started()

    win = MainWindow(lm)
    win.show()
    win.statusBar().showMessage(f"Log: {log_path}", 4000)

    # Optionale Datei als Argument
    if len(argv) > 1 and not argv[1].startswith("-"):
        p = Path(argv[1])
        if p.exists():
            win.open_path(str(p))

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
