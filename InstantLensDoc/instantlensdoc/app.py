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


def _make_splash(app):
    """Kurzer Start-Splash mit Produktname + Version."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
    from PySide6.QtWidgets import QSplashScreen

    from instantlensdoc import __version__
    from instantlensdoc.config import DISPLAY_NAME, icon_path

    pm = QPixmap(480, 260)
    pm.fill(QColor("#1B2A3A"))
    painter = QPainter(pm)
    painter.setPen(QColor("#E8EEF4"))
    title_font = QFont("Segoe UI", 22, QFont.Bold)
    title_font.setStyleHint(QFont.SansSerif)
    painter.setFont(title_font)
    painter.drawText(pm.rect().adjusted(0, 70, 0, 0), Qt.AlignHCenter | Qt.AlignTop, DISPLAY_NAME)
    ver_font = QFont("Segoe UI", 14)
    painter.setFont(ver_font)
    painter.setPen(QColor("#A8C0D4"))
    painter.drawText(
        pm.rect().adjusted(0, 120, 0, 0),
        Qt.AlignHCenter | Qt.AlignTop,
        f"Version {__version__}",
    )
    painter.setPen(QColor("#7A93A8"))
    small = QFont("Segoe UI", 10)
    painter.setFont(small)
    painter.drawText(
        pm.rect().adjusted(0, 0, 0, -28),
        Qt.AlignHCenter | Qt.AlignBottom,
        "PDF · Annotationen · OCR · Formulare",
    )
    icon = icon_path()
    if icon is not None:
        try:
            from PySide6.QtGui import QIcon

            ic = QIcon(str(icon)).pixmap(48, 48)
            if not ic.isNull():
                painter.drawPixmap(216, 18, ic)
        except Exception:
            pass
    painter.end()
    splash = QSplashScreen(pm)
    splash.show()
    app.processEvents()
    return splash


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from instantlensdoc import __version__
    from instantlensdoc.config import DISPLAY_NAME
    from instantlensdoc.core.logging_setup import setup_logging
    from instantlensdoc.license import LicenseManager
    from instantlensdoc.ui.main_window import MainWindow
    from instantlensdoc.ui.theme import apply_theme

    log_path = setup_logging()

    app = QApplication(argv)
    apply_theme(app)
    app.setApplicationName(DISPLAY_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Andreas Meyer")
    app.setOrganizationDomain("sellerbach.de")
    _apply_icon(app)

    splash = None
    # Kein Splash in Smoke/Headless-Tests
    import os

    if os.environ.get("ILD_SMOKE_QT") != "1" and os.environ.get("ILD_NO_SPLASH") != "1":
        try:
            splash = _make_splash(app)
        except Exception:
            splash = None

    lm = LicenseManager()
    lm.ensure_trial_started()

    win = MainWindow(lm)
    win.show()
    if splash is not None:
        splash.finish(win)
        QTimer.singleShot(50, splash.close)
    win.statusBar().showMessage(f"Log: {log_path}", 4000)

    # Optionale Datei als Argument
    if len(argv) > 1 and not argv[1].startswith("-"):
        p = Path(argv[1])
        if p.exists():
            win.open_path(str(p))

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
