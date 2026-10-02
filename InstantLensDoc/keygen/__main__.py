"""InstantLens Doc Keygenerator — separates Tool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo-Root auf sys.path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from instantlensdoc.license import KEY_DAYS, generate_key, verify_key


def cli(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="InstantLens Doc Keygenerator")
    p.add_argument("email", nargs="?", help="E-Mail des Lizenznehmers")
    p.add_argument("--gui", action="store_true", help="Einfache GUI starten")
    p.add_argument("--verify", metavar="KEY", help="Key prüfen statt erzeugen")
    args = p.parse_args(argv)

    if args.gui:
        return run_gui()

    if args.verify:
        ok, msg, data = verify_key(args.verify)
        print("OK:" if ok else "FEHLER:", msg)
        if data:
            print("Payload:", data)
        return 0 if ok else 1

    if not args.email:
        p.print_help()
        return 2

    key = generate_key(args.email)
    print(key)
    print(f"# Gültigkeit: {KEY_DAYS} Tage (30+2) ab Ausstellung")
    print("# Kontakt: ame@sellerbach.de")
    return 0


def run_gui() -> int:
    try:
        from PySide6.QtWidgets import (
            QApplication,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PySide6 fehlt — pip install PySide6", file=sys.stderr)
        return 1

    class KeygenWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("InstantLens Doc — Keygenerator")
            self.resize(520, 280)
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.addWidget(QLabel("E-Mail:"))
            self.email = QLineEdit()
            self.email.setPlaceholderText("kunde@example.com")
            layout.addWidget(self.email)
            row = QHBoxLayout()
            btn = QPushButton("Key erzeugen")
            btn.clicked.connect(self._gen)
            row.addWidget(btn)
            btn2 = QPushButton("Prüfen")
            btn2.clicked.connect(self._verify)
            row.addWidget(btn2)
            layout.addLayout(row)
            self.out = QTextEdit()
            self.out.setReadOnly(True)
            layout.addWidget(self.out)
            layout.addWidget(QLabel(f"Keys gelten {KEY_DAYS} Tage. Kontakt: ame@sellerbach.de"))
            self.setCentralWidget(w)

        def _gen(self):
            email = self.email.text().strip()
            if not email or "@" not in email:
                QMessageBox.warning(self, "Hinweis", "Bitte gültige E-Mail eingeben.")
                return
            key = generate_key(email)
            self.out.setPlainText(key)

        def _verify(self):
            key = self.out.toPlainText().strip() or self.email.text().strip()
            ok, msg, data = verify_key(key)
            info = msg + (f"\n{data}" if data else "")
            QMessageBox.information(self, "Prüfung", info)

    app = QApplication(sys.argv)
    win = KeygenWindow()
    win.show()
    return app.exec()


def main() -> None:
    raise SystemExit(cli())


if __name__ == "__main__":
    main()
