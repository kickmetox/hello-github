"""Scan-Backend-Einstellungen (Widget) — Einstellungen → Scannen und Scan-Dialog → Erweitert — 2.6.54.

Wahl des Scanprogramms (Automatik / ScanTuxio Win / WIA / NAPS2 / eSCL / TWAIN /
externes Programm) mit Verfügbarkeitsanzeige (gefunden / nicht gefunden, Pfad),
„Pfad wählen…“ für NAPS2 und ScanTuxio sowie Befehlsvorlage + Ausgabeordner für ein
externes Programm. Persistenz über ``app_settings.get_scan_settings/set_scan_settings``.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.core.app_settings import get_scan_settings, set_scan_settings
from instantlensdoc.core.scan_transfer import (
    BACKEND_EXTERNAL,
    BACKEND_LABELS_DE,
    BACKEND_NAPS2,
    BACKEND_ORDER,
    BACKEND_SCANTUXIO,
    BACKEND_TWAIN,
    EXTERNAL_PLACEHOLDERS,
    backend_availability,
    is_windows,
    scan_log_path,
)

EXTERNAL_CMD_EXAMPLE_WIN = (
    r'"C:\Program Files\NAPS2\NAPS2.Console.exe" -o "{output}" --driver wia --dpi {dpi}'
)
EXTERNAL_CMD_EXAMPLE_POSIX = 'scanimage --format=png --resolution {dpi} --mode {color} -o "{output}"'


class ScanBackendSettingsWidget(QWidget):
    """Backend-Auswahl + Verfügbarkeit + Pfade + externes Programm."""

    backend_changed = Signal(str)
    settings_saved = Signal(dict)

    def __init__(self, parent=None, *, apply_immediately: bool = False, compact: bool = False):
        super().__init__(parent)
        self.setObjectName("scanBackendSettings")
        self._apply_immediately = bool(apply_immediately)
        self._compact = bool(compact)
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.backend_combo = QComboBox()
        self.backend_combo.setObjectName("scanBackendCombo")
        self.backend_combo.setToolTip(
            "Welches Scanprogramm „Scannen“ verwendet. Automatik = lokal WIA/NAPS2, "
            "Netzwerk eSCL/AirScan (kein WIA-Connect im Energiesparmodus) — 2.6.57"
        )
        for key in BACKEND_ORDER:
            self.backend_combo.addItem(BACKEND_LABELS_DE[key], key)
        form.addRow("Scan-Backend:", self.backend_combo)
        self.backend_status = QLabel("")
        self.backend_status.setObjectName("scanBackendStatus")
        self.backend_status.setWordWrap(True)
        self.backend_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("", self.backend_status)
        root.addLayout(form)

        avail_box = QGroupBox("Verfügbarkeit der Backends")
        avail_box.setObjectName("scanBackendAvailability")
        self.avail_box = avail_box
        av = QVBoxLayout(avail_box)
        self.avail_list = QListWidget()
        self.avail_list.setObjectName("scanBackendAvailabilityList")
        self.avail_list.setWordWrap(False)
        self.avail_list.setMinimumHeight(168)
        self.avail_list.setMaximumHeight(200)
        self.avail_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.avail_list.setAlternatingRowColors(True)
        av.addWidget(self.avail_list)
        self._status_labels: dict[str, QListWidgetItem] = {}
        btn_row = QHBoxLayout()
        self.btn_check = QPushButton("Verfügbarkeit prüfen")
        self.btn_check.setObjectName("scanBackendCheckBtn")
        self.btn_check.clicked.connect(self.refresh_availability)
        btn_row.addWidget(self.btn_check)
        self.btn_log = QPushButton("scan.log öffnen")
        self.btn_log.setObjectName("scanLogOpenBtn")
        self.btn_log.setToolTip(str(scan_log_path()))
        self.btn_log.clicked.connect(self._open_log)
        btn_row.addWidget(self.btn_log)
        btn_row.addStretch(1)
        av.addLayout(btn_row)
        root.addWidget(avail_box)

        paths_box = QGroupBox("Programmpfade (leer = automatisch suchen)")
        paths_box.setObjectName("scanBackendPaths")
        pform = QFormLayout(paths_box)
        pform.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.naps2_path = QLineEdit()
        self.naps2_path.setObjectName("scanNaps2Path")
        self.naps2_path.setPlaceholderText(r"C:\Program Files\NAPS2\NAPS2.Console.exe")
        self.btn_naps2_pick = QPushButton("Pfad wählen…")
        self.btn_naps2_pick.setObjectName("scanNaps2PickBtn")
        self.btn_naps2_pick.clicked.connect(
            lambda: self._pick_exe(self.naps2_path, "NAPS2.Console.exe wählen", "NAPS2.Console.exe")
        )
        pform.addRow("NAPS2.Console:", self._with_button(self.naps2_path, self.btn_naps2_pick))
        self.scantuxio_path = QLineEdit()
        self.scantuxio_path.setObjectName("scanScantuxioPath")
        self.scantuxio_path.setPlaceholderText(r"D:\AI_Temp\ScanTuxio Win\ScanTuxio.exe")
        self.btn_scantuxio_pick = QPushButton("Pfad wählen…")
        self.btn_scantuxio_pick.setObjectName("scanScantuxioPickBtn")
        self.btn_scantuxio_pick.clicked.connect(
            lambda: self._pick_exe(
                self.scantuxio_path, "ScanTuxio.exe oder scantuxio\\main.py wählen", "ScanTuxio.exe main.py"
            )
        )
        pform.addRow("ScanTuxio:", self._with_button(self.scantuxio_path, self.btn_scantuxio_pick))
        root.addWidget(paths_box)

        self.external_box = QGroupBox("Externes Programm")
        self.external_box.setObjectName("scanExternalBox")
        eform = QFormLayout(self.external_box)
        eform.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.external_cmd = QLineEdit()
        self.external_cmd.setObjectName("scanExternalCmd")
        self.external_cmd.setPlaceholderText(
            EXTERNAL_CMD_EXAMPLE_WIN if is_windows() else EXTERNAL_CMD_EXAMPLE_POSIX
        )
        self.external_cmd.setToolTip(
            "Befehlszeile mit Platzhaltern. {output} = Zieldatei (PNG), {outdir} = Ausgabeordner, "
            "{dpi}, {device} = Gerätename, {color} = Color/Gray/Lineart, {source} = Flatbed/ADF/ADF Duplex"
        )
        eform.addRow("Befehlszeile:", self.external_cmd)
        ph = QLabel("Platzhalter: " + "  ".join(f"<code>{p}</code>" for p in EXTERNAL_PLACEHOLDERS))
        ph.setObjectName("scanExternalPlaceholders")
        ph.setTextFormat(Qt.RichText)
        ph.setWordWrap(True)
        eform.addRow("", ph)
        self.external_outdir = QLineEdit()
        self.external_outdir.setObjectName("scanExternalOutdir")
        self.external_outdir.setPlaceholderText("Ordner, in dem das Programm Scans ablegt (neue Dateien werden übernommen)")
        self.btn_external_outdir = QPushButton("…")
        self.btn_external_outdir.setObjectName("scanExternalOutdirBtn")
        self.btn_external_outdir.setFixedWidth(32)
        self.btn_external_outdir.clicked.connect(self._pick_outdir)
        eform.addRow("Ausgabeordner:", self._with_button(self.external_outdir, self.btn_external_outdir))
        root.addWidget(self.external_box)

        self.backend_combo.currentIndexChanged.connect(self._on_backend_index_changed)
        for edit in (self.naps2_path, self.scantuxio_path, self.external_cmd, self.external_outdir):
            edit.editingFinished.connect(self._on_field_edited)

        if compact:
            # Scan-Dialog: Verfügbarkeit nur als Statuszeile, Details in Einstellungen
            avail_box.setVisible(False)
            self.btn_check.setVisible(False)

        self.load()
        self.refresh_availability()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _with_button(edit: QLineEdit, btn: QPushButton) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(edit, 1)
        h.addWidget(btn)
        return w

    def _pick_exe(self, edit: QLineEdit, title: str, names: str) -> None:
        start = edit.text().strip() or str(Path.home())
        filt = f"Programm ({names} *.exe *.py);;Alle Dateien (*)"
        path, _ = QFileDialog.getOpenFileName(self, title, start, filt)
        if path:
            edit.setText(path)
            self._on_field_edited()
            self.refresh_availability()

    def _pick_outdir(self) -> None:
        start = self.external_outdir.text().strip() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "Ausgabeordner des externen Programms", start)
        if path:
            self.external_outdir.setText(path)
            self._on_field_edited()

    def _open_log(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        p = scan_log_path()
        try:
            if not p.exists():
                p.write_text("", encoding="utf-8")
        except OSError:
            pass
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    # ------------------------------------------------------------------ state
    def current_backend(self) -> str:
        return str(self.backend_combo.currentData() or "auto")

    def set_backend(self, key: str) -> None:
        idx = self.backend_combo.findData(key)
        if idx >= 0:
            self.backend_combo.setCurrentIndex(idx)

    def values(self) -> dict:
        return {
            "scan_backend": self.current_backend(),
            "scan_naps2_path": self.naps2_path.text().strip(),
            "scan_scantuxio_path": self.scantuxio_path.text().strip(),
            "scan_external_cmd": self.external_cmd.text().strip(),
            "scan_external_outdir": self.external_outdir.text().strip(),
        }

    def load(self) -> None:
        self._loading = True
        try:
            cfg = get_scan_settings()
            self.set_backend(str(cfg.get("scan_backend") or "auto"))
            self.naps2_path.setText(str(cfg.get("scan_naps2_path") or ""))
            self.scantuxio_path.setText(str(cfg.get("scan_scantuxio_path") or ""))
            self.external_cmd.setText(str(cfg.get("scan_external_cmd") or ""))
            self.external_outdir.setText(str(cfg.get("scan_external_outdir") or ""))
        finally:
            self._loading = False
        self._sync_external_visibility()
        self._update_backend_status()

    def save(self) -> dict:
        vals = self.values()
        out = set_scan_settings(**vals)
        self.settings_saved.emit(out)
        return out

    def refresh_availability(self) -> None:
        cfg = get_scan_settings()
        cfg.update(self.values())
        self._statuses = {s.key: s for s in backend_availability(cfg)}
        self.avail_list.clear()
        self._status_labels = {}
        for key in BACKEND_ORDER:
            st = self._statuses.get(key)
            if st is None:
                continue
            mark = "gefunden" if st.available else "nicht gefunden"
            line = f"{st.label} — {mark}: {st.detail}"
            item = QListWidgetItem(line)
            item.setData(Qt.UserRole, key)
            item.setToolTip(st.path or st.detail)
            if st.available:
                item.setForeground(Qt.darkGreen)
            else:
                item.setForeground(Qt.darkRed)
            self.avail_list.addItem(item)
            self._status_labels[key] = item
        self._update_backend_status()

    def _update_backend_status(self) -> None:
        key = self.current_backend()
        st = getattr(self, "_statuses", {}).get(key)
        if st is None:
            self.backend_status.setText("")
            return
        text = st.status_text_de()
        if key == BACKEND_TWAIN and not st.available:
            text += " — TWAIN wird über NAPS2.Console (--driver twain) angesprochen."
        if key == BACKEND_SCANTUXIO and not st.available:
            text += " — Pfad unter „ScanTuxio“ wählen."
        if key == BACKEND_NAPS2 and not st.available:
            text += " — NAPS2 installieren oder Pfad wählen."
        self.backend_status.setText(text)
        self.backend_status.setStyleSheet("color: #1b7f3b;" if st.available else "color: #a33;")

    def _sync_external_visibility(self) -> None:
        is_ext = self.current_backend() == BACKEND_EXTERNAL
        if self._compact:
            self.external_box.setVisible(is_ext)
        else:
            self.external_box.setEnabled(True)

    def _on_backend_index_changed(self, *_a) -> None:
        if self._loading:
            return
        self._sync_external_visibility()
        self._update_backend_status()
        key = self.current_backend()
        if self._apply_immediately:
            set_scan_settings(scan_backend=key)
        self.backend_changed.emit(key)

    def _on_field_edited(self, *_a) -> None:
        if self._loading:
            return
        if self._apply_immediately:
            self.save()
