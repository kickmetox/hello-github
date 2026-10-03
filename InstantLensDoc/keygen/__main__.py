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
    p.add_argument(
        "--days",
        type=int,
        default=None,
        metavar="N",
        help=f"Gültigkeitstage (Standard: {KEY_DAYS}; kompatibel ohne --days)",
    )
    args = p.parse_args(argv)

    if args.gui:
        return run_gui(days=args.days)

    if args.verify:
        ok, msg, data = verify_key(args.verify)
        print("OK:" if ok else "FEHLER:", msg)
        if data:
            print("Payload:", data)
        return 0 if ok else 1

    if not args.email:
        p.print_help()
        return 2

    days = int(args.days) if args.days is not None else KEY_DAYS
    if days < 1:
        print("FEHLER: --days muss ≥ 1 sein", file=sys.stderr)
        return 2
    key = generate_key(args.email, days=days)
    print(key)
    print(f"# Gültigkeit: {days} Tage" + (" (30+2)" if days == KEY_DAYS else "") + " ab Ausstellung")
    print("# Kontakt: ame@sellerbach.de")
    return 0


def run_gui(*, days: int | None = None) -> int:
    try:
        from PySide6.QtWidgets import (
            QApplication,
            QFileDialog,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QSpinBox,
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
            self.resize(540, 320)
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.addWidget(QLabel("E-Mail:"))
            self.email = QLineEdit()
            self.email.setPlaceholderText("kunde@example.com")
            layout.addWidget(self.email)
            days_row = QHBoxLayout()
            days_row.addWidget(QLabel("Tage:"))
            self.days_spin = QSpinBox()
            self.days_spin.setRange(1, 3650)
            self.days_spin.setValue(int(days) if days is not None else KEY_DAYS)
            self.days_spin.setToolTip(
                f"Gültigkeitstage (--days; Standard {KEY_DAYS}) — 1.1.2"
            )
            days_row.addWidget(self.days_spin)
            days_row.addStretch(1)
            layout.addLayout(days_row)
            row = QHBoxLayout()
            btn = QPushButton("Key erzeugen")
            btn.clicked.connect(self._gen)
            row.addWidget(btn)
            btn2 = QPushButton("Prüfen")
            btn2.clicked.connect(self._verify)
            row.addWidget(btn2)
            btn_copy = QPushButton("Kopieren")
            btn_copy.setToolTip("Key als Klartext in die Zwischenablage kopieren — 1.1.0")
            btn_copy.clicked.connect(self._copy)
            row.addWidget(btn_copy)
            btn_save = QPushButton("Speichern als .txt…")
            btn_save.setToolTip("Key als Textdatei speichern — 1.1.2")
            btn_save.clicked.connect(self._save_txt)
            row.addWidget(btn_save)
            layout.addLayout(row)
            out_header = QHBoxLayout()
            out_header.addWidget(QLabel("Ausgabe (Klartext, ohne QR):"))
            self.validity_label = QLabel("")
            self.validity_label.setToolTip(
                f"Gültigkeitstage des generierten Keys (Standard {KEY_DAYS} = 30+2) — 1.1.2"
            )
            out_header.addStretch(1)
            out_header.addWidget(self.validity_label)
            layout.addLayout(out_header)
            self.out = QTextEdit()
            self.out.setReadOnly(True)
            self.out.setPlaceholderText("Key erscheint hier als Klartext…")
            layout.addWidget(self.out)
            layout.addWidget(
                QLabel(f"Standard: {KEY_DAYS} Tage. Kontakt: ame@sellerbach.de")
            )
            self.setCentralWidget(w)
            self._last_days = int(self.days_spin.value())

        def _gen(self):
            email = self.email.text().strip()
            if not email or "@" not in email:
                QMessageBox.warning(self, "Hinweis", "Bitte gültige E-Mail eingeben.")
                return
            d = int(self.days_spin.value())
            key = generate_key(email, days=d)
            self.out.setPlainText(key)
            self._last_days = d
            self.validity_label.setText(f"Gültigkeit: {d} Tage")

        def _copy(self):
            text = self.out.toPlainText().strip()
            if not text:
                QMessageBox.information(self, "Kopieren", "Kein Key zum Kopieren.")
                return
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage("Key in Zwischenablage kopiert", 2500)

        def _save_txt(self):
            text = self.out.toPlainText().strip()
            if not text:
                QMessageBox.information(self, "Speichern", "Kein Key zum Speichern.")
                return
            email = self.email.text().strip() or "key"
            safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in email)
            suggested = f"ILD1-{safe}.txt"
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Key als .txt speichern",
                suggested,
                "Textdatei (*.txt)",
            )
            if not path:
                return
            if not path.lower().endswith(".txt"):
                path += ".txt"
            d = self._last_days
            body = (
                f"{text}\n"
                f"# E-Mail: {email}\n"
                f"# Gültigkeit: {d} Tage\n"
                f"# Kontakt: ame@sellerbach.de\n"
            )
            try:
                Path(path).write_text(body, encoding="utf-8")
            except Exception as e:
                QMessageBox.critical(self, "Speichern", str(e))
                return
            self.statusBar().showMessage(f"Gespeichert: {path}", 4000)

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
