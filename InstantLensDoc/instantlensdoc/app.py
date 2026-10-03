"""InstantLens Doc — Einstieg."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo-Root auf sys.path (python -m instantlensdoc aus InstantLensDoc/)
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


class _GermanHelpFormatter(argparse.HelpFormatter):
    """Hilfe-Texte auf Deutsch belassen (Formatter-Hook) — 1.5.1."""

    def __init__(self, prog: str, **kwargs):
        kwargs.setdefault("width", 88)
        super().__init__(prog, **kwargs)


def parse_cli(argv: list[str] | None = None) -> argparse.Namespace:
    """
    CLI für ``python -m instantlensdoc`` — 1.5.1.
    ``--version`` / ``--open FILE`` (mehrfach) / ``--help`` DE; positional Datei bleibt kompatibel.
    """
    from instantlensdoc import __version__

    p = argparse.ArgumentParser(
        prog="instantlensdoc",
        description=(
            "InstantLens Doc — PDF-Annotator, OCR, Formulare.\n"
            "Startet die Desktop-Oberfläche; optional Dateien öffnen."
        ),
        epilog=(
            "Beispiele:\n"
            "  python -m instantlensdoc --version\n"
            "  python -m instantlensdoc --open dokument.pdf\n"
            "  python -m instantlensdoc --open a.pdf --open b.pdf\n"
            "  python -m instantlensdoc dokument.pdf\n"
            "\n"
            "Exitcodes: 0 OK · 1 allgemeiner Fehler · 2 Datei nicht gefunden"
        ),
        formatter_class=_GermanHelpFormatter,
        add_help=False,
    )
    p.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Diese Hilfe anzeigen und beenden",
    )
    p.add_argument(
        "--version",
        "-V",
        action="store_true",
        help="Version ausgeben und beenden",
    )
    p.add_argument(
        "--open",
        metavar="DATEI",
        dest="open_files",
        action="append",
        default=None,
        help="Datei beim Start öffnen (mehrfach möglich)",
    )
    p.add_argument(
        "file",
        nargs="?",
        default=None,
        help="Datei öffnen (positional, alternativ zu --open)",
    )
    args, unknown = p.parse_known_args(list(argv if argv is not None else sys.argv[1:]))
    args.unknown = unknown
    args.version_str = __version__
    # Kompatibilität 1.5.0: open_file = erste --open-Datei
    opens = list(args.open_files or [])
    args.open_files = opens
    args.open_file = opens[0] if opens else None
    return args


def _collect_open_targets(cli: argparse.Namespace) -> list[Path]:
    """Alle gewünschten Öffnungsziele (--open* + positional), Reihenfolge erhalten."""
    targets: list[Path] = []
    seen: set[str] = set()
    for candidate in list(cli.open_files or []) + (
        [cli.file] if cli.file else []
    ):
        if not candidate:
            continue
        p = Path(candidate)
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        targets.append(p)
    return targets


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
    raw = list(sys.argv if argv is None else argv)
    # --help wird von argparse behandelt (exit 0)
    cli = parse_cli(raw[1:])
    if cli.version:
        print(f"InstantLens Doc {cli.version_str}")
        return 0

    open_targets = _collect_open_targets(cli)
    missing = [p for p in open_targets if not p.exists()]
    # Exitcode 2 bei fehlender Datei — vor Qt, klar für CLI — 1.5.1
    if missing:
        for m in missing:
            print(f"Datei nicht gefunden: {m}", file=sys.stderr)
        return 2

    # Qt-argv: Programmname + unbekannte Args (keine doppelten --open/--version)
    qt_argv = [raw[0], *list(getattr(cli, "unknown", []) or [])]

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from instantlensdoc import __version__
    from instantlensdoc.config import DISPLAY_NAME
    from instantlensdoc.core.deps_check import check_runtime_dependencies, has_any_failure
    from instantlensdoc.core.logging_setup import setup_logging
    from instantlensdoc.license import LicenseManager
    from instantlensdoc.ui.deps_dialog import show_startup_dependency_dialog
    from instantlensdoc.ui.main_window import MainWindow
    from instantlensdoc.ui.theme import apply_theme, install_system_theme_watch

    log_path = setup_logging()

    app = QApplication(qt_argv)
    apply_theme(app)
    # OS-Theme-Wechsel live nachziehen wenn „System folgen“ — 1.4.2
    install_system_theme_watch()
    app.setApplicationName(DISPLAY_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Andreas Meyer")
    app.setOrganizationDomain("sellerbach.de")
    _apply_icon(app)

    splash = None
    # Kein Splash in Smoke/Headless-Tests; optional Quiet-Startup (Einstellungen)
    import os

    smoke = os.environ.get("ILD_SMOKE_QT") == "1"
    skip_splash = False
    try:
        from instantlensdoc.core.app_settings import get_skip_splash

        skip_splash = get_skip_splash()
    except Exception:
        skip_splash = False
    if (
        not smoke
        and os.environ.get("ILD_NO_SPLASH") != "1"
        and not skip_splash
    ):
        try:
            splash = _make_splash(app)
        except Exception:
            splash = None

    lm = LicenseManager()
    lm.ensure_trial_started()

    # Startup-Check Abhängigkeiten (pypdfium2 kritisch, Tesseract optional)
    dep_statuses = check_runtime_dependencies()
    skip_deps_dialog = smoke or os.environ.get("ILD_SKIP_DEPS_CHECK") == "1"

    win = MainWindow(lm)
    win.show()
    if splash is not None:
        splash.finish(win)
        QTimer.singleShot(50, splash.close)
    win.statusBar().showMessage(f"Log: {log_path}", 4000)

    if not skip_deps_dialog and has_any_failure(dep_statuses):
        def _show_deps():
            show_startup_dependency_dialog(win, only_if_issues=True, statuses=dep_statuses)

        QTimer.singleShot(200, _show_deps)
    elif not has_any_failure(dep_statuses):
        # Kurzer Statushinweis wenn alles OK (nicht im Smoke)
        if not smoke:
            win.statusBar().showMessage("Abhängigkeiten OK (pypdfium2 / OCR-Check)", 3500)

    # Dateien öffnen: mehrere --open + positional — 1.5.1
    for target in open_targets:
        try:
            win.open_path(str(target))
        except Exception as e:
            win.statusBar().showMessage(f"Öffnen fehlgeschlagen: {target.name}: {e}", 6000)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
