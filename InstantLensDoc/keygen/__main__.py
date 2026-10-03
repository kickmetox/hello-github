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
from keygen.history import (
    HISTORY_MAX,
    add_history,
    clear_history,
    load_history,
    mask_key,
)


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
    p.add_argument(
        "--clear-history",
        action="store_true",
        help="Lokale Key-History leeren (keine Secrets in Logs) — 1.1.3",
    )
    args = p.parse_args(argv)

    if args.gui:
        return run_gui(days=args.days)

    if args.clear_history:
        clear_history()
        print(f"# History geleert (max. {HISTORY_MAX} Einträge)")
        return 0

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
    add_history(email=args.email, key=key, days=days)
    print(key)
    print(f"# Gültigkeit: {days} Tage" + (" (30+2)" if days == KEY_DAYS else "") + " ab Ausstellung")
    print("# Kontakt: ame@sellerbach.de")
    return 0


def run_gui(*, days: int | None = None) -> int:
    try:
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QKeySequence, QShortcut
        from PySide6.QtWidgets import (
            QApplication,
            QComboBox,
            QFileDialog,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QListWidget,
            QListWidgetItem,
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

    from instantlensdoc.core.app_settings import (
        KEYGEN_REVEAL_AUTO_HIDE_CHOICES,
        get_keygen_reveal_auto_hide_sec,
        set_keygen_reveal_auto_hide_sec,
    )

    class KeygenWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("InstantLens Doc — Keygenerator")
            self.resize(580, 500)
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

            hist_header = QHBoxLayout()
            hist_header.addWidget(
                QLabel(f"History (letzte {HISTORY_MAX} Keys, lokal):")
            )
            self.reveal_check = QPushButton("Reveal")
            self.reveal_check.setCheckable(True)
            self.reveal_check.setChecked(False)
            self.reveal_check.setToolTip(
                "Keys unmaskiert anzeigen — Auto-Hide (5/10/30 s); Esc maskiert; "
                "Countdown pausiert bei inaktivem Fenster (Label „pausiert“) — 1.1.8"
            )
            self.reveal_check.toggled.connect(self._on_reveal_toggled)
            self.reveal_countdown = QLabel("")
            self.reveal_countdown.setMinimumWidth(72)
            self.reveal_countdown.setAlignment(Qt.AlignCenter)
            self.reveal_countdown.setToolTip(
                "Countdown bis Auto-Hide — bei Fokusverlust Label „pausiert“, "
                "Fortsetzen bei Fokus — 1.1.8"
            )
            self.reveal_countdown.setStyleSheet("color: #555; font-variant-numeric: tabular-nums;")
            hide_row = QHBoxLayout()
            hide_row.addWidget(QLabel("Auto-Hide:"))
            self.hide_combo = QComboBox()
            cur_hide = get_keygen_reveal_auto_hide_sec()
            hide_pick = 0
            for i, sec in enumerate(KEYGEN_REVEAL_AUTO_HIDE_CHOICES):
                self.hide_combo.addItem(f"{sec} s", int(sec))
                if int(sec) == int(cur_hide):
                    hide_pick = i
            self.hide_combo.setCurrentIndex(hide_pick)
            self.hide_combo.setToolTip(
                "Reveal Auto-Hide Intervall (Settings: 5 / 10 / 30 s) — 1.1.6"
            )
            self.hide_combo.currentIndexChanged.connect(self._on_hide_interval_changed)
            hide_row.addWidget(self.hide_combo)
            btn_clear = QPushButton("Clear History")
            btn_clear.setToolTip(
                "Lokale Key-History leeren (keine Secrets in Logs) — 1.1.3"
            )
            btn_clear.clicked.connect(self._clear_history)
            hist_header.addStretch(1)
            hist_header.addLayout(hide_row)
            hist_header.addWidget(self.reveal_check)
            hist_header.addWidget(self.reveal_countdown)
            hist_header.addWidget(btn_clear)
            layout.addLayout(hist_header)
            self.history_list = QListWidget()
            self.history_list.setToolTip(
                "Maskiert (nur letzte 4); Hover/Reveal zeigt Key; "
                "Reveal Auto-Hide 5/10/30 s / Esc; Countdown „pausiert“ bei Fokusverlust; "
                "Doppelklick kopiert — 1.1.8"
            )
            self.history_list.setMaximumHeight(120)
            self.history_list.setMouseTracking(True)
            self.history_list.itemDoubleClicked.connect(self._history_copy)
            self.history_list.itemEntered.connect(self._history_hover_enter)
            self.history_list.viewport().installEventFilter(self)
            layout.addWidget(self.history_list)
            self._history_hover_row = -1
            self._reveal_remaining = 0
            self._countdown_paused = False
            self._reveal_paused_ms = 0
            self._reveal_timer = QTimer(self)
            self._reveal_timer.setSingleShot(True)
            self._reveal_timer.timeout.connect(self._auto_hide_reveal)
            self._countdown_timer = QTimer(self)
            self._countdown_timer.setInterval(1000)
            self._countdown_timer.timeout.connect(self._tick_countdown)
            esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
            esc.setContext(Qt.WindowShortcut)
            esc.activated.connect(self._mask_reveal)
            app = QApplication.instance()
            if app is not None:
                app.applicationStateChanged.connect(self._on_app_state_changed)

            layout.addWidget(
                QLabel(f"Standard: {KEY_DAYS} Tage. Kontakt: ame@sellerbach.de")
            )
            self.setCentralWidget(w)
            self._last_days = int(self.days_spin.value())
            self._reload_history()
            self._update_countdown_label()

        def _hide_seconds(self) -> int:
            data = self.hide_combo.currentData()
            try:
                val = int(data) if data is not None else get_keygen_reveal_auto_hide_sec()
            except (TypeError, ValueError):
                val = 10
            if val not in KEYGEN_REVEAL_AUTO_HIDE_CHOICES:
                val = 10
            return val

        def _on_hide_interval_changed(self, *_args) -> None:
            sec = self._hide_seconds()
            set_keygen_reveal_auto_hide_sec(sec)
            if self.reveal_check.isChecked():
                self._start_reveal_timers(sec)
                self.statusBar().showMessage(
                    f"Reveal an — Auto-Hide in {sec} s · Esc maskiert", 2500
                )

        def _start_reveal_timers(self, sec: int | None = None) -> None:
            seconds = int(sec if sec is not None else self._hide_seconds())
            self._countdown_paused = False
            self._reveal_paused_ms = 0
            self._reveal_remaining = seconds
            self._reveal_timer.stop()
            self._reveal_timer.start(seconds * 1000)
            self._countdown_timer.start()
            self._update_countdown_label()

        def _stop_reveal_timers(self) -> None:
            self._reveal_timer.stop()
            self._countdown_timer.stop()
            self._reveal_remaining = 0
            self._countdown_paused = False
            self._reveal_paused_ms = 0
            self._update_countdown_label()

        def _pause_countdown(self) -> None:
            """Countdown + Auto-Hide pausieren bei inaktivem Fenster — 1.1.7."""
            if not self.reveal_check.isChecked() or self._countdown_paused:
                return
            if not self._reveal_timer.isActive() and self._reveal_remaining <= 0:
                return
            self._countdown_paused = True
            remaining_ms = self._reveal_timer.remainingTime()
            if remaining_ms > 0:
                self._reveal_paused_ms = int(remaining_ms)
                self._reveal_remaining = max(1, (remaining_ms + 999) // 1000)
            else:
                self._reveal_paused_ms = max(0, int(self._reveal_remaining) * 1000)
            self._reveal_timer.stop()
            self._countdown_timer.stop()
            self._update_countdown_label()

        def _resume_countdown(self) -> None:
            """Countdown fortsetzen wenn Fenster wieder Fokus hat — 1.1.7."""
            if not self._countdown_paused or not self.reveal_check.isChecked():
                self._countdown_paused = False
                return
            self._countdown_paused = False
            ms = int(getattr(self, "_reveal_paused_ms", 0) or 0)
            self._reveal_paused_ms = 0
            if ms <= 0:
                self._auto_hide_reveal()
                return
            self._reveal_remaining = max(1, (ms + 999) // 1000)
            self._reveal_timer.start(ms)
            self._countdown_timer.start()
            self._update_countdown_label()

        def _on_app_state_changed(self, state) -> None:
            if state == Qt.ApplicationInactive or state == Qt.ApplicationSuspended:
                self._pause_countdown()
            elif state == Qt.ApplicationActive:
                self._resume_countdown()

        def changeEvent(self, event) -> None:
            from PySide6.QtCore import QEvent

            if event.type() == QEvent.WindowDeactivate:
                self._pause_countdown()
            elif event.type() == QEvent.WindowActivate:
                self._resume_countdown()
            super().changeEvent(event)

        def _tick_countdown(self) -> None:
            if not self.reveal_check.isChecked():
                self._stop_reveal_timers()
                return
            if self._countdown_paused:
                return
            self._reveal_remaining = max(0, int(self._reveal_remaining) - 1)
            self._update_countdown_label()
            if self._reveal_remaining <= 0:
                self._countdown_timer.stop()

        def _update_countdown_label(self) -> None:
            if self.reveal_check.isChecked() and self._reveal_remaining > 0:
                # Pause-Indikator am Countdown-Label — 1.1.8
                if self._countdown_paused:
                    self.reveal_countdown.setText(
                        f"{self._reveal_remaining}s · pausiert"
                    )
                    self.reveal_countdown.setStyleSheet(
                        "color: #a65; font-variant-numeric: tabular-nums; font-style: italic;"
                    )
                    self.reveal_countdown.setToolTip(
                        "Countdown pausiert (Fenster inaktiv) — 1.1.8"
                    )
                else:
                    self.reveal_countdown.setText(f"{self._reveal_remaining}s")
                    self.reveal_countdown.setStyleSheet(
                        "color: #555; font-variant-numeric: tabular-nums;"
                    )
                    self.reveal_countdown.setToolTip(
                        "Countdown bis Auto-Hide — bei Fokusverlust „pausiert“ — 1.1.8"
                    )
            elif self.reveal_check.isChecked():
                self.reveal_countdown.setText("0s")
                self.reveal_countdown.setStyleSheet(
                    "color: #555; font-variant-numeric: tabular-nums;"
                )
            else:
                self.reveal_countdown.setText("")
                self.reveal_countdown.setStyleSheet(
                    "color: #555; font-variant-numeric: tabular-nums;"
                )

        def _history_label(self, entry: dict, *, reveal: bool) -> str:
            email = entry.get("email") or "?"
            days = entry.get("days") or 0
            created = (entry.get("created") or "")[:10]
            key = str(entry.get("key") or "")
            shown = key if reveal else mask_key(key)
            return f"{email} · {days}d · {created} · {shown}"

        def _reload_history(self):
            self.history_list.clear()
            self._history_hover_row = -1
            reveal_all = bool(self.reveal_check.isChecked())
            for entry in load_history():
                label = self._history_label(entry, reveal=reveal_all)
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, entry)
                item.setToolTip(
                    "Hover/Reveal zeigt Key · Esc/Auto-Hide maskiert · "
                    "Countdown „pausiert“ bei Fokusverlust · Doppelklick kopiert — 1.1.8"
                )
                self.history_list.addItem(item)

        def _refresh_history_labels(self):
            reveal_all = bool(self.reveal_check.isChecked())
            for i in range(self.history_list.count()):
                item = self.history_list.item(i)
                if item is None:
                    continue
                entry = item.data(Qt.UserRole)
                if not isinstance(entry, dict):
                    continue
                reveal = reveal_all or (i == self._history_hover_row)
                item.setText(self._history_label(entry, reveal=reveal))

        def _mask_reveal(self) -> None:
            """Reveal aus / Keys wieder maskieren (Esc oder Auto-Hide) — 1.1.5/1.1.6."""
            self._stop_reveal_timers()
            if self.reveal_check.isChecked():
                self.reveal_check.setChecked(False)
            else:
                self._refresh_history_labels()
            self.statusBar().showMessage("History wieder maskiert", 2000)

        def _auto_hide_reveal(self) -> None:
            if self.reveal_check.isChecked():
                self._mask_reveal()

        def _on_reveal_toggled(self, checked: bool = False):
            if checked:
                sec = self._hide_seconds()
                self._start_reveal_timers(sec)
                self.statusBar().showMessage(
                    f"Reveal an — Auto-Hide in {sec} s · Esc maskiert", 3000
                )
            else:
                self._stop_reveal_timers()
            self._refresh_history_labels()

        def _history_hover_enter(self, item: QListWidgetItem):
            row = self.history_list.row(item) if item else -1
            if row == self._history_hover_row:
                return
            self._history_hover_row = row
            self._refresh_history_labels()

        def eventFilter(self, obj, event):
            from PySide6.QtCore import QEvent

            if obj is self.history_list.viewport():
                if event.type() == QEvent.Leave:
                    if self._history_hover_row >= 0:
                        self._history_hover_row = -1
                        self._refresh_history_labels()
            return super().eventFilter(obj, event)

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Escape and self.reveal_check.isChecked():
                self._mask_reveal()
                event.accept()
                return
            super().keyPressEvent(event)

        def _history_copy(self, item: QListWidgetItem):
            """Doppelklick kopiert Key in die Zwischenablage — 1.1.4."""
            entry = item.data(Qt.UserRole) if item else None
            if not isinstance(entry, dict):
                return
            key = str(entry.get("key") or "")
            if not key:
                return
            QApplication.clipboard().setText(key)
            self.out.setPlainText(key)
            email = str(entry.get("email") or "")
            if email:
                self.email.setText(email)
            try:
                d = int(entry.get("days") or KEY_DAYS)
            except (TypeError, ValueError):
                d = KEY_DAYS
            self.days_spin.setValue(max(1, d))
            self._last_days = d
            self.validity_label.setText(f"Gültigkeit: {d} Tage")
            self.statusBar().showMessage(
                "Key aus History kopiert (Zwischenablage)", 2500
            )

        def _clear_history(self):
            if self.history_list.count() <= 0:
                QMessageBox.information(self, "History", "History ist bereits leer.")
                return
            reply = QMessageBox.question(
                self,
                "Clear History",
                f"Lokale History ({self.history_list.count()} Einträge) leeren?",
            )
            if reply != QMessageBox.Yes:
                return
            clear_history()
            self._reload_history()
            self.statusBar().showMessage("History geleert", 2500)

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
            add_history(email=email, key=key, days=d)
            self._reload_history()

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
