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
    QVBoxLayout,
    QWidget,
)

from instantlensdoc import __version__
from instantlensdoc.config import DISPLAY_NAME, icon_paths_for_qt
from instantlensdoc.core.documents import (
    DocKind,
    Document,
    open_document,
    render_doc_template,
    save_document,
)
from instantlensdoc.core import ocr as ocr_mod
from instantlensdoc.core.layout import LayoutDocument
from instantlensdoc.core import recent as recent_mod
from instantlensdoc.core import recent_searches as recent_searches_mod
from instantlensdoc.license import LicenseManager
from instantlensdoc.ui.editor import EditorPane
from instantlensdoc.ui.form_builder import FormBuilderDialog
from instantlensdoc.ui.attachments_dialog import AttachmentsDialog
from instantlensdoc.ui.help_dialog import AboutDialog, GettingStartedWizard, HelpDialog
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
    get_editor_doc_split,
    get_editor_doc_split_sync_scroll,
    get_editor_doc_split_vertical,
    get_editor_markdown_preview,
    get_editor_soft_wrap,
    get_last_export_dir,
    get_minimize_to_tray,
    get_page_size_unit,
    get_pdf_thumbnail_scale,
    get_restore_session_on_start,
    get_restore_window_geometry_on_start,
    get_update_check_on_start,
    get_window_geometry_b64,
    get_window_state_b64,
    remember_recent_dir,
    remember_project_workspace,
    get_project_workspaces,
    get_active_project_workspace,
    set_last_export_dir,
    set_window_geometry_b64,
    set_window_state_b64,
    toggle_page_size_unit,
)
from instantlensdoc.ui.batch_dialog import BatchConvertDialog
from instantlensdoc.ui.file_dialogs import (
    confirm_overwrite_export,
    resolve_template_zip_conflicts,
)
from instantlensdoc.ui.pdf_tools_dialog import PdfToolsDialog
from instantlensdoc.ui.watermark_dialog import WatermarkDialog
from instantlensdoc.ui.compare_dialog import PdfCompareDialog
from instantlensdoc.ui.text_compare_dialog import TextCompareDialog
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
        self._workspace_menu = None
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
        self._unsaved_paths: set[str] = set()
        self._secondary_path: str | None = None
        self._secondary_kind: str = ""  # "pdf" | "editor" | "" — Panel-Typ je Session
        self._last_tag_rename: tuple[str, str] | None = None  # (old, new) für einstufiges Undo
        self._batch_save_quiet: bool = False  # Alle-speichern: Einzeldialoge unterdrücken

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
        self._refresh_workspaces()
        self._refresh_recent_searches()
        self._update_license_status()
        apply_theme()
        self._sync_theme_menu()
        if get_editor_doc_split() and get_editor_doc_split_sync_scroll():
            self._apply_doc_split_sync_scroll()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(get_autosave_interval_sec() * 1000)
        self._autosave_timer.timeout.connect(self._autosave_tick)
        self._autosave_timer.start()
        QTimer.singleShot(200, self._restore_session)
        QTimer.singleShot(600, self._maybe_show_getting_started_wizard)
        if get_update_check_on_start():
            QTimer.singleShot(1500, lambda: self._check_updates(silent=True))

    def _restore_window_geometry(self) -> None:
        import base64

        from PySide6.QtCore import QByteArray

        if not get_restore_window_geometry_on_start():
            return
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
        # Sidebar-Dokumente = „offene Tabs“ (Drag-Reihenfolge)
        try:
            if hasattr(self.sidebar, "document_paths"):
                paths.extend(self.sidebar.document_paths())
            else:
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

    def _on_documents_reordered(self):
        """Session-Tab-Reihenfolge nach Drag in der Dokumentliste speichern."""
        self._save_session()
        n = len(self._session_paths())
        self._set_status(f"Dokument-Reihenfolge gespeichert ({n} Tab(s))")

    def _save_session(self):
        paths = self._session_paths()
        active = str(Path(self.doc.path)) if self.doc and self.doc.path else None
        page = self.pdf_view.page_index if self.pdf_view.pdf_path else 0
        scale = self.pdf_view.scale if self.pdf_view.pdf_path else 1.5
        sec_path = ""
        sec_kind = ""
        if getattr(self, "_secondary_path", None) and Path(self._secondary_path).is_file():
            sec_path = str(Path(self._secondary_path))
            sec_kind = str(getattr(self, "_secondary_kind", "") or "")
            if not sec_kind:
                sec_kind = "pdf" if Path(sec_path).suffix.lower() == ".pdf" else "editor"
        state = session_mod.build_session(
            paths,
            active_path=active,
            page=page,
            scale=scale,
            restore=True,
            secondary_path=sec_path or None,
            secondary_kind=sec_kind or None,
            sync_scroll=get_editor_doc_split_sync_scroll(),
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
        # Doc-Split Panel-Typ / Zweit-Doc aus Session wiederherstellen
        sec = str(getattr(state, "secondary_path", "") or "").strip()
        kind = str(getattr(state, "secondary_kind", "") or "").strip().lower()
        if sec and Path(sec).is_file():
            self._secondary_path = str(Path(sec))
            self._secondary_kind = kind if kind in ("pdf", "editor") else (
                "pdf" if Path(sec).suffix.lower() == ".pdf" else "editor"
            )
            if get_editor_doc_split():
                if hasattr(self, "_doc_split_action"):
                    self._doc_split_action.blockSignals(True)
                    self._doc_split_action.setChecked(True)
                    self._doc_split_action.blockSignals(False)
                if hasattr(self, "secondary_wrap"):
                    self.secondary_wrap.setVisible(True)
                self._load_secondary_document(self._secondary_path)
        # Sync-Scroll-Zustand aus Session wiederherstellen (0.6.9)
        from instantlensdoc.core.app_settings import set_editor_doc_split_sync_scroll

        want_sync = bool(getattr(state, "sync_scroll", False))
        set_editor_doc_split_sync_scroll(want_sync)
        if hasattr(self, "_doc_split_sync_action"):
            self._doc_split_sync_action.blockSignals(True)
            self._doc_split_sync_action.setChecked(want_sync)
            self._doc_split_sync_action.blockSignals(False)
        self._apply_doc_split_sync_scroll()
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
        self.sidebar.search_prev_requested.connect(self._on_search_prev)
        self.sidebar.search_export_requested.connect(self._on_search_export)
        self.sidebar.file_activated.connect(self.open_path)
        self.sidebar.document_close_requested.connect(self.close_tab_path)
        self.sidebar.document_close_others_requested.connect(self.close_other_tabs_keeping)
        self.sidebar.recent_activated.connect(self.open_path)
        self.sidebar.recent_remove_requested.connect(self._remove_recent_path)
        self.sidebar.mark_activated.connect(self._on_mark_activated)
        self.sidebar.annotation_activated.connect(self._on_annotation_activated)
        self.sidebar.outline_activated.connect(self._on_outline_jump)
        self.sidebar.outline_add_requested.connect(self._outline_add)
        self.sidebar.outline_delete_requested.connect(self._outline_delete)
        self.sidebar.annotation_filter_changed.connect(lambda _t: None)
        self.sidebar.annotation_tag_rename_requested.connect(self._rename_annotation_tag_global)
        self.sidebar.annotation_tag_recolor_requested.connect(self._recolor_annotation_tag_global)
        self.sidebar.annotation_group_edit_requested.connect(self._edit_annotation_group)
        self.sidebar.fulltext_hit_activated.connect(self._on_fulltext_hit)
        self.sidebar.page_thumb_activated.connect(self._on_thumb_jump)
        self.sidebar.page_favorite_activated.connect(self._on_page_favorite_jump)
        self.sidebar.page_favorites_reordered.connect(self._on_page_favorites_reordered)
        self.sidebar.documents_reordered.connect(self._on_documents_reordered)
        self.sidebar.line_favorite_activated.connect(self._on_line_favorite_jump)
        self.sidebar.line_favorite_label_edit.connect(self._edit_line_favorite_label)
        self.sidebar.line_favorites_reordered.connect(self._on_line_favorites_reordered)
        self.sidebar.pages_reordered.connect(self._on_thumbs_reordered)
        self.sidebar.page_rotate_requested.connect(self._on_thumb_rotate)
        self.sidebar.page_duplicate_requested.connect(self._on_thumb_duplicate)
        self.sidebar.page_delete_requested.connect(self._on_thumb_delete)
        self.sidebar.pages_batch_duplicate_requested.connect(self._on_thumbs_batch_duplicate)
        self.sidebar.pages_batch_delete_requested.connect(self._on_thumbs_batch_delete)
        self.sidebar.pages_batch_rotate_requested.connect(self._on_thumbs_batch_rotate)
        self.sidebar.pages_batch_extract_requested.connect(self._on_thumbs_batch_extract)
        self.sidebar.pages_batch_open_requested.connect(self._on_thumbs_batch_open)
        self.sidebar.annotation_group_export_requested.connect(self._on_ann_group_export)
        splitter.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.editor_pane = EditorPane()
        self.editor = self.editor_pane.editor
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.line_bookmarks_changed.connect(self._on_line_bookmarks_changed)
        self.editor.cursorPositionChanged.connect(self._on_editor_cursor_changed)
        self.pdf_view = PdfViewer()
        self.pdf_view.status.connect(self._set_status)
        self.pdf_view.annotations_changed.connect(self._refresh_pdf_marks)
        self.pdf_view.annotations_changed.connect(self._refresh_undo_hint)
        # Toolbar-Undo und Ctrl+Z: Tag-Rename-Filter nach einstufigem Undo mitziehen
        _pdf_undo = self.pdf_view.undo_annotation

        def _undo_annotation_with_tag_revert() -> bool:
            ok = bool(_pdf_undo())
            if ok:
                self._revert_tag_filter_after_rename_undo()
                self._refresh_undo_hint()
            return ok

        self.pdf_view.undo_annotation = _undo_annotation_with_tag_revert  # type: ignore[method-assign]
        self.pdf_view.page_favorites_changed.connect(self._refresh_page_favorites)
        self.pdf_view.page_changed.connect(self._on_pdf_page_changed)
        self.pdf_view.zoom_changed.connect(self._on_pdf_zoom_changed)
        self.pdf_view.document_changed.connect(self._on_pdf_document_changed)
        self.pdf_view.grayscale_changed.connect(self._sync_grayscale_action)
        self.pdf_view.night_mode_changed.connect(self._sync_night_action)
        self.pdf_view.two_page_spread_changed.connect(self._sync_spread_action)
        self.pdf_view.continuous_scroll_changed.connect(self._sync_continuous_action)
        self.pdf_view.annotations_layer_changed.connect(self._sync_ann_layer_action)
        self.pdf_view.annotations_lock_changed.connect(self._sync_ann_lock_action)
        self.pdf_view.page_boxes_changed.connect(self._sync_page_boxes_action)
        self.pdf_view.page_number_overlay_changed.connect(
            self._sync_page_number_overlay_action
        )
        self.pdf_view.printer_marks_changed.connect(self._sync_printer_marks_action)
        self.image_label = QLabel(alignment=Qt.AlignCenter)
        self.image_label.setText("Bildvorschau")
        self.stack.addWidget(self.editor_pane)  # 0
        self.stack.addWidget(self.pdf_view)  # 1
        self.stack.addWidget(self.image_label)  # 2
        self.stack.currentChanged.connect(lambda *_: self._apply_doc_split_sync_scroll())
        self.stack.currentChanged.connect(lambda *_: self._update_doc_status())
        # Doc-Split: horizontal (nebeneinander) oder vertikal (übereinander)
        split_orient = (
            Qt.Vertical if get_editor_doc_split_vertical() else Qt.Horizontal
        )
        self.doc_splitter = QSplitter(split_orient)
        self.doc_splitter.addWidget(self.stack)
        self.secondary_wrap = QWidget()
        sec_lay = QVBoxLayout(self.secondary_wrap)
        sec_lay.setContentsMargins(4, 4, 4, 4)
        sec_lay.setSpacing(2)
        self.secondary_title = QLabel("Zweites Dokument")
        self.secondary_title.setStyleSheet("color: #555; font-size: 11px; padding: 2px 0;")
        self.secondary_title.setToolTip(
            "Zweites Dokument im geteilten Fenster (Anzeige): PDF oder Editor — Mischung erlaubt"
        )
        sec_lay.addWidget(self.secondary_title)
        self.secondary_stack = QStackedWidget()
        self.secondary_pane = EditorPane()
        self.secondary_editor = self.secondary_pane.editor
        self.secondary_editor.setReadOnly(True)
        # Vorschau aus, ohne globale Markdown-Einstellung zu überschreiben
        self.secondary_pane._preview_visible = False
        self.secondary_pane.preview.setVisible(False)
        self.secondary_pdf = PdfViewer()
        self.secondary_pdf.status.connect(self._set_status)
        # Zweit-Panel: nur Anzeige (Annotationen gesperrt)
        try:
            self.secondary_pdf.set_annotations_locked(True)
        except Exception:
            pass
        self.secondary_stack.addWidget(self.secondary_pane)  # 0 Editor
        self.secondary_stack.addWidget(self.secondary_pdf)  # 1 PDF
        sec_lay.addWidget(self.secondary_stack, 1)
        self.doc_splitter.addWidget(self.secondary_wrap)
        self.doc_splitter.setStretchFactor(0, 3)
        self.doc_splitter.setStretchFactor(1, 2)
        self.secondary_wrap.setVisible(bool(get_editor_doc_split()))
        splitter.addWidget(self.doc_splitter)
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
        self.unsaved_status_label = QLabel("0 ungespeichert")
        self.unsaved_status_label.setStyleSheet("padding-right: 10px; color: #555;")
        self.unsaved_status_label.setToolTip(
            "Ungespeicherte Tabs — Klick öffnet Liste zum Wechseln"
        )
        self.unsaved_status_label.setCursor(Qt.PointingHandCursor)
        self.unsaved_status_label.mousePressEvent = (  # type: ignore[method-assign]
            lambda e: self._on_unsaved_status_clicked(e)
        )
        sb.addPermanentWidget(self.unsaved_status_label)
        self._pending_blink_active = False
        self._pending_was_pending = False
        self._split_scroll_syncing = False
        self.undo_hint_label = QLabel("Ctrl+Z · Letzte Aktion rückgängig")
        self.undo_hint_label.setObjectName("undoHint")
        self.undo_hint_label.setStyleSheet(
            "QLabel#undoHint { color: #777; padding-right: 8px; font-size: 11px; }"
        )
        self.undo_hint_label.setToolTip(
            "Rückgängig: Editor · PDF-Annotationen (benannt, z. B. Tag umbenennen) · Seiten (Ctrl+Z)"
        )
        sb.addPermanentWidget(self.undo_hint_label)
        self.version_label = QLabel(f"v{__version__}")
        self.version_label.setStyleSheet("color: #666; padding-right: 8px;")
        sb.addPermanentWidget(self.version_label)
        self.license_label = QLabel()
        sb.addPermanentWidget(self.license_label)
        self._update_doc_status()

    def _build_menus(self):
        mb = self.menuBar()

        m_file = mb.addMenu("&Datei")
        m_new = m_file.addMenu("Neu")
        act_new = QAction("Leeres Dokument", self)
        act_new.setShortcut(QKeySequence.New)
        act_new.setToolTip("Neues leeres Textdokument")
        act_new.triggered.connect(lambda: self.new_doc("empty"))
        m_new.addAction(act_new)
        act_new_brief = QAction("Brief…", self)
        act_new_brief.setToolTip("Neues Dokument aus Brief-Vorlage")
        act_new_brief.triggered.connect(lambda: self.new_doc("brief"))
        m_new.addAction(act_new_brief)
        act_new_notiz = QAction("Notiz…", self)
        act_new_notiz.setToolTip("Neues Dokument aus Notiz-Vorlage")
        act_new_notiz.triggered.connect(lambda: self.new_doc("notiz"))
        m_new.addAction(act_new_notiz)
        self._m_user_templates = m_new.addMenu("Meine Vorlagen")
        self._refresh_user_template_menu()
        act_tpl_folder = QAction("Vorlagen-Ordner öffnen…", self)
        act_tpl_folder.setToolTip(
            "Gespiegelte Nutzer-Vorlagen im Dateimanager öffnen (Explorer)"
        )
        act_tpl_folder.triggered.connect(self._open_user_templates_folder)
        m_new.addAction(act_tpl_folder)
        act_tpl_export = QAction("Vorlagen als Zip exportieren…", self)
        act_tpl_export.setToolTip("Nutzer-Vorlagen-Ordner als Zip speichern")
        act_tpl_export.triggered.connect(self._export_user_templates_zip)
        m_new.addAction(act_tpl_export)
        act_tpl_import = QAction("Vorlagen aus Zip importieren…", self)
        act_tpl_import.setToolTip("Nutzer-Vorlagen aus Zip laden (merge)")
        act_tpl_import.triggered.connect(self._import_user_templates_zip)
        m_new.addAction(act_tpl_import)
        act_tpl_order = QAction("Vorlagen-Reihenfolge…", self)
        act_tpl_order.setToolTip(
            "Nutzer-Vorlagen per Drag umsortieren und Reihenfolge speichern"
        )
        act_tpl_order.triggered.connect(self._reorder_user_templates_dialog)
        m_new.addAction(act_tpl_order)
        act_save_tpl = QAction("Als Vorlage speichern…", self)
        act_save_tpl.setToolTip(
            "Aktuelles Editor-Dokument als wiederverwendbare Vorlage speichern"
        )
        act_save_tpl.triggered.connect(self._save_doc_as_template)
        m_file.addAction(act_save_tpl)

        act_open = QAction("Öffnen…", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self.open_dialog)
        m_file.addAction(act_open)
        act_open_enc = QAction("Öffnen mit Encoding…", self)
        act_open_enc.setToolTip("Textdatei mit UTF-8 oder Latin-1 öffnen")
        act_open_enc.triggered.connect(self.open_dialog_with_encoding)
        m_file.addAction(act_open_enc)

        self._recent_menu = m_file.addMenu("Zuletzt geöffnet")
        self._workspace_menu = m_file.addMenu("Projekt-Ordner")
        m_file.addSeparator()

        act_save = QAction("Speichern", self)
        act_save.setShortcut(QKeySequence.Save)
        act_save.triggered.connect(self.save_doc)
        m_file.addAction(act_save)
        act_save_enc = QAction("Speichern mit Encoding…", self)
        act_save_enc.setToolTip("Aktuelles Textdokument mit UTF-8 oder Latin-1 speichern")
        act_save_enc.triggered.connect(self.save_doc_with_encoding)
        m_file.addAction(act_save_enc)
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
        act_close_others = QAction("Andere Tabs schließen", self)
        act_close_others.setShortcut(QKeySequence("Ctrl+Shift+W"))
        act_close_others.setToolTip(
            "Alle Dokumente in der Sidebar schließen außer dem aktuellen"
        )
        act_close_others.triggered.connect(self.close_other_tabs)
        m_file.addAction(act_close_others)
        act_dup_tab = QAction("Tab duplizieren", self)
        act_dup_tab.setShortcut(QKeySequence("Ctrl+Shift+T"))
        act_dup_tab.setToolTip(
            "Editor: Inhalt als neues Dokument klonen · Datei mit Pfad: optional erneut öffnen"
        )
        act_dup_tab.triggered.connect(self.duplicate_tab)
        m_file.addAction(act_dup_tab)
        act_compare_tabs = QAction("Dateien vergleichen…", self)
        act_compare_tabs.setShortcut(QKeySequence("Ctrl+Alt+D"))
        act_compare_tabs.setToolTip(
            "Zwei Tabs/Dateien Side-by-Side vergleichen (einfacher Zeilen-Diff)"
        )
        act_compare_tabs.triggered.connect(self._compare_text_tabs)
        m_file.addAction(act_compare_tabs)
        act_reopen = QAction("Erneut öffnen", self)
        act_reopen.setShortcut(QKeySequence("Ctrl+Alt+Shift+O"))
        act_reopen.setToolTip("Aktuelle Datei vom Datenträger neu laden")
        act_reopen.triggered.connect(self.reopen_current)
        m_file.addAction(act_reopen)
        act_workdir = QAction("Arbeitsverzeichnis öffnen", self)
        act_workdir.setShortcut(QKeySequence("Ctrl+Shift+E"))
        act_workdir.setToolTip(
            "Ordner der aktuellen Datei (sonst Prozess-CWD) im Dateimanager öffnen"
        )
        act_workdir.triggered.connect(self._open_workdir)
        m_file.addAction(act_workdir)
        m_export = m_file.addMenu("Exportieren")
        for title, fmt in [
            ("Als HTML…", "html"),
            ("Als DOCX…", "docx"),
            ("Als PDF…", "pdf"),
        ]:
            a = QAction(title, self)
            a.triggered.connect(lambda checked=False, f=fmt: self._export_editor(f))
            m_export.addAction(a)
        m_export.addSeparator()
        act_exp_prof_save = QAction("Export-Profil speichern…", self)
        act_exp_prof_save.setToolTip("DPI / Format / Zielordner als Profil speichern")
        act_exp_prof_save.triggered.connect(self._save_export_profile)
        m_export.addAction(act_exp_prof_save)
        act_exp_prof_apply = QAction("Export-Profil anwenden…", self)
        act_exp_prof_apply.setToolTip("Gespeichertes Profil (DPI/Format/Ziel) aktivieren")
        act_exp_prof_apply.triggered.connect(self._apply_export_profile)
        m_export.addAction(act_exp_prof_apply)
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
            ("Kopieren", self._copy),
            ("Einfügen", self.editor.paste),
        ]:
            a = QAction(name, self)
            if name == "Kopieren":
                a.setToolTip(
                    "Editor-Auswahl oder PDF-Textauswahl (Auswahl-Werkzeug + Aufziehen) → Zwischenablage"
                )
            a.triggered.connect(slot)
            m_edit.addAction(a)
        act_paste_img = QAction("Bild aus Zwischenablage…", self)
        act_paste_img.setShortcut(QKeySequence("Ctrl+Shift+V"))
        act_paste_img.triggered.connect(self._paste_clipboard_image)
        m_edit.addAction(act_paste_img)
        self._clipboard_history_menu = m_edit.addMenu("Zwischenablage-Verlauf")
        self._clipboard_history_menu.setToolTip(
            "Letzte 3 eingefügten Textschnipsel erneut einfügen"
        )
        self._clipboard_history_menu.aboutToShow.connect(self._rebuild_clipboard_history_menu)
        m_edit.addSeparator()
        act_find = QAction("Suchen…", self)
        act_find.setShortcut(QKeySequence.Find)
        act_find.triggered.connect(self._focus_search)
        m_edit.addAction(act_find)
        act_find_next = QAction("Weitersuchen", self)
        act_find_next.setShortcut(QKeySequence.FindNext)  # F3
        act_find_next.setToolTip(
            "Nächster Suchtreffer (F3) — PDF: Highlight auf Seite, Editor: nächster Treffer"
        )
        act_find_next.triggered.connect(self._on_search_next)
        m_edit.addAction(act_find_next)
        act_find_prev = QAction("Rückwärtssuchen", self)
        act_find_prev.setShortcut(QKeySequence.FindPrevious)  # Shift+F3
        act_find_prev.setToolTip(
            "Vorheriger Suchtreffer (Shift+F3) — PDF: Highlight auf Seite"
        )
        act_find_prev.triggered.connect(self._on_search_prev)
        m_edit.addAction(act_find_prev)
        act_find_repl = QAction("Suchen und Ersetzen…", self)
        act_find_repl.setShortcut(QKeySequence("Ctrl+R"))
        act_find_repl.setToolTip("Find/Replace im Texteditor")
        act_find_repl.triggered.connect(self._find_replace)
        m_edit.addAction(act_find_repl)
        act_search_csv = QAction("Suchergebnisse als CSV exportieren…", self)
        act_search_csv.setToolTip("Aktuelle Trefferliste (Sidebar) als CSV speichern")
        act_search_csv.triggered.connect(lambda: self._on_search_export("csv"))
        m_edit.addAction(act_search_csv)
        act_search_json = QAction("Suchergebnisse als JSON exportieren…", self)
        act_search_json.setToolTip(
            "Aktuelle Trefferliste (Sidebar) als JSON speichern (ildsearch-v1)"
        )
        act_search_json.triggered.connect(lambda: self._on_search_export("json"))
        m_edit.addAction(act_search_json)
        act_goto = QAction("Gehe zu Zeile…", self)
        act_goto.setShortcut(QKeySequence("Ctrl+G"))
        act_goto.setToolTip("Editor: Zeile · PDF: Seite (Ctrl+G)")
        act_goto.triggered.connect(self._goto_line_or_page)
        m_edit.addAction(act_goto)
        act_bookmark = QAction("Zeile favorisieren / Lesezeichen", self)
        act_bookmark.setShortcut(QKeySequence("Ctrl+F2"))
        act_bookmark.setToolTip(
            "Editor: aktuelle Zeile als Lesezeichen (Klick auf Zeilennummer)"
        )
        act_bookmark.triggered.connect(self._toggle_line_bookmark)
        m_edit.addAction(act_bookmark)
        act_bm_next = QAction("Nächstes Zeilen-Lesezeichen", self)
        act_bm_next.setShortcut(QKeySequence("F2"))
        act_bm_next.setToolTip("Zum nächsten Editor-Lesezeichen springen")
        act_bm_next.triggered.connect(self._goto_next_line_bookmark)
        m_edit.addAction(act_bm_next)
        act_bm_prev = QAction("Vorheriges Zeilen-Lesezeichen", self)
        act_bm_prev.setShortcut(QKeySequence("Shift+F2"))
        act_bm_prev.setToolTip("Zum vorherigen Editor-Lesezeichen springen")
        act_bm_prev.triggered.connect(self._goto_prev_line_bookmark)
        m_edit.addAction(act_bm_prev)
        act_bm_clear = QAction("Alle Zeilen-Lesezeichen löschen", self)
        act_bm_clear.setToolTip("Alle Editor-Zeilenfavoriten entfernen")
        act_bm_clear.triggered.connect(self._clear_line_bookmarks)
        m_edit.addAction(act_bm_clear)
        act_bm_export = QAction("Zeilen-Lesezeichen als JSON exportieren…", self)
        act_bm_export.setToolTip("Editor-Lesezeichen als ildbm-v1 JSON speichern")
        act_bm_export.triggered.connect(self._export_line_bookmarks_json)
        m_edit.addAction(act_bm_export)
        act_bm_import = QAction("Zeilen-Lesezeichen aus JSON importieren…", self)
        act_bm_import.setToolTip("Editor-Lesezeichen aus JSON laden (ersetzen oder zusammenführen)")
        act_bm_import.triggered.connect(self._import_line_bookmarks_json)
        m_edit.addAction(act_bm_import)
        act_dup_line = QAction("Zeile / Annotation duplizieren", self)
        act_dup_line.setShortcut(QKeySequence("Ctrl+D"))
        act_dup_line.setToolTip(
            "Editor: Zeile/Auswahl duplizieren; PDF: ausgewählte Annotation (Ctrl+D)"
        )
        act_dup_line.triggered.connect(self._duplicate_current)
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
        act_sort_az = QAction("Zeilen sortieren (A–Z)", self)
        act_sort_az.setShortcut(QKeySequence("Ctrl+Shift+O"))
        act_sort_az.setToolTip("Ausgewählte Zeilen alphabetisch sortieren (ohne Auswahl: gesamte Datei)")
        act_sort_az.triggered.connect(self._sort_lines_az)
        m_edit.addAction(act_sort_az)
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
        act_all_upper = QAction("Alles großschreiben", self)
        act_all_upper.setShortcut(QKeySequence("Ctrl+Alt+Shift+U"))
        act_all_upper.setToolTip("Gesamten Editor-Text in Großbuchstaben")
        act_all_upper.triggered.connect(lambda: self._transform_document_case("upper"))
        m_edit.addAction(act_all_upper)
        act_all_lower = QAction("Alles kleinschreiben", self)
        act_all_lower.setShortcut(QKeySequence("Ctrl+Alt+Shift+L"))
        act_all_lower.setToolTip("Gesamten Editor-Text in Kleinbuchstaben")
        act_all_lower.triggered.connect(lambda: self._transform_document_case("lower"))
        m_edit.addAction(act_all_lower)
        m_snippets = m_edit.addMenu("Textbausteine")
        for i in range(3):
            a_ins = QAction(f"Einfügen {i + 1}", self)
            a_ins.setShortcut(QKeySequence(f"Ctrl+Alt+{i + 1}"))
            a_ins.setToolTip(f"Gespeicherten Textbaustein {i + 1} an Cursor einfügen")
            a_ins.triggered.connect(lambda checked=False, idx=i: self._insert_snippet(idx))
            m_snippets.addAction(a_ins)
        m_snippets.addSeparator()
        for i in range(3):
            a_save = QAction(f"Auswahl → Slot {i + 1}", self)
            a_save.setToolTip(f"Aktuelle Auswahl (oder Zeile) als Textbaustein {i + 1} speichern")
            a_save.triggered.connect(lambda checked=False, idx=i: self._save_snippet(idx))
            m_snippets.addAction(a_save)
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
        m_specialchars = m_edit.addMenu("Sonderzeichen einfügen")
        act_shy = QAction("Weiches Trennzeichen (Soft-Hyphen)", self)
        act_shy.setShortcut(QKeySequence("Ctrl+Shift+-"))
        act_shy.setToolTip("U+00AD Soft Hyphen an Cursor einfügen")
        act_shy.triggered.connect(self._insert_soft_hyphen)
        m_specialchars.addAction(act_shy)
        act_nbsp = QAction("Geschütztes Leerzeichen (NBSP)", self)
        act_nbsp.setShortcut(QKeySequence("Ctrl+Shift+Space"))
        act_nbsp.setToolTip(
            "U+202F Narrow No-Break Space an Cursor (Qt behält U+00A0 nicht)"
        )
        act_nbsp.triggered.connect(self._insert_nbsp)
        m_specialchars.addAction(act_nbsp)
        act_spell = QAction("Rechtschreibung prüfen…", self)
        act_spell.setShortcut(QKeySequence("F7"))
        act_spell.setToolTip(
            "Wortliste aus Einstellungen laden und unbekannte Wörter markieren (ohne Spell-Lib)"
        )
        act_spell.triggered.connect(self._check_spelling)
        m_edit.addAction(act_spell)
        act_spell_clear = QAction("Rechtschreibmarkierungen löschen", self)
        act_spell_clear.triggered.connect(self._clear_spelling)
        m_edit.addAction(act_spell_clear)
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
        act_sel_note = QAction("Auswahl → Notiz…", self)
        act_sel_note.setShortcut(QKeySequence("Ctrl+Alt+N"))
        act_sel_note.setToolTip(
            "PDF-Textauswahl als Sticky/Notiz; optional zusätzlich Highlight (Checkbox)"
        )
        act_sel_note.triggered.connect(self._sticky_from_selection)
        m_edit.addAction(act_sel_note)
        act_edit_tags = QAction("Annotation-Tags bearbeiten…", self)
        act_edit_tags.setShortcut(QKeySequence("Ctrl+Alt+T"))
        act_edit_tags.setToolTip("Freie Tags/Labels der ausgewählten Annotation (filterbar)")
        act_edit_tags.triggered.connect(self._edit_annotation_tags)
        m_edit.addAction(act_edit_tags)
        act_edit_group = QAction("Annotationsgruppe umbenennen/Farbe…", self)
        act_edit_group.setShortcut(QKeySequence("Ctrl+Alt+G"))
        act_edit_group.setToolTip(
            "Seiten-Gruppe in der Annotationsliste umbenennen und farblich markieren"
        )
        act_edit_group.triggered.connect(self._edit_annotation_group)
        m_edit.addAction(act_edit_group)
        act_recolor_ann = QAction("Auswahl-Farbe ändern…", self)
        act_recolor_ann.setShortcut(QKeySequence("Ctrl+Alt+Shift+F"))
        act_recolor_ann.setToolTip(
            "Farbe aller ausgewählten Annotationen auf einmal ändern (Batch)"
        )
        act_recolor_ann.triggered.connect(self._recolor_selected_annotations)
        m_edit.addAction(act_recolor_ann)
        act_opacity_ann = QAction("Auswahl-Deckkraft ändern…", self)
        act_opacity_ann.setShortcut(QKeySequence("Ctrl+Alt+Shift+O"))
        act_opacity_ann.setToolTip(
            "Deckkraft aller ausgewählten Annotationen auf einmal ändern (Batch)"
        )
        act_opacity_ann.triggered.connect(self._opacity_selected_annotations)
        m_edit.addAction(act_opacity_ann)
        m_align = m_edit.addMenu("Auswahl ausrichten")
        m_align.setToolTip("Mehrfachauswahl ausrichten / verteilen (H/V)")
        act_align_l = QAction("Links", self)
        act_align_l.setToolTip("Ausgewählte Annotationen links ausrichten (≥2)")
        act_align_l.triggered.connect(
            lambda: self._align_selected_annotations("left")
        )
        m_align.addAction(act_align_l)
        act_align_c = QAction("Zentrieren", self)
        act_align_c.setToolTip("Ausgewählte Annotationen horizontal zentrieren (≥2)")
        act_align_c.triggered.connect(
            lambda: self._align_selected_annotations("center")
        )
        m_align.addAction(act_align_c)
        act_align_r = QAction("Rechts", self)
        act_align_r.setToolTip("Ausgewählte Annotationen rechts ausrichten (≥2)")
        act_align_r.triggered.connect(
            lambda: self._align_selected_annotations("right")
        )
        m_align.addAction(act_align_r)
        m_align.addSeparator()
        act_align_t = QAction("Oben", self)
        act_align_t.setToolTip("Ausgewählte Annotationen oben ausrichten (≥2)")
        act_align_t.triggered.connect(
            lambda: self._align_selected_annotations("top")
        )
        m_align.addAction(act_align_t)
        act_align_m = QAction("Vertikal mittig", self)
        act_align_m.setToolTip("Ausgewählte Annotationen vertikal mittig ausrichten (≥2)")
        act_align_m.triggered.connect(
            lambda: self._align_selected_annotations("middle")
        )
        m_align.addAction(act_align_m)
        act_align_b = QAction("Unten", self)
        act_align_b.setToolTip("Ausgewählte Annotationen unten ausrichten (≥2)")
        act_align_b.triggered.connect(
            lambda: self._align_selected_annotations("bottom")
        )
        m_align.addAction(act_align_b)
        m_align.addSeparator()
        act_dist_h = QAction("Horizontal verteilen", self)
        act_dist_h.setToolTip(
            "Ausgewählte Annotationen horizontal gleichmäßig verteilen (≥3)"
        )
        act_dist_h.triggered.connect(self._distribute_selected_annotations_horizontal)
        m_align.addAction(act_dist_h)
        act_dist_v = QAction("Vertikal verteilen", self)
        act_dist_v.setToolTip(
            "Ausgewählte Annotationen vertikal gleichmäßig verteilen (≥3)"
        )
        act_dist_v.triggered.connect(self._distribute_selected_annotations_vertical)
        m_align.addAction(act_dist_v)
        m_align.addSeparator()
        act_group = QAction("Gruppieren", self)
        act_group.setShortcut(QKeySequence("Ctrl+Alt+Shift+G"))
        act_group.setToolTip(
            "Ausgewählte Annotationen gruppieren (≥2) — temporäre Gruppen-ID im Sidecar "
            "(Ctrl+Alt+Shift+G)"
        )
        act_group.triggered.connect(self._group_selected_annotations)
        m_align.addAction(act_group)
        act_ungroup = QAction("Entgruppieren", self)
        act_ungroup.setShortcut(QKeySequence("Ctrl+Alt+Shift+Y"))
        act_ungroup.setToolTip(
            "Auswahl entgruppieren (group_id leeren) — Ctrl+Alt+Shift+Y"
        )
        act_ungroup.triggered.connect(self._ungroup_selected_annotations)
        m_align.addAction(act_ungroup)
        act_group_lock = QAction("Gruppen-Sperre umschalten", self)
        act_group_lock.setShortcut(QKeySequence("Ctrl+Alt+Shift+L"))
        act_group_lock.setToolTip(
            "Gruppenmitglieder der Auswahl sperren/entsperren (nicht verschiebbar) "
            "— Ctrl+Alt+Shift+L"
        )
        act_group_lock.triggered.connect(self._toggle_selected_group_lock)
        m_align.addAction(act_group_lock)
        act_group_edit = QAction("Gruppe umbenennen / Farbe…", self)
        act_group_edit.setShortcut(QKeySequence("Ctrl+Alt+Shift+N"))
        act_group_edit.setToolTip(
            "Temporäre Ann.-Gruppe umbenennen und Farbe der Sidecar-Markierung "
            "— Ctrl+Alt+Shift+N"
        )
        act_group_edit.triggered.connect(self._edit_selected_ann_group)
        m_align.addAction(act_group_edit)
        act_dup_ann = QAction("Annotation duplizieren", self)
        act_dup_ann.setShortcut(QKeySequence("Ctrl+Shift+D"))
        act_dup_ann.setToolTip(
            "Ausgewählte Annotation kopieren (leicht versetzt); im PDF auch Ctrl+D"
        )
        act_dup_ann.triggered.connect(self._duplicate_annotation)
        m_edit.addAction(act_dup_ann)
        act_copy_ann = QAction("Annotationen kopieren", self)
        act_copy_ann.setShortcut(QKeySequence("Ctrl+Alt+C"))
        act_copy_ann.setToolTip("Auswahl in Zwischenablage (Einfügen auf anderer Seite)")
        act_copy_ann.triggered.connect(self._copy_annotations)
        m_edit.addAction(act_copy_ann)
        act_paste_ann = QAction("Annotationen einfügen", self)
        act_paste_ann.setShortcut(QKeySequence("Ctrl+Alt+V"))
        act_paste_ann.setToolTip("Kopierte Annotationen auf aktueller Seite einfügen")
        act_paste_ann.triggered.connect(self._paste_annotations)
        m_edit.addAction(act_paste_ann)
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
            get_editor_minimap,
            get_pdf_grayscale,
            get_pdf_night_mode,
        )

        self._line_numbers_action.setChecked(get_editor_line_numbers())
        self._line_numbers_action.setToolTip("Zeilennummern im Texteditor anzeigen")
        self._line_numbers_action.toggled.connect(self._toggle_line_numbers)
        m_view.addAction(self._line_numbers_action)
        self._indent_guides_action = QAction("Einrückungs-Guides", self)
        self._indent_guides_action.setCheckable(True)
        from instantlensdoc.core.app_settings import (
            get_editor_current_line_highlight,
            get_editor_indent_guides,
        )

        self._indent_guides_action.setChecked(get_editor_indent_guides())
        self._indent_guides_action.setToolTip(
            "Vertikale Linien an Tab-Stops für führende Einrückung"
        )
        self._indent_guides_action.toggled.connect(self._toggle_indent_guides)
        m_view.addAction(self._indent_guides_action)
        self._current_line_hl_action = QAction("Aktuelle Zeile hervorheben", self)
        self._current_line_hl_action.setCheckable(True)
        self._current_line_hl_action.setChecked(get_editor_current_line_highlight())
        self._current_line_hl_action.setToolTip(
            "Aktuelle Editorzeile farblich hervorheben (auch in Einstellungen)"
        )
        self._current_line_hl_action.toggled.connect(self._toggle_current_line_highlight)
        m_view.addAction(self._current_line_hl_action)
        self._minimap_action = QAction("Editor-Minimap", self)
        self._minimap_action.setCheckable(True)
        self._minimap_action.setChecked(get_editor_minimap())
        self._minimap_action.setToolTip(
            "Einfache Linien-Übersicht rechts + dickere Scrollbar (optional)"
        )
        self._minimap_action.setShortcut(QKeySequence("Ctrl+Shift+I"))
        self._minimap_action.toggled.connect(self._toggle_minimap)
        m_view.addAction(self._minimap_action)
        self._md_preview_action = QAction("Markdown-Vorschau", self)
        self._md_preview_action.setCheckable(True)
        self._md_preview_action.setChecked(get_editor_markdown_preview())
        self._md_preview_action.setToolTip("Editor-Split: Markdown-Vorschau ein/aus")
        self._md_preview_action.setShortcut(QKeySequence("Ctrl+Shift+M"))
        self._md_preview_action.toggled.connect(self._toggle_markdown_preview)
        m_view.addAction(self._md_preview_action)
        self._doc_split_action = QAction("Fenster teilen (zwei Docs)", self)
        self._doc_split_action.setCheckable(True)
        self._doc_split_action.setChecked(get_editor_doc_split())
        self._doc_split_action.setToolTip(
            "Hauptfenster teilen: aktuelles Dokument + zweites Tab "
            "(horizontal nebeneinander oder vertikal übereinander)"
        )
        self._doc_split_action.setShortcut(QKeySequence("Ctrl+\\"))
        self._doc_split_action.toggled.connect(self._toggle_doc_split)
        m_view.addAction(self._doc_split_action)
        self._doc_split_vertical_action = QAction("Vertikaler Split (übereinander)", self)
        self._doc_split_vertical_action.setCheckable(True)
        self._doc_split_vertical_action.setChecked(get_editor_doc_split_vertical())
        self._doc_split_vertical_action.setToolTip(
            "Doc-Split vertikal (übereinander) statt horizontal (nebeneinander)"
        )
        self._doc_split_vertical_action.setShortcut(QKeySequence("Ctrl+Shift+\\"))
        self._doc_split_vertical_action.toggled.connect(self._toggle_doc_split_vertical)
        m_view.addAction(self._doc_split_vertical_action)
        self._doc_split_sync_action = QAction("Sync-Scroll (geteilte Docs)", self)
        self._doc_split_sync_action.setCheckable(True)
        self._doc_split_sync_action.setChecked(get_editor_doc_split_sync_scroll())
        self._doc_split_sync_action.setToolTip(
            "Vertikales Scrollen in beiden Split-Panes synchronisieren (optional)"
        )
        self._doc_split_sync_action.setShortcut(QKeySequence("Ctrl+Alt+\\"))
        self._doc_split_sync_action.toggled.connect(self._toggle_doc_split_sync_scroll)
        m_view.addAction(self._doc_split_sync_action)
        act_sec_doc = QAction("Zweites Dokument wählen…", self)
        act_sec_doc.setToolTip("Datei für die rechte Split-Ansicht aus offenen Tabs wählen")
        act_sec_doc.triggered.connect(self._pick_secondary_document)
        m_view.addAction(act_sec_doc)
        self._soft_wrap_action = QAction("Wortumbruch", self)
        self._soft_wrap_action.setCheckable(True)
        self._soft_wrap_action.setChecked(get_editor_soft_wrap())
        self._soft_wrap_action.setToolTip(
            "Wortumbruch (Soft-Wrap) am Fensterrand im Texteditor — persistiert"
        )
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
        from instantlensdoc.core.app_settings import (
            get_pdf_continuous_scroll,
            get_pdf_two_page_spread,
        )

        self._spread_action = QAction("Zwei-Seiten-Ansicht (Spread)", self)
        self._spread_action.setCheckable(True)
        self._spread_action.setChecked(get_pdf_two_page_spread())
        self._spread_action.setToolTip(
            "Aktuelle und nächste PDF-Seite nebeneinander (Ctrl+2 / Toolbar 2S)"
        )
        self._spread_action.setShortcut(QKeySequence("Ctrl+2"))
        self._spread_action.toggled.connect(self._toggle_two_page_spread)
        m_view.addAction(self._spread_action)
        self._continuous_action = QAction("Continuous Scroll", self)
        self._continuous_action.setCheckable(True)
        self._continuous_action.setChecked(get_pdf_continuous_scroll())
        self._continuous_action.setToolTip(
            "Seiten untereinander scrollen statt Einzelseite (Ctrl+3 / Toolbar CS); schließt Spread aus"
        )
        self._continuous_action.setShortcut(QKeySequence("Ctrl+3"))
        self._continuous_action.toggled.connect(self._toggle_continuous_scroll)
        m_view.addAction(self._continuous_action)
        self._ann_layer_action = QAction("Annotation-Layer", self)
        self._ann_layer_action.setCheckable(True)
        self._ann_layer_action.setChecked(get_annotations_visible())
        self._ann_layer_action.setToolTip("Annotationen auf der PDF-Seite ein-/ausblenden")
        self._ann_layer_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
        self._ann_layer_action.toggled.connect(self._toggle_ann_layer)
        m_view.addAction(self._ann_layer_action)
        from instantlensdoc.core.app_settings import (
            get_annotations_locked,
            get_show_page_boxes,
            get_show_printer_marks,
        )

        self._ann_lock_action = QAction("Annotationen sperren", self)
        self._ann_lock_action.setCheckable(True)
        self._ann_lock_action.setChecked(get_annotations_locked())
        self._ann_lock_action.setToolTip(
            "Gesperrt: Annotationen nicht per Drag verschiebbar (Auswahl-Werkzeug)"
        )
        self._ann_lock_action.setShortcut(QKeySequence("Ctrl+Shift+L"))
        self._ann_lock_action.toggled.connect(self._toggle_ann_lock)
        m_view.addAction(self._ann_lock_action)
        self._page_boxes_action = QAction("Seitenrahmen / CropBox", self)
        self._page_boxes_action.setCheckable(True)
        self._page_boxes_action.setChecked(get_show_page_boxes())
        self._page_boxes_action.setToolTip(
            "MediaBox- und CropBox-Rahmen als Overlay auf der PDF-Seite"
        )
        self._page_boxes_action.setShortcut(QKeySequence("Ctrl+Shift+B"))
        self._page_boxes_action.toggled.connect(self._toggle_page_boxes)
        m_view.addAction(self._page_boxes_action)
        from instantlensdoc.core.app_settings import get_show_page_number_overlay

        self._page_num_overlay_action = QAction("Seitennummer-Overlay", self)
        self._page_num_overlay_action.setCheckable(True)
        self._page_num_overlay_action.setChecked(get_show_page_number_overlay())
        self._page_num_overlay_action.setToolTip(
            "Seitennummer als Overlay auf der PDF-Seite (auch in Einstellungen)"
        )
        self._page_num_overlay_action.toggled.connect(self._toggle_page_number_overlay)
        m_view.addAction(self._page_num_overlay_action)
        self._printer_marks_action = QAction("Druckermarken", self)
        self._printer_marks_action.setCheckable(True)
        self._printer_marks_action.setChecked(get_show_printer_marks())
        self._printer_marks_action.setToolTip(
            "Seitenrand-Druckermarken (Crop/Registration) als Overlay"
        )
        self._printer_marks_action.setShortcut(QKeySequence("Ctrl+Alt+M"))
        self._printer_marks_action.toggled.connect(self._toggle_printer_marks)
        m_view.addAction(self._printer_marks_action)
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
        act_fit = QAction("Seite einpassen (Fit-Page)", self)
        act_fit.setShortcut(QKeySequence("Ctrl+0"))
        act_fit.setToolTip("Aktuelle Seite in Viewport einpassen (Ctrl+0)")
        act_fit.triggered.connect(self._fit_page)
        m_view.addAction(act_fit)
        act_fit_w = QAction("Breite einpassen (Fit-Width)", self)
        act_fit_w.setShortcut(QKeySequence("Ctrl+9"))
        act_fit_w.setToolTip("Seitenbreite an Viewport anpassen (Ctrl+9)")
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
        act_zoom_default = QAction("Aktuellen Zoom als Standard speichern", self)
        act_zoom_default.setShortcut(QKeySequence("Ctrl+Shift+0"))
        act_zoom_default.setToolTip(
            "Aktuellen PDF-Zoom-% als Standard-Zoom in den Einstellungen speichern"
        )
        act_zoom_default.triggered.connect(self._save_current_zoom_as_default)
        m_view.addAction(act_zoom_default)
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
        act_sanitize = QAction("PDF bereinigen…", self)
        act_sanitize.setToolTip("PDF neu speichern; optional Metadaten entfernen")
        act_sanitize.triggered.connect(self._sanitize_pdf)
        m_pdf.addAction(act_sanitize)
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
        act_goto_page = QAction("Gehe zu Seite…", self)
        act_goto_page.setShortcut(QKeySequence("Ctrl+Shift+G"))
        act_goto_page.setToolTip("Seitennummer eingeben und springen (auch Ctrl+G im PDF)")
        act_goto_page.triggered.connect(self._goto_page)
        m_pdf.addAction(act_goto_page)
        m_pdf.addSeparator()
        for title, slot in [
            ("Annotationen speichern (Sidecar)", lambda: self.pdf_view.save_annotations()),
            ("Annotationen speichern unter…", lambda: self.pdf_view.save_annotations_as()),
            ("Annotationen laden", lambda: self.pdf_view.reload_annotations()),
            ("Annotationen als JSON exportieren…", lambda: self.pdf_view.export_annotations_json()),
            ("Annotationen als CSV exportieren…", lambda: self.pdf_view.export_annotations_csv()),
            (
                "Kommentar-Bericht (Markdown)…",
                lambda: self.pdf_view.export_annotations_report(default_fmt="md"),
            ),
            (
                "Kommentar-Bericht (Text)…",
                lambda: self.pdf_view.export_annotations_report(default_fmt="txt"),
            ),
            ("Annotationen flatten/bake exportieren…", lambda: self.pdf_view.export_annotations_flattened()),
            ("Annotationen aus JSON importieren…", lambda: self.pdf_view.import_annotations_json()),
            (
                "Annotation-Duplikate finden / zusammenführen…",
                lambda: self.pdf_view.merge_duplicate_annotations(),
            ),
        ]:
            a = QAction(title, self)
            a.triggered.connect(slot)
            m_pdf.addAction(a)
        act_cycle_color = QAction("Annotation-Farbe Palette-Zyklus", self)
        act_cycle_color.setShortcut(QKeySequence("Ctrl+Shift+C"))
        act_cycle_color.setToolTip("Nächste Highlight-Farbe aus der festen Palette")
        act_cycle_color.triggered.connect(lambda: self.pdf_view.cycle_annotation_color())
        m_pdf.addAction(act_cycle_color)
        act_rand_color = QAction("Annotation-Farbe randomisieren", self)
        act_rand_color.setShortcut(QKeySequence("Ctrl+Alt+Shift+C"))
        act_rand_color.setToolTip("Zufällige Highlight-Farbe aus der Palette")
        act_rand_color.triggered.connect(lambda: self.pdf_view.randomize_annotation_color())
        m_pdf.addAction(act_rand_color)
        m_pdf.addSeparator()
        for title, slot in [
            ("Lesezeichen hinzufügen…", self._outline_add),
            ("Lesezeichen löschen", self._outline_delete),
            ("Seite drehen 90° ⟳", lambda: self.pdf_view.rotate_current(90)),
            ("Seite drehen −90° ⟲", lambda: self.pdf_view.rotate_current(-90)),
            ("Stempel 90° drehen ↻", lambda: self.pdf_view.rotate_selected_stamp(90)),
            ("Seite horizontal spiegeln ↔", lambda: self.pdf_view.flip_current(horizontal=True)),
            ("Seite vertikal spiegeln ↕", lambda: self.pdf_view.flip_current(vertical=True)),
            ("Graustufen umschalten", lambda: self._toggle_grayscale(not self.pdf_view.grayscale_enabled())),
            ("Nachtmodus umschalten", lambda: self._toggle_night_mode(not self.pdf_view.night_mode_enabled())),
            ("Leere Seite einfügen", lambda: self.pdf_view.insert_blank_after_current()),
            ("Seite duplizieren", lambda: self.pdf_view.duplicate_current()),
            ("Seite löschen…", lambda: self.pdf_view.delete_current()),
            (
                "Annotationsgruppe umbenennen/Farbe…",
                lambda: self._edit_annotation_group(),
            ),
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
        act_page_hist = QAction("Seiten-Historie (Undo)…", self)
        act_page_hist.setShortcut(QKeySequence("Ctrl+Shift+H"))
        act_page_hist.setToolTip("Gelöschte/gedrehte Seiten aus dem Undo-Stack wiederherstellen")
        act_page_hist.triggered.connect(lambda: self.pdf_view.show_page_ops_history())
        m_pdf.addAction(act_page_hist)
        act_page_fav = QAction("Seite als Favorit umschalten", self)
        act_page_fav.setShortcut(QKeySequence("Ctrl+Shift+F"))
        act_page_fav.setToolTip("Aktuelle PDF-Seite als Favorit markieren/entfernen")
        act_page_fav.triggered.connect(lambda: self.pdf_view.toggle_page_favorite())
        m_pdf.addAction(act_page_fav)
        act_page_fav_jump = QAction("Seiten-Favoriten…", self)
        act_page_fav_jump.setShortcut(QKeySequence("Ctrl+Alt+F"))
        act_page_fav_jump.setToolTip("Zu markierten Favoriten-Seiten springen")
        act_page_fav_jump.triggered.connect(lambda: self.pdf_view.show_page_favorites())
        m_pdf.addAction(act_page_fav_jump)
        act_fav_export = QAction("Seiten-Favoriten als JSON exportieren…", self)
        act_fav_export.setToolTip("Favoritenliste als ildfav-v1 JSON speichern")
        act_fav_export.triggered.connect(lambda: self.pdf_view.export_page_favorites_json())
        m_pdf.addAction(act_fav_export)
        act_fav_import = QAction("Seiten-Favoriten aus JSON importieren…", self)
        act_fav_import.setToolTip("Favoritenliste aus JSON laden (ersetzen oder zusammenführen)")
        act_fav_import.triggered.connect(lambda: self.pdf_view.import_page_favorites_json())
        m_pdf.addAction(act_fav_import)
        m_pdf.addSeparator()
        for title, slot in [
            ("PDF-Text → Overlay…", lambda: self.pdf_view.import_text_overlays()),
            ("Text-Overlays einbrennen…", lambda: self.pdf_view.bake_overlays()),
            ("Text dieser Seite → Editor", self._extract_page_text_to_editor),
            ("Gesamten PDF-Text → Editor", self._extract_all_text_to_editor),
            ("Seitenbild → Editor", self._insert_page_image_to_editor),
            ("Alle Seitenbilder → Editor", self._insert_all_page_images_to_editor),
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
        a = QAction("OCR gesamtes PDF…", self)
        a.setToolTip("Batch-OCR aller Seiten mit Fortschrittsanzeige")
        a.triggered.connect(self._run_ocr_document)
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
        a = QAction("Erste Schritte…", self)
        a.setToolTip("Kurz-Wizard: Öffnen, Annotieren, Editor, 0.6-Highlights (4 Seiten)")
        a.triggered.connect(self._show_getting_started_wizard)
        m_help.addAction(a)
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
        a = QAction("Crash-Report erstellen…", self)
        a.setToolTip("Logordner als ZIP speichern (Support / Diagnose)")
        a.triggered.connect(self._create_crash_report)
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
        entries = recent_mod.load_recent_entries()
        self.sidebar.set_recent(entries)
        if self._recent_menu is None:
            return
        self._recent_menu.clear()
        if not entries:
            empty = QAction("(leer)", self)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)
        else:
            for path, exists in entries:
                label = str(path) if exists else f"{path} (fehlt)"
                a = QAction(label, self)
                if exists:
                    a.triggered.connect(lambda checked=False, p=path: self.open_path(p))
                else:
                    a.setEnabled(False)
                self._recent_menu.addAction(a)
        self._recent_menu.addSeparator()
        clear = QAction("Liste leeren", self)
        clear.triggered.connect(self._clear_recent)
        self._recent_menu.addAction(clear)

    def _remove_recent_path(self, path: str) -> None:
        """Einzelnen Recent-Eintrag entfernen (Sidebar-Kontextmenü)."""
        recent_mod.remove_recent(path)
        self._refresh_recent()
        self._set_status(f"Aus Zuletzt geöffnet entfernt: {Path(path).name}")

    def _refresh_workspaces(self):
        """Projekt-Ordner-Menü (letzte 5 Workspaces) neu aufbauen."""
        if self._workspace_menu is None:
            return
        self._workspace_menu.clear()
        act_choose = QAction("Projekt-Ordner wählen…", self)
        act_choose.setToolTip("Ordner als Workspace setzen (letzte 5 merken)")
        act_choose.triggered.connect(self._choose_project_workspace)
        self._workspace_menu.addAction(act_choose)
        act_open = QAction("Aktiven Projekt-Ordner öffnen", self)
        act_open.setToolTip("Aktiven Workspace im Dateimanager öffnen")
        act_open.triggered.connect(self._open_active_project_workspace)
        self._workspace_menu.addAction(act_open)
        self._workspace_menu.addSeparator()
        workspaces = get_project_workspaces()
        active = get_active_project_workspace()
        active_key = str(active.resolve()) if active else ""
        if not workspaces:
            empty = QAction("(keine Projekt-Ordner)", self)
            empty.setEnabled(False)
            self._workspace_menu.addAction(empty)
        else:
            for folder in workspaces:
                label = str(folder)
                try:
                    key = str(folder.resolve())
                except Exception:
                    key = str(folder)
                if key == active_key:
                    label = f"● {label}"
                a = QAction(label, self)
                a.setToolTip(f"Workspace aktivieren:\n{folder}")
                a.triggered.connect(
                    lambda checked=False, p=folder: self._activate_project_workspace(p)
                )
                self._workspace_menu.addAction(a)

    def _choose_project_workspace(self):
        from PySide6.QtWidgets import QFileDialog

        start = dialog_start_dir()
        folder = QFileDialog.getExistingDirectory(self, "Projekt-Ordner wählen", start)
        if not folder:
            return
        self._activate_project_workspace(folder)

    def _activate_project_workspace(self, folder: str | Path):
        path = Path(folder)
        if not path.is_dir():
            QMessageBox.warning(self, "Projekt-Ordner", f"Ordner existiert nicht:\n{path}")
            return
        remember_project_workspace(path, activate=True)
        self._refresh_workspaces()
        self._set_status(f"Projekt-Ordner: {path}")

    def _open_active_project_workspace(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        folder = get_active_project_workspace()
        if folder is None:
            self._choose_project_workspace()
            folder = get_active_project_workspace()
        if folder is None:
            return
        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        if ok:
            self._set_status(f"Projekt-Ordner: {folder}")
        else:
            QMessageBox.information(
                self,
                "Projekt-Ordner",
                f"Ordner konnte nicht geöffnet werden.\nPfad:\n{folder}",
            )

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
        """Statusleiste: Dateiname, Seite x/y bzw. Zeile x/y, Seitengröße, Zoom %, Wörter."""
        name = "—"
        page_txt = "Seite —"
        size_txt = "—"
        zoom_txt = "— %"
        word_txt = "— Wörter"
        current = self.stack.currentWidget()
        if self.doc and self.doc.path:
            name = Path(self.doc.path).name
        elif self.pdf_view.pdf_path:
            name = self.pdf_view.pdf_path.name
        # Aktuelle Ansicht zuerst: PDF↔Editor-Wechsel darf Seiten-/Zeileninfo nicht „kleben“ lassen
        if current is self.editor_pane:
            line = self.editor.current_line_number()
            total = self.editor.line_count()
            page_txt = f"Zeile {line}/{total}"
            zoom_txt = "—"
            words, chars = self.editor.word_stats()
            word_txt = f"{words} Wörter · {chars} Z."
            size_txt = "—"
            self.page_status_label.setToolTip("Editor: aktuelle Zeile / Zeilenanzahl")
        elif current is self.pdf_view and self.pdf_view.pdf_path and self.pdf_view.page_count > 0:
            from ild_pdf import format_page_status

            page_txt = format_page_status(
                self.pdf_view.page_index,
                self.pdf_view.page_count,
                self.pdf_view.page_label(),
            )
            zoom_txt = f"Zoom {int(round(self.pdf_view.scale * 100))}%"
            word_txt = f"{len(self.pdf_view.store.annotations) if self.pdf_view.store else 0} Ann."
            size_txt = self._format_current_page_size() or "—"
            self.page_status_label.setToolTip("PDF: aktuelle Seite / Seitenanzahl")
        elif current is self.image_label:
            page_txt = "Bild"
            zoom_txt = "—"
            self.page_status_label.setToolTip("Bildvorschau")
        elif self.pdf_view.pdf_path and self.pdf_view.page_count > 0:
            # Fallback wenn Stack kurzzeitig woanders steht, PDF aber geladen
            from ild_pdf import format_page_status

            page_txt = format_page_status(
                self.pdf_view.page_index,
                self.pdf_view.page_count,
                self.pdf_view.page_label(),
            )
            zoom_txt = f"Zoom {int(round(self.pdf_view.scale * 100))}%"
            word_txt = f"{len(self.pdf_view.store.annotations) if self.pdf_view.store else 0} Ann."
            size_txt = self._format_current_page_size() or "—"
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
        if zoom_txt.startswith("Zoom"):
            self.zoom_status_label.setToolTip("PDF-Zoom in Prozent")
        else:
            self.zoom_status_label.setToolTip("Zoom (nur PDF-Ansicht)")
        self.word_status_label.setText(word_txt)
        self._update_unsaved_status()

    def _on_editor_cursor_changed(self) -> None:
        """Zeileninfo in der Statusleiste live aktualisieren (nur Editor-Ansicht)."""
        if self.stack.currentWidget() is self.editor_pane:
            line = self.editor.current_line_number()
            total = self.editor.line_count()
            self.page_status_label.setText(f"Zeile {line}/{total}")
            words, chars = self.editor.word_stats()
            self.word_status_label.setText(f"{words} Wörter · {chars} Z.")

    def _path_key(self, path: str | Path | None) -> str | None:
        if not path:
            return None
        try:
            return str(Path(path).resolve())
        except Exception:
            return str(path)

    def _mark_unsaved(self, path: str | Path | None, dirty: bool = True) -> None:
        key = self._path_key(path)
        if not key:
            return
        if dirty:
            self._unsaved_paths.add(key)
        else:
            self._unsaved_paths.discard(key)
        self._update_unsaved_status()
        self._refresh_document_dirty_labels()

    def _refresh_document_dirty_labels(self) -> None:
        """Dirty-Indikator (*) an Sidebar-Dokument-Tabs inkl. pending Sidecar-Debounce."""
        files = getattr(self.sidebar, "files", None)
        if files is None:
            return
        dirty_keys = set(self._unsaved_paths)
        if self._current_is_dirty() and self.doc and self.doc.path:
            cur = self._path_key(self.doc.path)
            if cur:
                dirty_keys.add(cur)
        pending_key = None
        pending = False
        if (
            self.doc
            and self.doc.path
            and self.stack.currentWidget() is self.pdf_view
        ):
            if hasattr(self.pdf_view, "sidecar_save_pending"):
                pending = bool(self.pdf_view.sidecar_save_pending())
            else:
                pending = bool(getattr(self.pdf_view, "_sidecar_save_pending", False))
            if pending:
                pending_key = self._path_key(self.doc.path)
        # Rising-edge: kurzer Statusleisten-Blink bei pending Debounce
        was = bool(getattr(self, "_pending_was_pending", False))
        if pending and not was:
            self._blink_pending_debounce_status()
        self._pending_was_pending = bool(pending)
        for i in range(files.count()):
            it = files.item(i)
            if it is None:
                continue
            raw = it.data(256) or it.data(Qt.UserRole)
            if not raw:
                continue
            key = self._path_key(raw)
            base = Path(str(raw)).name
            if key and key in dirty_keys:
                it.setText(f"{base} *")
                if pending_key and key == pending_key:
                    it.setToolTip("Speichern ausstehend…")
                else:
                    it.setToolTip("Ungespeicherte Änderungen")
            else:
                it.setText(base)
                it.setToolTip("")

    def _blink_pending_debounce_status(self) -> None:
        """
        Statusleisten-Hinweis bei pending Sidecar-Debounce (Settings: kurz/aus).
        kurz: Blink-Animation; aus: einmaliger Status-Hinweis ohne Blink.
        """
        from PySide6.QtCore import QTimer

        from instantlensdoc.core.app_settings import (
            STATUS_BLINK_AUS,
            get_status_blink_mode,
        )

        if get_status_blink_mode() == STATUS_BLINK_AUS:
            # Aus: kein Blink, aber einmaliger Status-Hinweis (Rising-Edge)
            self._pending_blink_active = False
            try:
                self.statusBar().showMessage("Speichern ausstehend…", 1800)
            except Exception:
                pass
            return
        if getattr(self, "_pending_blink_active", False):
            return
        if not hasattr(self, "unsaved_status_label"):
            return
        self._pending_blink_active = True
        try:
            self.statusBar().showMessage("Speichern ausstehend…", 700)
        except Exception:
            pass
        label = self.unsaved_status_label
        # kurz: 2 Schritte, schwächere Intensität
        styles = (
            "padding-right: 10px; color: #fff; background-color: #B9770E; font-weight: 600;",
            "padding-right: 10px; color: #B9770E; font-weight: 600;",
        )
        self._pending_blink_step = 0

        def _tick() -> None:
            i = int(getattr(self, "_pending_blink_step", 0))
            if i >= len(styles):
                self._pending_blink_active = False
                self._update_unsaved_status()
                return
            label.setStyleSheet(styles[i])
            self._pending_blink_step = i + 1
            QTimer.singleShot(90, _tick)

        _tick()

    def count_unsaved_tabs(self) -> int:
        """Ungespeicherte Tabs: aktuelles Doc + markierte offene Sidebar-Pfade."""
        open_keys = {self._path_key(p) for p in self.sidebar.document_paths()}
        open_keys.discard(None)
        tracked = {k for k in self._unsaved_paths if k in open_keys}
        untitled = 0
        if self._current_is_dirty():
            cur = self._path_key(self.doc.path) if self.doc and self.doc.path else None
            if cur:
                tracked.add(cur)
            else:
                untitled = 1
        return len(tracked) + untitled

    def _update_unsaved_status(self) -> None:
        if not hasattr(self, "unsaved_status_label"):
            return
        n = self.count_unsaved_tabs()
        self.unsaved_status_label.setText(f"{n} ungespeichert")
        if n > 0:
            self.unsaved_status_label.setStyleSheet(
                "padding-right: 10px; color: #B9770E; font-weight: 600;"
            )
        else:
            self.unsaved_status_label.setStyleSheet("padding-right: 10px; color: #555;")

    def list_unsaved_tabs(self) -> list[tuple[str | None, str]]:
        """Ungespeicherte Tabs als (Pfad|None, Anzeigename). Untitled → path=None."""
        items: list[tuple[str | None, str]] = []
        seen: set[str] = set()
        open_map = {
            self._path_key(p): p
            for p in self.sidebar.document_paths()
            if self._path_key(p)
        }
        for key in sorted(self._unsaved_paths):
            path = open_map.get(key)
            if not path:
                continue
            seen.add(key)
            items.append((path, Path(path).name))
        if self._current_is_dirty():
            cur = self._path_key(self.doc.path) if self.doc and self.doc.path else None
            if cur and cur not in seen and cur in open_map:
                path = open_map[cur]
                items.append((path, Path(path).name))
            elif not cur:
                items.insert(0, (None, "Unbenannt *"))
        return items

    def _on_unsaved_status_clicked(self, event) -> None:
        """Statusleiste „ungespeichert“: Menü mit dirty Tabs → öffnen/wechseln + Speichern / Alle speichern."""
        if event.button() != Qt.LeftButton:
            return
        entries = self.list_unsaved_tabs()
        menu = QMenu(self)
        if not entries:
            act = menu.addAction("(keine ungespeicherten Tabs)")
            act.setEnabled(False)
        else:
            act_all = menu.addAction("Alle speichern")
            act_all.setToolTip("Alle ungespeicherten Tabs speichern")
            act_all.triggered.connect(self._save_all_unsaved_tabs)
            menu.addSeparator()
            for path, label in entries:
                act = menu.addAction(label)
                if path:
                    act.setToolTip(path)
                    act.triggered.connect(lambda checked=False, p=path: self.open_path(p))
                    act_save = menu.addAction(f"Speichern: {label}")
                    act_save.setToolTip(f"„{label}“ speichern")
                    act_save.triggered.connect(
                        lambda checked=False, p=path: self._save_unsaved_tab(p)
                    )
                else:
                    act.setEnabled(False)
                    act.setToolTip("Aktuelles unbenanntes Dokument (bereits aktiv)")
                    act_save = menu.addAction("Speichern: Unbenannt")
                    act_save.setToolTip("Unbenanntes Dokument speichern (Speichern unter…)")
                    act_save.triggered.connect(lambda checked=False: self.save_doc())
        menu.exec(self.unsaved_status_label.mapToGlobal(event.pos()))

    def _save_unsaved_tab(self, path: str | None) -> None:
        """Dirty-Tab speichern: bei Bedarf wechseln, dann Speichern."""
        if not path:
            self.save_doc()
            return
        cur = self._path_key(self.doc.path) if self.doc and self.doc.path else None
        key = self._path_key(path)
        if cur != key:
            self.open_path(path)
        self.save_doc()

    def _save_all_unsaved_tabs(self) -> None:
        """Alle dirty Tabs speichern; Fortschritt bei >3; Fehlerliste am Ende (0.6.9)."""
        from PySide6.QtWidgets import QApplication, QProgressDialog

        entries = list(self.list_unsaved_tabs())
        if not entries:
            self._set_status("Keine ungespeicherten Tabs")
            return
        # Aktuelles Doc zuerst — sonst verliert open_path den Editor-Inhalt
        cur_key = self._path_key(self.doc.path) if self.doc and self.doc.path else None
        work: list[tuple[str | None, str]] = []
        seen: set[str] = set()
        if self._current_is_dirty():
            if cur_key and self.doc and self.doc.path:
                work.append((str(self.doc.path), Path(self.doc.path).name))
                seen.add(cur_key)
            else:
                work.append((None, "Unbenannt"))
                seen.add("__unnamed__")
        for path, label in entries:
            if path is None:
                continue
            key = self._path_key(path)
            if key in seen:
                continue
            seen.add(key)
            work.append((path, label))
        total = len(work)
        if total == 0:
            self._set_status("Keine ungespeicherten Tabs")
            return
        use_progress = total > 3
        prog: QProgressDialog | None = None
        if use_progress:
            prog = QProgressDialog("Alle speichern…", "Abbrechen", 0, total, self)
            prog.setWindowTitle("Alle speichern")
            prog.setWindowModality(Qt.WindowModal)
            prog.setMinimumDuration(0)
            prog.setCancelButtonText("Abbrechen")
            prog.setValue(0)
            prog.setLabelText(f"0 / {total} Dateien…")
            QApplication.processEvents()
        n = 0
        cancelled = False
        errors: list[str] = []
        self._batch_save_quiet = True
        try:
            for path, label in work:
                if prog is not None:
                    if prog.wasCanceled():
                        cancelled = True
                        break
                    prog.setLabelText(f"Speichern {n + 1}/{total}: {label}")
                    prog.setValue(n)
                    QApplication.processEvents()
                    if prog.wasCanceled():
                        cancelled = True
                        break
                try:
                    ok = True
                    if path is None:
                        ok = self.save_doc()
                    elif cur_key and self._path_key(path) == cur_key:
                        ok = self.save_doc()
                    else:
                        self._save_unsaved_tab(path)
                        key = self._path_key(path)
                        ok = not (key and key in self._unsaved_paths)
                    if not ok:
                        errors.append(f"{label}: Speichern fehlgeschlagen")
                except Exception as e:
                    errors.append(f"{label}: {e}")
                n += 1
        finally:
            self._batch_save_quiet = False
        if prog is not None:
            if not cancelled:
                prog.setValue(total)
            prog.close()
        self._update_unsaved_status()
        if errors:
            detail = "\n".join(f"• {e}" for e in errors[:40])
            if len(errors) > 40:
                detail += f"\n… und {len(errors) - 40} weitere"
            QMessageBox.warning(
                self,
                "Alle speichern — Fehler",
                f"{len(errors)} Datei(en) konnten nicht gespeichert werden:\n\n{detail}",
            )
        if cancelled:
            self._set_status(
                f"Alle speichern abgebrochen ({n}/{total}"
                + (f", {len(errors)} Fehler)" if errors else ")")
            )
        elif errors:
            self._set_status(f"Alle speichern: {n - len(errors)}/{total} OK, {len(errors)} Fehler")
        elif use_progress:
            self._set_status(f"Alle speichern: {n}/{total} Datei(en) fertig")
        else:
            self._set_status(f"Alle speichern: {n} Tab(s)")

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

    def _duplicate_current(self):
        """Ctrl+D: PDF → Annotation duplizieren; Editor → Zeile duplizieren."""
        if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
            if self.pdf_view._selected_ann_id:
                self._duplicate_annotation()
                return
            self._set_status("Keine Annotation ausgewählt (Ctrl+D)")
            return
        self._duplicate_line()

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

    def _save_current_zoom_as_default(self):
        """Aktuellen PDF-Zoom als Standard-% speichern (Modus: Prozent)."""
        from instantlensdoc.core.app_settings import (
            set_default_zoom_mode,
            set_default_zoom_percent,
        )

        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Standard-Zoom: PDF öffnen")
            return
        pct = max(25, min(500, int(round(float(self.pdf_view.scale) * 100))))
        set_default_zoom_percent(pct)
        set_default_zoom_mode("percent")
        self._set_status(f"Standard-Zoom gespeichert: {pct}%")

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

    def _sort_lines_az(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self._set_status("Zeilen sortieren nur im Texteditor")
            return
        if self.editor.sort_lines_az():
            if self.doc and self.doc.kind in (
                DocKind.TEXT,
                DocKind.MARKDOWN,
                DocKind.HTML,
                DocKind.DOCX,
            ):
                self.doc.text = self.editor.toPlainText()
                self.doc.dirty = True
            self._on_text_changed()
            self._set_status("Zeilen A–Z sortiert")
        else:
            self._set_status("Zeilen sortieren nicht möglich")

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
        if self.stack.currentWidget() is not self.pdf_view:
            return
        self.zoom_status_label.setText(f"Zoom {int(round(float(scale) * 100))}%")
        self.zoom_status_label.setToolTip("PDF-Zoom in Prozent")
        if self.pdf_view.pdf_path and self.pdf_view.page_count > 0:
            from ild_pdf import format_page_status

            self.page_status_label.setText(
                format_page_status(
                    self.pdf_view.page_index,
                    self.pdf_view.page_count,
                    self.pdf_view.page_label(),
                )
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

    def _edit_annotation_tags(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Annotation-Tags nur im PDF-Modus")
            return
        if not self.pdf_view._selected_ann_id:
            self._set_status("Keine Annotation ausgewählt")
            return
        self.pdf_view.edit_selected_annotation_tags()

    def _edit_annotation_group(self, page: int | None = None):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Annotationsgruppe nur im PDF-Modus")
            return
        idx = None if page is None or isinstance(page, bool) else int(page)
        self.pdf_view.edit_page_annotation_group(idx)
        self._refresh_pdf_marks()

    def _recolor_selected_annotations(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Auswahl-Farbe nur im PDF-Modus")
            return
        n = self.pdf_view.recolor_selected_annotations()
        if n:
            self._refresh_pdf_marks()

    def _opacity_selected_annotations(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Auswahl-Deckkraft nur im PDF-Modus")
            return
        n = self.pdf_view.set_opacity_selected_annotations()
        if n:
            self._refresh_pdf_marks()

    def _align_selected_annotations(self, mode: str = "left"):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Ausrichten nur im PDF-Modus")
            return
        n = self.pdf_view.align_selected_annotations(mode)
        if n:
            self._refresh_pdf_marks()

    def _distribute_selected_annotations_horizontal(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Verteilen nur im PDF-Modus")
            return
        n = self.pdf_view.distribute_selected_annotations_horizontal()
        if n:
            self._refresh_pdf_marks()

    def _distribute_selected_annotations_vertical(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Verteilen nur im PDF-Modus")
            return
        n = self.pdf_view.distribute_selected_annotations_vertical()
        if n:
            self._refresh_pdf_marks()

    def _group_selected_annotations(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Gruppieren nur im PDF-Modus")
            return
        n = self.pdf_view.group_selected_annotations()
        if n:
            self._refresh_pdf_marks()

    def _ungroup_selected_annotations(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Entgruppieren nur im PDF-Modus")
            return
        n = self.pdf_view.ungroup_selected_annotations()
        if n:
            self._refresh_pdf_marks()

    def _toggle_selected_group_lock(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Gruppen-Sperre nur im PDF-Modus")
            return
        n = self.pdf_view.toggle_selected_group_lock()
        if n:
            self._refresh_pdf_marks()

    def _edit_selected_ann_group(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Ann.-Gruppe nur im PDF-Modus")
            return
        if self.pdf_view.edit_selected_ann_group():
            self._refresh_pdf_marks()

    def _toggle_line_bookmark(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self.stack.setCurrentWidget(self.editor_pane)
        now = self.editor.toggle_line_bookmark()
        line = self.editor.textCursor().blockNumber() + 1
        self._refresh_line_favorites()
        self._set_status(
            f"Zeile {line} als Lesezeichen markiert"
            if now
            else f"Zeile {line} Lesezeichen entfernt"
        )

    def _goto_next_line_bookmark(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self.stack.setCurrentWidget(self.editor_pane)
        line = self.editor.goto_next_line_bookmark()
        if line:
            self._refresh_line_favorites()
            self._set_status(f"Lesezeichen → Zeile {line}")
        else:
            self._set_status("Keine Zeilen-Lesezeichen")

    def _goto_prev_line_bookmark(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self.stack.setCurrentWidget(self.editor_pane)
        line = self.editor.goto_prev_line_bookmark()
        if line:
            self._refresh_line_favorites()
            self._set_status(f"Lesezeichen → Zeile {line}")
        else:
            self._set_status("Keine Zeilen-Lesezeichen")

    def _clear_line_bookmarks(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self.stack.setCurrentWidget(self.editor_pane)
        self.editor.clear_line_bookmarks()
        self._refresh_line_favorites()
        self._set_status("Zeilen-Lesezeichen gelöscht")

    def _export_line_bookmarks_json(self) -> bool:
        """Editor-Zeilen-Lesezeichen als JSON (ildbm-v1) exportieren."""
        from PySide6.QtWidgets import QFileDialog
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        if self.stack.currentWidget() is not self.editor_pane:
            self.stack.setCurrentWidget(self.editor_pane)
        marks = self.editor.list_line_bookmarks_with_labels()
        if not marks:
            QMessageBox.information(
                self, "Lesezeichen", "Keine Zeilen-Lesezeichen zum Exportieren."
            )
            return False
        src_name = ""
        default_dir = str(Path.home())
        if self.doc and self.doc.path:
            src_name = Path(self.doc.path).name
            default_dir = str(Path(self.doc.path).parent)
            default = str(Path(self.doc.path).with_suffix(".bookmarks.json"))
        else:
            default = str(Path(default_dir) / "bookmarks.json")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Zeilen-Lesezeichen als JSON exportieren",
            default,
            "Lesezeichen JSON (*.bookmarks.json *.json);;Alle (*.*)",
        )
        if not path:
            return False
        dest = Path(path)
        if dest.suffix.lower() != ".json":
            dest = dest.with_suffix(".json")
        if not confirm_overwrite_export(dest, self):
            return False
        try:
            saved = self.editor.export_line_bookmarks_json(dest, source=src_name)
            self._set_status(f"Lesezeichen exportiert: {saved.name} ({len(marks)})")
            return True
        except Exception as e:
            QMessageBox.warning(self, "Lesezeichen exportieren", str(e))
            return False

    def _import_line_bookmarks_json(self) -> bool:
        """Editor-Zeilen-Lesezeichen aus JSON importieren (ersetzen oder zusammenführen)."""
        from PySide6.QtWidgets import QFileDialog
        from instantlensdoc.core.bookmarks import BookmarksImportError

        if self.stack.currentWidget() is not self.editor_pane:
            self.stack.setCurrentWidget(self.editor_pane)
        start = str(Path(self.doc.path).parent) if self.doc and self.doc.path else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Zeilen-Lesezeichen aus JSON importieren",
            start,
            "Lesezeichen JSON (*.bookmarks.json *.json);;Alle (*.*)",
        )
        if not path:
            return False
        reply = QMessageBox.question(
            self,
            "Lesezeichen importieren",
            "Bestehende Lesezeichen behalten und neue anhängen?\n\n"
            "Ja = zusammenführen · Nein = ersetzen · Abbrechen = abbrechen",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Cancel:
            return False
        merge = reply == QMessageBox.Yes
        try:
            marks = self.editor.import_line_bookmarks_json(
                path,
                merge=merge,
                max_line=self.editor.blockCount(),
            )
        except BookmarksImportError as e:
            QMessageBox.warning(self, "Lesezeichen importieren", str(e))
            return False
        except Exception as e:
            QMessageBox.warning(self, "Lesezeichen importieren", str(e))
            return False
        self._refresh_line_favorites()
        mode = "zusammengeführt" if merge else "ersetzt"
        self._set_status(f"Lesezeichen {mode}: {len(marks)} Zeile(n)")
        return True

    def _refresh_line_favorites(self):
        """Sidebar-Liste aller Editor-Zeilenfavoriten aktualisieren (inkl. Labels)."""
        marks = self.editor.list_line_bookmarks_with_labels()
        lines = [ln for ln, _lab in marks]
        cur = self.editor.textCursor().blockNumber() + 1
        self.sidebar.set_line_favorites(marks, current=cur if cur in lines else None)

    def _on_line_bookmarks_changed(self) -> None:
        """Sidebar aktualisieren und Sidecar persistieren."""
        self._refresh_line_favorites()
        if not getattr(self, "_suppress_bookmark_persist", False):
            self._persist_line_bookmarks_sidecar()

    def _on_line_favorites_reordered(self, lines: list) -> None:
        """Drag-Reorder der Bookmark-Liste → Editor-Reihenfolge + Sidecar."""
        try:
            order = [int(x) for x in list(lines or [])]
        except (TypeError, ValueError):
            return
        if not order:
            return
        self.editor.reorder_line_bookmarks(order)
        self._set_status(f"Lesezeichen-Reihenfolge: {len(order)} Einträge")

    def _persist_line_bookmarks_sidecar(self) -> None:
        """Editor-Lesezeichen neben Textdatei speichern (*.ildbm.json)."""
        if getattr(self, "_suppress_bookmark_persist", False):
            return
        if not self.doc or not self.doc.path:
            return
        if self.doc.kind in (DocKind.PDF, DocKind.IMAGE):
            return
        from instantlensdoc.core.bookmarks import (
            delete_bookmarks_sidecar,
            save_bookmarks_sidecar,
        )

        marks = self.editor.list_line_bookmarks_with_labels()
        try:
            if not marks:
                delete_bookmarks_sidecar(self.doc.path)
            else:
                save_bookmarks_sidecar(self.doc.path, marks)
        except Exception as e:
            _log.debug("Lesezeichen-Sidecar speichern fehlgeschlagen: %s", e)

    def _load_line_bookmarks_sidecar(self, path: str | Path) -> None:
        """Sidecar-Lesezeichen für Textdatei laden (falls vorhanden)."""
        from instantlensdoc.core.bookmarks import (
            BookmarksImportError,
            load_bookmarks_sidecar,
            bookmarks_to_export_dict,
        )

        try:
            marks = load_bookmarks_sidecar(path, max_line=self.editor.blockCount())
        except BookmarksImportError as e:
            _log.debug("Lesezeichen-Sidecar ungültig: %s", e)
            return
        except Exception as e:
            _log.debug("Lesezeichen-Sidecar laden fehlgeschlagen: %s", e)
            return
        if marks is None:
            return
        if not marks:
            return
        data = bookmarks_to_export_dict(marks, source=Path(path).name)
        self.editor.import_line_bookmarks_dict(
            data, merge=False, max_line=self.editor.blockCount()
        )

    def _edit_line_favorite_label(self, line: int):
        """Label eines Editor-Zeilenfavoriten bearbeiten (Sidebar Doppelklick/Menü)."""
        from PySide6.QtWidgets import QInputDialog

        if self.stack.currentWidget() is not self.editor_pane:
            self.stack.setCurrentWidget(self.editor_pane)
        try:
            ln = int(line)
        except (TypeError, ValueError):
            return
        if ln < 1 or not self.editor.is_line_bookmarked(ln):
            return
        current = self.editor.get_line_bookmark_label(ln)
        text, ok = QInputDialog.getText(
            self,
            "Zeilenfavorit-Label",
            f"Label für Zeile {ln}:",
            text=current,
        )
        if not ok:
            return
        if self.editor.set_line_bookmark_label(ln, text):
            self._refresh_line_favorites()
            label = self.editor.get_line_bookmark_label(ln)
            self._set_status(
                f"Zeilenfavorit Zeile {ln}: „{label}“" if label else f"Label Zeile {ln} entfernt"
            )

    def _on_line_favorite_jump(self, line: int):
        if self.stack.currentWidget() is not self.editor_pane:
            self.stack.setCurrentWidget(self.editor_pane)
        try:
            ln = int(line)
        except (TypeError, ValueError):
            return
        if ln < 1:
            return
        self.editor.goto_line(ln)
        self._refresh_line_favorites()
        self._set_status(f"Zeilenfavorit → Zeile {ln}")

    def _check_spelling(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self.stack.setCurrentWidget(self.editor_pane)
        from instantlensdoc.core.app_settings import get_spellcheck_dict_path

        path = get_spellcheck_dict_path()
        if not path:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                "Rechtschreibung",
                "Kein Wörterbuch-Pfad gesetzt.\n"
                "Extras → Einstellungen → Rechtschreibwörterbuch (Wortliste).",
            )
            self._set_status("Rechtschreibung: kein Wörterbuch-Pfad")
            return
        try:
            n = self.editor.check_spelling(path)
        except FileNotFoundError as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Rechtschreibung", str(e))
            self._set_status("Rechtschreibung: Wörterbuch fehlt")
            return
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Rechtschreibung", str(e))
            return
        self._set_status(
            f"Rechtschreibung: {n} unbekannt(e) Wort(e)"
            if n
            else "Rechtschreibung: keine unbekannten Wörter"
        )

    def _clear_spelling(self):
        self.editor.clear_spelling()
        self._set_status("Rechtschreibmarkierungen gelöscht")

    def _insert_soft_hyphen(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self.stack.setCurrentWidget(self.editor_pane)
        if self.editor.insert_soft_hyphen():
            self._set_status("Soft-Hyphen eingefügt (U+00AD)")

    def _insert_nbsp(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self.stack.setCurrentWidget(self.editor_pane)
        if self.editor.insert_nbsp():
            self._set_status("Geschütztes Leerzeichen eingefügt (U+202F)")

    def _duplicate_annotation(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Annotation duplizieren nur im PDF-Modus")
            return
        if not self.pdf_view._selected_ann_id:
            self._set_status("Keine Annotation ausgewählt")
            return
        self.pdf_view.duplicate_selected_annotation()

    def _copy(self):
        """Kopieren: PDF-Textauswahl bevorzugt, sonst Editor."""
        if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
            if self.pdf_view.copy_text_selection():
                return
        self.editor.copy()

    def _sticky_from_selection(self):
        """PDF-Textauswahl → Sticky/Notiz; optional zusätzlich Highlight."""
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Auswahl → Notiz nur im PDF-Modus")
            return
        if self.pdf_view.sticky_from_text_selection(edit=True):
            self._refresh_pdf_marks()
            if self.doc and self.doc.path:
                self._mark_unsaved(self.doc.path, True)

    def _toggle_doc_split(self, checked: bool):
        from instantlensdoc.core.app_settings import set_editor_doc_split

        set_editor_doc_split(bool(checked))
        if hasattr(self, "secondary_wrap"):
            self.secondary_wrap.setVisible(bool(checked))
        if checked:
            self._apply_doc_split_orientation()
            # Panel-Typ / Zweit-Doc aus Session merken — nicht jedes Mal neu wählen
            remembered = getattr(self, "_secondary_path", None)
            if remembered and Path(remembered).is_file():
                self._load_secondary_document(remembered)
            else:
                self._load_secondary_document()
            self._apply_doc_split_sync_scroll()
            orient = "vertikal" if get_editor_doc_split_vertical() else "horizontal"
            kind = getattr(self, "_secondary_kind", "") or "?"
            self._set_status(f"Fenster teilen an — zwei Docs {orient} (Panel: {kind})")
        else:
            self._disconnect_doc_split_sync_scroll()
            self._set_status("Fenster teilen aus")

    def _toggle_doc_split_vertical(self, checked: bool):
        from instantlensdoc.core.app_settings import set_editor_doc_split_vertical

        set_editor_doc_split_vertical(bool(checked))
        self._apply_doc_split_orientation()
        self._set_status(
            "Doc-Split vertikal (übereinander)"
            if checked
            else "Doc-Split horizontal (nebeneinander)"
        )

    def _apply_doc_split_orientation(self) -> None:
        if not hasattr(self, "doc_splitter"):
            return
        self.doc_splitter.setOrientation(
            Qt.Vertical if get_editor_doc_split_vertical() else Qt.Horizontal
        )

    def _sync_doc_split_orientation(self) -> None:
        """Einstellungen → Doc-Split H/V auf Menüaktion + Splitter anwenden."""
        vertical = get_editor_doc_split_vertical()
        if hasattr(self, "_doc_split_vertical_action") and self._doc_split_vertical_action is not None:
            self._doc_split_vertical_action.blockSignals(True)
            self._doc_split_vertical_action.setChecked(bool(vertical))
            self._doc_split_vertical_action.blockSignals(False)
        self._apply_doc_split_orientation()

    def _toggle_doc_split_sync_scroll(self, checked: bool):
        from instantlensdoc.core.app_settings import set_editor_doc_split_sync_scroll

        set_editor_doc_split_sync_scroll(bool(checked))
        self._apply_doc_split_sync_scroll()
        self._save_session()
        self._set_status(
            "Sync-Scroll an (geteilte Docs)" if checked else "Sync-Scroll aus"
        )

    def _recolor_annotation_tag_global(self, tag: str) -> None:
        """Tag-Cloud: Farbe aller Annotationen mit diesem Tag ändern (eine Undo-Stufe)."""
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QColorDialog

        store = getattr(self.pdf_view, "store", None)
        if store is None or not self.pdf_view.pdf_path:
            self._set_status("Tag-Farbe nur bei geöffnetem PDF")
            return
        tag_s = str(tag or "").strip()
        if not tag_s:
            return
        tag_cf = tag_s.casefold()
        targets = [
            a
            for a in store.annotations
            if any(str(t).casefold() == tag_cf for t in (getattr(a, "tags", None) or []))
        ]
        if not targets:
            self._set_status(f"Kein Tag „{tag_s}“ gefunden")
            return
        initial = QColor(getattr(targets[0], "color", None) or "#FFE066")
        if not initial.isValid():
            initial = QColor("#FFE066")
        chosen = QColorDialog.getColor(
            initial,
            self,
            f"Farbe für Tag „{tag_s}“ ({len(targets)} Annotationen)",
        )
        if not chosen.isValid():
            return
        color = chosen.name().upper()
        ids = [a.id for a in targets if getattr(a, "id", None)]
        n = store.set_colors(ids, color)
        if n <= 0:
            self._set_status("Farbe nicht geändert")
            return
        try:
            store.save()
        except Exception as e:
            QMessageBox.warning(self, "Tag-Farbe", str(e))
            return
        self.pdf_view.refresh()
        self._refresh_pdf_marks()
        if self.doc and self.doc.path:
            self._mark_unsaved(self.doc.path, bool(store.dirty))
        self._refresh_undo_hint()
        self._set_status(f"Farbe {color} für Tag „{tag_s}“ ({n} Annotationen)")

    def _rename_annotation_tag_global(self, old_tag: str, new_tag: str) -> None:
        """Tag-Cloud: Tag in allen Annotationen des aktuellen PDFs umbenennen (eine Undo-Stufe)."""
        from instantlensdoc.core.app_settings import get_tag_rename_confirm_threshold

        store = getattr(self.pdf_view, "store", None)
        if store is None:
            self._set_status("Tag umbenennen nur bei geöffnetem PDF")
            return
        # Bestätigung bei vielen Treffern (Schwelle in Einstellungen, Default 20)
        hit_count = 0
        if hasattr(store, "count_tag"):
            try:
                hit_count = int(store.count_tag(old_tag))
            except Exception:
                hit_count = 0
        if hit_count <= 0:
            self._set_status(f"Kein Tag „{old_tag}“ gefunden")
            return
        threshold = get_tag_rename_confirm_threshold()
        if hit_count > threshold:
            reply = QMessageBox.question(
                self,
                "Tag umbenennen",
                f"Tag „{old_tag}“ → „{new_tag}“ betrifft {hit_count} Annotationen "
                f"(Schwelle {threshold}).\n"
                "Wirklich alle umbenennen?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                self._set_status(f"Tag umbenennen abgebrochen ({hit_count} Treffer)")
                return
        n = store.rename_tag(old_tag, new_tag)
        if n <= 0:
            self._set_status(f"Kein Tag „{old_tag}“ gefunden")
            return
        # Sidecar schreiben, Undo-History bleibt erhalten → Ctrl+Z = ein Schritt für alle Ann.
        try:
            store.save()
        except Exception as e:
            QMessageBox.warning(self, "Tag umbenennen", str(e))
            return
        self._last_tag_rename = (str(old_tag), str(new_tag))
        # Aktiven Filter mitziehen
        old_cf = old_tag.casefold()
        filt = list(self.sidebar.annotation_filter_tags())
        nxt: list[str] = []
        seen: set[str] = set()
        for t in filt:
            s = new_tag if t.casefold() == old_cf else t
            key = s.casefold()
            if key in seen:
                continue
            seen.add(key)
            nxt.append(s)
        self.sidebar.set_annotation_tag_filter(nxt)
        self.pdf_view.refresh()
        self._refresh_pdf_marks()
        if self.doc and self.doc.path:
            self._mark_unsaved(self.doc.path, bool(store.dirty))
        self._refresh_undo_hint()
        self._set_status(
            f"Tag „{old_tag}“ → „{new_tag}“ ({n} Annotationen) — Ctrl+Z: Tag umbenennen rückgängig"
        )

    def _refresh_undo_hint(self) -> None:
        """Statusleisten-Hint: nächstes PDF-Undo sichtbar benennen (z. B. Tag umbenennen)."""
        if not hasattr(self, "undo_hint_label"):
            return
        store = getattr(self.pdf_view, "store", None)
        label = None
        if store is not None and hasattr(store, "peek_undo_label"):
            try:
                label = store.peek_undo_label()
            except Exception:
                label = None
        if label:
            self.undo_hint_label.setText(f"Ctrl+Z · {label} rückgängig")
            self.undo_hint_label.setToolTip(
                f"Nächste Undo-Stufe: {label} (PDF-Undo-Stack / Ctrl+Z)"
            )
        else:
            self.undo_hint_label.setText("Ctrl+Z · Letzte Aktion rückgängig")
            self.undo_hint_label.setToolTip(
                "Rückgängig: Editor · PDF-Annotationen (benannt) · Seiten (Ctrl+Z)"
            )

    def _revert_tag_filter_after_rename_undo(self) -> None:
        """Nach Undo des globalen Tag-Rename: Filter old←new zurücksetzen."""
        if not self._last_tag_rename:
            return
        old_tag, new_tag = self._last_tag_rename
        store = getattr(self.pdf_view, "store", None)
        old_cf = old_tag.casefold()
        has_old = False
        if store is not None:
            has_old = any(
                any(str(t).casefold() == old_cf for t in (a.tags or []))
                for a in store.annotations
            )
        if not has_old:
            # Undo betraf eine andere Aktion — Rename-Merker behalten
            return
        self._last_tag_rename = None
        new_cf = new_tag.casefold()
        filt = list(self.sidebar.annotation_filter_tags())
        # Nach Undo kann der Filter leer sein (neuer Tag existiert nicht mehr)
        if not filt or all(t.casefold() == new_cf for t in filt):
            self.sidebar.set_annotation_tag_filter([old_tag])
            self._refresh_pdf_marks()
            return
        nxt: list[str] = []
        seen: set[str] = set()
        for t in filt:
            s = old_tag if t.casefold() == new_cf else t
            key = s.casefold()
            if key in seen:
                continue
            seen.add(key)
            nxt.append(s)
        self.sidebar.set_annotation_tag_filter(nxt)
        self._refresh_pdf_marks()

    def _primary_scroll_bar(self):
        """Vertikale Scrollbar der aktuellen Hauptansicht (Editor/PDF)."""
        w = self.stack.currentWidget()
        if w is self.editor_pane and hasattr(self, "editor"):
            return self.editor.verticalScrollBar()
        if w is self.pdf_view:
            scroll = getattr(self.pdf_view, "scroll", None)
            if scroll is not None:
                return scroll.verticalScrollBar()
        return None

    def _secondary_scroll_bar(self):
        if hasattr(self, "secondary_stack") and hasattr(self, "secondary_pdf"):
            if self.secondary_stack.currentWidget() is self.secondary_pdf:
                scroll = getattr(self.secondary_pdf, "scroll", None)
                if scroll is not None:
                    return scroll.verticalScrollBar()
        if hasattr(self, "secondary_editor"):
            return self.secondary_editor.verticalScrollBar()
        return None

    def _disconnect_doc_split_sync_scroll(self) -> None:
        primary = getattr(self, "_sync_primary_bar", None)
        secondary = getattr(self, "_sync_secondary_bar", None)
        if primary is not None:
            try:
                primary.valueChanged.disconnect(self._on_primary_scroll_sync)
            except (TypeError, RuntimeError):
                pass
        if secondary is not None:
            try:
                secondary.valueChanged.disconnect(self._on_secondary_scroll_sync)
            except (TypeError, RuntimeError):
                pass
        self._sync_primary_bar = None
        self._sync_secondary_bar = None

    def _apply_doc_split_sync_scroll(self) -> None:
        """Sync-Scroll verbinden wenn Split sichtbar und Einstellung an."""
        self._disconnect_doc_split_sync_scroll()
        if not hasattr(self, "secondary_wrap") or not self.secondary_wrap.isVisible():
            return
        if not get_editor_doc_split_sync_scroll():
            return
        primary = self._primary_scroll_bar()
        secondary = self._secondary_scroll_bar()
        if primary is None or secondary is None:
            return
        self._sync_primary_bar = primary
        self._sync_secondary_bar = secondary
        primary.valueChanged.connect(self._on_primary_scroll_sync)
        secondary.valueChanged.connect(self._on_secondary_scroll_sync)

    def _sync_scroll_ratio(self, source, target) -> None:
        if source is None or target is None or source is target:
            return
        s_max = source.maximum()
        t_max = target.maximum()
        if s_max <= 0:
            target.setValue(0)
            return
        if t_max <= 0:
            return
        ratio = source.value() / s_max
        target.setValue(int(round(ratio * t_max)))

    def _on_primary_scroll_sync(self, _value: int = 0) -> None:
        if getattr(self, "_split_scroll_syncing", False):
            return
        self._split_scroll_syncing = True
        try:
            self._sync_scroll_ratio(
                getattr(self, "_sync_primary_bar", None),
                getattr(self, "_sync_secondary_bar", None),
            )
        finally:
            self._split_scroll_syncing = False

    def _on_secondary_scroll_sync(self, _value: int = 0) -> None:
        if getattr(self, "_split_scroll_syncing", False):
            return
        self._split_scroll_syncing = True
        try:
            self._sync_scroll_ratio(
                getattr(self, "_sync_secondary_bar", None),
                getattr(self, "_sync_primary_bar", None),
            )
        finally:
            self._split_scroll_syncing = False

    def _pick_secondary_document(self):
        paths = list(self.sidebar.document_paths()) if hasattr(self.sidebar, "document_paths") else []
        if not paths:
            self._set_status("Keine offenen Tabs für zweites Dokument")
            return
        from PySide6.QtWidgets import QInputDialog

        labels = [Path(p).name for p in paths]
        choice, ok = QInputDialog.getItem(
            self,
            "Zweites Dokument",
            "Dokument für rechte Split-Ansicht:",
            labels,
            0,
            False,
        )
        if not ok or not choice:
            return
        idx = labels.index(choice) if choice in labels else 0
        self._load_secondary_document(paths[idx])
        if hasattr(self, "_doc_split_action") and not self._doc_split_action.isChecked():
            self._doc_split_action.setChecked(True)

    def _load_secondary_document(self, path: str | None = None):
        """Zweites Split-Pane: Editor oder PDF (Mischung mit Hauptbereich erlaubt)."""
        if not hasattr(self, "secondary_editor"):
            return
        paths = list(self.sidebar.document_paths()) if hasattr(self.sidebar, "document_paths") else []
        current = self._path_key(self.doc.path) if self.doc and self.doc.path else None
        pick = path
        text_ext = {".txt", ".md", ".markdown", ".html", ".htm", ".csv", ".json", ".log", ".py"}
        remembered_kind = str(getattr(self, "_secondary_kind", "") or "").strip().lower()
        if not pick:
            # Session-gemerktes Zweit-Doc bevorzugen, sonst Typ-Mischung
            remembered = getattr(self, "_secondary_path", None)
            if remembered and Path(remembered).is_file():
                if self._path_key(remembered) != current:
                    pick = remembered
            if not pick:
                # Bevorzugt gemerkten Panel-Typ, sonst anderen Typ als aktuelles Doc
                cur_suf = Path(self.doc.path).suffix.lower() if self.doc and self.doc.path else ""
                prefer_pdf = remembered_kind == "pdf" or (
                    not remembered_kind
                    and (cur_suf in text_ext or cur_suf == ".docx" or cur_suf == "")
                )
                prefer_text = remembered_kind == "editor" or (
                    not remembered_kind and cur_suf == ".pdf"
                )
                for p in paths:
                    if self._path_key(p) == current:
                        continue
                    suf = Path(p).suffix.lower()
                    if prefer_pdf and suf == ".pdf":
                        pick = p
                        break
                    if prefer_text and (suf in text_ext or suf == ".docx"):
                        pick = p
                        break
            if not pick:
                for p in paths:
                    if self._path_key(p) != current:
                        pick = p
                        break
        if not pick or not Path(pick).is_file():
            self._secondary_path = None
            self._secondary_kind = ""
            self.secondary_title.setText("Kein zweites Dokument")
            if hasattr(self, "secondary_stack"):
                self.secondary_stack.setCurrentWidget(self.secondary_pane)
            self.secondary_editor.blockSignals(True)
            self.secondary_editor.setPlainText("")
            self.secondary_editor.blockSignals(False)
            self._save_session()
            return
        self._secondary_path = str(pick)
        name = Path(pick).name
        suffix = Path(pick).suffix.lower()
        try:
            if suffix == ".pdf" and hasattr(self, "secondary_pdf"):
                ok = bool(self.secondary_pdf.load(pick))
                if ok:
                    try:
                        self.secondary_pdf.set_annotations_locked(True)
                    except Exception:
                        pass
                    self.secondary_title.setText(f"Rechts: {name} (PDF)")
                    self.secondary_stack.setCurrentWidget(self.secondary_pdf)
                    self._secondary_kind = "pdf"
                else:
                    self.secondary_title.setText(f"Rechts: {name} (PDF-Fehler)")
                    self.secondary_stack.setCurrentWidget(self.secondary_pane)
                    self._secondary_kind = "editor"
                    self.secondary_editor.blockSignals(True)
                    self.secondary_editor.setPlainText(
                        f"[PDF] {name}\nLaden fehlgeschlagen.\nPfad: {pick}"
                    )
                    self.secondary_editor.blockSignals(False)
            elif suffix in text_ext or suffix == ".docx":
                doc = open_document(pick)
                body = doc.text or ""
                self.secondary_title.setText(f"Rechts: {name}")
                self.secondary_stack.setCurrentWidget(self.secondary_pane)
                self._secondary_kind = "editor"
                self.secondary_editor.blockSignals(True)
                self.secondary_editor.setPlainText(body)
                self.secondary_editor.blockSignals(False)
            else:
                self.secondary_title.setText(f"Rechts: {name}")
                self.secondary_stack.setCurrentWidget(self.secondary_pane)
                self._secondary_kind = "editor"
                self.secondary_editor.blockSignals(True)
                self.secondary_editor.setPlainText(f"[Datei] {pick}")
                self.secondary_editor.blockSignals(False)
        except Exception as e:
            self.secondary_title.setText(f"Rechts: {name} (Fehler)")
            if hasattr(self, "secondary_stack"):
                self.secondary_stack.setCurrentWidget(self.secondary_pane)
            self._secondary_kind = "editor"
            self.secondary_editor.blockSignals(True)
            self.secondary_editor.setPlainText(f"Laden fehlgeschlagen:\n{e}")
            self.secondary_editor.blockSignals(False)
        self._save_session()
        self._apply_doc_split_sync_scroll()

    def _copy_annotations(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Annotationen kopieren nur im PDF-Modus")
            return
        n = self.pdf_view.copy_selected_annotations()
        if n:
            self._set_status(f"{n} Annotation(en) kopiert — Einfügen: Ctrl+Alt+V")

    def _paste_annotations(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Annotationen einfügen nur im PDF-Modus")
            return
        n = self.pdf_view.paste_annotations_on_page()
        if n:
            self._refresh_pdf_marks()
            self._set_status(f"{n} Annotation(en) eingefügt")

    def _toggle_line_numbers(self, checked: bool):
        """Ansicht-Toggle: Zeilennummern sofort anwenden und in Settings persistieren."""
        from instantlensdoc.core.app_settings import (
            get_editor_line_numbers,
            set_editor_line_numbers,
        )

        on = bool(checked)
        set_editor_line_numbers(on)
        self.editor.set_line_numbers_visible(on)
        # Verifizieren: Round-Trip Settings → Anzeige
        persisted = bool(get_editor_line_numbers())
        if persisted != on:
            set_editor_line_numbers(on)
            persisted = bool(get_editor_line_numbers())
        if hasattr(self, "_line_numbers_action") and self._line_numbers_action is not None:
            self._line_numbers_action.blockSignals(True)
            self._line_numbers_action.setChecked(persisted)
            self._line_numbers_action.blockSignals(False)
        self._set_status("Zeilennummern an" if persisted else "Zeilennummern aus")

    def _toggle_indent_guides(self, checked: bool):
        """Ansicht-Toggle: Einrückungs-Guides sofort anwenden und persistieren."""
        from instantlensdoc.core.app_settings import (
            get_editor_indent_guides,
            set_editor_indent_guides,
        )

        on = bool(checked)
        set_editor_indent_guides(on)
        if hasattr(self.editor, "set_indent_guides_visible"):
            self.editor.set_indent_guides_visible(on)
        persisted = bool(get_editor_indent_guides())
        if persisted != on:
            set_editor_indent_guides(on)
            persisted = bool(get_editor_indent_guides())
        if hasattr(self, "_indent_guides_action") and self._indent_guides_action is not None:
            self._indent_guides_action.blockSignals(True)
            self._indent_guides_action.setChecked(persisted)
            self._indent_guides_action.blockSignals(False)
        self._set_status("Einrückungs-Guides an" if persisted else "Einrückungs-Guides aus")

    def _toggle_current_line_highlight(self, checked: bool):
        """Ansicht-Toggle: aktuelle Zeile hervorheben, persistieren."""
        from instantlensdoc.core.app_settings import (
            get_editor_current_line_highlight,
            set_editor_current_line_highlight,
        )

        on = bool(checked)
        set_editor_current_line_highlight(on)
        if hasattr(self.editor, "set_current_line_highlight"):
            self.editor.set_current_line_highlight(on)
        persisted = bool(get_editor_current_line_highlight())
        if persisted != on:
            set_editor_current_line_highlight(on)
            persisted = bool(get_editor_current_line_highlight())
        if hasattr(self, "_current_line_hl_action") and self._current_line_hl_action is not None:
            self._current_line_hl_action.blockSignals(True)
            self._current_line_hl_action.setChecked(persisted)
            self._current_line_hl_action.blockSignals(False)
        self._set_status(
            "Aktuelle Zeile hervorheben an" if persisted else "Aktuelle Zeile hervorheben aus"
        )

    def _toggle_minimap(self, checked: bool):
        from instantlensdoc.core.app_settings import set_editor_minimap

        set_editor_minimap(bool(checked))
        self.editor.set_minimap_visible(bool(checked))
        self._set_status("Minimap an" if checked else "Minimap aus")

    def _toggle_markdown_preview(self, checked: bool):
        self.editor_pane.set_preview_visible(bool(checked))
        self._set_status("Markdown-Vorschau an" if checked else "Markdown-Vorschau aus")

    def _toggle_soft_wrap(self, checked: bool):
        """Ansicht-Toggle: Wortumbruch sofort anwenden und in Settings persistieren."""
        from instantlensdoc.core.app_settings import (
            get_editor_soft_wrap,
            set_editor_soft_wrap,
        )

        on = bool(checked)
        set_editor_soft_wrap(on)
        self.editor.set_soft_wrap(on)
        persisted = bool(get_editor_soft_wrap())
        if persisted != on:
            set_editor_soft_wrap(on)
            persisted = bool(get_editor_soft_wrap())
        if hasattr(self, "_soft_wrap_action") and self._soft_wrap_action is not None:
            self._soft_wrap_action.blockSignals(True)
            self._soft_wrap_action.setChecked(persisted)
            self._soft_wrap_action.blockSignals(False)
        self._set_status("Wortumbruch an" if persisted else "Wortumbruch aus")

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

    def _toggle_two_page_spread(self, checked: bool):
        self.pdf_view.set_two_page_spread(bool(checked))
        self._sync_spread_action(bool(checked))
        self._sync_continuous_action()

    def _toggle_continuous_scroll(self, checked: bool):
        self.pdf_view.set_continuous_scroll(bool(checked))
        self._sync_continuous_action(bool(checked))
        self._sync_spread_action()

    def _toggle_ann_layer(self, checked: bool):
        self.pdf_view.set_annotations_visible(bool(checked))
        self._sync_ann_layer_action(bool(checked))

    def _toggle_ann_lock(self, checked: bool):
        self.pdf_view.set_annotations_locked(bool(checked))
        self._sync_ann_lock_action(bool(checked))

    def _toggle_page_boxes(self, checked: bool):
        self.pdf_view.set_show_page_boxes(bool(checked))
        self._sync_page_boxes_action(bool(checked))

    def _toggle_page_number_overlay(self, checked: bool):
        self.pdf_view.set_show_page_number_overlay(bool(checked))
        self._sync_page_number_overlay_action(bool(checked))

    def _toggle_printer_marks(self, checked: bool):
        self.pdf_view.set_show_printer_marks(bool(checked))
        self._sync_printer_marks_action(bool(checked))

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

    def _sync_spread_action(self, enabled: bool | None = None):
        if enabled is None:
            enabled = self.pdf_view.two_page_spread_enabled()
        if hasattr(self, "_spread_action") and self._spread_action is not None:
            self._spread_action.blockSignals(True)
            self._spread_action.setChecked(bool(enabled))
            self._spread_action.blockSignals(False)

    def _sync_continuous_action(self, enabled: bool | None = None):
        if enabled is None:
            enabled = self.pdf_view.continuous_scroll_enabled()
        if hasattr(self, "_continuous_action") and self._continuous_action is not None:
            self._continuous_action.blockSignals(True)
            self._continuous_action.setChecked(bool(enabled))
            self._continuous_action.blockSignals(False)

    def _sync_ann_layer_action(self, enabled: bool):
        if hasattr(self, "_ann_layer_action") and self._ann_layer_action is not None:
            self._ann_layer_action.blockSignals(True)
            self._ann_layer_action.setChecked(bool(enabled))
            self._ann_layer_action.blockSignals(False)

    def _sync_ann_lock_action(self, enabled: bool):
        if hasattr(self, "_ann_lock_action") and self._ann_lock_action is not None:
            self._ann_lock_action.blockSignals(True)
            self._ann_lock_action.setChecked(bool(enabled))
            self._ann_lock_action.blockSignals(False)

    def _sync_page_boxes_action(self, enabled: bool):
        if hasattr(self, "_page_boxes_action") and self._page_boxes_action is not None:
            self._page_boxes_action.blockSignals(True)
            self._page_boxes_action.setChecked(bool(enabled))
            self._page_boxes_action.blockSignals(False)

    def _sync_page_number_overlay_action(self, enabled: bool):
        if (
            hasattr(self, "_page_num_overlay_action")
            and self._page_num_overlay_action is not None
        ):
            self._page_num_overlay_action.blockSignals(True)
            self._page_num_overlay_action.setChecked(bool(enabled))
            self._page_num_overlay_action.blockSignals(False)

    def _sync_printer_marks_action(self, enabled: bool):
        if hasattr(self, "_printer_marks_action") and self._printer_marks_action is not None:
            self._printer_marks_action.blockSignals(True)
            self._printer_marks_action.setChecked(bool(enabled))
            self._printer_marks_action.blockSignals(False)

    def _insert_snippet(self, index: int):
        if self.stack.currentWidget() is not self.editor_pane:
            self._set_status("Textbausteine nur im Editor")
            return
        from instantlensdoc.core.app_settings import get_editor_snippets

        snippets = get_editor_snippets()
        i = max(0, min(2, int(index)))
        text = snippets[i] if i < len(snippets) else ""
        if not text:
            self._set_status(f"Textbaustein {i + 1} ist leer")
            return
        self.editor.insertPlainText(text)
        self._set_status(f"Textbaustein {i + 1} eingefügt")

    def _save_snippet(self, index: int):
        if self.stack.currentWidget() is not self.editor_pane:
            self._set_status("Textbausteine nur im Editor")
            return
        from instantlensdoc.core.app_settings import set_editor_snippet

        cur = self.editor.textCursor()
        text = cur.selectedText().replace("\u2029", "\n")
        if not text.strip():
            # aktuelle Zeile
            from PySide6.QtGui import QTextCursor

            cur.select(QTextCursor.LineUnderCursor)
            text = cur.selectedText().replace("\u2029", "\n")
        i = max(0, min(2, int(index)))
        set_editor_snippet(i, text)
        preview = (text[:40] + "…") if len(text) > 40 else text.replace("\n", "⏎")
        self._set_status(f"Textbaustein {i + 1} gespeichert: {preview}")

    def _toggle_case_selection(self):
        if self.stack.currentWidget() is not self.editor_pane:
            self._set_status("Groß-/Kleinschreibung nur im Texteditor")
            return
        if self.editor.toggle_case_selection():
            self._set_status("Schreibweise umgeschaltet")
        else:
            self._set_status("Keine Textauswahl")

    def _transform_document_case(self, mode: str):
        if self.stack.currentWidget() is not self.editor_pane:
            self._set_status("Alles groß/klein nur im Texteditor")
            return
        if self.editor.transform_document_case(mode):
            label = "GROSS" if mode == "upper" else "klein"
            self._set_status(f"Datei → {label}")
        else:
            self._set_status("Keine Änderung (leer oder schon umgewandelt)")

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

    def _create_crash_report(self):
        from instantlensdoc.ui.help_dialog import create_crash_report_zip_dialog

        path = create_crash_report_zip_dialog(self)
        if path is not None:
            self._set_status(f"Crash-Report: {path}")

    def _open_workdir(self):
        """Ordner der aktuellen Datei bzw. Prozess-CWD im Dateimanager öffnen."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        folder: Path | None = None
        if self.doc and self.doc.path:
            p = Path(self.doc.path)
            folder = p.parent if p.exists() else None
        if folder is None and self.pdf_view.pdf_path:
            p = Path(self.pdf_view.pdf_path)
            folder = p.parent if p.exists() else None
        if folder is None or not folder.is_dir():
            folder = Path.cwd()
        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        if ok:
            self._set_status(f"Arbeitsverzeichnis: {folder}")
        else:
            QMessageBox.information(
                self,
                "Arbeitsverzeichnis",
                f"Ordner konnte nicht geöffnet werden.\nPfad:\n{folder}",
            )

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
        paths: list[str] = []
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if path:
                paths.append(path)
        if paths:
            for path in paths:
                self.open_path(path)
            event.acceptProposedAction()
            n = len(paths)
            self._set_status(f"{n} Datei(en) per Drag & Drop geöffnet")
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
            if self.pdf_view.store and (
                self.pdf_view.store.dirty
                or getattr(self.pdf_view, "_sidecar_save_pending", False)
            ):
                try:
                    self.pdf_view.schedule_sidecar_save(force=True)
                    if self.doc.path:
                        self._mark_unsaved(self.doc.path, False)
                    self._set_status(f"Autosave: Annotationen ({self.doc.display_name})")
                except Exception:
                    pass
            return
        if self.doc.kind not in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            return
        self._sync_editor_text_before_save()
        self.doc.text = self.editor.toPlainText()
        try:
            save_document(self.doc)
            self.doc.dirty = False
            if self.doc.path:
                self._mark_unsaved(self.doc.path, False)
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
            if self.doc.path:
                self._mark_unsaved(self.doc.path, True)
            else:
                self._update_unsaved_status()
        if self.stack.currentWidget() is self.editor_pane:
            words, chars = self.editor.word_stats()
            self.word_status_label.setText(f"{words} Wörter · {chars} Z.")

    def _on_pdf_document_changed(self):
        self._update_doc_status()
        if self.pdf_view.pdf_path:
            self._refresh_thumbs()
            self._refresh_outline(self.pdf_view.pdf_path)
            self._refresh_page_favorites()
        else:
            self.sidebar.clear_thumbs()
            self.sidebar.clear_annotations()
            self.sidebar.set_outline([])
            self.sidebar.clear_page_favorites()
            self.sidebar.clear_line_favorites()

    def _refresh_page_favorites(self):
        """Sidebar-Liste der nummerierten PDF-Favoriten aktualisieren."""
        if not self.pdf_view.pdf_path or self.pdf_view.store is None:
            self.sidebar.clear_page_favorites()
            return
        favs = self.pdf_view.list_page_favorites()
        labels: list[str] = []
        for p in favs:
            try:
                labels.append(
                    self.pdf_view.page_label(p) if self.pdf_view.has_page_labels() else ""
                )
            except Exception:
                labels.append("")
        self.sidebar.set_page_favorites(
            favs, labels=labels, current=self.pdf_view.page_index
        )

    def _on_page_favorites_reordered(self, pages: list):
        """Drag-Drop in der Favoriten-Sidebar → Sidecar-Reihenfolge speichern."""
        if not self.pdf_view.pdf_path or self.pdf_view.store is None:
            return
        order = []
        for p in pages or []:
            try:
                order.append(int(p))
            except (TypeError, ValueError):
                continue
        self.pdf_view.reorder_page_favorites(order)
        self._refresh_page_favorites()
        self._set_status(f"PDF-Favoriten umsortiert ({len(order)})")

    def _on_page_favorite_jump(self, page_index: int):
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            self._set_status("Favorit: PDF öffnen")
            return
        self.pdf_view.goto_page(int(page_index))
        self.sidebar.select_thumb(int(page_index))
        self._set_status(f"Favorit → Seite {int(page_index) + 1}")

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

    def _goto_line_or_page(self):
        """Ctrl+G: Editor → Zeile, PDF → Seite."""
        if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
            self._goto_page()
        else:
            self._goto_line()

    def _goto_line(self):
        if self.stack.currentWidget() is not self.editor_pane:
            if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
                self._goto_page()
                return
            QMessageBox.information(
                self,
                "Gehe zu Zeile",
                "Gehe zu Zeile ist im Texteditor verfügbar.",
            )
            return
        from instantlensdoc.ui.goto_line_dialog import GotoLineDialog

        GotoLineDialog(self.editor, self).exec()

    def _goto_page(self):
        if not self.pdf_view.pdf_path or self.pdf_view.page_count < 1:
            QMessageBox.information(
                self,
                "Gehe zu Seite",
                "Bitte zuerst ein PDF öffnen.",
            )
            return
        self.stack.setCurrentWidget(self.pdf_view)
        from instantlensdoc.ui.goto_page_dialog import GotoPageDialog

        GotoPageDialog(self.pdf_view, self).exec()
        self._update_doc_status()

    def duplicate_tab(self):
        """Editor: Inhalt als neues unbenanntes Dokument klonen; PDF: Datei erneut öffnen."""
        if not self.doc:
            self._set_status("Kein Dokument zum Duplizieren")
            return
        if self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            text = self.editor.toPlainText()
            src_name = self.doc.display_name
            enc = self.doc.meta.get("encoding")
            if self.doc.path:
                self.sidebar.add_document(self.doc.path)
            title = f"{src_name} (Kopie)"
            meta = {}
            if enc:
                meta["encoding"] = enc
            self.doc = Document(kind=self.doc.kind, title=title, text=text, dirty=True, meta=meta)
            self.editor.blockSignals(True)
            self.editor.setPlainText(text)
            self.editor.blockSignals(False)
            self.editor.clear_extra_selections()
            self.editor.clear_line_bookmarks()
            self._editor_marks.clear()
            self.sidebar.set_marks([])
            self.sidebar.clear_thumbs()
            self.sidebar.clear_annotations()
            self.stack.setCurrentWidget(self.editor_pane)
            self.setWindowTitle(self._app_title(title))
            self._update_doc_status()
            self._set_status(f"Tab dupliziert: {title}")
            return
        if self.doc.path:
            self.reopen_current()
            return
        self._set_status("Tab duplizieren: nur Editor-Inhalt oder gespeicherte Datei")

    def reopen_current(self):
        """Aktuelle Datei vom Datenträger neu laden."""
        if not self.doc or not self.doc.path:
            self._set_status("Erneut öffnen: keine gespeicherte Datei")
            return
        path = str(self.doc.path)
        if self._current_is_dirty():
            if not self._confirm_close_current(allow_discard=True):
                return
        enc = self.doc.meta.get("encoding") if self.doc.kind in (
            DocKind.TEXT,
            DocKind.MARKDOWN,
            DocKind.HTML,
        ) else None
        self.open_path(path, encoding=enc)
        self._set_status(f"Erneut geöffnet: {Path(path).name}")

    def _sync_editor_text_before_save(self) -> None:
        """Editor-Text für Speichern vorbereiten (optional Trailing-Whitespace trimmen)."""
        from instantlensdoc.core.app_settings import get_editor_trim_trailing_whitespace

        if get_editor_trim_trailing_whitespace():
            if self.editor.trim_trailing_whitespace():
                self._on_text_changed()

    def _render_pdf_page_image_path(self, page_index: int, *, scale: float = 2.0) -> Path:
        from ild_pdf import render_page

        if not self.pdf_view.pdf_path:
            raise ValueError("Kein PDF geladen")
        pdf_path = Path(self.pdf_view.pdf_path)
        out_dir = pdf_path.parent
        stem = pdf_path.stem
        out = out_dir / f"{stem}_page_{page_index + 1}.png"
        img = render_page(
            pdf_path,
            page_index,
            scale=scale,
            password=self.pdf_view.password,
        )
        img.save(out, "PNG")
        return out

    def _insert_page_image_to_editor(self):
        if not self.pdf_view.pdf_path:
            self._set_status("Kein PDF geladen")
            return
        idx = self.pdf_view.page_index
        try:
            out = self._render_pdf_page_image_path(idx)
        except Exception as e:
            QMessageBox.warning(self, "Seitenbild", str(e))
            return
        self.stack.setCurrentWidget(self.editor_pane)
        self.editor.insert_pdf_page_image_reference(out, page_label=f"Seite {idx + 1}")
        self._on_text_changed()
        self._set_status(f"Seitenbild Seite {idx + 1} → Editor ({out.name})")

    def _insert_all_page_images_to_editor(self):
        if not self.pdf_view.pdf_path:
            self._set_status("Kein PDF geladen")
            return
        n_pages = self.pdf_view.page_count
        if n_pages < 1:
            return
        paths: list[Path] = []
        try:
            for i in range(n_pages):
                paths.append(self._render_pdf_page_image_path(i))
        except Exception as e:
            QMessageBox.warning(self, "Seitenbilder", str(e))
            return
        self.stack.setCurrentWidget(self.editor_pane)
        for i, out in enumerate(paths):
            self.editor.insert_pdf_page_image_reference(out, page_label=f"Seite {i + 1}")
        self._on_text_changed()
        self._set_status(f"{len(paths)} Seitenbild(er) → Editor")

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
            self._last_tag_rename = None
        else:
            self.editor.redo()

    def _show_getting_started_wizard(self) -> None:
        """Wizard manuell öffnen (Hilfe-Menü)."""
        GettingStartedWizard(self).exec()

    def _maybe_show_getting_started_wizard(self) -> None:
        """Beim Start: Wizard zeigen, sofern nicht abgeschlossen / skip-once."""
        import os

        if os.environ.get("ILD_SMOKE_QT") == "1":
            return
        from instantlensdoc.core.app_settings import (
            consume_wizard_skip_once,
            get_wizard_completed,
        )

        if get_wizard_completed():
            return
        if consume_wizard_skip_once():
            self._set_status("Erste-Schritte-Wizard: dieses Mal übersprungen")
            return
        GettingStartedWizard(self).exec()

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

    def _on_search_export(self, fmt: str = "csv"):
        """Trefferliste der Sidebar als CSV oder JSON exportieren."""
        kind = str(fmt or "csv").strip().casefold()
        if kind not in ("csv", "json"):
            kind = "csv"
        hits = self.sidebar.search_hit_records()
        if not hits:
            self._set_status("Keine Suchergebnisse zum Export")
            QMessageBox.information(
                self,
                "Suchergebnis-Export",
                "Die Trefferliste ist leer — zuerst suchen.",
            )
            return
        query = self.sidebar.search_text()
        start = dialog_start_dir(get_last_export_dir())
        safe_q = "".join(c if c.isalnum() or c in "-_" else "_" for c in (query or "hits"))[
            :40
        ] or "hits"
        if kind == "json":
            default = str(Path(start) / f"search_{safe_q}.json")
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Suchergebnisse als JSON",
                default,
                "JSON (*.json)",
            )
            if not path:
                return
            dest = fulltext_mod.export_search_hits_json(path, hits, query=query)
        else:
            default = str(Path(start) / f"search_{safe_q}.csv")
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Suchergebnisse als CSV",
                default,
                "CSV (*.csv)",
            )
            if not path:
                return
            dest = fulltext_mod.export_search_hits_csv(path, hits, query=query)
        set_last_export_dir(Path(dest).parent)
        self._set_status(f"Suchergebnisse exportiert ({len(hits)}): {dest.name}")

    def _on_search(self, query: str):
        if not query:
            self._set_status("Leere Suche")
            return
        self._remember_search(query)
        if self.sidebar.fulltext_mode:
            paths = self.sidebar.document_paths()
            if self.doc and self.doc.path and str(self.doc.path) not in paths:
                paths.append(str(self.doc.path))
            pdf_only = bool(getattr(self.sidebar, "pdf_fulltext_mode", False))
            if pdf_only:
                paths = fulltext_mod.filter_pdf_paths(paths)
                if not paths:
                    self._set_status("Keine PDFs in der Liste für PDF-Schnellsuche")
                    self.sidebar.set_marks([f"Keine PDFs für „{query}“"])
                    return
                hits = fulltext_mod.search_open_pdfs(paths, query)
                scope_label = f"{len(paths)} PDF(s)"
            else:
                if not paths:
                    self._set_status("Keine Dokumente in der Liste für Volltextsuche")
                    return
                hits = fulltext_mod.search_paths(paths, query)
                scope_label = f"{len(paths)} Dokument(en)"
            if not hits:
                self.sidebar.set_marks([f"Keine Treffer für „{query}“"])
                self.sidebar.clear_search_hit_status()
                self._set_status(f"0 Treffer in {scope_label}")
                return
            lines = []
            payloads = []
            pdf_names: set[str] = set()
            for h in hits[:100]:
                snip = (h.snippet or "").strip() or query
                lines.append(
                    fulltext_mod.format_hit_line(
                        Path(h.path).name,
                        page=h.page,
                        line=h.line,
                        snippet=snip,
                        kind=h.kind,
                        query=query,
                    )
                )
                payloads.append((h.path, h.page, query))
                pdf_names.add(Path(h.path).name)
            self.sidebar.set_marks(lines, payloads)
            self.sidebar.set_search_hit_status(0, len(payloads))
            extra = f" · {len(pdf_names)} Datei(en)" if pdf_only else ""
            self._set_status(
                f"{len(hits)} Treffer in {scope_label}{extra} — Weiter/Zurück navigiert"
            )
            return
        if self.stack.currentWidget() is self.editor_pane:
            n = self.editor.find_and_highlight(query)
            self.sidebar.set_search_hit_status(1 if n else 0, n)
            self._set_status(f"{n} Treffer für „{query}“")
            lines = [f"Suche: {query} → {n} Treffer"] + self._editor_marks
            self.sidebar.set_marks(lines)
            self.sidebar.set_search_hit_status(1 if n else 0, n)
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
            try:
                from instantlensdoc.core.app_settings import (
                    get_search_snippet_context_chars,
                )

                snip_ctx = get_search_snippet_context_chars()
            except Exception:
                snip_ctx = 40
            if page_hits:
                for pi, blob in page_hits:
                    for line in blob.splitlines():
                        if query.lower() in line.lower():
                            snip = fulltext_mod._snippet_around(
                                line, query, context_chars=snip_ctx, width=96
                            )
                            hits.append(("page", pi, snip))
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
                        lines.append(
                            fulltext_mod.format_hit_line(
                                Path(pdf_path).name if pdf_path else "PDF",
                                page=pi,
                                line=None,
                                snippet=snip,
                                kind="pdf",
                                query=query,
                            )
                        )
                        payloads.append((str(pdf_path), pi, query))
                    else:
                        ann_snip = fulltext_mod._snippet_around(
                            f"{h.type.value} {h.text}",
                            query,
                            context_chars=max(20, snip_ctx - 4),
                            width=80,
                        )
                        lines.append(f"S.{h.page + 1} Ann.: {ann_snip}")
                        payloads.append(h)
                self.sidebar.set_marks(lines, payloads)
                if n_page:
                    self.sidebar.set_search_hit_status(1, n_page)
                self._set_status(
                    f"{n_page} Treffer auf Seite {self.pdf_view.page_index + 1} · "
                    f"{len(lines)} Einträge (PDF-Text/Annotationen)"
                )
            else:
                self.pdf_view.clear_search_highlights()
                self.sidebar.clear_search_hit_status()
                self._set_status("Kein Treffer — „Alle Docs“ oder OCR für gescannte PDFs")
            return
        self._set_status("Suche: Editor oder PDF öffnen")

    def _activate_search_hit_payload(self, payload) -> bool:
        """Doc-Treffer-Payload öffnen/hervorheben. True wenn verarbeitet."""
        if not (isinstance(payload, tuple) and len(payload) >= 2):
            return False
        if payload[0] in (None, "", "__search__"):
            return False
        q = payload[2] if len(payload) >= 3 else self.sidebar.search_text()
        self._on_fulltext_hit(str(payload[0]), payload[1], query=q)
        total = int(getattr(self.sidebar, "_search_hit_total", 0) or 0)
        cur = int(getattr(self.sidebar, "_search_hit_index", -1)) + 1
        if total > 0 and cur > 0:
            self._set_status(f"Treffer {cur}/{total} · {Path(str(payload[0])).name}")
        return True

    def _on_search_next(self):
        # Zuerst über Doc-Trefferliste (Alle Docs / Alle PDFs)
        adv = self.sidebar.advance_search_hit(delta=1)
        if adv is not None:
            _idx, payload = adv
            if self._activate_search_hit_payload(payload):
                return
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
                    self.sidebar.set_search_hit_status(1, n)
                    self._set_status(f"{n} Treffer auf aktueller Seite (1/{n})")
                else:
                    self.sidebar.clear_search_hit_status()
                    self._set_status("Kein Texttreffer auf aktueller Seite")
                return
            if self.pdf_view.search_next():
                i = self.pdf_view._search_index + 1
                n = self.pdf_view.search_hit_count()
                self.sidebar.set_search_hit_status(i, n)
                self._set_status(f"Treffer {i}/{n} auf Seite {self.pdf_view.page_index + 1}")
            else:
                self._set_status("Keine weiteren Treffer auf aktueller Seite")
            return
        self._set_status("Suche: Editor oder PDF öffnen")

    def _on_search_prev(self):
        adv = self.sidebar.advance_search_hit(delta=-1)
        if adv is not None:
            _idx, payload = adv
            if self._activate_search_hit_payload(payload):
                return
        q = self.sidebar.search_text()
        if self.stack.currentWidget() is self.editor_pane:
            if self.editor.find_prev(q or None):
                self._set_status("Vorheriger Treffer")
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
                    self.pdf_view._search_index = n - 1
                    self.pdf_view.canvas.set_search_highlights(
                        self.pdf_view._search_rects, self.pdf_view._search_index
                    )
                    self.sidebar.set_search_hit_status(n, n)
                    self._set_status(f"{n} Treffer auf aktueller Seite ({n}/{n})")
                else:
                    self.sidebar.clear_search_hit_status()
                    self._set_status("Kein Texttreffer auf aktueller Seite")
                return
            if self.pdf_view.search_prev():
                i = self.pdf_view._search_index + 1
                n = self.pdf_view.search_hit_count()
                self.sidebar.set_search_hit_status(i, n)
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
        self.sidebar.set_annotation_current_page(self.pdf_view.page_index)
        groups = None
        ann_groups = None
        if self.pdf_view.store is not None:
            groups = self.pdf_view.store.list_page_groups()
            if hasattr(self.pdf_view.store, "list_ann_groups"):
                ann_groups = self.pdf_view.store.list_ann_groups()
        self.sidebar.set_annotations(
            [p[0] for p in pairs],
            [p[1] for p in pairs],
            page_groups=groups,
            ann_groups=ann_groups,
        )
        n = len(self.pdf_view.store.annotations) if self.pdf_view.store else 0
        self.word_status_label.setText(f"{n} Ann.")
        if self.doc and self.doc.path and self.pdf_view.store is not None:
            pending = False
            if hasattr(self.pdf_view, "sidecar_save_pending"):
                pending = bool(self.pdf_view.sidecar_save_pending())
            else:
                pending = bool(getattr(self.pdf_view, "_sidecar_save_pending", False))
            self._mark_unsaved(
                self.doc.path, bool(self.pdf_view.store.dirty or pending)
            )
        else:
            self._update_unsaved_status()
            self._refresh_document_dirty_labels()

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
        if isinstance(payload, tuple) and len(payload) >= 2:
            q = payload[2] if len(payload) >= 3 else self.sidebar.search_text()
            self._on_fulltext_hit(str(payload[0]), payload[1], query=q)
            return
        if payload is not None and hasattr(payload, "page"):
            self.stack.setCurrentWidget(self.pdf_view)
            self.pdf_view.focus_annotation(payload)
            self._set_status(f"Annotation Seite {payload.page + 1}")

    def _on_fulltext_hit(self, path: str, page, query: str | None = None):
        self.open_path(path)
        q = (query or self.sidebar.search_text() or "").strip()
        if page is not None and self.stack.currentWidget() is self.pdf_view:
            self.pdf_view.goto_page(int(page))
            n = 0
            if q:
                n = self.pdf_view.highlight_search(q)
            if n:
                self._set_status(
                    f"Treffer: {Path(path).name} Seite {int(page) + 1} · {n} hervorgehoben"
                )
            else:
                self._set_status(f"Treffer: {Path(path).name} Seite {int(page) + 1}")
            return
        if q and self.stack.currentWidget() is self.editor_pane:
            self.editor.find_and_highlight(q)
            self._set_status(f"Treffer: {Path(path).name}")

    def _on_outline_jump(self, page_index: int):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Lesezeichen: PDF öffnen")
            return
        if page_index is None or int(page_index) < 0:
            self._set_status("Lesezeichen ohne Seiten-Ziel")
            return
        n = int(self.pdf_view.page_count or 0)
        idx = int(page_index)
        if n <= 0:
            self._set_status("Lesezeichen: keine Seiten")
            return
        if idx >= n:
            self._set_status(f"Lesezeichen-Ziel S. {idx + 1} außerhalb (1–{n})")
            return
        self.pdf_view.goto_page(idx)
        self.sidebar.select_thumb(idx)
        self._set_status(f"Lesezeichen → Seite {idx + 1}")

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

    def _on_thumb_rotate(self, page_index: int, degrees: int):
        """Thumbnail-Kontextmenü: Seite 90° drehen (Undo via Ctrl+Z)."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            return
        if self.pdf_view.rotate_at(int(page_index), int(degrees)):
            self._refresh_thumbs()
            self._update_doc_status()

    def _on_thumb_duplicate(self, page_index: int):
        """Thumbnail-Kontextmenü: Seite duplizieren (Undo Ctrl+Z)."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            return
        if self.pdf_view.duplicate_at(int(page_index)):
            self._refresh_thumbs()
            self._update_doc_status()

    def _on_thumb_delete(self, page_index: int):
        """Thumbnail-Kontextmenü: Seite löschen (Bestätigung + Undo Ctrl+Z)."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            return
        if self.pdf_view.delete_at(int(page_index), confirm=True):
            self._refresh_thumbs()
            self._update_doc_status()

    def _on_thumbs_batch_duplicate(self, pages: list):
        """Thumbnail-Mehrfachauswahl: Seiten batch-duplizieren."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            return
        idxs = [int(p) for p in (pages or [])]
        if self.pdf_view.duplicate_many(idxs):
            self._refresh_thumbs()
            self._update_doc_status()

    def _on_thumbs_batch_delete(self, pages: list):
        """Thumbnail-Mehrfachauswahl: Seiten batch-löschen."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            return
        idxs = [int(p) for p in (pages or [])]
        if self.pdf_view.delete_many(idxs, confirm=True):
            self._refresh_thumbs()
            self._update_doc_status()

    def _on_thumbs_batch_rotate(self, pages: list, degrees: int):
        """Thumbnail-Mehrfachauswahl: Seiten batch-drehen (±90, Undo Ctrl+Z)."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            return
        idxs = [int(p) for p in (pages or [])]
        if self.pdf_view.rotate_many(idxs, int(degrees)):
            self._refresh_thumbs()
            self._update_doc_status()

    def _on_thumbs_batch_extract(self, pages: list):
        """Thumbnail-Auswahl: Seiten als neues PDF extrahieren."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            return
        idxs = [int(p) for p in (pages or [])]
        self.pdf_view.extract_selected_pages_as_pdf(idxs)

    def _on_thumbs_batch_open(self, pages: list):
        """Thumbnail-Auswahl: Seiten als neues Dokument in neuem Tab öffnen."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            return
        idxs = [int(p) for p in (pages or [])]
        dest = None
        if hasattr(self.pdf_view, "open_selected_pages_as_document"):
            dest = self.pdf_view.open_selected_pages_as_document(idxs)
        else:
            dest = self.pdf_view.extract_selected_pages_as_pdf(idxs)
        if dest:
            self.open_path(str(dest))

    def _on_ann_group_export(self, group_id: str):
        """Sidebar: Ann.-Gruppe als JSON exportieren."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            return
        if hasattr(self.pdf_view, "export_selected_ann_group_json"):
            self.pdf_view.export_selected_ann_group_json(group_id)

    def _on_pdf_page_changed(self, page_index: int):
        self.sidebar.select_thumb(page_index)
        self.sidebar.set_annotation_current_page(page_index)
        self._refresh_page_favorites()
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
                get_editor_current_line_highlight,
                get_editor_indent_guides,
                get_editor_line_numbers,
                get_editor_markdown_preview,
                get_editor_minimap,
                get_editor_show_special_chars,
                get_editor_soft_tabs,
                get_editor_soft_wrap,
                get_editor_tab_width,
                get_pdf_grayscale,
                get_pdf_night_mode,
                get_sidecar_save_debounce_ms,
            )

            show_ln = get_editor_line_numbers()
            self.editor.set_line_numbers_visible(show_ln)
            if hasattr(self, "_line_numbers_action") and self._line_numbers_action is not None:
                self._line_numbers_action.blockSignals(True)
                self._line_numbers_action.setChecked(show_ln)
                self._line_numbers_action.blockSignals(False)
            show_mm = get_editor_minimap()
            self.editor.set_minimap_visible(show_mm)
            if hasattr(self, "_minimap_action") and self._minimap_action is not None:
                self._minimap_action.blockSignals(True)
                self._minimap_action.setChecked(show_mm)
                self._minimap_action.blockSignals(False)
            soft = get_editor_soft_wrap()
            self.editor.set_soft_wrap(soft)
            if hasattr(self, "_soft_wrap_action") and self._soft_wrap_action is not None:
                self._soft_wrap_action.blockSignals(True)
                self._soft_wrap_action.setChecked(soft)
                self._soft_wrap_action.blockSignals(False)
            self.editor.set_tab_width(get_editor_tab_width())
            if hasattr(self.editor, "set_soft_tabs"):
                self.editor.set_soft_tabs(get_editor_soft_tabs())
            if hasattr(self.editor, "set_indent_guides_visible"):
                ig = get_editor_indent_guides()
                self.editor.set_indent_guides_visible(ig)
                if hasattr(self, "_indent_guides_action") and self._indent_guides_action is not None:
                    self._indent_guides_action.blockSignals(True)
                    self._indent_guides_action.setChecked(ig)
                    self._indent_guides_action.blockSignals(False)
            if hasattr(self.editor, "set_current_line_highlight"):
                clh = get_editor_current_line_highlight()
                self.editor.set_current_line_highlight(clh)
                if hasattr(self, "_current_line_hl_action") and self._current_line_hl_action is not None:
                    self._current_line_hl_action.blockSignals(True)
                    self._current_line_hl_action.setChecked(clh)
                    self._current_line_hl_action.blockSignals(False)
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
            debounce_ms = self.pdf_view.apply_sidecar_debounce_ms(
                get_sidecar_save_debounce_ms()
            )
            self.pdf_view.apply_settings_colors()
            self.pdf_view.apply_toolbar_groups()
            if self.pdf_view.pdf_path:
                self._refresh_thumbs()
            self._set_status(
                f"Einstellungen gespeichert · Autosave {get_autosave_interval_sec()}s · "
                f"Sidecar-Debounce {debounce_ms} ms"
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
            store = self.pdf_view.store
            if not store:
                return False
            pending = False
            if hasattr(self.pdf_view, "sidecar_save_pending"):
                pending = bool(self.pdf_view.sidecar_save_pending())
            else:
                pending = bool(getattr(self.pdf_view, "_sidecar_save_pending", False))
            return bool(store.dirty or pending)
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
                if self.doc.path:
                    self._mark_unsaved(self.doc.path, False)
            if self.pdf_view.store:
                self.pdf_view.store.dirty = False
            self._update_unsaved_status()
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
            key = self._path_key(path)
            if key:
                self._unsaved_paths.discard(key)
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

    def close_tab_path(self, path: str) -> None:
        """Sidebar-Tab schließen (Mittelklick / Kontextmenü) — dirty → Speichern-Dialog."""
        target = str(Path(path)) if path else ""
        if not target:
            self._set_status("Kein Tab zum Schließen")
            return
        cur = str(Path(self.doc.path)) if self.doc and self.doc.path else None
        if cur and target == cur:
            self.close_current_tab()
            return
        key = self._path_key(target)
        if key and key in self._unsaved_paths and Path(target).is_file():
            # Dirty anderer Tab: erst aktivieren, dann mit Bestätigung schließen
            self.open_path(target)
            self.close_current_tab()
            return
        if not self.sidebar.remove_document(target):
            self._set_status("Tab nicht in der Liste")
            return
        if key:
            self._unsaved_paths.discard(key)
        try:
            self._save_session()
        except Exception:
            pass
        self._update_unsaved_status()
        self._refresh_document_dirty_labels()
        self._set_status(f"Tab geschlossen: {Path(target).name}")

    def close_other_tabs_keeping(self, keep_path: str) -> None:
        """Andere Tabs schließen; Keep-Pfad aktivieren (Kontextmenü „Andere schließen“)."""
        keep = str(Path(keep_path)) if keep_path else ""
        if not keep or not Path(keep).is_file():
            self._set_status("Kein Tab zum Behalten")
            return
        cur = str(Path(self.doc.path)) if self.doc and self.doc.path else None
        if cur != keep:
            self.open_path(keep)
        self.close_other_tabs()

    def close_other_tabs(self):
        """Alle Sidebar-Dokumente schließen außer dem aktuellen."""
        if not self.doc:
            self._set_status("Kein Dokument geöffnet")
            return
        keep = str(self.doc.path) if self.doc.path else None
        paths = list(self.sidebar.document_paths()) if hasattr(self.sidebar, "document_paths") else []
        if not paths:
            self._set_status("Keine weiteren Tabs")
            return
        closed = 0
        for p in paths:
            if keep and str(Path(str(p))) == str(Path(keep)):
                continue
            self.sidebar.remove_document(p)
            key = self._path_key(p)
            if key:
                self._unsaved_paths.discard(key)
            closed += 1
        if closed == 0:
            self._set_status("Keine anderen Tabs zum Schließen")
            return
        try:
            self._save_session()
        except Exception:
            pass
        self._update_unsaved_status()
        self._refresh_document_dirty_labels()
        self._set_status(f"{closed} andere Tab(s) geschlossen — aktuell bleibt offen")

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

    def _compare_text_tabs(self):
        """Zwei Sidebar-Tabs / Dateien Side-by-Side (Zeilen-Diff)."""
        tabs = self.sidebar.document_paths() if hasattr(self.sidebar, "document_paths") else []
        left_text = None
        left_label = None
        right_text = None
        right_label = None
        if self.doc and self.doc.kind != DocKind.PDF:
            left_text = self.editor.toPlainText()
            left_label = self.doc.display_name or "Aktuell"
        TextCompareDialog(
            self,
            tab_paths=tabs,
            left_path=str(self.doc.path) if self.doc and self.doc.path else None,
            left_text=left_text,
            left_label=left_label,
            right_text=right_text,
            right_label=right_label,
        ).exec()

    def _save_export_profile(self):
        from PySide6.QtWidgets import QFileDialog, QInputDialog
        from instantlensdoc.core.app_settings import (
            EXPORT_PROFILE_FORMATS,
            EXPORT_RASTER_DPI_CHOICES,
            dialog_start_dir,
            get_export_raster_dpi,
            get_last_export_dir,
            save_export_profile,
        )

        name, ok = QInputDialog.getText(self, "Export-Profil", "Name:")
        if not ok or not (name or "").strip():
            return
        dpi_items = [str(d) for d in EXPORT_RASTER_DPI_CHOICES]
        default_dpi = str(get_export_raster_dpi())
        dpi_idx = dpi_items.index(default_dpi) if default_dpi in dpi_items else 1
        dpi_str, ok = QInputDialog.getItem(
            self, "Export-Profil", "DPI:", dpi_items, dpi_idx, False
        )
        if not ok:
            return
        fmt_items = list(EXPORT_PROFILE_FORMATS)
        fmt, ok = QInputDialog.getItem(self, "Export-Profil", "Format:", fmt_items, 0, False)
        if not ok:
            return
        start = dialog_start_dir(get_last_export_dir())
        target = QFileDialog.getExistingDirectory(self, "Zielordner für Profil", start)
        if not target:
            # Leer erlauben — nur DPI/Format speichern
            target = ""
        try:
            profile = save_export_profile(
                name.strip(), dpi=int(dpi_str), format=fmt, target=target or None
            )
            tip = f"{profile['dpi']} DPI · {profile['format']}"
            if profile.get("target"):
                tip += f" · {Path(str(profile['target'])).name}"
            self._set_status(f"Export-Profil gespeichert: {profile['name']} ({tip})")
        except Exception as e:
            QMessageBox.warning(self, "Export-Profil", str(e))

    def _apply_export_profile(self):
        from PySide6.QtWidgets import QInputDialog
        from instantlensdoc.core.app_settings import (
            apply_export_profile,
            get_active_export_profile_name,
            get_export_profiles,
        )

        profiles = get_export_profiles()
        if not profiles:
            QMessageBox.information(
                self,
                "Export-Profil",
                "Keine Profile gespeichert.\nDatei → Exportieren → Export-Profil speichern…",
            )
            return
        names = [str(p["name"]) for p in profiles]
        active = get_active_export_profile_name()
        idx = names.index(active) if active in names else 0
        chosen, ok = QInputDialog.getItem(
            self, "Export-Profil", "Profil anwenden:", names, idx, False
        )
        if not ok or not chosen:
            return
        profile = apply_export_profile(chosen)
        if not profile:
            self._set_status("Export-Profil nicht gefunden")
            return
        tip = f"{profile['dpi']} DPI · {profile['format']}"
        if profile.get("target"):
            tip += f" · {profile['target']}"
        self._set_status(f"Export-Profil aktiv: {profile['name']} ({tip})")

    def _rebuild_clipboard_history_menu(self):
        menu = getattr(self, "_clipboard_history_menu", None)
        if menu is None:
            return
        menu.clear()
        hist = self.editor.clipboard_history() if hasattr(self.editor, "clipboard_history") else []
        if not hist:
            empty = QAction("(leer)", self)
            empty.setEnabled(False)
            menu.addAction(empty)
            return
        for i, text in enumerate(hist):
            preview = text.replace("\n", "⏎").replace("\t", "→")
            if len(preview) > 48:
                preview = preview[:45] + "…"
            a = QAction(f"{i + 1}: {preview}", self)
            a.setToolTip(text[:500])
            a.triggered.connect(lambda checked=False, idx=i: self._paste_clipboard_history(idx))
            menu.addAction(a)

    def _paste_clipboard_history(self, index: int):
        if self.stack.currentWidget() is not self.editor_pane:
            self._set_status("Zwischenablage-Verlauf nur im Editor")
            return
        if self.editor.paste_clipboard_history(index):
            self._set_status(f"Verlauf #{index + 1} eingefügt")
        else:
            self._set_status("Verlaufseintrag leer / ungültig")

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

    def _refresh_user_template_menu(self):
        from instantlensdoc.core.app_settings import get_user_doc_templates

        menu = getattr(self, "_m_user_templates", None)
        if menu is None:
            return
        menu.clear()
        templates = get_user_doc_templates()
        if not templates:
            empty = QAction("(keine gespeichert)", self)
            empty.setEnabled(False)
            menu.addAction(empty)
        else:
            for t in templates:
                tid = t["id"]
                title = t["title"]
                sub = menu.addMenu(title)
                sub.setToolTip(f"Vorlage „{title}“")
                act_open = QAction("Öffnen", self)
                act_open.setToolTip(f"Neues Dokument aus Vorlage „{title}“")
                act_open.triggered.connect(
                    lambda checked=False, i=tid: self.new_doc(f"user:{i}")
                )
                sub.addAction(act_open)
                act_ren = QAction("Umbenennen…", self)
                act_ren.triggered.connect(
                    lambda checked=False, i=tid, n=title: self._rename_user_template(i, n)
                )
                sub.addAction(act_ren)
                act_del = QAction("Löschen…", self)
                act_del.triggered.connect(
                    lambda checked=False, i=tid, n=title: self._delete_user_template(i, n)
                )
                sub.addAction(act_del)
        menu.addSeparator()
        act_order = QAction("Reihenfolge…", self)
        act_order.setToolTip("Vorlagen per Drag umsortieren und speichern")
        act_order.triggered.connect(self._reorder_user_templates_dialog)
        menu.addAction(act_order)
        act_folder = QAction("Vorlagen-Ordner öffnen…", self)
        act_folder.setToolTip("Spiegel-Ordner der Nutzer-Vorlagen im Explorer öffnen")
        act_folder.triggered.connect(self._open_user_templates_folder)
        menu.addAction(act_folder)
        act_export = QAction("Als Zip exportieren…", self)
        act_export.setToolTip("Vorlagen-Ordner als Zip speichern (templates.json + *.ildtpl.md)")
        act_export.triggered.connect(self._export_user_templates_zip)
        menu.addAction(act_export)
        act_import = QAction("Aus Zip importieren…", self)
        act_import.setToolTip("Vorlagen aus Zip laden und mit bestehenden mergen")
        act_import.triggered.connect(self._import_user_templates_zip)
        menu.addAction(act_import)

    def _export_user_templates_zip(self) -> None:
        """Nutzer-Vorlagen-Ordner als Zip exportieren."""
        from instantlensdoc.core.app_settings import (
            export_user_templates_zip,
            get_user_doc_templates,
        )

        if not get_user_doc_templates():
            QMessageBox.information(
                self,
                "Vorlagen exportieren",
                "Keine Nutzer-Vorlagen gespeichert.",
            )
            return
        start = dialog_start_dir(get_last_export_dir())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Vorlagen als Zip exportieren",
            str(Path(start) / "ild-templates.zip"),
            "Zip-Archiv (*.zip)",
        )
        if not path:
            return
        if not path.lower().endswith(".zip"):
            path = path + ".zip"
        try:
            dest = export_user_templates_zip(path)
        except Exception as exc:
            QMessageBox.warning(self, "Vorlagen exportieren", f"Export fehlgeschlagen:\n{exc}")
            return
        set_last_export_dir(Path(dest).parent)
        self._set_status(f"Vorlagen exportiert: {dest}")

    def _import_user_templates_zip(self) -> None:
        """Nutzer-Vorlagen aus Zip importieren (Dry-Run + Konflikt-Dialog)."""
        from instantlensdoc.core.app_settings import (
            dry_run_user_templates_zip_import,
            find_user_template_import_conflicts,
            import_user_templates_zip,
            parse_user_templates_zip,
        )

        start = dialog_start_dir(get_last_export_dir())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Vorlagen aus Zip importieren",
            start,
            "Zip-Archiv (*.zip);;Alle Dateien (*)",
        )
        if not path:
            return
        try:
            items = parse_user_templates_zip(path)
            dry_rows = dry_run_user_templates_zip_import(path)
            conflicts = find_user_template_import_conflicts(items)
            conflict_mode = "overwrite"
            if conflicts:
                titles = [
                    str(c["existing"].get("title") or c["incoming"].get("title") or "")
                    for c in conflicts
                ]
                decision = resolve_template_zip_conflicts(
                    titles, self, dry_run_rows=dry_rows
                )
                if decision == "cancel":
                    self._set_status("Vorlagen-Import abgebrochen")
                    return
                conflict_mode = decision
            imported = import_user_templates_zip(
                path, merge=True, conflict_mode=conflict_mode
            )
        except Exception as exc:
            QMessageBox.warning(self, "Vorlagen importieren", f"Import fehlgeschlagen:\n{exc}")
            return
        self._refresh_user_template_menu()
        set_last_export_dir(Path(path).parent)
        mode_label = (
            "Konflikte übersprungen"
            if conflict_mode == "skip"
            else "merge"
        )
        self._set_status(f"Vorlagen importiert: {len(imported)} ({mode_label})")
        QMessageBox.information(
            self,
            "Vorlagen importieren",
            f"{len(imported)} Vorlage(n) importiert ({mode_label}).",
        )

    def _reorder_user_templates_dialog(self) -> None:
        """Drag-Reihenfolge der Nutzer-Vorlagen speichern."""
        from PySide6.QtWidgets import QDialog

        from instantlensdoc.core.app_settings import (
            get_user_doc_templates,
            reorder_user_doc_templates,
        )
        from instantlensdoc.ui.templates_dialog import TemplatesOrderDialog

        templates = get_user_doc_templates()
        if not templates:
            QMessageBox.information(
                self,
                "Vorlagen-Reihenfolge",
                "Keine Nutzer-Vorlagen gespeichert.",
            )
            return
        dlg = TemplatesOrderDialog(templates, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        ordered = reorder_user_doc_templates(dlg.ordered_ids())
        self._refresh_user_template_menu()
        self._set_status(f"Vorlagen-Reihenfolge gespeichert ({len(ordered)})")

    def _open_user_templates_folder(self) -> None:
        """Nutzer-Vorlagen spiegeln und Ordner im Dateimanager öffnen."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from instantlensdoc.core.app_settings import sync_user_templates_folder

        folder = sync_user_templates_folder()
        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        if ok:
            self._set_status(f"Vorlagen-Ordner: {folder}")
        else:
            QMessageBox.information(
                self,
                "Vorlagen-Ordner",
                f"Ordner konnte nicht geöffnet werden.\nPfad:\n{folder}",
            )

    def _rename_user_template(self, template_id: str, current_title: str = "") -> None:
        from instantlensdoc.core.app_settings import rename_user_doc_template
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            "Vorlage umbenennen",
            "Neuer Name:",
            text=current_title or "Vorlage",
        )
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            self._set_status("Vorlage: Name fehlt")
            return
        entry = rename_user_doc_template(template_id, name)
        if not entry:
            QMessageBox.warning(self, "Vorlage", "Vorlage nicht gefunden.")
            return
        self._refresh_user_template_menu()
        self._set_status(f"Vorlage umbenannt: {entry['title']}")

    def _delete_user_template(self, template_id: str, title: str = "") -> None:
        from instantlensdoc.core.app_settings import delete_user_doc_template

        label = title or template_id
        r = QMessageBox.question(
            self,
            "Vorlage löschen",
            f"Vorlage „{label}“ wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if r != QMessageBox.Yes:
            return
        if delete_user_doc_template(template_id):
            self._refresh_user_template_menu()
            self._set_status(f"Vorlage gelöscht: {label}")
        else:
            QMessageBox.warning(self, "Vorlage", "Vorlage nicht gefunden.")

    def _save_doc_as_template(self):
        """Aktuelles Editor-Dokument als Nutzer-Vorlage speichern."""
        from instantlensdoc.core.app_settings import save_user_doc_template
        from PySide6.QtWidgets import QInputDialog

        if self.stack.currentWidget() is not self.editor_pane:
            QMessageBox.information(
                self,
                "Als Vorlage speichern",
                "Bitte zuerst ein Textdokument im Editor öffnen.",
            )
            return
        self._sync_editor_text_before_save()
        body = self.editor.toPlainText()
        if not body.strip():
            QMessageBox.information(
                self,
                "Als Vorlage speichern",
                "Das Dokument ist leer — nichts zu speichern.",
            )
            return
        default = ""
        if self.doc:
            default = (self.doc.title or "").strip()
            if self.doc.path and (not default or default == "Unbenannt"):
                default = Path(self.doc.path).stem
        name, ok = QInputDialog.getText(
            self,
            "Als Vorlage speichern",
            "Name der Vorlage:",
            text=default or "Meine Vorlage",
        )
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            self._set_status("Vorlage: Name fehlt")
            return
        entry = save_user_doc_template(title=name, body=body)
        self._refresh_user_template_menu()
        self._set_status(f"Vorlage gespeichert: {entry['title']}")

    def new_doc(self, template_id: str = "empty"):
        title, text = render_doc_template(template_id)
        tid = (template_id or "empty").strip().lower()
        kind = DocKind.MARKDOWN if tid == "notiz" or tid.startswith("user:") else DocKind.TEXT
        # Nutzer-Vorlagen: Markdown wenn Titel/Body wie Notiz aussieht
        if tid.startswith("user:") and text.lstrip().startswith("#"):
            kind = DocKind.MARKDOWN
        self.doc = Document(kind=kind, title=title, text=text)
        self.editor.setPlainText(text)
        self.editor.clear_extra_selections()
        self._editor_marks.clear()
        self.sidebar.set_marks([])
        self.sidebar.clear_annotations()
        self.stack.setCurrentWidget(self.editor_pane)
        self.setWindowTitle(self._app_title(title))
        self._update_doc_status()
        label = {
            "brief": "Neues Dokument (Brief)",
            "notiz": "Neues Dokument (Notiz)",
        }.get(tid, f"Neues Dokument ({title})" if tid.startswith("user:") else "Neues Dokument")
        self._set_status(label)

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

    def _pick_text_encoding(self, title: str, current: str | None = None) -> str | None:
        from instantlensdoc.core.app_settings import get_editor_text_encoding
        from instantlensdoc.core.documents import ENCODING_LABELS, TEXT_ENCODINGS, normalize_text_encoding
        from PySide6.QtWidgets import QInputDialog

        cur = normalize_text_encoding(current or get_editor_text_encoding())
        labels = [ENCODING_LABELS[e] for e in TEXT_ENCODINGS]
        idx = list(TEXT_ENCODINGS).index(cur) if cur in TEXT_ENCODINGS else 0
        choice, ok = QInputDialog.getItem(self, title, "Encoding:", labels, idx, False)
        if not ok or not choice:
            return None
        for enc, lab in ENCODING_LABELS.items():
            if lab == choice:
                return enc
        return cur

    def open_dialog_with_encoding(self):
        enc = self._pick_text_encoding("Öffnen mit Encoding")
        if not enc:
            return
        start = dialog_start_dir(get_default_open_dir())
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"Öffnen ({enc})",
            start,
            "Textdokumente (*.txt *.md *.html *.htm *.log *.csv);;Alle (*.*)",
        )
        if path:
            remember_recent_dir(path)
            self.open_path(path, encoding=enc)

    def open_path(self, path: str, *, encoding: str | None = None):
        try:
            self.doc = open_document(path, encoding=encoding)
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
                self._suppress_bookmark_persist = True
                try:
                    self.editor.clear_line_bookmarks()
                    self._load_line_bookmarks_sidecar(path)
                finally:
                    self._suppress_bookmark_persist = False
                self._refresh_line_favorites()
                self._editor_marks.clear()
                self.sidebar.set_marks([])
                self.sidebar.clear_thumbs()
                self.sidebar.clear_annotations()
            self._update_doc_status()
            enc = self.doc.meta.get("encoding")
            if enc:
                self._set_status(f"Geöffnet: {path} [{enc}]")
            else:
                self._set_status(f"Geöffnet: {path}")
        except Exception as e:
            _log.exception("Anzeige fehlgeschlagen: %s", path)
            QMessageBox.critical(self, "Öffnen", f"Anzeige fehlgeschlagen:\n{e}")

    def save_doc(self) -> bool:
        """Dokument speichern. Rückgabe True bei Erfolg (für Alle-speichern-Fehlerliste)."""
        quiet = bool(getattr(self, "_batch_save_quiet", False))
        # Ctrl+S: ausstehendes Sidecar-Debounce sofort flushen
        try:
            self.pdf_view.flush_sidecar_save()
        except Exception:
            pass
        st = self.license_manager.status()
        if not st.allowed:
            if not quiet:
                QMessageBox.warning(self, "Lizenz", "Speichern nicht möglich — Lizenz/Trial abgelaufen.")
            return False
        if not self.doc:
            return False
        if self.doc.kind == DocKind.PDF:
            if self.pdf_view.save_annotations():
                side = (
                    self.pdf_view.store.sidecar_path.name
                    if self.pdf_view.store
                    else "*.ildann.json"
                )
                if self.doc.path:
                    self._mark_unsaved(self.doc.path, False)
                self._set_status(f"PDF-Annotationen (Sidecar) gespeichert: {side}")
                return True
            return False
        if not self.doc.path:
            self.save_as()
            return not self._current_is_dirty()
        if self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            self._sync_editor_text_before_save()
        self.doc.text = self.editor.toPlainText()
        try:
            save_document(self.doc)
            self._remember_path(self.doc.path)
            self._mark_unsaved(self.doc.path, False)
            enc = self.doc.meta.get("encoding")
            suffix = f" [{enc}]" if enc else ""
            self._set_status(f"Gespeichert: {self.doc.path}{suffix}")
            return True
        except Exception as e:
            if not quiet:
                QMessageBox.critical(self, "Speichern", f"Speichern fehlgeschlagen:\n{e}")
            return False

    def save_doc_with_encoding(self):
        st = self.license_manager.status()
        if not st.allowed:
            QMessageBox.warning(self, "Lizenz", "Speichern nicht möglich — Lizenz/Trial abgelaufen.")
            return
        if not self.doc or self.doc.kind not in (
            DocKind.TEXT,
            DocKind.MARKDOWN,
            DocKind.HTML,
        ):
            QMessageBox.information(
                self,
                "Encoding",
                "Encoding gilt für Textdokumente (TXT/MD/HTML).",
            )
            return
        enc = self._pick_text_encoding(
            "Speichern mit Encoding",
            self.doc.meta.get("encoding"),
        )
        if not enc:
            return
        self._sync_editor_text_before_save()
        self.doc.text = self.editor.toPlainText()
        if not self.doc.path:
            self.save_as()
            if not self.doc.path:
                return
        try:
            save_document(self.doc, encoding=enc)
            self._remember_path(self.doc.path)
            self._set_status(f"Gespeichert ({enc}): {self.doc.path}")
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
                        self._sync_editor_text_before_save()
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
            self._sync_editor_text_before_save()
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

    def _run_ocr_document(self):
        """Batch-OCR aller PDF-Seiten mit Fortschrittsdialog."""
        from PySide6.QtWidgets import QApplication, QDialog, QProgressDialog

        if not self.doc or self.doc.kind != DocKind.PDF or not self.doc.path:
            QMessageBox.information(
                self,
                "OCR gesamtes PDF",
                "Bitte zuerst ein PDF öffnen.",
            )
            return

        ok, msg = ocr_mod.tesseract_available()
        dlg = OcrDialog(
            self,
            need_file=False,
            default_label=f"{Path(self.doc.path).name} (alle Seiten)",
        )
        # Batch-OCR liefert immer editierbaren Text
        dlg.rb_editable.setChecked(True)
        dlg.rb_searchable.setEnabled(False)
        if dlg.exec() != QDialog.Accepted:
            return
        if not ok:
            QMessageBox.information(self, "OCR — Tesseract fehlt", msg)
            self._set_status("OCR nicht verfügbar")
            return

        lang = dlg.lang_code()
        pdf_path = Path(self.doc.path)
        cancelled = {"flag": False}

        # Seitenzahl vorab für Dialog
        try:
            import pypdfium2 as pdfium

            _doc = pdfium.PdfDocument(str(pdf_path))
            total = len(_doc)
            _doc.close()
        except Exception:
            total = max(1, int(self.pdf_view.page_count or 1))

        prog = QProgressDialog("OCR gesamtes PDF…", "Abbrechen", 0, total, self)
        prog.setWindowTitle("Batch-OCR")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        prog.setValue(0)
        prog.show()
        QApplication.processEvents()

        def on_progress(page: int, n: int, label: str) -> bool:
            if prog.wasCanceled():
                cancelled["flag"] = True
                return False
            prog.setMaximum(max(1, n))
            prog.setValue(page)
            prog.setLabelText(f"OCR: {pdf_path.name} — {label}")
            QApplication.processEvents()
            return True

        try:
            result = ocr_mod.ocr_pdf_document(
                pdf_path,
                lang=lang,
                progress=on_progress,
            )
        except ocr_mod.OcrUnavailable as e:
            QMessageBox.information(self, "OCR — Tesseract fehlt", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "OCR gesamtes PDF", f"OCR fehlgeschlagen:\n{e}")
            return
        finally:
            prog.close()

        if result.cancelled or cancelled["flag"]:
            self._set_status(
                f"Batch-OCR abgebrochen ({result.pages_done}/{result.pages_total})"
            )
            if not result.text.strip():
                return

        title = f"OCR — {pdf_path.name} ({result.pages_done}/{result.pages_total})"
        self.stack.setCurrentWidget(self.editor_pane)
        self.editor.setPlainText(result.text)
        self.doc = Document(kind=DocKind.TEXT, title=title, text=result.text)
        self.setWindowTitle(self._app_title(title))
        status = (
            f"Batch-OCR ({result.lang}): {result.pages_done}/{result.pages_total} Seiten"
        )
        if result.cancelled:
            status += " (abgebrochen)"
        self._set_status(status)

    def _sanitize_pdf(self):
        """Schnellaktion: PDF bereinigen, optional Metadaten strippen."""
        from PySide6.QtWidgets import (
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QLabel,
            QVBoxLayout,
        )

        if not self.pdf_view.pdf_path:
            QMessageBox.information(self, "PDF bereinigen", "Bitte zuerst ein PDF öffnen.")
            return
        src = Path(self.pdf_view.pdf_path)

        dlg = QDialog(self)
        dlg.setWindowTitle("PDF bereinigen")
        dlg.resize(420, 160)
        layout = QVBoxLayout(dlg)
        layout.addWidget(
            QLabel(
                f"„{src.name}“ neu speichern.\n"
                "Entfernt verwaiste Objekte; Metadaten optional strippen."
            )
        )
        cb_meta = QCheckBox("Metadaten entfernen (Titel, Autor, XMP, …)")
        cb_meta.setChecked(True)
        layout.addWidget(cb_meta)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if dlg.exec() != QDialog.Accepted:
            return

        default = str(Path(dialog_start_dir(src.parent)) / f"{src.stem}_clean.pdf")
        out, _ = QFileDialog.getSaveFileName(
            self,
            "Bereinigtes PDF speichern",
            default,
            "PDF (*.pdf)",
        )
        if not out:
            return
        dest = Path(out)
        if dest.suffix.lower() != ".pdf":
            dest = dest.with_suffix(".pdf")
        if not confirm_overwrite_export(dest, self):
            return
        try:
            from ild_pdf import sanitize_pdf

            sanitize_pdf(src, strip_meta=cb_meta.isChecked(), out_path=dest)
        except Exception as e:
            QMessageBox.warning(self, "PDF bereinigen", str(e))
            return
        remember_recent_dir(dest)
        self._set_status(
            f"PDF bereinigt: {dest.name}"
            + (" (ohne Metadaten)" if cb_meta.isChecked() else "")
        )
        QMessageBox.information(
            self,
            "PDF bereinigen",
            f"Gespeichert:\n{dest}",
        )

    def _forms(self):
        try:
            FormBuilderDialog(self).exec()
        except Exception as e:
            QMessageBox.critical(self, "Formulare", f"Formulargenerator fehlgeschlagen:\n{e}")

    def _license(self):
        if LicenseDialog(self.license_manager, self).exec():
            self._update_license_status()
