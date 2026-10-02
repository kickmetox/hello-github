"""Einstellungen: Theme, OCR, Sprache, Export, Zoom, Autosave, Pfade."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ild_pdf.pages import PAGE_SIZE_PRESETS
from instantlensdoc.core.app_settings import (
    get_autosave_interval_sec,
    get_batch_output_dir,
    get_default_open_dir,
    get_default_zoom_percent,
    get_export_image_max_edge,
    get_export_jpeg_quality,
    get_export_pdf_page,
    get_ocr_lang,
    get_theme,
    get_ui_lang,
    get_update_check_on_start,
    save_settings,
    set_autosave_interval_sec,
    set_batch_output_dir,
    set_default_open_dir,
    set_default_zoom_percent,
    set_ocr_lang,
    set_theme,
    set_ui_lang,
    set_update_check_on_start,
)
from instantlensdoc.core.i18n import sync_from_settings, tr
from instantlensdoc.core.ocr import LANG_PRESETS
from instantlensdoc.ui.theme import apply_theme


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        sync_from_settings()
        self.setWindowTitle(tr("settings"))
        self.resize(540, 440)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("settings_title")))

        form = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(tr("theme_light"), "light")
        self.theme_combo.addItem(tr("theme_dark"), "dark")
        cur_theme = get_theme()
        self.theme_combo.setCurrentIndex(1 if cur_theme == "dark" else 0)
        form.addRow(tr("theme"), self.theme_combo)

        self.ui_lang = QComboBox()
        self.ui_lang.addItem(tr("lang_de"), "de")
        self.ui_lang.addItem(tr("lang_en"), "en")
        self.ui_lang.setCurrentIndex(1 if get_ui_lang() == "en" else 0)
        form.addRow(tr("ui_lang"), self.ui_lang)

        self.lang_combo = QComboBox()
        cur_lang = get_ocr_lang()
        pick = 0
        for i, (name, code) in enumerate(LANG_PRESETS.items()):
            self.lang_combo.addItem(name, code)
            if code == cur_lang:
                pick = i
        self.lang_combo.setCurrentIndex(pick)
        form.addRow(tr("ocr_lang"), self.lang_combo)

        self.zoom_pct = QSpinBox()
        self.zoom_pct.setRange(25, 500)
        self.zoom_pct.setSingleStep(10)
        self.zoom_pct.setSuffix(" %")
        self.zoom_pct.setValue(get_default_zoom_percent())
        self.zoom_pct.setToolTip("Standard-Zoom beim Öffnen von PDFs")
        form.addRow(tr("default_zoom"), self.zoom_pct)

        self.autosave_sec = QSpinBox()
        self.autosave_sec.setRange(10, 600)
        self.autosave_sec.setSingleStep(10)
        self.autosave_sec.setSuffix(" s")
        self.autosave_sec.setValue(get_autosave_interval_sec())
        self.autosave_sec.setToolTip("Intervall für Autosave (Editor + Annotationen)")
        form.addRow(tr("autosave_interval"), self.autosave_sec)

        self.jpeg_q = QSpinBox()
        self.jpeg_q.setRange(10, 100)
        self.jpeg_q.setValue(get_export_jpeg_quality())
        form.addRow(tr("export_jpeg_q"), self.jpeg_q)

        self.page_combo = QComboBox()
        cur_page = get_export_pdf_page()
        page_pick = 0
        for i, name in enumerate(PAGE_SIZE_PRESETS.keys()):
            self.page_combo.addItem(name, name)
            if name == cur_page:
                page_pick = i
        self.page_combo.setCurrentIndex(page_pick)
        form.addRow(tr("export_page"), self.page_combo)

        self.max_edge = QSpinBox()
        self.max_edge.setRange(200, 8000)
        self.max_edge.setSingleStep(100)
        self.max_edge.setValue(get_export_image_max_edge())
        form.addRow("Export Max-Kante (px)", self.max_edge)

        self.update_chk = QCheckBox(tr("update_check"))
        self.update_chk.setChecked(get_update_check_on_start())
        form.addRow(self.update_chk)

        self.batch_dir = QLineEdit()
        bd = get_batch_output_dir()
        self.batch_dir.setText(str(bd) if bd else "")
        batch_row = QHBoxLayout()
        batch_row.addWidget(self.batch_dir)
        btn_b = QPushButton("…")
        btn_b.clicked.connect(lambda: self._pick_dir(self.batch_dir))
        batch_row.addWidget(btn_b)
        form.addRow(tr("batch_dir"), batch_row)

        self.open_dir = QLineEdit()
        od = get_default_open_dir()
        self.open_dir.setText(str(od) if od else "")
        open_row = QHBoxLayout()
        open_row.addWidget(self.open_dir)
        btn_o = QPushButton("…")
        btn_o.clicked.connect(lambda: self._pick_dir(self.open_dir))
        open_row.addWidget(btn_o)
        form.addRow(tr("open_dir"), open_row)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick_dir(self, field: QLineEdit):
        start = field.text().strip() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, tr("pick_dir"), start)
        if path:
            field.setText(path)

    def _save(self):
        theme = self.theme_combo.currentData() or "light"
        lang = self.lang_combo.currentData() or "deu+eng"
        set_theme("dark" if theme == "dark" else "light")
        set_ocr_lang(str(lang))
        set_ui_lang(str(self.ui_lang.currentData() or "de"))
        sync_from_settings()
        set_update_check_on_start(self.update_chk.isChecked())
        set_default_zoom_percent(int(self.zoom_pct.value()))
        set_autosave_interval_sec(int(self.autosave_sec.value()))
        save_settings(
            {
                "export_jpeg_quality": int(self.jpeg_q.value()),
                "export_pdf_page": str(self.page_combo.currentData() or "A4"),
                "export_image_max_edge": int(self.max_edge.value()),
            }
        )
        batch = self.batch_dir.text().strip()
        if batch:
            set_batch_output_dir(batch)
        else:
            save_settings({"batch_output_dir": ""})
        op = self.open_dir.text().strip()
        if op:
            set_default_open_dir(op)
        else:
            save_settings({"default_open_dir": ""})
        apply_theme(mode=get_theme())
        self.accept()
