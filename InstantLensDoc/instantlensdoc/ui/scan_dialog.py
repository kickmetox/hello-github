"""Scan/Import-Dialog + Geräteauswahl (Drucker/Scanner) — 2.6.2 / 2.6.41 / 2.6.46."""

from __future__ import annotations

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
    QPushButton,
    QVBoxLayout,
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
)

# ScanTuxio-UI lazy: Dialog bleibt nutzbar wenn UI-Bridge fehlt — 2.6.51
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
except Exception:  # pragma: no cover - Defensiv ohne ScanTuxio-UI
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
    """
    Scannen oder Bilder importieren → Seiten in die aktuelle PDF-Session;
    optional Tesseract-OCR; Geräte-Picker mit Aktualisieren/Neu suchen.
    """

    def __init__(self, pdf_view, parent=None, *, auto_launch_scantuxio: bool = True):
        super().__init__(parent)
        self.pdf_view = pdf_view
        self._discovery = DeviceDiscoveryResult()
        self._pending_images: list[Path] = []
        self._auto_launch_scantuxio = bool(auto_launch_scantuxio)
        self._st_proc = None
        self._st_handshake: Path | None = None
        self._st_watch: list[Path] = []
        self._st_snapshot: dict[str, tuple[int, int]] = {}
        self.setWindowTitle("Scannen / Import")
        self.setWindowModality(Qt.WindowModal)
        self.setObjectName("scanDialog")
        self.resize(560, 680)
        self.setAccessibleName("Scannen und Import")
        self.setAccessibleDescription(
            "ScanTuxio-UI starten und Scan übernehmen, oder Bilder importieren — 2.6.46"
        )

        layout = QVBoxLayout(self)
        self.hint = QLabel(
            "Scanner wählen und scannen, oder Seitenbilder importieren. "
            "OCR mit Layout-Erhalt (Blöcke / Lesereihenfolge; optional hOCR/TSV).\n"
            f"{SCAN_START_HINT_DE} — 2.6.46"
        )
        self.hint.setWordWrap(True)
        self.hint.setObjectName("scanDialogHint")
        layout.addWidget(self.hint)

        self.entry_banner = QLabel(
            "<b>Einstieg:</b> Menü <b>Geräte → Scanner / Scannen…</b> · "
            "PDF → Scannen / Import… · Toolbar <b>Scan…</b> · "
            "Ctrl+Alt+Shift+I"
        )
        self.entry_banner.setWordWrap(True)
        self.entry_banner.setObjectName("scanEntryBanner")
        self.entry_banner.setStyleSheet(
            "background:#eef5ff; color:#1a3a5c; padding:8px; border-radius:4px;"
        )
        layout.addWidget(self.entry_banner)

        # --- Geräte ---
        dev_box = QGroupBox("Geräte (Drucker & Scanner)")
        dev_box.setObjectName("scanDevicesGroup")
        dev_layout = QVBoxLayout(dev_box)
        self.device_list = QListWidget()
        self.device_list.setObjectName("scanDeviceList")
        self.device_list.setAlternatingRowColors(True)
        self.device_list.setAccessibleName("Geräteliste")
        self.device_list.setAccessibleDescription(
            "Lokale und Netzwerk-Drucker/Scanner; Auswahl für Scan"
        )
        dev_layout.addWidget(self.device_list)

        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.setObjectName("scanDeviceRefresh")
        self.btn_refresh.setToolTip("Geräteliste neu laden")
        self.btn_refresh.clicked.connect(self.refresh_devices)
        self.btn_rescan = QPushButton("Neu suchen")
        self.btn_rescan.setObjectName("scanDeviceRescan")
        self.btn_rescan.setToolTip("Vollständige Neu-Erkennung (lokal + Netzwerk)")
        self.btn_rescan.clicked.connect(self.refresh_devices)
        self.btn_retry = QPushButton("Erneut versuchen")
        self.btn_retry.setObjectName("scanDeviceRetry")
        self.btn_retry.setToolTip(
            "Geräteliste neu laden und ScanTuxio erneut öffnen — 2.6.46"
        )
        self.btn_retry.clicked.connect(self._retry_scan_flow)
        self.filter_combo = QComboBox()
        self.filter_combo.setObjectName("scanDeviceFilter")
        self.filter_combo.addItem("Alle Geräte", "all")
        self.filter_combo.addItem("Nur Scanner", "scanner")
        self.filter_combo.addItem("Nur Drucker", "printer")
        self.filter_combo.addItem("Nur Netzwerk", "network")
        self.filter_combo.currentIndexChanged.connect(self._populate_device_list)
        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_rescan)
        btn_row.addWidget(self.btn_retry)
        btn_row.addWidget(self.filter_combo, 1)
        dev_layout.addLayout(btn_row)

        self.device_status = QLabel("")
        self.device_status.setObjectName("scanDeviceStatus")
        self.device_status.setWordWrap(True)
        dev_layout.addWidget(self.device_status)
        layout.addWidget(dev_box)

        # --- Aktionen ---
        act_box = QGroupBox("Erfassen")
        act_layout = QVBoxLayout(act_box)
        act_btns = QHBoxLayout()
        self.btn_scantuxio = QPushButton("ScanTuxio öffnen")
        self.btn_scantuxio.setObjectName("scanScantuxioBtn")
        self.btn_scantuxio.setToolTip(
            "ScanTuxio-Hauptfenster starten (D:\\AI_Temp\\ScanTuxio Win) — 2.6.46"
        )
        self.btn_scantuxio.clicked.connect(self._launch_scantuxio_ui)
        self.btn_take_scan = QPushButton("Scan übernehmen")
        self.btn_take_scan.setObjectName("scanTakeBtn")
        self.btn_take_scan.setToolTip(
            "Neue PDF/Bilder aus ScanTuxio-Übergabeordner übernehmen — 2.6.46"
        )
        self.btn_take_scan.clicked.connect(self._collect_scantuxio_output)
        self.btn_acquire = QPushButton("WIA / NAPS2…")
        self.btn_acquire.setObjectName("scanAcquireBtn")
        self.btn_acquire.setToolTip(
            "Sekundär: WIA/NAPS2/eSCL ohne ScanTuxio-UI — 2.6.46"
        )
        self.btn_acquire.clicked.connect(self._acquire_scan)
        self.btn_import = QPushButton("Bilder importieren…")
        self.btn_import.setObjectName("scanImportBtn")
        self.btn_import.setToolTip("PNG/JPEG/TIFF/BMP als Seiten importieren")
        self.btn_import.clicked.connect(self._import_images)
        act_btns.addWidget(self.btn_scantuxio)
        act_btns.addWidget(self.btn_take_scan)
        act_btns.addWidget(self.btn_acquire)
        act_btns.addWidget(self.btn_import)
        act_layout.addLayout(act_btns)

        self.pending_label = QLabel("Keine Seiten in der Warteschlange.")
        self.pending_label.setObjectName("scanPendingLabel")
        self.pending_label.setWordWrap(True)
        act_layout.addWidget(self.pending_label)
        layout.addWidget(act_box)

        # --- OCR ---
        ocr_form = QFormLayout()
        self.ocr_enabled = QCheckBox("OCR mit Tesseract (Layout-Erhalt)")
        self.ocr_enabled.setObjectName("scanOcrEnabled")
        self.ocr_enabled.setChecked(True)
        self.ocr_enabled.setToolTip(
            "Durchsuchbarer/editierbarer Text mit Blöcken und Lesereihenfolge — 2.6.5"
        )
        ok_tess, tess_msg = tesseract_available()
        self.ocr_enabled.setEnabled(ok_tess)
        if not ok_tess:
            self.ocr_enabled.setChecked(False)
            self.ocr_enabled.setToolTip(tess_msg)
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("scanOcrLang")
        for label, code in LANG_PRESETS.items():
            self.lang_combo.addItem(label, code)
        # Default deu+eng
        idx = self.lang_combo.findData("deu+eng")
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.layout_hocr = QCheckBox("hOCR Sidecar")
        self.layout_hocr.setObjectName("scanOcrHocr")
        self.layout_hocr.setChecked(True)
        self.layout_hocr.setToolTip("*.ildocr.hocr mit Bounding-Boxes — 2.6.5")
        self.layout_tsv = QCheckBox("TSV Sidecar")
        self.layout_tsv.setObjectName("scanOcrTsv")
        self.layout_tsv.setChecked(True)
        self.layout_tsv.setToolTip("*.ildocr.tsv (Wörter + Koordinaten) — 2.6.5")
        self.word_suite_check = QCheckBox("In Word-Suite öffnen/übernehmen")
        self.word_suite_check.setObjectName("scanOcrWordSuite")
        self.word_suite_check.setChecked(True)
        self.word_suite_check.setToolTip(
            "OCR-Text als editierbares Word-Suite-Dokument (Absätze/Lesereihenfolge) — 2.6.15"
        )
        self.ocr_enabled.toggled.connect(self._sync_scan_ocr_opts)
        ocr_form.addRow(self.ocr_enabled)
        ocr_form.addRow("OCR-Sprache:", self.lang_combo)
        ocr_form.addRow(self.layout_hocr)
        ocr_form.addRow(self.layout_tsv)
        ocr_form.addRow(self.word_suite_check)
        layout.addLayout(ocr_form)
        self._sync_scan_ocr_opts()

        self.tess_hint = QLabel(
            tess_msg if ok_tess else INSTALL_HINT_DE.split("\n\n")[0]
            + "\n\n" + WINDOWS_SCAN_DEPS_HINT
        )
        self.tess_hint.setObjectName("scanTessHint")
        self.tess_hint.setWordWrap(True)
        self.tess_hint.setStyleSheet("color: #555;")
        layout.addWidget(self.tess_hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText("In Dokument einfügen")
        buttons.button(QDialogButtonBox.Ok).setObjectName("scanInsertOk")
        buttons.accepted.connect(self._insert_into_document)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._st_timer = QTimer(self)
        self._st_timer.setInterval(1200)
        self._st_timer.timeout.connect(self._poll_scantuxio_output)
        self.refresh_devices()
        if self._auto_launch_scantuxio:
            QTimer.singleShot(0, self._launch_scantuxio_ui)

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
        super().closeEvent(event)

    def open_in_word_suite(self) -> bool:
        """OCR-Text in Word-Suite übernehmen — 2.6.15."""
        return bool(getattr(self, "word_suite_check", None) and self.word_suite_check.isChecked())

    def selected_scanner(self) -> DeviceInfo | None:
        item = self.device_list.currentItem()
        if not item:
            return None
        dev = item.data(Qt.UserRole)
        if isinstance(dev, DeviceInfo) and dev.kind == DeviceKind.SCANNER:
            return dev
        return None

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
        self.device_status.setText("Suche Geräte…")
        self.btn_refresh.setEnabled(False)
        self.btn_rescan.setEnabled(False)
        try:
            try:
                from PySide6.QtWidgets import QApplication

                app = QApplication.instance()
                if app is not None:
                    app.processEvents()
            except Exception:
                pass
            self._discovery = discover_devices()
        except Exception as e:
            self._discovery = DeviceDiscoveryResult(
                warnings=[f"Geräteerkennung fehlgeschlagen: {e}"]
            )
        finally:
            self.btn_refresh.setEnabled(True)
            self.btn_rescan.setEnabled(True)
        self._populate_device_list()
        msg = format_discovery_status(self._discovery)
        self.device_status.setText(msg)
        self.device_status.setAccessibleName(msg)
        self.device_status.setToolTip(
            "\n".join(self._discovery.warnings[:6])
            if self._discovery.warnings
            else msg
        )
        # Leere Liste: klare DE-Hinweise (Treiber) ohne Crash
        if not self._discovery.printers and not self._discovery.scanners:
            tip = WINDOWS_SCAN_DEPS_HINT + "\n\n" + SCAN_START_HINT_DE
            tip = WINDOWS_PRINTER_DRIVER_HINT_DE + "\n\n" + tip
            tip = WINDOWS_SCANNER_DRIVER_HINT_DE + "\n\n" + tip
            self.device_status.setToolTip(tip)
            if not (self.device_status.text() or "").strip():
                self.device_status.setText(NO_DEVICE_STATUS_DE)

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
                "Kein Gerät in diesem Filter — „Aktualisieren“ oder "
                "„Bilder importieren…“ · Menü Geräte → Scanner / Scannen…"
            )
            placeholder.setFlags(Qt.ItemIsEnabled)  # nicht wählbar als Scan-Ziel
            placeholder.setData(Qt.UserRole, None)
            placeholder.setToolTip(
                WINDOWS_SCANNER_DRIVER_HINT_DE + "\n\n" + SCAN_START_HINT_DE
            )
            self.device_list.addItem(placeholder)
            return
        for d in devices:
            item = QListWidgetItem(d.label())
            item.setData(Qt.UserRole, d)
            tip = d.details or d.device_id or d.name
            item.setToolTip(tip)
            self.device_list.addItem(item)
        if self.device_list.count() and not self.device_list.currentItem():
            # Ersten Scanner bevorzugen
            for i in range(self.device_list.count()):
                dev = self.device_list.item(i).data(Qt.UserRole)
                if isinstance(dev, DeviceInfo) and dev.kind == DeviceKind.SCANNER:
                    self.device_list.setCurrentRow(i)
                    break
            else:
                self.device_list.setCurrentRow(0)

    def _update_pending_label(self) -> None:
        n = len(self._pending_images)
        if n == 0:
            self.pending_label.setText("Keine Seiten in der Warteschlange.")
        else:
            names = ", ".join(p.name for p in self._pending_images[:5])
            more = f" … (+{n - 5})" if n > 5 else ""
            self.pending_label.setText(f"{n} Seite(n) bereit: {names}{more}")

    def _set_acquire_status(self, text: str) -> None:
        """Fehler/Hinweise in der Geräteliste, ohne Extra-Modal — 2.6.46."""
        msg = (text or "").strip()
        self.device_status.setText(msg)
        self.device_status.setToolTip(msg)
        self.device_status.setAccessibleName(msg[:120] if msg else "Gerätestatus")

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
                "Bitte „Bilder importieren…“ nutzen oder InstantLens Doc neu installieren (2.6.51)."
            )
            return
        if self._scantuxio_alive() and not force:
            self._set_acquire_status(
                "ScanTuxio läuft bereits. Bitte dort speichern, dann „Scan übernehmen“. "
                "Oder „Erneut versuchen“."
            )
            self._st_timer.start()
            return
        inst = find_scantuxio_install()
        if inst is None:
            hint = (
                missing_scantuxio_hint_de()
                if callable(missing_scantuxio_hint_de)
                else "ScanTuxio nicht gefunden. Bilder importieren…"
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
            self._set_acquire_status(
                f"ScanTuxio konnte nicht gestartet werden: {e}\n\n" + hint
            )
            return
        self._set_acquire_status(
            f"ScanTuxio geöffnet ({inst.root}).\n"
            f"Scan dort speichern, dann „Scan übernehmen“.\n"
            f"Übergabeordner: {handshake}"
        )
        self._st_timer.start()

    def _poll_scantuxio_output(self) -> None:
        if not self._st_watch or not callable(collect_new_scan_files):
            return
        found = self._collect_scantuxio_output(quiet=True)
        if found:
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
                self._set_acquire_status(
                    "ScanTuxio-Übergabe nicht verfügbar — bitte Bilder importieren."
                )
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
        paths = list(read_handoff_manifest(handshake) if handshake and callable(read_handoff_manifest) else [])
        paths.extend(collect_new_scan_files(roots, snap))
        # dedupe
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
                    "In ScanTuxio als PDF/Bild speichern, dann „Scan übernehmen“.\n"
                    "Ohne ScanTuxio: „Bilder importieren…“."
                )
            return False
        expanded = expand_scan_import_paths(uniq)
        if not expanded:
            expanded = import_image_paths(uniq)
        if not expanded:
            if not quiet:
                self._set_acquire_status(
                    "ScanTuxio-Datei gefunden, aber nicht als Bild/PDF lesbar. "
                    "Bitte Bilder importieren."
                )
            return False
        self._pending_images.extend(expanded)
        self._update_pending_label()
        self._st_snapshot = snapshot_scan_files(roots)
        self._set_acquire_status(
            f"{len(expanded)} Scan-Seite(n) übernommen. "
            "„In Dokument einfügen“ oder weiter scannen."
        )
        return True

    def _acquire_scan(self) -> None:
        scanner = self.selected_scanner()
        if scanner is None and self._discovery.scanners:
            self._set_acquire_status(
                "Bitte einen Scanner in der Liste auswählen "
                "(oder ScanTuxio öffnen / Bilder importieren)."
            )
            return
        if scanner is None and not self._discovery.scanners:
            st_hint = (
                missing_scantuxio_hint_de()
                if callable(missing_scantuxio_hint_de)
                else "Optional: ScanTuxio unter D:\\AI_Temp\\ScanTuxio Win installieren."
            )
            self._set_acquire_status(
                "Kein Scanner erkannt.\n\n"
                + WINDOWS_SCANNER_DRIVER_HINT_DE
                + "\n\n"
                + st_hint
            )
            return
        try:
            paths = acquire_from_scanner(scanner)
        except Exception as e:
            self._set_acquire_status(
                f"{e}\n\nDie App bleibt stabil — bitte ScanTuxio öffnen "
                "oder Bilder importieren.\n\n" + WINDOWS_SCAN_DEPS_HINT
            )
            return
        if not paths:
            detail = last_acquire_error()
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
                body = "Kein Bild vom Scanner erhalten.\n\n"
                if detail:
                    body += f"Detail: {detail}\n\n"
                body += (
                    "Primär: ScanTuxio-Hauptfenster („ScanTuxio öffnen“).\n"
                    "Ohne Gerät: „Bilder importieren…“.\n\n"
                    + WINDOWS_SCAN_DEPS_HINT
                )
            self._set_acquire_status(body)
            return
        self._pending_images.extend(paths)
        self._update_pending_label()

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

    def _ensure_pdf_target(self) -> Path | None:
        if getattr(self.pdf_view, "pdf_path", None):
            return Path(self.pdf_view.pdf_path)
        # Neues PDF anlegen
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

    def _insert_into_document(self) -> None:
        if not self._pending_images:
            QMessageBox.information(
                self,
                "Scannen / Import",
                "Bitte zuerst scannen oder Bilder importieren.",
            )
            return
        target = self._ensure_pdf_target()
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
            # Nach aktueller Seite einfügen
            try:
                at_index = int(self.pdf_view.page_index) + 1
            except Exception:
                at_index = None

        from PySide6.QtWidgets import QProgressDialog

        prog = QProgressDialog(
            "Seiten werden eingefügt…", "Abbrechen", 0, len(self._pending_images), self
        )
        prog.setWindowTitle("Scan / Import")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        cancelled = {"v": False}

        def _progress(i, total, label):
            if prog.wasCanceled():
                cancelled["v"] = True
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
            QMessageBox.warning(self, "Scan / Import", str(e))
            return
        prog.close()

        # Viewer aktualisieren
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
                    f"Scan/Import: {result.ok_count} Seite(n)"
                    + (" · OCR" if result.ocr_enabled else "")
                )
            else:
                mw = self.parent()
                if mw is not None and hasattr(mw, "open_path"):
                    mw.open_path(str(target))
        except Exception as e:
            QMessageBox.warning(
                self,
                "Scan / Import",
                f"Seiten geschrieben, Viewer-Refresh: {e}",
            )

        msg = f"{result.ok_count} Seite(n) eingefügt in\n{target}"
        if result.warnings:
            msg += "\n\nHinweise:\n" + "\n".join(result.warnings[:3])
        if result.combined_text and hasattr(self.parent(), "_open_text_result"):
            pass
        # OCR-Text → Word-Suite (Default) oder Editor — 2.6.15
        if result.combined_text:
            mw = self.parent()
            use_ws = bool(getattr(self, "open_in_word_suite", lambda: True)())
            if use_ws:
                ws_fn = getattr(mw, "_handoff_ocr_to_word_suite", None) if mw is not None else None
                if callable(ws_fn):
                    try:
                        ws_fn(
                            text=result.combined_text,
                            title=f"Word-Suite — Scan {target.stem}",
                            auto_format=True,
                        )
                    except Exception:
                        show_fn = getattr(mw, "_show_scan_ocr_text", None)
                        if callable(show_fn):
                            show_fn(result.combined_text, f"Scan-OCR — {target.stem}")
                else:
                    show_fn = getattr(mw, "_show_scan_ocr_text", None) if mw is not None else None
                    if callable(show_fn):
                        try:
                            show_fn(result.combined_text, f"Scan-OCR — {target.stem}")
                        except Exception:
                            pass
            else:
                show_fn = getattr(mw, "_show_scan_ocr_text", None) if mw is not None else None
                if callable(show_fn):
                    try:
                        show_fn(result.combined_text, f"Scan-OCR — {target.stem}")
                    except Exception:
                        pass

        self._last_result = result
        QMessageBox.information(self, "Scan / Import", msg)
        self.accept()
