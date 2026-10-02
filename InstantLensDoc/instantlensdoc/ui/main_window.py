"""Hauptfenster: Menüleiste, Seitenleiste, Editor, Statusleiste."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from instantlensdoc import __version__
from instantlensdoc.config import DISPLAY_NAME, icon_paths_for_qt
from instantlensdoc.core.documents import DocKind, Document, open_document, save_document
from instantlensdoc.core import ocr as ocr_mod
from instantlensdoc.core.layout import LayoutDocument
from instantlensdoc.core import recent as recent_mod
from instantlensdoc.core import recent_searches as recent_searches_mod
from instantlensdoc.license import LicenseManager
from instantlensdoc.ui.editor import TextEditor
from instantlensdoc.ui.form_builder import FormBuilderDialog
from instantlensdoc.ui.help_dialog import AboutDialog, HelpDialog
from instantlensdoc.ui.license_dialog import LicenseDialog
from instantlensdoc.ui.ocr_dialog import OcrDialog
from instantlensdoc.ui.pdf_view import PdfViewer
from instantlensdoc.ui.sidebar import Sidebar
from instantlensdoc.core import fulltext as fulltext_mod
from instantlensdoc.core.app_settings import (
    get_autosave_interval_sec,
    get_default_open_dir,
    get_last_export_dir,
    get_update_check_on_start,
    set_last_export_dir,
)
from instantlensdoc.ui.batch_dialog import BatchConvertDialog
from instantlensdoc.ui.pdf_tools_dialog import PdfToolsDialog
from instantlensdoc.ui.watermark_dialog import WatermarkDialog
from instantlensdoc.ui.compare_dialog import PdfCompareDialog
from instantlensdoc.ui.settings_dialog import SettingsDialog
from instantlensdoc.ui.stubs import show_planned
from instantlensdoc.ui.theme import apply_theme, load_theme_mode, toggle_theme
from instantlensdoc.ui.keyboard_help import KeyboardHelpDialog
from instantlensdoc.ui.password_dialog import CompressPdfDialog, SetPasswordDialog
from instantlensdoc.ui.metadata_dialog import MetadataDialog
from instantlensdoc.ui.page_size_dialog import PageSizeDialog
from instantlensdoc.core import session as session_mod
from instantlensdoc.core.i18n import sync_from_settings
from ild_pdf.outline import extract_outline
import logging

_log = logging.getLogger("instantlensdoc.ui.main")


class MainWindow(QMainWindow):
    def __init__(self, license_manager: LicenseManager):
        super().__init__()
        sync_from_settings()
        self.license_manager = license_manager
        self.doc: Document | None = None
        self.layout_doc = LayoutDocument()
        self._editor_marks: list[str] = []
        self._recent_menu = None
        self._theme_action: QAction | None = None
        self._autosave_enabled = True

        self.setAcceptDrops(True)
        self.setWindowTitle(DISPLAY_NAME)
        self.resize(1200, 800)
        icon = QIcon()
        for p in icon_paths_for_qt():
            icon.addFile(str(p))
        if not icon.isNull():
            self.setWindowIcon(icon)

        self._build_ui()
        self._build_menus()
        self._refresh_recent()
        self._refresh_recent_searches()
        self._update_license_status()
        apply_theme()
        self._sync_theme_menu()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(get_autosave_interval_sec() * 1000)
        self._autosave_timer.timeout.connect(self._autosave_tick)
        self._autosave_timer.start()
        QTimer.singleShot(200, self._restore_session)
        if get_update_check_on_start():
            QTimer.singleShot(1500, lambda: self._check_updates(silent=True))

    def closeEvent(self, event):
        try:
            self._save_session()
        except Exception:
            pass
        super().closeEvent(event)

    def _session_paths(self) -> list[str]:
        paths: list[str] = []
        # Sidebar-Dokumente = „offene Tabs“
        try:
            for i in range(self.sidebar.files.count()):
                item = self.sidebar.files.item(i)
                if item is None:
                    continue
                p = item.data(256) or item.data(Qt.UserRole) or item.toolTip() or item.text()
                if p and Path(str(p)).is_file():
                    paths.append(str(Path(str(p))))
        except Exception:
            pass
        if self.doc and self.doc.path and Path(self.doc.path).is_file():
            paths.append(str(Path(self.doc.path)))
        # dedupe preserve order
        out: list[str] = []
        seen: set[str] = set()
        for p in paths:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out

    def _save_session(self):
        paths = self._session_paths()
        active = str(Path(self.doc.path)) if self.doc and self.doc.path else None
        page = self.pdf_view.page_index if self.pdf_view.pdf_path else 0
        scale = self.pdf_view.scale if self.pdf_view.pdf_path else 1.5
        state = session_mod.build_session(
            paths,
            active_path=active,
            page=page,
            scale=scale,
            restore=True,
        )
        session_mod.save_session(state)

    def _restore_session(self):
        import os

        if os.environ.get("ILD_NO_SESSION") == "1" or os.environ.get("ILD_SMOKE_QT"):
            return
        # CLI-Argument hat Vorrang (app.py öffnet danach) — nur wenn noch kein Doc
        if self.doc and self.doc.path:
            return
        state = session_mod.load_session()
        if not state.restore or not state.tabs:
            return
        # Alle Tabs in Sidebar laden, aktives Dokument anzeigen
        for tab in state.tabs:
            if Path(tab.path).is_file():
                self.sidebar.add_document(tab.path)
        active = state.tabs[state.active] if 0 <= state.active < len(state.tabs) else state.tabs[-1]
        if not Path(active.path).is_file():
            return
        self.open_path(active.path)
        if self.pdf_view.pdf_path and self.doc and self.doc.kind == DocKind.PDF:
            if 0 <= active.page < self.pdf_view.page_count:
                self.pdf_view.page_index = active.page
            if active.scale > 0:
                self.pdf_view.set_scale(active.scale, immediate=True)
            else:
                self.pdf_view.refresh()
        self._set_status(f"Session wiederhergestellt ({len(state.tabs)} Tab(s))")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)
        self.sidebar = Sidebar()
        self.sidebar.search_requested.connect(self._on_search)
        self.sidebar.search_next_requested.connect(self._on_search_next)
        self.sidebar.file_activated.connect(self.open_path)
        self.sidebar.recent_activated.connect(self.open_path)
        self.sidebar.mark_activated.connect(self._on_mark_activated)
        self.sidebar.annotation_activated.connect(self._on_annotation_activated)
        self.sidebar.outline_activated.connect(self._on_outline_jump)
        self.sidebar.fulltext_hit_activated.connect(self._on_fulltext_hit)
        self.sidebar.page_thumb_activated.connect(self._on_thumb_jump)
        self.sidebar.pages_reordered.connect(self._on_thumbs_reordered)
        splitter.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.editor = TextEditor()
        self.editor.textChanged.connect(self._on_text_changed)
        self.pdf_view = PdfViewer()
        self.pdf_view.status.connect(self._set_status)
        self.pdf_view.annotations_changed.connect(self._refresh_pdf_marks)
        self.pdf_view.page_changed.connect(self._on_pdf_page_changed)
        self.pdf_view.zoom_changed.connect(self._on_pdf_zoom_changed)
        self.pdf_view.document_changed.connect(self._on_pdf_document_changed)
        self.image_label = QLabel(alignment=Qt.AlignCenter)
        self.image_label.setText("Bildvorschau")
        self.stack.addWidget(self.editor)  # 0
        self.stack.addWidget(self.pdf_view)  # 1
        self.stack.addWidget(self.image_label)  # 2
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter)

        sb = QStatusBar()
        self.setStatusBar(sb)
        self.file_status_label = QLabel("—")
        self.file_status_label.setMinimumWidth(120)
        self.file_status_label.setStyleSheet("padding-left: 6px; padding-right: 8px;")
        sb.addWidget(self.file_status_label, 1)
        self.page_status_label = QLabel("Seite —")
        self.page_status_label.setStyleSheet("padding-right: 10px;")
        sb.addPermanentWidget(self.page_status_label)
        self.zoom_status_label = QLabel("— %")
        self.zoom_status_label.setStyleSheet("padding-right: 10px;")
        sb.addPermanentWidget(self.zoom_status_label)
        self.version_label = QLabel(f"v{__version__}")
        self.version_label.setStyleSheet("color: #666; padding-right: 8px;")
        sb.addPermanentWidget(self.version_label)
        self.license_label = QLabel()
        sb.addPermanentWidget(self.license_label)
        self._update_doc_status()

    def _build_menus(self):
        mb = self.menuBar()

        m_file = mb.addMenu("&Datei")
        act_new = QAction("Neu", self)
        act_new.setShortcut(QKeySequence.New)
        act_new.triggered.connect(self.new_doc)
        m_file.addAction(act_new)

        act_open = QAction("Öffnen…", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self.open_dialog)
        m_file.addAction(act_open)

        self._recent_menu = m_file.addMenu("Zuletzt geöffnet")
        m_file.addSeparator()

        act_save = QAction("Speichern", self)
        act_save.setShortcut(QKeySequence.Save)
        act_save.triggered.connect(self.save_doc)
        m_file.addAction(act_save)

        act_save_as = QAction("Speichern unter…", self)
        act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_as.setToolTip(
            "Text: Dokument speichern unter… · PDF: Annotation-Sidecar speichern unter…"
        )
        act_save_as.triggered.connect(self.save_as)
        m_file.addAction(act_save_as)
        m_export = m_file.addMenu("Exportieren")
        for title, fmt in [
            ("Als HTML…", "html"),
            ("Als DOCX…", "docx"),
            ("Als PDF…", "pdf"),
        ]:
            a = QAction(title, self)
            a.triggered.connect(lambda checked=False, f=fmt: self._export_editor(f))
            m_export.addAction(a)
        m_file.addSeparator()
        act_print = QAction("Drucken…", self)
        act_print.setShortcut(QKeySequence.Print)
        act_print.triggered.connect(self._print)
        m_file.addAction(act_print)
        m_file.addSeparator()
        act_quit = QAction("Beenden", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)

        m_edit = mb.addMenu("&Bearbeiten")
        act_undo = QAction("Rückgängig", self)
        act_undo.setShortcut(QKeySequence.Undo)
        act_undo.triggered.connect(self._undo)
        m_edit.addAction(act_undo)
        act_redo = QAction("Wiederholen", self)
        act_redo.setShortcut(QKeySequence.Redo)
        act_redo.triggered.connect(self._redo)
        m_edit.addAction(act_redo)
        m_edit.addSeparator()
        for name, slot in [
            ("Ausschneiden", self.editor.cut),
            ("Kopieren", self.editor.copy),
            ("Einfügen", self.editor.paste),
        ]:
            a = QAction(name, self)
            a.triggered.connect(slot)
            m_edit.addAction(a)
        act_paste_img = QAction("Bild aus Zwischenablage…", self)
        act_paste_img.setShortcut(QKeySequence("Ctrl+Shift+V"))
        act_paste_img.triggered.connect(self._paste_clipboard_image)
        m_edit.addAction(act_paste_img)
        m_edit.addSeparator()
        act_find = QAction("Suchen…", self)
        act_find.setShortcut(QKeySequence.Find)
        act_find.triggered.connect(self._focus_search)
        m_edit.addAction(act_find)
        act_mark = QAction("Auswahl markieren", self)
        act_mark.setShortcut(QKeySequence("Ctrl+H"))
        act_mark.triggered.connect(self._mark_selection)
        m_edit.addAction(act_mark)
        act_clear_marks = QAction("Markierungen löschen", self)
        act_clear_marks.triggered.connect(self._clear_editor_marks)
        m_edit.addAction(act_clear_marks)
        m_edit.addSeparator()
        act_del_ann = QAction("Annotation löschen", self)
        act_del_ann.setShortcut(QKeySequence.Delete)
        act_del_ann.setToolTip("Ausgewählte Annotation oder letzte auf der Seite")
        act_del_ann.triggered.connect(self._delete_annotation)
        m_edit.addAction(act_del_ann)

        m_view = mb.addMenu("&Ansicht")
        a = QAction("Seitenleiste", self)
        a.setCheckable(True)
        a.setChecked(True)
        a.toggled.connect(self.sidebar.setVisible)
        m_view.addAction(a)
        m_view.addSeparator()
        act_zi = QAction("Vergrößern", self)
        act_zi.setShortcut(QKeySequence.ZoomIn)
        act_zi.triggered.connect(self._zoom_in)
        m_view.addAction(act_zi)
        act_zo = QAction("Verkleinern", self)
        act_zo.setShortcut(QKeySequence.ZoomOut)
        act_zo.triggered.connect(self._zoom_out)
        m_view.addAction(act_zo)
        act_fit = QAction("Seite einpassen", self)
        act_fit.setShortcut(QKeySequence("Ctrl+0"))
        act_fit.triggered.connect(self._fit_page)
        m_view.addAction(act_fit)
        act_fit_w = QAction("Breite einpassen", self)
        act_fit_w.setShortcut(QKeySequence("Ctrl+9"))
        act_fit_w.triggered.connect(self._fit_width)
        m_view.addAction(act_fit_w)
        act_z100 = QAction("Zoom 100 %", self)
        act_z100.setShortcut(QKeySequence("Ctrl+1"))
        act_z100.triggered.connect(self._zoom_100)
        m_view.addAction(act_z100)
        m_view.addSeparator()
        self._theme_action = QAction("Dunkles Design", self)
        self._theme_action.setCheckable(True)
        self._theme_action.setChecked(load_theme_mode() == "dark")
        self._theme_action.triggered.connect(self._toggle_theme)
        m_view.addAction(self._theme_action)

        m_pdf = mb.addMenu("&PDF")
        act_merge = QAction("PDFs zusammenführen / teilen…", self)
        act_merge.triggered.connect(self._pdf_tools)
        m_pdf.addAction(act_merge)
        act_wm = QAction("Wasserzeichen / Seitennummern…", self)
        act_wm.triggered.connect(self._watermark_tools)
        m_pdf.addAction(act_wm)
        act_cmp = QAction("Zwei PDFs vergleichen…", self)
        act_cmp.triggered.connect(self._compare_pdfs)
        m_pdf.addAction(act_cmp)
        act_pw = QAction("Passwort setzen…", self)
        act_pw.triggered.connect(self._set_pdf_password)
        m_pdf.addAction(act_pw)
        act_compress = QAction("Bildkompression (Seiten neu)…", self)
        act_compress.triggered.connect(self._compress_pdf_images)
        m_pdf.addAction(act_compress)
        act_meta = QAction("Metadaten bearbeiten…", self)
        act_meta.triggered.connect(self._edit_pdf_metadata)
        m_pdf.addAction(act_meta)
        act_psize = QAction("Seitengröße / Zuschneiden…", self)
        act_psize.triggered.connect(self._pdf_page_size)
        m_pdf.addAction(act_psize)
        m_pdf.addSeparator()
        for title, slot in [
            ("Annotationen speichern (Sidecar)", lambda: self.pdf_view.save_annotations()),
            ("Annotationen speichern unter…", lambda: self.pdf_view.save_annotations_as()),
            ("Annotationen laden", lambda: self.pdf_view.reload_annotations()),
        ]:
            a = QAction(title, self)
            a.triggered.connect(slot)
            m_pdf.addAction(a)
        m_pdf.addSeparator()
        for title, slot in [
            ("Seite drehen 90° ⟳", lambda: self.pdf_view.rotate_current(90)),
            ("Seite drehen −90° ⟲", lambda: self.pdf_view.rotate_current(-90)),
            ("Leere Seite einfügen", lambda: self.pdf_view.insert_blank_after_current()),
            ("Seite duplizieren", lambda: self.pdf_view.duplicate_current()),
            ("Seite löschen…", lambda: self.pdf_view.delete_current()),
            ("Seiten neu anordnen…", lambda: self.pdf_view.reorder_dialog()),
            ("Seite als Bild exportieren…", lambda: self.pdf_view.extract_page_as_image()),
            ("Seiten als Bilder exportieren…", lambda: self.pdf_view.export_pages_as_images()),
            ("Bild als neue Seite…", lambda: self.pdf_view.insert_image_page()),
            ("Seite drucken…", lambda: self.pdf_view.print_current_page()),
        ]:
            a = QAction(title, self)
            a.triggered.connect(slot)
            m_pdf.addAction(a)
        m_pdf.addSeparator()
        for title, slot in [
            ("PDF-Text → Overlay…", lambda: self.pdf_view.import_text_overlays()),
            ("Text-Overlays einbrennen…", lambda: self.pdf_view.bake_overlays()),
            ("Schwärzung einbrennen…", lambda: self.pdf_view.bake_redactions()),
            ("Schwärzungs-Annotationen löschen…", lambda: self.pdf_view.clear_redactions()),
            ("Signaturfeld setzen…", lambda: self.pdf_view.place_signature_field()),
            ("Signatur (Bild) einfügen…", lambda: self.pdf_view.insert_signature_image()),
        ]:
            a = QAction(title, self)
            a.triggered.connect(slot)
            m_pdf.addAction(a)

        m_ins = mb.addMenu("&Einfügen")
        a = QAction("Textrahmen", self)
        a.triggered.connect(self._add_text_frame)
        m_ins.addAction(a)
        a = QAction("Verketteten Textrahmen…", self)
        a.triggered.connect(self._add_chained_frame)
        m_ins.addAction(a)
        a = QAction("Bild einfügen…", self)
        a.triggered.connect(self._insert_image)
        m_ins.addAction(a)

        m_extra = mb.addMenu("E&xtras")
        a = QAction("Einstellungen…", self)
        a.triggered.connect(self._settings)
        m_extra.addAction(a)
        m_extra.addSeparator()
        a = QAction("Batch-Konvertierung (Ordner)…", self)
        a.triggered.connect(self._batch_convert)
        m_extra.addAction(a)
        a = QAction("OCR (Bild/PDF-Seite)…", self)
        a.triggered.connect(self._run_ocr)
        m_extra.addAction(a)
        a = QAction("Formulargenerator…", self)
        a.triggered.connect(self._forms)
        m_extra.addAction(a)
        m_extra.addSeparator()
        for key, title in [
            ("ki", "KI-Assistent (geplant)"),
            ("cloud", "Cloud-Sync (geplant)"),
            ("stylus", "Stylus / Palm Rejection (geplant)"),
            ("shapes_ai", "Intelligente Formerkennung (geplant)"),
            ("extrude3d", "3D-Extrusion (geplant)"),
            ("varfonts", "Variable Fonts (geplant)"),
            ("envelope", "Envelope Distort (geplant)"),
            ("esign", "E-Signatur (geplant)"),
        ]:
            a = QAction(title, self)
            a.triggered.connect(lambda checked=False, k=key: show_planned(self, k))
            m_extra.addAction(a)

        m_help = mb.addMenu("&Hilfe")
        a = QAction("Tastaturhilfe…", self)
        a.setShortcut(QKeySequence("F1"))
        a.triggered.connect(lambda: KeyboardHelpDialog(self).exec())
        m_help.addAction(a)
        a = QAction("Hilfe…", self)
        a.triggered.connect(lambda: HelpDialog(self).exec())
        m_help.addAction(a)
        m_help.addSeparator()
        a = QAction("Auf Updates prüfen…", self)
        a.triggered.connect(lambda: self._check_updates(silent=False))
        m_help.addAction(a)
        a = QAction("Lizenz…", self)
        a.triggered.connect(self._license)
        m_help.addAction(a)
        a = QAction("Info…", self)
        a.triggered.connect(lambda: AboutDialog(self).exec())
        m_help.addAction(a)

    def _refresh_recent(self):
        files = recent_mod.load_recent()
        self.sidebar.set_recent(files)
        if self._recent_menu is None:
            return
        self._recent_menu.clear()
        if not files:
            empty = QAction("(keine)", self)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)
        else:
            for path in files:
                a = QAction(Path(path).name, self)
                a.setToolTip(path)
                a.triggered.connect(lambda checked=False, p=path: self.open_path(p))
                self._recent_menu.addAction(a)
            self._recent_menu.addSeparator()
            clear = QAction("Liste leeren", self)
            clear.triggered.connect(self._clear_recent)
            self._recent_menu.addAction(clear)

    def _refresh_recent_searches(self):
        try:
            queries = recent_searches_mod.load_recent_searches()
            self.sidebar.set_recent_searches(queries)
        except Exception:
            pass

    def _remember_search(self, query: str):
        q = (query or "").strip()
        if not q:
            return
        try:
            recent_searches_mod.add_recent_search(q)
            self._refresh_recent_searches()
            self.sidebar.set_search_text(q)
        except Exception:
            pass

    def _clear_recent(self):
        recent_mod.clear_recent()
        self._refresh_recent()
        self._set_status("Zuletzt geöffnet geleert")

    def _remember_path(self, path: str | Path):
        try:
            recent_mod.add_recent(path)
            self._refresh_recent()
        except Exception:
            pass

    def _set_status(self, msg: str):
        self.statusBar().showMessage(msg, 5000)

    def _update_doc_status(self):
        """Statusleiste: Dateiname, Seite x/y, Zoom %."""
        name = "—"
        page_txt = "Seite —"
        zoom_txt = "— %"
        if self.doc and self.doc.path:
            name = Path(self.doc.path).name
        elif self.pdf_view.pdf_path:
            name = self.pdf_view.pdf_path.name
        if self.pdf_view.pdf_path and self.pdf_view.page_count > 0:
            page_txt = f"Seite {self.pdf_view.page_index + 1}/{self.pdf_view.page_count}"
            zoom_txt = f"{int(round(self.pdf_view.scale * 100))} %"
        elif self.doc and self.doc.path:
            page_txt = "Editor"
            zoom_txt = "—"
        self.file_status_label.setText(name)
        self.file_status_label.setToolTip(str(self.doc.path) if self.doc and self.doc.path else name)
        self.page_status_label.setText(page_txt)
        self.zoom_status_label.setText(zoom_txt)

    def _on_pdf_zoom_changed(self, scale: float):
        self.zoom_status_label.setText(f"{int(round(float(scale) * 100))} %")
        if self.pdf_view.pdf_path and self.pdf_view.page_count > 0:
            self.page_status_label.setText(
                f"Seite {self.pdf_view.page_index + 1}/{self.pdf_view.page_count}"
            )

    def _delete_annotation(self):
        if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
            self.pdf_view.delete_annotation()
        else:
            self._set_status("Annotation löschen nur im PDF-Modus")

    def _sync_theme_menu(self):
        if self._theme_action is not None:
            dark = load_theme_mode() == "dark"
            self._theme_action.setChecked(dark)
            self._theme_action.setText("Helles Design" if dark else "Dunkles Design")

    def _toggle_theme(self):
        mode = toggle_theme(self)
        self._sync_theme_menu()
        self._set_status("Dunkles Design" if mode == "dark" else "Helles Design")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if path:
                self.open_path(path)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def _autosave_tick(self):
        if not self._autosave_enabled:
            return
        st = self.license_manager.status()
        if not st.allowed:
            return
        if not self.doc or not self.doc.dirty or not self.doc.path:
            return
        if self.doc.kind == DocKind.PDF:
            if self.pdf_view.store and self.pdf_view.store.dirty:
                try:
                    self.pdf_view.store.save(force=True)
                    self._set_status(f"Autosave: Annotationen ({self.doc.display_name})")
                except Exception:
                    pass
            return
        if self.doc.kind not in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            return
        self.doc.text = self.editor.toPlainText()
        try:
            save_document(self.doc)
            self.doc.dirty = False
            self._set_status(f"Autosave: {self.doc.display_name}")
        except Exception:
            pass

    def _update_license_status(self):
        st = self.license_manager.status()
        self.version_label.setText(f"v{__version__}")
        if st.mode == "licensed":
            who = f" · {st.email}" if st.email else ""
            text = f"Lizenz: Aktiviert{who} · noch {st.days_remaining} Tag(e)"
            style = "color: #1B7A3D; font-weight: 600; padding-right: 6px;"
        elif st.mode == "trial":
            text = f"Lizenz: Testversion · noch {st.days_remaining} Tag(e) — Hilfe → Lizenz"
            style = "color: #B9770E; font-weight: 600; padding-right: 6px;"
        else:
            text = "Lizenz: Abgelaufen — Hilfe → Lizenz · ame@sellerbach.de"
            style = "color: #C0392B; font-weight: 700; padding-right: 6px;"
        self.license_label.setText(text)
        self.license_label.setStyleSheet(style)
        self.license_label.setToolTip(st.message)
        if not st.allowed:
            QMessageBox.warning(
                self,
                "Lizenz abgelaufen",
                st.message + "\n\nDie App bleibt geöffnet, Speichern kann eingeschränkt sein.",
            )

    def _on_text_changed(self):
        if self.doc and self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            self.doc.text = self.editor.toPlainText()
            self.doc.dirty = True

    def _on_pdf_document_changed(self):
        self._update_doc_status()
        if self.pdf_view.pdf_path:
            self._refresh_thumbs()
        else:
            self.sidebar.clear_thumbs()
            self.sidebar.clear_annotations()

    def _focus_search(self):
        self.sidebar.setVisible(True)
        le = self.sidebar.search.lineEdit()
        if le is not None:
            le.setFocus()
            le.selectAll()
        else:
            self.sidebar.search.setFocus()

    def _undo(self):
        if self.stack.currentWidget() is self.pdf_view:
            self.pdf_view.undo_annotation()
        else:
            self.editor.undo()

    def _redo(self):
        if self.stack.currentWidget() is self.pdf_view:
            self.pdf_view.redo_annotation()
        else:
            self.editor.redo()

    def _zoom_in(self):
        if self.stack.currentWidget() is self.pdf_view:
            self.pdf_view.zoom_in()
        else:
            self._set_status("Zoom gilt für die PDF-Ansicht")

    def _zoom_out(self):
        if self.stack.currentWidget() is self.pdf_view:
            self.pdf_view.zoom_out()
        else:
            self._set_status("Zoom gilt für die PDF-Ansicht")

    def _fit_page(self):
        if self.stack.currentWidget() is self.pdf_view:
            self.pdf_view.fit_page()
        else:
            self._set_status("Seite einpassen: PDF öffnen")

    def _fit_width(self):
        if self.stack.currentWidget() is self.pdf_view:
            self.pdf_view.fit_width()
        else:
            self._set_status("Breite einpassen: PDF öffnen")

    def _zoom_100(self):
        if self.stack.currentWidget() is self.pdf_view:
            self.pdf_view.zoom_100()
        else:
            self._set_status("Zoom 100 %: PDF öffnen")

    def _print(self):
        try:
            if self.stack.currentWidget() is self.pdf_view:
                self.pdf_view.print_current_page()
                return
            if self.stack.currentWidget() is self.editor:
                from PySide6.QtPrintSupport import QPrintDialog, QPrinter

                printer = QPrinter(QPrinter.HighResolution)
                printer.setDocName(self.doc.display_name if self.doc else "InstantLens Doc")
                dlg = QPrintDialog(printer, self)
                dlg.setWindowTitle("Editor drucken")
                if dlg.exec() == QPrintDialog.Accepted:
                    self.editor.print_(printer)
                    self._set_status("Editor gedruckt")
                return
            QMessageBox.information(
                self,
                "Drucken",
                "Drucken ist für Texteditor und PDF-Seite verfügbar.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Drucken", f"Druck fehlgeschlagen:\n{e}")

    def _on_search(self, query: str):
        if not query:
            self._set_status("Leere Suche")
            return
        self._remember_search(query)
        if self.sidebar.fulltext_mode:
            paths = self.sidebar.document_paths()
            if self.doc and self.doc.path and str(self.doc.path) not in paths:
                paths.append(str(self.doc.path))
            if not paths:
                self._set_status("Keine Dokumente in der Liste für Volltextsuche")
                return
            hits = fulltext_mod.search_paths(paths, query)
            if not hits:
                self.sidebar.set_marks([f"Keine Treffer für „{query}“"])
                self._set_status(f"0 Treffer in {len(paths)} Dokument(en)")
                return
            lines = []
            payloads = []
            for h in hits[:80]:
                loc = f"S.{h.page + 1}" if h.page is not None else f"Z.{h.line}"
                lines.append(f"{Path(h.path).name} {loc}: {h.snippet[:60]}")
                payloads.append((h.path, h.page))
            self.sidebar.set_marks(lines, payloads)
            self._set_status(f"{len(hits)} Treffer in {len(paths)} Dokument(en)")
            return
        if self.stack.currentWidget() is self.editor:
            n = self.editor.find_and_highlight(query)
            self._set_status(f"{n} Treffer für „{query}“")
            lines = [f"Suche: {query} → {n} Treffer"] + self._editor_marks
            self.sidebar.set_marks(lines)
            return
        if self.stack.currentWidget() is self.pdf_view:
            hits = []
            if self.pdf_view.store:
                for a in self.pdf_view.store.annotations:
                    blob = f"{a.type.value} {a.text}".lower()
                    if query.lower() in blob:
                        hits.append(a)
            pdf_path = self.pdf_view.pdf_path
            page_hits: list[tuple[int, str]] = []
            if pdf_path:
                for page_idx, blob in fulltext_mod.extract_document_text(pdf_path):
                    if page_idx is None:
                        continue
                    if query.lower() in blob.lower():
                        page_hits.append((page_idx, blob))
            # Aktuelle Seite: Texttreffer highlighten
            n_page = self.pdf_view.highlight_search(query)
            if page_hits:
                for pi, blob in page_hits:
                    for line in blob.splitlines():
                        if query.lower() in line.lower():
                            hits.append(("page", pi, line.strip()[:80]))
                            break
            if hits or n_page:
                lines = []
                payloads = []
                if n_page:
                    lines.append(f"Seite {self.pdf_view.page_index + 1}: {n_page} Texttreffer (hervorgehoben)")
                    payloads.append(("__search__", self.pdf_view.page_index))
                for h in hits:
                    if isinstance(h, tuple) and h[0] == "page":
                        _, pi, snip = h
                        lines.append(f"S.{pi + 1} Text: {snip}")
                        payloads.append((str(pdf_path), pi))
                    else:
                        lines.append(f"S{h.page + 1}: {h.type.value} {h.text[:40]}")
                        payloads.append(h)
                self.sidebar.set_marks(lines, payloads)
                self._set_status(
                    f"{n_page} Treffer auf Seite {self.pdf_view.page_index + 1} · "
                    f"{len(lines)} Einträge (PDF-Text/Annotationen)"
                )
            else:
                self.pdf_view.clear_search_highlights()
                self._set_status("Kein Treffer — „Alle Docs“ oder OCR für gescannte PDFs")
            return
        self._set_status("Suche: Editor oder PDF öffnen")

    def _on_search_next(self):
        q = self.sidebar.search_text()
        if self.stack.currentWidget() is self.editor:
            if self.editor.find_next(q or None):
                self._set_status("Nächster Treffer")
            else:
                self._set_status("Keine weiteren Treffer")
            return
        if self.stack.currentWidget() is self.pdf_view:
            if not q:
                self._set_status("Keine Suche aktiv")
                return
            if self.pdf_view._search_query != q:
                n = self.pdf_view.highlight_search(q)
                if n:
                    self._set_status(f"{n} Treffer auf aktueller Seite (1/{n})")
                else:
                    self._set_status("Kein Texttreffer auf aktueller Seite")
                return
            if self.pdf_view.search_next():
                i = self.pdf_view._search_index + 1
                n = self.pdf_view.search_hit_count()
                self._set_status(f"Treffer {i}/{n} auf Seite {self.pdf_view.page_index + 1}")
            else:
                self._set_status("Keine weiteren Treffer auf aktueller Seite")
            return
        self._set_status("Suche: Editor oder PDF öffnen")

    def _mark_selection(self):
        if self.stack.currentWidget() is not self.editor:
            QMessageBox.information(self, "Markieren", "Markieren funktioniert im Texteditor.")
            return
        if not self.editor.highlight_selection():
            QMessageBox.information(self, "Markieren", "Bitte Text auswählen.")
            return
        snip = self.editor.selected_snippet() or "Auswahl"
        label = f"Markierung: {snip}"
        self._editor_marks.append(label)
        self.sidebar.append_mark(label)
        self._set_status("Auswahl markiert")

    def _clear_editor_marks(self):
        self.editor.clear_extra_selections()
        self._editor_marks.clear()
        if self.stack.currentWidget() is self.pdf_view:
            self._refresh_pdf_marks()
        else:
            self.sidebar.set_marks([])
        self._set_status("Markierungen gelöscht")

    def _refresh_pdf_marks(self):
        if self.stack.currentWidget() is not self.pdf_view:
            return
        pairs = self.pdf_view.annotation_summaries()
        self.sidebar.set_annotations([p[0] for p in pairs], [p[1] for p in pairs])

    def _on_annotation_activated(self, payload):
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if self.pdf_view.focus_annotation(payload):
            return
        if payload is not None and hasattr(payload, "page"):
            self.pdf_view.goto_page(int(payload.page))
            self._set_status(f"Annotation Seite {payload.page + 1}")

    def _on_mark_activated(self, index: int):
        payload = self.sidebar.mark_payload(index)
        if isinstance(payload, tuple) and len(payload) == 2:
            self._on_fulltext_hit(str(payload[0]), payload[1])
            return
        if payload is not None and hasattr(payload, "page"):
            self.stack.setCurrentWidget(self.pdf_view)
            self.pdf_view.focus_annotation(payload)
            self._set_status(f"Annotation Seite {payload.page + 1}")

    def _on_fulltext_hit(self, path: str, page):
        self.open_path(path)
        if page is not None and self.stack.currentWidget() is self.pdf_view:
            self.pdf_view.goto_page(int(page))
            self._set_status(f"Treffer: {Path(path).name} Seite {int(page) + 1}")

    def _on_outline_jump(self, page_index: int):
        if self.stack.currentWidget() is not self.pdf_view:
            self._set_status("Lesezeichen: PDF öffnen")
            return
        self.pdf_view.goto_page(page_index)
        self._set_status(f"Lesezeichen → Seite {page_index + 1}")

    def _refresh_outline(self, path: str | Path):
        try:
            items = extract_outline(path)
        except Exception:
            items = []
        self.sidebar.set_outline(items)

    def _refresh_thumbs(self):
        if not self.pdf_view.pdf_path:
            self.sidebar.clear_thumbs()
            return
        try:
            imgs = self.pdf_view.render_thumbnails()
            self.sidebar.set_page_thumbs(imgs, current=self.pdf_view.page_index)
        except Exception as e:
            _log.warning("Thumbnails: %s", e)
            self.sidebar.clear_thumbs()

    def _on_thumb_jump(self, page_index: int):
        if self.stack.currentWidget() is not self.pdf_view:
            return
        self.pdf_view.goto_page(page_index)

    def _on_thumbs_reordered(self, order: list):
        if self.stack.currentWidget() is not self.pdf_view:
            return
        if not self.pdf_view.pdf_path:
            return
        if self.pdf_view.apply_page_order([int(i) for i in order]):
            self._refresh_thumbs()
            self._update_doc_status()

    def _on_pdf_page_changed(self, page_index: int):
        self.sidebar.select_thumb(page_index)
        self._update_doc_status()
    def _set_pdf_password(self):
        if not self.pdf_view.pdf_path:
            QMessageBox.information(self, "Passwort", "Bitte zuerst ein PDF öffnen.")
            return
        dlg = SetPasswordDialog(self, pdf_name=self.pdf_view.pdf_path.name)
        if not dlg.exec():
            return
        vals = dlg.values()
        try:
            from ild_pdf import set_password
            from ild_pdf.render import clear_render_cache

            out = self.pdf_view.pdf_path.with_name(
                f"{self.pdf_view.pdf_path.stem}_locked.pdf"
            )
            set_password(self.pdf_view.pdf_path, out_path=out, **vals)
            clear_render_cache(self.pdf_view.pdf_path)
            self._set_status(f"Passwort gesetzt → {out.name}")
            QMessageBox.information(
                self,
                "Passwort",
                f"Geschütztes PDF gespeichert:\n{out}\n\n"
                "Öffnen Sie die Datei und geben Sie das User-Passwort ein.",
            )
            _log.info("PDF encrypted: %s", out)
        except Exception as e:
            _log.exception("Passwort setzen fehlgeschlagen")
            QMessageBox.warning(self, "Passwort", str(e))

    def _compress_pdf_images(self):
        if not self.pdf_view.pdf_path:
            QMessageBox.information(self, "Kompression", "Bitte zuerst ein PDF öffnen.")
            return
        dlg = CompressPdfDialog(self)
        if not dlg.exec():
            return
        vals = dlg.values()
        try:
            from ild_pdf import compress_pdf_as_images
            from ild_pdf.render import clear_render_cache

            out = self.pdf_view.pdf_path.with_name(
                f"{self.pdf_view.pdf_path.stem}_compressed.pdf"
            )
            compress_pdf_as_images(
                self.pdf_view.pdf_path,
                out_path=out,
                jpeg_quality=vals["jpeg_quality"],
                max_edge=vals["max_edge"],
                render_scale=1.5,
            )
            clear_render_cache(self.pdf_view.pdf_path)
            self._set_status(f"Komprimiert → {out.name}")
            QMessageBox.information(self, "Kompression", f"Gespeichert:\n{out}")
            _log.info("PDF compressed: %s", out)
        except Exception as e:
            _log.exception("Kompression fehlgeschlagen")
            QMessageBox.warning(self, "Kompression", str(e))

    def _settings(self):
        if SettingsDialog(self).exec():
            sync_from_settings()
            self._sync_theme_menu()
            self._autosave_timer.setInterval(get_autosave_interval_sec() * 1000)
            self.pdf_view.apply_settings_colors()
            self._set_status(
                f"Einstellungen gespeichert · Autosave {get_autosave_interval_sec()}s"
            )

    def _edit_pdf_metadata(self):
        if not self.pdf_view.pdf_path:
            QMessageBox.information(self, "Metadaten", "Bitte zuerst ein PDF öffnen.")
            return
        if MetadataDialog(self.pdf_view.pdf_path, self).exec():
            self._set_status("PDF-Metadaten gespeichert")

    def _pdf_page_size(self):
        if not self.pdf_view.pdf_path:
            QMessageBox.information(self, "Seitengröße", "Bitte zuerst ein PDF öffnen.")
            return
        if PageSizeDialog(self.pdf_view.pdf_path, self.pdf_view.page_index, self).exec():
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_view.pdf_path)
            self.pdf_view.refresh()
            self._set_status("Seitengröße/Crop aktualisiert")

    def _check_updates(self, *, silent: bool = False):
        from instantlensdoc.core.i18n import get_lang
        from instantlensdoc.core.update_check import check_for_updates

        result = check_for_updates(allow_network=True)
        msg = result.message(get_lang())
        self._set_status(msg)
        if silent and not result.newer_available:
            return
        QMessageBox.information(self, "Update-Check", msg)

    def _batch_convert(self):
        BatchConvertDialog(self).exec()

    def _pdf_tools(self):
        initial = str(self.pdf_view.pdf_path) if self.pdf_view.pdf_path else None
        PdfToolsDialog(self, initial_pdf=initial).exec()

    def _watermark_tools(self):
        initial = str(self.pdf_view.pdf_path) if self.pdf_view.pdf_path else None
        dlg = WatermarkDialog(
            self,
            pdf_path=initial,
            page_index=self.pdf_view.page_index,
            page_count=self.pdf_view.page_count or 1,
        )
        dlg.exec()
        if dlg.result_path and self.pdf_view.pdf_path:
            # Neu laden wenn gleiches/verwandtes PDF
            try:
                from ild_pdf.render import clear_render_cache

                clear_render_cache(self.pdf_view.pdf_path)
                self.pdf_view.load(self.pdf_view.pdf_path)
                self._set_status(f"PDF aktualisiert: {dlg.result_path}")
            except Exception:
                pass

    def _compare_pdfs(self):
        left = str(self.pdf_view.pdf_path) if self.pdf_view.pdf_path else None
        PdfCompareDialog(self, left_pdf=left).exec()

    def _paste_clipboard_image(self):
        if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
            if self.pdf_view.paste_clipboard_image():
                return
        if self.doc and self.doc.path:
            self.editor.set_paste_image_dir(Path(self.doc.path).parent)
        if self.editor.paste_clipboard_image():
            self.stack.setCurrentWidget(self.editor)
            self._set_status("Bild aus Zwischenablage in Editor eingefügt")
            return
        QMessageBox.information(
            self,
            "Einfügen",
            "Kein Bild in der Zwischenablage.\n"
            "Strg+V im PDF-Viewer fügt ebenfalls Bilder ein.",
        )

    def new_doc(self):
        self.doc = Document(kind=DocKind.TEXT, title="Unbenannt")
        self.editor.setPlainText("")
        self.editor.clear_extra_selections()
        self._editor_marks.clear()
        self.sidebar.set_marks([])
        self.sidebar.clear_annotations()
        self.stack.setCurrentWidget(self.editor)
        self.setWindowTitle(f"{DISPLAY_NAME} — Unbenannt")
        self._update_doc_status()
        self._set_status("Neues Dokument")

    def open_dialog(self):
        start = ""
        d = get_default_open_dir()
        if d:
            start = str(d)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Öffnen",
            start,
            "Dokumente (*.txt *.md *.html *.htm *.docx *.pdf *.png *.jpg *.jpeg);;Alle (*.*)",
        )
        if path:
            self.open_path(path)

    def open_path(self, path: str):
        try:
            self.doc = open_document(path)
        except Exception as e:
            QMessageBox.critical(self, "Öffnen", f"Datei konnte nicht geöffnet werden:\n{e}")
            return

        self.sidebar.add_document(path)
        self._remember_path(path)
        self.setWindowTitle(f"{DISPLAY_NAME} — {self.doc.display_name}")

        try:
            if self.doc.kind == DocKind.PDF:
                self.stack.setCurrentWidget(self.pdf_view)
                if not self.pdf_view.load(path):
                    self.sidebar.clear_thumbs()
                    return
                self._refresh_pdf_marks()
                self._refresh_outline(path)
                self._refresh_thumbs()
                _log.info("PDF geöffnet: %s", path)
            elif self.doc.kind == DocKind.IMAGE:
                from PySide6.QtGui import QPixmap

                self.stack.setCurrentWidget(self.image_label)
                pm = QPixmap(path)
                self.image_label.setPixmap(
                    pm.scaled(900, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.sidebar.set_marks([f"Bild: {Path(path).name}"])
                self.sidebar.clear_thumbs()
                self.sidebar.clear_annotations()
            else:
                self.stack.setCurrentWidget(self.editor)
                self.editor.blockSignals(True)
                self.editor.setPlainText(self.doc.text)
                self.editor.blockSignals(False)
                self.editor.clear_extra_selections()
                self._editor_marks.clear()
                self.sidebar.set_marks([])
                self.sidebar.clear_thumbs()
                self.sidebar.clear_annotations()
            self._update_doc_status()
            self._set_status(f"Geöffnet: {path}")
        except Exception as e:
            _log.exception("Anzeige fehlgeschlagen: %s", path)
            QMessageBox.critical(self, "Öffnen", f"Anzeige fehlgeschlagen:\n{e}")

    def save_doc(self):
        st = self.license_manager.status()
        if not st.allowed:
            QMessageBox.warning(self, "Lizenz", "Speichern nicht möglich — Lizenz/Trial abgelaufen.")
            return
        if not self.doc:
            return
        if self.doc.kind == DocKind.PDF:
            if self.pdf_view.save_annotations():
                side = (
                    self.pdf_view.store.sidecar_path.name
                    if self.pdf_view.store
                    else "*.ildann.json"
                )
                self._set_status(f"PDF-Annotationen (Sidecar) gespeichert: {side}")
            return
        if not self.doc.path:
            self.save_as()
            return
        if self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            self.doc.text = self.editor.toPlainText()
        try:
            save_document(self.doc)
            self._remember_path(self.doc.path)
            self._set_status(f"Gespeichert: {self.doc.path}")
        except Exception as e:
            QMessageBox.critical(self, "Speichern", f"Speichern fehlgeschlagen:\n{e}")

    def save_as(self):
        if not self.doc:
            return
        if self.doc.kind == DocKind.PDF:
            # Klar: Speichern-unter bei PDF = Sidecar-Annotationen, nicht die PDF-Datei
            if self.pdf_view.save_annotations_as():
                self._set_status("Annotation-Sidecar gespeichert unter…")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Speichern unter",
            self.doc.display_name,
            "Text (*.txt);;Markdown (*.md);;HTML (*.html);;DOCX (*.docx);;Alle (*.*)",
        )
        if not path:
            return
        if self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            self.doc.text = self.editor.toPlainText()
        try:
            save_document(self.doc, Path(path))
            self.sidebar.add_document(path)
            self._remember_path(path)
            self.setWindowTitle(f"{DISPLAY_NAME} — {self.doc.display_name}")
            self._set_status(f"Gespeichert: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Speichern", f"Speichern fehlgeschlagen:\n{e}")

    def _export_editor(self, fmt: str):
        """Editor-Inhalt nach HTML / DOCX / PDF exportieren."""
        text = ""
        title = "InstantLens Doc"
        if self.stack.currentWidget() is self.editor:
            text = self.editor.toPlainText()
            if self.doc:
                title = self.doc.title or self.doc.display_name
        elif self.doc and self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            text = self.doc.text or self.editor.toPlainText()
            title = self.doc.display_name
        else:
            QMessageBox.information(
                self,
                "Export",
                "Export gilt für den Texteditor.\nBitte TXT/MD/HTML/DOCX öffnen oder Text eingeben.",
            )
            return
        filters = {
            "html": ("HTML (*.html)", ".html"),
            "docx": ("DOCX (*.docx)", ".docx"),
            "pdf": ("PDF (*.pdf)", ".pdf"),
        }
        filt, ext = filters[fmt]
        default_name = (self.doc.display_name if self.doc else "export") + ext
        if "." in default_name and not default_name.lower().endswith(ext):
            default_name = Path(default_name).stem + ext
        last_dir = get_last_export_dir()
        start = str((last_dir / default_name) if last_dir else Path(default_name))
        path, _ = QFileDialog.getSaveFileName(self, f"Export {fmt.upper()}", start, filt)
        if not path:
            return
        try:
            from instantlensdoc.core import export as exp

            if fmt == "html":
                exp.export_html(text, path, title=title)
            elif fmt == "docx":
                exp.export_docx(text, path, title=title)
            else:
                exp.export_pdf(text, path, title=title)
            set_last_export_dir(path)
            self._set_status(f"Exportiert: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export", f"Export fehlgeschlagen:\n{e}")

    def _add_text_frame(self):
        text = self.editor.toPlainText() if self.stack.currentWidget() is self.editor else ""
        frame = self.layout_doc.add_text_frame(text=text)
        flowed = self.layout_doc.flow_text(text or "Neuer Textrahmen", frame)
        if self.stack.currentWidget() is self.editor:
            self.editor.appendPlainText(f"\n--- Textrahmen {frame.id} ---\n{flowed}")
        self._set_status(f"Textrahmen {frame.id} hinzugefügt")

    def _add_chained_frame(self):
        """Verkettete Textrahmen: Overflow fließt in den nächsten Rahmen."""
        source = self.editor.toPlainText() if self.stack.currentWidget() is self.editor else ""
        if not source.strip():
            source = (
                "Dies ist ein Beispieltext für verkettete Textrahmen in InstantLens Doc. "
                "Der Text fließt automatisch in den nächsten Rahmen, sobald die Kapazität "
                "des ersten Rahmens erreicht ist. Weitere Wörter landen im Folgeahmen. "
            ) * 4
        # Zwei schmale Rahmen verkettet
        f1 = self.layout_doc.add_text_frame(
            text="", x=40, y=40, width=240, height=120, font_size=12
        )
        f2 = self.layout_doc.chain_new_frame(f1, x=40, y=180, width=240, height=120)
        filled = self.layout_doc.flow_text_chain(source, f1)
        overflow = filled.pop("__overflow__", "")
        if self.stack.currentWidget() is self.editor:
            lines = [
                f"\n=== Verkettete Rahmen {f1.id} → {f2.id} ===",
                f"--- Rahmen {f1.id} ---",
                f1.text,
                f"--- Rahmen {f2.id} (Fortsetzung) ---",
                f2.text,
            ]
            if overflow:
                lines.append(f"--- Overflow (kein weiterer Rahmen) ---\n{overflow[:400]}")
            self.editor.appendPlainText("\n".join(lines))
        self._set_status(f"Verkettung {f1.id}→{f2.id} ({len(filled)} Rahmen gefüllt)")

    def _insert_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Bild einfügen", "", "Bilder (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return
        frame = self.layout_doc.add_image(path)
        if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
            from PySide6.QtWidgets import QInputDialog

            choice, ok = QInputDialog.getItem(
                self,
                "Bild einfügen",
                "Ziel:",
                ["Layout-Rahmen (Editor-Hinweis)", "Als neue PDF-Seite", "Als Stempel-Annotation"],
                0,
                False,
            )
            if ok and choice == "Als neue PDF-Seite":
                try:
                    from ild_pdf import PdfDocument, insert_image_as_page

                    insert_image_as_page(self.pdf_view.pdf_path, path)
                    with PdfDocument(self.pdf_view.pdf_path) as doc:
                        self.pdf_view.page_count = len(doc)
                    self.pdf_view.page_index = self.pdf_view.page_count - 1
                    self.pdf_view.refresh()
                    self._set_status("Bild als PDF-Seite eingefügt")
                    return
                except Exception as e:
                    QMessageBox.warning(self, "Bild", str(e))
                    return
            if ok and choice == "Als Stempel-Annotation":
                try:
                    from ild_pdf import insert_image_stamp_overlay

                    insert_image_stamp_overlay(
                        self.pdf_view.pdf_path,
                        path,
                        page_index=self.pdf_view.page_index,
                    )
                    self.pdf_view.reload_annotations()
                    self._set_status("Bildstempel-Annotation gesetzt")
                    return
                except Exception as e:
                    QMessageBox.warning(self, "Bild", str(e))
                    return
        if self.stack.currentWidget() is self.editor:
            self.editor.appendPlainText(
                f"\n[Bild: {path} @ {frame.x},{frame.y} {frame.width}x{frame.height}]\n"
            )
        self._set_status(f"Bild eingefügt: {Path(path).name}")

    def _run_ocr(self):
        from PySide6.QtWidgets import QApplication, QDialog, QProgressDialog

        ok, msg = ocr_mod.tesseract_available()
        need_file = not (
            self.doc and self.doc.path and self.doc.kind in (DocKind.IMAGE, DocKind.PDF)
        )
        dlg = OcrDialog(
            self,
            need_file=need_file,
            default_label=Path(self.doc.path).name if self.doc and self.doc.path else "",
        )
        if dlg.exec() != QDialog.Accepted:
            return

        if not ok:
            QMessageBox.information(self, "OCR — Tesseract fehlt", msg)
            self._set_status("OCR nicht verfügbar")
            return

        lang = dlg.lang_code()
        mode = dlg.output_mode()
        prog = QProgressDialog("OCR läuft…", None, 0, 0, self)
        prog.setWindowTitle("OCR")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        prog.setValue(0)
        prog.show()
        QApplication.processEvents()
        try:
            if self.doc and self.doc.kind == DocKind.IMAGE and self.doc.path:
                source_label = Path(self.doc.path).name
                prog.setLabelText(f"OCR: {source_label}")
                QApplication.processEvents()
                result = ocr_mod.run_ocr(
                    self.doc.path,
                    lang=lang,
                    mode=mode,
                    out_dir=Path(self.doc.path).parent,
                    source_label=source_label,
                )
            elif self.doc and self.doc.kind == DocKind.PDF and self.doc.path:
                from ild_pdf import render_page

                source_label = f"{Path(self.doc.path).name} Seite {self.pdf_view.page_index + 1}"
                prog.setLabelText(f"OCR: {source_label}")
                QApplication.processEvents()
                img = render_page(self.doc.path, self.pdf_view.page_index, scale=2.0)
                result = ocr_mod.run_ocr(
                    img,
                    lang=lang,
                    mode=mode,
                    out_dir=Path(self.doc.path).parent,
                    source_label=source_label,
                )
            else:
                path = dlg.selected_path
                if not path:
                    path, _ = QFileDialog.getOpenFileName(
                        self, "Bild für OCR", "", "Bilder (*.png *.jpg *.jpeg *.tif *.tiff)"
                    )
                if not path:
                    return
                source_label = Path(path).name
                prog.setLabelText(f"OCR: {source_label}")
                QApplication.processEvents()
                result = ocr_mod.run_ocr(
                    path,
                    lang=lang,
                    mode=mode,
                    out_dir=Path(path).parent,
                    source_label=source_label,
                )
        except ocr_mod.OcrUnavailable as e:
            QMessageBox.information(self, "OCR — Tesseract fehlt", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "OCR", f"OCR fehlgeschlagen:\n{e}")
            return
        finally:
            prog.close()

        self.stack.setCurrentWidget(self.editor)
        self.editor.setPlainText(result.text)
        self.doc = Document(kind=DocKind.TEXT, title=f"OCR — {source_label}", text=result.text)
        self.setWindowTitle(f"{DISPLAY_NAME} — OCR — {source_label}")
        extra = ""
        if result.searchable_pdf:
            extra = f" · PDF {result.searchable_pdf.name}"
            if result.sidecar:
                extra += f" + {result.sidecar.name}"
        self._set_status(f"OCR ({result.lang}, {result.mode.value}){extra}")

    def _forms(self):
        try:
            FormBuilderDialog(self).exec()
        except Exception as e:
            QMessageBox.critical(self, "Formulare", f"Formulargenerator fehlgeschlagen:\n{e}")

    def _license(self):
        if LicenseDialog(self.license_manager, self).exec():
            self._update_license_status()
