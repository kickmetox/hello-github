"""Scan/Import-Dialog + Geräteauswahl (Drucker/Scanner) — 2.6.2 / Layout-OCR 2.6.3."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
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
    WINDOWS_SCAN_DEPS_HINT,
    DeviceDiscoveryResult,
    DeviceInfo,
    DeviceKind,
    DeviceScope,
    discover_devices,
)
from instantlensdoc.core.ocr import (
    INSTALL_HINT_DE,
    LANG_PRESETS,
    OcrOutputMode,
    tesseract_available,
)
from instantlensdoc.core.scan import (
    acquire_from_scanner,
    import_image_paths,
    insert_scan_pages_into_pdf,
)


class ScanDialog(QDialog):
    """
    Scannen oder Bilder importieren → Seiten in die aktuelle PDF-Session;
    optional Tesseract-OCR; Geräte-Picker mit Aktualisieren/Neu suchen.
    """

    def __init__(self, pdf_view, parent=None):
        super().__init__(parent)
        self.pdf_view = pdf_view
        self._discovery = DeviceDiscoveryResult()
        self._pending_images: list[Path] = []
        self.setWindowTitle("Scannen / Import")
        self.setWindowModality(Qt.WindowModal)
        self.setObjectName("scanDialog")
        self.resize(560, 640)
        self.setAccessibleName("Scannen und Import")
        self.setAccessibleDescription(
            "Scanner wählen oder Bilder importieren, optional OCR mit Layout-Erhalt — 2.6.4"
        )

        layout = QVBoxLayout(self)
        self.hint = QLabel(
            "Scanner wählen und scannen, oder Seitenbilder importieren. "
            "OCR mit Layout-Erhalt (Blöcke / Lesereihenfolge; optional hOCR/TSV). — 2.6.4"
        )
        self.hint.setWordWrap(True)
        self.hint.setObjectName("scanDialogHint")
        layout.addWidget(self.hint)

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
        self.filter_combo = QComboBox()
        self.filter_combo.setObjectName("scanDeviceFilter")
        self.filter_combo.addItem("Alle Geräte", "all")
        self.filter_combo.addItem("Nur Scanner", "scanner")
        self.filter_combo.addItem("Nur Drucker", "printer")
        self.filter_combo.addItem("Nur Netzwerk", "network")
        self.filter_combo.currentIndexChanged.connect(self._populate_device_list)
        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_rescan)
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
        self.btn_acquire = QPushButton("Vom Scanner…")
        self.btn_acquire.setObjectName("scanAcquireBtn")
        self.btn_acquire.setToolTip("Seite vom ausgewählten Scanner erfassen (WIA/SANE)")
        self.btn_acquire.clicked.connect(self._acquire_scan)
        self.btn_import = QPushButton("Bilder importieren…")
        self.btn_import.setObjectName("scanImportBtn")
        self.btn_import.setToolTip("PNG/JPEG/TIFF/BMP als Seiten importieren")
        self.btn_import.clicked.connect(self._import_images)
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
            "Durchsuchbarer/editierbarer Text mit Blöcken und Lesereihenfolge — 2.6.4"
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
        self.layout_hocr.setToolTip("*.ildocr.hocr mit Bounding-Boxes — 2.6.4")
        self.layout_tsv = QCheckBox("TSV Sidecar")
        self.layout_tsv.setObjectName("scanOcrTsv")
        self.layout_tsv.setChecked(True)
        self.layout_tsv.setToolTip("*.ildocr.tsv (Wörter + Koordinaten) — 2.6.4")
        self.ocr_enabled.toggled.connect(self._sync_scan_ocr_opts)
        ocr_form.addRow(self.ocr_enabled)
        ocr_form.addRow("OCR-Sprache:", self.lang_combo)
        ocr_form.addRow(self.layout_hocr)
        ocr_form.addRow(self.layout_tsv)
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

        self.refresh_devices()

    def _sync_scan_ocr_opts(self, *_args) -> None:
        on = bool(self.ocr_enabled.isChecked()) and self.ocr_enabled.isEnabled()
        self.lang_combo.setEnabled(on)
        self.layout_hocr.setEnabled(on)
        self.layout_tsv.setEnabled(on)

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
            self._discovery = discover_devices()
        finally:
            self.btn_refresh.setEnabled(True)
            self.btn_rescan.setEnabled(True)
        self._populate_device_list()
        n_p = len(self._discovery.printers)
        n_s = len(self._discovery.scanners)
        warn = "; ".join(self._discovery.warnings[:2])
        msg = f"{n_s} Scanner · {n_p} Drucker"
        if warn:
            msg += f" — {warn}"
        self.device_status.setText(msg)
        self.device_status.setAccessibleName(msg)

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

    def _acquire_scan(self) -> None:
        scanner = self.selected_scanner()
        if scanner is None and self._discovery.scanners:
            QMessageBox.information(
                self,
                "Scanner",
                "Bitte einen Scanner in der Liste auswählen "
                "(oder Bilder importieren).",
            )
            return
        try:
            paths = acquire_from_scanner(scanner)
        except Exception as e:
            QMessageBox.warning(self, "Scan", str(e))
            return
        if not paths:
            QMessageBox.information(
                self,
                "Scan",
                "Kein Bild vom Scanner erhalten.\n\n"
                "Hinweis: Auf Windows wird WIA genutzt; ohne unterstütztes Gerät "
                "bitte „Bilder importieren…“ verwenden.\n\n"
                + WINDOWS_SCAN_DEPS_HINT,
            )
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
        # OCR-Text optional an MainWindow übergeben (Editor)
        if result.combined_text:
            mw = self.parent()
            show_fn = getattr(mw, "_show_scan_ocr_text", None) if mw is not None else None
            if callable(show_fn):
                try:
                    show_fn(result.combined_text, f"Scan-OCR — {target.stem}")
                except Exception:
                    pass

        self._last_result = result
        QMessageBox.information(self, "Scan / Import", msg)
        self.accept()
