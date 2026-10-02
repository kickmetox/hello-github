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
    QMenu,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QSystemTrayIcon,
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
from instantlensdoc.ui.editor import EditorPane
from instantlensdoc.ui.form_builder import FormBuilderDialog
from instantlensdoc.ui.attachments_dialog import AttachmentsDialog
from instantlensdoc.ui.help_dialog import AboutDialog, HelpDialog
from instantlensdoc.ui.license_dialog import LicenseDialog
from instantlensdoc.ui.ocr_dialog import OcrDialog
from instantlensdoc.ui.pdf_view import PdfViewer
from instantlensdoc.ui.sidebar import Sidebar
from instantlensdoc.core import fulltext as fulltext_mod
from instantlensdoc.core.app_settings import (
    dialog_start_dir,
    get_annotations_visible,
    get_autosave_interval_sec,
    get_default_open_dir,
    get_editor_markdown_preview,
    get_editor_soft_wrap,
    get_last_export_dir,
    get_minimize_to_tray,
    get_page_size_unit,
    get_pdf_thumbnail_scale,
    get_restore_session_on_start,
    get_update_check_on_start,
    get_window_geometry_b64,
    get_window_state_b64,
    remember_recent_dir,
    set_last_export_dir,
    set_window_geometry_b64,
    set_window_state_b64,
    toggle_page_size_unit,
)
from instantlensdoc.ui.batch_dialog import BatchConvertDialog
from instantlensdoc.ui.file_dialogs import confirm_overwrite_export
from instantlensdoc.ui.pdf_tools_dialog import PdfToolsDialog
from instantlensdoc.ui.watermark_dialog import WatermarkDialog
from instantlensdoc.ui.compare_dialog import PdfCompareDialog
from instantlensdoc.ui.settings_dialog import SettingsDialog
from instantlensdoc.ui.stubs import show_planned
from instantlensdoc.ui.theme import apply_theme, load_theme_mode, toggle_theme
from instantlensdoc.ui.keyboard_help import KeyboardHelpDialog
from instantlensdoc.ui.password_dialog import CompressPdfDialog, SetPasswordDialog
from instantlensdoc.ui.metadata_dialog import MetadataDialog
from instantlensdoc.ui.form_fields_dialog import FormFieldsDialog
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
        self._thumb_lazy_timer: QTimer | None = None
        self._thumb_lazy_queue: list[int] = []
        self._thumb_lazy_token: int | None = None
        self._tray: QSystemTrayIcon | None = None
        self._tray_menu: QMenu | None = None
        self._force_quit = False
        self._presentation_active = False
        self._presentation_prev: dict | None = None

        self.setAcceptDrops(True)
        self.setWindowTitle(self._app_title())
        self.resize(1200, 800)
        icon = QIcon()
        for p in icon_paths_for_qt():
            icon.addFile(str(p))
        if not icon.isNull():
            self.setWindowIcon(icon)

        self._build_ui()
        self._build_menus()
        self._restore_window_geometry()
        self.apply_tray_setting()
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

    def _restore_window_geometry(self) -> None:
        import base64

        from PySide6.QtCore import QByteArray

        geo = get_window_geometry_b64()
        state = get_window_state_b64()
        if geo:
            try:
                self.restoreGeometry(QByteArray(base64.b64decode(geo)))
            except Exception:
                pass
        if state:
            try:
                self.restoreState(QByteArray(base64.b64decode(state)))
            except Exception:
                pass

    def _save_window_geometry(self) -> None:
        import base64

        try:
            geo = bytes(self.saveGeometry())
            state = bytes(self.saveState())
            set_window_geometry_b64(base64.b64encode(geo).decode("ascii"))
            set_window_state_b64(base64.b64encode(state).decode("ascii"))
        except Exception:
            pass

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent

        if (
            event.type() == QEvent.WindowStateChange
            and self.isMinimized()
            and get_minimize_to_tray()
            and self._tray is not None
            and self._tray.isVisible()
        ):
            QTimer.singleShot(0, self.hide)
            event.accept()
            return
        super().changeEvent(event)

    def closeEvent(self, event):
        if self._presentation_active:
            self._exit_presentation()
        if not self._confirm_close_current(allow_discard=True, quitting=True):
            event.ignore()
            return
        try:
            self._save_window_geometry()
        except Exception:
            pass
        try:
            self._save_session()
        except Exception:
            pass
        if self._tray is not None:
            self._tray.hide()
        super().closeEvent(event)

    def apply_tray_setting(self) -> None:
        """System-Tray gemäß Einstellung ein-/ausschalten."""
        enabled = get_minimize_to_tray()
        if not enabled:
            if self._tray is not None:
                self._tray.hide()
                self._tray.setParent(None)
                self._tray.deleteLater()
                self._tray = None
                self._tray_menu = None
            return
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        if self._tray is None:
            icon = self.windowIcon()
            if icon.isNull():
                icon = QIcon()
                for p in icon_paths_for_qt():
                    icon.addFile(str(p))
            self._tray = QSystemTrayIcon(icon, self)
            menu = QMenu(self)
            act_show = QAction("Anzeigen", self)
            act_show.triggered.connect(self._tray_restore)
            menu.addAction(act_show)
            act_quit = QAction("Beenden", self)
            act_quit.triggered.connect(self._tray_quit)
            menu.addAction(act_quit)
            self._tray_menu = menu
            self._tray.setContextMenu(menu)
            self._tray.activated.connect(self._tray_activated)
        self._tray.setToolTip(f"{DISPLAY_NAME} v{__version__}")
        self._tray.show()

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._tray_restore()

    def _tray_restore(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _tray_quit(self):
        self._force_quit = True
        self.close()

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
        if not get_restore_session_on_start():
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
        self.sidebar.outline_add_requested.connect(self._outline_add)
        self.sidebar.outline_delete_requested.connect(self._outline_delete)
        self.sidebar.annotation_filter_changed.connect(lambda _t: None)
        self.sidebar.fulltext_hit_activated.connect(self._on_fulltext_hit)
        self.sidebar.page_thumb_activated.connect(self._on_thumb_jump)
        self.sidebar.pages_reordered.connect(self._on_thumbs_reordered)
        splitter.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.editor_pane = EditorPane()
        self.editor = self.editor_pane.editor
        self.editor.textChanged.connect(self._on_text_changed)
        self.pdf_view = PdfViewer()
        self.pdf_view.status.connect(self._set_status)
        self.pdf_view.annotations_changed.connect(self._refresh_pdf_marks)
        self.pdf_view.page_changed.connect(self._on_pdf_page_changed)
        self.pdf_view.zoom_changed.connect(self._on_pdf_zoom_changed)
        self.pdf_view.document_changed.connect(self._on_pdf_document_changed)
        self.pdf_view.grayscale_changed.connect(self._sync_grayscale_action)
        self.pdf_view.night_mode_changed.connect(self._sync_night_action)
        self.pdf_view.annotations_layer_changed.connect(self._sync_ann_layer_action)
        self.image_label = QLabel(alignment=Qt.AlignCenter)
        self.image_label.setText("Bildvorschau")
        self.stack.addWidget(self.editor_pane)  # 0
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
        self.size_status_label = QLabel("—")
        self.size_status_label.setStyleSheet("padding-right: 10px; color: #555;")
        self.size_status_label.setToolTip("Seitengröße — Klick wechselt mm ↔ inch")
        self.size_status_label.setCursor(Qt.PointingHandCursor)
        self.size_status_label.mousePressEvent = (  # type: ignore[method-assign]
            lambda _e: self._toggle_page_size_unit()
        )
        sb.addPermanentWidget(self.size_status_label)
        self.zoom_status_label = QLabel("— %")
        self.zoom_status_label.setStyleSheet("padding-right: 10px;")
        sb.addPermanentWidget(self.zoom_status_label)
        self.word_status_label = QLabel("— Wörter")
        self.word_status_label.setStyleSheet("padding-right: 10px;")
        self.word_status_label.setToolTip("Wörter / Zeichen (Editor)")
        sb.addPermanentWidget(self.word_status_label)
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
        act_save_all = QAction("Alles speichern", self)
        act_save_all.setShortcut(QKeySequence("Ctrl+Alt+Shift+S"))
        act_save_all.setToolTip("Aktuelles Dokument + Annotation-Sidecars aller offenen PDF-Tabs")
        act_save_all.triggered.connect(self.save_all_docs)
        m_file.addAction(act_save_all)

        act_save_as = QAction("Speichern unter…", self)
        act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_as.setToolTip(
            "Text: Dokument speichern unter… · PDF: Annotation-Sidecar speichern unter…"
        )
        act_save_as.triggered.connect(self.save_as)
        m_file.addAction(act_save_as)
        act_save_copy = QAction("Als Kopie speichern…", self)
        act_save_copy.setShortcut(QKeySequence("Ctrl+Alt+S"))
        act_save_copy.setToolTip("PDF: Datei (+ Sidecar) als Kopie; Editor: Speichern unter")
        act_save_copy.triggered.connect(self.save_as_copy)
        m_file.addAction(act_save_copy)
        m_file.addSeparator()
        act_close = QAction("Schließen", self)
        act_close.setShortcut(QKeySequence.Close)
        act_close.setToolTip("Aktuelles Dokument schließen (Speichern-Dialog bei Änderungen)")
        act_close.triggered.connect(self.close_current_tab)
        m_file.addAction(act_close)
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
        act_find_repl = QAction("Suchen und Ersetzen…", self)
        act_find_repl.setShortcut(QKeySequence("Ctrl+R"))
        act_find_repl.setToolTip("Find/Replace im Texteditor")
        act_find_repl.triggered.connect(self._find_replace)
        m_edit.addAction(act_find_repl)
        act_goto = QAction("Gehe zu Zeile…", self)
        act_goto.setShortcut(QKeySequence("Ctrl+G"))
        act_goto.setToolTip("Cursor auf Zeilennummer setzen")
        act_goto.triggered.connect(self._goto_line)
        m_edit.addAction(act_goto)
        act_dup_line = QAction("Zeile duplizieren", self)
        act_dup_line.setShortcut(QKeySequence("Ctrl+D"))
        act_dup_line.setToolTip("Aktuelle Zeile / Auswahl darunter duplizieren")
        act_dup_line.triggered.connect(self._duplicate_line)
        m_edit.addAction(act_dup_line)
        act_move_up = QAction("Zeile nach oben", self)
        act_move_up.setShortcut(QKeySequence("Alt+Up"))
        act_move_up.setToolTip("Aktuelle Zeile / Auswahl nach oben verschieben")
        act_move_up.triggered.connect(self._move_line_up)
        m_edit.addAction(act_move_up)
        act_move_down = QAction("Zeile nach unten", self)
        act_move_down.setShortcut(QKeySequence("Alt+Down"))
        act_move_down.setToolTip("Aktuelle Zeile / Auswahl nach unten verschieben")
        act_move_down.triggered.connect(self._move_line_down)
        m_edit.addAction(act_move_down)
        act_comment = QAction("Zeile kommentieren/auskommentieren", self)
        act_comment.setShortcut(QKeySequence("Ctrl+/"))
        act_comment.setToolTip("Kommentarpräfix # oder // je nach Dateityp umschalten")
        act_comment.triggered.connect(self._toggle_line_comment)
        m_edit.addAction(act_comment)
        act_mark = QAction("Auswahl markieren", self)
        act_mark.setShortcut(QKeySequence("Ctrl+H"))
        act_mark.triggered.connect(self._mark_selection)
        m_edit.addAction(act_mark)
        act_toggle_case = QAction("Groß-/Kleinschreibung umschalten", self)
        act_toggle_case.setShortcut(QKeySequence("Ctrl+Shift+U"))
        act_toggle_case.setToolTip("Auswahl: GROSS → klein → Titel → GROSS")
        act_toggle_case.triggered.connect(self._toggle_case_selection)
        m_edit.addAction(act_toggle_case)
        act_indent = QAction("Einrückung erhöhen", self)
        act_indent.setShortcut(QKeySequence("Ctrl+]"))
        act_indent.setToolTip("Zeilen/Block einrücken (auch Tab)")
        act_indent.triggered.connect(self._indent_selection)
        m_edit.addAction(act_indent)
        act_outdent = QAction("Einrückung verringern", self)
        act_outdent.setShortcut(QKeySequence("Ctrl+["))
        act_outdent.setToolTip("Zeilen/Block ausrücken (auch Shift+Tab)")
        act_outdent.triggered.connect(self._outdent_selection)
        m_edit.addAction(act_outdent)
        act_clear_marks = QAction("Markierungen löschen", self)
        act_clear_marks.triggered.connect(self._clear_editor_marks)
        m_edit.addAction(act_clear_marks)
        m_edit.addSeparator()
        act_del_ann = QAction("Annotation löschen", self)
        act_del_ann.setShortcut(QKeySequence.Delete)
        act_del_ann.setToolTip("Ausgewählte Annotation oder letzte auf der Seite")
        act_del_ann.triggered.connect(self._delete_annotation)
        m_edit.addAction(act_del_ann)
        act_edit_ann = QAction("Annotationstext bearbeiten…", self)
        act_edit_ann.setShortcut(QKeySequence("Ctrl+E"))
        act_edit_ann.setToolTip("Notiz/Kommentar/Overlay der Auswahl bearbeiten (auch Doppelklick)")
        act_edit_ann.triggered.connect(self._edit_annotation_text)
        m_edit.addAction(act_edit_ann)
        act_dup_ann = QAction("Annotation duplizieren", self)
        act_dup_ann.setShortcut(QKeySequence("Ctrl+Shift+D"))
        act_dup_ann.setToolTip("Ausgewählte Annotation kopieren (leicht versetzt)")
        act_dup_ann.triggered.connect(self._duplicate_annotation)
        m_edit.addAction(act_dup_ann)
        act_sel_all_ann = QAction("Alle Annotationen auf Seite auswählen", self)
        act_sel_all_ann.setShortcut(QKeySequence.SelectAll)  # Ctrl+A
        act_sel_all_ann.setToolTip(
            "PDF: alle Annotationen der Seite; Editor: gesamten Text auswählen"
        )
        act_sel_all_ann.triggered.connect(self._select_all_annotations_on_page)
        m_edit.addAction(act_sel_all_ann)

        m_view = mb.addMenu("&Ansicht")
        a = QAction("Seitenleiste", self)
        a.setCheckable(True)
        a.setChecked(True)
        a.toggled.connect(self.sidebar.setVisible)
        m_view.addAction(a)
        self._line_numbers_action = QAction("Zeilennummern", self)
        self._line_numbers_action.setCheckable(True)
        from instantlensdoc.core.app_settings import (
            get_editor_line_numbers,
            get_pdf_grayscale,
            get_pdf_night_mode,
        )

        self._line_numbers_action.setChecked(get_editor_line_numbers())
        self._line_numbers_action.setToolTip("Zeilennummern im Texteditor anzeigen")
        self._line_numbers_action.toggled.connect(self._toggle_line_numbers)
        m_view.addAction(self._line_numbers_action)
        self._md_preview_action = QAction("Markdown-Vorschau", self)
        self._md_preview_action.setCheckable(True)
        self._md_preview_action.setChecked(get_editor_markdown_preview())
        self._md_preview_action.setToolTip("Editor-Split: Markdown-Vorschau ein/aus")
        self._md_preview_action.setShortcut(QKeySequence("Ctrl+Shift+M"))
        self._md_preview_action.toggled.connect(self._toggle_markdown_preview)
        m_view.addAction(self._md_preview_action)
        self._soft_wrap_action = QAction("Soft-Wrap", self)
        self._soft_wrap_action.setCheckable(True)
        self._soft_wrap_action.setChecked(get_editor_soft_wrap())
        self._soft_wrap_action.setToolTip("Zeilenumbruch am Fensterrand im Texteditor")
        self._soft_wrap_action.setShortcut(QKeySequence("Ctrl+Shift+W"))
        self._soft_wrap_action.toggled.connect(self._toggle_soft_wrap)
        m_view.addAction(self._soft_wrap_action)
        self._special_chars_action = QAction("Sonderzeichen anzeigen", self)
        self._special_chars_action.setCheckable(True)
        from instantlensdoc.core.app_settings import get_editor_show_special_chars

        self._special_chars_action.setChecked(get_editor_show_special_chars())
        self._special_chars_action.setToolTip(
            "Tabs, Leerzeichen und Absatzenden im Editor sichtbar machen"
        )
        self._special_chars_action.setShortcut(QKeySequence("Ctrl+Shift+."))
        self._special_chars_action.toggled.connect(self._toggle_special_chars)
        m_view.addAction(self._special_chars_action)
        self._grayscale_action = QAction("PDF Graustufen", self)
        self._grayscale_action.setCheckable(True)
        self._grayscale_action.setChecked(get_pdf_grayscale())
        self._grayscale_action.setToolTip("PDF-Seiten in Graustufen rendern und exportieren")
        self._grayscale_action.toggled.connect(self._toggle_grayscale)
        m_view.addAction(self._grayscale_action)
        self._night_action = QAction("PDF Nachtmodus", self)
        self._night_action.setCheckable(True)
        self._night_action.setChecked(get_pdf_night_mode())
        self._night_action.setToolTip(
            "Dunkle Invert-Ansicht (nur Darstellung, nicht speichern/exportieren)"
        )
        self._night_action.toggled.connect(self._toggle_night_mode)
        m_view.addAction(self._night_action)
        self._ann_layer_action = QAction("Annotation-Layer", self)
        self._ann_layer_action.setCheckable(True)
        self._ann_layer_action.setChecked(get_annotations_visible())
        self._ann_layer_action.setToolTip("Annotationen auf der PDF-Seite ein-/ausblenden")
        self._ann_layer_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
        self._ann_layer_action.toggled.connect(self._toggle_ann_layer)
        m_view.addAction(self._ann_layer_action)
        act_size_unit = QAction("Seitengröße mm/inch umschalten", self)
        act_size_unit.setShortcut(QKeySequence("Ctrl+Alt+U"))
        act_size_unit.setToolTip("Einheit der PDF-Seitengröße in der Statusleiste (mm ↔ inch)")
        act_size_unit.triggered.connect(self._toggle_page_size_unit)
        m_view.addAction(act_size_unit)
        act_present = QAction("Präsentationsmodus", self)
        act_present.setShortcut(QKeySequence("F5"))
        act_present.setToolTip(
            "PDF Vollbild-Präsentation (Pfeiltasten/Leertaste weiter, Esc beendet)"
        )
        act_present.triggered.connect(self._toggle_presentation)
        m_view.addAction(act_present)
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
        act_fit_h = QAction("Höhe einpassen", self)
        act_fit_h.setShortcut(QKeySequence("Ctrl+8"))
        act_fit_h.setToolTip("Seitenhöhe an Viewport anpassen")
        act_fit_h.triggered.connect(self._fit_height)
        m_view.addAction(act_fit_h)
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
        act_extract = QAction("Seitenbereich extrahieren…", self)
        act_extract.setToolTip("Seiten von–bis in neues PDF")
        act_extract.triggered.connect(self._extract_page_range)
        m_pdf.addAction(act_extract)
        act_split_pages = QAction("Seiten als Einzel-PDFs…", self)
        act_split_pages.setToolTip("Jede Seite als eigene PDF-Datei in einen Ordner")
        act_split_pages.triggered.connect(self._split_into_single_page_pdfs)
        m_pdf.addAction(act_split_pages)
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
        act_forms = QAction("Formularfelder ausfüllen…", self)
        act_forms.setToolTip("Bestehende AcroForm-Felder lesen und schreiben")
        act_forms.triggered.connect(self._edit_pdf_form_fields)
        m_pdf.addAction(act_forms)
        act_attach = QAction("Anhänge…", self)
        act_attach.setToolTip("Eingebettete PDF-Anhänge auflisten und extrahieren")
        act_attach.triggered.connect(self._pdf_attachments)
        m_pdf.addAction(act_attach)
        act_psize = QAction("Seitengröße / Zuschneiden…", self)
        act_psize.triggered.connect(self._pdf_page_size)
        m_pdf.addAction(act_psize)
        m_pdf.addSeparator()
        for title, slot in [
            ("Annotationen speichern (Sidecar)", lambda: self.pdf_view.save_annotations()),
            ("Annotationen speichern unter…", lambda: self.pdf_view.save_annotations_as()),
            ("Annotationen laden", lambda: self.pdf_view.reload_annotations()),
            ("Annotationen als JSON exportieren…", lambda: self.pdf_view.export_annotations_json()),
            ("Annotationen als CSV exportieren…", lambda: self.pdf_view.export_annotations_csv()),
            ("Annotationen flatten/bake exportieren…", lambda: self.pdf_view.export_annotations_flattened()),
            ("Annotationen aus JSON importieren…", lambda: self.pdf_view.import_annotations_json()),
        ]:
            a = QAction(title, self)
            a.triggered.connect(slot)
            m_pdf.addAction(a)
        m_pdf.addSeparator()
        for title, slot in [
            ("Lesezeichen hinzufügen…", self._outline_add),
            ("Lesezeichen löschen", self._outline_delete),
            ("Seite drehen 90° ⟳", lambda: self.pdf_view.rotate_current(90)),
            ("Seite drehen −90° ⟲", lambda: self.pdf_view.rotate_current(-90)),
            ("Seite horizontal spiegeln ↔", lambda: self.pdf_view.flip_current(horizontal=True)),
            ("Seite vertikal spiegeln ↕", lambda: self.pdf_view.flip_current(vertical=True)),
            ("Graustufen umschalten", lambda: self._toggle_grayscale(not self.pdf_view.grayscale_enabled())),
            ("Nachtmodus umschalten", lambda: self._toggle_night_mode(not self.pdf_view.night_mode_enabled())),
            ("Leere Seite einfügen", lambda: self.pdf_view.insert_blank_after_current()),
            ("Seite duplizieren", lambda: self.pdf_view.duplicate_current()),
            ("Seite löschen…", lambda: self.pdf_view.delete_current()),
            ("Seiten neu anordnen…", lambda: self.pdf_view.reorder_dialog()),
            ("Seite als Bild exportieren…", lambda: self.pdf_view.extract_page_as_image()),
            ("Seiten als Bilder exportieren…", lambda: self.pdf_view.export_pages_as_images()),
            ("Bild als neue Seite…", lambda: self.pdf_view.insert_image_page()),
            ("Seite drucken…", lambda: self.pdf_view.print_current_page()),
            ("PDF als Kopie speichern…", lambda: self.pdf_view.save_pdf_as_copy()),
        ]:
            a = QAction(title, self)
            a.triggered.connect(slot)
            m_pdf.addAction(a)
        m_pdf.addSeparator()
        for title, slot in [
            ("PDF-Text → Overlay…", lambda: self.pdf_view.import_text_overlays()),
            ("Text-Overlays einbrennen…", lambda: self.pdf_view.bake_overlays()),
            ("Text dieser Seite → Editor", self._extract_page_text_to_editor),
            ("Gesamten PDF-Text → Editor", self._extract_all_text_to_editor),
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
        a = QAction("Logordner öffnen", self)
        a.setToolTip("Crash-/App-Logordner im Dateimanager öffnen")
        a.triggered.connect(self._open_log_folder)
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
        """Statusleiste: Dateiname, Seite x/y, Seitengröße, Zoom %, Wörter (Editor)."""
        name = "—"
        page_txt = "Seite —"
        size_txt = "—"
        zoom_txt = "— %"
        word_txt = "— Wörter"
        if self.doc and self.doc.path:
            name = Path(self.doc.path).name
        elif self.pdf_view.pdf_path:
            name = self.pdf_view.pdf_path.name
        if self.pdf_view.pdf_path and self.pdf_view.page_count > 0:
            page_txt = f"Seite {self.pdf_view.page_index + 1}/{self.pdf_view.page_count}"
            zoom_txt = f"{int(round(self.pdf_view.scale * 100))} %"
            word_txt = f"{len(self.pdf_view.store.annotations) if self.pdf_view.store else 0} Ann."
            size_txt = self._format_current_page_size() or "—"
        elif self.stack.currentWidget() is self.editor_pane:
            page_txt = "Editor"
            zoom_txt = "—"
            words, chars = self.editor.word_stats()
            word_txt = f"{words} Wörter · {chars} Z."
        elif self.doc and self.doc.path:
            page_txt = "Editor"
            zoom_txt = "—"
        self.file_status_label.setText(name)
        self.file_status_label.setToolTip(str(self.doc.path) if self.doc and self.doc.path else name)
        self.page_status_label.setText(page_txt)
        if hasattr(self, "size_status_label"):
            self.size_status_label.setText(size_txt)
            unit = get_page_size_unit()
            self.size_status_label.setToolTip(
                f"Seitengröße ({unit}) — Klick wechselt mm ↔ inch"
            )
        self.zoom_status_label.setText(zoom_txt)
        self.word_status_label.setText(word_txt)

    def _format_current_page_size(self) -> str:
        """Aktuelle PDF-Seitengröße formatiert (mm/inch laut Einstellung)."""
        if not self.pdf_view.pdf_path or self.pdf_view.page_count <= 0:
            return ""
        try:
            from ild_pdf.pages import format_size_pair, get_page_boxes

            boxes = get_page_boxes(self.pdf_view.pdf_path, self.pdf_view.page_index)
            mb = boxes["mediabox"]
            w = mb[2] - mb[0]
            h = mb[3] - mb[1]
            return format_size_pair(w, h, get_page_size_unit())
        except Exception:
            try:
                from ild_pdf import PdfDocument

                with PdfDocument(self.pdf_view.pdf_path) as doc:
                    w, h = doc.page_size(self.pdf_view.page_index)
                from ild_pdf.pages import format_size_pair

                return format_size_pair(w, h, get_page_size_unit())
            except Exception:
                return ""

    def _toggle_page_size_unit(self):
        new_unit = toggle_page_size_unit()
        self._update_doc_status()
        self._set_status(f"Seitengröße in {'inch' if new_unit == 'inch' else 'mm'}")

    def _toggle_presentation(self):
        if self._presentation_active:
            self._exit_presentation()
        else:
            self._enter_presentation()

    def _enter_presentation(self):
        if not self.pdf_view.pdf_path:
            self._set_status("Präsentationsmodus: bitte zuerst ein PDF öffnen")
            QMessageBox.information(
                self,
                "Präsentationsmodus",
                "Bitte zuerst ein PDF öffnen.",
            )
            return
        self._presentation_prev = {
            "menu": self.menuBar().isVisible(),
            "status": self.statusBar().isVisible(),
            "sidebar": self.sidebar.isVisible(),
            "was_fullscreen": self.isFullScreen(),
            "stack": self.stack.currentWidget(),
        }
        # PDF-Toolbar ausblenden (erste Layout-Zeile)
        try:
            tb = self.pdf_view.layout().itemAt(0).layout() if self.pdf_view.layout() else None
            if tb is not None:
                for i in range(tb.count()):
                    item = tb.itemAt(i)
                    w = item.widget() if item else None
                    if w is not None:
                        w.setVisible(False)
                self._presentation_prev["toolbar_layout"] = tb
        except Exception:
            self._presentation_prev["toolbar_layout"] = None
        self.stack.setCurrentWidget(self.pdf_view)
        self.menuBar().setVisible(False)
        self.statusBar().setVisible(False)
        self.sidebar.setVisible(False)
        self._presentation_active = True
        self.showFullScreen()
        try:
            self.pdf_view.fit_page()
        except Exception:
            pass
        self.pdf_view.setFocus(Qt.OtherFocusReason)
        self._set_status(
            f"Präsentation — Seite {self.pdf_view.page_index + 1}/{self.pdf_view.page_count} "
            "(←/→ Esc)"
        )

    def _exit_presentation(self):
        if not self._presentation_active:
            return
        prev = self._presentation_prev or {}
        self._presentation_active = False
        # Toolbar wieder ein
        tb = prev.get("toolbar_layout")
        if tb is not None:
            try:
                for i in range(tb.count()):
                    item = tb.itemAt(i)
                    w = item.widget() if item else None
                    if w is not None:
                        w.setVisible(True)
            except Exception:
                pass
        self.menuBar().setVisible(bool(prev.get("menu", True)))
        self.statusBar().setVisible(bool(prev.get("status", True)))
        self.sidebar.setVisible(bool(prev.get("sidebar", True)))
        stack_w = prev.get("stack")
        if stack_w is not None:
            self.stack.setCurrentWidget(stack_w)
        if prev.get("was_fullscreen"):
            self.showFullScreen()
        else:
            self.showNormal()
        self._presentation_prev = None
        self._set_status("Präsentationsmodus beendet")

    def keyPressEvent(self, event):  # noqa: N802
        if self._presentation_active:
            key = event.key()
            if key in (Qt.Key_Escape, Qt.Key_F5, Qt.Key_Q):
                self._exit_presentation()
                event.accept()
                return
            if key in (Qt.Key_Right, Qt.Key_Down, Qt.Key_PageDown, Qt.Key_Space, Qt.Key_Return):
                self.pdf_view.next_page()
                self._set_status(
                    f"Präsentation — Seite {self.pdf_view.page_index + 1}/{self.pdf_view.page_count}"
                )
                event.accept()
                return
            if key in (Qt.Key_Left, Qt.Key_Up, Qt.Key_PageUp, Qt.Key_Backspace):
                self.pdf_view.prev_page()
                self._set_status(
                    f"Präsentation — Seite {self.pdf_view.page_index + 1}/{self.pdf_view.page_count}"
                )
                event.accept()
                return
            if key == Qt.Key_Home:
                self.pdf_view.goto_page(0)
                event.accept()
                return
            if key == Qt.Key_End and self.pdf_view.page_count > 0:
                self.pdf_view.goto_page(self.pdf_view.page_count - 1)
                event.accept()
                return
            event.accept()
            return
        super().keyPressEvent(event)

    def _duplicate_line(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self._set_status("Zeile duplizieren nur im Texteditor")
            return
        if self.editor.duplicate_line():
            if self.doc and self.doc.kind in (
                DocKind.TEXT,
                DocKind.MARKDOWN,
                DocKind.HTML,
                DocKind.DOCX,
            ):
                self.doc.text = self.editor.toPlainText()
                self.doc.dirty = True
            self._on_text_changed()
            self._set_status("Zeile dupliziert")
        else:
            self._set_status("Zeile duplizieren nicht möglich")

    def _move_line_up(self):
        self._move_line(-1)

    def _move_line_down(self):
        self._move_line(1)

    def _move_line(self, delta: int):
        if self.stack.currentWidget() is not self.editor_pane:
            self._set_status("Zeile verschieben nur im Texteditor")
            return
        ok = self.editor.move_line_up() if delta < 0 else self.editor.move_line_down()
        if ok:
            if self.doc and self.doc.kind in (
                DocKind.TEXT,
                DocKind.MARKDOWN,
                DocKind.HTML,
                DocKind.DOCX,
            ):
                self.doc.text = self.editor.toPlainText()
                self.doc.dirty = True
            self._on_text_changed()
            self._set_status("Zeile nach oben" if delta < 0 else "Zeile nach unten")
        else:
            self._set_status("Zeile verschieben nicht möglich")

    def _toggle_line_comment(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self._set_status("Kommentieren nur im Texteditor")
            return
        path = self.doc.path if self.doc else None
        prefix = self.editor.comment_prefix_for_path(path)
        if self.editor.toggle_line_comment(prefix):
            if self.doc and self.doc.kind in (
                DocKind.TEXT,
                DocKind.MARKDOWN,
                DocKind.HTML,
                DocKind.DOCX,
            ):
                self.doc.text = self.editor.toPlainText()
                self.doc.dirty = True
            self._on_text_changed()
            self._set_status(f"Kommentar umgeschaltet ({prefix})")
        else:
            self._set_status("Kommentieren nicht möglich")

    def _select_all_annotations_on_page(self):
        if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
            n = self.pdf_view.select_all_annotations_on_page()
            if n == 0:
                self._set_status("Keine Annotationen auf dieser Seite")
            return
        # Editor / sonst: klassisches Alles auswählen
        if self.stack.currentWidget() is self.editor_pane:
            self.editor.selectAll()
            self._set_status("Text ausgewählt")
        else:
            self._set_status("Auswahl: PDF mit Annotationen öffnen oder Texteditor nutzen")

    def _on_pdf_zoom_changed(self, scale: float):
        self.zoom_status_label.setText(f"{int(round(float(scale) * 100))} %")
        if self.pdf_view.pdf_path and self.pdf_view.page_count > 0:
            self.page_status_label.setText(
                f"Seite {self.pdf_view.page_index + 1}/{self.pdf_view.page_count}"
            )
            if hasattr(self, "size_status_label"):
                self.size_status_label.setText(self._format_current_page_size() or "—")

    def _delete_annotation(self):
        if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
            self.pdf_view.delete_annotation()
        else:
            self._set_status("Annotation löschen nur im PDF-Modus")

    def _edit_annotation_text(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Annotation bearbeiten nur im PDF-Modus")
            return
        if not self.pdf_view._selected_ann_id:
            self._set_status("Keine Annotation ausgewählt (Auswahl-Werkzeug / Doppelklick)")
            return
        self.pdf_view.edit_selected_annotation_text()

    def _duplicate_annotation(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Annotation duplizieren nur im PDF-Modus")
            return
        if not self.pdf_view._selected_ann_id:
            self._set_status("Keine Annotation ausgewählt")
            return
        self.pdf_view.duplicate_selected_annotation()

    def _toggle_line_numbers(self, checked: bool):
        from instantlensdoc.core.app_settings import set_editor_line_numbers

        set_editor_line_numbers(bool(checked))
        self.editor.set_line_numbers_visible(bool(checked))
        self._set_status("Zeilennummern an" if checked else "Zeilennummern aus")

    def _toggle_markdown_preview(self, checked: bool):
        self.editor_pane.set_preview_visible(bool(checked))
        self._set_status("Markdown-Vorschau an" if checked else "Markdown-Vorschau aus")

    def _toggle_soft_wrap(self, checked: bool):
        from instantlensdoc.core.app_settings import set_editor_soft_wrap

        set_editor_soft_wrap(bool(checked))
        self.editor.set_soft_wrap(bool(checked))
        self._set_status("Soft-Wrap an" if checked else "Soft-Wrap aus")

    def _toggle_special_chars(self, checked: bool):
        from instantlensdoc.core.app_settings import set_editor_show_special_chars

        set_editor_show_special_chars(bool(checked))
        self.editor.set_special_chars_visible(bool(checked))
        self._set_status("Sonderzeichen an" if checked else "Sonderzeichen aus")

    def _toggle_grayscale(self, checked: bool):
        self.pdf_view.set_grayscale(bool(checked))
        self._sync_grayscale_action(bool(checked))

    def _toggle_night_mode(self, checked: bool):
        self.pdf_view.set_night_mode(bool(checked))
        self._sync_night_action(bool(checked))

    def _toggle_ann_layer(self, checked: bool):
        self.pdf_view.set_annotations_visible(bool(checked))
        self._sync_ann_layer_action(bool(checked))

    def _sync_grayscale_action(self, enabled: bool):
        if hasattr(self, "_grayscale_action") and self._grayscale_action is not None:
            self._grayscale_action.blockSignals(True)
            self._grayscale_action.setChecked(bool(enabled))
            self._grayscale_action.blockSignals(False)

    def _sync_night_action(self, enabled: bool):
        if hasattr(self, "_night_action") and self._night_action is not None:
            self._night_action.blockSignals(True)
            self._night_action.setChecked(bool(enabled))
            self._night_action.blockSignals(False)

    def _sync_ann_layer_action(self, enabled: bool):
        if hasattr(self, "_ann_layer_action") and self._ann_layer_action is not None:
            self._ann_layer_action.blockSignals(True)
            self._ann_layer_action.setChecked(bool(enabled))
            self._ann_layer_action.blockSignals(False)

    def _toggle_case_selection(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self._set_status("Groß-/Kleinschreibung nur im Texteditor")
            return
        if self.editor.toggle_case_selection():
            self._set_status("Schreibweise umgeschaltet")
        else:
            self._set_status("Keine Textauswahl")

    def _indent_selection(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self._set_status("Einrückung nur im Texteditor")
            return
        if self.editor.indent_selection():
            self._set_status("Einrückung erhöht")
        else:
            self._set_status("Einrückung nicht möglich")

    def _outdent_selection(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self._set_status("Einrückung nur im Texteditor")
            return
        if self.editor.outdent_selection():
            self._set_status("Einrückung verringert")
        else:
            self._set_status("Einrückung nicht möglich")

    def _open_log_folder(self):
        from instantlensdoc.ui.help_dialog import open_log_folder

        if open_log_folder(self):
            from instantlensdoc.core.logging_setup import log_dir

            self._set_status(f"Logordner: {log_dir()}")

    def _app_title(self, suffix: str | None = None) -> str:
        base = f"{DISPLAY_NAME} {__version__}"
        if suffix:
            return f"{base} — {suffix}"
        return base

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
        urgent = st.allowed and st.days_remaining < 7
        if st.mode == "licensed":
            who = f" · {st.email}" if st.email else ""
            if urgent:
                text = f"⚠ Lizenz: noch {st.days_remaining} Tag(e)!{who}"
                style = (
                    "color: #7B241C; background: #F5B7B1; font-weight: 800; "
                    "font-size: 12px; padding: 3px 8px; border-radius: 3px;"
                )
            else:
                text = f"Lizenz: Aktiviert{who} · noch {st.days_remaining} Tag(e)"
                style = "color: #1B7A3D; font-weight: 600; padding-right: 6px;"
        elif st.mode == "trial":
            if urgent:
                text = f"⚠ Testversion: noch {st.days_remaining} Tag(e)! — Hilfe → Lizenz"
                style = (
                    "color: #7B241C; background: #F9E79F; font-weight: 800; "
                    "font-size: 12px; padding: 3px 8px; border-radius: 3px;"
                )
            else:
                text = f"Lizenz: Testversion · noch {st.days_remaining} Tag(e) — Hilfe → Lizenz"
                style = "color: #B9770E; font-weight: 600; padding-right: 6px;"
        else:
            text = "Lizenz: Abgelaufen — Hilfe → Lizenz · ame@sellerbach.de"
            style = "color: #C0392B; font-weight: 700; padding-right: 6px;"
        self.license_label.setText(text)
        self.license_label.setStyleSheet(style)
        tip = st.message
        if urgent:
            tip = f"Restlaufzeit unter 7 Tagen — {st.message}"
        self.license_label.setToolTip(tip)
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
        if self.stack.currentWidget() is self.editor_pane:
            words, chars = self.editor.word_stats()
            self.word_status_label.setText(f"{words} Wörter · {chars} Z.")

    def _on_pdf_document_changed(self):
        self._update_doc_status()
        if self.pdf_view.pdf_path:
            self._refresh_thumbs()
            self._refresh_outline(self.pdf_view.pdf_path)
        else:
            self.sidebar.clear_thumbs()
            self.sidebar.clear_annotations()
            self.sidebar.set_outline([])

    def _focus_search(self):
        self.sidebar.setVisible(True)
        le = self.sidebar.search.lineEdit()
        if le is not None:
            le.setFocus()
            le.selectAll()
        else:
            self.sidebar.search.setFocus()

    def _find_replace(self):
        if self.stack.currentWidget() is not self.editor_pane:
            QMessageBox.information(
                self,
                "Suchen und Ersetzen",
                "Find/Replace ist im Texteditor verfügbar.",
            )
            return
        from instantlensdoc.ui.find_replace_dialog import FindReplaceDialog

        initial = ""
        cur = self.editor.textCursor()
        if cur.hasSelection():
            initial = cur.selectedText().replace("\u2029", " ")
        dlg = FindReplaceDialog(self.editor, self, initial_find=initial)
        dlg.exec()
        if self.doc and self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            self.doc.text = self.editor.toPlainText()
            self.doc.dirty = True
        self._on_text_changed()

    def _goto_line(self):
        if self.stack.currentWidget() is not self.editor_pane:
            QMessageBox.information(
                self,
                "Gehe zu Zeile",
                "Gehe zu Zeile ist im Texteditor verfügbar.",
            )
            return
        from instantlensdoc.ui.goto_line_dialog import GotoLineDialog

        GotoLineDialog(self.editor, self).exec()

    def _extract_page_text_to_editor(self):
        if not self.pdf_view.pdf_path:
            self._set_status("Kein PDF geladen")
            return
        from ild_pdf import extract_page_plain_text

        try:
            text = extract_page_plain_text(
                self.pdf_view.pdf_path,
                self.pdf_view.page_index,
                password=self.pdf_view.password,
            )
        except Exception as e:
            QMessageBox.warning(self, "Text extrahieren", str(e))
            return
        self.editor.setPlainText(text)
        self.stack.setCurrentWidget(self.editor_pane)
        self._on_text_changed()
        words = len(text.split()) if text.strip() else 0
        self._set_status(
            f"Seite {self.pdf_view.page_index + 1}: Text → Editor ({words} Wörter)"
        )

    def _extract_all_text_to_editor(self):
        if not self.pdf_view.pdf_path:
            self._set_status("Kein PDF geladen")
            return
        from ild_pdf import extract_all_plain_text

        try:
            text = extract_all_plain_text(
                self.pdf_view.pdf_path,
                password=self.pdf_view.password,
                page_headers=True,
            )
        except Exception as e:
            QMessageBox.warning(self, "Text extrahieren", str(e))
            return
        self.editor.setPlainText(text)
        self.stack.setCurrentWidget(self.editor_pane)
        self._on_text_changed()
        words = len(text.split()) if text.strip() else 0
        self._set_status(
            f"Gesamter PDF-Text ({self.pdf_view.page_count} Seite(n)) → Editor ({words} Wörter)"
        )

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

    def _fit_height(self):
        if self.stack.currentWidget() is self.pdf_view:
            self.pdf_view.fit_height()
        else:
            self._set_status("Höhe einpassen: PDF öffnen")

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
            if self.stack.currentWidget() is self.editor_pane:
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
        if self.stack.currentWidget() is self.editor_pane:
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
        if self.stack.currentWidget() is self.editor_pane:
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
        if self.stack.currentWidget() is not self.editor_pane:
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
        n = len(self.pdf_view.store.annotations) if self.pdf_view.store else 0
        self.word_status_label.setText(f"{n} Ann.")

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

    def _outline_add(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Lesezeichen hinzufügen: PDF öffnen")
            return
        from PySide6.QtWidgets import QInputDialog
        from ild_pdf.outline import add_outline_item

        page = self.pdf_view.page_index
        title, ok = QInputDialog.getText(
            self,
            "Lesezeichen hinzufügen",
            f"Titel (Seite {page + 1}):",
            text=f"Seite {page + 1}",
        )
        if not ok:
            return
        try:
            add_outline_item(self.pdf_view.pdf_path, title, page)
            self._refresh_outline(self.pdf_view.pdf_path)
            self._set_status(f"Lesezeichen „{(title or '').strip() or 'Lesezeichen'}“ → S. {page + 1}")
        except Exception as e:
            QMessageBox.warning(self, "Lesezeichen", str(e))

    def _outline_delete(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Lesezeichen löschen: PDF öffnen")
            return
        path = self.sidebar.selected_outline_path()
        if path is None:
            self._set_status("Kein Lesezeichen ausgewählt")
            return
        from ild_pdf.outline import delete_outline_item

        try:
            delete_outline_item(self.pdf_view.pdf_path, path)
            self._refresh_outline(self.pdf_view.pdf_path)
            self._set_status("Lesezeichen gelöscht")
        except Exception as e:
            QMessageBox.warning(self, "Lesezeichen löschen", str(e))

    def _refresh_outline(self, path: str | Path):
        try:
            items = extract_outline(path)
        except Exception:
            items = []
        self.sidebar.set_outline(items)

    def _refresh_thumbs(self):
        if not self.pdf_view.pdf_path:
            self._stop_thumb_lazy()
            self.sidebar.clear_thumbs()
            return
        # Lazy: Platzhalter sofort, Seiten einzeln nachladen (UI bleibt responsiv)
        try:
            page_count = int(self.pdf_view.page_count or 0)
            current = int(self.pdf_view.page_index or 0)
            token = self.sidebar.prepare_lazy_thumbs(page_count, current=current, max_pages=40)
            self._start_thumb_lazy(token, page_count=min(page_count, 40), prefer=current)
        except Exception as e:
            _log.warning("Thumbnails: %s", e)
            self._stop_thumb_lazy()
            self.sidebar.clear_thumbs()

    def _stop_thumb_lazy(self):
        if self._thumb_lazy_timer is not None:
            try:
                self._thumb_lazy_timer.stop()
            except Exception:
                pass
            self._thumb_lazy_timer = None
        self._thumb_lazy_queue = []
        self._thumb_lazy_token = None

    def _start_thumb_lazy(self, token: int, *, page_count: int, prefer: int = 0):
        self._stop_thumb_lazy()
        if page_count <= 0:
            return
        # Aktuelle Seite zuerst, dann Nachbarn, dann Rest
        order: list[int] = []
        seen: set[int] = set()
        for i in [prefer, prefer - 1, prefer + 1] + list(range(page_count)):
            if 0 <= i < page_count and i not in seen:
                seen.add(i)
                order.append(i)
        self._thumb_lazy_queue = order
        self._thumb_lazy_token = token
        self._thumb_lazy_timer = QTimer(self)
        self._thumb_lazy_timer.setInterval(16)
        self._thumb_lazy_timer.timeout.connect(self._thumb_lazy_tick)
        self._thumb_lazy_timer.start()

    def _thumb_lazy_tick(self):
        if not self._thumb_lazy_queue or self._thumb_lazy_token is None:
            self._stop_thumb_lazy()
            return
        if not self.pdf_view.pdf_path:
            self._stop_thumb_lazy()
            return
        idx = self._thumb_lazy_queue.pop(0)
        try:
            img = self.pdf_view.render_thumbnail(idx, scale=get_pdf_thumbnail_scale())
            self.sidebar.update_thumb(idx, img, token=self._thumb_lazy_token)
        except Exception as e:
            _log.debug("Thumb lazy %s: %s", idx, e)
        if not self._thumb_lazy_queue:
            self._stop_thumb_lazy()

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
            from instantlensdoc.core.app_settings import (
                get_editor_line_numbers,
                get_editor_markdown_preview,
                get_editor_show_special_chars,
                get_editor_soft_wrap,
                get_pdf_grayscale,
                get_pdf_night_mode,
            )

            show_ln = get_editor_line_numbers()
            self.editor.set_line_numbers_visible(show_ln)
            if hasattr(self, "_line_numbers_action") and self._line_numbers_action is not None:
                self._line_numbers_action.blockSignals(True)
                self._line_numbers_action.setChecked(show_ln)
                self._line_numbers_action.blockSignals(False)
            soft = get_editor_soft_wrap()
            self.editor.set_soft_wrap(soft)
            if hasattr(self, "_soft_wrap_action") and self._soft_wrap_action is not None:
                self._soft_wrap_action.blockSignals(True)
                self._soft_wrap_action.setChecked(soft)
                self._soft_wrap_action.blockSignals(False)
            special = get_editor_show_special_chars()
            self.editor.set_special_chars_visible(special)
            if hasattr(self, "_special_chars_action") and self._special_chars_action is not None:
                self._special_chars_action.blockSignals(True)
                self._special_chars_action.setChecked(special)
                self._special_chars_action.blockSignals(False)
            md = get_editor_markdown_preview()
            self.editor_pane.set_preview_visible(md)
            if hasattr(self, "_md_preview_action") and self._md_preview_action is not None:
                self._md_preview_action.blockSignals(True)
                self._md_preview_action.setChecked(md)
                self._md_preview_action.blockSignals(False)
            gray = get_pdf_grayscale()
            self.pdf_view.set_grayscale(gray)
            if hasattr(self, "_grayscale_action") and self._grayscale_action is not None:
                self._grayscale_action.blockSignals(True)
                self._grayscale_action.setChecked(gray)
                self._grayscale_action.blockSignals(False)
            night = get_pdf_night_mode()
            self.pdf_view.set_night_mode(night)
            if hasattr(self, "_night_action") and self._night_action is not None:
                self._night_action.blockSignals(True)
                self._night_action.setChecked(night)
                self._night_action.blockSignals(False)
            self._autosave_timer.setInterval(get_autosave_interval_sec() * 1000)
            self.pdf_view.apply_settings_colors()
            if self.pdf_view.pdf_path:
                self._refresh_thumbs()
            self._set_status(
                f"Einstellungen gespeichert · Autosave {get_autosave_interval_sec()}s"
            )

    def _edit_pdf_metadata(self):
        if not self.pdf_view.pdf_path:
            QMessageBox.information(self, "Metadaten", "Bitte zuerst ein PDF öffnen.")
            return
        if MetadataDialog(self.pdf_view.pdf_path, self).exec():
            self._set_status("PDF-Metadaten gespeichert")

    def _edit_pdf_form_fields(self):
        if not self.pdf_view.pdf_path:
            QMessageBox.information(self, "Formularfelder", "Bitte zuerst ein PDF öffnen.")
            return
        from ild_pdf import has_acroform

        if not has_acroform(self.pdf_view.pdf_path):
            QMessageBox.information(
                self,
                "Formularfelder",
                "Dieses PDF enthält keine AcroForm-Felder.\n"
                "Nur bestehende Formularfelder können ausgefüllt werden.",
            )
            return
        if FormFieldsDialog(self.pdf_view.pdf_path, self).exec():
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_view.pdf_path)
            self.pdf_view.refresh()
            self._set_status("Formularfelder gespeichert")

    def _pdf_attachments(self):
        if not self.pdf_view.pdf_path:
            QMessageBox.information(self, "Anhänge", "Bitte zuerst ein PDF öffnen.")
            return
        from ild_pdf import list_attachments

        try:
            items = list_attachments(self.pdf_view.pdf_path)
        except Exception as e:
            QMessageBox.warning(self, "Anhänge", str(e))
            return
        if not items:
            QMessageBox.information(self, "Anhänge", "Dieses PDF enthält keine Anhänge.")
            return
        AttachmentsDialog(self.pdf_view.pdf_path, self).exec()

    def _current_is_dirty(self) -> bool:
        if not self.doc:
            return False
        if self.doc.kind == DocKind.PDF:
            return bool(self.pdf_view.store and self.pdf_view.store.dirty)
        if self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            current = self.editor.toPlainText()
            if current != (self.doc.text or ""):
                self.doc.dirty = True
                return True
        return bool(self.doc.dirty)

    def _confirm_close_current(self, *, allow_discard: bool = True, quitting: bool = False) -> bool:
        """Speichern-Dialog wenn dirty. True = fortfahren, False = abbrechen."""
        if not self._current_is_dirty():
            return True
        name = self.doc.display_name if self.doc else "Dokument"
        buttons = QMessageBox.Save | QMessageBox.Cancel
        if allow_discard:
            buttons |= QMessageBox.Discard
        title = "Beenden" if quitting else "Schließen"
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Warning)
        box.setText(f"„{name}“ wurde geändert.")
        box.setInformativeText("Änderungen speichern?")
        box.setStandardButtons(buttons)
        box.setDefaultButton(QMessageBox.Save)
        result = box.exec()
        if result == QMessageBox.Cancel:
            return False
        if result == QMessageBox.Discard:
            if self.doc:
                self.doc.dirty = False
            if self.pdf_view.store:
                self.pdf_view.store.dirty = False
            return True
        try:
            self.save_doc()
        except Exception as e:
            QMessageBox.warning(self, title, f"Speichern fehlgeschlagen:\n{e}")
            return False
        return not self._current_is_dirty()

    def close_current_tab(self):
        """Aktuelles Dokument schließen; Speichern-Dialog bei dirty."""
        if not self.doc:
            self._set_status("Kein Dokument geöffnet")
            return
        if not self._confirm_close_current(allow_discard=True):
            return
        path = str(self.doc.path) if self.doc.path else None
        if path:
            self.sidebar.remove_document(path)
        remaining = self.sidebar.document_paths()
        self.doc = None
        try:
            self.pdf_view.pdf_path = None
            self.pdf_view.store = None
            self.pdf_view.page_count = 0
        except Exception:
            pass
        self.editor.blockSignals(True)
        self.editor.setPlainText("")
        self.editor.blockSignals(False)
        self.sidebar.clear_thumbs()
        self.sidebar.clear_annotations()
        self.sidebar.set_marks([])
        self.stack.setCurrentWidget(self.editor_pane)
        self.setWindowTitle(self._app_title())
        self._update_doc_status()
        if remaining:
            nxt = remaining[0]
            self.open_path(nxt)
            self._set_status(f"Geschlossen — gewechselt zu {Path(nxt).name}")
        else:
            self._set_status("Dokument geschlossen")

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
        pc = self.pdf_view.page_count if self.pdf_view.pdf_path else None
        PdfToolsDialog(
            self,
            initial_pdf=initial,
            page_count=pc,
            current_page=self.pdf_view.page_index if self.pdf_view.pdf_path else 0,
        ).exec()

    def _extract_page_range(self):
        """Schnelldialog: Seiten von–bis → neues PDF (aktuelles Dokument vorausgefüllt)."""
        if not self.pdf_view.pdf_path:
            QMessageBox.information(
                self,
                "Seitenbereich",
                "Bitte zuerst ein PDF öffnen — oder PDF → zusammenführen / teilen → Seitenbereich.",
            )
            self._pdf_tools()
            return
        from PySide6.QtWidgets import QInputDialog
        from ild_pdf.pages import extract_page_range

        n = self.pdf_view.page_count
        start, ok1 = QInputDialog.getInt(
            self, "Seitenbereich", "Von Seite (1-basiert):", self.pdf_view.page_index + 1, 1, n
        )
        if not ok1:
            return
        end, ok2 = QInputDialog.getInt(self, "Seitenbereich", "Bis Seite (inklusive):", n, start, n)
        if not ok2:
            return
        src = Path(self.pdf_view.pdf_path)
        default = str(Path(dialog_start_dir(src.parent)) / f"{src.stem}_p{start}-{end}.pdf")
        dest, _ = QFileDialog.getSaveFileName(self, "Ziel-PDF", default, "PDF (*.pdf)")
        if not dest:
            return
        remember_recent_dir(dest)
        if not dest.lower().endswith(".pdf"):
            dest += ".pdf"
        if not confirm_overwrite_export(dest, self):
            return
        try:
            out = extract_page_range(src, dest, start, end, one_based=True)
            self._set_status(f"Seitenbereich {start}–{end} → {Path(out).name}")
            QMessageBox.information(self, "Seitenbereich", f"Gespeichert:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Seitenbereich", str(e))

    def _split_into_single_page_pdfs(self):
        """Jede Seite des aktuellen PDFs als eigene Datei exportieren."""
        if not self.pdf_view.pdf_path:
            QMessageBox.information(
                self,
                "Einzel-PDFs",
                "Bitte zuerst ein PDF öffnen — oder PDF → zusammenführen / teilen.",
            )
            self._pdf_tools()
            return
        from ild_pdf.pages import split_into_single_page_pdfs

        n = self.pdf_view.page_count
        src = Path(self.pdf_view.pdf_path)
        out_dir = QFileDialog.getExistingDirectory(
            self,
            f"Ausgabeordner ({n} Einzel-PDF(s))",
            dialog_start_dir(src.parent),
        )
        if not out_dir:
            return
        remember_recent_dir(out_dir)
        try:
            written = split_into_single_page_pdfs(src, out_dir)
            set_last_export_dir(out_dir)
            self._set_status(f"{len(written)} Einzel-PDF(s) → {out_dir}")
            QMessageBox.information(
                self,
                "Einzel-PDFs",
                f"{len(written)} Datei(en) erstellt in:\n{out_dir}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Einzel-PDFs", str(e))

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
            self.stack.setCurrentWidget(self.editor_pane)
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
        self.stack.setCurrentWidget(self.editor_pane)
        self.setWindowTitle(self._app_title("Unbenannt"))
        self._update_doc_status()
        self._set_status("Neues Dokument")

    def open_dialog(self):
        start = dialog_start_dir(get_default_open_dir())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Öffnen",
            start,
            "Dokumente (*.txt *.md *.html *.htm *.docx *.pdf *.png *.jpg *.jpeg);;Alle (*.*)",
        )
        if path:
            remember_recent_dir(path)
            self.open_path(path)

    def open_path(self, path: str):
        try:
            self.doc = open_document(path)
        except Exception as e:
            QMessageBox.critical(self, "Öffnen", f"Datei konnte nicht geöffnet werden:\n{e}")
            return

        self.sidebar.add_document(path)
        self._remember_path(path)
        self.setWindowTitle(self._app_title(self.doc.display_name))

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
                self.stack.setCurrentWidget(self.editor_pane)
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

    def save_all_docs(self):
        """Aktuelles Dokument speichern und Annotation-Sidecars aller offenen PDF-Tabs flushen."""
        st = self.license_manager.status()
        if not st.allowed:
            QMessageBox.warning(self, "Lizenz", "Speichern nicht möglich — Lizenz/Trial abgelaufen.")
            return
        saved = 0
        errors: list[str] = []
        current = str(self.doc.path) if self.doc and self.doc.path else ""
        # Aktuelles Doc zuerst
        if self.doc:
            try:
                if self.doc.kind == DocKind.PDF:
                    if self.pdf_view.store is not None:
                        self.pdf_view.store.save(force=True)
                        saved += 1
                elif self.doc.path:
                    if self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
                        self.doc.text = self.editor.toPlainText()
                    save_document(self.doc)
                    saved += 1
                elif self.doc.dirty:
                    self.save_as()
                    if self.doc.path:
                        saved += 1
            except Exception as e:
                errors.append(str(e))
        # Andere offene PDF-Tabs: Sidecar neu schreiben (bereits auf Disk = no-op bei clean)
        from ild_pdf import AnnotationStore

        for path in self.sidebar.document_paths():
            p = Path(path)
            if str(p.resolve()) == (str(Path(current).resolve()) if current else ""):
                continue
            if p.suffix.lower() != ".pdf" or not p.is_file():
                continue
            try:
                store = AnnotationStore(p)
                if store.annotations and store.sidecar_path.is_file():
                    # Sidecar existiert → erneut speichern (garantiert Flush)
                    store.dirty = True
                    store.save(force=True)
                    saved += 1
            except Exception as e:
                errors.append(f"{p.name}: {e}")
        if errors:
            QMessageBox.warning(
                self,
                "Alles speichern",
                f"Gespeichert: {saved}\nFehler:\n" + "\n".join(errors[:8]),
            )
        else:
            self._set_status(f"Alles speichern: {saved} Datei(en)/Sidecar(s)")

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
            str(Path(dialog_start_dir()) / self.doc.display_name),
            "Text (*.txt);;Markdown (*.md);;HTML (*.html);;DOCX (*.docx);;Alle (*.*)",
        )
        if not path:
            return
        remember_recent_dir(path)
        if self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            self.doc.text = self.editor.toPlainText()
        try:
            save_document(self.doc, Path(path))
            self.sidebar.add_document(path)
            self._remember_path(path)
            self.setWindowTitle(self._app_title(self.doc.display_name))
            self._set_status(f"Gespeichert: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Speichern", f"Speichern fehlgeschlagen:\n{e}")

    def save_as_copy(self):
        """PDF: Dateikopie (+ Sidecar); Editor: Speichern unter."""
        if not self.doc:
            return
        if self.doc.kind == DocKind.PDF:
            if self.pdf_view.save_pdf_as_copy():
                self._set_status("PDF-Kopie gespeichert")
            return
        self.save_as()

    def _export_editor(self, fmt: str):
        """Editor-Inhalt nach HTML / DOCX / PDF exportieren."""
        text = ""
        title = "InstantLens Doc"
        if self.stack.currentWidget() is self.editor_pane:
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
        start = str(Path(dialog_start_dir(last_dir)) / default_name)
        path, _ = QFileDialog.getSaveFileName(self, f"Export {fmt.upper()}", start, filt)
        if not path:
            return
        if not confirm_overwrite_export(path, self):
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
            remember_recent_dir(path)
            self._set_status(f"Exportiert: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export", f"Export fehlgeschlagen:\n{e}")

    def _add_text_frame(self):
        text = self.editor.toPlainText() if self.stack.currentWidget() is self.editor_pane else ""
        frame = self.layout_doc.add_text_frame(text=text)
        flowed = self.layout_doc.flow_text(text or "Neuer Textrahmen", frame)
        if self.stack.currentWidget() is self.editor_pane:
            self.editor.appendPlainText(f"\n--- Textrahmen {frame.id} ---\n{flowed}")
        self._set_status(f"Textrahmen {frame.id} hinzugefügt")

    def _add_chained_frame(self):
        """Verkettete Textrahmen: Overflow fließt in den nächsten Rahmen."""
        source = self.editor.toPlainText() if self.stack.currentWidget() is self.editor_pane else ""
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
        if self.stack.currentWidget() is self.editor_pane:
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
            self,
            "Bild einfügen",
            dialog_start_dir(),
            "Bilder (*.png *.jpg *.jpeg *.bmp)",
        )
        if not path:
            return
        remember_recent_dir(path)
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
        if self.stack.currentWidget() is self.editor_pane:
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
                        self,
                        "Bild für OCR",
                        dialog_start_dir(),
                        "Bilder (*.png *.jpg *.jpeg *.tif *.tiff)",
                    )
                if not path:
                    return
                remember_recent_dir(path)
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

        self.stack.setCurrentWidget(self.editor_pane)
        self.editor.setPlainText(result.text)
        self.doc = Document(kind=DocKind.TEXT, title=f"OCR — {source_label}", text=result.text)
        self.setWindowTitle(self._app_title(f"OCR — {source_label}"))
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
