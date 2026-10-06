"""Scan-Dialog — ein Einstieg, ein Dialog — 2.6.54.

Gerät (Dropdown, Auto-Refresh, merkt letztes Gerät je Backend) · DPI / Farbe /
Duplex · **Scannen** (gewähltes Backend, Ergebnis sofort ins Dokument) ·
**ScanTuxio öffnen**. Erweitert (zuklappbar): Backend-Wahl, OCR, Import,
Gerätefilter, ScanTuxio-Übergabe.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.core.app_settings import (
    get_scan_backend,
    get_scan_last_device,
    get_scan_settings,
    set_scan_backend,
    set_scan_last_device,
    set_scan_settings,
)
from instantlensdoc.core.devices import (
    NO_DEVICE_STATUS_DE,
    SCAN_START_HINT_DE,
    WINDOWS_PRINTER_DRIVER_HINT_DE,
    WINDOWS_SCAN_DEPS_HINT,
    WINDOWS_SCANNER_DRIVER_HINT_DE,
    DeviceDiscoveryResult,
    DeviceInfo,
    DeviceKind,
    DeviceScope,
    discover_devices,
    format_discovery_status,
    load_cached_discovery,
    scanner_choices,
)
from instantlensdoc.core.device_io import (
    ACQUIRE_OK_TIMEOUT_S,
    DEVICE_IO_TIMEOUT_S,
    DEVICE_TIMEOUT_DE,
    io_timeout_s,
)
from instantlensdoc.core.ocr import (
    INSTALL_HINT_DE,
    LANG_PRESETS,
    OcrOutputMode,
    tesseract_available,
)
from instantlensdoc.core.scan import (
    acquire_from_scanner,
    expand_scan_import_paths,
    import_image_paths,
    insert_scan_pages_into_pdf,
    last_acquire_error,
    last_acquire_result,
)
from instantlensdoc.core.scan_transfer import (
    BACKEND_LABELS_DE,
    BACKEND_SCANTUXIO,
    COLOR_LABELS_DE,
    COLOR_MODES,
    DPI_CHOICES,
    SOURCE_LABELS_DE,
    SOURCES,
    classify_device_id,
    scan_log,
    scan_log_path,
)
from instantlensdoc.ui.async_worker import watch_worker
from instantlensdoc.ui.scan_settings import ScanBackendSettingsWidget

try:
    from instantlensdoc.core.scantuxio_ui import (
        build_launch,
        collect_new_scan_files,
        default_watch_dirs,
        find_scantuxio_install,
        launch_scantuxio_process,
        missing_scantuxio_hint_de,
        prepare_handshake_dir,
        read_handoff_manifest,
        snapshot_scan_files,
        wia_busy_user_hint_de,
    )
except Exception:  # pragma: no cover
    build_launch = None  # type: ignore
    collect_new_scan_files = None  # type: ignore
    default_watch_dirs = None  # type: ignore
    find_scantuxio_install = None  # type: ignore
    launch_scantuxio_process = None  # type: ignore
    missing_scantuxio_hint_de = None  # type: ignore
    prepare_handshake_dir = None  # type: ignore
    read_handoff_manifest = None  # type: ignore
    snapshot_scan_files = None  # type: ignore
    wia_busy_user_hint_de = None  # type: ignore


def _st_ui_available() -> bool:
    return callable(find_scantuxio_install) and callable(launch_scantuxio_process)


class ScanDialog(QDialog):
    """Ein Scan-Dialog: Gerät + Optionen + Scannen. Erweitert zuklappbar."""

    def __init__(
        self,
        pdf_view,
        parent=None,
        *,
        auto_launch_scantuxio: bool = False,
        preferred_device_id: str | None = None,
    ):
        super().__init__(parent)
        self.pdf_view = pdf_view
        self._discovery = DeviceDiscoveryResult()
        self._pending_images: list[Path] = []
        self._choices = []
        self._auto_launch_scantuxio = bool(auto_launch_scantuxio)
        self._preferred_device_id = str(preferred_device_id or "").strip()
        self._st_proc = None
        self._st_handshake: Path | None = None
        self._st_watch: list[Path] = []
        self._st_snapshot: dict[str, tuple[int, int]] = {}
        self._last_result = None
        self._io_busy = False
        self._insert_after_acquire = False
        self._discover_watch = None
        self._acquire_watch = None
        self._discover_inflight = False
        self.setWindowTitle("Scannen")
        self.setWindowModality(Qt.WindowModal)
        self.setObjectName("scanDialog")
        self.resize(540, 520)
        self.setAccessibleName("Scannen")
        self.setAccessibleDescription(
            "Scanner wählen, scannen, Ergebnis ins Dokument — 2.6.54"
        )

        layout = QVBoxLayout(self)
        self.hint = QLabel(
            "Gerät wählen und <b>Scannen</b> — das Bild wird ins Dokument übernommen. "
            "Scan-Programm unter Erweitert oder Einstellungen → Scannen."
        )
        self.hint.setWordWrap(True)
        self.hint.setObjectName("scanDialogHint")
        self.hint.setTextFormat(Qt.RichText)
        layout.addWidget(self.hint)

        self.entry_banner = QLabel(
            "<b>Scannen…</b> · Ctrl+Shift+S · Geräte · Toolbar Scan… · Startseite"
        )
        self.entry_banner.setWordWrap(True)
        self.entry_banner.setObjectName("scanEntryBanner")
        self.entry_banner.setStyleSheet(
            "background:#eef5ff; color:#1a3a5c; padding:6px; border-radius:4px;"
        )
        layout.addWidget(self.entry_banner)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        dev_row = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.setObjectName("scanDeviceCombo")
        self.device_combo.setAccessibleName("Scanner")
        self.device_combo.setMinimumContentsLength(28)
        self.device_combo.currentIndexChanged.connect(self._on_device_combo_changed)
        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setObjectName("scanDeviceRefresh")
        self.btn_refresh.setToolTip("Geräteliste neu laden")
        self.btn_refresh.setFixedWidth(32)
        self.btn_refresh.clicked.connect(self.refresh_devices)
        self.btn_rescan = QPushButton("Neu")
        self.btn_rescan.setObjectName("scanDeviceRescan")
        self.btn_rescan.setToolTip("Vollständige Neu-Erkennung (lokal + Netzwerk)")
        self.btn_rescan.setVisible(False)
        self.btn_rescan.clicked.connect(self.refresh_devices)
        self.btn_retry = QPushButton("Erneut")
        self.btn_retry.setObjectName("scanDeviceRetry")
        self.btn_retry.setToolTip("Geräteliste neu laden — 2.6.54")
        self.btn_retry.setVisible(False)
        self.btn_retry.clicked.connect(self._retry_scan_flow)
        dev_row.addWidget(self.device_combo, 1)
        dev_row.addWidget(self.btn_refresh)
        form.addRow("Gerät:", dev_row)

        self.dpi_combo = QComboBox()
        self.dpi_combo.setObjectName("scanDpiCombo")
        for d in DPI_CHOICES:
            self.dpi_combo.addItem(f"{d} dpi", int(d))
        form.addRow("Auflösung:", self.dpi_combo)

        self.color_combo = QComboBox()
        self.color_combo.setObjectName("scanColorCombo")
        for m in COLOR_MODES:
            self.color_combo.addItem(COLOR_LABELS_DE[m], m)
        form.addRow("Farbe:", self.color_combo)

        self.source_combo = QComboBox()
        self.source_combo.setObjectName("scanSourceCombo")
        for s in SOURCES:
            self.source_combo.addItem(SOURCE_LABELS_DE[s], s)
        form.addRow("Quelle:", self.source_combo)
        layout.addLayout(form)

        act = QHBoxLayout()
        self.btn_scan = QPushButton("Scannen")
        self.btn_scan.setObjectName("scanStartBtn")
        self.btn_scan.setDefault(True)
        self.btn_scan.setToolTip("Scan mit dem gewählten Backend starten und ins Dokument übernehmen")
        self.btn_scan.clicked.connect(self._do_scan_and_insert)
        self.btn_scantuxio = QPushButton("ScanTuxio öffnen")
        self.btn_scantuxio.setObjectName("scanScantuxioBtn")
        self.btn_scantuxio.setToolTip("ScanTuxio-Hauptfenster starten und Scan übernehmen — 2.6.54")
        self.btn_scantuxio.clicked.connect(self._launch_scantuxio_ui)
        act.addWidget(self.btn_scan)
        act.addWidget(self.btn_scantuxio)
        layout.addLayout(act)

        self.device_status = QLabel("")
        self.device_status.setObjectName("scanDeviceStatus")
        self.device_status.setWordWrap(True)
        layout.addWidget(self.device_status)

        self.pending_label = QLabel("Keine Seiten in der Warteschlange.")
        self.pending_label.setObjectName("scanPendingLabel")
        self.pending_label.setWordWrap(True)
        layout.addWidget(self.pending_label)

        self.adv_toggle = QPushButton("Erweitert ▸")
        self.adv_toggle.setObjectName("scanAdvancedToggle")
        self.adv_toggle.setCheckable(True)
        self.adv_toggle.setFlat(True)
        self.adv_toggle.setStyleSheet("text-align:left; padding:4px 0;")
        layout.addWidget(self.adv_toggle)

        self.adv_panel = QWidget()
        self.adv_panel.setObjectName("scanAdvancedPanel")
        self.adv_panel.setVisible(False)
        adv = QVBoxLayout(self.adv_panel)
        adv.setContentsMargins(0, 0, 0, 0)

        self.backend_widget = ScanBackendSettingsWidget(
            self, apply_immediately=True, compact=True
        )
        self.backend_widget.backend_changed.connect(self._on_backend_changed)
        adv.addWidget(self.backend_widget)

        # Legacy-Geräteliste (Geräte-Dialog / Smoke-Tests)
        dev_box = QGroupBox("Geräte (Drucker & Scanner)")
        dev_box.setObjectName("scanDevicesGroup")
        dev_layout = QVBoxLayout(dev_box)
        self.device_list = QListWidget()
        self.device_list.setObjectName("scanDeviceList")
        self.device_list.setAlternatingRowColors(True)
        self.device_list.setAccessibleName("Geräteliste")
        self.device_list.setMaximumHeight(140)
        self.device_list.currentItemChanged.connect(self._on_list_item_changed)
        dev_layout.addWidget(self.device_list)
        filt_row = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.setObjectName("scanDeviceFilter")
        self.filter_combo.addItem("Alle Geräte", "all")
        self.filter_combo.addItem("Nur Scanner", "scanner")
        self.filter_combo.addItem("Nur Drucker", "printer")
        self.filter_combo.addItem("Nur Netzwerk", "network")
        self.filter_combo.currentIndexChanged.connect(self._populate_device_list)
        filt_row.addWidget(self.filter_combo, 1)
        dev_layout.addLayout(filt_row)
        adv.addWidget(dev_box)

        extra_btns = QHBoxLayout()
        self.btn_acquire = QPushButton("WIA / NAPS2…")
        self.btn_acquire.setObjectName("scanAcquireBtn")
        self.btn_acquire.setToolTip("Scan mit dem gewählten Backend, ohne sofort einzufügen")
        self.btn_acquire.clicked.connect(self._acquire_scan)
        self.btn_import = QPushButton("Bilder importieren…")
        self.btn_import.setObjectName("scanImportBtn")
        self.btn_import.setToolTip("PNG/JPEG/TIFF/BMP als Seiten importieren")
        self.btn_import.clicked.connect(self._import_images)
        self.btn_take_scan = QPushButton("Scan übernehmen")
        self.btn_take_scan.setObjectName("scanTakeBtn")
        self.btn_take_scan.setToolTip("Neue Dateien aus ScanTuxio-Übergabeordner übernehmen")
        self.btn_take_scan.clicked.connect(self._collect_scantuxio_output)
        extra_btns.addWidget(self.btn_acquire)
        extra_btns.addWidget(self.btn_import)
        extra_btns.addWidget(self.btn_take_scan)
        adv.addLayout(extra_btns)

        ocr_form = QFormLayout()
        self.ocr_enabled = QCheckBox("OCR mit Tesseract (Layout-Erhalt)")
        self.ocr_enabled.setObjectName("scanOcrEnabled")
        self.ocr_enabled.setChecked(True)
        ok_tess, tess_msg = tesseract_available()
        self.ocr_enabled.setEnabled(ok_tess)
        if not ok_tess:
            self.ocr_enabled.setChecked(False)
            self.ocr_enabled.setToolTip(tess_msg)
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("scanOcrLang")
        for label, code in LANG_PRESETS.items():
            self.lang_combo.addItem(label, code)
        idx = self.lang_combo.findData("deu+eng")
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.layout_hocr = QCheckBox("hOCR Sidecar")
        self.layout_hocr.setObjectName("scanOcrHocr")
        self.layout_hocr.setChecked(True)
        self.layout_tsv = QCheckBox("TSV Sidecar")
        self.layout_tsv.setObjectName("scanOcrTsv")
        self.layout_tsv.setChecked(True)
        self.word_suite_check = QCheckBox("In Word-Suite öffnen/übernehmen")
        self.word_suite_check.setObjectName("scanOcrWordSuite")
        self.word_suite_check.setChecked(True)
        self.ocr_enabled.toggled.connect(self._sync_scan_ocr_opts)
        ocr_form.addRow(self.ocr_enabled)
        ocr_form.addRow("OCR-Sprache:", self.lang_combo)
        ocr_form.addRow(self.layout_hocr)
        ocr_form.addRow(self.layout_tsv)
        ocr_form.addRow(self.word_suite_check)
        adv.addLayout(ocr_form)
        self._sync_scan_ocr_opts()

        self.tess_hint = QLabel(
            tess_msg if ok_tess else INSTALL_HINT_DE.split("\n\n")[0]
            + "\n\n" + WINDOWS_SCAN_DEPS_HINT
        )
        self.tess_hint.setObjectName("scanTessHint")
        self.tess_hint.setWordWrap(True)
        self.tess_hint.setStyleSheet("color: #555;")
        adv.addWidget(self.tess_hint)
        layout.addWidget(self.adv_panel)
        self.adv_toggle.toggled.connect(self._on_adv_toggled)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("In Dokument einfügen")
        buttons.button(QDialogButtonBox.Ok).setObjectName("scanInsertOk")
        cancel = buttons.button(QDialogButtonBox.Cancel)
        if cancel is not None:
            cancel.setText("Abbrechen")
        buttons.accepted.connect(self._insert_into_document)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._st_timer = QTimer(self)
        self._st_timer.setInterval(1200)
        self._st_timer.timeout.connect(self._poll_scantuxio_output)
        self._load_prefs()
        # Sofort aus Cache füllen — keine Hardware-Suche im GUI-Thread.
        self._apply_discovery(load_cached_discovery(), from_cache=True)
        QTimer.singleShot(0, self._start_discovery_bg)
        if self._auto_launch_scantuxio:
            QTimer.singleShot(0, self._launch_scantuxio_ui)

    def _on_adv_toggled(self, on: bool) -> None:
        self.adv_panel.setVisible(bool(on))
        self.adv_toggle.setText("Erweitert ▾" if on else "Erweitert ▸")
        if on:
            self.resize(max(self.width(), 560), max(self.height(), 720))

    def _load_prefs(self) -> None:
        cfg = get_scan_settings()
        dpi = int(cfg.get("scan_dpi") or 300)
        idx = self.dpi_combo.findData(dpi)
        if idx >= 0:
            self.dpi_combo.setCurrentIndex(idx)
        cidx = self.color_combo.findData(str(cfg.get("scan_color_mode") or "Color"))
        if cidx >= 0:
            self.color_combo.setCurrentIndex(cidx)
        sidx = self.source_combo.findData(str(cfg.get("scan_source") or "Flatbed"))
        if sidx >= 0:
            self.source_combo.setCurrentIndex(sidx)
        if hasattr(self, "ocr_enabled"):
            try:
                self.ocr_enabled.setChecked(bool(cfg.get("scan_ocr_enabled", True)) and self.ocr_enabled.isEnabled())
            except Exception:
                pass

    def _save_scan_prefs(self) -> None:
        try:
            set_scan_settings(
                scan_dpi=int(self.dpi_combo.currentData() or 300),
                scan_color_mode=str(self.color_combo.currentData() or "Color"),
                scan_source=str(self.source_combo.currentData() or "Flatbed"),
                scan_ocr_enabled=bool(self.ocr_enabled.isChecked()),
            )
        except Exception:
            pass

    def _sync_scan_ocr_opts(self, *_args) -> None:
        on = bool(self.ocr_enabled.isChecked()) and self.ocr_enabled.isEnabled()
        self.lang_combo.setEnabled(on)
        self.layout_hocr.setEnabled(on)
        self.layout_tsv.setEnabled(on)
        if hasattr(self, "word_suite_check"):
            self.word_suite_check.setEnabled(on)

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            if getattr(self, "_st_timer", None) is not None:
                self._st_timer.stop()
        except Exception:
            pass
        self._save_scan_prefs()
        super().closeEvent(event)

    def open_in_word_suite(self) -> bool:
        return bool(getattr(self, "word_suite_check", None) and self.word_suite_check.isChecked())

    def current_backend(self) -> str:
        try:
            return self.backend_widget.current_backend()
        except Exception:
            return get_scan_backend()

    def selected_scanner(self) -> DeviceInfo | None:
        data = self.device_combo.currentData()
        if isinstance(data, DeviceInfo) and data.kind == DeviceKind.SCANNER:
            return data
        item = self.device_list.currentItem()
        if item:
            dev = item.data(Qt.UserRole)
            if isinstance(dev, DeviceInfo) and dev.kind == DeviceKind.SCANNER:
                return dev
        return None

    def selected_choice_alternates(self) -> list[DeviceInfo]:
        idx = self.device_combo.currentIndex()
        if 0 <= idx < len(self._choices):
            return list(self._choices[idx].alternates)
        return []

    def selected_printer(self) -> DeviceInfo | None:
        item = self.device_list.currentItem()
        if not item:
            return None
        dev = item.data(Qt.UserRole)
        if isinstance(dev, DeviceInfo) and dev.kind == DeviceKind.PRINTER:
            return dev
        return None

    def printer_names(self) -> list[str]:
        return [p.name for p in self._discovery.printers]

    def refresh_devices(self) -> None:
        """Geräteliste: Cache sofort, Live-Suche im Hintergrund — nie GUI-blockierend."""
        self._apply_discovery(load_cached_discovery(), from_cache=True)
        self._start_discovery_bg()

    def _apply_discovery(self, result: DeviceDiscoveryResult, *, from_cache: bool = False) -> None:
        self._discovery = result or DeviceDiscoveryResult()
        self._populate_device_combo()
        self._populate_device_list()
        msg = format_discovery_status(self._discovery)
        if from_cache and (self._discovery.scanners or self._discovery.printers):
            msg = "Zwischengespeichert: " + msg + " — Suche im Hintergrund…"
        elif from_cache:
            msg = "Suche Geräte im Hintergrund… (letzte Liste leer)"
        self.device_status.setText(msg)
        self.device_status.setAccessibleName(msg)
        self.device_status.setToolTip(
            "\n".join(self._discovery.warnings[:6]) if self._discovery.warnings else msg
        )
        if not self._discovery.printers and not self._discovery.scanners:
            tip = (
                WINDOWS_SCANNER_DRIVER_HINT_DE
                + "\n\n"
                + WINDOWS_PRINTER_DRIVER_HINT_DE
                + "\n\n"
                + WINDOWS_SCAN_DEPS_HINT
                + "\n\n"
                + SCAN_START_HINT_DE
            )
            self.device_status.setToolTip(tip)
            if not (self.device_status.text() or "").strip():
                self.device_status.setText(NO_DEVICE_STATUS_DE)

    def _start_discovery_bg(self) -> None:
        if self._io_busy:
            return
        if getattr(self, "_discover_inflight", False):
            return
        self._discover_inflight = True
        self.btn_refresh.setEnabled(False)
        self.btn_rescan.setEnabled(False)
        if not (self._discovery.scanners or self._discovery.printers):
            self.device_status.setText("Suche Geräte…")
        timeout = io_timeout_s(45.0)

        def _done(result) -> None:
            self._discover_inflight = False
            self.btn_refresh.setEnabled(True)
            self.btn_rescan.setEnabled(True)
            if isinstance(result, Exception):
                self._discovery = DeviceDiscoveryResult(
                    warnings=[f"Geräteerkennung fehlgeschlagen: {result}"]
                )
                self._apply_discovery(self._discovery)
                return
            if isinstance(result, DeviceDiscoveryResult):
                self._apply_discovery(result)

        def _to() -> None:
            self._discover_inflight = False
            self.btn_refresh.setEnabled(True)
            self.btn_rescan.setEnabled(True)
            if not (self._discovery.scanners or self._discovery.printers):
                self.device_status.setText(
                    DEVICE_TIMEOUT_DE.format(seconds=int(timeout))
                )

        self._discover_watch = watch_worker(
            self,
            discover_devices,
            timeout=timeout,
            on_done=_done,
            on_timeout=_to,
            on_error=lambda e: _done(e),
        )

    def _populate_device_combo(self) -> None:
        backend = self.current_backend()
        self._choices = scanner_choices(self._discovery.scanners, backend=backend)
        remembered = get_scan_last_device(backend)
        prefer = self._preferred_device_id or remembered
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        restore = 0
        for i, ch in enumerate(self._choices):
            self.device_combo.addItem(ch.label, ch.primary)
            ids = {ch.primary.device_id, ch.primary.name}
            for a in ch.alternates:
                ids.add(a.device_id)
                ids.add(a.name)
            if prefer and prefer in ids:
                restore = i
        if not self._choices:
            self.device_combo.addItem("Kein Scanner — ↻ oder Bilder importieren", None)
        self.device_combo.setCurrentIndex(restore)
        self.device_combo.blockSignals(False)
        self.btn_scan.setEnabled(bool(self._choices) or backend == "external")

    def _populate_device_list(self) -> None:
        filt = self.filter_combo.currentData() or "all"
        self.device_list.clear()
        devices: list[DeviceInfo] = []
        if filt in ("all", "scanner"):
            devices.extend(self._discovery.scanners)
        if filt in ("all", "printer"):
            devices.extend(self._discovery.printers)
        if filt == "network":
            devices = [
                d
                for d in (self._discovery.scanners + self._discovery.printers)
                if d.scope == DeviceScope.NETWORK
            ]
        if not devices:
            placeholder = QListWidgetItem(
                "Kein Gerät in diesem Filter — „↻“ oder „Bilder importieren…“"
            )
            placeholder.setFlags(Qt.ItemIsEnabled)
            placeholder.setData(Qt.UserRole, None)
            placeholder.setToolTip(WINDOWS_SCANNER_DRIVER_HINT_DE + "\n\n" + SCAN_START_HINT_DE)
            self.device_list.addItem(placeholder)
            return
        sel = self.selected_scanner()
        sel_id = (sel.device_id if sel else "") or ""
        current_row = 0
        for i, d in enumerate(devices):
            item = QListWidgetItem(d.label())
            item.setData(Qt.UserRole, d)
            item.setToolTip(d.details or d.device_id or d.name)
            self.device_list.addItem(item)
            if sel_id and d.device_id == sel_id:
                current_row = i
            elif not sel_id and d.kind == DeviceKind.SCANNER and current_row == 0 and i == 0:
                current_row = i
        if self.device_list.count():
            self.device_list.setCurrentRow(current_row)

    def _on_device_combo_changed(self, *_a) -> None:
        dev = self.selected_scanner()
        if dev is not None:
            try:
                set_scan_last_device(self.current_backend(), dev.device_id or dev.name)
            except Exception:
                pass

    def _on_list_item_changed(self, current, _prev) -> None:
        if current is None:
            return
        dev = current.data(Qt.UserRole)
        if not isinstance(dev, DeviceInfo) or dev.kind != DeviceKind.SCANNER:
            return
        for i in range(self.device_combo.count()):
            data = self.device_combo.itemData(i)
            if isinstance(data, DeviceInfo) and data.device_id == dev.device_id:
                self.device_combo.blockSignals(True)
                self.device_combo.setCurrentIndex(i)
                self.device_combo.blockSignals(False)
                return

    def _on_backend_changed(self, key: str) -> None:
        try:
            set_scan_backend(key)
        except Exception:
            pass
        self._populate_device_combo()
        label = BACKEND_LABELS_DE.get(key, key)
        self.device_status.setText(f"Backend: {label}")

    def _update_pending_label(self) -> None:
        n = len(self._pending_images)
        if n == 0:
            self.pending_label.setText("Keine Seiten in der Warteschlange.")
        else:
            names = ", ".join(p.name for p in self._pending_images[:5])
            more = f" … (+{n - 5})" if n > 5 else ""
            self.pending_label.setText(f"{n} Seite(n) bereit: {names}{more}")

    def _set_acquire_status(self, text: str) -> None:
        msg = (text or "").strip()
        self.device_status.setText(msg)
        self.device_status.setToolTip(msg)
        self.device_status.setAccessibleName(msg[:120] if msg else "Gerätestatus")

    def _set_io_busy(self, busy: bool) -> None:
        self._io_busy = bool(busy)
        enable = not busy
        self.btn_scan.setEnabled(enable and (bool(self._choices) or self.current_backend() == "external"))
        self.btn_refresh.setEnabled(enable)
        self.btn_rescan.setEnabled(enable)
        self.btn_acquire.setEnabled(enable)
        self.device_combo.setEnabled(enable)
        self.device_list.setEnabled(enable)
        try:
            self.backend_widget.setEnabled(enable)
        except Exception:
            pass

    def _acquire_timeout_s(self) -> float:
        override = io_timeout_s(DEVICE_IO_TIMEOUT_S)
        if os.environ.get("ILD_DEVICE_IO_TIMEOUT"):
            return override
        scanner = self.selected_scanner()
        be = (self.current_backend() or "").lower()
        cls = ""
        if scanner is not None:
            try:
                cls = classify_device_id(scanner.device_id, scanner.backend)
            except Exception:
                cls = ""
        if be == "wia" or cls == "wia":
            return DEVICE_IO_TIMEOUT_S
        return ACQUIRE_OK_TIMEOUT_S

    def _retry_scan_flow(self) -> None:
        self.refresh_devices()
        if self._auto_launch_scantuxio:
            self._launch_scantuxio_ui(force=True)

    def _scantuxio_alive(self) -> bool:
        proc = self._st_proc
        if proc is None:
            return False
        try:
            return proc.poll() is None
        except Exception:
            return False

    def _launch_scantuxio_ui(self, force: bool = False) -> None:
        if not _st_ui_available():
            self._set_acquire_status(
                "ScanTuxio-UI-Bridge nicht verfügbar.\n"
                "Bitte „Bilder importieren…“ (Erweitert) nutzen oder InstantLens Doc neu installieren."
            )
            return
        if self._scantuxio_alive() and not force:
            self._set_acquire_status(
                "ScanTuxio läuft bereits. Bitte dort speichern — neue Dateien werden übernommen."
            )
            self._st_timer.start()
            return
        inst = find_scantuxio_install()
        if inst is None:
            hint = (
                missing_scantuxio_hint_de()
                if callable(missing_scantuxio_hint_de)
                else "ScanTuxio nicht gefunden. Pfad unter Erweitert → ScanTuxio wählen."
            )
            self._set_acquire_status(hint)
            return
        try:
            handshake = prepare_handshake_dir()
            launch = build_launch(inst, handshake)
            self._st_handshake = handshake
            self._st_watch = default_watch_dirs(inst, handshake)
            self._st_snapshot = snapshot_scan_files(self._st_watch)
            self._st_proc = launch_scantuxio_process(launch)
        except Exception as e:
            hint = (
                missing_scantuxio_hint_de()
                if callable(missing_scantuxio_hint_de)
                else "ScanTuxio starten fehlgeschlagen."
            )
            self._set_acquire_status(f"ScanTuxio konnte nicht gestartet werden: {e}\n\n{hint}")
            return
        self._set_acquire_status(
            f"ScanTuxio geöffnet ({inst.root}).\n"
            f"Scan dort speichern — InstantLens Doc übernimmt neue Dateien.\n"
            f"Übergabeordner: {handshake}"
        )
        self._st_timer.start()

    def _poll_scantuxio_output(self) -> None:
        if not self._st_watch or not callable(collect_new_scan_files):
            return
        found = self._collect_scantuxio_output(quiet=True)
        if found:
            if self._pending_images:
                self._insert_into_document(quiet=True)
            return
        if self._st_proc is not None:
            try:
                rc = self._st_proc.poll()
            except Exception:
                rc = 0
            if rc is not None:
                self._st_timer.stop()
                self._collect_scantuxio_output(quiet=False)

    def _collect_scantuxio_output(self, quiet: bool = False) -> bool:
        if not callable(collect_new_scan_files) or not callable(snapshot_scan_files):
            if not quiet:
                self._set_acquire_status("ScanTuxio-Übergabe nicht verfügbar — bitte Bilder importieren.")
            return False
        handshake = self._st_handshake
        roots = list(self._st_watch or [])
        if handshake and handshake not in roots:
            roots.append(handshake)
        if not roots:
            if not quiet:
                self._set_acquire_status(
                    "Kein ScanTuxio-Übergabeordner. Bitte ScanTuxio öffnen oder Bilder importieren."
                )
            return False
        snap = self._st_snapshot or {}
        paths = list(
            read_handoff_manifest(handshake) if handshake and callable(read_handoff_manifest) else []
        )
        paths.extend(collect_new_scan_files(roots, snap))
        seen: set[str] = set()
        uniq: list[Path] = []
        for p in paths:
            try:
                key = str(p.resolve())
            except OSError:
                key = str(p)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(p)
        if not uniq:
            if not quiet:
                self._set_acquire_status(
                    "Noch kein neues Scan-Dokument gefunden.\n"
                    "In ScanTuxio als PDF/Bild speichern.\n"
                    "Ohne ScanTuxio: Erweitert → „Bilder importieren…“."
                )
            return False
        expanded = expand_scan_import_paths(uniq)
        if not expanded:
            expanded = import_image_paths(uniq)
        if not expanded:
            if not quiet:
                self._set_acquire_status(
                    "ScanTuxio-Datei gefunden, aber nicht als Bild/PDF lesbar. Bitte Bilder importieren."
                )
            return False
        self._pending_images.extend(expanded)
        self._update_pending_label()
        self._st_snapshot = snapshot_scan_files(roots)
        self._set_acquire_status(
            f"{len(expanded)} Scan-Seite(n) übernommen. „In Dokument einfügen“ oder weiter scannen."
        )
        return True

    def _scan_kwargs(self) -> dict:
        return {
            "dpi": int(self.dpi_combo.currentData() or 300),
            "color_mode": str(self.color_combo.currentData() or "Color"),
            "source": str(self.source_combo.currentData() or "Flatbed"),
            "backend": self.current_backend(),
            "fallback_devices": self.selected_choice_alternates(),
        }

    def _acquire_scan(self) -> bool:
        """Startet Acquire asynchron. Rückgabe immer False (Ergebnis kommt im Callback)."""
        self._start_acquire(insert=False)
        return False

    def _do_scan_and_insert(self) -> None:
        self._start_acquire(insert=True)

    def _start_acquire(self, *, insert: bool) -> None:
        if self._io_busy:
            return
        if self.current_backend() == BACKEND_SCANTUXIO:
            self._launch_scantuxio_ui()
            return
        scanner = self.selected_scanner()
        if scanner is None and self._discovery.scanners and self.current_backend() != "external":
            self._set_acquire_status("Bitte einen Scanner im Dropdown auswählen.")
            return
        if scanner is None and not self._discovery.scanners and self.current_backend() != "external":
            st_hint = (
                missing_scantuxio_hint_de()
                if callable(missing_scantuxio_hint_de)
                else "Optional: ScanTuxio unter D:\\AI_Temp\\ScanTuxio Win installieren."
            )
            self._set_acquire_status(
                "Kein Scanner erkannt.\n\n" + WINDOWS_SCANNER_DRIVER_HINT_DE + "\n\n" + st_hint
            )
            return
        self._save_scan_prefs()
        self._insert_after_acquire = bool(insert)
        timeout = self._acquire_timeout_s()
        kwargs = self._scan_kwargs()
        self._set_io_busy(True)
        self._set_acquire_status("Scanne… die Oberfläche bleibt bedienbar. Abbrechen schließt den Dialog.")

        def _work():
            return acquire_from_scanner(scanner, **kwargs)

        def _done(paths) -> None:
            self._set_io_busy(False)
            if isinstance(paths, Exception):
                self._set_acquire_status(
                    f"{paths}\n\nDie App bleibt stabil — bitte ScanTuxio öffnen oder Bilder importieren.\n\n"
                    + WINDOWS_SCAN_DEPS_HINT
                )
                return
            self._finish_acquire(list(paths or []))

        def _to() -> None:
            self._set_io_busy(False)
            seconds = max(1, int(round(timeout)))
            msg = DEVICE_TIMEOUT_DE.format(seconds=seconds)
            self._set_acquire_status(msg)
            scan_log(f"UI: Timeout {seconds}s — {msg}")

        self._acquire_watch = watch_worker(
            self,
            _work,
            timeout=timeout,
            on_done=_done,
            on_timeout=_to,
            on_error=lambda e: _done(e),
        )

    def _finish_acquire(self, paths: list) -> None:
        if not paths:
            detail = last_acquire_error()
            res = last_acquire_result()
            if res is not None and getattr(res, "cancelled", False):
                self._set_acquire_status("Scan abgebrochen.")
                return
            if "ausgelastet" in (detail or "").lower() or "busy" in (detail or "").lower():
                body = (
                    wia_busy_user_hint_de(detail)
                    if callable(wia_busy_user_hint_de)
                    else (
                        "WIA-Gerät ausgelastet. Bitte ScanTuxio / Windows Fax und Scan schließen.\n"
                        + (detail or "")
                    )
                )
            else:
                body = detail or "Kein Bild vom Scanner erhalten."
                if "Log:" not in body:
                    body += f"\n\nLog: {scan_log_path()}"
            self._set_acquire_status(body)
            scan_log(f"UI: kein Bild — {body[:400]}")
            return
        self._pending_images.extend(paths)
        self._update_pending_label()
        self._set_acquire_status(f"{len(paths)} Seite(n) gescannt.")
        if self._insert_after_acquire:
            self._insert_into_document()

    def _import_images(self) -> None:
        from instantlensdoc.core.app_settings import dialog_start_dir, remember_recent_dir

        start = None
        if getattr(self.pdf_view, "pdf_path", None):
            start = self.pdf_view.pdf_path.parent
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Seitenbilder importieren",
            dialog_start_dir(start),
            "Bilder (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp)",
        )
        if not paths:
            return
        remember_recent_dir(paths[0])
        imported = import_image_paths(paths)
        if not imported:
            QMessageBox.warning(self, "Import", "Keine gültigen Bilddateien.")
            return
        self._pending_images.extend(imported)
        self._update_pending_label()

    def _ensure_pdf_target(self, *, ask: bool = True) -> Path | None:
        if getattr(self.pdf_view, "pdf_path", None):
            return Path(self.pdf_view.pdf_path)
        cfg = get_scan_settings()
        out = str(cfg.get("scan_output_dir") or "").strip()
        if out:
            d = Path(out)
            try:
                d.mkdir(parents=True, exist_ok=True)
                return d / "scan.pdf"
            except OSError:
                pass
        if not ask:
            from instantlensdoc.core.app_settings import dialog_start_dir

            return Path(dialog_start_dir()) / "scan.pdf"
        from instantlensdoc.core.app_settings import dialog_start_dir, remember_recent_dir

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Neues Scan-PDF speichern",
            str(Path(dialog_start_dir()) / "scan.pdf"),
            "PDF (*.pdf)",
        )
        if not path:
            return None
        remember_recent_dir(path)
        return Path(path)

    def _insert_into_document(self, quiet: bool = False) -> None:
        if not self._pending_images:
            if not quiet:
                QMessageBox.information(
                    self,
                    "Scannen",
                    "Bitte zuerst scannen oder Bilder importieren.",
                )
            return
        target = self._ensure_pdf_target(ask=not quiet)
        if target is None:
            return
        lang = self.lang_combo.currentData() or "deu+eng"
        do_ocr = bool(self.ocr_enabled.isChecked())
        write_hocr = bool(self.layout_hocr.isChecked())
        write_tsv = bool(self.layout_tsv.isChecked())
        at_index = None
        if getattr(self.pdf_view, "pdf_path", None) and target.resolve() == Path(
            self.pdf_view.pdf_path
        ).resolve():
            try:
                at_index = int(self.pdf_view.page_index) + 1
            except Exception:
                at_index = None

        prog = QProgressDialog(
            "Seiten werden eingefügt…", "Abbrechen", 0, len(self._pending_images), self
        )
        prog.setWindowTitle("Scannen")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)

        def _progress(i, total, label):
            if prog.wasCanceled():
                return
            prog.setMaximum(total)
            prog.setValue(i)
            prog.setLabelText(f"{i}/{total}: {Path(label).name}")

        try:
            result = insert_scan_pages_into_pdf(
                target,
                list(self._pending_images),
                at_index=at_index,
                ocr=do_ocr,
                lang=str(lang),
                ocr_mode=OcrOutputMode.LAYOUT_PRESERVE,
                write_hocr=write_hocr,
                write_tsv=write_tsv,
                on_progress=_progress,
            )
        except Exception as e:
            prog.close()
            if not quiet:
                QMessageBox.warning(self, "Scannen", str(e))
            return
        prog.close()
        self._pending_images.clear()
        self._update_pending_label()

        try:
            if getattr(self.pdf_view, "pdf_path", None) and Path(
                self.pdf_view.pdf_path
            ).resolve() == target.resolve():
                from ild_pdf import PdfDocument
                from ild_pdf.render import clear_render_cache

                clear_render_cache(target)
                with PdfDocument(target, password=self.pdf_view.password) as doc:
                    self.pdf_view.page_count = len(doc)
                    if hasattr(self.pdf_view, "_reload_page_labels"):
                        self.pdf_view._reload_page_labels()
                if result.pages and result.pages[0].page_index is not None:
                    self.pdf_view.page_index = result.pages[0].page_index
                self.pdf_view.refresh()
                if hasattr(self.pdf_view, "document_changed"):
                    self.pdf_view.document_changed.emit()
                self.pdf_view.status.emit(
                    f"Scan: {result.ok_count} Seite(n)"
                    + (" · OCR" if result.ocr_enabled else "")
                )
            else:
                mw = self.parent()
                if mw is not None and hasattr(mw, "open_path"):
                    mw.open_path(str(target))
        except Exception as e:
            if not quiet:
                QMessageBox.warning(self, "Scannen", f"Seiten geschrieben, Viewer-Refresh: {e}")

        if result.combined_text:
            mw = self.parent()
            use_ws = bool(getattr(self, "open_in_word_suite", lambda: True)())
            imported = False
            if use_ws:
                present = getattr(mw, "open_ocr_result", None) if mw is not None else None
                if callable(present):
                    try:
                        imported = bool(
                            present(
                                scan=result,
                                title=f"Word-Suite — Scan {target.stem}",
                                auto_format=True,
                            )
                        )
                    except Exception:
                        imported = False
                if not imported:
                    ws_fn = getattr(mw, "_handoff_ocr_to_word_suite", None) if mw is not None else None
                    if callable(ws_fn):
                        try:
                            imported = bool(
                                ws_fn(
                                    scan=result,
                                    text=result.combined_text,
                                    title=f"Word-Suite — Scan {target.stem}",
                                    auto_format=True,
                                    source_path=str(target),
                                )
                            )
                        except Exception:
                            imported = False
            if not imported:
                show_fn = getattr(mw, "_show_scan_ocr_text", None) if mw is not None else None
                if callable(show_fn):
                    try:
                        show_fn(result.combined_text, f"Scan-OCR — {target.stem}")
                    except Exception:
                        pass

        self._last_result = result
        msg = f"{result.ok_count} Seite(n) eingefügt in\n{target}"
        if result.warnings:
            msg += "\n\nHinweise:\n" + "\n".join(result.warnings[:3])
        self._set_acquire_status(msg.replace("\n", " — "))
        if not quiet:
            QMessageBox.information(self, "Scannen", msg)
            self.accept()
