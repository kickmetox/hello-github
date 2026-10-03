"""Dialog: Wasserzeichen (Text/Bild, Settings, Seitenbereich, Vorschau, Bake) — 1.6.5."""

from __future__ import annotations

import html as _html
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ild_pdf.pages import flatten_page_indices, parse_page_ranges
from ild_pdf.watermark import (
    DEFAULT_WATERMARK_OUTPUT_TEMPLATE,
    WatermarkBakeCancelled,
    apply_header_footer,
    apply_image_watermark,
    apply_page_numbers,
    apply_watermark,
    find_invalid_watermark_placeholders,
    format_header_footer_preview,
    format_watermark_output_path,
    highlight_watermark_template_html,
    preview_watermark_output_filename,
    render_watermark_preview,
)
from instantlensdoc.core.app_settings import (
    get_last_header_footer_settings,
    get_last_watermark_settings,
    get_watermark_output_template,
    set_last_header_footer_settings,
    set_last_watermark_settings,
    set_watermark_output_template,
)


class WmOutTemplateEdit(QLineEdit):
    """WM-Ausgabe-Template: Cursor merken + lokales Undo — 1.6.4."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_cursor = 0
        self._saved_sel_start = -1
        self._saved_sel_len = 0

    def focusOutEvent(self, event):
        self._saved_cursor = self.cursorPosition()
        self._saved_sel_start = self.selectionStart()
        self._saved_sel_len = self.selectionLength()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Undo):
            if self.isUndoAvailable():
                self.undo()
            event.accept()
            return
        if event.matches(QKeySequence.Redo):
            if self.isRedoAvailable():
                self.redo()
            event.accept()
            return
        super().keyPressEvent(event)

    def restore_insert_position(self) -> None:
        if self.hasFocus():
            return
        if self._saved_sel_start >= 0 and self._saved_sel_len > 0:
            self.setSelection(self._saved_sel_start, self._saved_sel_len)
        else:
            pos = max(0, min(self._saved_cursor, len(self.text())))
            self.setCursorPosition(pos)


class WatermarkDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        pdf_path: str | None = None,
        page_index: int = 0,
        page_count: int = 1,
    ):
        super().__init__(parent)
        self.setWindowTitle("Wasserzeichen / Seitennummern / Kopfzeile")
        self.resize(740, 640)
        self._initial = pdf_path or ""
        self._page_index = page_index
        self._page_count = max(page_count, 1)
        self.result_path: str | None = None
        self._last = get_last_watermark_settings()
        self._last_hf = get_last_header_footer_settings()

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_wm_tab(), "Wasserzeichen")
        tabs.addTab(self._build_num_tab(), "Seitennummern")
        tabs.addTab(self._build_hf_tab(), "Kopf-/Fußzeile")
        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh_preview()

    def _path_row(self, initial: str) -> tuple[QLineEdit, QHBoxLayout]:
        edit = QLineEdit(initial)
        pick = QPushButton("PDF…")
        row = QHBoxLayout()
        row.addWidget(edit)
        row.addWidget(pick)

        def _pick():
            path, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
            if path:
                edit.setText(path)
                self._refresh_preview()

        pick.clicked.connect(_pick)
        edit.textChanged.connect(lambda *_: self._refresh_preview())
        return edit, row

    def _build_wm_tab(self) -> QWidget:
        w = QWidget()
        root = QHBoxLayout(w)
        form_host = QWidget()
        form = QFormLayout(form_host)
        self.wm_src, src_row = self._path_row(self._initial)
        form.addRow("PDF", src_row)

        mode_row = QHBoxLayout()
        self.wm_mode_text = QRadioButton("Text")
        self.wm_mode_image = QRadioButton("Bild")
        if self._last.get("mode") == "image":
            self.wm_mode_image.setChecked(True)
        else:
            self.wm_mode_text.setChecked(True)
        mode_row.addWidget(self.wm_mode_text)
        mode_row.addWidget(self.wm_mode_image)
        mode_row.addStretch(1)
        form.addRow("Art", mode_row)
        self.wm_mode_text.toggled.connect(self._on_wm_mode)
        self.wm_mode_image.toggled.connect(self._on_wm_mode)

        self.wm_text = QLineEdit(str(self._last.get("text") or "VERTRAULICH"))
        self.wm_text.textChanged.connect(lambda *_: self._refresh_preview())
        form.addRow("Text", self.wm_text)

        img_row = QHBoxLayout()
        self.wm_image = QLineEdit(str(self._last.get("image") or ""))
        self.wm_image.setPlaceholderText("PNG / JPEG…")
        btn_img = QPushButton("Bild…")
        btn_img.clicked.connect(self._pick_image)
        img_row.addWidget(self.wm_image)
        img_row.addWidget(btn_img)
        form.addRow("Bild", img_row)
        self.wm_image.textChanged.connect(lambda *_: self._refresh_preview())

        self.wm_placement = QComboBox()
        self.wm_placement.addItem("Diagonal", "diagonal")
        self.wm_placement.addItem("Zentriert", "center")
        place = str(self._last.get("placement") or "diagonal")
        idx = self.wm_placement.findData(place)
        if idx >= 0:
            self.wm_placement.setCurrentIndex(idx)
        self.wm_placement.currentIndexChanged.connect(lambda *_: self._refresh_preview())
        form.addRow("Position", self.wm_placement)

        # Opacity / Größe / Winkel Settings — 1.6.1
        self.wm_opacity = QDoubleSpinBox()
        self.wm_opacity.setRange(0.05, 1.0)
        self.wm_opacity.setSingleStep(0.05)
        self.wm_opacity.setValue(float(self._last.get("opacity") or 0.25))
        self.wm_opacity.setToolTip("Deckkraft (Settings merken) — 1.6.1")
        self.wm_opacity.valueChanged.connect(lambda *_: self._refresh_preview())
        form.addRow("Deckkraft", self.wm_opacity)

        self.wm_angle = QDoubleSpinBox()
        self.wm_angle.setRange(-90, 90)
        self.wm_angle.setValue(float(self._last.get("angle") or 45))
        self.wm_angle.setToolTip("Winkel in Grad (Settings merken) — 1.6.1")
        self.wm_angle.valueChanged.connect(lambda *_: self._refresh_preview())
        form.addRow("Winkel °", self.wm_angle)

        self.wm_size = QDoubleSpinBox()
        self.wm_size.setRange(8, 120)
        self.wm_size.setValue(float(self._last.get("font_size") or 48))
        self.wm_size.setToolTip("Schriftgröße (Settings merken) — 1.6.1")
        self.wm_size.valueChanged.connect(lambda *_: self._refresh_preview())
        form.addRow("Schriftgröße", self.wm_size)

        self.wm_img_scale = QDoubleSpinBox()
        self.wm_img_scale.setRange(0.1, 1.0)
        self.wm_img_scale.setSingleStep(0.05)
        self.wm_img_scale.setValue(float(self._last.get("img_scale") or 0.45))
        self.wm_img_scale.setToolTip("Bild-Skalierung (Settings merken) — 1.6.1")
        self.wm_img_scale.valueChanged.connect(lambda *_: self._refresh_preview())
        form.addRow("Bild-Skalierung", self.wm_img_scale)

        # Seitenbereich — 1.6.1
        self.wm_scope = QComboBox()
        self.wm_scope.addItem("Alle Seiten", "all")
        self.wm_scope.addItem("Aktuelle Seite", "current")
        self.wm_scope.addItem("Seitenbereich…", "range")
        self.wm_scope.currentIndexChanged.connect(self._on_wm_scope)
        form.addRow("Seiten", self.wm_scope)

        self.wm_range = QLineEdit()
        self.wm_range.setPlaceholderText(f"z.B. 1-3,5 (1…{self._page_count})")
        self.wm_range.setToolTip(
            "Seitenbereich 1-basiert, z. B. 1-3,5 — 1.6.1"
        )
        form.addRow("Seitenbereich", self.wm_range)

        # Kompatibilität: altes Flag bleibt für Smoke/API erreichbar
        self.wm_current = QCheckBox("Nur aktuelle Seite")
        self.wm_current.setVisible(False)
        self.wm_scope.currentIndexChanged.connect(
            lambda *_: self.wm_current.setChecked(
                self.wm_scope.currentData() == "current"
            )
        )

        # Ausgabe-Pfad Template: Quick-Insert + Reset-Template·Fokus/Selektion — 1.6.5
        self.wm_out_tpl = WmOutTemplateEdit(get_watermark_output_template())
        self.wm_out_tpl.setPlaceholderText(DEFAULT_WATERMARK_OUTPUT_TEMPLATE)
        self.wm_out_tpl.setToolTip(
            "Ausgabe-Pfad-Template: {stem}, {name}, {suffix}, {date}. "
            "Quick-Insert an Cursor; lokales Undo (Ctrl+Z); "
            "Reset-Template auf Default — 1.6.5"
        )
        tpl_row = QHBoxLayout()
        tpl_row.addWidget(self.wm_out_tpl, 1)
        for token in ("{stem}", "{date}"):
            btn = QPushButton(token)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.TabFocus)
            btn.setToolTip(
                f"Platzhalter {token} an Cursor-Position einfügen "
                "(lokales Undo: Ctrl+Z) — 1.6.5"
            )
            btn.clicked.connect(
                lambda _checked=False, t=token: self._insert_wm_out_placeholder(t)
            )
            tpl_row.addWidget(btn)
        self.btn_reset_wm_tpl = QPushButton("Reset-Template")
        self.btn_reset_wm_tpl.setAutoDefault(False)
        self.btn_reset_wm_tpl.setDefault(False)
        self.btn_reset_wm_tpl.setFocusPolicy(Qt.TabFocus)
        self.btn_reset_wm_tpl.setToolTip(
            f"Template auf Default zurücksetzen "
            f"({DEFAULT_WATERMARK_OUTPUT_TEMPLATE}); "
            "Bestätigung nur wenn Feld vom Default abweicht; "
            "danach Live-Vorschau + Fokus mit Selektion des Default-Texts "
            "(wie Ann.-Template) — 1.6.5"
        )
        self.btn_reset_wm_tpl.clicked.connect(self._reset_wm_out_template)
        tpl_row.addWidget(self.btn_reset_wm_tpl)
        form.addRow("Ausgabe-Template", tpl_row)
        self.wm_out_preview = QLabel("")
        self.wm_out_preview.setWordWrap(True)
        self.wm_out_preview.setTextFormat(Qt.RichText)
        self.wm_out_preview.setStyleSheet("color:#555;")
        self.wm_out_preview.setToolTip(
            "Live-Vorschau Dateiname; ungültige Platzhalter rot — 1.6.5"
        )
        form.addRow("Vorschau Dateiname", self.wm_out_preview)
        self.wm_out_tpl.textChanged.connect(self._update_wm_out_preview)
        self.wm_src.textChanged.connect(self._update_wm_out_preview)
        self._update_wm_out_preview()

        self.wm_inplace = QCheckBox("Original überschreiben")
        self.wm_inplace.setChecked(False)
        self.wm_inplace.setToolTip(
            "Standard: neues PDF aus Template (Settings) — Bake — 1.6.2"
        )
        form.addRow("", self.wm_inplace)

        btn_prev = QPushButton("Vorschau aktualisieren")
        btn_prev.clicked.connect(self._refresh_preview)
        form.addRow(btn_prev)
        run = QPushButton("Wasserzeichen in PDF bakken")
        run.setToolTip(
            "Bake mit Fortschritt/Abbruch; Teilergebnis bei Abbruch; "
            "Template Quick-Insert {stem}/{date}; Reset-Template·Fokus/Selektion; "
            "ungültige Platzhalter rot — 1.6.5"
        )
        run.clicked.connect(self._run_wm)
        form.addRow(run)

        root.addWidget(form_host, 3)
        prev_col = QVBoxLayout()
        prev_col.addWidget(QLabel("Vorschau (aktuelle Seite)"))
        self.wm_preview = QLabel("—")
        self.wm_preview.setAlignment(Qt.AlignCenter)
        self.wm_preview.setMinimumSize(260, 340)
        self.wm_preview.setStyleSheet(
            "QLabel { background:#2a2a2a; border:1px solid #555; color:#aaa; }"
        )
        self.wm_preview.setScaledContents(False)
        prev_col.addWidget(self.wm_preview, 1)
        root.addLayout(prev_col, 2)
        self._on_wm_mode()
        self._on_wm_scope()
        return w

    def _on_wm_scope(self, *_):
        is_range = self.wm_scope.currentData() == "range"
        self.wm_range.setEnabled(is_range)

    def _on_wm_mode(self, *_):
        is_text = self.wm_mode_text.isChecked()
        self.wm_text.setEnabled(is_text)
        self.wm_size.setEnabled(is_text)
        self.wm_image.setEnabled(not is_text)
        self.wm_img_scale.setEnabled(not is_text)
        self._refresh_preview()

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Wasserzeichen-Bild",
            "",
            "Bilder (*.png *.jpg *.jpeg *.webp *.bmp);;Alle (*.*)",
        )
        if path:
            self.wm_image.setText(path)
            self.wm_mode_image.setChecked(True)
            self._refresh_preview()

    def _placement(self) -> str:
        data = self.wm_placement.currentData()
        return str(data or "diagonal")

    def _insert_wm_out_placeholder(self, token: str) -> None:
        """Quick-Insert {stem}/{date} an Cursor — 1.6.4/1.6.5."""
        edit = self.wm_out_tpl
        if isinstance(edit, WmOutTemplateEdit):
            edit.restore_insert_position()
        edit.insert(str(token or ""))
        edit.setFocus()
        if isinstance(edit, WmOutTemplateEdit):
            edit._saved_cursor = edit.cursorPosition()
            edit._saved_sel_start = -1
            edit._saved_sel_len = 0
        self._update_wm_out_preview()

    def _focus_wm_out_tpl_select_all(self) -> None:
        """Fokus + Selektion ganzer Default-Text (wie Ann.-Template) — 1.6.5."""
        if not hasattr(self, "wm_out_tpl"):
            return
        edit = self.wm_out_tpl
        edit.setFocus()
        edit.selectAll()
        if isinstance(edit, WmOutTemplateEdit):
            edit._saved_cursor = 0
            edit._saved_sel_start = 0
            edit._saved_sel_len = len(edit.text() or "")

    def _reset_wm_out_template(self) -> None:
        """
        Template auf Default; Bestätigung nur bei Abweichung;
        danach Live-Vorschau + Fokus mit Selektion (wie Ann.-Template) — 1.6.5.
        """
        if not hasattr(self, "wm_out_tpl"):
            return
        edit = self.wm_out_tpl
        default = DEFAULT_WATERMARK_OUTPUT_TEMPLATE
        current = edit.text() or ""
        if current == default:
            self._update_wm_out_preview()
            QTimer.singleShot(0, self._focus_wm_out_tpl_select_all)
            return
        reply = QMessageBox.question(
            self,
            "Reset-Template",
            f"Wasserzeichen-Ausgabe-Template auf Default zurücksetzen?\n\n"
            f"Aktuell: {current}\n"
            f"Default: {default}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            QTimer.singleShot(0, self._focus_wm_out_tpl_select_all)
            return
        # selectAll + insert → ein Undo-Schritt (Ctrl+Z stellt vorherigen Text wieder her)
        edit.selectAll()
        edit.insert(default)
        if isinstance(edit, WmOutTemplateEdit):
            edit._saved_cursor = edit.cursorPosition()
            edit._saved_sel_start = -1
            edit._saved_sel_len = 0
        self._update_wm_out_preview()
        QTimer.singleShot(0, self._focus_wm_out_tpl_select_all)

    def _update_wm_out_preview(self, *_args) -> None:
        """Live-Vorschau; ungültige Platzhalter rot — 1.6.4/1.6.5."""
        if not hasattr(self, "wm_out_preview"):
            return
        src = (self.wm_src.text().strip() if hasattr(self, "wm_src") else "") or ""
        sample = Path(src).stem if src else "dokument"
        tpl = self.wm_out_tpl.text().strip() or DEFAULT_WATERMARK_OUTPUT_TEMPLATE
        try:
            name = preview_watermark_output_filename(
                tpl,
                sample_stem=sample or "dokument",
            )
            html_tpl = highlight_watermark_template_html(tpl)
            invalid = find_invalid_watermark_placeholders(tpl)
            parts = [html_tpl, f"→ {_html.escape(name)}"]
            if invalid:
                listed = ", ".join(_html.escape("{" + n + "}") for n in invalid)
                parts.append(
                    f'<span style="color:#c62828">Ungültige Platzhalter: {listed}</span>'
                )
            self.wm_out_preview.setText("<br>".join(parts))
            self.wm_out_preview.setStyleSheet("color:#555;")
        except Exception as e:
            self.wm_out_preview.setText(
                f'<span style="color:#c62828">Ungültiges Template: '
                f"{_html.escape(str(e))}</span>"
            )
            self.wm_out_preview.setStyleSheet("color:#c62828;")

    def _persist_wm_settings(self) -> None:
        set_last_watermark_settings(
            text=self.wm_text.text().strip() or "VERTRAULICH",
            image=self.wm_image.text().strip(),
            opacity=self.wm_opacity.value(),
            angle=self.wm_angle.value(),
            font_size=self.wm_size.value(),
            img_scale=self.wm_img_scale.value(),
            placement=self._placement(),
            mode="image" if self.wm_mode_image.isChecked() else "text",
        )
        set_watermark_output_template(self.wm_out_tpl.text().strip())

    def _resolve_pages(self) -> list[int] | None:
        """None = alle Seiten; sonst 0-basierte Indizes — 1.6.1."""
        scope = str(self.wm_scope.currentData() or "all")
        if scope == "current" or self.wm_current.isChecked():
            return [self._page_index]
        if scope == "range":
            spec = self.wm_range.text().strip()
            ranges = parse_page_ranges(spec, self._page_count, one_based=True)
            return flatten_page_indices(ranges)
        return None

    def _refresh_preview(self):
        src = (self.wm_src.text() if hasattr(self, "wm_src") else "").strip()
        if not src or not Path(src).is_file():
            if hasattr(self, "wm_preview"):
                self.wm_preview.setText("PDF wählen…")
                self.wm_preview.setPixmap(QPixmap())
            return
        try:
            mode = "text" if self.wm_mode_text.isChecked() else "image"
            img = render_watermark_preview(
                src,
                page_index=self._page_index,
                mode=mode,
                text=self.wm_text.text().strip() or "VERTRAULICH",
                image=self.wm_image.text().strip() or None,
                opacity=self.wm_opacity.value(),
                angle_deg=self.wm_angle.value(),
                font_size=self.wm_size.value(),
                scale=self.wm_img_scale.value(),
                placement=self._placement(),
                render_scale=0.85,
            )
            data = img.tobytes("raw", "RGB")
            qimg = QImage(data, img.width, img.height, img.width * 3, QImage.Format_RGB888)
            pm = QPixmap.fromImage(qimg.copy())
            scaled = pm.scaled(
                self.wm_preview.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.wm_preview.setPixmap(scaled)
            self.wm_preview.setText("")
        except Exception as e:
            self.wm_preview.setPixmap(QPixmap())
            self.wm_preview.setText(f"Vorschau:\n{e}")

    def _build_num_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.num_src, src_row = self._path_row(self._initial)
        form.addRow("PDF", src_row)
        self.num_tpl = QLineEdit("{n} / {total}")
        self.num_tpl.setToolTip("Platzhalter: {n}, {total}, {i}")
        form.addRow("Vorlage", self.num_tpl)
        self.num_pos = QComboBox()
        self.num_pos.addItems(
            ["bottom-center", "bottom-right", "bottom-left", "top-center"]
        )
        form.addRow("Position", self.num_pos)
        self.num_size = QDoubleSpinBox()
        self.num_size.setRange(6, 36)
        self.num_size.setValue(10)
        form.addRow("Schriftgröße", self.num_size)
        self.num_start = QSpinBox()
        self.num_start.setRange(0, 9999)
        self.num_start.setValue(1)
        form.addRow("Startnummer", self.num_start)
        self.num_inplace = QCheckBox("Original überschreiben")
        self.num_inplace.setChecked(True)
        form.addRow("", self.num_inplace)
        run = QPushButton("Seitennummern stempeln")
        run.clicked.connect(self._run_num)
        form.addRow(run)
        return w

    def _out_path(self, src: Path, inplace: bool, suffix: str) -> Path:
        if inplace:
            return src
        if suffix == "wm":
            tpl = set_watermark_output_template(self.wm_out_tpl.text().strip())
            return format_watermark_output_path(src, tpl, inplace=False)
        return src.with_name(f"{src.stem}_{suffix}{src.suffix}")

    def _run_wm(self):
        src = self.wm_src.text().strip()
        if not src:
            QMessageBox.warning(self, "Wasserzeichen", "PDF angeben.")
            return
        try:
            pages = self._resolve_pages()
        except ValueError as e:
            QMessageBox.warning(self, "Wasserzeichen — Seitenbereich", str(e))
            return
        path = Path(src)
        out = self._out_path(path, self.wm_inplace.isChecked(), "wm")
        placement = self._placement()
        # Fortschritt + Abbruch — 1.6.2
        if pages is None:
            total_pages = max(1, self._page_count)
        else:
            total_pages = max(1, len(pages))
        prog = QProgressDialog(
            "Wasserzeichen bakken…", "Abbrechen", 0, total_pages, self
        )
        prog.setWindowTitle("Wasserzeichen")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        prog.setValue(0)
        cancelled = {"v": False}

        def on_progress(cur: int, total: int) -> bool:
            if prog.wasCanceled():
                cancelled["v"] = True
                return False
            prog.setMaximum(max(1, total))
            prog.setValue(cur)
            prog.setLabelText(f"Wasserzeichen bakken… Seite {cur}/{total}")
            QApplication.processEvents()
            if prog.wasCanceled():
                cancelled["v"] = True
                return False
            return True

        try:
            if self.wm_mode_image.isChecked():
                img = self.wm_image.text().strip()
                if not img or not Path(img).is_file():
                    prog.close()
                    QMessageBox.warning(self, "Wasserzeichen", "Bilddatei angeben.")
                    return
                apply_image_watermark(
                    path,
                    img,
                    out_path=out,
                    pages=pages,
                    opacity=self.wm_opacity.value(),
                    angle_deg=self.wm_angle.value(),
                    scale=self.wm_img_scale.value(),
                    placement=placement,
                    on_progress=on_progress,
                )
            else:
                text = self.wm_text.text().strip()
                if not text:
                    prog.close()
                    QMessageBox.warning(self, "Wasserzeichen", "Text angeben.")
                    return
                apply_watermark(
                    path,
                    text,
                    out_path=out,
                    pages=pages,
                    opacity=self.wm_opacity.value(),
                    angle_deg=self.wm_angle.value(),
                    font_size=self.wm_size.value(),
                    placement=placement,
                    on_progress=on_progress,
                )
            prog.close()
            self._persist_wm_settings()
            self.result_path = str(out)
            QMessageBox.information(
                self,
                "Wasserzeichen",
                f"Gebacken / gespeichert:\n{out}",
            )
        except WatermarkBakeCancelled as e:
            prog.close()
            # Teilergebnis-Hinweis — 1.6.3
            if e.partial_path is not None and Path(e.partial_path).is_file():
                self.result_path = str(e.partial_path)
                QMessageBox.information(
                    self,
                    "Wasserzeichen",
                    f"Bake abgebrochen — Teilergebnis "
                    f"({e.done}/{e.total} Seiten) gespeichert:\n{e.partial_path}",
                )
            else:
                QMessageBox.information(
                    self,
                    "Wasserzeichen",
                    "Bake abgebrochen — kein Teilergebnis "
                    "(noch keine Seite fertig).",
                )
        except Exception as e:
            prog.close()
            QMessageBox.critical(self, "Wasserzeichen", str(e))

    def _run_num(self):
        src = self.num_src.text().strip()
        if not src:
            QMessageBox.warning(self, "Seitennummern", "PDF angeben.")
            return
        try:
            path = Path(src)
            out = self._out_path(path, self.num_inplace.isChecked(), "pages")
            apply_page_numbers(
                path,
                out_path=out,
                template=self.num_tpl.text().strip() or "{n} / {total}",
                position=self.num_pos.currentText(),
                font_size=self.num_size.value(),
                start_at=self.num_start.value(),
            )
            self.result_path = str(out)
            QMessageBox.information(self, "Seitennummern", f"Gespeichert:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Seitennummern", str(e))

    def _build_hf_tab(self) -> QWidget:
        """Kopf-/Fußzeile + Seitenzahl bake; Schrift/Rand Settings·Vorschau·Seitenbereich — 1.8.1."""
        w = QWidget()
        root = QHBoxLayout(w)
        form_host = QWidget()
        form = QFormLayout(form_host)
        self.hf_src, src_row = self._path_row(self._initial)
        form.addRow("PDF", src_row)
        self.hf_header = QLineEdit(str(self._last_hf.get("header_text") or ""))
        self.hf_header.setPlaceholderText("z. B. {stem} — vertraulich")
        self.hf_header.setToolTip("Platzhalter: {n} {total} {page} {stem} {date}")
        form.addRow("Kopfzeile", self.hf_header)
        self.hf_footer = QLineEdit(str(self._last_hf.get("footer_text") or ""))
        self.hf_footer.setPlaceholderText("z. B. Entwurf {date}")
        self.hf_footer.setToolTip("Platzhalter: {n} {total} {page} {stem} {date}")
        form.addRow("Fußzeile", self.hf_footer)
        self.hf_include_num = QCheckBox("Seitenzahl bakken")
        self.hf_include_num.setChecked(
            bool(self._last_hf.get("include_page_numbers", True))
        )
        form.addRow("", self.hf_include_num)
        self.hf_num_tpl = QLineEdit(
            str(self._last_hf.get("page_template") or "{n} / {total}")
        )
        form.addRow("Seitenzahl-Vorlage", self.hf_num_tpl)
        positions = [
            "top-left",
            "top-center",
            "top-right",
            "bottom-left",
            "bottom-center",
            "bottom-right",
        ]
        self.hf_header_pos = QComboBox()
        self.hf_header_pos.addItems(positions)
        idx = self.hf_header_pos.findText(
            str(self._last_hf.get("header_position") or "top-center")
        )
        if idx >= 0:
            self.hf_header_pos.setCurrentIndex(idx)
        form.addRow("Kopf-Position", self.hf_header_pos)
        self.hf_footer_pos = QComboBox()
        self.hf_footer_pos.addItems(positions)
        idx = self.hf_footer_pos.findText(
            str(self._last_hf.get("footer_position") or "bottom-center")
        )
        if idx >= 0:
            self.hf_footer_pos.setCurrentIndex(idx)
        form.addRow("Fuß-Position", self.hf_footer_pos)
        self.hf_page_pos = QComboBox()
        self.hf_page_pos.addItems(positions)
        idx = self.hf_page_pos.findText(
            str(self._last_hf.get("page_position") or "bottom-right")
        )
        if idx >= 0:
            self.hf_page_pos.setCurrentIndex(idx)
        form.addRow("Seitenzahl-Position", self.hf_page_pos)
        self.hf_size = QDoubleSpinBox()
        self.hf_size.setRange(6, 36)
        self.hf_size.setValue(float(self._last_hf.get("font_size") or 10))
        self.hf_size.setToolTip("Schriftgröße (Settings merken) — 1.8.1")
        form.addRow("Schriftgröße", self.hf_size)
        self.hf_margin = QDoubleSpinBox()
        self.hf_margin.setRange(8, 120)
        self.hf_margin.setValue(float(self._last_hf.get("margin") or 28))
        self.hf_margin.setToolTip("Rand in pt (Settings merken) — 1.8.1")
        form.addRow("Rand (pt)", self.hf_margin)
        # Seitenbereich — 1.8.1
        self.hf_range = QLineEdit(str(self._last_hf.get("page_range") or ""))
        self.hf_range.setPlaceholderText("leer = alle; z. B. 1-3,5")
        self.hf_range.setToolTip(
            "Seitenbereich 1-basiert, z. B. 1-3,5 (Settings merken) — 1.8.1"
        )
        form.addRow("Seitenbereich", self.hf_range)
        self.hf_inplace = QCheckBox("Original überschreiben")
        self.hf_inplace.setChecked(True)
        form.addRow("", self.hf_inplace)
        run = QPushButton("Kopf-/Fußzeile bakken")
        run.clicked.connect(self._run_hf)
        form.addRow(run)
        root.addWidget(form_host, 3)
        # Vorschau erste Seite — 1.8.1
        prev_col = QVBoxLayout()
        prev_col.addWidget(QLabel("Vorschau erste Seite"))
        self.hf_page_thumb = QLabel()
        self.hf_page_thumb.setAlignment(Qt.AlignCenter)
        self.hf_page_thumb.setMinimumSize(180, 220)
        self.hf_page_thumb.setStyleSheet(
            "QLabel { background: #f4f4f4; border: 1px solid #ccc; }"
        )
        prev_col.addWidget(self.hf_page_thumb, 1)
        self.hf_preview = QLabel()
        self.hf_preview.setWordWrap(True)
        self.hf_preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.hf_preview.setStyleSheet("QLabel { color: #333; padding: 4px; }")
        prev_col.addWidget(self.hf_preview)
        btn_prev = QPushButton("Vorschau aktualisieren")
        btn_prev.clicked.connect(self._refresh_hf_preview)
        prev_col.addWidget(btn_prev)
        prev_host = QWidget()
        prev_host.setLayout(prev_col)
        root.addWidget(prev_host, 2)
        for wdg in (
            self.hf_header,
            self.hf_footer,
            self.hf_num_tpl,
            self.hf_range,
        ):
            wdg.textChanged.connect(lambda *_: self._refresh_hf_preview())
        self.hf_include_num.toggled.connect(lambda *_: self._refresh_hf_preview())
        self.hf_size.valueChanged.connect(lambda *_: self._refresh_hf_preview())
        self.hf_margin.valueChanged.connect(lambda *_: self._refresh_hf_preview())
        QTimer.singleShot(0, self._refresh_hf_preview)
        return w

    def _resolve_hf_pages(self):
        """Seitenbereich für HF-Bake; None = alle — 1.8.1."""
        spec = (self.hf_range.text() or "").strip()
        if not spec:
            return None
        ranges = parse_page_ranges(spec, self._page_count, one_based=True)
        return flatten_page_indices(ranges)

    def _refresh_hf_preview(self) -> None:
        """Text + Thumbnail der ersten Seite — 1.8.1."""
        src = ""
        if hasattr(self, "hf_src"):
            src = self.hf_src.text().strip()
        stem = Path(src).stem if src else "dokument"
        try:
            text = format_header_footer_preview(
                header_text=self.hf_header.text() if hasattr(self, "hf_header") else "",
                footer_text=self.hf_footer.text() if hasattr(self, "hf_footer") else "",
                include_page_numbers=(
                    self.hf_include_num.isChecked()
                    if hasattr(self, "hf_include_num")
                    else True
                ),
                page_number_template=(
                    self.hf_num_tpl.text().strip()
                    if hasattr(self, "hf_num_tpl")
                    else "{n} / {total}"
                )
                or "{n} / {total}",
                font_size=self.hf_size.value() if hasattr(self, "hf_size") else 10,
                margin=self.hf_margin.value() if hasattr(self, "hf_margin") else 28,
                total_pages=self._page_count,
                stem=stem,
                page_index=0,
            )
            if hasattr(self, "hf_preview"):
                self.hf_preview.setText(text)
        except Exception as e:
            if hasattr(self, "hf_preview"):
                self.hf_preview.setText(f"Vorschau:\n{e}")
        if hasattr(self, "hf_page_thumb") and src and Path(src).is_file():
            try:
                from ild_pdf.render import render_page

                img = render_page(src, 0, scale=0.35, use_cache=True)
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                data = img.tobytes("raw", "RGBA")
                qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
                pm = QPixmap.fromImage(qimg.copy())
                self.hf_page_thumb.setPixmap(
                    pm.scaled(
                        self.hf_page_thumb.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            except Exception:
                self.hf_page_thumb.setText("Vorschau n/a")
        elif hasattr(self, "hf_page_thumb"):
            self.hf_page_thumb.setText("PDF wählen…")

    def _run_hf(self):
        src = self.hf_src.text().strip()
        if not src:
            QMessageBox.warning(self, "Kopf-/Fußzeile", "PDF angeben.")
            return
        header = self.hf_header.text()
        footer = self.hf_footer.text()
        include_num = self.hf_include_num.isChecked()
        if not header.strip() and not footer.strip() and not include_num:
            QMessageBox.warning(
                self,
                "Kopf-/Fußzeile",
                "Kopfzeile, Fußzeile oder Seitenzahl angeben.",
            )
            return
        try:
            pages = self._resolve_hf_pages()
        except ValueError as e:
            QMessageBox.warning(self, "Kopf-/Fußzeile — Seitenbereich", str(e))
            return
        try:
            path = Path(src)
            out = self._out_path(path, self.hf_inplace.isChecked(), "hf")
            apply_header_footer(
                path,
                out_path=out,
                pages=pages,
                header_text=header,
                footer_text=footer,
                include_page_numbers=include_num,
                page_number_template=self.hf_num_tpl.text().strip() or "{n} / {total}",
                header_position=self.hf_header_pos.currentText(),
                footer_position=self.hf_footer_pos.currentText(),
                page_number_position=self.hf_page_pos.currentText(),
                font_size=self.hf_size.value(),
                margin=self.hf_margin.value(),
            )
            set_last_header_footer_settings(
                header_text=header,
                footer_text=footer,
                include_page_numbers=include_num,
                page_template=self.hf_num_tpl.text().strip() or "{n} / {total}",
                header_position=self.hf_header_pos.currentText(),
                footer_position=self.hf_footer_pos.currentText(),
                page_position=self.hf_page_pos.currentText(),
                font_size=self.hf_size.value(),
                margin=self.hf_margin.value(),
                page_range=self.hf_range.text().strip(),
            )
            self.result_path = str(out)
            QMessageBox.information(self, "Kopf-/Fußzeile", f"Gespeichert:\n{out}")
            self._refresh_hf_preview()
        except Exception as e:
            QMessageBox.critical(self, "Kopf-/Fußzeile", str(e))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "wm_preview") and self.wm_preview.pixmap() and not self.wm_preview.pixmap().isNull():
            self._refresh_preview()
