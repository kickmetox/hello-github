from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from officedisplay.paths import icon_path
from officedisplay.ui.main_window import MainWindow


def main() -> int:
    from PySide6.QtCore import Qt

    try:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_SynthesizeMouseForUnhandledTabletEvents, False)
    except (AttributeError, TypeError):
        pass
    app = QApplication(sys.argv)
    app.setApplicationName("Office Display")
    app.setOrganizationName("Andreas Meyer")
    if icon_path().is_file():
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(icon_path())))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
