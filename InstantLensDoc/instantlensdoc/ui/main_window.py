"""Hauptfenster: Menüleiste, Seitenleiste, Editor, Statusleiste."""

from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QDockWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc import __version__
from instantlensdoc.config import DISPLAY_NAME, icon_paths_for_qt
from instantlensdoc.core.documents import (
    DocKind,
    Document,
    backup_ildbak,
    open_document,
    render_doc_template,
    save_document,
)
from instantlensdoc.core.manual_backup import (
    append_backup_log,
    backup_dir,
    manual_backup_file,
    manual_backup_text,
)
from instantlensdoc.core import ocr as ocr_mod
from instantlensdoc.core.layout import LayoutDocument
from instantlensdoc.core import recent as recent_mod
from instantlensdoc.core import recent_searches as recent_searches_mod
from instantlensdoc.core import recent_tags as recent_tags_mod
from instantlensdoc.license import LicenseManager
from instantlensdoc.ui.editor import EditorPane
from instantlensdoc.ui.form_builder import FormBuilderDialog
from instantlensdoc.ui.attachments_dialog import AttachmentsDialog
from instantlensdoc.ui.help_dialog import AboutDialog, GettingStartedWizard, HelpDialog
from instantlensdoc.ui.license_dialog import LicenseDialog
from instantlensdoc.ui.ocr_dialog import OcrDialog
from instantlensdoc.ui.pdf_view import PdfViewer
from instantlensdoc.ui.sidebar import Sidebar
from instantlensdoc.ui.welcome import WelcomePage
from instantlensdoc.dtp.canvas import DtpPane
from instantlensdoc.core import fulltext as fulltext_mod
from instantlensdoc.core.app_settings import (
    dialog_start_dir,
    get_ann_layer_types_visible,
    get_annotations_visible,
    get_autosave_enabled,
    get_crash_recovery_enabled,
    get_crash_recovery_max_age_hours,
    get_autosave_interval_sec,
    get_default_open_dir,
    get_editor_doc_split,
    get_editor_doc_split_sync_scroll,
    get_editor_doc_split_vertical,
    get_editor_markdown_preview,
    get_editor_soft_wrap,
    get_last_export_dir,
    get_last_text_pdf_dir,
    get_minimize_to_tray,
    get_page_size_unit,
    get_pdf_thumbnail_scale,
    get_restore_session_on_start,
    get_restore_window_geometry_on_start,
    get_favorites_bar_visible,
    get_presentation_auto_advance_sec,
    get_presentation_black_background,
    get_presentation_countdown_color,
    get_presentation_countdown_position,
    get_presentation_hide_annotations,
    get_presentation_show_page_number,
    get_text_pdf_font_size,
    get_text_pdf_margin,
    get_text_pdf_open_after,
    get_update_check_on_start,
    get_update_dismissed_version,
    set_presentation_show_page_number,
    set_update_dismissed_version,
    get_window_geometry_b64,
    get_window_state_b64,
    remember_recent_dir,
    remember_project_workspace,
    get_project_workspaces,
    get_active_project_workspace,
    set_last_export_dir,
    set_last_text_pdf_dir,
    set_window_geometry_b64,
    set_window_state_b64,
    toggle_page_size_unit,
)
from instantlensdoc.ui.batch_dialog import BatchConvertDialog
from instantlensdoc.ui.esign_dialog import ESignDialog
from instantlensdoc.ui.mail_merge_dialog import MailMergeDialog
from instantlensdoc.ui.file_dialogs import (
    confirm_overwrite_export,
    resolve_template_zip_conflicts,
)


class GlobalFavoritesList(QListWidget):
    """Horizontale globale Favoriten; Drag InternalMove → Reihenfolge — 1.7.3."""

    favorites_reordered = Signal(list)  # list[tuple[str, int]]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlow(QListWidget.LeftToRight)
        self.setWrapping(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFixedHeight(32)
        self.setSpacing(2)
        self.setFrameShape(QFrame.NoFrame)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setMovement(QListWidget.Snap)
        self.setResizeMode(QListWidget.Adjust)
        self.setToolTip(
            "Globale Favoriten (ildfav-v1) — Klick springt; Doppelklick: Label; "
            "Rechtsklick: Label / neuer Tab; ziehen zum Umsortieren; "
            "Esc → Fokus zurück auf Liste; Enter bestätigt Edit; "
            "leerer Edit → Dateiname ohne extra Schritt — 1.7.5"
        )
        self._reorder_enabled = True

    def dropEvent(self, event):  # noqa: N802
        if not self._reorder_enabled:
            event.ignore()
            return
        super().dropEvent(event)
        order: list[tuple[str, int]] = []
        for i in range(self.count()):
            item = self.item(i)
            if item is None:
                continue
            data = item.data(Qt.UserRole)
            if isinstance(data, (tuple, list)) and len(data) >= 2:
                try:
                    order.append((str(data[0]), int(data[1])))
                except (TypeError, ValueError):
                    continue
        if order:
            self.favorites_reordered.emit(order)
from instantlensdoc.ui.pdf_tools_dialog import PdfToolsDialog
from instantlensdoc.ui.watermark_dialog import WatermarkDialog
from instantlensdoc.ui.annotation_search_dialog import AnnotationSearchDialog
from instantlensdoc.ui.batch_rename_dialog import BatchRenameDialog
from instantlensdoc.ui.compare_dialog import PdfCompareDialog
from instantlensdoc.ui.doc_tab_bar import DocumentTabBar
from instantlensdoc.ui.ribbon_bar import RibbonBar
from instantlensdoc.ui.text_compare_dialog import TextCompareDialog
from instantlensdoc.ui.settings_dialog import SettingsDialog
from instantlensdoc.ui.theme import (
    apply_theme,
    cycle_theme_mode,
    install_system_theme_watch,
    load_theme_mode,
    resolve_theme,
    set_follow_system,
    theme_status_text,
    toggle_high_contrast,
    toggle_theme,
)
from instantlensdoc.ui.keyboard_help import KeyboardHelpDialog
from instantlensdoc.ui.password_dialog import (
    CompressPdfDialog,
    PdfSecurityDialog,
    RemovePasswordDialog,
    SetPasswordDialog,
)
from instantlensdoc.ui.metadata_dialog import MetadataDialog
from instantlensdoc.ui.doc_stats_dialog import DocStatsDialog
from instantlensdoc.ui.form_fields_dialog import FormFieldsDialog
from instantlensdoc.ui.page_size_dialog import PageSizeDialog
from instantlensdoc.core import session as session_mod
from instantlensdoc.core.i18n import apply_ui_language, sync_from_settings
from ild_pdf.outline import extract_outline
import logging

_log = logging.getLogger("instantlensdoc.ui.main")


class MainWindow(QMainWindow):
    def __init__(self, license_manager: LicenseManager):
        super().__init__()
        sync_from_settings()
        apply_ui_language(self)  # Sprache + RTL aus Settings — 2.6.18
        self.license_manager = license_manager
        self.doc: Document | None = None
        self.layout_doc = LayoutDocument()
        try:
            from instantlensdoc.dtp.model import DtpDocument

            self.dtp_doc = DtpDocument.sample("A5")
        except Exception:
            self.dtp_doc = None
        self._editor_marks: list[str] = []
        self._recent_menu = None
        self._workspace_menu = None
        self._theme_action: QAction | None = None
        self._theme_system_action: QAction | None = None
        self._ann_search_dialog: AnnotationSearchDialog | None = None
        self._doc_stats_dialog: DocStatsDialog | None = None
        self._workspace_layout_menu = None
        self._crypto_reload_prefill: str | None = None  # unsicher, Toggle; nie loggen — 1.6.3
        self._autosave_enabled = bool(get_autosave_enabled())
        self._thumb_lazy_timer: QTimer | None = None
        self._thumb_lazy_queue: list[int] = []
        self._thumb_lazy_token: int | None = None
        self._thumb_lazy_loaded: set[int] = set()
        self._thumb_lazy_page_count: int = 0
        self._thumb_lazy_virtual: bool = False
        self._tray: QSystemTrayIcon | None = None
        self._tray_menu: QMenu | None = None
        self._force_quit = False
        self._presentation_active = False
        self._presentation_prev: dict | None = None
        self._presentation_timer: QTimer | None = None
        self._presentation_page_num_on = True
        self._presentation_paused = False
        self._presentation_interval_sec = 0
        self._presentation_remaining = 0
        self._presentation_countdown: QLabel | None = None
        self._fav_bar_buttons: list = []
        self._unsaved_paths: set[str] = set()
        self._readonly_preview_paths: set[str] = set()  # Merge-Vorschau-Tabs — 1.1.5
        self._ann_zero_sticky = False  # 0-Treffer-Status dauerhaft — 1.1.7
        self._secondary_path: str | None = None
        self._secondary_kind: str = ""  # "pdf" | "editor" | "" — Panel-Typ je Session
        self._last_tag_rename: tuple[str, str] | None = None  # (old, new) für einstufiges Undo
        self._batch_save_quiet: bool = False  # Alle-speichern: Einzeldialoge unterdrücken
        # Last-Page / Scroll je Tab (path_key → {page, scale, scroll_y}) — 0.9.1
        self._tab_view_state: dict[str, dict] = {}
        # Geparste Dokumente offener Tabs (path_key → (signatur, Document)) — Tab-Wechsel /
        # Schließen des Nachbar-Tabs importiert DOCX/RTF/XLSX nicht erneut — 2.6.54
        self._doc_cache: dict[str, tuple[tuple[int, int], Document]] = {}
        # Seitengröße-Statustext je (pdf, mtime, seite, einheit) — kein pikepdf-Open pro
        # Statusupdate (bis zu 7× je Tab-Wechsel) — 2.6.54
        self._page_size_cache: dict[tuple, str] = {}
        self._thumb_lazy_open_gen: int = 0  # Dokument-Token des Thumb-Laufs — 2.6.54
        self._doc_tab_bar_sync_pending = False
        self._last_tab_close_ms: float = 0.0  # Diagnose: Dauer des letzten Tab-Schließens
        self._editor_only_actions: list = []
        self._editor_only_menus: list = []
        self._last_backup_path = None  # Pfad der letzten Backup-Datei — 1.0.1
        self._last_outline_export_dir = None  # Zielordner Outlines-Export — 1.3.4
        self._last_text_pdf_status_path = None  # Text→PDF Status-Klick → Ordner — 1.7.4
        self._text_pdf_toast_active = False
        self._update_status_source_tip = ""  # Tooltip Quelle VERSION.txt/docs — 1.7.4
        self._update_status_reference_path = None  # Klick öffnet lokale VERSION — 1.7.5

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
        # Geräte/Scan-Menü nach Build absichern + Menüleiste sichtbar — 2.6.51
        try:
            self._ensure_devices_menu(self.menuBar())
        except Exception:
            pass
        try:
            apply_ui_language(self)
        except Exception:
            pass
        self._restore_window_geometry()
        try:
            self._apply_chrome_mode()
        except Exception:
            if not getattr(self, "_presentation_active", False):
                self.menuBar().setVisible(True)
        self.apply_tray_setting()
        self._refresh_recent()
        self._refresh_workspaces()
        self._refresh_recent_searches()
        self._update_license_status()
        apply_theme()
        self._sync_theme_menu()
        # System-Theme live nachziehen wenn „folgen“ aktiv — 1.4.1
        install_system_theme_watch(self._on_system_theme_live)
        if get_editor_doc_split() and get_editor_doc_split_sync_scroll():
            self._apply_doc_split_sync_scroll()
        self._update_sync_scroll_status_indicator()
        self._update_thumb_cache_debug_status()
        # Thumb Auto-Prune: Status-Callback + Intervall-Timer — 2.4.3
        try:
            from instantlensdoc.core.thumb_cache import set_prune_status_callback

            set_prune_status_callback(self._on_thumb_prune_status)
        except Exception:
            pass
        self._thumb_prune_timer = QTimer(self)
        self._thumb_prune_timer.timeout.connect(self._thumb_prune_tick)
        self._sync_thumb_prune_timer()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(get_autosave_interval_sec() * 1000)
        self._autosave_timer.timeout.connect(self._autosave_tick)
        self._autosave_timer.start()
        # Crash-Recovery vor Session-Restore — 1.8.0
        QTimer.singleShot(150, self._maybe_recover_orphans)
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
        # Hintergrund-Thumbs stoppen; kein Warten auf Worker (Daemon-Threads) — 2.6.54
        try:
            self._stop_thumb_lazy()
        except Exception:
            pass
        try:
            self._save_window_geometry()
        except Exception:
            pass
        try:
            self._save_session()
        except Exception:
            pass
        try:
            from instantlensdoc.core.scan_procs import kill_tracked_scan_children

            kill_tracked_scan_children(wia_orphans=True)
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
        """Session-Tab-Reihenfolge nach Drag in der Dokumentliste speichern (0.9.3)."""
        self._save_session()
        self._refresh_doc_tab_bar()

    def _on_document_renamed(self, _path: str = "") -> None:
        """Tab-Anzeige-Label geändert → Session speichern (0.9.4)."""
        self._save_session()

    def _on_document_label_reset(self, _path: str = ""):
        """Tab-Label auf Originaltitel zurückgesetzt → Session (0.9.5)."""
        self._save_session()
        self._set_status("Tab-Titel gespeichert")
        n = len(self._session_paths())
        self._set_status(f"Tab-Reihenfolge gespeichert ({n} Tab(s))")

    def _main_splitter_sizes(self) -> list[int]:
        """Aktuelle Sidebar/Viewer-Splitter-Größen (0.9.3)."""
        try:
            sp = getattr(self, "main_splitter", None)
            if sp is None:
                return []
            sizes = [int(x) for x in sp.sizes()]
            if len(sizes) >= 2 and sizes[0] > 0 and sizes[1] > 0:
                return sizes[:2]
        except Exception:
            pass
        return []

    def _apply_main_splitter_sizes(self, sizes) -> bool:
        """Splitter-Größen wiederherstellen. True wenn angewendet."""
        try:
            if not isinstance(sizes, (list, tuple)) or len(sizes) < 2:
                return False
            a, b = int(sizes[0]), int(sizes[1])
            if a <= 0 or b <= 0:
                return False
            sp = getattr(self, "main_splitter", None)
            if sp is None:
                return False
            sp.setSizes([a, b])
            return True
        except Exception:
            return False

    def _on_main_splitter_moved(self, *_args) -> None:
        """Splitter ziehen → Session merken (debounced über Timer)."""
        if getattr(self, "_splitter_save_timer", None) is None:
            self._splitter_save_timer = QTimer(self)
            self._splitter_save_timer.setSingleShot(True)
            self._splitter_save_timer.timeout.connect(self._save_session)
        self._splitter_save_timer.start(400)

    def _capture_current_tab_view_state(self) -> None:
        """Aktuelle Seite/Zoom/Scroll für den geöffneten Tab merken (0.9.1)."""
        if not self.doc or not self.doc.path:
            return
        key = self._path_key(self.doc.path)
        if not key:
            return
        page = 0
        scale = 1.5
        scroll_y = 0
        try:
            if self.doc.kind == DocKind.PDF and self.pdf_view.pdf_path:
                page = int(self.pdf_view.page_index or 0)
                scale = float(self.pdf_view.scale or 1.5)
                bar = self.pdf_view.scroll.verticalScrollBar()
                scroll_y = int(bar.value()) if bar is not None else 0
            elif self.stack.currentWidget() is self.editor_pane:
                bar = self.editor.verticalScrollBar()
                scroll_y = int(bar.value()) if bar is not None else 0
        except Exception:
            pass
        self._tab_view_state[key] = {
            "page": max(0, page),
            "scale": float(scale) if scale > 0 else 1.5,
            "scroll_y": max(0, scroll_y),
        }

    def _restore_tab_view_state(self, path: str) -> None:
        """Gespeicherte Last-Page / Zoom / Scroll für Tab anwenden (0.9.2 Zoom)."""
        key = self._path_key(path)
        if not key:
            return
        st = self._tab_view_state.get(key)
        if not st:
            return
        try:
            page = max(0, int(st.get("page", 0) or 0))
        except (TypeError, ValueError):
            page = 0
        try:
            scale = float(st.get("scale", 1.5) or 1.5)
        except (TypeError, ValueError):
            scale = 1.5
        try:
            scroll_y = max(0, int(st.get("scroll_y", 0) or 0))
        except (TypeError, ValueError):
            scroll_y = 0
        if self.doc and self.doc.kind == DocKind.PDF and self.pdf_view.pdf_path:
            # Session-Zoom hat Vorrang vor Fit/Default-Zoom aus load()
            if scale > 0:
                self.pdf_view._suppress_default_zoom = True
            if 0 <= page < int(self.pdf_view.page_count or 0):
                self.pdf_view.page_index = page
            if scale > 0:
                self.pdf_view.set_scale(scale, immediate=True)
            else:
                self.pdf_view.refresh()
            if not self.pdf_view._canvas_has_page_image():
                self.pdf_view._ensure_page_painted(warn=False)

            def _apply_scroll(sy: int = scroll_y) -> None:
                try:
                    bar = self.pdf_view.scroll.verticalScrollBar()
                    if bar is not None:
                        bar.setValue(min(sy, bar.maximum()))
                except Exception:
                    pass

            def _clear_zoom_suppress() -> None:
                try:
                    self.pdf_view._suppress_default_zoom = False
                except Exception:
                    pass

            QTimer.singleShot(0, _apply_scroll)
            QTimer.singleShot(80, _apply_scroll)
            # Fit-Default-Timer aus load() (~0ms) überdauern, dann Flag lösen
            QTimer.singleShot(200, _clear_zoom_suppress)
        elif self.stack.currentWidget() is self.editor_pane:

            def _apply_ed_scroll(sy: int = scroll_y) -> None:
                try:
                    bar = self.editor.verticalScrollBar()
                    if bar is not None:
                        bar.setValue(min(sy, bar.maximum()))
                except Exception:
                    pass

            QTimer.singleShot(0, _apply_ed_scroll)

    # ---- Tab-Dokument-Cache (geparste Nicht-PDF-Dokumente offener Tabs) — 2.6.54 ----
    _DOC_CACHE_KINDS = (DocKind.DOCX, DocKind.RTF, DocKind.XLSX, DocKind.HTML, DocKind.TEXT, DocKind.MARKDOWN)

    @staticmethod
    def _doc_cache_sig(path: str | Path | None) -> tuple[int, int] | None:
        try:
            st = Path(str(path)).stat()
        except (OSError, TypeError, ValueError):
            return None
        return (int(st.st_mtime_ns), int(st.st_size))

    def _doc_cache_put(self, path: str | Path | None, doc: Document | None) -> None:
        """Dokument für diesen Tab merken (nur Kinds mit teurem Import)."""
        if doc is None or not path:
            return
        if getattr(doc, "kind", None) not in self._DOC_CACHE_KINDS:
            return
        key = self._path_key(path)
        sig = self._doc_cache_sig(path)
        if not key or sig is None:
            return
        self._doc_cache[key] = (sig, doc)

    def _doc_cache_get(self, path: str | Path | None) -> Document | None:
        """Gecachtes Dokument, falls Datei unverändert — oder dirty (Edits gewinnen)."""
        key = self._path_key(path) if path else None
        if not key:
            return None
        entry = self._doc_cache.get(key)
        if not entry:
            return None
        sig, doc = entry
        try:
            if doc.path is None or self._path_key(doc.path) != key:
                self._doc_cache.pop(key, None)
                return None
        except Exception:
            self._doc_cache.pop(key, None)
            return None
        if bool(getattr(doc, "dirty", False)):
            return doc
        if self._doc_cache_sig(path) != sig:
            # Extern geändert → neu importieren
            self._doc_cache.pop(key, None)
            return None
        return doc

    def _doc_cache_store_current(self) -> None:
        """Aktuelles Dokument vor einem Tab-Wechsel in den Cache legen (inkl. Edits)."""
        doc = self.doc
        if doc is None or not doc.path:
            return
        if doc.kind not in self._DOC_CACHE_KINDS:
            return
        key = self._path_key(doc.path)
        if not key:
            return
        try:
            if self.stack.currentWidget() is self.editor_pane and self._current_is_dirty():
                # Editor-Inhalt (Plain + Rich-HTML) in das Dokument übernehmen
                self._sync_editor_rich_meta()
        except Exception:
            pass
        entry = self._doc_cache.get(key)
        sig = entry[0] if entry else self._doc_cache_sig(doc.path)
        if sig is None:
            return
        self._doc_cache[key] = (sig, doc)

    def _save_session(self):
        self._capture_current_tab_view_state()
        paths = self._session_paths()
        active = str(Path(self.doc.path)) if self.doc and self.doc.path else None
        page = self.pdf_view.page_index if self.pdf_view.pdf_path else 0
        scale = self.pdf_view.scale if self.pdf_view.pdf_path else 1.5
        scroll_y = 0
        try:
            if self.pdf_view.pdf_path:
                bar = self.pdf_view.scroll.verticalScrollBar()
                scroll_y = int(bar.value()) if bar is not None else 0
            elif self.stack.currentWidget() is self.editor_pane:
                bar = self.editor.verticalScrollBar()
                scroll_y = int(bar.value()) if bar is not None else 0
        except Exception:
            scroll_y = 0
        sec_path = ""
        sec_kind = ""
        if getattr(self, "_secondary_path", None) and Path(self._secondary_path).is_file():
            sec_path = str(Path(self._secondary_path))
            sec_kind = str(getattr(self, "_secondary_kind", "") or "")
            if not sec_kind:
                sec_kind = "pdf" if Path(sec_path).suffix.lower() == ".pdf" else "editor"
        theme = ""
        try:
            theme = load_theme_mode()
        except Exception:
            theme = ""
        tab_labels = {}
        try:
            tab_labels = dict(self.sidebar.document_labels())
        except Exception:
            tab_labels = {}
        panels = {"thumbs": True, "ann": True, "bookmark": True}
        try:
            panels = dict(self.sidebar.panel_visibility())
        except Exception:
            panels = {"thumbs": True, "ann": True, "bookmark": True}
        search = {"case": False, "whole": False, "regex": False}
        try:
            search = dict(self.sidebar.search_options())
        except Exception:
            search = {"case": False, "whole": False, "regex": False}
        ann_tool = ""
        try:
            ann_tool = self.pdf_view.current_tool_id()
        except Exception:
            ann_tool = ""
        ann_opacity = 0.0
        ann_stroke_width = 0.0
        ann_fill_color = ""
        ann_stroke_color = ""
        try:
            ann_opacity = float(getattr(self.pdf_view, "_default_opacity", 0.0) or 0.0)
        except Exception:
            ann_opacity = 0.0
        try:
            ann_stroke_width = float(
                getattr(self.pdf_view, "_default_stroke_width", 0.0) or 0.0
            )
        except Exception:
            ann_stroke_width = 0.0
        try:
            ann_fill_color = str(
                getattr(self.pdf_view, "_default_fill_color", "") or ""
            ).strip()
        except Exception:
            ann_fill_color = ""
        try:
            ann_stroke_color = str(getattr(self.pdf_view, "_pen_color", "") or "").strip()
        except Exception:
            ann_stroke_color = ""
        ann_layer_types = None
        try:
            ann_layer_types = dict(get_ann_layer_types_visible())
        except Exception:
            ann_layer_types = None
        state = session_mod.build_session(
            paths,
            active_path=active,
            page=page,
            scale=scale,
            scroll_y=scroll_y,
            tab_states=getattr(self, "_tab_view_state", None),
            restore=True,
            secondary_path=sec_path or None,
            secondary_kind=sec_kind or None,
            sync_scroll=get_editor_doc_split_sync_scroll(),
            splitter_sizes=self._main_splitter_sizes() or None,
            theme=theme or None,
            tab_labels=tab_labels or None,
            panels=panels,
            search=search,
            ann_tool=ann_tool,
            ann_opacity=ann_opacity,
            ann_stroke_width=ann_stroke_width,
            ann_fill_color=ann_fill_color or None,
            ann_stroke_color=ann_stroke_color or None,
            ann_layer_types=ann_layer_types,
        )
        session_mod.save_session(state)

    def _restore_session(self, force: bool = False):
        """Session-Tabs wiederherstellen. ``force=True``: Willkommen „Weiterarbeiten“ — 1.0.7."""
        import os

        if os.environ.get("ILD_NO_SESSION") == "1" or os.environ.get("ILD_SMOKE_QT"):
            return
        if not force and not get_restore_session_on_start():
            return
        # CLI-Argument hat Vorrang (app.py öffnet danach) — nur wenn noch kein Doc
        if self.doc and self.doc.path:
            return
        state = session_mod.load_session()
        if not force and not state.restore:
            return
        if not state.tabs:
            return
        # Theme aus Session wiederherstellen (0.9.4); system — 1.4.0
        theme = str(getattr(state, "theme", "") or "").strip().lower()
        if theme in ("dark", "light", "system"):
            try:
                apply_theme(mode=theme)  # type: ignore[arg-type]
                self._sync_theme_menu()
            except Exception:
                pass
        # Alle Tabs in Sidebar laden; View-State je Tab vorbereiten (0.9.1)
        for tab in state.tabs:
            if Path(tab.path).is_file():
                self.sidebar.add_document(tab.path)
                # Anzeige-Label (≠ Dateiname) — 0.9.4
                lbl = str(getattr(tab, "label", "") or "").strip()
                if lbl:
                    try:
                        self.sidebar.set_document_label(tab.path, lbl)
                    except Exception:
                        pass
                key = self._path_key(tab.path)
                if key:
                    self._tab_view_state[key] = {
                        "page": max(0, int(getattr(tab, "page", 0) or 0)),
                        "scale": float(getattr(tab, "scale", 1.5) or 1.5),
                        "scroll_y": max(0, int(getattr(tab, "scroll_y", 0) or 0)),
                    }
        # Aktiver Tab-Index aus Session (0.9.4 explizit)
        active_idx = int(getattr(state, "active", 0) or 0)
        if active_idx < 0 or active_idx >= len(state.tabs):
            active_idx = len(state.tabs) - 1
        active = state.tabs[active_idx]
        if not Path(active.path).is_file():
            return
        self.open_path(active.path)
        # open_path stellt Last-Page/Scroll aus _tab_view_state wieder her
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
        # Sidebar/Viewer-Splitter aus Session (0.9.3)
        sizes = list(getattr(state, "splitter_sizes", None) or [])
        if sizes:

            def _restore_split(sz=sizes) -> None:
                self._apply_main_splitter_sizes(sz)

            QTimer.singleShot(0, _restore_split)
            QTimer.singleShot(120, _restore_split)
        # Panel-Sichtbarkeit Thumb/Ann/Bookmark (0.9.5)
        try:
            self.sidebar.set_panel_visibility(
                thumbs=bool(getattr(state, "panel_thumbs", True)),
                ann=bool(getattr(state, "panel_ann", True)),
                bookmark=bool(getattr(state, "panel_bookmark", True)),
            )
            self._sync_panel_visibility_menu()
        except Exception:
            pass
        # PDF-Suche Toggles Aa / Wort / Regex (0.9.6)
        try:
            self.sidebar.set_search_options(
                case=bool(getattr(state, "search_case", False)),
                whole=bool(getattr(state, "search_whole", False)),
                regex=bool(getattr(state, "search_regex", False)),
            )
            if hasattr(self.pdf_view, "set_search_options"):
                self.pdf_view.set_search_options(
                    case_sensitive=bool(getattr(state, "search_case", False)),
                    whole_word=bool(getattr(state, "search_whole", False)),
                    regex=bool(getattr(state, "search_regex", False)),
                )
        except Exception:
            pass
        # Zuletzt genutztes Ann.-Werkzeug (0.9.7)
        try:
            tool_id = str(getattr(state, "ann_tool", "") or "")
            if hasattr(self.pdf_view, "set_tool_from_id"):
                self.pdf_view.set_tool_from_id(tool_id)
        except Exception:
            pass
        # Letzte Ann.-Opacity / Stroke-Width (0.9.8)
        try:
            op = float(getattr(state, "ann_opacity", 0.0) or 0.0)
            if op > 0 and hasattr(self.pdf_view, "restore_default_opacity"):
                self.pdf_view.restore_default_opacity(op)
            elif op > 0:
                from instantlensdoc.core.app_settings import set_ann_default_opacity

                set_ann_default_opacity(op)
                self.pdf_view._default_opacity = max(0.05, min(1.0, op))
                if hasattr(self.pdf_view, "_sync_opacity_controls"):
                    self.pdf_view._sync_opacity_controls(self.pdf_view._default_opacity)
        except Exception:
            pass
        try:
            sw = float(getattr(state, "ann_stroke_width", 0.0) or 0.0)
            if sw > 0 and hasattr(self.pdf_view, "restore_default_stroke_width"):
                self.pdf_view.restore_default_stroke_width(sw)
            elif sw > 0:
                from instantlensdoc.core.app_settings import set_ann_default_stroke_width

                set_ann_default_stroke_width(sw)
                self.pdf_view._default_stroke_width = max(1.0, min(12.0, sw))
                if hasattr(self.pdf_view, "_sync_stroke_controls"):
                    self.pdf_view._sync_stroke_controls(self.pdf_view._default_stroke_width)
        except Exception:
            pass
        # Letzte Ann.-Fill-/Stroke-Farbe (0.9.9)
        try:
            fc = str(getattr(state, "ann_fill_color", "") or "").strip()
            if fc and hasattr(self.pdf_view, "restore_default_fill_color"):
                self.pdf_view.restore_default_fill_color(fc)
            elif fc:
                from instantlensdoc.core.app_settings import set_ann_default_fill_color

                set_ann_default_fill_color(fc)
                self.pdf_view._default_fill_color = fc
        except Exception:
            pass
        try:
            sc = str(getattr(state, "ann_stroke_color", "") or "").strip()
            if sc and hasattr(self.pdf_view, "restore_default_stroke_color"):
                self.pdf_view.restore_default_stroke_color(sc)
            elif sc:
                from instantlensdoc.core.app_settings import set_ann_pen_color

                set_ann_pen_color(sc)
                self.pdf_view._pen_color = sc
                if hasattr(self.pdf_view, "_style_color_btn") and hasattr(
                    self.pdf_view, "btn_pen_color"
                ):
                    self.pdf_view._style_color_btn(self.pdf_view.btn_pen_color, sc)
        except Exception:
            pass
        # Annotation-Layer Typ-Toggles Session — 1.8.1
        try:
            layer = getattr(state, "ann_layer_types", None) or {}
            if isinstance(layer, dict) and layer:
                from instantlensdoc.core.app_settings import set_ann_layer_types_visible

                set_ann_layer_types_visible(layer)
                if hasattr(self.pdf_view, "set_annotation_types_visible"):
                    self.pdf_view.set_annotation_types_visible(layer)
                self._sync_ann_type_actions()
        except Exception:
            pass
        self._set_status(f"Session wiederhergestellt ({len(state.tabs)} Tab(s))")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Ablaufwarnung-Banner: Fokus-Ring; Enter→Aktivierung; Esc schließt — 1.0.9
        from PySide6.QtWidgets import QStyle

        from instantlensdoc.core.i18n import tr as _tr_ban

        self.expiry_warn_banner = QWidget()
        self.expiry_warn_banner.setObjectName("expiryWarnBanner")
        self.expiry_warn_banner.setAccessibleName(_tr_ban("expiry_banner_accessible"))
        self.expiry_warn_banner.setFocusPolicy(Qt.StrongFocus)
        self.expiry_warn_banner.setAttribute(Qt.WA_StyledBackground, True)
        self._expiry_banner_kind = "warn"
        self._apply_expiry_banner_style("warn")
        ban_lay = QHBoxLayout(self.expiry_warn_banner)
        ban_lay.setContentsMargins(10, 6, 8, 6)
        ban_lay.setSpacing(8)
        self.expiry_warn_icon = QLabel()
        self.expiry_warn_icon.setFixedSize(22, 22)
        self.expiry_warn_icon.setAlignment(Qt.AlignCenter)
        try:
            icon = self.style().standardIcon(QStyle.SP_MessageBoxWarning)
            self.expiry_warn_icon.setPixmap(icon.pixmap(20, 20))
        except Exception:
            self.expiry_warn_icon.setText("⚠")
        self.expiry_warn_icon.setToolTip(_tr_ban("expiry_warn_tooltip"))
        self.expiry_warn_icon.setAccessibleName(_tr_ban("expiry_banner_icon_accessible"))
        ban_lay.addWidget(self.expiry_warn_icon)
        self.expiry_warn_label = QLabel()
        self.expiry_warn_label.setWordWrap(True)
        self.expiry_warn_label.setCursor(Qt.PointingHandCursor)
        self.expiry_warn_label.setToolTip(_tr_ban("expiry_warn_tooltip"))
        self.expiry_warn_label.setAccessibleName(_tr_ban("expiry_banner_accessible"))
        self.expiry_warn_label.mousePressEvent = (  # type: ignore[method-assign]
            lambda e: self._on_expiry_warn_clicked(e)
        )
        ban_lay.addWidget(self.expiry_warn_label, 1)
        self.btn_expiry_warn_dismiss = QPushButton(_tr_ban("expiry_dismiss_label"))
        self.btn_expiry_warn_dismiss.setToolTip(_tr_ban("expiry_dismiss_tooltip"))
        self.btn_expiry_warn_dismiss.setAccessibleName(
            _tr_ban("expiry_dismiss_accessible")
        )
        self.btn_expiry_warn_dismiss.clicked.connect(self._dismiss_expiry_warning)
        ban_lay.addWidget(self.btn_expiry_warn_dismiss)
        self.btn_expiry_warn_close = QPushButton("×")
        self.btn_expiry_warn_close.setFixedWidth(28)
        self.btn_expiry_warn_close.setToolTip(_tr_ban("expiry_close_tooltip"))
        self.btn_expiry_warn_close.setAccessibleName(
            _tr_ban("expiry_close_accessible")
        )
        self.btn_expiry_warn_close.clicked.connect(self._dismiss_expiry_warning)
        ban_lay.addWidget(self.btn_expiry_warn_close)
        self.expiry_warn_banner.installEventFilter(self)
        self.expiry_warn_banner.setVisible(False)
        outer.addWidget(self.expiry_warn_banner)

        # Readonly-Vorschau-Banner (Merge-Thumbnail) — 1.1.5
        self.preview_readonly_banner = QWidget()
        self.preview_readonly_banner.setObjectName("previewReadonlyBanner")
        self.preview_readonly_banner.setAccessibleName("Vorschau — schreibgeschützt")
        self.preview_readonly_banner.setAttribute(Qt.WA_StyledBackground, True)
        self.preview_readonly_banner.setStyleSheet(
            "#previewReadonlyBanner {"
            " background: #E8F0FE; color: #1A3A6B; border-bottom: 1px solid #A8C0E8;"
            "}"
        )
        prev_lay = QHBoxLayout(self.preview_readonly_banner)
        prev_lay.setContentsMargins(10, 6, 8, 6)
        prev_lay.setSpacing(10)
        self.preview_readonly_label = QLabel("Vorschau")
        self.preview_readonly_label.setToolTip(
            "Datei ist als Readonly-Vorschau geöffnet — Speichern deaktiviert — 1.1.5"
        )
        self.preview_readonly_label.setStyleSheet("font-weight: 600;")
        prev_lay.addWidget(self.preview_readonly_label)
        prev_hint = QLabel("Schreibgeschützt — Änderungen werden nicht gespeichert.")
        prev_hint.setWordWrap(True)
        self.preview_readonly_hint = prev_hint
        prev_lay.addWidget(prev_hint, 1)
        self.btn_preview_open_edit = QPushButton("Zum Bearbeiten öffnen")
        self.btn_preview_open_edit.setToolTip(
            "Dieselbe Datei als normales, bearbeitbares Dokument öffnen — 1.1.5"
        )
        self.btn_preview_open_edit.setAccessibleName("Zum Bearbeiten öffnen")
        self.btn_preview_open_edit.clicked.connect(self._open_preview_for_edit)
        prev_lay.addWidget(self.btn_preview_open_edit)
        self.preview_readonly_banner.setVisible(False)
        outer.addWidget(self.preview_readonly_banner)

        # Globale Lesezeichen-Leiste (ildfav-v1) — Drag-Reorder / fehlend grau — 1.7.1
        self.favorites_bar = QFrame()
        self.favorites_bar.setObjectName("globalFavoritesBar")
        self.favorites_bar.setAttribute(Qt.WA_StyledBackground, True)
        self.favorites_bar.setStyleSheet(
            "#globalFavoritesBar {"
            " background: #F3F5F8; border-bottom: 1px solid #C8D0DA;"
            "}"
        )
        fav_outer = QHBoxLayout(self.favorites_bar)
        fav_outer.setContentsMargins(8, 2, 8, 2)
        fav_outer.setSpacing(6)
        self.favorites_bar_label = QLabel("★ Favoriten")
        self.favorites_bar_label.setStyleSheet("font-weight: 600; color: #334;")
        self.favorites_bar_label.setToolTip(
            "Globale Dokument-Favoriten (ildfav-v1) — Drag-Reorder, Export/Import — 1.7.1"
        )
        fav_outer.addWidget(self.favorites_bar_label)
        # Kompatibilität: leeres Layout (ältere Smoke-Tests)
        self.favorites_bar_inner = QWidget()
        self.favorites_bar_layout = QHBoxLayout(self.favorites_bar_inner)
        self.favorites_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.favorites_list = GlobalFavoritesList(self.favorites_bar)
        self.favorites_list.itemClicked.connect(self._on_global_fav_item_clicked)
        self.favorites_list.itemDoubleClicked.connect(
            self._on_global_fav_item_double_clicked
        )
        self.favorites_list.favorites_reordered.connect(self._on_global_favorites_reordered)
        self.favorites_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.favorites_list.customContextMenuRequested.connect(
            self._on_global_fav_list_context
        )
        fav_outer.addWidget(self.favorites_list, 1)
        self.btn_fav_add = QToolButton()
        self.btn_fav_add.setText("+")
        self.btn_fav_add.setToolTip(
            "Aktuelle PDF-Seite zur globalen Favoriten-Leiste hinzufügen — 1.7.0"
        )
        self.btn_fav_add.clicked.connect(self._add_current_to_global_favorites)
        fav_outer.addWidget(self.btn_fav_add)
        self.btn_fav_export = QToolButton()
        self.btn_fav_export.setText("⇓")
        self.btn_fav_export.setToolTip(
            "Globale Favoriten als ildfav-v1 JSON exportieren — 1.7.1"
        )
        self.btn_fav_export.clicked.connect(self._export_global_favorites_json)
        fav_outer.addWidget(self.btn_fav_export)
        self.btn_fav_import = QToolButton()
        self.btn_fav_import.setText("⇑")
        self.btn_fav_import.setToolTip(
            "Globale Favoriten aus ildfav-v1 JSON importieren — 1.7.1"
        )
        self.btn_fav_import.clicked.connect(self._import_global_favorites_json)
        fav_outer.addWidget(self.btn_fav_import)
        self.favorites_bar.setVisible(get_favorites_bar_visible())
        outer.addWidget(self.favorites_bar)
        QTimer.singleShot(0, self._refresh_favorites_bar)

        # Ribbon-Chrome (partiell) + Dokument-Tabs — 2.6.19
        from instantlensdoc.core.app_settings import (
            get_doc_tabs_visible,
            get_ribbon_visible,
        )

        self.ribbon_bar = RibbonBar(self)
        self.ribbon_bar.action_triggered.connect(self._on_ribbon_action)
        outer.addWidget(self.ribbon_bar)
        self.doc_tab_bar = DocumentTabBar(self)
        self.doc_tab_bar.tab_activated.connect(self._on_doc_tab_activated)
        self.doc_tab_bar.tab_close_requested.connect(self.close_tab_path)
        self.doc_tab_bar.tab_detach_requested.connect(self._detach_document_window)
        self.doc_tab_bar.setVisible(get_doc_tabs_visible())
        outer.addWidget(self.doc_tab_bar)
        self._detached_windows: list = []

        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(root, 1)

        splitter = QSplitter(Qt.Horizontal)
        self.main_splitter = splitter  # Sidebar / Viewer — Größen in Session (0.9.3)
        self.sidebar = Sidebar()
        self.sidebar.search_requested.connect(self._on_search)
        self.sidebar.search_next_requested.connect(self._on_search_next)
        self.sidebar.search_prev_requested.connect(self._on_search_prev)
        self.sidebar.search_export_requested.connect(self._on_search_export)
        self.sidebar.search_annotate_requested.connect(self._on_search_annotate_hits)
        self.sidebar.file_activated.connect(self.open_path)
        self.sidebar.document_close_requested.connect(self.close_tab_path)
        self.sidebar.document_close_others_requested.connect(self.close_other_tabs_keeping)
        self.sidebar.document_close_all_requested.connect(self.close_all_tabs)
        self.sidebar.document_close_left_requested.connect(self.close_tabs_left_of)
        self.sidebar.document_close_right_requested.connect(self.close_tabs_right_of)
        self.sidebar.document_pin_toggled.connect(self._on_document_pin_toggled)
        self.sidebar.document_rename_requested.connect(self._on_document_renamed)
        self.sidebar.document_label_reset_requested.connect(self._on_document_label_reset)
        self.sidebar.recent_activated.connect(self.open_path)
        self.sidebar.recent_remove_requested.connect(self._remove_recent_path)
        if hasattr(self.sidebar, "recent_clear_requested"):
            self.sidebar.recent_clear_requested.connect(self._clear_recent)
        if hasattr(self.sidebar, "recent_prune_requested"):
            self.sidebar.recent_prune_requested.connect(self._prune_missing_recent)
        # Tab-Leiste spiegelt die Dokumentliste automatisch: jede Änderung am Listen-
        # Modell (Tab entfernt/hinzugefügt/geleert/umsortiert) synchronisiert die
        # QTabBar — auch wenn ein Close-Pfad vorher abbricht — 2.6.54
        try:
            files_model = self.sidebar.files.model()
            files_model.rowsInserted.connect(self._schedule_doc_tab_bar_sync)
            files_model.rowsRemoved.connect(self._schedule_doc_tab_bar_sync)
            files_model.rowsMoved.connect(self._schedule_doc_tab_bar_sync)
            files_model.modelReset.connect(self._schedule_doc_tab_bar_sync)
        except Exception:
            pass
        self.sidebar.mark_activated.connect(self._on_mark_activated)
        self.sidebar.annotation_activated.connect(self._on_annotation_activated)
        self.sidebar.outline_activated.connect(self._on_outline_jump)
        if hasattr(self.sidebar, "outline_line_activated"):
            self.sidebar.outline_line_activated.connect(self._on_outline_line_jump)
        self.sidebar.outline_add_requested.connect(self._outline_add)
        self.sidebar.outline_delete_requested.connect(self._outline_delete)
        if hasattr(self.sidebar, "outline_refresh_requested"):
            self.sidebar.outline_refresh_requested.connect(self._refresh_document_outline)
        self.sidebar.form_field_activated.connect(self._on_form_field_jump)
        self.sidebar.form_fields_save_requested.connect(self._on_form_fields_save)
        self.sidebar.form_fields_export_csv_requested.connect(
            self._on_form_fields_export_csv
        )
        self.sidebar.redaction_activated.connect(self._on_redaction_activated)
        self.sidebar.redaction_delete_requested.connect(self._on_redaction_delete)
        self.sidebar.link_activated.connect(self._on_link_activated)
        self.sidebar.link_edit_requested.connect(self._on_link_edit)
        self.sidebar.link_delete_requested.connect(self._on_link_delete)
        if hasattr(self.sidebar, "links_export_requested"):
            self.sidebar.links_export_requested.connect(self._export_links_txt)
        self.sidebar.thumbs_viewport_changed.connect(self._on_thumbs_viewport_changed)
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
        self.sidebar.page_flip_requested.connect(self._on_thumb_flip)
        self.sidebar.page_duplicate_requested.connect(self._on_thumb_duplicate)
        self.sidebar.page_delete_requested.connect(self._on_thumb_delete)
        self.sidebar.pages_batch_duplicate_requested.connect(self._on_thumbs_batch_duplicate)
        self.sidebar.pages_batch_delete_requested.connect(self._on_thumbs_batch_delete)
        self.sidebar.pages_batch_rotate_requested.connect(self._on_thumbs_batch_rotate)
        self.sidebar.pages_batch_flip_requested.connect(self._on_thumbs_batch_flip)
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
        try:
            from instantlensdoc.ui.styles import StylePane

            self.style_pane = StylePane(self, on_apply=self._apply_paragraph_style)
            self.style_dock = QDockWidget("Formatvorlagen", self)
            self.style_dock.setObjectName("ildStyleDock")
            self.style_dock.setWidget(self.style_pane)
            self.style_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
            self.addDockWidget(Qt.RightDockWidgetArea, self.style_dock)
            self.style_dock.hide()
            self.style_pane.style_chosen.connect(self._apply_paragraph_style)
        except Exception:
            self.style_pane = None
            self.style_dock = None
        # Word-Suite / Text-Toolbar (Auswahl…Markierungen) — 2.6.44
        if hasattr(self.editor_pane, "tool_action"):
            self.editor_pane.tool_action.connect(self._on_editor_toolbar_action)
        self.pdf_view = PdfViewer()
        self.pdf_view.status.connect(self._on_pdf_view_status)
        self.pdf_view.ocr_region_finished.connect(self._on_ocr_region_finished)
        self.pdf_view.annotations_changed.connect(self._refresh_pdf_marks)
        self.pdf_view.annotations_changed.connect(self._refresh_undo_hint)
        self.pdf_view.undo_state_changed.connect(self._on_pdf_undo_state)
        # Toolbar-Undo/Redo: Layer-Alle-ein/aus · Tag-Rename-Filter — 1.8.3/1.8.4
        self._ann_layer_undo: list[dict[str, bool]] = []
        self._ann_layer_redo: list[dict[str, bool]] = []
        _pdf_undo = self.pdf_view.undo_annotation

        def _undo_annotation_with_tag_revert() -> bool:
            if self._undo_ann_type_layers():
                return True
            ok = bool(_pdf_undo())
            if ok:
                # Sticky 0-Treffer auch bei Ann.-Undo leeren — 1.1.9
                self._clear_ann_zero_sticky_status()
                self._revert_tag_filter_after_rename_undo()
                self._refresh_undo_hint()
            return ok

        self.pdf_view.undo_annotation = _undo_annotation_with_tag_revert  # type: ignore[method-assign]
        _pdf_redo = self.pdf_view.redo_annotation

        def _redo_annotation_with_sticky_clear() -> bool:
            if self._redo_ann_type_layers():
                return True
            ok = bool(_pdf_redo())
            if ok:
                # Sticky 0-Treffer auch bei Ann.-Redo leeren — 1.1.9
                self._clear_ann_zero_sticky_status()
                self._refresh_undo_hint()
            return ok

        self.pdf_view.redo_annotation = _redo_annotation_with_sticky_clear  # type: ignore[method-assign]
        self.pdf_view.page_favorites_changed.connect(self._refresh_page_favorites)
        self.pdf_view.page_changed.connect(self._on_pdf_page_changed)
        # PageUp/PageDown auch wenn die Thumbnail-Liste den Fokus hat — 2.6.54
        self._sc_pdf_page_down = QShortcut(QKeySequence(Qt.Key_PageDown), self)
        self._sc_pdf_page_down.setContext(Qt.WindowShortcut)
        self._sc_pdf_page_down.activated.connect(lambda: self._pdf_page_shortcut(1))
        self._sc_pdf_page_down.setEnabled(False)
        self._sc_pdf_page_up = QShortcut(QKeySequence(Qt.Key_PageUp), self)
        self._sc_pdf_page_up.setContext(Qt.WindowShortcut)
        self._sc_pdf_page_up.activated.connect(lambda: self._pdf_page_shortcut(-1))
        self._sc_pdf_page_up.setEnabled(False)
        self.pdf_view.zoom_changed.connect(self._on_pdf_zoom_changed)
        self.pdf_view.document_changed.connect(self._on_pdf_document_changed)
        self.pdf_view.grayscale_changed.connect(self._sync_grayscale_action)
        self.pdf_view.night_mode_changed.connect(self._sync_night_action)
        self.pdf_view.two_page_spread_changed.connect(self._sync_spread_action)
        self.pdf_view.continuous_scroll_changed.connect(self._sync_continuous_action)
        self.pdf_view.book_layout_changed.connect(self._sync_book_layout_action)
        self.pdf_view.page_by_page_changed.connect(self._sync_page_by_page_action)
        self.pdf_view.annotations_layer_changed.connect(self._sync_ann_layer_action)
        self.pdf_view.annotations_lock_changed.connect(self._sync_ann_lock_action)
        self.pdf_view.page_boxes_changed.connect(self._sync_page_boxes_action)
        self.pdf_view.page_number_overlay_changed.connect(
            self._sync_page_number_overlay_action
        )
        self.pdf_view.printer_marks_changed.connect(self._sync_printer_marks_action)
        self.image_label = QLabel(alignment=Qt.AlignCenter)
        self.image_label.setText("Bildvorschau")
        self.welcome_page = WelcomePage()
        self.welcome_page.open_requested.connect(self.open_dialog)
        self.welcome_page.new_text_requested.connect(lambda: self.new_doc("empty"))
        if hasattr(self.welcome_page, "scan_requested"):
            self.welcome_page.scan_requested.connect(self._run_scan_import)
        self.welcome_page.recent_activated.connect(self.open_path)
        self.welcome_page.recent_remove_requested.connect(self._remove_recent_path)
        self.welcome_page.clear_recent_requested.connect(self._clear_recent)
        self.welcome_page.files_dropped.connect(self._welcome_files_dropped)
        self.welcome_page.continue_session_requested.connect(self._continue_last_session)
        self.dtp_pane = DtpPane(self, doc=getattr(self, "dtp_doc", None))
        self.dtp_pane.statusMessage.connect(self._set_status)
        self.stack.addWidget(self.editor_pane)  # 0
        self.stack.addWidget(self.pdf_view)  # 1
        self.stack.addWidget(self.image_label)  # 2
        self.stack.addWidget(self.welcome_page)  # 3 — Startseite ohne Tabs (1.0.0)
        self.stack.addWidget(self.dtp_pane)  # 4 — DTP-Layout-Modus 2.6.54
        self.stack.currentChanged.connect(lambda *_: self._apply_doc_split_sync_scroll())
        self.stack.currentChanged.connect(lambda *_: self._update_doc_status())
        self.stack.currentChanged.connect(lambda *_: self._sync_editor_toolbar_for_stack())
        self.stack.currentChanged.connect(lambda *_: self._sync_pdf_page_shortcuts())
        self.stack.currentChanged.connect(lambda *_: self._sync_menu_enablement())
        self.stack.currentChanged.connect(lambda *_: self._sync_undo_redo_ui())
        # Beim Start ohne Session: Willkommen zeigen (nach Session-Restore ggf. überschrieben)
        self.stack.setCurrentWidget(self.welcome_page)
        self._sync_editor_toolbar_for_stack()
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
        # Zweit-Panel: nur Anzeige (lokal gesperrt, Setting unangetastet)
        try:
            self.secondary_pdf._persist_ann_lock = False
            self.secondary_pdf.set_annotations_locked(True, persist=False)
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
        splitter.splitterMoved.connect(self._on_main_splitter_moved)
        root.addWidget(splitter)

        sb = QStatusBar()
        self.setStatusBar(sb)
        # Viele permanente Labels summierten sich auf ~1300 px Mindestbreite und
        # zwangen das Fenster breiter als kleine Monitore — 2.6.52
        from PySide6.QtWidgets import QSizePolicy as _QSizePolicy

        sb.setSizePolicy(_QSizePolicy.Ignored, _QSizePolicy.Fixed)
        # Status-Klick: Outlines-Export-Zielordner öffnen — 1.3.4
        sb.mousePressEvent = self._on_status_bar_clicked  # type: ignore[method-assign]
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
        # Sync-Scroll Status-Widget (PDF↔PDF) — AccessibleName live an/aus — 2.4.5
        self.sync_scroll_status_label = QLabel("")
        self.sync_scroll_status_label.setObjectName("syncScrollStatus")
        self.sync_scroll_status_label.setStyleSheet(
            "QLabel#syncScrollStatus { color: #555; padding-right: 8px; font-size: 11px; }"
        )
        self.sync_scroll_status_label.setToolTip(
            "Sync-Scroll: Zustand aus — Klick toggled · Shortcut Ctrl+Alt+\\ — 2.4.5"
        )
        self.sync_scroll_status_label.setAccessibleName("Sync-Scroll Status: aus")
        self.sync_scroll_status_label.setAccessibleDescription(
            "Sync-Scroll Status-Widget PDF↔PDF. AccessibleName live an/aus bei Toggle. "
            "Klick toggled. Shortcut Ctrl+Alt+Backslash. Toggle mit Announcement — 2.4.5"
        )
        self._last_thumb_prune_status = ""
        self._thumb_prune_status_active = False
        self.sync_scroll_status_label.setCursor(Qt.PointingHandCursor)
        self.sync_scroll_status_label.mousePressEvent = (  # type: ignore[method-assign]
            lambda e: self._on_sync_scroll_status_clicked(e)
        )
        self.sync_scroll_status_label.setVisible(False)
        sb.addPermanentWidget(self.sync_scroll_status_label)
        # Thumb-Cache Hit/Miss optional Debug — 2.4.1
        self.thumb_cache_debug_label = QLabel("")
        self.thumb_cache_debug_label.setObjectName("thumbCacheDebug")
        self.thumb_cache_debug_label.setStyleSheet(
            "QLabel#thumbCacheDebug { color: #777; padding-right: 8px; font-size: 11px; }"
        )
        self.thumb_cache_debug_label.setToolTip(
            "Thumbnail-Cache Hit/Miss (Debug, Einstellungen) — 2.4.1"
        )
        self.thumb_cache_debug_label.setVisible(False)
        sb.addPermanentWidget(self.thumb_cache_debug_label)
        self.undo_hint_label = QLabel("Ctrl+Z · Letzte Aktion rückgängig")
        self.undo_hint_label.setObjectName("undoHint")
        self.undo_hint_label.setStyleSheet(
            "QLabel#undoHint { color: #777; padding-right: 8px; font-size: 11px; }"
        )
        self.undo_hint_label.setToolTip(
            "Rückgängig: Editor · PDF-Annotationen (benannt, z. B. Tag umbenennen) · Seiten (Ctrl+Z)"
        )
        sb.addPermanentWidget(self.undo_hint_label)
        # Ann. 0-Treffer: dauerhaft bis nächste Ann.-Aktion — 1.1.7
        self.ann_zero_status_label = QLabel("")
        self.ann_zero_status_label.setObjectName("annZeroStatus")
        self.ann_zero_status_label.setStyleSheet(
            "QLabel#annZeroStatus { color: #a60; padding-right: 8px; font-size: 11px; }"
        )
        self.ann_zero_status_label.setToolTip(
            "0 gefilterte Annotationen — bleibt bis zur nächsten Annotations-Aktion — 1.1.7"
        )
        self.ann_zero_status_label.setVisible(False)
        sb.addPermanentWidget(self.ann_zero_status_label)
        # Theme: Indicator; Klick → Schnellmenü; Ctrl+Shift+T Zyklus — 1.4.4
        self.theme_status_label = QLabel(theme_status_text())
        self.theme_status_label.setObjectName("themeStatus")
        self.theme_status_label.setStyleSheet(
            "QLabel#themeStatus { color: #666; padding-right: 8px; font-size: 11px; }"
        )
        self.theme_status_label.setCursor(Qt.PointingHandCursor)
        self.theme_status_label.setToolTip(
            "Klick: Theme-Schnellmenü · Ctrl+Shift+T: "
            "Theme zyklisch System → Hell → Dunkel → System — 1.4.5"
        )
        self.theme_status_label.mousePressEvent = (  # type: ignore[method-assign]
            self._on_theme_status_clicked
        )
        sb.addPermanentWidget(self.theme_status_label)
        self.version_label = QLabel(f"v{__version__}")
        self.version_label.setStyleSheet("color: #666; padding-right: 8px;")
        sb.addPermanentWidget(self.version_label)
        self.license_label = QLabel()
        sb.addPermanentWidget(self.license_label)
        self._update_doc_status()

    def _ensure_devices_menu(self, mb=None):
        """Menü Geräte (Scanner/Drucker/Erkennen) — idempotent, früh + nach PDF — 2.6.51."""
        from PySide6.QtGui import QAction, QKeySequence

        if mb is None:
            mb = self.menuBar()
        existing = None
        try:
            existing = self.findChild(QMenu, "menuDevices")
        except Exception:
            existing = None
        if existing is None:
            try:
                for act in mb.actions():
                    menu = act.menu() if hasattr(act, "menu") else None
                    if menu is not None and menu.objectName() == "menuDevices":
                        existing = menu
                        break
            except Exception:
                existing = None
        if existing is not None:
            m_devices = existing
            try:
                if any(
                    a.objectName() == "actDevicesScanner" for a in m_devices.actions()
                ):
                    self._bind_devices_menu_live(m_devices)
                    return m_devices
            except Exception:
                pass
        else:
            m_devices = QMenu("&Geräte", self)
            m_devices.setObjectName("menuDevices")
            insert_before = None
            try:
                for act in mb.actions():
                    menu = act.menu() if hasattr(act, "menu") else None
                    title = ""
                    try:
                        title = (menu.title() if menu is not None else act.text()) or ""
                    except Exception:
                        title = act.text() or ""
                    if "PDF" in title.replace("&", ""):
                        insert_before = act
                        break
            except Exception:
                insert_before = None
            if insert_before is not None:
                mb.insertMenu(insert_before, m_devices)
            else:
                mb.addMenu(m_devices)
        m_devices.setToolTip(
            "Scanner, Drucker und lokale/Netzwerk-Geräteerkennung — 2.6.51"
        )
        try:
            m_devices.clear()
        except Exception:
            pass
        act_dev_scan = QAction("Scannen…", self)
        act_dev_scan.setObjectName("actDevicesScanner")
        act_dev_scan.setShortcuts(
            [QKeySequence("Ctrl+Shift+S"), QKeySequence("Ctrl+Alt+Shift+I")]
        )
        act_dev_scan.setToolTip(
            "Scan-Dialog: Gerät, DPI/Farbe, Scannen — Ergebnis ins Dokument "
            "(Ctrl+Shift+S) — 2.6.54"
        )
        act_dev_scan.triggered.connect(self._run_scan_import)
        m_devices.addAction(act_dev_scan)
        # Alias-Text für bestehende Tests / Hilfe („Scannen / Import…“)
        act_dev_scan.setStatusTip("Scannen / Import…")
        act_dev_printers = QAction("Drucker…", self)
        act_dev_printers.setObjectName("actDevicesPrinters")
        act_dev_printers.setToolTip(
            "Lokale und Netzwerk-Drucker auflisten (Qt/Winspool/Get-Printer) — 2.6.51"
        )
        act_dev_printers.triggered.connect(
            lambda: self._show_devices_dialog(filter_kind="printer")
        )
        m_devices.addAction(act_dev_printers)
        act_dev_all = QAction("Geräte erkennen…", self)
        act_dev_all.setObjectName("actDevicesDiscover")
        act_dev_all.setToolTip(
            "Drucker & Scanner neu suchen (WIA/PnP/TWAIN/NAPS2/Get-Printer) — 2.6.51"
        )
        act_dev_all.triggered.connect(self._show_devices_dialog)
        m_devices.addAction(act_dev_all)
        m_devices.addSeparator()
        act_dev_refresh = QAction("Aktualisieren / Neu suchen", self)
        act_dev_refresh.setObjectName("actDevicesRefresh")
        act_dev_refresh.setToolTip("Geräteliste sofort neu laden — 2.6.51")
        act_dev_refresh.triggered.connect(
            lambda: self._show_devices_dialog(auto_refresh=True)
        )
        m_devices.addAction(act_dev_refresh)
        try:
            from instantlensdoc.core.devices import SCAN_START_HINT_DE

            self._set_status(SCAN_START_HINT_DE)
        except Exception:
            pass
        try:
            from instantlensdoc.ui.menu_click import prepare_menu_for_clicks

            prepare_menu_for_clicks(m_devices)
        except Exception:
            pass
        self._bind_devices_menu_live(m_devices)
        return m_devices

    def _bind_devices_menu_live(self, menu) -> None:
        """aboutToShow: Cache sofort, Hardware-Suche nur im Hintergrund."""
        if getattr(self, "_devices_menu_live_bound", False):
            return
        self._devices_menu_live_bound = True
        try:
            menu.aboutToShow.connect(self._on_devices_menu_about_to_show)
        except Exception:
            pass
        QTimer.singleShot(0, self._schedule_device_cache_refresh)

    def _on_devices_menu_about_to_show(self) -> None:
        menu = None
        try:
            menu = self.findChild(QMenu, "menuDevices")
        except Exception:
            menu = None
        if menu is None:
            return
        self._fill_devices_menu_from_cache(menu)
        self._schedule_device_cache_refresh()

    def _fill_devices_menu_from_cache(self, menu) -> None:
        """Menü Geräte mit letzter Liste füllen — ohne discover_devices()."""
        from PySide6.QtGui import QAction

        from instantlensdoc.core.devices import (
            DeviceInfo,
            DeviceKind,
            devices_menu_entries,
            load_cached_discovery,
        )

        for act in list(menu.actions()):
            try:
                name = act.objectName() or ""
            except Exception:
                name = ""
            if name.startswith("actCachedDevice") or name in (
                "actDevicesCacheSep",
                "actDevicesCacheHint",
            ):
                menu.removeAction(act)
        entries = devices_menu_entries(load_cached_discovery())
        sep = menu.addSeparator()
        sep.setObjectName("actDevicesCacheSep")
        if not entries:
            hint = QAction("(letzte Geräteliste leer — Suche im Hintergrund)", self)
            hint.setObjectName("actDevicesCacheHint")
            hint.setEnabled(False)
            menu.addAction(hint)
            return
        for i, (label, dev) in enumerate(entries):
            act = QAction(label, self)
            act.setObjectName(f"actCachedDevice{i}")
            if isinstance(dev, DeviceInfo) and dev.kind == DeviceKind.PRINTER:
                act.setToolTip("Drucker (keine Geräteöffnung beim Klick)")
            else:
                act.setToolTip("Scanner öffnen — kein Probe/Connect beim Klick")
            act.triggered.connect(
                lambda _checked=False, d=dev: self._on_cached_device_clicked(d)
            )
            menu.addAction(act)

    def _on_cached_device_clicked(self, dev) -> None:
        from instantlensdoc.core.devices import DeviceInfo, DeviceKind

        if not isinstance(dev, DeviceInfo):
            return
        if dev.kind == DeviceKind.PRINTER:
            self._show_devices_dialog(filter_kind="printer")
            return
        self._preferred_scan_device_id = dev.device_id or dev.name
        self._run_scan_import()

    def _schedule_device_cache_refresh(self) -> None:
        if getattr(self, "_device_refresh_inflight", False):
            return
        self._device_refresh_inflight = True
        from instantlensdoc.core.device_io import MENU_REFRESH_TIMEOUT_S
        from instantlensdoc.core.devices import DeviceDiscoveryResult, discover_devices
        from instantlensdoc.ui.async_worker import watch_worker

        def _done(result) -> None:
            self._device_refresh_inflight = False
            if isinstance(result, DeviceDiscoveryResult):
                try:
                    menu = self.findChild(QMenu, "menuDevices")
                except Exception:
                    menu = None
                if menu is not None and menu.isVisible():
                    self._fill_devices_menu_from_cache(menu)

        def _to() -> None:
            self._device_refresh_inflight = False

        watch_worker(
            self,
            discover_devices,
            timeout=MENU_REFRESH_TIMEOUT_S,
            on_done=_done,
            on_timeout=_to,
            on_error=lambda _e: _to(),
        )

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
        act_open.setObjectName("actFileOpen")
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
        act_save.setObjectName("actFileSave")
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
        act_save_as.setObjectName("actFileSaveAs")
        # Word-Parity: F12 = Speichern unter; Alt-Chord bleibt — 2.6.28
        act_save_as.setShortcuts(
            [
                QKeySequence("F12"),
                QKeySequence("Ctrl+Alt+Shift+U"),
            ]
        )
        act_save_as.setToolTip(
            "Text: Dokument speichern unter… · PDF: Annotation-Sidecar speichern unter… "
            "(F12 / Ctrl+Alt+Shift+U; Ctrl+Shift+S = Standard-Stempel ★) — 2.6.28"
        )
        act_save_as.triggered.connect(self.save_as)
        self._act_save_as = act_save_as
        m_file.addAction(act_save_as)
        act_save_copy = QAction("Als Kopie speichern…", self)
        act_save_copy.setShortcut(QKeySequence("Ctrl+Alt+S"))
        act_save_copy.setToolTip("PDF: Datei (+ Sidecar) als Kopie; Editor: Speichern unter")
        act_save_copy.triggered.connect(self.save_as_copy)
        m_file.addAction(act_save_copy)
        m_file.addSeparator()
        act_backup_now = QAction("Backup jetzt", self)
        act_backup_now.setToolTip(
            "Aktuelles Dokument manuell in den Backup-Ordner kopieren — 1.0.0"
        )
        act_backup_now.triggered.connect(self._manual_backup_now)
        m_file.addAction(act_backup_now)
        act_backup_folder = QAction("Backup-Ordner öffnen…", self)
        act_backup_folder.setToolTip("App-Backup-Ordner im Dateimanager öffnen — 1.0.0")
        act_backup_folder.triggered.connect(self._open_backup_folder)
        m_file.addAction(act_backup_folder)
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
        act_close_all = QAction("Alle Tabs schließen", self)
        act_close_all.setShortcut(QKeySequence("Ctrl+Alt+Shift+W"))
        act_close_all.setToolTip("Alle Dokument-Tabs schließen (Sidebar-Kontextmenü)")
        act_close_all.triggered.connect(self.close_all_tabs)
        m_file.addAction(act_close_all)
        act_close_left = QAction("Tabs links schließen", self)
        act_close_left.setToolTip("Alle Tabs links vom aktuellen schließen")
        act_close_left.triggered.connect(self.close_tabs_left_of_current)
        m_file.addAction(act_close_left)
        act_close_right = QAction("Tabs rechts schließen", self)
        act_close_right.setToolTip("Alle Tabs rechts vom aktuellen schließen")
        act_close_right.triggered.connect(self.close_tabs_right_of_current)
        m_file.addAction(act_close_right)
        act_dup_tab = QAction("Tab duplizieren", self)
        # Ctrl+Shift+T → Theme-Zyklus (1.4.5); Tab-Duplikat: Ctrl+Alt+Shift+T
        act_dup_tab.setShortcut(QKeySequence("Ctrl+Alt+Shift+T"))
        act_dup_tab.setToolTip(
            "Editor: Inhalt als neues Dokument klonen · Datei mit Pfad: optional erneut öffnen "
            "(Ctrl+Alt+Shift+T; Ctrl+Shift+T = Theme-Zyklus) — 1.4.5"
        )
        act_dup_tab.triggered.connect(self.duplicate_tab)
        m_file.addAction(act_dup_tab)
        act_compare_tabs = QAction("Text-Diff (offene Tabs)…", self)
        act_compare_tabs.setShortcut(QKeySequence("Ctrl+Alt+D"))
        act_compare_tabs.setToolTip(
            "Zwei offene Text-Tabs: Wrap-Blink Dauer/Sound · Änderung i/n · Wrap-around · F7/Shift+F7 · Sync-Scroll · Ignore-Whitespace · Diff-TXT — 1.2.9"
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
            ("Als XLSX…", "xlsx"),
            ("Als PDF…", "pdf"),
            ("Als TXT…", "txt"),
            ("Als RTF…", "rtf"),
            ("Als JPG…", "jpg"),
            ("Als EPUB…", "epub"),
            ("Als PPTX…", "pptx"),
        ]:
            a = QAction(title, self)
            a.triggered.connect(lambda checked=False, f=fmt: self._export_editor(f))
            m_export.addAction(a)
        act_text_pdf = QAction("Text → PDF…", self)
        act_text_pdf.setShortcut(QKeySequence("Ctrl+Shift+P"))
        act_text_pdf.setToolTip(
            "Aktuellen Text-Tab als einfaches PDF exportieren (pikepdf Seiten) — 1.7.0"
        )
        act_text_pdf.triggered.connect(self._export_text_to_pdf)
        m_export.addAction(act_text_pdf)
        act_pdfx = QAction("Als PDF/X (druckreif)…", self)
        act_pdfx.setObjectName("actExportPdfX")
        act_pdfx.setToolTip(
            "Druckreifes PDF/X bzw. Print-Ready mit Anschnitt — 2.6.18"
        )
        act_pdfx.triggered.connect(self._export_pdfx)
        m_export.addAction(act_pdfx)
        m_export.addSeparator()
        act_exp_prof_save = QAction("Export-Profil speichern…", self)
        act_exp_prof_save.setToolTip(
            "Benanntes Preset speichern (max. 10; Duplikate abgelehnt) — 2.5.2"
        )
        act_exp_prof_save.triggered.connect(self._save_export_profile)
        m_export.addAction(act_exp_prof_save)
        act_exp_prof_apply = QAction("Export-Presets verwalten…", self)
        act_exp_prof_apply.setToolTip(
            "Benannte Presets (max. 10): Anwenden/Löschen · Export/Import JSON — 2.5.2"
        )
        act_exp_prof_apply.triggered.connect(self._manage_export_presets)
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
        m_edit.setObjectName("menuBearbeiten")
        # Sichtbares Vor/Zurück: Pfeil-Icons, Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z, Enabled-
        # Zustand folgt dem Undo-Stack des aktiven Editors (undoAvailable/redoAvailable);
        # dieselben Aktionen bedienen die Ribbon-Pfeile (Start + Bearbeiten) — 2.6.54
        from PySide6.QtWidgets import QStyle

        act_undo = QAction(self.style().standardIcon(QStyle.SP_ArrowBack), "Rückgängig", self)
        act_undo.setShortcut(QKeySequence.Undo)
        act_undo.setToolTip("Letzte Änderung rückgängig (Ctrl+Z)")
        act_undo.triggered.connect(self._undo)
        m_edit.addAction(act_undo)
        act_redo = QAction(self.style().standardIcon(QStyle.SP_ArrowForward), "Wiederholen", self)
        redo_keys: list[QKeySequence] = []
        for ks in [*QKeySequence.keyBindings(QKeySequence.Redo), QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")]:
            if ks.toString() and all(ks.toString() != k.toString() for k in redo_keys):
                redo_keys.append(ks)
        act_redo.setShortcuts(redo_keys)
        act_redo.setToolTip("Rückgängig gemachte Änderung wiederholen (Ctrl+Y / Ctrl+Shift+Z)")
        act_redo.triggered.connect(self._redo)
        m_edit.addAction(act_redo)
        self._undo_action = act_undo
        self._redo_action = act_redo
        self._edit_undo_action = act_undo
        self._edit_redo_action = act_redo
        try:
            self.editor.undoAvailable.connect(lambda _a: self._sync_undo_redo_enabled())
            self.editor.redoAvailable.connect(lambda _a: self._sync_undo_redo_enabled())
            self.stack.currentChanged.connect(lambda _i: self._sync_undo_redo_enabled())
        except Exception:
            pass
        QTimer.singleShot(0, self._sync_undo_redo_enabled)
        m_edit.addSeparator()
        act_cut = QAction("Ausschneiden", self)
        act_cut.setShortcut(QKeySequence.Cut)
        act_cut.setObjectName("actEditCut")
        act_cut.setToolTip("Auswahl ausschneiden (Ctrl+X) — Editor")
        act_cut.triggered.connect(self._cut_editor)
        m_edit.addAction(self._track_editor_action(act_cut))
        act_copy = QAction("Kopieren", self)
        act_copy.setShortcut(QKeySequence.Copy)
        act_copy.setObjectName("actEditCopy")
        act_copy.setToolTip(
            "Editor-Auswahl oder PDF-Textauswahl (Auswahl-Werkzeug + Aufziehen) → Zwischenablage"
        )
        act_copy.triggered.connect(self._copy)
        m_edit.addAction(act_copy)
        act_paste = QAction("Einfügen", self)
        act_paste.setShortcut(QKeySequence.Paste)
        act_paste.setObjectName("actEditPaste")
        act_paste.setToolTip("Zwischenablage einfügen (Ctrl+V) — Editor")
        act_paste.triggered.connect(self._paste_editor)
        m_edit.addAction(self._track_editor_action(act_paste))
        act_select_all = QAction("Alles auswählen", self)
        act_select_all.setShortcut(QKeySequence.SelectAll)
        act_select_all.setObjectName("actEditSelectAll")
        act_select_all.setToolTip(
            "Editor: gesamten Text; PDF: alle Annotationen der Seite (Ctrl+A)"
        )
        act_select_all.triggered.connect(self._select_all_annotations_on_page)
        m_edit.addAction(act_select_all)
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
        act_find.setObjectName("actEditFind")
        act_find.setToolTip("Editor: Suchen/Ersetzen; PDF: Sidebar-Suche (Ctrl+F)")
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
        act_find_repl.setObjectName("actEditFindReplace")
        # Word-like Ctrl+H; Ctrl+R = Absatz rechts (2.6.11)
        act_find_repl.setShortcut(QKeySequence("Ctrl+H"))
        act_find_repl.setToolTip(
            "Find/Replace (Word: Ctrl+H) — Editor; PDF via Scripting"
        )
        act_find_repl.triggered.connect(self._find_replace)
        m_edit.addAction(self._track_editor_action(act_find_repl))
        act_bold = QAction("Fett", self)
        act_bold.setShortcut(QKeySequence("Ctrl+B"))
        act_bold.setObjectName("actEditBold")
        act_bold.setToolTip("Fett (QTextCharFormat) — Word/InDesign — 2.6.49")
        act_bold.triggered.connect(self._toggle_bold)
        m_edit.addAction(self._track_editor_action(act_bold))
        act_italic = QAction("Kursiv", self)
        act_italic.setShortcut(QKeySequence("Ctrl+I"))
        act_italic.setObjectName("actEditItalic")
        act_italic.setToolTip("Kursiv (QTextCharFormat) — 2.6.49")
        act_italic.triggered.connect(self._toggle_italic)
        m_edit.addAction(self._track_editor_action(act_italic))
        act_underline = QAction("Unterstrichen", self)
        act_underline.setShortcut(QKeySequence("Ctrl+U"))
        act_underline.setObjectName("actEditUnderline")
        act_underline.setToolTip("Unterstrichen (QTextCharFormat, Buchstaben inkl.) — 2.6.49")
        act_underline.triggered.connect(self._toggle_underline)
        m_edit.addAction(self._track_editor_action(act_underline))
        act_strike = QAction("Durchgestrichen", self)
        act_strike.setShortcut(QKeySequence("Ctrl+Shift+X"))
        act_strike.setObjectName("actEditStrike")
        act_strike.setToolTip("Durchgestrichen (QTextCharFormat) — Ctrl+Shift+X")
        act_strike.triggered.connect(self._toggle_strike)
        m_edit.addAction(self._track_editor_action(act_strike))
        act_font = QAction("Schriftart…", self)
        act_font.setObjectName("actEditFont")
        act_font.setToolTip("Schriftart und -größe (QFontDialog)")
        act_font.triggered.connect(self._choose_font)
        m_edit.addAction(self._track_editor_action(act_font))
        act_font_size = QAction("Schriftgröße…", self)
        act_font_size.setObjectName("actEditFontSize")
        act_font_size.setToolTip("Schriftgröße in Punkt")
        act_font_size.triggered.connect(self._choose_font_size)
        m_edit.addAction(self._track_editor_action(act_font_size))
        act_font_color = QAction("Schriftfarbe…", self)
        act_font_color.setObjectName("actEditFontColor")
        act_font_color.setToolTip("Textfarbe (QColorDialog)")
        act_font_color.triggered.connect(self._choose_font_color)
        m_edit.addAction(self._track_editor_action(act_font_color))
        act_highlight = QAction("Texthervorhebung…", self)
        act_highlight.setObjectName("actEditHighlight")
        act_highlight.setToolTip(
            "Textmarker/Hintergrundfarbe — QTextCharFormat.setBackground, bleibt in DOCX"
        )
        act_highlight.triggered.connect(self._choose_highlight_color)
        m_edit.addAction(self._track_editor_action(act_highlight))
        act_bg = QAction("Hintergrundfarbe…", self)
        act_bg.setObjectName("actEditBackgroundColor")
        act_bg.setToolTip("Hintergrundfarbe mergen (QTextCharFormat.setBackground)")
        act_bg.triggered.connect(self._choose_highlight_color)
        m_edit.addAction(self._track_editor_action(act_bg))
        act_clear_fmt = QAction("Formatierungen löschen", self)
        act_clear_fmt.setShortcut(QKeySequence("Ctrl+Space"))
        act_clear_fmt.setObjectName("actEditClearFormatting")
        act_clear_fmt.setToolTip("Zeichen- und Absatzformat auf Standard zurücksetzen")
        act_clear_fmt.triggered.connect(self._clear_formatting)
        m_edit.addAction(self._track_editor_action(act_clear_fmt))
        m_styles = m_edit.addMenu("Formatvorlagen")
        m_styles.setObjectName("menuEditStyles")
        m_styles.setToolTip("Absatzstile: Normal, Überschrift, Zitat")
        self._editor_only_menus.append(m_styles)
        for sid, label in (
            ("normal", "Normal"),
            ("h1", "Überschrift 1"),
            ("h2", "Überschrift 2"),
            ("h3", "Überschrift 3"),
            ("title", "Titel"),
            ("quote", "Zitat"),
            ("list", "Liste"),
        ):
            a_st = QAction(label, self)
            a_st.setObjectName(f"actEditStyle_{sid}")
            a_st.triggered.connect(lambda _c=False, s=sid: self._apply_paragraph_style(s))
            m_styles.addAction(self._track_editor_action(a_st))
        act_bullet = QAction("Aufzählungszeichen", self)
        act_bullet.setShortcut(QKeySequence("Ctrl+Shift+L"))
        act_bullet.setObjectName("actEditBulletList")
        act_bullet.setToolTip("Aufzählung ein/aus (• )")
        act_bullet.triggered.connect(lambda: self._toggle_list(ordered=False))
        m_edit.addAction(self._track_editor_action(act_bullet))
        self._act_bullet_list = act_bullet
        act_number = QAction("Nummerierung", self)
        act_number.setObjectName("actEditNumberedList")
        act_number.setToolTip("Nummerierte Liste ein/aus (1. )")
        act_number.triggered.connect(lambda: self._toggle_list(ordered=True))
        m_edit.addAction(self._track_editor_action(act_number))
        self._act_numbered_list = act_number
        act_para_dlg = QAction("Absatz…", self)
        act_para_dlg.setObjectName("actEditParagraph")
        act_para_dlg.setToolTip("Zeilenabstand, Einzug, Abstand davor/danach, Absatzkontrolle")
        act_para_dlg.triggered.connect(self._paragraph_format_dialog)
        m_edit.addAction(self._track_editor_action(act_para_dlg))
        self._act_paragraph_dialog = act_para_dlg
        act_break_line = QAction("Zeilenumbruch einfügen", self)
        act_break_line.setObjectName("actEditInsertLineBreak")
        act_break_line.setToolTip("Harter Zeilenumbruch an der Cursorposition")
        act_break_line.triggered.connect(lambda: self._insert_break("line"))
        m_edit.addAction(self._track_editor_action(act_break_line))
        act_break_page = QAction("Seitenumbruch einfügen", self)
        act_break_page.setShortcut(QKeySequence("Ctrl+Enter"))
        act_break_page.setObjectName("actEditInsertPageBreak")
        act_break_page.setToolTip("Seitenumbruch (Ctrl+Enter)")
        act_break_page.triggered.connect(lambda: self._insert_break("page"))
        m_edit.addAction(self._track_editor_action(act_break_page))
        act_link_edit = QAction("Hyperlink…", self)
        act_link_edit.setObjectName("actEditHyperlink")
        act_link_edit.setToolTip("Hyperlink in den Editor einfügen — Ctrl+Shift+K")
        act_link_edit.triggered.connect(self._insert_hyperlink_dialog)
        m_edit.addAction(self._track_editor_action(act_link_edit))
        act_table_edit = QAction("Tabelle einfügen…", self)
        act_table_edit.setObjectName("actEditInsertTable")
        act_table_edit.setToolTip("Tabelle an Cursor einfügen")
        act_table_edit.triggered.connect(self._insert_table_dialog)
        m_edit.addAction(self._track_editor_action(act_table_edit))
        act_auto_fmt = QAction("Automatische Formatierung", self)
        act_auto_fmt.setShortcut(QKeySequence("Ctrl+Alt+Shift+F"))
        act_auto_fmt.setToolTip(
            "Überschriften/Fließtext/Zitate heuristisch setzen (Presets) — 2.6.10"
        )
        act_auto_fmt.triggered.connect(self._auto_format_document)
        m_edit.addAction(act_auto_fmt)
        act_auto_toc = QAction("Inhaltsverzeichnis aktualisieren", self)
        act_auto_toc.setObjectName("actEditAutoToc")
        act_auto_toc.setToolTip(
            "TOC aus Überschriften: Editor→Markdown · PDF→Outline/Sidebar — 2.6.10 "
            "(ohne Ctrl+Alt+Shift+T: das Kürzel bleibt Tab duplizieren)"
        )
        act_auto_toc.triggered.connect(self._update_auto_toc)
        m_edit.addAction(act_auto_toc)
        act_lof = QAction("Abbildungsverzeichnis aktualisieren", self)
        act_lof.setObjectName("actEditAutoLof")
        act_lof.setShortcut(QKeySequence("Ctrl+Alt+Shift+A"))
        act_lof.setToolTip(
            "Abbildungsverzeichnis aus Captions/Markdown-Bildern — 2.6.28"
        )
        act_lof.triggered.connect(self._update_figure_list)
        m_edit.addAction(act_lof)
        act_idx = QAction("Stichwortverzeichnis aktualisieren", self)
        act_idx.setObjectName("actEditAutoIndex")
        act_idx.setShortcut(QKeySequence("Ctrl+Alt+Shift+X"))
        act_idx.setToolTip(
            "Stichwortverzeichnis aus Häufigkeitsanalyse — 2.6.28"
        )
        act_idx.triggered.connect(self._update_index)
        m_edit.addAction(act_idx)
        m_edit.addSeparator()
        act_align_l = QAction("Absatz links", self)
        act_align_l.setShortcut(QKeySequence("Ctrl+L"))
        act_align_l.setObjectName("actEditAlignLeft")
        act_align_l.setToolTip("Absatzausrichtung links — 2.6.11")
        act_align_l.triggered.connect(lambda: self._set_paragraph_alignment("left"))
        m_edit.addAction(self._track_editor_action(act_align_l))
        self._act_align_left = act_align_l
        act_align_c = QAction("Absatz zentriert", self)
        act_align_c.setShortcut(QKeySequence("Ctrl+E"))
        act_align_c.setObjectName("actEditAlignCenter")
        act_align_c.setToolTip("Absatzausrichtung zentriert — 2.6.11")
        act_align_c.triggered.connect(lambda: self._set_paragraph_alignment("center"))
        m_edit.addAction(self._track_editor_action(act_align_c))
        self._act_align_center = act_align_c
        act_align_r = QAction("Absatz rechts", self)
        act_align_r.setShortcut(QKeySequence("Ctrl+R"))
        act_align_r.setObjectName("actEditAlignRight")
        act_align_r.setToolTip(
            "Absatzausrichtung rechts (Ctrl+R; Ersetzen: Ctrl+H) — 2.6.11"
        )
        act_align_r.triggered.connect(lambda: self._set_paragraph_alignment("right"))
        m_edit.addAction(self._track_editor_action(act_align_r))
        self._act_align_right = act_align_r
        act_align_j = QAction("Absatz Blocksatz", self)
        act_align_j.setShortcut(QKeySequence("Ctrl+J"))
        act_align_j.setObjectName("actEditAlignJustify")
        act_align_j.setToolTip("Absatzausrichtung Blocksatz — 2.6.11")
        act_align_j.triggered.connect(lambda: self._set_paragraph_alignment("justify"))
        m_edit.addAction(self._track_editor_action(act_align_j))
        self._act_align_justify = act_align_j
        act_spacing = QAction("Zeilenabstand 1,5", self)
        act_spacing.setObjectName("actLineSpacing15")
        act_spacing.setToolTip("Zeilenabstand 1,5 für aktuellen Absatz — 2.6.11")
        act_spacing.triggered.connect(lambda: self._set_paragraph_line_spacing(1.5))
        m_edit.addAction(self._track_editor_action(act_spacing))
        self._act_spacing_15 = act_spacing
        act_spacing15 = QAction("Zeilenabstand 1,15 (Standard)", self)
        act_spacing15.setObjectName("actLineSpacing115")
        act_spacing15.triggered.connect(lambda: self._set_paragraph_line_spacing(1.15))
        m_edit.addAction(self._track_editor_action(act_spacing15))
        self._act_spacing_115 = act_spacing15
        act_tracking = QAction("Laufweite +50 (Tracking)", self)
        act_tracking.setToolTip("Tracking +50/1000 em für aktuellen Absatz — 2.6.13")
        act_tracking.triggered.connect(lambda: self._set_typography(tracking=50.0))
        m_edit.addAction(self._track_editor_action(act_tracking))
        act_leading = QAction("Durchschuss 1,5 (Leading)", self)
        act_leading.setToolTip("Leading 1,5 für aktuellen Absatz — 2.6.13")
        act_leading.triggered.connect(lambda: self._set_typography(leading=1.5))
        m_edit.addAction(self._track_editor_action(act_leading))
        act_dropcap = QAction("Initial / Drop Cap", self)
        act_dropcap.setShortcut(QKeySequence("Ctrl+Alt+Shift+D"))
        act_dropcap.setToolTip("Drop Cap (3 Zeilen, 1 Zeichen) — 2.6.13")
        act_dropcap.triggered.connect(self._apply_drop_cap)
        m_edit.addAction(self._track_editor_action(act_dropcap))
        # Silbentrennung: Menü aller 9 UI-Sprachen (Engine seit 2.6.28) — 2.6.36
        from ild_pdf.typography import HYPHENATION_UI_LANGS

        _hyphen_labels = {
            "de": "Deutsch (DE)",
            "en": "English (EN)",
            "fr": "Français (FR)",
            "ru": "Русский (RU)",
            "es": "Español (ES)",
            "zh": "中文 (ZH, no-break)",
            "pt": "Português (PT)",
            "ar": "العربية (AR, no-break)",
            "it": "Italiano (IT)",
        }
        m_hyphen = m_edit.addMenu("Silbentrennung")
        m_hyphen.setToolTip(
            "Intelligente Silbentrennung — alle 9 UI-Sprachen (ZH/AR no-break) — 2.6.36"
        )
        self._editor_only_menus.append(m_hyphen)
        for _lang in HYPHENATION_UI_LANGS:
            _label = _hyphen_labels.get(_lang, _lang.upper())
            _act = QAction(_label, self)
            if _lang == "de":
                _act.setShortcut(QKeySequence("Ctrl+Alt+Shift+H"))
            _act.setToolTip(f"Silbentrennung {_label} — 2.6.36")
            _act.triggered.connect(
                lambda _checked=False, lang=_lang: self._hyphenate_document(lang)
            )
            m_hyphen.addAction(_act)
        act_palette = QAction("Schnellaktionen…", self)
        act_palette.setShortcut(QKeySequence("Ctrl+K"))
        act_palette.setToolTip(
            "Command Palette: öffnen, suchen, OCR, export… — Ctrl+K — 2.3.0"
        )
        act_palette.triggered.connect(self._open_command_palette)
        m_edit.addAction(act_palette)
        act_search_csv = QAction("Suchergebnisse als CSV exportieren…", self)
        act_search_csv.setToolTip("Aktuelle Trefferliste (Sidebar) als CSV speichern")
        act_search_csv.triggered.connect(lambda: self._on_search_export("csv"))
        m_edit.addAction(act_search_csv)
        act_search_json = QAction("Suchergebnisse als JSON exportieren…", self)
        act_search_json.setToolTip(
            "Trefferliste als JSON (ildsearch-v1): Seite, Offset, Snippet — 0.9.5"
        )
        act_search_json.triggered.connect(lambda: self._on_search_export("json"))
        m_edit.addAction(act_search_json)
        act_multi_search = QAction("Multi-Dokument-Suche…", self)
        act_multi_search.setShortcut(QKeySequence("Ctrl+Shift+F"))
        act_multi_search.setToolTip(
            "Volltext über alle offenen PDFs (Textlayer) · zentrale Trefferliste — 2.0.0"
        )
        act_multi_search.triggered.connect(self._open_multi_doc_search)
        m_edit.addAction(act_multi_search)
        act_search_hl = QAction("Treffer als Highlight (Seite)…", self)
        act_search_hl.setToolTip(
            "Suchtreffer der aktuellen PDF-Seite als Highlight-Annotationen — 0.9.6"
        )
        act_search_hl.triggered.connect(
            lambda: self._on_search_annotate_hits(False)
        )
        m_edit.addAction(act_search_hl)
        act_search_hl_all = QAction("Treffer als Highlight (alle Seiten)…", self)
        act_search_hl_all.setToolTip(
            "Suchtreffer aller PDF-Seiten als Highlight-Annotationen (ein Undo) — 0.9.7"
        )
        act_search_hl_all.triggered.connect(
            lambda: self._on_search_annotate_hits(True)
        )
        m_edit.addAction(act_search_hl_all)
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
        # Ctrl+H = Suchen/Ersetzen (Word); Markieren → Ctrl+Shift+H — 2.6.10
        act_mark.setShortcut(QKeySequence("Ctrl+Shift+H"))
        act_mark.setToolTip(
            "Textmarker: QTextCharFormat.setBackground auf Auswahl oder ganzes Dokument"
        )
        act_mark.triggered.connect(self._mark_selection)
        m_edit.addAction(act_mark)
        act_toggle_case = QAction("Groß-/Kleinschreibung umschalten", self)
        act_toggle_case.setShortcut(QKeySequence("Ctrl+Shift+U"))
        act_toggle_case.setToolTip("Auswahl: GROSS → klein → Titel → GROSS")
        act_toggle_case.triggered.connect(self._toggle_case_selection)
        m_edit.addAction(act_toggle_case)
        act_all_upper = QAction("Alles großschreiben", self)
        # Collision mit Speichern-unter (U) und Gruppieren (G) behoben — 2.6.28
        act_all_upper.setShortcut(QKeySequence("Ctrl+Alt+Shift+J"))
        act_all_upper.setToolTip(
            "Gesamten Editor-Text in Großbuchstaben (Ctrl+Alt+Shift+J) — 2.6.28"
        )
        act_all_upper.triggered.connect(lambda: self._transform_document_case("upper"))
        m_edit.addAction(act_all_upper)
        act_all_lower = QAction("Alles kleinschreiben", self)
        act_all_lower.setShortcut(QKeySequence("Ctrl+Alt+Shift+L"))
        act_all_lower.setToolTip("Gesamten Editor-Text in Kleinbuchstaben")
        act_all_lower.triggered.connect(lambda: self._transform_document_case("lower"))
        m_edit.addAction(act_all_lower)
        m_snippets = m_edit.addMenu("Textbausteine")
        for i in range(9):
            a_ins = QAction(f"Einfügen {i + 1}", self)
            # Ctrl+Alt+1–4 = Annotation-Typen (PDF); Bausteine 1–4 ohne Kürzel — 2.6.54
            if i >= 4:
                a_ins.setShortcut(QKeySequence(f"Ctrl+Alt+{i + 1}"))
            a_ins.setToolTip(
                f"Gespeicherten Textbaustein {i + 1} an Cursor einfügen"
                + (
                    " (Ctrl+Alt+1–4: Annotation-Typen)"
                    if i < 4
                    else f" (Ctrl+Alt+{i + 1})"
                )
            )
            a_ins.triggered.connect(lambda checked=False, idx=i: self._insert_snippet(idx))
            m_snippets.addAction(a_ins)
        m_snippets.addSeparator()
        for i in range(9):
            a_save = QAction(f"Auswahl → Slot {i + 1}", self)
            a_save.setToolTip(f"Aktuelle Auswahl (oder Zeile) als Textbaustein {i + 1} speichern")
            a_save.triggered.connect(lambda checked=False, idx=i: self._save_snippet(idx))
            m_snippets.addAction(a_save)
        act_ac = QAction("Autokorrektur", self)
        act_ac.setCheckable(True)
        from instantlensdoc.core.app_settings import get_autocorrect_enabled as _gae_init

        act_ac.setChecked(bool(_gae_init()))
        act_ac.setToolTip(
            "Tippfehler und Baustein-Kürzel beim Tippen ersetzen (Space/Satzzeichen) — 2.6.20"
        )
        act_ac.triggered.connect(self._toggle_autocorrect)
        m_edit.addAction(act_ac)
        self._autocorrect_action = act_ac
        act_indent = QAction("Einrückung erhöhen", self)
        act_indent.setShortcut(QKeySequence("Ctrl+]"))
        act_indent.setToolTip("Zeilen/Block einrücken (auch Tab)")
        act_indent.triggered.connect(self._indent_selection)
        m_edit.addAction(self._track_editor_action(act_indent))
        self._act_indent = act_indent
        act_outdent = QAction("Einrückung verringern", self)
        act_outdent.setShortcut(QKeySequence("Ctrl+["))
        act_outdent.setToolTip("Zeilen/Block ausrücken (auch Shift+Tab)")
        act_outdent.triggered.connect(self._outdent_selection)
        m_edit.addAction(self._track_editor_action(act_outdent))
        self._act_outdent = act_outdent
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
        act_spell.setObjectName("actEditSpellcheck")
        act_spell.setToolTip(
            "Wortliste + Builtin der UI-Sprache; Vorschläge im Tooltip; "
            "leichte Grammatik-Hinweise — 2.6.20"
        )
        act_spell.triggered.connect(self._check_spelling)
        m_edit.addAction(self._track_editor_action(act_spell))
        act_spell_sugg = QAction("Rechtschreibvorschläge…", self)
        act_spell_sugg.setShortcut(QKeySequence("Shift+F7"))
        act_spell_sugg.setToolTip("Unbekannte Wörter mit Korrekturvorschlägen auflisten — 2.6.20")
        act_spell_sugg.triggered.connect(self._show_spell_suggestions)
        m_edit.addAction(self._track_editor_action(act_spell_sugg))
        act_spell_clear = QAction("Rechtschreibmarkierungen löschen", self)
        act_spell_clear.triggered.connect(self._clear_spelling)
        m_edit.addAction(act_spell_clear)
        m_edit.addSeparator()
        m_review = m_edit.addMenu("Review / Zusammenarbeit")
        act_shared = QAction("Gemeinsames Review…", self)
        act_shared.setObjectName("actSharedReview")
        act_shared.setShortcut(QKeySequence("Ctrl+Alt+Shift+C"))
        act_shared.setToolTip(
            "Review-Session starten/beitreten: Freigabeordner oder optionaler "
            "HTTP-Endpoint — Notizen/Markierungen/Stempel/Kommentare — 2.6.23"
        )
        act_shared.triggered.connect(self._show_shared_review_dialog)
        m_review.addAction(act_shared)
        act_review = QAction("Änderungen nachverfolgen…", self)
        act_review.setObjectName("actReviewMode")
        act_review.setShortcut(QKeySequence("Ctrl+Alt+Shift+R"))
        act_review.setToolTip(
            "Review-Modus: Einfügen/Löschen je Autor protokollieren (lokal) — 2.6.21 "
            "(Ctrl+Alt+Shift+R; Ctrl+Shift+E = Arbeitsverzeichnis)"
        )
        act_review.triggered.connect(self._show_review_dialog)
        m_review.addAction(act_review)
        self._review_action = act_review
        act_comments = QAction("Kommentare…", self)
        act_comments.setObjectName("actDocComments")
        act_comments.setShortcut(QKeySequence("Ctrl+Alt+M"))
        act_comments.setToolTip(
            "Feedback an Textstellen ohne Body-Änderung — 2.6.21"
        )
        act_comments.triggered.connect(self._show_comments_dialog)
        m_review.addAction(act_comments)
        act_versions = QAction("Versionsverlauf…", self)
        act_versions.setObjectName("actVersionHistory")
        act_versions.setShortcut(QKeySequence("Ctrl+Alt+Shift+H"))
        act_versions.setToolTip(
            "Dokumentstände speichern und wiederherstellen (lokal) — 2.6.21"
        )
        act_versions.triggered.connect(self._show_version_history_dialog)
        m_review.addAction(act_versions)
        act_mail_merge = QAction("Seriendruck…", self)
        act_mail_merge.setObjectName("actMailMerge")
        act_mail_merge.setToolTip(
            "Empfänger aus CSV/Excel → Briefe mit {{Feld}}-Platzhaltern — 2.6.21"
        )
        act_mail_merge.triggered.connect(self._run_mail_merge_dialog)
        m_review.addAction(act_mail_merge)
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
        act_sel_all_ann.setObjectName("actSelectAllAnnotations")
        act_sel_all_ann.setToolTip(
            "PDF: alle Annotationen der Seite; Editor: gesamten Text (Ctrl+A: Alles auswählen)"
        )
        act_sel_all_ann.triggered.connect(self._select_all_annotations_on_page)
        m_edit.addAction(act_sel_all_ann)
        act_clear_page_ann = QAction("Alle Annotationen auf Seite löschen…", self)
        act_clear_page_ann.setToolTip(
            "Alle Annotationen der aktuellen Seite nach Bestätigung löschen; "
            "bei 0 gefilterten Treffern Menü/Aktion no-op mit Status — 1.1.5"
        )
        act_clear_page_ann.triggered.connect(self._clear_annotations_on_page)
        m_edit.addAction(act_clear_page_ann)

        m_view = mb.addMenu("&Ansicht")
        a = QAction("Seitenleiste", self)
        a.setCheckable(True)
        a.setChecked(True)
        a.toggled.connect(self.sidebar.setVisible)
        m_view.addAction(a)
        # Panel-Sichtbarkeit Thumb / Ann / Bookmark — Session (0.9.5)
        self._panel_thumbs_action = QAction("Vorschaubilder (Thumbnails)", self)
        self._panel_thumbs_action.setCheckable(True)
        self._panel_thumbs_action.setChecked(True)
        self._panel_thumbs_action.setToolTip(
            "Sidebar-Panel Vorschaubilder ein-/ausblenden (Session) — 0.9.5"
        )
        self._panel_thumbs_action.toggled.connect(self._toggle_panel_thumbs)
        m_view.addAction(self._panel_thumbs_action)
        self._panel_ann_action = QAction("Annotationsliste", self)
        self._panel_ann_action.setCheckable(True)
        self._panel_ann_action.setChecked(True)
        self._panel_ann_action.setToolTip(
            "Sidebar-Panel Annotationen ein-/ausblenden (Session) — 0.9.5"
        )
        self._panel_ann_action.toggled.connect(self._toggle_panel_ann)
        m_view.addAction(self._panel_ann_action)
        self._panel_bookmark_action = QAction("Lesezeichen / Outline", self)
        self._panel_bookmark_action.setCheckable(True)
        self._panel_bookmark_action.setChecked(True)
        self._panel_bookmark_action.setToolTip(
            "Sidebar-Panel Lesezeichen/Outline ein-/ausblenden (Session) — 0.9.5"
        )
        self._panel_bookmark_action.toggled.connect(self._toggle_panel_bookmark)
        m_view.addAction(self._panel_bookmark_action)
        # Workspace-Layouts: Name + Panel-Sichtbarkeit + Splitter — 1.6.0
        self._workspace_layout_menu = m_view.addMenu("Arbeitsbereich-Layouts")
        self._refresh_workspace_layout_menu()
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
        self._rulers_action = QAction("Lineal", self)
        self._rulers_action.setCheckable(True)
        from instantlensdoc.core.app_settings import (
            get_show_rulers,
            get_show_alignment_grid,
        )

        self._rulers_action.setChecked(get_show_rulers())
        self._rulers_action.setShortcut(QKeySequence("Ctrl+Alt+R"))
        self._rulers_action.setToolTip(
            "Horizontales/vertikales Lineal im PDF-Viewer — 2.6.11"
        )
        self._rulers_action.toggled.connect(self._toggle_rulers)
        m_view.addAction(self._rulers_action)
        self._grid_action = QAction("Ausrichtungsraster", self)
        self._grid_action.setCheckable(True)
        self._grid_action.setChecked(get_show_alignment_grid())
        self._grid_action.setShortcut(QKeySequence("Ctrl+Alt+G"))
        self._grid_action.setToolTip(
            "Raster + Guides zur Ausrichtung — 2.6.11"
        )
        self._grid_action.toggled.connect(self._toggle_alignment_grid)
        m_view.addAction(self._grid_action)
        self._satzspiegel_action = QAction("Satzspiegel", self)
        self._satzspiegel_action.setCheckable(True)
        from instantlensdoc.core.app_settings import get_show_satzspiegel

        self._satzspiegel_action.setChecked(get_show_satzspiegel())
        self._satzspiegel_action.setShortcut(QKeySequence("Ctrl+Alt+S"))
        self._satzspiegel_action.setToolTip(
            "Satzspiegel / Type Area Overlay — 2.6.12"
        )
        self._satzspiegel_action.toggled.connect(self._toggle_satzspiegel)
        m_view.addAction(self._satzspiegel_action)
        self._layout_mode_action = QAction("Layout-Modus", self)
        self._layout_mode_action.setObjectName("actLayoutMode")
        self._layout_mode_action.setShortcut(QKeySequence("Ctrl+Alt+L"))
        self._layout_mode_action.setToolTip(
            "DTP-Canvas: Rahmen, Lineal, Raster, Musterseiten — 2.6.54"
        )
        self._layout_mode_action.triggered.connect(self._enter_layout_mode)
        m_view.addAction(self._layout_mode_action)
        self._current_line_hl_action = QAction("Aktuelle Zeile hervorheben", self)
        self._current_line_hl_action.setCheckable(True)
        self._current_line_hl_action.setChecked(get_editor_current_line_highlight())
        self._current_line_hl_action.setToolTip(
            "Aktuelle Editorzeile farblich hervorheben (auch in Einstellungen)"
        )
        self._current_line_hl_action.toggled.connect(self._toggle_current_line_highlight)
        m_view.addAction(self._current_line_hl_action)
        self._minimap_action = QAction("Editor-Minimap (nur Text/Code)", self)
        self._minimap_action.setCheckable(True)
        self._minimap_action.setChecked(get_editor_minimap())
        self._minimap_action.setToolTip(
            "Schmale Linien-Übersicht rechts neben Plaintext/Code (Standard: aus). "
            "In DOCX/HTML-Dokumenten nie sichtbar. Einstellung wird gespeichert."
        )
        # Kein Ctrl+Shift+I mehr: lag neben Kursiv (Ctrl+I) und schaltete die Minimap
        # unbemerkt dauerhaft ein (Feldbefund 2.6.53) — 2.6.54
        self._minimap_action.toggled.connect(self._toggle_minimap)
        m_view.addAction(self._minimap_action)
        self._md_preview_action = QAction("Markdown-Vorschau", self)
        self._md_preview_action.setCheckable(True)
        self._md_preview_action.setChecked(get_editor_markdown_preview())
        self._md_preview_action.setToolTip(
            "Editor-Split: Markdown-Vorschau ein/aus (Ctrl+Alt+Shift+M; "
            "Ctrl+Shift+M = Seitenmanagement)"
        )
        self._md_preview_action.setShortcut(QKeySequence("Ctrl+Alt+Shift+M"))
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
        self._doc_split_sync_action = QAction("Sync-Scroll (PDF-Tabs / Split)", self)
        self._doc_split_sync_action.setCheckable(True)
        self._doc_split_sync_action.setChecked(get_editor_doc_split_sync_scroll())
        self._doc_split_sync_action.setToolTip(
            "Sync-Scroll nur PDF↔PDF: Scroll-Ratio + Seiten-Sync "
            "(Ctrl+Alt+\\); Statusleisten-Indikator — 2.4.1"
        )
        self._doc_split_sync_action.setShortcut(QKeySequence("Ctrl+Alt+\\"))
        self._doc_split_sync_action.toggled.connect(self._toggle_doc_split_sync_scroll)
        m_view.addAction(self._doc_split_sync_action)
        # Status-Widget AccessibleName live an/aus (QAction ohne setAccessibleName) — 2.4.5
        self._sync_doc_split_sync_action_a11y_tip(
            bool(get_editor_doc_split_sync_scroll())
        )
        act_sec_doc = QAction("Zweites Dokument wählen…", self)
        act_sec_doc.setToolTip("Datei für die rechte Split-Ansicht aus offenen Tabs wählen")
        act_sec_doc.triggered.connect(self._pick_secondary_document)
        m_view.addAction(act_sec_doc)
        self._soft_wrap_action = QAction("Wortumbruch", self)
        self._soft_wrap_action.setCheckable(True)
        self._soft_wrap_action.setChecked(get_editor_soft_wrap())
        self._soft_wrap_action.setToolTip(
            "Wortumbruch am Fensterrand im Texteditor — persistiert "
            "(Ctrl+Alt+W; Ctrl+Shift+W = andere Tabs schließen)"
        )
        self._soft_wrap_action.setShortcut(QKeySequence("Ctrl+Alt+W"))
        self._soft_wrap_action.toggled.connect(self._toggle_soft_wrap)
        m_view.addAction(self._soft_wrap_action)
        self._page_layout_action = QAction("Seitenlayout…", self)
        self._page_layout_action.setObjectName("actPageLayout")
        self._page_layout_action.setToolTip(
            "Seitenformat (A4/Letter/Buchformate), Ausrichtung und Ränder für den "
            "Texteditor — Text bricht in Seitenbreite um (DOCX/Word-Suite) — 2.6.53"
        )
        self._page_layout_action.triggered.connect(self._show_page_layout_dialog)
        m_view.addAction(self._track_editor_action(self._page_layout_action))
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
        from instantlensdoc.core.app_settings import (
            get_pdf_book_layout,
            get_pdf_page_by_page,
            get_doc_tabs_visible as _get_doc_tabs,
            get_ribbon_visible as _get_ribbon,
        )

        self._book_layout_action = QAction("Buch-Layout", self)
        self._book_layout_action.setCheckable(True)
        self._book_layout_action.setChecked(get_pdf_book_layout())
        self._book_layout_action.setObjectName("actBookLayout")
        self._book_layout_action.setToolTip(
            "Buch-Layout: Cover allein, danach Doppelseiten (Ctrl+Alt+Shift+2) — 2.6.54"
        )
        self._book_layout_action.setShortcut(QKeySequence("Ctrl+Alt+Shift+2"))
        self._book_layout_action.toggled.connect(self._toggle_book_layout)
        m_view.addAction(self._book_layout_action)
        self._continuous_action = QAction("Fortlaufend scrollen", self)
        self._continuous_action.setCheckable(True)
        self._continuous_action.setChecked(get_pdf_continuous_scroll())
        self._continuous_action.setObjectName("actContinuousScroll")
        self._continuous_action.setToolTip(
            "Seiten untereinander scrollen statt Einzelseite (Ctrl+3); schließt Doppelseite aus"
        )
        self._continuous_action.setShortcut(QKeySequence("Ctrl+3"))
        self._continuous_action.toggled.connect(self._toggle_continuous_scroll)
        m_view.addAction(self._continuous_action)
        self._page_by_page_action = QAction("Seite-für-Seite-Scrollen", self)
        self._page_by_page_action.setCheckable(True)
        self._page_by_page_action.setChecked(get_pdf_page_by_page())
        self._page_by_page_action.setObjectName("actPageByPage")
        self._page_by_page_action.setToolTip(
            "Mausrad blättert Seiten (kein fortlaufendes Scrollen) — Ctrl+Alt+Shift+3 — 2.6.54"
        )
        self._page_by_page_action.setShortcut(QKeySequence("Ctrl+Alt+Shift+3"))
        self._page_by_page_action.toggled.connect(self._toggle_page_by_page)
        m_view.addAction(self._page_by_page_action)
        self._doc_tabs_action = QAction("Dokument-Tabs", self)
        self._doc_tabs_action.setCheckable(True)
        self._doc_tabs_action.setChecked(_get_doc_tabs())
        self._doc_tabs_action.setObjectName("actDocTabs")
        self._doc_tabs_action.setToolTip(
            "Horizontale Tabs für offene Dokumente ein-/ausblenden — 2.6.19"
        )
        self._doc_tabs_action.toggled.connect(self._toggle_doc_tabs)
        m_view.addAction(self._doc_tabs_action)
        self._ribbon_action = QAction("Ribbon-Leiste", self)
        self._ribbon_action.setCheckable(True)
        self._ribbon_action.setChecked(_get_ribbon())
        self._ribbon_action.setObjectName("actRibbon")
        self._ribbon_action.setToolTip(
            "Ribbon-ähnliche Werkzeugleiste (partiell) — 2.6.19"
        )
        self._ribbon_action.toggled.connect(self._toggle_ribbon)
        m_view.addAction(self._ribbon_action)
        self._chrome_mode_actions: dict = {}
        m_chrome = m_view.addMenu("Oberfläche")
        m_chrome.setObjectName("menuChromeMode")
        m_chrome.setToolTip("Klassisch (Pull-down), Ribbon oder kombiniert")
        chrome_group = QActionGroup(self)
        chrome_group.setExclusive(True)
        chrome_group.setObjectName("actGroupChromeMode")
        for mode, label in (
            ("klassisch", "Klassisch (Pull-down)"),
            ("ribbon", "Ribbon"),
            ("kombiniert", "Kombiniert"),
        ):
            act = QAction(label, self)
            act.setCheckable(True)
            act.setObjectName(f"actChrome_{mode}")
            chrome_group.addAction(act)
            act.triggered.connect(lambda _c=False, m=mode: self._set_chrome_mode(m))
            m_chrome.addAction(act)
            self._chrome_mode_actions[mode] = act
        act_styles_pane = QAction("Formatvorlagen", self)
        act_styles_pane.setObjectName("actStylesPane")
        act_styles_pane.triggered.connect(self._toggle_style_pane)
        m_view.addAction(act_styles_pane)
        self._ann_layer_action = QAction("Annotation-Layer", self)
        self._ann_layer_action.setCheckable(True)
        self._ann_layer_action.setChecked(get_annotations_visible())
        self._ann_layer_action.setToolTip("Annotationen auf der PDF-Seite ein-/ausblenden")
        self._ann_layer_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
        self._ann_layer_action.toggled.connect(self._toggle_ann_layer)
        m_view.addAction(self._ann_layer_action)
        # Typ-Toggles Highlight/Note/Shape/Redaction — 1.8.0; Zähler-Klick filtert · Alle ein/aus — 1.8.2
        m_ann_types = m_view.addMenu("Annotation-Typen")
        m_ann_types.setToolTip(
            "Sichtbarkeit nach Typ; Klick auf Zähler filtert Ann.-Liste; Alle ein/aus — 1.8.2"
        )
        types_vis = get_ann_layer_types_visible()
        self._ann_type_actions: dict[str, QAction] = {}
        self._ann_type_labels = {
            "highlight": "Markierungen",
            "note": "Notizen",
            "shape": "Formen",
            "redaction": "Schwärzungen",
        }
        type_shortcuts = {
            "highlight": "Ctrl+Alt+1",
            "note": "Ctrl+Alt+2",
            "shape": "Ctrl+Alt+3",
            "redaction": "Ctrl+Alt+4",
        }
        act_all_on = QAction("Alle ein", self)
        act_all_on.setShortcut(QKeySequence("Ctrl+Alt+0"))
        act_all_on.setToolTip(
            "Alle Annotation-Typen einblenden (Ctrl+Alt+0); Undo/Redo ein Stack-Eintrag — 1.8.4"
        )
        act_all_on.triggered.connect(lambda: self._set_all_ann_type_layers(True))
        m_ann_types.addAction(act_all_on)
        act_all_off = QAction("Alle aus", self)
        act_all_off.setShortcut(QKeySequence("Ctrl+Alt+Shift+0"))
        act_all_off.setToolTip(
            "Alle Annotation-Typen ausblenden (Ctrl+Alt+Shift+0); Undo/Redo ein Stack-Eintrag — 1.8.4"
        )
        act_all_off.triggered.connect(lambda: self._set_all_ann_type_layers(False))
        m_ann_types.addAction(act_all_off)
        act_clear_filter = QAction("Listenfilter zurücksetzen", self)
        act_clear_filter.setToolTip("Ann.-Listenfilter (Layer-Typ) zurücksetzen — 1.8.2")
        act_clear_filter.triggered.connect(
            lambda: self._filter_ann_list_by_layer_group("")
        )
        m_ann_types.addAction(act_clear_filter)
        m_ann_types.addSeparator()
        for key, label in self._ann_type_labels.items():
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(bool(types_vis.get(key, True)))
            act.setData(key)
            act.setShortcut(QKeySequence(type_shortcuts[key]))
            act.setToolTip(
                f"{label} ein-/ausblenden ({type_shortcuts[key]}); "
                f"Klick filtert Ann.-Liste auf diesen Typ — 1.8.2"
            )
            act.toggled.connect(
                lambda checked, g=key: self._toggle_ann_type_layer(g, checked)
            )
            act.triggered.connect(
                lambda _checked=False, g=key: self._filter_ann_list_by_layer_group(g)
            )
            m_ann_types.addAction(act)
            self._ann_type_actions[key] = act
        self._m_ann_types = m_ann_types
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
            "PDF Vollbild-Präsentation (Pfeiltasten/Leertaste weiter, Esc beendet; "
            "optional Ann.-Overlay aus) — 1.7.0"
        )
        act_present.triggered.connect(self._toggle_presentation)
        m_view.addAction(act_present)
        self._favorites_bar_action = QAction("Lesezeichen-Leiste", self)
        self._favorites_bar_action.setCheckable(True)
        self._favorites_bar_action.setChecked(get_favorites_bar_visible())
        self._favorites_bar_action.setToolTip(
            "Globale Favoriten-Leiste (ildfav-v1) ein-/ausblenden — 1.7.0"
        )
        self._favorites_bar_action.toggled.connect(self._toggle_favorites_bar)
        m_view.addAction(self._favorites_bar_action)
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
        act_fit.setToolTip("Aktuelle Seite in den sichtbaren Bereich einpassen (Ctrl+0)")
        act_fit.triggered.connect(self._fit_page)
        m_view.addAction(act_fit)
        act_fit_w = QAction("Breite einpassen", self)
        act_fit_w.setShortcut(QKeySequence("Ctrl+9"))
        act_fit_w.setToolTip("Seitenbreite an den sichtbaren Bereich anpassen (Ctrl+9)")
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
        self._theme_system_action = QAction("System-Theme folgen", self)
        self._theme_system_action.setCheckable(True)
        self._theme_system_action.setToolTip(
            "OS Hell/Dunkel folgen (live bei OS-Wechsel); "
            "aus = manueller Override — 1.4.1"
        )
        self._theme_system_action.triggered.connect(self._toggle_follow_system)
        m_view.addAction(self._theme_system_action)
        self._theme_action = QAction("Dunkles Design", self)
        self._theme_action.setCheckable(True)
        self._theme_action.setToolTip("Manuell Hell/Dunkel umschalten (Override) — 1.4.0")
        self._theme_action.triggered.connect(self._toggle_theme)
        m_view.addAction(self._theme_action)
        act_theme_cycle = QAction("Theme zyklisch (System→Hell→Dunkel)", self)
        act_theme_cycle.setShortcut(QKeySequence("Ctrl+Shift+T"))
        act_theme_cycle.setToolTip(
            "Theme zyklisch: System → Hell → Dunkel → System "
            "(Ctrl+Shift+T); Status-Toast „Theme: …“ — 1.4.5"
        )
        act_theme_cycle.triggered.connect(self._cycle_theme_mode)
        m_view.addAction(act_theme_cycle)
        self._theme_cycle_action = act_theme_cycle
        self._high_contrast_action = QAction("Hoher Kontrast", self)
        self._high_contrast_action.setCheckable(True)
        self._high_contrast_action.setShortcut(QKeySequence("Ctrl+Alt+H"))
        self._high_contrast_action.setToolTip(
            "High-Contrast Theme ein/aus (Ctrl+Alt+H) — Toast Dauer OCR-Settings · "
            "A11y wie OCR-Toast — 2.0.5"
        )
        try:
            from instantlensdoc.core.app_settings import get_high_contrast

            self._high_contrast_action.setChecked(bool(get_high_contrast()))
        except Exception:
            self._high_contrast_action.setChecked(False)
        self._high_contrast_action.triggered.connect(self._toggle_high_contrast)
        m_view.addAction(self._high_contrast_action)
        self._sync_theme_menu()

        # Geräte VOR dem großen PDF-Menü — sichtbar + robust — 2.6.51
        self._ensure_devices_menu(mb)

        m_pdf = mb.addMenu("&PDF")
        m_pdf.setObjectName("menuPdf")
        m_pdf.setToolTipsVisible(True)
        self._pdf_menu = m_pdf
        act_merge = QAction("PDFs zusammenführen / teilen…", self)
        self._bind_pdf_action(act_merge, self._pdf_tools)
        m_pdf.addAction(act_merge)
        act_extract = QAction("Seitenbereich extrahieren…", self)
        act_extract.setToolTip(
            "Seitenbereiche z. B. 1-3,5,8-10; DE-Validierung + Seitenanzahl-Vorschau — 1.2.1"
        )
        self._bind_pdf_action(act_extract, self._extract_page_range)
        m_pdf.addAction(act_extract)
        act_split_pages = QAction("Seiten als Einzel-PDFs…", self)
        act_split_pages.setToolTip("Jede Seite als eigene PDF-Datei in einen Ordner")
        self._bind_pdf_action(act_split_pages, self._split_into_single_page_pdfs)
        m_pdf.addAction(act_split_pages)
        act_wm = QAction("Wasserzeichen / Seitennummern / Kopfzeile…", self)
        act_wm.setToolTip(
            "Opacity/Größe/Winkel Settings; Seitenbereich; zuletzt Text/Bild; Bake — 1.6.1"
        )
        self._bind_pdf_action(act_wm, self._watermark_tools)
        m_pdf.addAction(act_wm)
        act_cmp = QAction("Zwei PDFs vergleichen…", self)
        act_cmp.setShortcut(QKeySequence("Ctrl+Alt+Shift+V"))
        act_cmp.setObjectName("actComparePdfs")
        act_cmp.setToolTip(
            "Dokumentvergleich: Side-by-Side, Drag-and-Drop, Sync-Scroll, "
            "Diff-Highlight — 2.6.19"
        )
        self._bind_pdf_action(act_cmp, self._compare_pdfs)
        m_pdf.addAction(act_cmp)
        act_ann_search = QAction("Annotation-Suche (offene Docs)…", self)
        act_ann_search.setShortcut(QKeySequence("Ctrl+Shift+F3"))
        act_ann_search.setToolTip(
            "Volltext Sidecar; Treffer klickbar (Doc+Seite); Case/Regex — 1.4.1"
        )
        self._bind_pdf_action(act_ann_search, self._annotation_search_open_docs)
        m_pdf.addAction(act_ann_search)
        act_sec = QAction("Verschlüsselung & Rechte…", self)
        act_sec.setShortcut(QKeySequence("Ctrl+Alt+Shift+P"))
        act_sec.setToolTip(
            "Passwortschutz AES-256, Rechte (Druck/Kopieren/…), "
            "setzen/entfernen — 2.6.7"
        )
        self._bind_pdf_action(act_sec, self._pdf_security_dialog)
        m_pdf.addAction(act_sec)
        act_esign = QAction("Digitale Signatur (eIDAS)…", self)
        act_esign.setObjectName("actionPdfESign")
        act_esign.setShortcut(QKeySequence("Ctrl+Alt+Shift+G"))
        act_esign.setToolTip(
            "Offizielle/digitale Signatur — Zertifikat AES/QES-Pfad, SES-Stempel — 2.6.22"
        )
        self._bind_pdf_action(act_esign, self._run_esign_dialog)
        m_pdf.addAction(act_esign)
        act_para = QAction("Absatz hervorheben", self)
        act_para.setShortcut(QKeySequence("Ctrl+Alt+Shift+H"))
        act_para.setToolTip(
            "Highlight ganzer Textabsätze (nicht nur freie Rechtecke) — 2.6.10"
        )
        self._bind_pdf_action(
            act_para, lambda: self.pdf_view._toggle_paragraph_highlight(True)
        )
        m_pdf.addAction(act_para)
        act_pw = QAction("PDF verschlüsseln…", self)
        act_pw.setToolTip(
            "Stärke-Hinweis; AES-256; Rechte; leeres PW abgelehnt; "
            "nach Erfolg neu laden — 2.6.7 / 1.6.1"
        )
        self._bind_pdf_action(act_pw, self._set_pdf_password)
        m_pdf.addAction(act_pw)
        act_pw_rm = QAction("PDF entschlüsseln…", self)
        act_pw_rm.setToolTip("Passwort entfernen; leeres PW abgelehnt; nach Erfolg neu laden — 1.6.1")
        self._bind_pdf_action(act_pw_rm, self._remove_pdf_password)
        m_pdf.addAction(act_pw_rm)
        act_stats = QAction("Dokument-Statistik…", self)
        act_stats.setToolTip(
            "Refresh; Auto-Update Doc-Wechsel; Wörter nur Textschicht sonst „—“ — 1.6.1"
        )
        self._bind_pdf_action(act_stats, self._show_doc_stats)
        m_pdf.addAction(act_stats)
        act_compress = QAction("PDF komprimieren / Downsample…", self)
        act_compress.setToolTip(
            "Seiten rastern (pypdfium2), optional Downsample, JPEG → neues File (pikepdf) — 2.3.0"
        )
        self._bind_pdf_action(act_compress, self._compress_pdf_images)
        m_pdf.addAction(act_compress)
        act_preflight = QAction("Preflight (Druckprüfung)…", self)
        act_preflight.setObjectName("actPreflight")
        act_preflight.setToolTip(
            "Fehlende Schriften, niedrige Bildauflösung, Bleed — 2.6.18"
        )
        self._bind_pdf_action(act_preflight, self._run_preflight)
        m_pdf.addAction(act_preflight)
        act_bleed = QAction("Anschnitt / Bleed setzen…", self)
        act_bleed.setObjectName("actBleed")
        act_bleed.setToolTip("BleedBox/TrimBox für Druck — 2.6.18")
        self._bind_pdf_action(act_bleed, self._apply_bleed_dialog)
        m_pdf.addAction(act_bleed)
        act_layers = QAction("Dokument-Ebenen…", self)
        act_layers.setObjectName("actDocLayers")
        act_layers.setToolTip(
            "Hintergrund / Bilder / Text — Rahmen-Ebenen — 2.6.18"
        )
        self._bind_pdf_action(act_layers, self._show_doc_layers)
        m_pdf.addAction(act_layers)
        act_bake_links = QAction("Link-Annotationen in PDF backen…", self)
        act_bake_links.setToolTip(
            "Sidecar-URL-Links als native PDF Link-Annotationen speichern — 2.3.0"
        )
        self._bind_pdf_action(act_bake_links, self._bake_uri_links)
        m_pdf.addAction(act_bake_links)
        act_meta = QAction("Metadaten bearbeiten…", self)
        self._bind_pdf_action(act_meta, self._edit_pdf_metadata)
        m_pdf.addAction(act_meta)
        act_doc_tags = QAction("Dokument-Tags…", self)
        act_doc_tags.setToolTip(
            "Globale Dokument-Tags (ildtags-v1) für Welcome/Recent-Filter — 2.5.0"
        )
        self._bind_pdf_action(act_doc_tags, self._edit_doc_tags)
        m_pdf.addAction(act_doc_tags)
        act_sanitize = QAction("PDF bereinigen…", self)
        act_sanitize.setToolTip("PDF neu speichern; optional Metadaten entfernen")
        self._bind_pdf_action(act_sanitize, self._sanitize_pdf)
        m_pdf.addAction(act_sanitize)
        act_forms = QAction("Formularfelder ausfüllen…", self)
        act_forms.setToolTip("Bestehende AcroForm-Felder lesen und schreiben")
        self._bind_pdf_action(act_forms, self._edit_pdf_form_fields)
        m_pdf.addAction(act_forms)
        act_attach = QAction("Anhänge…", self)
        act_attach.setToolTip(
            "Eingebettete PDF-Anhänge listen, extrahieren und hinzufügen (pikepdf) — 1.9.0"
        )
        self._bind_pdf_action(act_attach, self._pdf_attachments)
        m_pdf.addAction(act_attach)
        act_portfolio = QAction("PDF-Portfolio…", self)
        act_portfolio.setToolTip(
            "Portfolio erstellen/öffnen (pikepdf Attachments + Collection) — 2.0.0"
        )
        self._bind_pdf_action(act_portfolio, self._pdf_portfolio)
        m_pdf.addAction(act_portfolio)
        act_stamp_lib = QAction("Stempel-Bibliothek (Bilder)…", self)
        act_stamp_lib.setToolTip(
            "Eigene Stempel-Bilder verwalten und als Sidecar-Stempel setzen — 1.9.0"
        )
        self._bind_pdf_action(act_stamp_lib, self._stamp_image_library)
        m_pdf.addAction(act_stamp_lib)
        act_ann_tmpl = QAction("Annotation-Vorlagen…", self)
        act_ann_tmpl.setToolTip(
            "Stempel/Highlight-Styles speichern/laden (ildtmpl-v1) — 2.4.0"
        )
        self._bind_pdf_action(act_ann_tmpl, self._open_ann_templates)
        m_pdf.addAction(act_ann_tmpl)
        act_psize = QAction("Seitengröße / Zuschneiden…", self)
        self._bind_pdf_action(act_psize, self._pdf_page_size)
        m_pdf.addAction(act_psize)
        act_goto_page = QAction("Gehe zu Seite…", self)
        act_goto_page.setShortcut(QKeySequence("Ctrl+Shift+G"))
        act_goto_page.setToolTip("Seitennummer eingeben und springen (auch Ctrl+G im PDF)")
        self._bind_pdf_action(act_goto_page, self._goto_page)
        m_pdf.addAction(act_goto_page)
        act_page_labels = QAction("Seitenbeschriftungen…", self)
        act_page_labels.setToolTip(
            "Benutzerdefinierte Labels — Range-Editor · Import PDF · Reset arabisch 1… — 2.2.1"
        )
        self._bind_pdf_action(act_page_labels, lambda: self.pdf_view.edit_page_labels())
        m_pdf.addAction(act_page_labels)
        act_doc_hist = QAction("Dokument-Historie…", self)
        act_doc_hist.setToolTip(
            "Dokument-Historie-Panel: letzte 50 · Filter Aktionstyp · Export JSON — 2.2.1"
        )
        self._bind_pdf_action(act_doc_hist, lambda: self.pdf_view.show_doc_history())
        m_pdf.addAction(act_doc_hist)
        m_pdf.addSeparator()
        for title, slot in [
            ("Annotationen speichern (Sidecar)", lambda: self.pdf_view.save_annotations()),
            ("Annotationen speichern unter…", lambda: self.pdf_view.save_annotations_as()),
            ("Annotationen laden", self._pdf_reload_annotations_menu),
            ("Annotationen als JSON exportieren…", lambda: self.pdf_view.export_annotations_json()),
            (
                "Annotationen exportieren (JSON / Flatten)…",
                lambda: self.pdf_view.export_annotations_json_flatten(),
            ),
            ("Annotationen als CSV exportieren…", lambda: self.pdf_view.export_annotations_csv()),
            (
                "Messwerte als CSV exportieren…",
                lambda: self.pdf_view.export_measures_csv(),
            ),
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
                "PDF-Kommentare importieren (native)…",
                lambda: self.pdf_view.import_native_pdf_comments(),
            ),
            (
                "Annotation-Duplikate finden / zusammenführen…",
                lambda: self.pdf_view.merge_duplicate_annotations(),
            ),
        ]:
            a = QAction(title, self)
            self._bind_pdf_action(a, slot)
            m_pdf.addAction(a)
        act_cycle_color = QAction("Annotation-Farbe Palette-Zyklus", self)
        act_cycle_color.setShortcut(QKeySequence("Ctrl+Shift+C"))
        act_cycle_color.setToolTip("Nächste Highlight-Farbe aus der festen Palette")
        self._bind_pdf_action(act_cycle_color, self._pdf_cycle_ann_color_menu)
        m_pdf.addAction(act_cycle_color)
        act_rand_color = QAction("Annotation-Farbe randomisieren", self)
        act_rand_color.setShortcut(QKeySequence("Ctrl+Alt+Shift+C"))
        act_rand_color.setToolTip("Zufällige Highlight-Farbe aus der Palette")
        self._bind_pdf_action(act_rand_color, self._pdf_randomize_ann_color_menu)
        m_pdf.addAction(act_rand_color)
        m_pdf.addSeparator()
        for title, slot in [
            ("Lesezeichen hinzufügen…", self._outline_add),
            ("Lesezeichen löschen", self._outline_delete),
            ("Seite drehen 90° ⟳", lambda: self.pdf_view.rotate_current(90)),
            ("Seite drehen −90° ⟲", lambda: self.pdf_view.rotate_current(-90)),
            ("Stempel 90° drehen ↻", self._pdf_rotate_stamp_menu),
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
            ("Seitenmanagement…", lambda: self.pdf_view.page_manage_dialog()),
            ("Scannen / Import…", lambda: self._run_scan_import()),
            ("Drucker & Scanner…", lambda: self._show_devices_dialog()),
            ("Text bearbeiten…", lambda: self.pdf_view.inline_text_edit_dialog()),
            (
                "Auswahl → Text bearbeiten",
                lambda: self.pdf_view.edit_inline_text_selection(),
            ),
            ("Objekt bearbeiten…", self._pdf_object_edit_menu),
            (
                "Objekt-Dialog…",
                self._pdf_object_transform_menu,
            ),
            ("Formularfelder…", lambda: self.pdf_view.form_field_dialog()),
            (
                "Formularfeld anlegen…",
                lambda: self.pdf_view.form_field_create_dialog(),
            ),
            (
                "Formularfelder erkennen…",
                lambda: self.pdf_view.form_field_detect_dialog(),
            ),
            ("Seiten neu anordnen…", lambda: self.pdf_view.reorder_dialog()),
            ("Seite als Bild exportieren…", lambda: self.pdf_view.extract_page_as_image()),
            ("Seiten als Bilder exportieren…", lambda: self.pdf_view.export_pages_as_images()),
            ("Bild als neue Seite…", lambda: self.pdf_view.insert_image_page()),
            ("Seite drucken…", lambda: self.pdf_view.print_current_page()),
            ("Dokument drucken…", lambda: self.pdf_view.print_document()),
            ("PDF als Kopie speichern…", lambda: self.pdf_view.save_pdf_as_copy()),
        ]:
            a = QAction(title, self)
            if title == "Seitenmanagement…":
                a.setToolTip(
                    "Seiten ordnen (Drag), einfügen, drehen, löschen, "
                    "aus anderem PDF zusammenfügen — 2.6.5"
                )
                a.setShortcut(QKeySequence("Ctrl+Shift+M"))
            if title == "Scannen / Import…":
                a.setToolTip(
                    "Scanner oder Bilder importieren · Tesseract-OCR · "
                    "Geräte → Scannen… · Toolbar Scan… — 2.6.54"
                )
                a.setShortcuts(
                    [QKeySequence("Ctrl+Shift+S"), QKeySequence("Ctrl+Alt+Shift+I")]
                )
                a.setObjectName("actScanImport")
            if title == "Drucker & Scanner…":
                a.setToolTip(
                    "Lokale und Netzwerk-Drucker/Scanner auflisten · "
                    "Menü Geräte → Geräte erkennen… — 2.6.41"
                )
                a.setObjectName("actDevicesDialog")
            if title == "Text bearbeiten…":
                a.setToolTip(
                    "Inline-Textbearbeitung: Klick/Doppelklick auf Text · "
                    "Schriftart/Größe/Farbe aus Kontext · Reflow — 2.6.5"
                )
                a.setShortcut(QKeySequence("Ctrl+Alt+Shift+E"))
            if title == "Auswahl → Text bearbeiten":
                a.setToolTip(
                    "Aktuelle Textauswahl inline ändern/löschen (Formatabgleich) — 2.6.5"
                )
            if title == "Objekt bearbeiten…":
                a.setToolTip(
                    "Objektmanipulation: Bild/Vektor/Tabelle wählen, "
                    "verschieben/skalieren/spiegeln/ersetzen — 2.6.5"
                )
                a.setShortcut(QKeySequence("Ctrl+Alt+Shift+O"))
            if title == "Objekt-Dialog…":
                a.setToolTip(
                    "Transform-Dialog für aktuelle Objektauswahl (Flip/Ersetzen) — 2.6.5"
                )
            if title == "Formularfelder…":
                a.setToolTip(
                    "AcroForm: ausfüllen, anlegen, löschen, erkennen — 2.6.6"
                )
                a.setShortcut(QKeySequence("Ctrl+Alt+Shift+K"))
            if title == "Formularfeld anlegen…":
                a.setToolTip(
                    "Werkzeug: Rechteck ziehen → Text/Checkbox/Dropdown — 2.6.6"
                )
            if title == "Formularfelder erkennen…":
                a.setToolTip(
                    "Heuristik Labels „:“ / ____ / [ ] → Felder anlegen — 2.6.6"
                )
            if title == "Verschlüsselung & Rechte…":
                a.setToolTip(
                    "AES-256 Passwortschutz · Rechte Druck/Kopieren/Ändern · "
                    "setzen/entfernen — 2.6.7"
                )
                a.setShortcut(QKeySequence("Ctrl+Alt+Shift+P"))
            self._bind_pdf_action(a, slot)
            m_pdf.addAction(a)
        # Batch Drehen/Spiegeln Shortcuts (Auswahl oder aktuelle Seite) — 1.8.1
        m_pdf.addSeparator()
        act_batch_r90 = QAction("Auswahl 90° rechts drehen", self)
        act_batch_r90.setShortcut(QKeySequence("Ctrl+Alt+Right"))
        act_batch_r90.setToolTip(
            "Thumbnail-Auswahl oder aktuelle Seite 90° rechts (Batch) — 1.8.1"
        )
        self._bind_pdf_action(act_batch_r90, lambda: self._batch_rotate_selection(90))
        m_pdf.addAction(act_batch_r90)
        act_batch_l90 = QAction("Auswahl 90° links drehen", self)
        act_batch_l90.setShortcut(QKeySequence("Ctrl+Alt+Left"))
        act_batch_l90.setToolTip(
            "Thumbnail-Auswahl oder aktuelle Seite 90° links (Batch) — 1.8.1"
        )
        self._bind_pdf_action(act_batch_l90, lambda: self._batch_rotate_selection(-90))
        m_pdf.addAction(act_batch_l90)
        act_batch_180 = QAction("Auswahl 180° drehen", self)
        act_batch_180.setShortcut(QKeySequence("Ctrl+Alt+Up"))
        act_batch_180.setToolTip(
            "Thumbnail-Auswahl oder aktuelle Seite 180° (Batch) — 1.8.1"
        )
        self._bind_pdf_action(act_batch_180, lambda: self._batch_rotate_selection(180))
        m_pdf.addAction(act_batch_180)
        act_batch_fh = QAction("Auswahl horizontal spiegeln", self)
        act_batch_fh.setShortcut(QKeySequence("Ctrl+Alt+H"))
        act_batch_fh.setToolTip(
            "Thumbnail-Auswahl oder aktuelle Seite horizontal spiegeln — 1.8.1"
        )
        self._bind_pdf_action(
            act_batch_fh,
            lambda: self._batch_flip_selection(horizontal=True, vertical=False),
        )
        m_pdf.addAction(act_batch_fh)
        act_batch_fv = QAction("Auswahl vertikal spiegeln", self)
        act_batch_fv.setShortcut(QKeySequence("Ctrl+Alt+Shift+V"))
        act_batch_fv.setToolTip(
            "Thumbnail-Auswahl oder aktuelle Seite vertikal spiegeln — 1.8.1"
        )
        self._bind_pdf_action(
            act_batch_fv,
            lambda: self._batch_flip_selection(horizontal=False, vertical=True),
        )
        m_pdf.addAction(act_batch_fv)
        act_page_hist = QAction("Seiten-Historie (Undo)…", self)
        act_page_hist.setShortcut(QKeySequence("Ctrl+Shift+H"))
        act_page_hist.setToolTip("Gelöschte/gedrehte Seiten aus dem Undo-Stack wiederherstellen")
        self._bind_pdf_action(act_page_hist, lambda: self.pdf_view.show_page_ops_history())
        m_pdf.addAction(act_page_hist)
        act_page_fav = QAction("Seite als Favorit umschalten", self)
        act_page_fav.setShortcut(QKeySequence("Ctrl+Shift+F"))
        act_page_fav.setToolTip("Aktuelle PDF-Seite als Favorit markieren/entfernen")
        self._bind_pdf_action(act_page_fav, lambda: self.pdf_view.toggle_page_favorite())
        m_pdf.addAction(act_page_fav)
        act_page_fav_jump = QAction("Seiten-Favoriten…", self)
        act_page_fav_jump.setShortcut(QKeySequence("Ctrl+Alt+F"))
        act_page_fav_jump.setToolTip("Zu markierten Favoriten-Seiten springen")
        self._bind_pdf_action(act_page_fav_jump, lambda: self.pdf_view.show_page_favorites())
        m_pdf.addAction(act_page_fav_jump)
        act_fav_export = QAction("Seiten-Favoriten als JSON exportieren…", self)
        act_fav_export.setToolTip("Favoritenliste als ildfav-v1 JSON speichern")
        self._bind_pdf_action(act_fav_export, lambda: self.pdf_view.export_page_favorites_json())
        m_pdf.addAction(act_fav_export)
        act_fav_import = QAction("Seiten-Favoriten aus JSON importieren…", self)
        act_fav_import.setToolTip("Favoritenliste aus JSON laden (ersetzen oder zusammenführen)")
        self._bind_pdf_action(act_fav_import, lambda: self.pdf_view.import_page_favorites_json())
        m_pdf.addAction(act_fav_import)
        act_global_fav = QAction("Zur Lesezeichen-Leiste hinzufügen", self)
        act_global_fav.setShortcut(QKeySequence("Ctrl+Alt+Shift+B"))
        act_global_fav.setToolTip(
            "Aktuelle Seite in globale Favoriten (ildfav-v1) — Schnelljump — 1.7.0"
        )
        self._bind_pdf_action(act_global_fav, self._add_current_to_global_favorites)
        m_pdf.addAction(act_global_fav)
        act_gf_export = QAction("Lesezeichen-Leiste als JSON exportieren…", self)
        act_gf_export.setToolTip("Globale Favoriten als ildfav-v1 JSON speichern — 1.7.1")
        self._bind_pdf_action(act_gf_export, self._export_global_favorites_json)
        m_pdf.addAction(act_gf_export)
        act_gf_import = QAction("Lesezeichen-Leiste aus JSON importieren…", self)
        act_gf_import.setToolTip(
            "Globale Favoriten aus ildfav-v1 JSON laden (ersetzen oder zusammenführen) — 1.7.1"
        )
        self._bind_pdf_action(act_gf_import, self._import_global_favorites_json)
        m_pdf.addAction(act_gf_import)
        act_ol_import = QAction("Bookmarks aus PDF-Outlines importieren…", self)
        act_ol_import.setToolTip(
            "PDF-Outline → Seiten-Favoriten (Bookmarks) importieren — 1.3.0"
        )
        self._bind_pdf_action(act_ol_import, self._import_bookmarks_from_outline)
        m_pdf.addAction(act_ol_import)
        act_ol_export = QAction("Bookmarks als PDF-Outlines exportieren…", self)
        act_ol_export.setToolTip(
            "Seiten-Favoriten (Bookmarks) als PDF-Outline schreiben — 1.3.0"
        )
        self._bind_pdf_action(act_ol_export, self._export_bookmarks_to_outline)
        m_pdf.addAction(act_ol_export)
        m_pdf.addSeparator()
        for title, slot in [
            ("PDF-Text → Overlay…", self._pdf_import_text_overlays_menu),
            ("Text-Overlays einbrennen…", lambda: self.pdf_view.bake_overlays()),
            ("Text dieser Seite → Editor", self._extract_page_text_to_editor),
            ("Gesamten PDF-Text → Editor", self._extract_all_text_to_editor),
            ("Seitenbild → Editor", self._insert_page_image_to_editor),
            ("Alle Seitenbilder → Editor", self._insert_all_page_images_to_editor),
            ("Redactions anwenden…", lambda: self.pdf_view.bake_redactions()),
            (
                "Echt schwärzen…",
                lambda: self.pdf_view.apply_true_redactions(),
            ),
            (
                "Auswahl → Schwärzung",
                lambda: self.pdf_view.redactions_from_text_selection(),
            ),
            ("Schwärzungs-Annotationen löschen…", lambda: self.pdf_view.clear_redactions()),
            (
                "Signaturfeld setzen…",
                self._place_signature_field_menu,
            ),
            (
                "Signatur (Bild) einfügen…",
                self._insert_signature_image_menu,
            ),
        ]:
            a = QAction(title, self)
            if title == "Echt schwärzen…":
                a.setToolTip(
                    "Unwiderrufliches Schwärzen: Content-Stream/Textschicht entfernen "
                    "+ optional Metadaten — 2.6.5"
                )
            elif title == "Auswahl → Schwärzung":
                a.setToolTip(
                    "Textauswahl als Schwärzungs-Rechtecke markieren (Sidecar) — 2.6.5"
                )
            self._bind_pdf_action(a, slot)
            m_pdf.addAction(a)

        try:
            from instantlensdoc.ui.menu_click import prepare_menu_for_clicks

            prepare_menu_for_clicks(m_pdf)
        except Exception:
            pass
        try:
            m_pdf.aboutToShow.connect(self._on_pdf_menu_about_to_show)
        except Exception:
            pass

        # Geräte-Menü idempotent nachziehen — 2.6.51
        self._ensure_devices_menu(mb)

        act_field = QAction("Ersatzzeichen…", self)
        act_field.setObjectName("actFieldToken")
        act_field.setToolTip(
            "Felder: Datum, Uhrzeit, Seite, Seitenanzahl, Dateiname, Autor und eigene Werte"
        )
        act_field.triggered.connect(self._field_token_dialog)
        self._field_token_action = act_field

        m_ins = mb.addMenu("&Einfügen")
        a = QAction("Textrahmen", self)
        a.triggered.connect(self._add_text_frame)
        m_ins.addAction(a)
        a = QAction("Verketteten Textrahmen…", self)
        a.triggered.connect(self._add_chained_frame)
        m_ins.addAction(a)
        a = QAction("Spalten-Rahmen…", self)
        a.setToolTip("Verkettete Spalten-Textrahmen — 2.6.12")
        a.triggered.connect(self._add_column_frames)
        m_ins.addAction(a)
        a = QAction("Rahmen verschieben…", self)
        a.setToolTip("Text-/Bildrahmen verschieben — 2.6.12")
        a.triggered.connect(self._move_frame_dialog)
        m_ins.addAction(a)
        a = QAction("Rahmen skalieren…", self)
        a.setToolTip("Text-/Bildrahmen skalieren — 2.6.12")
        a.triggered.connect(self._resize_frame_dialog)
        m_ins.addAction(a)
        a = QAction("Bild einfügen…", self)
        a.triggered.connect(self._insert_image)
        m_ins.addAction(a)
        a = QAction("Form einfügen…", self)
        a.setObjectName("actInsertShape")
        a.setToolTip("Formrahmen (Rechteck/Ellipse/…) — 2.6.26")
        a.triggered.connect(self._insert_shape_frame)
        m_ins.addAction(a)
        a = QAction("Video-Platzhalter (URL)…", self)
        a.setObjectName("actInsertVideo")
        a.setToolTip("Online-Video als Platzhalter mit URL — 2.6.26")
        a.triggered.connect(self._insert_video_placeholder)
        m_ins.addAction(a)
        a = QAction("Bild skalieren…", self)
        a.setObjectName("actScaleImage")
        a.setToolTip("Bild-/Formrahmen skalieren — 2.6.26")
        a.triggered.connect(self._scale_image_frame)
        m_ins.addAction(a)
        a = QAction("Bild zuschneiden…", self)
        a.setObjectName("actCropImage")
        a.setToolTip("Bild zuschneiden (relative Ränder) — 2.6.26")
        a.triggered.connect(self._crop_image_frame)
        m_ins.addAction(a)
        a = QAction("Textumfluss um Bildrahmen…", self)
        a.setToolTip("Text fließt um Bild-/Formrahmen (bounding_box/contour/jump) — 2.6.13")
        a.triggered.connect(self._set_image_text_wrap)
        m_ins.addAction(a)
        a = QAction("Hyperlink…", self)
        a.setObjectName("actHyperlink")
        a.setShortcut(QKeySequence("Ctrl+Shift+K"))
        a.setToolTip("Text mit URL oder Dokumentziel verknüpfen — Ctrl+Shift+K — 2.6.26")
        a.triggered.connect(self._insert_hyperlink_dialog)
        m_ins.addAction(a)
        a = QAction("Tabelle einfügen…", self)
        a.setShortcut(QKeySequence("Ctrl+Alt+Shift+8"))
        a.setToolTip("Markdown-Tabelle erstellen (Zeilen/Spalten) — Ctrl+Alt+Shift+8 — 2.6.54")
        a.triggered.connect(self._insert_table_dialog)
        m_ins.addAction(a)
        a = QAction("Tabelle formatieren…", self)
        a.setToolTip("Ausrichtung/Stil/Rahmen der aktuellen Tabelle — 2.6.14")
        a.triggered.connect(self._format_table_dialog)
        m_ins.addAction(a)
        a = QAction("Tabelle sortieren…", self)
        a.setToolTip("Aktuelle Tabelle nach Spalte sortieren — 2.6.14")
        a.triggered.connect(self._sort_table_dialog)
        m_ins.addAction(a)
        a = QAction("Zahlen/Daten importieren (CSV/Excel)…", self)
        a.setToolTip("CSV oder .xlsx in Tabelle übernehmen — 2.6.14")
        a.triggered.connect(self._import_table_data)
        m_ins.addAction(a)
        a = QAction("Musterseite anwenden…", self)
        a.setToolTip(
            "Kopf-/Fußzeile + Seitenzahlen über Seiten (Musterseite) — 2.6.12"
        )
        a.triggered.connect(self._apply_master_page_dialog)
        m_ins.addAction(a)
        m_ins.addSeparator()
        m_ins.addAction(act_field)

        m_extra = mb.addMenu("E&xtras")
        a = QAction("Einstellungen…", self)
        a.triggered.connect(self._settings)
        m_extra.addAction(a)
        m_extra.addSeparator()
        a = QAction("Stapelverarbeitung (Batch)…", self)
        a.setToolTip(
            "Viele Dateien: Bilder→PDF, OCR, PDFs konvertieren/"
            "Wasserzeichen/komprimieren/verschlüsseln — 2.6.22"
        )
        a.triggered.connect(self._batch_convert)
        m_extra.addAction(a)
        a = QAction("Digitale Signatur (eIDAS)…", self)
        a.setObjectName("actionESign")
        a.setToolTip(
            "Zertifikatsbasierte Signatur (AES/QES-Pfad) bzw. SES — 2.6.22"
        )
        a.triggered.connect(self._run_esign_dialog)
        m_extra.addAction(a)
        a = QAction("Batch-Umbenennen (offene Tabs)…", self)
        a.setToolTip(
            "Offene Tabs Template {stem}_{n}; Dry-Run, Kollision, Undo-Log — 1.4.1"
        )
        a.triggered.connect(self._batch_rename_tabs)
        m_extra.addAction(a)
        a = QAction("OCR (Bild/PDF-Seite)…", self)
        a.triggered.connect(self._run_ocr)
        m_extra.addAction(a)
        a = QAction("OCR gesamtes PDF…", self)
        a.setToolTip(
            "Batch-OCR: Sprach-Preset + DPI 150/300 + optional von–bis "
            "→ neue Textdatei-Tab — 1.1.2"
        )
        a.triggered.connect(self._run_ocr_document)
        m_extra.addAction(a)
        a = QAction("OCR Region (Rechteck)…", self)
        a.setToolTip(
            "Rechteck auf der PDF-Seite wählen → nur Region OCR → Text-Tab — 2.5.0"
        )
        a.triggered.connect(self._run_ocr_region)
        m_extra.addAction(a)
        a = QAction("Handschriftenerkennung…", self)
        a.setObjectName("actHandwritingOcr")
        a.setToolTip(
            "Basis-Handschriftenerkennung (Tesseract PSM) — Bild/PDF-Seite → Text — 2.6.18"
        )
        a.triggered.connect(self._run_ocr_handwriting)
        m_extra.addAction(a)
        a = QAction("In Word-Suite öffnen/übernehmen…", self)
        a.setObjectName("actOcrWordSuite")
        a.setShortcut("Ctrl+Alt+Shift+W")
        a.setToolTip(
            "OCR-/Layout-Ergebnis oder *.ildocr.*-Sidecar als editierbares "
            "Word-Suite-Dokument übernehmen (Blöcke/Lesereihenfolge) — 2.6.15"
        )
        a.triggered.connect(self._ocr_word_suite_action)
        m_extra.addAction(a)
        a = QAction("Dokument erstellen… (KI-Wizard)", self)
        a.setObjectName("actKiDocumentWizard")
        a.setShortcut("Ctrl+Alt+Shift+Q")
        a.setToolTip(
            "Geführte KI-Standardabläufe: Formular, Anschreiben, Kaufvertrag, "
            "Rechnung — isoliert, kein freier Chat — 2.6.16"
        )
        a.triggered.connect(self._ki_document_wizard_action)
        m_extra.addAction(a)
        a = QAction("Formulargenerator…", self)
        a.triggered.connect(self._forms)
        m_extra.addAction(a)
        m_extra.addSeparator()
        a = QAction("Gemeinsames Review / Cloud-Ordner…", self)
        a.setObjectName("actCloudSharedReview")
        a.setToolTip(
            "Shared Review: Freigabeordner-Sync + optionaler Endpoint — 2.6.23"
        )
        a.triggered.connect(self._show_shared_review_dialog)
        m_extra.addAction(a)
        a = QAction("Stylus / Stift…", self)
        a.setObjectName("actStylusTool")
        a.setToolTip("Stylus-Druck + Palm-Rejection aktivieren (Freihand) — 2.6.26")
        a.triggered.connect(self._activate_stylus_tool)
        m_extra.addAction(a)
        a = QAction("3D-Extrusion…", self)
        a.setObjectName("actExtrude3d")
        a.setToolTip("3D-Extrusion auf DTP-Rahmen (QPainterPath) — 2.6.54")
        a.triggered.connect(self._show_extrude3d_dialog)
        m_extra.addAction(a)
        a = QAction("Script-/Plugin-Hooks…", self)
        a.setObjectName("actPluginHooks")
        a.setToolTip("User-Hooks on_open/on_save/on_scan + Menü-Plugins — 2.6.54")
        a.triggered.connect(self._show_hooks_info)
        m_extra.addAction(a)
        a = QAction("KI-Assistent…", self)
        a.setObjectName("actKiAssistant")
        a.setToolTip("Zusammenfassen, umformulieren, übersetzen — Offline ohne Schlüssel")
        a.triggered.connect(self._show_ki_assistant)
        m_extra.addAction(a)
        a = QAction("Intelligente Formerkennung", self)
        a.setObjectName("actShapeRecognize")
        a.setToolTip("Tinte auf dem DTP-Canvas als Form erkennen — 2.6.54")
        a.triggered.connect(self._run_shape_recognition)
        m_extra.addAction(a)
        a = QAction("Variable Fonts…", self)
        a.setObjectName("actVariableFonts")
        a.setToolTip("Achsen wght/wdth/slnt, System- und Windows-Fonts — 2.6.54")
        a.triggered.connect(self._show_variable_fonts)
        m_extra.addAction(a)
        a = QAction("Envelope Distort…", self)
        a.setObjectName("actEnvelopeDistort")
        a.setToolTip("4-Punkt-Envelope auf DTP-Rahmen — 2.6.54")
        a.triggered.connect(self._apply_envelope_distort)
        m_extra.addAction(a)
        a = QAction("E-Signatur PAdES / QES…", self)
        a.setObjectName("actPadesSign")
        a.setToolTip("PAdES-B mit PKCS#12; QES nur mit QTSP-Zertifikat — 2.6.54")
        a.triggered.connect(self._show_pades_dialog)
        m_extra.addAction(a)
        a = QAction("Text auf Pfad…", self)
        a.setObjectName("actTextOnPath")
        a.setToolTip("DTP: Text entlang Ellipse oder Linie — 2.6.54")
        a.triggered.connect(self._dtp_text_on_path)
        m_extra.addAction(a)
        a = QAction("Text in Pfade umwandeln", self)
        a.setObjectName("actTextToOutlines")
        a.setToolTip("DTP: Glyphen als QPainterPath — 2.6.54")
        a.triggered.connect(self._dtp_text_to_outlines)
        m_extra.addAction(a)
        a = QAction("Schnittmaske", self)
        a.setObjectName("actClipMask")
        a.setToolTip("DTP: Inhalt mit Formrahmen clippen — 2.6.54")
        a.triggered.connect(self._dtp_clip_mask)
        m_extra.addAction(a)
        a = QAction("Füllung / Live-Effekt…", self)
        a.setObjectName("actLiveFill")
        a.setToolTip("DTP: Verlauf, Deckkraft, Schlagschatten — 2.6.54")
        a.triggered.connect(self._dtp_live_fill)
        m_extra.addAction(a)
        a = QAction("Glyphen-Palette…", self)
        a.setObjectName("actGlyphPalette")
        a.setToolTip("Unicode-Glyphen der Systemschrift in Textrahmen — 2.6.54")
        a.triggered.connect(self._dtp_glyph_palette)
        m_extra.addAction(a)
        try:
            from instantlensdoc.features.plugins import iter_menu_plugins

            for spec in iter_menu_plugins():
                title = str(spec.get("title") or "").strip()
                cb = spec.get("callback")
                if title and callable(cb):
                    act_p = QAction(title, self)
                    act_p.triggered.connect(cb)
                    m_extra.addAction(act_p)
        except Exception:
            pass

        m_help = mb.addMenu("&Hilfe")
        a = QAction("Erste Schritte…", self)
        a.setToolTip("Kurz-Wizard: Öffnen, Annotieren, Editor, 0.6-Highlights (4 Seiten)")
        a.triggered.connect(self._show_getting_started_wizard)
        m_help.addAction(a)
        a = QAction("Tastatur-Cheat-Sheet…", self)
        a.setShortcut(QKeySequence("F1"))
        a.setToolTip("Shortcut-Liste (DE) — F1 — 2.4.0")
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
        a = QAction("Jetzt prüfen…", self)
        a.setToolTip(
            "Update-Hinweis jetzt prüfen (lokal docs/VERSION / VERSION.txt; "
            "kein Auto-Download) — 1.7.1"
        )
        a.triggered.connect(lambda: self._check_updates(silent=False, force=True))
        m_help.addAction(a)
        # Alias für Abwärtskompatibilität / Erkennbarkeit
        a = QAction("Auf Updates prüfen…", self)
        a.setToolTip("Alias: Jetzt prüfen… — 1.7.1")
        a.triggered.connect(lambda: self._check_updates(silent=False, force=True))
        m_help.addAction(a)
        a = QAction("Lizenz…", self)
        a.triggered.connect(self._license)
        m_help.addAction(a)
        a = QAction("Info…", self)
        a.triggered.connect(lambda: AboutDialog(self).exec())
        m_help.addAction(a)
        self._install_format_and_window_menus(mb)
        self._install_editor_context_menu()
        self._sync_editor_only_actions()
        self._sync_menu_enablement()
        from instantlensdoc.ui.menu_click import apply_clickable_popup_menus

        apply_clickable_popup_menus(self)
        self._bind_ribbon_qactions()

    _FORMAT_MENU_TEXTS = frozenset(
        {
            "Fett",
            "Kursiv",
            "Unterstrichen",
            "Durchgestrichen",
            "Schriftart…",
            "Schriftgröße…",
            "Schriftfarbe…",
            "Texthervorhebung…",
            "Hintergrundfarbe…",
            "Formatierungen löschen",
            "Aufzählungszeichen",
            "Nummerierung",
            "Absatz…",
            "Absatz links",
            "Absatz zentriert",
            "Absatz rechts",
            "Absatz Blocksatz",
            "Zeilenabstand 1,5",
            "Zeilenabstand 1,15 (Standard)",
            "Laufweite +50 (Tracking)",
            "Durchschuss 1,5 (Leading)",
            "Initial / Drop Cap",
            "Groß-/Kleinschreibung umschalten",
            "Alles großschreiben",
            "Alles kleinschreiben",
            "Automatische Formatierung",
            "Einrückung erhöhen",
            "Einrückung verringern",
            "Auswahl markieren",
        }
    )
    _FORMAT_MENU_SUBS = frozenset({"Formatvorlagen", "Silbentrennung"})
    _ABSATZ_MENU_ORDER = (
        "Absatz…",
        None,
        "Absatz links",
        "Absatz zentriert",
        "Absatz rechts",
        "Absatz Blocksatz",
        None,
        "Aufzählungszeichen",
        "Nummerierung",
        "Einrückung erhöhen",
        "Einrückung verringern",
        None,
        "Zeilenabstand 1,5",
        "Zeilenabstand 1,15 (Standard)",
    )
    _FENSTER_MENU_TEXTS = frozenset(
        {
            "Fenster teilen (zwei Docs)",
            "Vertikaler Split (übereinander)",
            "Sync-Scroll (PDF-Tabs / Split)",
            "Zweites Dokument wählen…",
        }
    )

    @staticmethod
    def _qt_widget_alive(obj) -> bool:
        if obj is None:
            return False
        try:
            obj.objectName()
            return True
        except RuntimeError:
            return False

    @staticmethod
    def _snapshot_menu_actions(menu) -> list:
        """QAction-Liste sofort kopieren — PySide-Wrapper von QAction.menu() verfallen."""
        if menu is None:
            return []
        try:
            return list(menu.actions())
        except RuntimeError:
            return []

    def _install_format_and_window_menus(self, mb) -> None:
        """Klassische Menüs Format + Fenster (Aktionen geteilt, nicht verdoppelt)."""
        extra_act = help_act = None
        edit_acts: list = []
        view_acts: list = []
        for act in mb.actions():
            menu = act.menu() if hasattr(act, "menu") else None
            title = ""
            try:
                title = (menu.title() if menu is not None else act.text() or "")
            except Exception:
                title = act.text() or ""
            title = title.replace("&", "")
            if title in ("Bearbeiten", "Edit"):
                edit_acts = self._snapshot_menu_actions(menu)
            elif title in ("Ansicht", "View"):
                view_acts = self._snapshot_menu_actions(menu)
            elif title in ("Extras", "Extra"):
                extra_act = act
            elif title == "Hilfe":
                help_act = act

        m_format = QMenu("&Format", self)
        m_format.setObjectName("menuFormat")
        m_format.setToolTip("Zeichen- und Absatzformat — Auswahl oder ganzes Dokument")
        for act in edit_acts:
            if act.isSeparator():
                continue
            sub = act.menu() if hasattr(act, "menu") else None
            if sub is not None:
                st = (sub.title() or "").replace("&", "")
                if st in self._FORMAT_MENU_SUBS:
                    nm = m_format.addMenu(st)
                    for sa in self._snapshot_menu_actions(sub):
                        if sa.isSeparator():
                            nm.addSeparator()
                        else:
                            nm.addAction(sa)
                continue
            text = (act.text() or "").replace("&", "").strip()
            if text in self._FORMAT_MENU_TEXTS:
                m_format.addAction(act)

        m_absatz = QMenu("&Absatz", self)
        m_absatz.setObjectName("menuAbsatz")
        m_absatz.setToolTip(
            "Absatzdialog, Ausrichtung, Aufzählung/Nummerierung — Word-Suite/DOCX"
        )
        by_edit = {}
        styles_acts: list = []
        for act in edit_acts:
            if act.isSeparator():
                continue
            sub = act.menu() if hasattr(act, "menu") else None
            if sub is not None:
                st = (sub.title() or "").replace("&", "").strip()
                if st == "Formatvorlagen":
                    styles_acts = self._snapshot_menu_actions(sub)
                continue
            by_edit[(act.text() or "").replace("&", "").strip()] = act
        for text in self._ABSATZ_MENU_ORDER:
            if text is None:
                m_absatz.addSeparator()
                continue
            shared = by_edit.get(text)
            if shared is not None:
                m_absatz.addAction(shared)
        if styles_acts:
            nm = m_absatz.addMenu("Formatvorlagen")
            for sa in styles_acts:
                if sa.isSeparator():
                    nm.addSeparator()
                else:
                    nm.addAction(sa)
        m_absatz.addSeparator()
        act_ls10 = QAction("Zeilenabstand 1,0", self)
        act_ls10.setObjectName("actLineSpacing10")
        act_ls10.triggered.connect(lambda: self._set_paragraph_line_spacing(1.0))
        m_absatz.addAction(self._track_editor_action(act_ls10))
        act_ls20 = QAction("Zeilenabstand 2,0", self)
        act_ls20.setObjectName("actLineSpacing20")
        act_ls20.triggered.connect(lambda: self._set_paragraph_line_spacing(2.0))
        m_absatz.addAction(self._track_editor_action(act_ls20))
        act_ls_ex = QAction("Zeilenabstand genau…", self)
        act_ls_ex.setObjectName("actLineSpacingExact")
        act_ls_ex.triggered.connect(self._paragraph_format_dialog)
        m_absatz.addAction(self._track_editor_action(act_ls_ex))
        act_keep = QAction("Mit nächstem Absatz zusammenhalten", self)
        act_keep.setObjectName("actKeepWithNext")
        act_keep.triggered.connect(lambda: self._set_keep_with_next(True))
        m_absatz.addAction(self._track_editor_action(act_keep))
        act_widow = QAction("Absatzkontrolle (Witwen/Waisen)", self)
        act_widow.setObjectName("actWidowOrphan")
        act_widow.triggered.connect(lambda: self._set_widow_orphan(True))
        m_absatz.addAction(self._track_editor_action(act_widow))
        m_absatz.addSeparator()
        act_glyph = QAction("Aufzählungszeichen ändern…", self)
        act_glyph.setObjectName("actListGlyph")
        act_glyph.triggered.connect(self._change_list_glyph_dialog)
        m_absatz.addAction(self._track_editor_action(act_glyph))
        act_restart = QAction("Nummerierung neu beginnen", self)
        act_restart.setObjectName("actListRestart")
        act_restart.triggered.connect(self._restart_list_numbering)
        m_absatz.addAction(self._track_editor_action(act_restart))
        act_l_in = QAction("Listenebene erhöhen", self)
        act_l_in.setObjectName("actListIndent")
        act_l_in.triggered.connect(lambda: self._adjust_list_indent(+1))
        m_absatz.addAction(self._track_editor_action(act_l_in))
        act_l_out = QAction("Listenebene verringern", self)
        act_l_out.setObjectName("actListOutdent")
        act_l_out.triggered.connect(lambda: self._adjust_list_indent(-1))
        m_absatz.addAction(self._track_editor_action(act_l_out))
        m_absatz.addSeparator()
        act_vtop = QAction("Zelle oben", self)
        act_vtop.setObjectName("actCellAlignTop")
        act_vtop.triggered.connect(lambda: self._set_cell_vertical_align("top"))
        m_absatz.addAction(self._track_editor_action(act_vtop))
        act_vmiddle = QAction("Zelle mittig", self)
        act_vmiddle.setObjectName("actCellAlignMiddle")
        act_vmiddle.triggered.connect(lambda: self._set_cell_vertical_align("middle"))
        m_absatz.addAction(self._track_editor_action(act_vmiddle))
        act_vbottom = QAction("Zelle unten", self)
        act_vbottom.setObjectName("actCellAlignBottom")
        act_vbottom.triggered.connect(lambda: self._set_cell_vertical_align("bottom"))
        m_absatz.addAction(self._track_editor_action(act_vbottom))
        m_absatz.addSeparator()
        m_absatz.addAction(self._track_editor_action(self._field_token_action))
        self._absatz_menu = m_absatz
        self._editor_only_menus.append(m_absatz)

        m_seiten = QMenu("Seiten&layout", self)
        m_seiten.setObjectName("menuSeitenlayout")
        m_seiten.setToolTip(
            "Seitenformat-Picker und Ausrichtung für den Word-Suite-/DOCX-Editor"
        )
        if getattr(self, "_page_layout_action", None) is not None:
            m_seiten.addAction(self._page_layout_action)
        m_seiten.addSeparator()
        act_port = QAction("Hochformat", self)
        act_port.setObjectName("actPageLayoutPortrait")
        act_port.setToolTip("Seitenlayout Hochformat")
        act_port.triggered.connect(
            lambda: self._apply_editor_page_layout_pick(orientation="portrait")
        )
        m_seiten.addAction(self._track_editor_action(act_port))
        act_land = QAction("Querformat", self)
        act_land.setObjectName("actPageLayoutLandscape")
        act_land.setToolTip("Seitenlayout Querformat")
        act_land.triggered.connect(
            lambda: self._apply_editor_page_layout_pick(orientation="landscape")
        )
        m_seiten.addAction(self._track_editor_action(act_land))
        m_seiten.addSeparator()
        for preset, objn, label in (
            ("A4", "actPageLayoutA4", "A4"),
            ("US Letter", "actPageLayoutLetter", "US Letter"),
            ("US Legal", "actPageLayoutLegal", "Legal"),
        ):
            act_p = QAction(label, self)
            act_p.setObjectName(objn)
            act_p.setToolTip(f"Seitenformat {label}")
            act_p.triggered.connect(
                lambda _c=False, n=preset: self._apply_editor_page_layout_pick(preset=n)
            )
            m_seiten.addAction(self._track_editor_action(act_p))
        m_seiten.addSeparator()
        for n_col, lab in ((1, "1 Spalte"), (2, "2 Spalten"), (3, "3 Spalten")):
            act_c = QAction(lab, self)
            act_c.setObjectName(f"actPageLayoutColumns{n_col}")
            act_c.triggered.connect(
                lambda _c=False, k=n_col: self._apply_editor_page_layout_pick(columns=k)
            )
            m_seiten.addAction(self._track_editor_action(act_c))
        m_seiten.addSeparator()
        act_sec = QAction("Abschnittsumbruch einfügen", self)
        act_sec.setObjectName("actInsertSectionBreak")
        act_sec.triggered.connect(self._insert_section_break)
        m_seiten.addAction(self._track_editor_action(act_sec))
        act_hf = QAction("Kopf-/Fußzeile…", self)
        act_hf.setObjectName("actHeaderFooter")
        act_hf.setToolTip("Kopf- und Fußzeile als Dokument-Meta, nicht im Fließtext")
        act_hf.triggered.connect(self._header_footer_dialog)
        m_seiten.addAction(self._track_editor_action(act_hf))
        self._seitenlayout_menu = m_seiten
        self._editor_only_menus.append(m_seiten)

        m_fenster = QMenu("&Fenster", self)
        m_fenster.setObjectName("menuFenster")
        m_fenster.setToolTip("Teilung, Sync-Scroll, separates Dokumentfenster")
        if view_acts:
            for act in view_acts:
                if act.isSeparator():
                    continue
                if act.menu() is not None:
                    continue
                text = (act.text() or "").replace("&", "").strip()
                if text in self._FENSTER_MENU_TEXTS:
                    m_fenster.addAction(act)
        act_detach = QAction("Dokument in eigenem Fenster", self)
        act_detach.setObjectName("actDetachDocumentWindow")
        act_detach.setToolTip("Aktuelles Dokument in einem schließbaren Viewer-Fenster")
        act_detach.triggered.connect(self._detach_current_document)
        m_fenster.addAction(act_detach)
        act_ws = None
        for act in view_acts:
            sub = act.menu() if hasattr(act, "menu") else None
            if sub is not None:
                try:
                    st = (sub.title() or "").lower()
                except RuntimeError:
                    continue
                if "layout" in st:
                    act_ws = act
                    break
        if act_ws is not None:
            src = act_ws.menu() if hasattr(act_ws, "menu") else None
            src_acts = self._snapshot_menu_actions(src)
            if src is not None and src_acts:
                nm = m_fenster.addMenu((src.title() if src is not None else "") or "Arbeitsbereich-Layouts")
                for sa in src_acts:
                    if sa.isSeparator():
                        nm.addSeparator()
                    else:
                        nm.addAction(sa)

        if extra_act is not None:
            mb.insertMenu(extra_act, m_format)
            mb.insertMenu(extra_act, m_absatz)
            mb.insertMenu(extra_act, m_seiten)
        else:
            mb.addMenu(m_format)
            mb.addMenu(m_absatz)
            mb.addMenu(m_seiten)
        if help_act is not None:
            mb.insertMenu(help_act, m_fenster)
        else:
            mb.addMenu(m_fenster)
        try:
            from instantlensdoc.ui.menu_click import prepare_menu_for_clicks

            for menu in (m_format, m_absatz, m_seiten, m_fenster):
                prepare_menu_for_clicks(menu)
                menu.aboutToShow.connect(self._on_word_suite_menu_about_to_show)
        except Exception:
            pass

    def _on_word_suite_menu_about_to_show(self) -> None:
        """Eine Spalte + Enablement bevor Absatz/Seitenlayout/Format layoutet."""
        try:
            from instantlensdoc.ui.menu_click import prepare_menu_for_clicks
            from PySide6.QtWidgets import QMenu

            menu = self.sender()
            if isinstance(menu, QMenu):
                prepare_menu_for_clicks(menu)
        except Exception:
            pass
        try:
            self._sync_menu_enablement()
        except Exception:
            pass

    def _install_editor_context_menu(self) -> None:
        ed = getattr(self, "editor", None)
        if ed is None:
            return
        try:
            ed.setContextMenuPolicy(Qt.CustomContextMenu)
            ed.customContextMenuRequested.connect(self._on_editor_context_menu)
        except Exception:
            pass

    def _on_editor_context_menu(self, pos) -> None:
        ed = getattr(self, "editor", None)
        if ed is None:
            return
        menu = ed.createStandardContextMenu()
        menu.setObjectName("editorContextMenu")
        menu.addSeparator()
        for label, slot in (
            ("Fett", self._toggle_bold),
            ("Kursiv", self._toggle_italic),
            ("Unterstrichen", self._toggle_underline),
            ("Durchgestrichen", self._toggle_strike),
            ("Formatierungen löschen", self._clear_formatting),
            ("Suchen und Ersetzen…", self._find_replace),
        ):
            act = menu.addAction(label)
            act.triggered.connect(slot)
        try:
            menu.exec(ed.mapToGlobal(pos))
        except Exception:
            menu.exec()

    def _feature_dialog(self, title: str, body: str, object_name: str = "ildFeatureDialog") -> None:
        """Echter schließbarer Dialog statt Info-Box / show_planned."""
        try:
            from instantlensdoc.ui.feature_dialog import FeatureDialog

            FeatureDialog(self, title=title, body=body, object_name=object_name).exec()
            return
        except Exception:
            pass
        try:
            QMessageBox.question(self, title, body, QMessageBox.Ok)
        except Exception:
            self._set_status(f"{title}: {body}")

    def _pdf_selected_annotation_ids(self) -> set:
        """Aktuelle PDF-Annotationsauswahl (Canvas + View), ohne Annot-Layer zu ändern."""
        ids: set = set()
        pv = getattr(self, "pdf_view", None)
        if pv is None:
            return ids
        for attr in ("_selected_ann_id", "_selected_id"):
            v = getattr(pv, attr, None)
            if v:
                ids.add(v)
        for attr in ("_selected_ids", "_selected_ann_ids", "_move_ids"):
            extra = getattr(pv, attr, None)
            if extra:
                try:
                    ids.update(extra)
                except Exception:
                    pass
        canvas = getattr(pv, "canvas", None)
        if canvas is not None:
            extra = getattr(canvas, "_selected_ids", None)
            if extra:
                try:
                    ids.update(extra)
                except Exception:
                    pass
            v = getattr(canvas, "_selected_id", None)
            if v:
                ids.add(v)
        return {x for x in ids if x}

    def _on_pdf_menu_about_to_show(self) -> None:
        """Eine Spalte + Enablement, bevor das lange PDF-Menü layoutet."""
        try:
            from instantlensdoc.ui.menu_click import prepare_menu_for_clicks

            menu = getattr(self, "_pdf_menu", None)
            if menu is not None:
                prepare_menu_for_clicks(menu)
        except Exception:
            pass
        try:
            self._sync_menu_enablement()
        except Exception:
            pass

    def _bind_pdf_action(self, act, slot):
        """PDF-Menü: jeder Klick geht durch _pdf_menu_call (Dialog oder Dateiänderung)."""
        from ild_pdf.menu_policy import pdf_menu_need

        title = (act.text() or "").replace("&", "").strip()
        try:
            act.setProperty("ildPdfNeed", pdf_menu_need(title))
        except Exception:
            pass
        act.triggered.connect(
            lambda checked=False, t=title, s=slot: self._pdf_menu_call(t, s)
        )
        return act

    def _open_pdf_paths(self) -> list:
        """Alle geöffneten PDF-Tabs plus aktueller Viewer-Pfad."""
        seen: set[str] = set()
        out: list = []

        def _add(raw) -> None:
            if not raw:
                return
            try:
                p = Path(str(raw))
            except Exception:
                return
            if not p.is_file() or p.suffix.lower() != ".pdf":
                return
            key = str(p.resolve()) if p.exists() else str(p)
            if key in seen:
                return
            seen.add(key)
            out.append(p)

        _add(getattr(self.pdf_view, "pdf_path", None))
        try:
            for item in list(self.sidebar.document_paths() or []):
                _add(item)
        except Exception:
            pass
        doc = getattr(self, "doc", None)
        if doc is not None:
            _add(getattr(doc, "path", None))
        return out

    def _activate_pdf_path(self, path) -> bool:
        """PDF-Tab aktivieren (Stack + pdf_view), ohne stilles No-Op."""
        p = Path(str(path))
        if not p.is_file():
            self._feature_dialog("PDF", f"Datei nicht gefunden:\n{p}")
            return False
        cur = getattr(self.pdf_view, "pdf_path", None)
        try:
            same = cur is not None and Path(cur).resolve() == p.resolve()
        except Exception:
            same = cur is not None and Path(cur) == p
        if same:
            try:
                self.stack.setCurrentWidget(self.pdf_view)
            except Exception:
                pass
            try:
                self._sync_menu_enablement()
            except Exception:
                pass
            return True
        try:
            self.open_path(str(p))
        except Exception as e:
            self._feature_dialog("PDF öffnen", str(e))
            return False
        ok = bool(getattr(self.pdf_view, "pdf_path", None))
        if not ok:
            self._feature_dialog("PDF öffnen", f"Konnte PDF nicht laden:\n{p}")
        return ok

    def _ensure_pdf_target(self, title: str) -> bool:
        """Aktives PDF oder Zielwahl unter offenen PDF-Tabs. Nie stilles No-Op."""
        t = (title or "").replace("&", "").strip() or "PDF"
        try:
            if bool(self._pdf_tab_active()) and bool(
                getattr(self.pdf_view, "pdf_path", None)
            ):
                return True
        except Exception:
            pass
        paths = self._open_pdf_paths()
        if not paths:
            self._feature_dialog(t, "Bitte zuerst ein PDF öffnen.")
            return False
        chosen = paths[0]
        if len(paths) == 1:
            labels = [paths[0].name]
            prompt = (
                "Aktiver Tab ist kein PDF.\nWelches geöffnete PDF verwenden?"
            )
        else:
            labels = [p.name for p in paths]
            prompt = "Welches geöffnete PDF verwenden?"
        from PySide6.QtWidgets import QInputDialog

        item, ok = QInputDialog.getItem(self, t, prompt, labels, 0, False)
        if not ok:
            return False
        if item in labels:
            chosen = paths[labels.index(item)]
        return self._activate_pdf_path(chosen)

    def _pdf_menu_selection_ok(self, title: str) -> bool:
        t = (title or "").replace("&", "").strip().lower()
        pv = getattr(self, "pdf_view", None)
        store = getattr(pv, "store", None) if pv is not None else None
        if "stempel 90" in t:
            aid = getattr(pv, "_selected_ann_id", None) if pv is not None else None
            if not aid or store is None:
                return False
            try:
                from ild_pdf.annotate import AnnotationType

                ann = store.get(aid)
                return bool(ann and ann.type == AnnotationType.STAMP)
            except Exception:
                return False
        if "lesezeichen löschen" in t:
            try:
                return self.sidebar.selected_outline_path() is not None
            except Exception:
                return False
        if "messwerte" in t:
            try:
                return bool(store and store.list_measure_annotations())
            except Exception:
                return False
        if "auswahl → text" in t or ("auswahl" in t and "schwärz" in t):
            rects = list(getattr(pv, "_text_selection_rects", None) or []) if pv else []
            return bool(rects)
        if t.startswith("auswahl ") and (
            "drehen" in t or "spiegeln" in t
        ):
            return bool(self._pages_for_batch_transform())
        return True

    def _pdf_menu_call(self, title: str, fn) -> None:
        """PDF-Menüslot: Zielwahl / FeatureDialog, sonst echte Funktion — kein No-Op."""
        from ild_pdf.menu_policy import pdf_menu_need

        t = (title or "").replace("&", "").strip()
        need = pdf_menu_need(t)
        if need != "always":
            if not self._ensure_pdf_target(t):
                return
        if need == "selection" and not self._pdf_menu_selection_ok(t):
            from ild_pdf.menu_policy import pdf_menu_disable_reason

            reason = pdf_menu_disable_reason(
                t, has_open_pdf=True, is_pdf_tab=bool(self._pdf_tab_active())
            )
            self._feature_dialog(t, reason or "Voraussetzung nicht erfüllt.")
            return
        store = getattr(self.pdf_view, "store", None)
        low = t.lower()
        try:
            if "messwerte" in low:
                n = 0
                try:
                    n = len(store.list_measure_annotations()) if store is not None else 0
                except Exception:
                    n = 0
                if n == 0:
                    self._feature_dialog(
                        "Messwerte", "Keine Mess-Annotationen vorhanden."
                    )
                    return
            if "formularfelder erkennen" in low:
                from ild_pdf.acroform import detect_form_candidates

                cands = detect_form_candidates(
                    self.pdf_view.pdf_path, self.pdf_view.page_index
                )
                if not cands:
                    self._feature_dialog(
                        "Felder erkennen",
                        "Keine Kandidaten auf dieser Seite (Labels „:“, ____, [ ]).",
                    )
                    return
            if "overlay" in low and "einbrenn" in low:
                n = (
                    len(store.text_overlays())
                    if store is not None and hasattr(store, "text_overlays")
                    else 0
                )
                if n == 0:
                    self._feature_dialog(
                        "Einbrennen", "Keine TEXT/TEXT_OVERLAY Annotationen."
                    )
                    return
            if ("schwärz" in low or "redaction" in low) and "auswahl" not in low:
                n = 0
                if store is not None:
                    anns = store.all() if hasattr(store, "all") else []
                    n = sum(
                        1
                        for a in anns
                        if "redact"
                        in str(
                            getattr(getattr(a, "type", None), "value", a.type) or ""
                        ).lower()
                    )
                if n == 0:
                    self._feature_dialog(t, "Keine Schwärzungen vorhanden.")
                    return
            if "auswahl" in low and "schwärz" in low:
                rects = list(getattr(self.pdf_view, "_text_selection_rects", None) or [])
                if not rects:
                    self._feature_dialog(
                        t,
                        "Keine Textauswahl. Zuerst Text auf der Seite markieren.",
                    )
                    return
        except Exception as e:
            self._feature_dialog(t, str(e) or "Vorprüfung fehlgeschlagen.")
            return
        try:
            fn()
        except Exception as e:
            self._feature_dialog(t, str(e) or "Aktion fehlgeschlagen.")

    def _pdf_reload_annotations_menu(self) -> None:
        ok = bool(self.pdf_view.reload_annotations())
        if ok:
            n = 0
            try:
                n = len(self.pdf_view.store.annotations)
            except Exception:
                n = 0
            self._feature_dialog(
                "Annotationen laden",
                f"{n} Annotation(en) aus Sidecar geladen.",
                object_name="ildAnnReloadDialog",
            )

    def _pdf_cycle_ann_color_menu(self) -> None:
        color = self.pdf_view.cycle_annotation_color()
        self._feature_dialog(
            "Annotation-Farbe",
            f"Nächste Highlight-Farbe: {color}",
            object_name="ildAnnColorDialog",
        )

    def _pdf_randomize_ann_color_menu(self) -> None:
        color = self.pdf_view.randomize_annotation_color()
        self._feature_dialog(
            "Annotation-Farbe",
            f"Zufällige Highlight-Farbe: {color}",
            object_name="ildAnnColorDialog",
        )

    def _pdf_object_edit_menu(self) -> None:
        if not self.pdf_view.object_edit_dialog():
            self._feature_dialog("Objekt bearbeiten", "Kein PDF geöffnet.")
            return
        self._feature_dialog(
            "Objekt bearbeiten",
            "Objekt-Werkzeug aktiv. Klick wählt ein Objekt; "
            "Doppelklick öffnet den Transform-Dialog.",
            object_name="ildObjectEditDialog",
        )

    def _pdf_object_transform_menu(self) -> None:
        if self.pdf_view.object_transform_dialog():
            return
        self._feature_dialog(
            "Objekt-Dialog",
            "Kein Objekt gewählt. Zuerst ein Objekt auf der Seite anklicken.",
            object_name="ildObjectTransformHint",
        )

    def _pdf_import_text_overlays_menu(self) -> None:
        store = getattr(self.pdf_view, "store", None)
        n0 = 0
        try:
            n0 = len(store.text_overlays()) if store is not None else 0
        except Exception:
            n0 = 0
        self.pdf_view.import_text_overlays()
        n1 = n0
        try:
            n1 = len(store.text_overlays()) if store is not None else 0
        except Exception:
            n1 = n0
        added = max(0, n1 - n0)
        if added:
            self._feature_dialog(
                "PDF-Text → Overlay",
                f"{added} Overlay(s) aus der Textschicht angelegt.",
                object_name="ildTextOverlayDialog",
            )

    def _pdf_rotate_stamp_menu(self) -> None:
        ok = bool(self.pdf_view.rotate_selected_stamp(90))
        if not ok:
            self._feature_dialog(
                "Stempel drehen",
                "Kein Stempel ausgewählt. Zuerst einen Stempel auf der Seite markieren.",
                object_name="ildStampRotateDialog",
            )
            return
        try:
            self.pdf_view.schedule_sidecar_save(force=True)
        except Exception:
            pass
        rot = ""
        try:
            aid = getattr(self.pdf_view, "_selected_ann_id", None)
            ann = self.pdf_view.store.get(aid) if aid else None
            if ann is not None:
                rot = f" ({int(getattr(ann, 'rotation', 0) or 0)}°)"
        except Exception:
            rot = ""
        self._feature_dialog(
            "Stempel drehen",
            f"Stempel gedreht{rot}.",
            object_name="ildStampRotateDialog",
        )

    def _require_pdf(self, title: str) -> bool:
        """True wenn ein PDF bereit ist; sonst Zielwahl oder FeatureDialog — nie nur Status."""
        return self._ensure_pdf_target(title)

    def _set_action_available(self, act, available: bool, reason: str) -> None:
        """Enable/Disable mit Tooltip-Grund, ohne Tooltip zu stapeln — 2.6.54."""
        if act is None:
            return
        try:
            src = act.property("ildAvailTip")
            if not src:
                src = act.toolTip() or ""
                act.setProperty("ildAvailTip", src)
            act.setEnabled(bool(available))
            if available:
                act.setToolTip(str(src))
            else:
                extra = str(reason or "").strip()
                base = str(src).strip()
                act.setToolTip(f"{base} — {extra}".strip(" —") if base else extra)
        except Exception:
            try:
                act.setEnabled(bool(available))
            except Exception:
                pass

    @staticmethod
    def _label_is_editor_only(label: str) -> bool:
        """Absatz/Stil/Einrückung/Typografie — nicht für PDF-Ansicht — 2.6.54."""
        t = (label or "").strip().lower()
        needles = (
            "zeilenabstand",
            "absatz links",
            "absatz zentriert",
            "absatz rechts",
            "absatz blocksatz",
            "laufweite",
            "durchschuss",
            "tracking",
            "leading",
            "initial",
            "drop cap",
            "silbentrennung",
            "einrückung",
            "textbaustein",
            "sonderzeichen einfügen",
            "automatische formatierung",
            "inhaltsverzeichnis",
            "abbildungsverzeichnis",
            "stichwortverzeichnis",
            "formatvorlage",
            "absatzstil",
            "zeichenstil",
            "stil-preset",
            "fett",
            "kursiv",
            "unterstrichen",
            "durchgestrichen",
            "schriftart",
            "schriftgröße",
            "schriftfarbe",
            "texthervorhebung",
            "hintergrundfarbe",
            "textmarker",
            "formatierungen löschen",
            "formatvorlage",
            "aufzählungszeichen",
            "nummerierung",
            "absatz…",
            "zeilenumbruch einfügen",
            "seitenumbruch einfügen",
            "tabelle einfügen",
            "hyperlink",
            "groß-/klein",
            "alles groß",
            "alles klein",
            "autokorrektur",
            "zeile nach oben",
            "zeile nach unten",
            "zeilen sortieren",
            "zeile kommentieren",
            "zeile favorisieren",
            "zeilen-lesezeichen",
            "nächstes zeilen-lesezeichen",
            "vorheriges zeilen-lesezeichen",
            "weiches trennzeichen",
            "geschütztes leerzeichen",
            "deutsch (de)",
            "english (en)",
            "français",
            "русский",
            "español",
            "中文",
            "português",
            "العربية",
            "italiano",
        )
        return any(n in t for n in needles)

    @staticmethod
    def _label_is_editor_view_only(label: str) -> bool:
        t = (label or "").strip().lower()
        needles = (
            "seitenlayout",
            "hochformat",
            "querformat",
            "us letter",
            "a4",
            "zeilennummern",
            "editor-minimap",
            "minimap",
            "wortumbruch",
            "markdown-vorschau",
            "einrückungs-guides",
            "sonderzeichen anzeigen",
        )
        return any(n in t for n in needles)

    @staticmethod
    def _label_is_pdf_view(label: str, parent: str = "") -> bool:
        t = (label or "").strip().lower()
        p = (parent or "").strip().lower()
        if "annotation-typen" in p:
            return True
        needles = (
            "vergrößern",
            "verkleinern",
            "seite einpassen",
            "breite einpassen",
            "höhe einpassen",
            "zoom 100",
            "präsentationsmodus",
            "aktuellen zoom",
        )
        return any(n in t for n in needles)

    @staticmethod
    def _label_is_pdf_annotation(label: str, parent: str = "") -> bool:
        t = (label or "").strip().lower()
        p = (parent or "").strip().lower()
        if "auswahl ausrichten" in p:
            return True
        needles = (
            "annotation",
            "auswahl → notiz",
            "auswahl-farbe",
            "auswahl-deckkraft",
            "alle annotationen",
        )
        return any(n in t for n in needles)

    @staticmethod
    def _label_is_pdf_extra(label: str) -> bool:
        t = (label or "").strip().lower()
        needles = (
            "ocr gesamtes pdf",
            "ocr region",
        )
        return any(n in t for n in needles)

    def _sync_menu_enablement(self) -> None:
        """PDF-only / Editor-only Menüs an den aktuellen Dokumenttyp koppeln — 2.6.54."""
        is_pdf = False
        is_editor = False
        try:
            is_pdf = bool(self._pdf_tab_active()) and bool(
                getattr(self.pdf_view, "pdf_path", None)
            )
        except Exception:
            try:
                is_pdf = (
                    self.stack.currentWidget() is self.pdf_view
                    and bool(getattr(self.pdf_view, "pdf_path", None))
                )
            except Exception:
                is_pdf = False
        try:
            is_editor = bool(self._editor_document_active()) or bool(
                self._layout_mode_active()
            )
        except Exception:
            try:
                is_editor = self.stack.currentWidget() is self.editor_pane
            except Exception:
                is_editor = False
        try:
            pdf_paths = self._open_pdf_paths()
        except Exception:
            pdf_paths = []

        def _walk(menu, mode: str, parent: str = "") -> None:
            if menu is None:
                return
            for a in menu.actions():
                if a.isSeparator():
                    continue
                sub = a.menu() if hasattr(a, "menu") else None
                if sub is not None:
                    st = (sub.title() or "").replace("&", "")
                    _walk(sub, mode, st)
                    continue
                t = (a.text() or "").replace("&", "").lower()
                if mode == "pdf":
                    from ild_pdf.menu_policy import (
                        pdf_menu_disable_reason,
                        pdf_menu_need,
                    )

                    src = ""
                    try:
                        src = str(a.property("ild_i18n_src") or "")
                    except Exception:
                        src = ""
                    label = (src or t).replace("&", "")
                    need = ""
                    try:
                        need = str(a.property("ildPdfNeed") or "")
                    except Exception:
                        need = ""
                    if not need:
                        need = pdf_menu_need(label)
                    has_open = bool(pdf_paths)
                    if need == "always":
                        self._set_action_available(a, True, "")
                        continue
                    if need == "selection":
                        ok = bool(is_pdf) and self._pdf_menu_selection_ok(label)
                        reason = pdf_menu_disable_reason(
                            label, has_open_pdf=has_open, is_pdf_tab=bool(is_pdf)
                        )
                        self._set_action_available(a, ok, reason)
                        continue
                    if has_open:
                        self._set_action_available(a, True, "")
                    else:
                        self._set_action_available(
                            a,
                            False,
                            pdf_menu_disable_reason(
                                label,
                                has_open_pdf=False,
                                is_pdf_tab=False,
                            ),
                        )
                elif mode == "insert":
                    if "musterseite" in t:
                        self._set_action_available(
                            a, is_pdf, "Nur bei geöffnetem PDF verfügbar"
                        )
                    else:
                        self._set_action_available(
                            a, is_editor, "Nur im Text- oder DOCX-Editor verfügbar"
                        )
                elif mode == "edit":
                    src = ""
                    try:
                        src = str(a.property("ild_i18n_src") or "")
                    except Exception:
                        src = ""
                    label = (src or t).replace("&", "").lower()
                    if self._label_is_pdf_annotation(label, parent) or "treffer als highlight" in label:
                        ids = self._pdf_selected_annotation_ids()
                        need_sel = (
                            "auswahl ausrichten" in parent
                            or "auswahl-deckkraft" in label
                            or "auswahl-farbe" in label
                            or label.startswith("annotationen kopieren")
                        )
                        if need_sel:
                            self._set_action_available(
                                a,
                                is_pdf and bool(ids),
                                "Keine Annotation ausgewählt",
                            )
                        else:
                            self._set_action_available(
                                a, is_pdf, "Nur bei geöffnetem PDF verfügbar"
                            )
                    elif self._label_is_editor_only(label) or parent.strip().lower() == "absatz":
                        self._set_action_available(
                            a,
                            is_editor,
                            "Nur im Text- oder DOCX-Editor verfügbar",
                        )
                elif mode == "view-editor":
                    src = ""
                    try:
                        src = str(a.property("ild_i18n_src") or "")
                    except Exception:
                        src = ""
                    label = (src or t).replace("&", "").lower()
                    if self._label_is_editor_view_only(label):
                        self._set_action_available(
                            a,
                            is_editor,
                            "Nur im Text- oder DOCX-Editor verfügbar",
                        )
                    elif self._label_is_pdf_view(label, parent):
                        self._set_action_available(
                            a, is_pdf, "Nur bei geöffnetem PDF verfügbar"
                        )
                elif mode == "extra":
                    if self._label_is_pdf_extra(t):
                        self._set_action_available(
                            a, is_pdf, "Nur bei geöffnetem PDF verfügbar"
                        )
                elif mode == "export":
                    want = is_editor
                    if "pdf" in t and "text" not in t:
                        want = is_pdf or is_editor
                    self._set_action_available(
                        a, want, "Nur bei geöffnetem Dokument verfügbar"
                    )

        try:
            mb = self.menuBar()
        except Exception:
            return
        for top in mb.actions():
            menu = top.menu() if hasattr(top, "menu") else None
            title = ""
            try:
                title = (menu.title() if menu is not None else top.text() or "")
            except Exception:
                title = ""
            title = title.replace("&", "")
            if title == "PDF":
                _walk(menu, "pdf")
            elif title == "Einfügen":
                _walk(menu, "insert")
            elif title in ("Bearbeiten", "Edit", "Format", "Absatz"):
                _walk(menu, "edit")
            elif title in ("Ansicht", "View", "Fenster", "Seitenlayout"):
                _walk(menu, "view-editor")
            elif title in ("Extras", "Extra"):
                _walk(menu, "extra")
            elif title == "Datei" and menu is not None:
                dirty = bool(self.doc and getattr(self.doc, "dirty", False))
                untitled = bool(self.doc and not getattr(self.doc, "path", None))
                n_tabs = 1
                try:
                    n_tabs = len(list(self.sidebar.document_paths() or []))
                except Exception:
                    n_tabs = 1
                has_tpl = False
                try:
                    from instantlensdoc.core.app_settings import get_user_doc_templates

                    has_tpl = bool(get_user_doc_templates())
                except Exception:
                    has_tpl = False
                for a in menu.actions():
                    sub = a.menu() if hasattr(a, "menu") else None
                    if sub is not None:
                        st = (sub.title() or "").replace("&", "").lower()
                        if "export" in st:
                            _walk(sub, "export")
                        elif st in ("neu", "new"):
                            for sa in sub.actions():
                                if sa.isSeparator():
                                    continue
                                ssub = sa.menu() if hasattr(sa, "menu") else None
                                if ssub is not None:
                                    for xa in ssub.actions():
                                        xt = (xa.text() or "").replace("&", "").lower()
                                        if xt in (
                                            "reihenfolge…",
                                            "als zip exportieren…",
                                        ):
                                            self._set_action_available(
                                                xa,
                                                has_tpl,
                                                "Keine Nutzer-Vorlagen",
                                            )
                                    continue
                                stxt = (sa.text() or "").replace("&", "").lower()
                                if stxt in (
                                    "vorlagen-reihenfolge…",
                                    "vorlagen als zip exportieren…",
                                ):
                                    self._set_action_available(
                                        sa, has_tpl, "Keine Nutzer-Vorlagen"
                                    )
                        continue
                    t = (a.text() or "").replace("&", "").lower()
                    if t == "speichern":
                        self._set_action_available(
                            a, dirty or untitled, "Nichts zu speichern"
                        )
                    elif t == "alles speichern":
                        self._set_action_available(
                            a,
                            dirty or untitled or is_pdf,
                            "Nichts zu speichern",
                        )
                    elif t == "andere tabs schließen":
                        self._set_action_available(
                            a, n_tabs > 1, "Kein weiterer Tab"
                        )
                    elif t == "tabs links schließen":
                        idx = 0
                        try:
                            paths = list(self.sidebar.document_paths() or [])
                            cur = (
                                str(Path(self.doc.path))
                                if self.doc and self.doc.path
                                else ""
                            )
                            idx = next(
                                (
                                    i
                                    for i, p in enumerate(paths)
                                    if str(Path(str(p))) == str(Path(cur))
                                ),
                                0,
                            )
                        except Exception:
                            idx = 0
                        self._set_action_available(a, idx > 0, "Keine Tabs links")
                    elif t == "tabs rechts schließen":
                        idx = 0
                        n_p = n_tabs
                        try:
                            paths = list(self.sidebar.document_paths() or [])
                            n_p = len(paths)
                            cur = (
                                str(Path(self.doc.path))
                                if self.doc and self.doc.path
                                else ""
                            )
                            idx = next(
                                (
                                    i
                                    for i, p in enumerate(paths)
                                    if str(Path(str(p))) == str(Path(cur))
                                ),
                                n_p,
                            )
                        except Exception:
                            idx = 0
                        self._set_action_available(
                            a, n_p > 1 and idx < n_p - 1, "Keine Tabs rechts"
                        )

        rb = getattr(self, "ribbon_bar", None)
        if rb is not None:
            always = {
                "open",
                "scan_import",
                "devices_discover",
                "devices_printers",
                "devices_refresh",
                "toggle_ribbon",
                "toggle_doc_tabs",
                "settings",
                "chrome_klassisch",
                "chrome_ribbon",
                "chrome_kombiniert",
                "print",
            }
            pdf_ids = {
                "compare_pdfs",
                "preflight",
                "apply_bleed",
                "export_pdfx",
                "book_layout",
                "page_by_page",
                "continuous_scroll",
            }
            editor_ids = {
                "export_epub",
                "export_pptx",
                "insert_hyperlink",
                "insert_shape",
                "insert_snippet",
                "insert_table",
                "insert_break",
                "find_replace",
                "spellcheck",
                "auto_toc",
                "auto_lof",
                "auto_index",
                "page_layout",
                "bold",
                "italic",
                "underline",
                "strike",
                "highlight",
                "highlight_color",
                "align_left",
                "align_center",
                "align_right",
                "align_justify",
                "bullet_list",
                "numbered_list",
                "paragraph",
                "page_size_a4",
                "page_size_letter",
                "page_portrait",
                "page_landscape",
                "header_footer",
                "field_token",
                "indent",
                "outdent",
                "clear_formatting",
                "font",
                "font_color",
                "paragraph",
                "header_footer",
                "insert_special_chars",
                "insert_nbsp",
                "insert_shy",
                "styles_pane",
                "mail_merge",
                "mail_merge_data",
                "mail_merge_field",
                "mail_merge_preview",
                "mail_merge_finish",
                "table_add_row",
                "table_add_col",
                "table_del_row",
                "table_del_col",
                "table_merge",
                "table_split",
                "table_borders",
                "table_header_row",
                "table_align_left",
                "table_align_center",
                "table_align_right",
            }
            for aid, btn in (getattr(rb, "_actions", {}) or {}).items():
                if aid in always:
                    on = True
                elif aid in pdf_ids:
                    on = bool(is_pdf)
                elif aid in editor_ids:
                    on = bool(is_editor)
                else:
                    continue
                if hasattr(rb, "set_enabled"):
                    rb.set_enabled(aid, on)
                else:
                    btn.setEnabled(on)

        pane = getattr(self, "editor_pane", None)
        if pane is not None:
            for _aid, tb in (getattr(pane, "_tool_buttons", {}) or {}).items():
                try:
                    tb.setEnabled(bool(is_editor))
                except Exception:
                    pass

    def _refresh_recent(self):
        # Fehlende Dateien aus der persistierten Liste streichen — 2.6.54
        try:
            recent_mod.prune_missing_recent()
        except Exception:
            pass
        entries = recent_mod.load_recent_entries()
        self.sidebar.set_recent(entries)
        if hasattr(self, "welcome_page") and self.welcome_page is not None:
            try:
                self.welcome_page.refresh_recent()
            except Exception:
                pass
        if not self._qt_widget_alive(getattr(self, "_recent_menu", None)):
            self._recent_menu = None
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
        clear.setToolTip("Persistierte Liste der zuletzt geöffneten Dateien leeren")
        clear.setEnabled(bool(entries))
        clear.triggered.connect(lambda *_: self._clear_recent())
        self._recent_menu.addAction(clear)

    def _remove_recent_path(self, path: str) -> None:
        """Einzelnen Recent-Eintrag entfernen (Sidebar-Kontextmenü)."""
        recent_mod.remove_recent(path)
        self._refresh_recent()
        self._set_status(f"Aus Zuletzt geöffnet entfernt: {Path(path).name}")

    def _prune_missing_recent(self) -> None:
        """Nur noch existierende Dateien in der Recent-Liste behalten — 2.6.54."""
        try:
            kept = recent_mod.prune_missing_recent()
        except Exception:
            kept = []
        self._refresh_recent()
        self._set_status(f"Zuletzt geöffnet: {len(kept)} vorhandene Datei(en)")

    def _refresh_workspaces(self):
        """Projekt-Ordner-Menü (letzte 5 Workspaces) neu aufbauen."""
        if not self._qt_widget_alive(getattr(self, "_workspace_menu", None)):
            self._workspace_menu = None
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
            self._feature_dialog(
                "Projekt-Ordner",
                "Kein Projekt-Ordner gewählt.",
                object_name="ildProjectFolderDialog",
            )
            return
        from instantlensdoc.ui.feature_dialog import PathOpenDialog

        PathOpenDialog(self, title="Projekt-Ordner", path=folder).exec()
        self._set_status(f"Projekt-Ordner: {folder}")

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

    def _clear_recent(self, *args, confirm: bool = True):
        """Persistierte Recent-Liste leeren und alle drei Ansichten aktualisieren — 2.6.54."""
        if confirm:
            reply = QMessageBox.question(
                self,
                "Zuletzt geöffnet",
                "Liste der zuletzt geöffneten Dateien wirklich leeren?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        recent_mod.clear_recent()
        self._refresh_recent()
        self._set_status("Zuletzt geöffnet geleert")

    def _welcome_files_dropped(self, paths) -> None:
        """Dateien von der Willkommen-Seite per Drag & Drop öffnen — 1.0.2."""
        opened = 0
        for path in paths or []:
            if not path:
                continue
            try:
                self.open_path(path)
                opened += 1
            except Exception:
                pass
        if opened:
            self._set_status(f"{opened} Datei(en) per Drag & Drop geöffnet")

    def _remember_path(self, path: str | Path):
        try:
            recent_mod.add_recent(path)
            self._refresh_recent()
        except Exception:
            pass

    def _announce_status_toast(self, msg: str) -> None:
        """Accessibility-Announcement für Status-Toast (Metadaten) — 1.5.4."""
        sb = self.statusBar()
        try:
            sb.setAccessibleName(msg)
            sb.setAccessibleDescription(msg)
        except Exception:
            pass
        try:
            from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent

            ev = QAccessibleAnnouncementEvent(sb, msg)
            QAccessible.updateAccessibility(ev)
        except Exception:
            try:
                from PySide6.QtGui import QAccessible, QAccessibleEvent

                ev = QAccessibleEvent(sb, QAccessible.Event.NameChanged)
                QAccessible.updateAccessibility(ev)
            except Exception:
                pass

    def _set_status(self, msg: str):
        text = msg or ""
        # Metadaten-Toast-Klick-Flag nur bei Meta-Toast behalten — 1.5.4
        if not getattr(self, "_meta_toast_active", False) or "Metadaten" not in text:
            if "Metadaten gespeichert" not in text:
                self._meta_toast_active = False
        # Text→PDF-Toast nur behalten wenn Status dazu passt — 1.7.4
        if "Text → PDF" not in text:
            self._text_pdf_toast_active = False
        # Import-Status-Toast nur behalten wenn Status dazu passt — 2.1.5
        if "Import-Status" not in text:
            self._import_status_toast_active = False
        # Ink-Glättungs-Toast nur behalten wenn Status dazu passt — 2.2.5
        if "Glättung angewandt" not in text:
            self._smooth_status_toast_active = False
        # Auto-Prune Status kopierbar nur behalten wenn Status dazu passt — 2.4.5
        if "Thumb Auto-Prune" not in text and "Auto-Prune Status kopiert" not in text:
            self._thumb_prune_status_active = False
        # OCR-Region Status-Klick nur behalten wenn Status dazu passt — 2.5.5
        if "OCR-Region" not in text and "OCR Region" not in text:
            self._ocr_region_toast_active = False
        # Update-Quellen-Tooltip nur bei Update-Status — 1.7.4/1.7.5
        if not text.startswith("Update:") and "Update —" not in text:
            if "Update:" not in text:
                self._update_status_source_tip = ""
                self._update_status_reference_path = None
        self.statusBar().showMessage(text, 5000)
        # Outlines-Export: Klick-Hinweis wenn Zielordner gemerkt — 1.3.4
        # Metadaten-Toast: Klick öffnet Dialog erneut — 1.5.4
        # Text→PDF: Klick öffnet Ordner — 1.7.4
        # Update: Klick öffnet VERSION.txt / docs/VERSION — 1.7.5
        # Import-Status: Klick fokussiert Statusleiste/Log — 2.1.5
        # Ink-Toast: Klick fokussiert Ink-Tool — 2.2.5
        # Auto-Prune: Klick kopiert Status erneut — 2.4.5
        if getattr(self, "_meta_toast_active", False) and "Metadaten gespeichert" in text:
            self.statusBar().setToolTip(
                "Klick öffnet Metadaten-Dialog erneut — 1.5.5"
            )
            self.statusBar().setCursor(Qt.PointingHandCursor)
        elif getattr(self, "_import_status_toast_active", False) and "Import-Status" in text:
            self.statusBar().setToolTip(
                "Klick fokussiert Statusleiste/Log falls vorhanden — 2.1.5"
            )
            self.statusBar().setCursor(Qt.PointingHandCursor)
        elif getattr(self, "_smooth_status_toast_active", False) and "Glättung angewandt" in text:
            self.statusBar().setToolTip(
                "Klick fokussiert Ink-/Freihand-Werkzeug — 2.2.5"
            )
            self.statusBar().setCursor(Qt.PointingHandCursor)
        elif getattr(self, "_thumb_prune_status_active", False) and (
            "Thumb Auto-Prune" in text or "Auto-Prune Status kopiert" in text
        ):
            self.statusBar().setToolTip(
                "Klick kopiert Auto-Prune Status erneut "
                "(Dauer OCR-Toast-Settings) — 2.4.5"
            )
            self.statusBar().setCursor(Qt.PointingHandCursor)
        elif getattr(self, "_ocr_region_toast_active", False) and (
            "OCR-Region" in text or "OCR Region" in text
        ):
            tip = self._ocr_region_status_tooltip()
            self.statusBar().setToolTip(tip)
            self.statusBar().setCursor(Qt.PointingHandCursor)
        elif getattr(self, "_text_pdf_toast_active", False) and "Text → PDF" in text:
            self.statusBar().setToolTip(
                "Klick öffnet Zielordner (Text → PDF); "
                "fehlender Ordner → Neu anlegen — 1.7.5"
            )
            self.statusBar().setCursor(Qt.PointingHandCursor)
        elif getattr(self, "_last_outline_export_dir", None) and "PDF-Outline" in text:
            self.statusBar().setToolTip(
                "Klick öffnet Export-Zielordner — 1.3.4"
            )
            self.statusBar().setCursor(Qt.PointingHandCursor)
        elif getattr(self, "_update_status_source_tip", ""):
            tip = self._update_status_source_tip
            ref = getattr(self, "_update_status_reference_path", None)
            if ref is not None and Path(ref).is_file():
                tip = f"{tip} — Klick öffnet {Path(ref).name} im Editor — 1.7.5"
                self.statusBar().setCursor(Qt.PointingHandCursor)
            else:
                self.statusBar().unsetCursor()
            self.statusBar().setToolTip(tip)
        else:
            self.statusBar().setToolTip("")
            self.statusBar().unsetCursor()

    def _open_text_pdf_status_folder(self, folder: Path) -> bool:
        """Text→PDF Ordner öffnen; fehlt → Dialog mit Neu anlegen — 1.7.5."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        if folder.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            self._announce_status_toast(f"Ordner geöffnet: {folder}")
            return True
        reply = QMessageBox.question(
            self,
            "Ordner fehlt",
            f"Zielordner existiert nicht:\n{folder}\n\nNeu anlegen und öffnen?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            self._announce_status_toast(f"Ordner fehlt: {folder}")
            return False
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            QMessageBox.warning(
                self,
                "Ordner anlegen",
                f"Ordner konnte nicht angelegt werden:\n{folder}\n\n{e}",
            )
            return False
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        self._announce_status_toast(f"Ordner angelegt und geöffnet: {folder}")
        return True

    def _open_update_reference_in_editor(self) -> bool:
        """Lokale VERSION.txt / docs/VERSION im Editor öffnen — 1.7.5."""
        ref = getattr(self, "_update_status_reference_path", None)
        if ref is None:
            from instantlensdoc.core.update_check import find_embedded_version_file

            ref, _label = find_embedded_version_file()
        if ref is None or not Path(ref).is_file():
            self._announce_status_toast(
                "Keine lokale VERSION.txt / docs/VERSION gefunden"
            )
            return False
        path = Path(ref)
        self.open_path(str(path))
        self._announce_status_toast(f"Version geöffnet: {path.name}")
        return True

    def _focus_import_status_toast_target(self) -> bool:
        """
        Import-Status-Toast-Klick: Log-Widget fokussieren falls vorhanden,
        sonst Statusleiste — 2.1.5.
        """
        target = None
        for name in (
            "log_view",
            "status_log",
            "activity_log",
            "message_log",
            "log_widget",
        ):
            w = getattr(self, name, None)
            if w is not None and hasattr(w, "setFocus"):
                try:
                    if hasattr(w, "isVisible") and not w.isVisible():
                        continue
                except Exception:
                    pass
                target = w
                break
        if target is None:
            target = self.statusBar()
        try:
            target.setFocus(Qt.OtherFocusReason)
            if hasattr(target, "raise_"):
                target.raise_()
            if hasattr(target, "activateWindow"):
                try:
                    target.activateWindow()
                except Exception:
                    pass
        except Exception:
            return False
        msg = getattr(self, "_import_status_toast_msg", "") or (
            self.statusBar().currentMessage() or "Statusleiste"
        )
        self._announce_status_toast(msg)
        return True

    def _on_status_bar_clicked(self, event) -> None:
        """Statusleisten-Klick: Meta / Import / Prune-Copy / Text→PDF / Update — 2.4.4."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        cur = self.statusBar().currentMessage() or ""
        if (
            event.button() == Qt.LeftButton
            and getattr(self, "_meta_toast_active", False)
            and "Metadaten gespeichert" in cur
        ):
            # Nur öffnen wenn Dialog nicht schon offen — sonst Fokus/raise — 1.5.5
            existing = getattr(self, "_meta_dialog", None)
            if existing is not None and existing.isVisible():
                existing.raise_()
                existing.activateWindow()
                return
            self._meta_toast_active = False
            self.statusBar().unsetCursor()
            self.statusBar().setToolTip("")
            self._edit_pdf_metadata()
            return
        # Import-Status: Klick fokussiert Statusleiste/Log — 2.1.5
        if (
            event.button() == Qt.LeftButton
            and getattr(self, "_import_status_toast_active", False)
            and "Import-Status" in cur
        ):
            if self._focus_import_status_toast_target():
                return
        # Auto-Prune Status: Klick → Zwischenablage erneut — 2.4.5
        if (
            event.button() == Qt.LeftButton
            and getattr(self, "_thumb_prune_status_active", False)
            and (
                "Thumb Auto-Prune" in cur
                or "Auto-Prune Status kopiert" in cur
                or getattr(self, "_last_thumb_prune_status", "")
            )
        ):
            if self._copy_thumb_prune_status_to_clipboard():
                return
        # OCR-Region: L→Tab · R→Menü · Mittel/Ctrl→Pfad · Shift→Text · Alt→Datei — 2.5.5–2.5.10
        if (
            getattr(self, "_ocr_region_toast_active", False)
            and ("OCR-Region" in cur or "OCR Region" in cur)
        ):
            if event.button() == Qt.MiddleButton or (
                event.button() == Qt.LeftButton
                and bool(event.modifiers() & Qt.ControlModifier)
            ):
                if self._copy_ocr_region_result_path():
                    return
            elif event.button() == Qt.LeftButton and bool(
                event.modifiers() & Qt.ShiftModifier
            ):
                if self._copy_ocr_region_result_text():
                    return
            elif event.button() == Qt.LeftButton and bool(
                event.modifiers() & Qt.AltModifier
            ):
                if self._open_ocr_region_result_file():
                    return
            elif event.button() == Qt.LeftButton:
                if self._focus_ocr_region_result_tab():
                    return
            elif event.button() == Qt.RightButton:
                # RMB: Kontextmenü aller Aktionen (statt sofort Ordner) — 2.5.10
                if self._show_ocr_region_status_menu():
                    return
        # Ink-Toast: Klick fokussiert Ink-/Freihand-Werkzeug — 2.2.5
        if (
            event.button() == Qt.LeftButton
            and getattr(self, "_smooth_status_toast_active", False)
            and "Glättung angewandt" in cur
        ):
            pv = getattr(self, "pdf_view", None)
            if pv is not None and hasattr(pv, "_focus_ink_tool_from_toast"):
                try:
                    if pv._focus_ink_tool_from_toast():
                        return
                except Exception:
                    pass
        # Text → PDF: Klick öffnet Ordner; fehlt → Neu anlegen — 1.7.5
        if (
            event.button() == Qt.LeftButton
            and getattr(self, "_text_pdf_toast_active", False)
            and "Text → PDF" in cur
        ):
            pdf_path = getattr(self, "_last_text_pdf_status_path", None)
            if pdf_path is not None:
                folder = Path(pdf_path).parent
                self._open_text_pdf_status_folder(folder)
                return
        # Update-Status: Klick öffnet VERSION.txt / docs/VERSION — 1.7.5
        if (
            event.button() == Qt.LeftButton
            and (
                cur.startswith("Update:")
                or "Update —" in cur
                or getattr(self, "_update_status_source_tip", "")
            )
            and (
                getattr(self, "_update_status_reference_path", None) is not None
                or getattr(self, "_update_status_source_tip", "")
            )
        ):
            if self._open_update_reference_in_editor():
                return
        folder = getattr(self, "_last_outline_export_dir", None)
        if (
            event.button() == Qt.LeftButton
            and folder is not None
            and "PDF-Outline" in cur
        ):
            path = Path(folder)
            if path.is_dir():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
                return
        QStatusBar.mousePressEvent(self.statusBar(), event)

    def _on_pdf_view_status(self, msg: str) -> None:
        """PDF-View-Status; 0-Treffer dauerhaft sticky — 1.1.7."""
        text = str(msg or "")
        if "gefilterten Treffer" in text:
            self._set_ann_zero_sticky_status(text)
            return
        # Nächste Ann.-Aktion (Löschen/Einfügen/…) beendet Sticky — 1.1.7
        if "Annotation" in text and any(
            k in text for k in ("gelöscht", "eingefügt", "kopiert", "dupliziert")
        ):
            self._clear_ann_zero_sticky_status()
        self._set_status(text)

    def _set_ann_zero_sticky_status(self, msg: str) -> None:
        """0-Treffer-Hinweis dauerhaft in Statusleiste bis nächste Ann.-Aktion — 1.1.7."""
        self._ann_zero_sticky = True
        lbl = getattr(self, "ann_zero_status_label", None)
        if lbl is not None:
            lbl.setText(msg)
            lbl.setVisible(True)
        self.statusBar().showMessage(msg, 0)

    def _clear_ann_zero_sticky_status(self) -> None:
        """Sticky 0-Treffer-Status entfernen (nächste Ann.-Aktion) — 1.1.7."""
        if not getattr(self, "_ann_zero_sticky", False):
            return
        self._ann_zero_sticky = False
        lbl = getattr(self, "ann_zero_status_label", None)
        if lbl is not None:
            lbl.setText("")
            lbl.setVisible(False)
        cur = self.statusBar().currentMessage() or ""
        if "gefilterten Treffer" in cur:
            self.statusBar().clearMessage()

    def _ann_action_status(self, msg: str) -> None:
        """Status einer Annotations-Aktion — löscht Sticky 0-Treffer — 1.1.7."""
        self._clear_ann_zero_sticky_status()
        self._set_status(msg)

    def _update_doc_status(self):
        """Statusleiste: Dateiname, Seite x/y bzw. Zeile x/y, Seitengröße, Zoom %, Wörter."""
        # Während _build_ui kann stack.currentChanged feuern, bevor Labels existieren
        if not hasattr(self, "file_status_label"):
            return
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
        self._sync_table_tools()

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
        """Dirty-Indikator (*) an Sidebar-Dokument-Tabs inkl. pending Sidecar-Debounce — 0.9.6."""
        dirty_keys = set(self._unsaved_paths)
        if self._current_is_dirty() and self.doc and self.doc.path:
            cur = self._path_key(self.doc.path)
            if cur:
                dirty_keys.add(cur)
        pending = False
        pending_key = None
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
                if pending_key:
                    dirty_keys.add(pending_key)
        # Rising-edge: kurzer Statusleisten-Blink bei pending Debounce
        was = bool(getattr(self, "_pending_was_pending", False))
        if pending and not was:
            self._blink_pending_debounce_status()
        self._pending_was_pending = bool(pending)
        if hasattr(self.sidebar, "set_documents_dirty"):
            self.sidebar.set_documents_dirty(dirty_keys, pending_key=pending_key)
            return
        # Fallback ohne Sidebar-API
        files = getattr(self.sidebar, "files", None)
        if files is None:
            return
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
            else:
                it.setText(base)

    def _blink_status_briefly(self) -> None:
        """
        Statusleiste blinken bei Batch-Abschluss — 1.8.3.
        Dauer/Modus wie Status-Blink Settings (kurz/aus) — 1.8.4.
        aus: einmaliger Status-Hinweis ohne Blink (wie Pending-Blink) — 1.8.5.
        """
        from PySide6.QtCore import QTimer

        from instantlensdoc.core.app_settings import (
            STATUS_BLINK_AUS,
            get_status_blink_mode,
        )

        sb = self.statusBar()
        if sb is None:
            return
        if get_status_blink_mode() == STATUS_BLINK_AUS:
            # Aus: kein Blink, aber einmaliger Status-Hinweis (Rising-Edge)
            self._batch_status_blink_active = False
            try:
                current = sb.currentMessage() or ""
                if current:
                    sb.showMessage(current, 1800)
            except Exception:
                pass
            return
        if getattr(self, "_batch_status_blink_active", False):
            return
        self._batch_status_blink_active = True
        base = sb.styleSheet() or ""
        # kurz: 2 Blink-Zyklen, gleiche Timing-Familie wie Pending-Blink
        styles = (
            "color: #fff; background-color: #1F6F4A; font-weight: 600;",
            base,
            "color: #fff; background-color: #1F6F4A; font-weight: 600;",
            base,
        )
        self._batch_status_blink_step = 0

        def _tick() -> None:
            i = int(getattr(self, "_batch_status_blink_step", 0))
            if i >= len(styles):
                self._batch_status_blink_active = False
                try:
                    sb.setStyleSheet(base)
                except Exception:
                    pass
                return
            try:
                sb.setStyleSheet(styles[i])
            except Exception:
                pass
            self._batch_status_blink_step = i + 1
            QTimer.singleShot(90, _tick)

        _tick()

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
            path = self.pdf_view.pdf_path
            page = int(self.pdf_view.page_index or 0)
            unit = get_page_size_unit()
            try:
                mtime = int(Path(path).stat().st_mtime_ns)
            except OSError:
                mtime = 0
            cache_key = (str(path), mtime, page, unit)
            hit = self._page_size_cache.get(cache_key)
            if hit is not None:
                return hit
            from ild_pdf.pages import format_size_pair, get_page_boxes

            boxes = get_page_boxes(path, page)
            mb = boxes["mediabox"]
            w = mb[2] - mb[0]
            h = mb[3] - mb[1]
            text = format_size_pair(w, h, unit)
            if len(self._page_size_cache) > 64:
                self._page_size_cache.clear()
            self._page_size_cache[cache_key] = text
            return text
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
        if not self._require_pdf("Präsentationsmodus"):
            return
        try:
            ann_was = bool(self.pdf_view.annotations_visible())
        except TypeError:
            ann_was = bool(self.pdf_view.annotations_visible)
        hide_ann = get_presentation_hide_annotations()
        page_num_was = False
        try:
            page_num_was = bool(self.pdf_view.show_page_number_overlay())
        except Exception:
            page_num_was = False
        self._presentation_page_num_on = bool(get_presentation_show_page_number())
        self._presentation_prev = {
            "menu": self.menuBar().isVisible(),
            "status": self.statusBar().isVisible(),
            "sidebar": self.sidebar.isVisible(),
            "favorites_bar": bool(
                getattr(self, "favorites_bar", None)
                and self.favorites_bar.isVisible()
            ),
            "was_fullscreen": self.isFullScreen(),
            "stack": self.stack.currentWidget(),
            "ann_visible": ann_was,
            "hid_ann": False,
            "page_num": page_num_was,
            "stylesheet": self.styleSheet() or "",
            "central_ss": (
                self.centralWidget().styleSheet()
                if self.centralWidget() is not None
                else ""
            ),
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
        if getattr(self, "favorites_bar", None) is not None:
            self.favorites_bar.setVisible(False)
        # Optional Annotation-Overlay aus — 1.7.0
        if hide_ann and ann_was:
            try:
                self.pdf_view.set_annotations_visible(False)
                self._presentation_prev["hid_ann"] = True
            except Exception:
                self._presentation_prev["hid_ann"] = False
        # Schwarzer Hintergrund — 1.7.1
        if get_presentation_black_background():
            black_ss = (
                "QMainWindow, QWidget#central, QStackedWidget {"
                " background: #000000; }"
            )
            try:
                self.setStyleSheet((self.styleSheet() or "") + black_ss)
                if self.centralWidget() is not None:
                    self.centralWidget().setStyleSheet("background: #000000;")
                self.pdf_view.setStyleSheet("background: #000000;")
            except Exception:
                pass
        # Seitennummer-Overlay Toggle — 1.7.1
        try:
            self.pdf_view.set_show_page_number_overlay(self._presentation_page_num_on)
        except Exception:
            pass
        self._presentation_active = True
        self.showFullScreen()
        try:
            self.pdf_view.fit_page()
        except Exception:
            pass
        self.pdf_view.setFocus(Qt.OtherFocusReason)
        self._start_presentation_timer()
        ann_note = " · Ann. aus" if self._presentation_prev.get("hid_ann") else ""
        adv = get_presentation_auto_advance_sec()
        adv_note = f" · Auto {adv}s · Space Pause" if adv > 0 else ""
        pn_note = " · Nr. an" if self._presentation_page_num_on else " · Nr. aus"
        self._set_status(
            f"Präsentation — Seite {self.pdf_view.page_index + 1}/{self.pdf_view.page_count} "
            f"(←/→ Esc · N Nr.){ann_note}{adv_note}{pn_note}"
        )

    def _countdown_overlay_stylesheet(self) -> str:
        """Countdown-Farbe hell/dunkel aus Settings — 1.7.3."""
        color = get_presentation_countdown_color()
        if color == "light":
            return (
                "QLabel#presentationCountdown {"
                " background: rgba(255,255,255,220); color: #1a1a1a;"
                " font-size: 28px; font-weight: 600;"
                " padding: 8px 16px; border-radius: 8px;"
                " border: 1px solid rgba(0,0,0,40);"
                "}"
            )
        return (
            "QLabel#presentationCountdown {"
            " background: rgba(0,0,0,180); color: #ffffff;"
            " font-size: 28px; font-weight: 600;"
            " padding: 8px 16px; border-radius: 8px;"
            "}"
        )

    def _ensure_countdown_overlay(self) -> QLabel:
        """Countdown-Overlay Label (Präsentation Timer) — 1.7.3."""
        lbl = getattr(self, "_presentation_countdown", None)
        if lbl is None:
            lbl = QLabel(self)
            lbl.setObjectName("presentationCountdown")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.hide()
            self._presentation_countdown = lbl
        lbl.setStyleSheet(self._countdown_overlay_stylesheet())
        return lbl

    def _position_countdown_overlay(self) -> None:
        """Position unten-rechts oder mitte — 1.7.3."""
        lbl = getattr(self, "_presentation_countdown", None)
        if lbl is None or not lbl.isVisible():
            return
        lbl.adjustSize()
        margin = 24
        pos = get_presentation_countdown_position()
        if pos == "center":
            x = max(margin, (self.width() - lbl.width()) // 2)
            y = max(margin, (self.height() - lbl.height()) // 2)
        else:
            # bottom-right / unten-rechts
            x = max(margin, self.width() - lbl.width() - margin)
            y = max(margin, self.height() - lbl.height() - margin)
        lbl.move(x, y)
        lbl.raise_()

    def _update_countdown_overlay(self) -> None:
        """Countdown-Overlay Text/Pause/Position/Farbe — 1.7.3."""
        sec = int(getattr(self, "_presentation_interval_sec", 0) or 0)
        if (
            not self._presentation_active
            or sec <= 0
            or not getattr(self, "_presentation_timer", None)
        ):
            self._hide_countdown_overlay()
            return
        lbl = self._ensure_countdown_overlay()
        if getattr(self, "_presentation_paused", False):
            lbl.setText("❚❚ Pause")
        else:
            rem = max(0, int(getattr(self, "_presentation_remaining", 0)))
            lbl.setText(str(rem))
        lbl.show()
        self._position_countdown_overlay()

    def _hide_countdown_overlay(self) -> None:
        lbl = getattr(self, "_presentation_countdown", None)
        if lbl is not None:
            lbl.hide()

    def _start_presentation_timer(self) -> None:
        """Timer-Autoadvance mit 1s-Countdown; Intervalle 3/5/10/30 — 1.7.2."""
        self._stop_presentation_timer()
        sec = get_presentation_auto_advance_sec()
        if sec <= 0 or not self._presentation_active:
            self._hide_countdown_overlay()
            return
        self._presentation_paused = False
        self._presentation_interval_sec = int(sec)
        self._presentation_remaining = int(sec)
        self._presentation_timer = QTimer(self)
        self._presentation_timer.setInterval(1000)
        self._presentation_timer.timeout.connect(self._presentation_tick)
        self._presentation_timer.start()
        self._update_countdown_overlay()

    def _stop_presentation_timer(self) -> None:
        t = getattr(self, "_presentation_timer", None)
        if t is not None:
            try:
                t.stop()
                t.deleteLater()
            except Exception:
                pass
        self._presentation_timer = None
        self._presentation_paused = False
        self._presentation_remaining = 0
        self._presentation_interval_sec = 0
        self._hide_countdown_overlay()

    def _presentation_tick(self) -> None:
        """1s-Tick: Countdown; bei 0 Auto-Advance — 1.7.2."""
        if not self._presentation_active:
            self._stop_presentation_timer()
            return
        if getattr(self, "_presentation_paused", False):
            self._update_countdown_overlay()
            return
        rem = int(getattr(self, "_presentation_remaining", 0)) - 1
        self._presentation_remaining = rem
        if rem <= 0:
            self._presentation_auto_advance()
            if self._presentation_active and getattr(self, "_presentation_timer", None):
                self._presentation_remaining = int(
                    getattr(self, "_presentation_interval_sec", 0) or 0
                )
        self._update_countdown_overlay()

    def _toggle_presentation_pause(self) -> bool:
        """Space: Timer Pause/Resume; True wenn behandelt — 1.7.2."""
        if not self._presentation_active:
            return False
        if get_presentation_auto_advance_sec() <= 0:
            return False
        if getattr(self, "_presentation_timer", None) is None:
            self._start_presentation_timer()
            return True
        self._presentation_paused = not bool(getattr(self, "_presentation_paused", False))
        self._update_countdown_overlay()
        state = "pausiert" if self._presentation_paused else "weiter"
        self._set_status(
            f"Präsentation — Timer {state} "
            f"(noch {max(0, int(self._presentation_remaining))}s)"
        )
        return True

    def _presentation_auto_advance(self) -> None:
        if not self._presentation_active:
            self._stop_presentation_timer()
            return
        try:
            idx = int(self.pdf_view.page_index)
            total = int(self.pdf_view.page_count)
            if total <= 0:
                return
            if idx + 1 >= total:
                # am Ende: Timer stoppen (kein Loop)
                self._stop_presentation_timer()
                self._set_status(
                    f"Präsentation — Ende ({total}/{total}); Auto-Advance gestoppt"
                )
                return
            self.pdf_view.next_page()
            self._set_status(
                f"Präsentation — Seite {self.pdf_view.page_index + 1}/{self.pdf_view.page_count}"
            )
        except Exception:
            self._stop_presentation_timer()

    def _toggle_presentation_page_number(self) -> None:
        """Seitennummer-Overlay in Präsentation umschalten — 1.7.1."""
        self._presentation_page_num_on = not bool(self._presentation_page_num_on)
        set_presentation_show_page_number(self._presentation_page_num_on)
        try:
            self.pdf_view.set_show_page_number_overlay(self._presentation_page_num_on)
        except Exception:
            pass
        state = "an" if self._presentation_page_num_on else "aus"
        self._set_status(f"Präsentation — Seitennummer {state}")

    def _exit_presentation(self):
        if not self._presentation_active:
            return
        prev = self._presentation_prev or {}
        self._presentation_active = False
        self._stop_presentation_timer()
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
        try:
            self._apply_chrome_mode()
        except Exception:
            pass
        self.statusBar().setVisible(bool(prev.get("status", True)))
        self.sidebar.setVisible(bool(prev.get("sidebar", True)))
        if getattr(self, "favorites_bar", None) is not None:
            # nur wieder zeigen wenn Setting an und vorher sichtbar / Setting an
            show_bar = get_favorites_bar_visible()
            self.favorites_bar.setVisible(bool(show_bar))
        # Ann.-Overlay wiederherstellen wenn Präsentation ihn ausgeblendet hat
        if prev.get("hid_ann"):
            try:
                self.pdf_view.set_annotations_visible(bool(prev.get("ann_visible", True)))
            except Exception:
                pass
        # Seitennummer-Overlay auf Vor-Zustand
        try:
            self.pdf_view.set_show_page_number_overlay(bool(prev.get("page_num", False)))
        except Exception:
            pass
        # Stylesheet wiederherstellen
        try:
            self.setStyleSheet(str(prev.get("stylesheet") or ""))
            if self.centralWidget() is not None:
                self.centralWidget().setStyleSheet(str(prev.get("central_ss") or ""))
            self.pdf_view.setStyleSheet("")
        except Exception:
            pass
        stack_w = prev.get("stack")
        if stack_w is not None:
            self.stack.setCurrentWidget(stack_w)
        if prev.get("was_fullscreen"):
            self.showFullScreen()
        else:
            self.showNormal()
        self._presentation_prev = None
        self._set_status("Präsentationsmodus beendet")

    def eventFilter(self, obj, event):  # noqa: N802
        """Banner: Enter öffnet Aktivierung (Fokus auf Banner) — 1.0.9."""
        banner = getattr(self, "expiry_warn_banner", None)
        if (
            banner is not None
            and obj is banner
            and event.type() == QEvent.Type.KeyPress
        ):
            key = event.key()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._on_expiry_warn_clicked()
                event.accept()
                return True
            if key == Qt.Key_Escape:
                self._dismiss_expiry_warning()
                event.accept()
                return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        if self._presentation_active:
            self._position_countdown_overlay()

    def keyPressEvent(self, event):  # noqa: N802
        if self._presentation_active:
            key = event.key()
            if key in (Qt.Key_Escape, Qt.Key_F5, Qt.Key_Q):
                self._exit_presentation()
                event.accept()
                return
            if key == Qt.Key_N:
                self._toggle_presentation_page_number()
                event.accept()
                return
            # Space: Pause/Resume wenn Timer aktiv, sonst nächste Seite — 1.7.2
            if key == Qt.Key_Space:
                if self._toggle_presentation_pause():
                    event.accept()
                    return
            if key in (Qt.Key_Right, Qt.Key_Down, Qt.Key_PageDown, Qt.Key_Space, Qt.Key_Return):
                self.pdf_view.next_page()
                self._start_presentation_timer()
                self._set_status(
                    f"Präsentation — Seite {self.pdf_view.page_index + 1}/{self.pdf_view.page_count}"
                )
                event.accept()
                return
            if key in (Qt.Key_Left, Qt.Key_Up, Qt.Key_PageUp, Qt.Key_Backspace):
                self.pdf_view.prev_page()
                self._start_presentation_timer()
                self._set_status(
                    f"Präsentation — Seite {self.pdf_view.page_index + 1}/{self.pdf_view.page_count}"
                )
                event.accept()
                return
            if key == Qt.Key_Home:
                self.pdf_view.goto_page(0)
                self._start_presentation_timer()
                event.accept()
                return
            if key == Qt.Key_End and self.pdf_view.page_count > 0:
                self.pdf_view.goto_page(self.pdf_view.page_count - 1)
                self._start_presentation_timer()
                event.accept()
                return
            event.accept()
            return
        # Banner: Esc schließt; Enter öffnet Aktivierung — 1.0.9
        banner = getattr(self, "expiry_warn_banner", None)
        if banner is not None and banner.isVisible():
            key = event.key()
            if key == Qt.Key_Escape:
                self._dismiss_expiry_warning()
                event.accept()
                return
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._on_expiry_warn_clicked()
                event.accept()
                return
        # Quick-Stempel: Esc bricht Platzieren ab — 1.9.3
        if event.key() == Qt.Key_Escape:
            pv = getattr(self, "pdf_view", None)
            if pv is not None and getattr(pv, "_quick_stamp_armed", False):
                if callable(getattr(pv, "cancel_quick_stamp", None)):
                    pv.cancel_quick_stamp()
                    event.accept()
                    return
            # OCR-Region Status-Toast schließen — 2.5.11
            if getattr(self, "_ocr_region_toast_active", False):
                if self._dismiss_ocr_region_status():
                    event.accept()
                    return
        # OCR-Region Status: Enter → Ergebnis-Tab — 2.5.12
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if getattr(self, "_ocr_region_toast_active", False):
                if self._focus_ocr_region_result_tab():
                    event.accept()
                    return
        # OCR-Region Status: Ctrl+C Text · Ctrl+Shift+C Pfad — 2.5.13
        if event.key() == Qt.Key_C and bool(event.modifiers() & Qt.ControlModifier):
            if getattr(self, "_ocr_region_toast_active", False):
                if bool(event.modifiers() & Qt.ShiftModifier):
                    if self._copy_ocr_region_result_path():
                        event.accept()
                        return
                else:
                    if self._copy_ocr_region_result_text():
                        event.accept()
                        return
        # OCR-Region Status: F4 → Ordner öffnen — 2.5.14
        if event.key() == Qt.Key_F4:
            if getattr(self, "_ocr_region_toast_active", False):
                if self._open_ocr_region_result_folder():
                    event.accept()
                    return
        # OCR-Region Status: F5 → Datei öffnen — 2.5.15
        if event.key() == Qt.Key_F5:
            if getattr(self, "_ocr_region_toast_active", False):
                if self._open_ocr_region_result_file():
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
        if not self._guard_editor_action("Zeile duplizieren"):
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
        if not self._guard_editor_action("Zeile verschieben"):
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
            from instantlensdoc.ui.feature_dialog import FeatureDialog

            FeatureDialog(
                self,
                title="Zeile verschieben",
                body="Die Zeile kann in dieser Richtung nicht verschoben werden.",
                object_name="ildMoveLineDialog",
            ).exec()

    def _sort_lines_az(self):
        if not self._guard_editor_action("Zeilen sortieren"):
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
            self._feature_dialog(
                "Zeilen sortieren",
                "Nichts zu sortieren — weniger als zwei unterschiedliche Zeilen.",
                object_name="ildSortLinesDialog",
            )

    def _toggle_line_comment(self):
        if not self._guard_editor_action("Kommentieren"):
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

    def _ann_filter_is_active(self) -> bool:
        """True wenn Sidebar-Ann.-Filter (Typ/Farbe/Tags/Suche/Gruppe) aktiv — 1.1.5."""
        if not hasattr(self.sidebar, "annotation_filter_state"):
            return False
        try:
            st = self.sidebar.annotation_filter_state() or {}
        except Exception:
            return False
        return bool(
            st.get("type")
            or st.get("color")
            or st.get("tags")
            or st.get("search")
            or st.get("group_id")
        )

    def _clear_annotations_on_page(self):
        """Alle Annotationen der aktuellen PDF-Seite löschen (Bestätigung + Undo)."""
        if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
            page = int(self.pdf_view.page_index)
            filtered_ids = None
            if hasattr(self.sidebar, "visible_annotation_ids"):
                try:
                    filtered_ids = self.sidebar.visible_annotation_ids(page=page)
                except Exception:
                    filtered_ids = None
            # 0 gefilterte Treffer: Menü/Aktion no-op mit Sticky-Status — 1.1.5/1.1.7
            if (
                filtered_ids is not None
                and self._ann_filter_is_active()
                and self.pdf_view.store is not None
            ):
                anns = self.pdf_view.store.for_page(page)
                n_filt = sum(1 for a in anns if str(a.id) in {str(x) for x in filtered_ids})
                if anns and n_filt <= 0:
                    from instantlensdoc.core.i18n import tr_ann_zero_filtered

                    self._set_ann_zero_sticky_status(tr_ann_zero_filtered(page + 1))
                    return
            n = self.pdf_view.clear_annotations_on_page(
                filtered_ids=filtered_ids,
            )
            if n == 0:
                self._feature_dialog(
                    "Annotationen löschen",
                    "Keine Annotationen auf dieser Seite.",
                )
                return
            self._ann_action_status(
                f"{n} Annotation(en) auf Seite gelöscht (Ctrl+Z rückgängig)"
            )
            return
        self._set_status("Alle auf Seite löschen nur im PDF-Modus")

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
            self._clear_ann_zero_sticky_status()
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
        self._clear_ann_zero_sticky_status()
        self.pdf_view.edit_selected_annotation_text()

    def _edit_annotation_tags(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Annotation-Tags nur im PDF-Modus")
            return
        if not self.pdf_view._selected_ann_id:
            self._set_status("Keine Annotation ausgewählt")
            return
        self._clear_ann_zero_sticky_status()
        self.pdf_view.edit_selected_annotation_tags()

    def _edit_annotation_group(self, page: int | None = None):
        if not self._require_pdf("Annotationsgruppe"):
            return
        idx = None if page is None or isinstance(page, bool) else int(page)
        self.pdf_view.edit_page_annotation_group(idx)
        self._refresh_pdf_marks()

    def _recolor_selected_annotations(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Strichfarbe nur im PDF-Modus")
            return
        n = self.pdf_view.recolor_stroke_selected_annotations()
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
            self._feature_dialog("Auswahl ausrichten", "Ausrichten nur im PDF-Modus.")
            return
        n = self.pdf_view.align_selected_annotations(mode)
        if n:
            self._refresh_pdf_marks()
            return
        self._feature_dialog(
            "Auswahl ausrichten",
            "Keine Annotationen ausgewählt. Zuerst mindestens zwei Objekte markieren.",
        )

    def _distribute_selected_annotations_horizontal(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._feature_dialog("Verteilen", "Verteilen nur im PDF-Modus.")
            return
        n = self.pdf_view.distribute_selected_annotations_horizontal()
        if n:
            self._refresh_pdf_marks()
            return
        self._feature_dialog(
            "Verteilen",
            "Zu wenige Annotationen für horizontales Verteilen (mindestens 3).",
        )

    def _distribute_selected_annotations_vertical(self):
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._feature_dialog("Verteilen", "Verteilen nur im PDF-Modus.")
            return
        n = self.pdf_view.distribute_selected_annotations_vertical()
        if n:
            self._refresh_pdf_marks()
            return
        self._feature_dialog(
            "Verteilen",
            "Zu wenige Annotationen für vertikales Verteilen (mindestens 3).",
        )

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
        if not self._guard_editor_action("Zeilen-Lesezeichen"):
            return
        now = self.editor.toggle_line_bookmark()
        line = self.editor.textCursor().blockNumber() + 1
        self._refresh_line_favorites()
        self._set_status(
            f"Zeile {line} als Lesezeichen markiert"
            if now
            else f"Zeile {line} Lesezeichen entfernt"
        )

    def _goto_next_line_bookmark(self):
        if not self._guard_editor_action("Zeilen-Lesezeichen"):
            return
        cur = self.editor.textCursor().blockNumber() + 1
        line = self.editor.goto_next_line_bookmark()
        if line:
            if line == cur:
                self._feature_dialog(
                    "Nächstes Zeilen-Lesezeichen",
                    "Bereits am einzigen bzw. letzten Lesezeichen.",
                    object_name="ildLineBookmarkDialog",
                )
                return
            self._refresh_line_favorites()
            self._set_status(f"Lesezeichen → Zeile {line}")
        else:
            self._feature_dialog(
                "Nächstes Zeilen-Lesezeichen",
                "Keine Zeilen-Lesezeichen im Dokument.",
                object_name="ildLineBookmarkDialog",
            )

    def _goto_prev_line_bookmark(self):
        if not self._guard_editor_action("Zeilen-Lesezeichen"):
            return
        cur = self.editor.textCursor().blockNumber() + 1
        line = self.editor.goto_prev_line_bookmark()
        if line:
            if line == cur:
                self._feature_dialog(
                    "Vorheriges Zeilen-Lesezeichen",
                    "Bereits am einzigen bzw. ersten Lesezeichen.",
                    object_name="ildLineBookmarkDialog",
                )
                return
            self._refresh_line_favorites()
            self._set_status(f"Lesezeichen → Zeile {line}")
        else:
            self._feature_dialog(
                "Vorheriges Zeilen-Lesezeichen",
                "Keine Zeilen-Lesezeichen im Dokument.",
                object_name="ildLineBookmarkDialog",
            )

    def _clear_line_bookmarks(self):
        if not self._guard_editor_action("Zeilen-Lesezeichen"):
            return
        marks = (
            self.editor.list_line_bookmarks()
            if hasattr(self.editor, "list_line_bookmarks")
            else []
        )
        if not marks:
            self._feature_dialog(
                "Zeilen-Lesezeichen",
                "Keine Zeilen-Lesezeichen im Dokument.",
                object_name="ildLineBookmarkDialog",
            )
            return
        self.editor.clear_line_bookmarks()
        self._refresh_line_favorites()
        self._set_status("Zeilen-Lesezeichen gelöscht")

    def _export_line_bookmarks_json(self) -> bool:
        """Editor-Zeilen-Lesezeichen als JSON (ildbm-v1) exportieren."""
        from PySide6.QtWidgets import QFileDialog
        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        if not self._guard_editor_action("Zeilen-Lesezeichen"):
            return False
        marks = self.editor.list_line_bookmarks_with_labels()
        if not marks:
            self._feature_dialog(
                "Lesezeichen",
                "Keine Zeilen-Lesezeichen zum Exportieren.",
                object_name="ildLineBookmarkDialog",
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

        if not self._guard_editor_action("Zeilen-Lesezeichen"):
            return False
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
        if not self._guard_editor_action("Rechtschreibung"):
            return
        from instantlensdoc.core.app_settings import (
            get_spellcheck_dict_path,
            get_spellcheck_use_builtin,
        )

        path = get_spellcheck_dict_path()
        if not path and not get_spellcheck_use_builtin():
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                "Rechtschreibung",
                "Kein Wörterbuch-Pfad gesetzt und Builtin deaktiviert.\n"
                "Extras → Einstellungen → Rechtschreibwörterbuch (Wortliste).",
            )
            self._set_status("Rechtschreibung: kein Wörterbuch")
            return
        try:
            n = self.editor.check_spelling(path or None)
        except FileNotFoundError as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Rechtschreibung", str(e))
            self._set_status("Rechtschreibung: Wörterbuch fehlt")
            return
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Rechtschreibung", str(e))
            return
        result = self.editor.last_spell_result()
        g = int(result.get("grammar_count") or 0)
        extra = f", {g} Grammatik-Hinweis(e)" if g else ""
        self._set_status(
            f"Rechtschreibung: {n} unbekannt(e) Wort(e){extra}"
            if n or g
            else "Rechtschreibung: keine unbekannten Wörter"
        )

    def _show_spell_suggestions(self):
        """Dialog mit unbekannten Wörtern + Vorschlägen — 2.6.20."""
        if not self._guard_editor_action("Rechtschreibung"):
            return
        self._check_spelling()
        result = self.editor.last_spell_result()
        unknown = list(result.get("unknown") or [])
        from PySide6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QPushButton,
            QVBoxLayout,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Rechtschreibvorschläge — 2.6.20")
        dlg.resize(520, 360)
        lay = QVBoxLayout(dlg)
        lay.addWidget(
            QLabel(
                f"Sprache: {result.get('lang', '?')} · "
                f"{len(unknown)} unbekannt · "
                f"{int(result.get('grammar_count') or 0)} Grammatik"
            )
        )
        lst = QListWidget()
        for item in unknown:
            word = item.get("word") or ""
            sugg = item.get("suggestions") or []
            line = word
            if sugg:
                line += " → " + ", ".join(str(s) for s in sugg[:5])
            wi = QListWidgetItem(line)
            wi.setData(Qt.UserRole, item)
            lst.addItem(wi)
        lay.addWidget(lst, 1)
        row = QHBoxLayout()
        btn_apply = QPushButton("Ersten Vorschlag anwenden")
        btn_apply.setToolTip("Ersetzt das markierte Wort durch den ersten Vorschlag")
        row.addWidget(btn_apply)
        row.addStretch(1)
        lay.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        lay.addWidget(buttons)

        def _apply():
            cur = lst.currentItem()
            if cur is None:
                return
            data = cur.data(Qt.UserRole) or {}
            sugg = data.get("suggestions") or []
            if not sugg:
                self._set_status("Kein Vorschlag für dieses Wort")
                return
            ok = self.editor.apply_spell_suggestion(
                int(data["start"]), int(data["end"]), str(sugg[0])
            )
            if ok:
                self._set_status(f"Ersetzt: {data.get('word')} → {sugg[0]}")
                self._check_spelling()
                dlg.accept()

        btn_apply.clicked.connect(_apply)
        dlg.exec()

    def _toggle_autocorrect(self, checked: bool = False):
        from instantlensdoc.core.app_settings import (
            get_autocorrect_enabled,
            set_autocorrect_enabled,
        )

        if isinstance(checked, bool) and self.sender() is getattr(
            self, "_autocorrect_action", None
        ):
            want = bool(checked)
        else:
            want = not get_autocorrect_enabled()
        set_autocorrect_enabled(want)
        if getattr(self, "_autocorrect_action", None) is not None:
            self._autocorrect_action.blockSignals(True)
            self._autocorrect_action.setChecked(want)
            self._autocorrect_action.blockSignals(False)
        if getattr(self, "ribbon_bar", None) is not None:
            self.ribbon_bar.set_checked("autocorrect_toggle", want)
        self._set_status("Autokorrektur ein" if want else "Autokorrektur aus")

    def _clear_spelling(self):
        if not self._guard_editor_action("Rechtschreibung"):
            return
        self.editor.clear_spelling()
        self._set_status("Rechtschreibmarkierungen gelöscht")

    def _collab_doc_path(self) -> str | None:
        """Pfad für lokale Review-/Kommentar-/Versions-Sidecars — 2.6.21."""
        if self.doc and self.doc.path:
            return str(self.doc.path)
        if getattr(self.pdf_view, "pdf_path", None):
            return str(self.pdf_view.pdf_path)
        return None

    def _goto_editor_range(self, start: int, end: int) -> None:
        from PySide6.QtGui import QTextCursor

        self.stack.setCurrentWidget(self.editor_pane)
        cur = self.editor.textCursor()
        cur.setPosition(max(0, int(start)))
        cur.setPosition(max(0, int(end)), QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cur)
        self.editor.setFocus()

    def _show_review_dialog(self):
        from instantlensdoc.ui.review_dialog import ReviewDialog

        path = self._collab_doc_path()
        if not path:
            # Unbenannt: temporärer Sidecar-Anker unter config
            from instantlensdoc.config import config_dir

            path = str(config_dir() / "untitled.ildreview-anchor.txt")
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            if not Path(path).is_file():
                Path(path).write_text("", encoding="utf-8")
        dlg = ReviewDialog(
            path, self, on_goto=self._goto_editor_range
        )
        # Review-Toggle → Editor-Tracking
        if dlg.exec() is not None:
            pass
        try:
            from instantlensdoc.core.review import ReviewStore

            store = ReviewStore.for_doc(path, load=True)
            if getattr(self, "ribbon_bar", None) is not None:
                self.ribbon_bar.set_checked("review_mode", store.enabled)
            if hasattr(self.editor, "set_review_tracking"):
                self.editor.set_review_tracking(
                    store.enabled, path=path, author=store.author
                )
            self._set_status(
                f"Review {'ein' if store.enabled else 'aus'} · "
                f"pending {store.summary()['pending']}"
            )
        except Exception as e:
            self._set_status(f"Review: {e}")

    def _show_shared_review_dialog(self):
        """Gemeinsames Review starten/beitreten — Freigabeordner/Endpoint — 2.6.23."""
        from instantlensdoc.ui.shared_review_dialog import SharedReviewDialog

        path = self._collab_doc_path()
        if not path:
            from instantlensdoc.config import config_dir

            path = str(config_dir() / "untitled.ildshare-anchor.txt")
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            if not Path(path).is_file():
                Path(path).write_text("", encoding="utf-8")
        author = "local"
        try:
            from instantlensdoc.core.review import ReviewStore

            author = ReviewStore.for_doc(path, load=True).author or "local"
        except Exception:
            pass

        def _on_synced(result: dict) -> None:
            n = result.get("item_count")
            action = result.get("action")
            self._set_status(
                f"Shared Review {action}: {n} Items · "
                f"{result.get('participant_count', 0)} Teilnehmer"
            )
            # Annotation-/Kommentar-UI aktualisieren falls vorhanden
            try:
                if hasattr(self, "pdf_view") and self.pdf_view is not None:
                    store = getattr(self.pdf_view, "store", None)
                    if store is not None and hasattr(store, "load"):
                        store.load()
                        if hasattr(self.pdf_view, "refresh"):
                            self.pdf_view.refresh()
                        elif hasattr(self.pdf_view, "_redraw"):
                            self.pdf_view._redraw()
            except Exception:
                pass
            try:
                self._refresh_pdf_marks()
            except Exception:
                pass

        dlg = SharedReviewDialog(
            path, self, author=author, on_synced=_on_synced
        )
        dlg.exec()

    def _show_comments_dialog(self):
        from instantlensdoc.ui.comments_dialog import CommentsDialog

        path = self._collab_doc_path()
        if not path:
            from instantlensdoc.config import config_dir

            path = str(config_dir() / "untitled.ildcomments-anchor.txt")
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            if not Path(path).is_file():
                Path(path).write_text("", encoding="utf-8")
        cur = self.editor.textCursor()
        start, end = cur.selectionStart(), cur.selectionEnd()
        anchor = cur.selectedText().replace("\u2029", "\n")
        dlg = CommentsDialog(
            path,
            self,
            selection_start=start,
            selection_end=end,
            anchor_text=anchor,
            on_goto=self._goto_editor_range,
        )
        dlg.exec()
        self._set_status("Kommentare aktualisiert")

    def _show_version_history_dialog(self):
        from instantlensdoc.ui.version_history_dialog import VersionHistoryDialog

        path = self._collab_doc_path()
        if not path:
            from instantlensdoc.config import config_dir

            path = str(config_dir() / "untitled.ildversions-anchor.txt")
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            if not Path(path).is_file():
                Path(path).write_text(
                    self.editor.toPlainText(), encoding="utf-8"
                )

        def _restore(text: str) -> None:
            self.stack.setCurrentWidget(self.editor_pane)
            self.editor.setPlainText(text)
            if self.doc is not None:
                self.doc.text = text
                self.doc.dirty = True
            self._set_status("Version wiederhergestellt")

        dlg = VersionHistoryDialog(
            path,
            self,
            current_text=self.editor.toPlainText(),
            on_restore_text=_restore,
        )
        dlg.exec()

    def _run_mail_merge_dialog(self, focus: str | None = None):
        if not isinstance(focus, str):
            focus = None
        tpl_text = None
        if self.stack.currentWidget() is self.editor_pane:
            text = self.editor.toPlainText().strip()
            if text:
                tpl_text = text
        dlg = MailMergeDialog(self, template_text=tpl_text, editor=self.editor)
        if focus == "data":
            QTimer.singleShot(0, dlg._pick_rec)
        elif focus == "field":
            QTimer.singleShot(0, dlg.insert_current_field)
        elif focus == "preview":
            QTimer.singleShot(0, dlg._preview)
        elif focus == "run":
            QTimer.singleShot(0, dlg._run)
        dlg.exec()
        data = dlg.result_data()
        if data:
            self._set_status(
                f"Seriendruck: {data.get('count', 0)} Brief(e) → {data.get('out_dir')}"
            )

    def _run_esign_dialog(self):
        pdf = str(self.pdf_view.pdf_path) if self.pdf_view.pdf_path else None
        dlg = ESignDialog(self, pdf_path=pdf)
        dlg.exec()
        data = dlg.result_data()
        if data and data.get("out"):
            self._set_status(f"Signiert: {data['out']}")

    def _insert_soft_hyphen(self):
        if not self._guard_editor_action("Sonderzeichen"):
            return
        if self.editor.insert_soft_hyphen():
            self._set_status("Soft-Hyphen eingefügt (U+00AD)")

    def _insert_nbsp(self):
        if not self._guard_editor_action("Sonderzeichen"):
            return
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
        """Kopieren: PDF-Textauswahl bevorzugt, sonst Editor (Zeile ohne Auswahl)."""
        if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
            if self.pdf_view.copy_text_selection():
                return
        from PySide6.QtCore import QMimeData
        from PySide6.QtGui import QGuiApplication, QTextCursor
        import time as _time

        ed = getattr(self, "editor", None)
        if ed is None:
            return
        cur = ed.textCursor()
        if cur.hasSelection():
            text = cur.selectedText().replace("\u2029", "\n")
        else:
            restore = QTextCursor(cur)
            line = QTextCursor(cur)
            line.select(QTextCursor.LineUnderCursor)
            text = line.selectedText().replace("\u2029", "\n")
            ed.setTextCursor(restore)
        md = QMimeData()
        md.setText(text)
        md.setData("application/x-ild-copy", str(_time.time_ns()).encode("utf-8"))
        cb = QGuiApplication.clipboard()
        if cb is not None:
            cb.setMimeData(md)

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

    def _sync_doc_split_sync_action_a11y_tip(self, checked: bool) -> None:
        """Menü-Tooltip mit an/aus; Status-AccessibleName kommt separat — 2.4.5."""
        act = getattr(self, "_doc_split_sync_action", None)
        if act is None:
            return
        state = "an" if checked else "aus"
        try:
            act.setToolTip(
                f"Sync-Scroll {state} — nur PDF↔PDF: Scroll-Ratio + Seiten-Sync "
                f"(Ctrl+Alt+\\); Status-AccessibleName live an/aus — 2.4.5"
            )
        except Exception:
            pass
        # Falls Qt/PySide AccessibleName an QAction unterstützt
        try:
            setter = getattr(act, "setAccessibleName", None)
            if callable(setter):
                setter(f"Sync-Scroll {state}")
        except Exception:
            pass

    def _toggle_doc_split_sync_scroll(self, checked: bool):
        from instantlensdoc.core.app_settings import set_editor_doc_split_sync_scroll

        set_editor_doc_split_sync_scroll(bool(checked))
        self._apply_doc_split_sync_scroll()
        self._save_session()
        # Tooltip/AccessibleName Action live an/aus — 2.4.5
        self._sync_doc_split_sync_action_a11y_tip(bool(checked))
        self._update_sync_scroll_status_indicator()
        if checked:
            both_pdf = self._split_both_pdf()
            msg = (
                "Sync-Scroll an (PDF↔PDF + Seiten-Sync)"
                if both_pdf
                else "Sync-Scroll an — aktiv nur bei PDF↔PDF"
            )
        else:
            msg = "Sync-Scroll aus"
        self._set_status(msg)
        # A11y Announcement bei Toggle — 2.4.4
        try:
            self._announce_status_toast(msg)
        except Exception:
            pass

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

    def _split_both_pdf(self) -> bool:
        """True wenn Haupt- und Zweit-Panel PDF sind — 2.4.0."""
        if not hasattr(self, "secondary_wrap") or not self.secondary_wrap.isVisible():
            return False
        if self.stack.currentWidget() is not self.pdf_view:
            return False
        if not hasattr(self, "secondary_stack") or not hasattr(self, "secondary_pdf"):
            return False
        return self.secondary_stack.currentWidget() is self.secondary_pdf

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
        # PDF-Seiten-Sync lösen — 2.4.0 (nur wenn verbunden)
        if getattr(self, "_sync_page_hooks", False):
            try:
                self.pdf_view.page_changed.disconnect(self._on_primary_page_sync)
            except (TypeError, RuntimeError):
                pass
            if hasattr(self, "secondary_pdf"):
                try:
                    self.secondary_pdf.page_changed.disconnect(
                        self._on_secondary_page_sync
                    )
                except (TypeError, RuntimeError):
                    pass
            self._sync_page_hooks = False

    def _apply_doc_split_sync_scroll(self) -> None:
        """Sync-Scroll nur PDF↔PDF: Scroll-Ratio + Seiten-Sync — 2.4.1."""
        self._disconnect_doc_split_sync_scroll()
        if not hasattr(self, "secondary_wrap") or not self.secondary_wrap.isVisible():
            self._update_sync_scroll_status_indicator()
            return
        if not get_editor_doc_split_sync_scroll():
            self._update_sync_scroll_status_indicator()
            return
        # Nur PDF↔PDF — kein Sync mit Editor-Panels — 2.4.1
        if not self._split_both_pdf():
            self._update_sync_scroll_status_indicator()
            return
        primary = self._primary_scroll_bar()
        secondary = self._secondary_scroll_bar()
        if primary is None or secondary is None:
            self._update_sync_scroll_status_indicator()
            return
        self._sync_primary_bar = primary
        self._sync_secondary_bar = secondary
        primary.valueChanged.connect(self._on_primary_scroll_sync)
        secondary.valueChanged.connect(self._on_secondary_scroll_sync)
        self.pdf_view.page_changed.connect(self._on_primary_page_sync)
        self.secondary_pdf.page_changed.connect(self._on_secondary_page_sync)
        self._sync_page_hooks = True
        self._update_sync_scroll_status_indicator()

    def _on_sync_scroll_status_clicked(self, event=None) -> None:
        """Statusleisten-Klick toggled Sync-Scroll — 2.4.2."""
        from instantlensdoc.core.app_settings import get_sync_scroll_status_indicator

        if not get_sync_scroll_status_indicator():
            return
        act = getattr(self, "_doc_split_sync_action", None)
        if act is not None:
            act.toggle()
        else:
            from instantlensdoc.core.app_settings import (
                get_editor_doc_split_sync_scroll,
                set_editor_doc_split_sync_scroll,
            )

            nxt = not get_editor_doc_split_sync_scroll()
            set_editor_doc_split_sync_scroll(nxt)
            self._toggle_doc_split_sync_scroll(nxt)

    def _on_thumb_prune_status(self, msg: str) -> None:
        """
        Callback: Auto-Prune Toast Dauer OCR-Settings; Status kopierbar —
        Klick kopiert erneut — 2.4.5.
        """
        text = (msg or "").strip()
        if not text:
            return
        self._last_thumb_prune_status = text
        self._thumb_prune_status_active = True
        tip = (
            "Klick kopiert Auto-Prune Status erneut "
            "(Dauer OCR-Toast-Settings) — 2.4.5"
        )
        try:
            from instantlensdoc.core.app_settings import (
                get_ocr_defaults_toast_sec,
                get_thumb_cache_prune_toast,
            )

            show_toast = bool(get_thumb_cache_prune_toast())
            if show_toast:
                try:
                    ms = max(1, int(get_ocr_defaults_toast_sec())) * 1000
                except Exception:
                    ms = 2000
                self.statusBar().showMessage(text, ms)
                self.statusBar().setToolTip(tip)
                self.statusBar().setCursor(Qt.PointingHandCursor)
                try:
                    self._announce_status_toast(text)
                except Exception:
                    pass
            else:
                # Ohne Toast: Status dauerhaft (länger) + kopierbar — 2.4.5
                self.statusBar().showMessage(text, 15000)
                self.statusBar().setToolTip(tip)
                self.statusBar().setCursor(Qt.PointingHandCursor)
        except Exception:
            try:
                self._set_status(text)
            except Exception:
                pass

    def _copy_thumb_prune_status_to_clipboard(self) -> bool:
        """
        Auto-Prune Status in Zwischenablage; Toast Dauer OCR-Settings;
        Klick danach kopiert erneut — 2.4.5.
        """
        text = (getattr(self, "_last_thumb_prune_status", "") or "").strip()
        if not text:
            cur = self.statusBar().currentMessage() or ""
            if "Thumb Auto-Prune" in cur:
                text = cur.strip()
        if not text:
            return False
        try:
            from PySide6.QtWidgets import QApplication

            clip = QApplication.clipboard()
            if clip is not None:
                clip.setText(text.rstrip() + "\n")
        except Exception:
            return False
        toast = "Auto-Prune Status kopiert"
        # Aktiv lassen: erneuter Klick kopiert denselben Status erneut — 2.4.5
        self._thumb_prune_status_active = True
        try:
            self._announce_status_toast(toast)
        except Exception:
            pass
        try:
            from instantlensdoc.core.app_settings import get_ocr_defaults_toast_sec

            ms = max(1, int(get_ocr_defaults_toast_sec())) * 1000
        except Exception:
            ms = 2000
        self.statusBar().showMessage(toast, ms)
        self.statusBar().setToolTip(
            "Klick kopiert Auto-Prune Status erneut "
            "(Dauer OCR-Toast-Settings) — 2.4.5"
        )
        self.statusBar().setCursor(Qt.PointingHandCursor)
        return True

    def _sync_thumb_prune_timer(self) -> None:
        """Intervall-Timer für Thumb Auto-Prune starten/stoppen — 2.4.3."""
        from instantlensdoc.core.app_settings import (
            THUMB_CACHE_PRUNE_MODE_INTERVAL,
            get_thumb_cache_prune_interval_min,
            get_thumb_cache_prune_mode,
        )

        t = getattr(self, "_thumb_prune_timer", None)
        if t is None:
            return
        mode = get_thumb_cache_prune_mode()
        if mode == THUMB_CACHE_PRUNE_MODE_INTERVAL:
            mins = max(1, int(get_thumb_cache_prune_interval_min()))
            t.setInterval(mins * 60 * 1000)
            if not t.isActive():
                t.start()
        else:
            t.stop()

    def _thumb_prune_tick(self) -> None:
        """Periodisches Auto-Prune (Intervall-Modus) — 2.4.3."""
        try:
            from instantlensdoc.core.thumb_cache import auto_prune_thumb_cache

            auto_prune_thumb_cache(announce=True)
        except Exception:
            pass

    def _announce_sync_scroll_accessible_name(self, name: str) -> None:
        """AccessibleName live setzen + NameChanged (an/aus im Namen) — 2.4.5."""
        lbl = getattr(self, "sync_scroll_status_label", None)
        if lbl is None:
            return
        try:
            lbl.setAccessibleName(name)
        except Exception:
            pass
        try:
            from PySide6.QtGui import QAccessible, QAccessibleEvent

            ev = QAccessibleEvent(lbl, QAccessible.Event.NameChanged)
            QAccessible.updateAccessibility(ev)
        except Exception:
            pass

    def _update_sync_scroll_status_indicator(self) -> None:
        """Statusleiste: Sync an/aus; AccessibleName live bei Toggle — 2.4.5."""
        if not hasattr(self, "sync_scroll_status_label"):
            return
        from instantlensdoc.core.app_settings import (
            get_editor_doc_split_sync_scroll,
            get_sync_scroll_status_indicator,
        )

        show_pref = get_sync_scroll_status_indicator()
        enabled = get_editor_doc_split_sync_scroll()
        active = bool(enabled and self._split_both_pdf())
        tip_suffix = " · Klick toggled · Shortcut Ctrl+Alt+\\ — 2.4.5"
        # AccessibleName mit an/aus — live bei Toggle — 2.4.5
        widget_name = "Sync-Scroll Status"
        if not show_pref:
            self.sync_scroll_status_label.setVisible(False)
            self.sync_scroll_status_label.setText("")
            self._announce_sync_scroll_accessible_name(
                f"{widget_name}: ausgeblendet"
            )
            self.sync_scroll_status_label.setAccessibleDescription(
                "Sync-Scroll Status-Widget ausgeblendet (Einstellungen)."
            )
            return
        if not enabled:
            tip = "Sync-Scroll: Zustand aus — nur PDF↔PDF" + tip_suffix
            self.sync_scroll_status_label.setText("Sync aus")
            self.sync_scroll_status_label.setStyleSheet(
                "QLabel#syncScrollStatus { color: #888; padding-right: 8px; font-size: 11px; }"
            )
            self.sync_scroll_status_label.setToolTip(tip)
            self._announce_sync_scroll_accessible_name(f"{widget_name}: aus")
            self.sync_scroll_status_label.setAccessibleDescription(tip)
            self.sync_scroll_status_label.setVisible(True)
            return
        if active:
            tip = (
                "Sync-Scroll: Zustand an — aktiv (PDF↔PDF Scroll + Seiten)"
                + tip_suffix
            )
            self.sync_scroll_status_label.setText("Sync an")
            self.sync_scroll_status_label.setStyleSheet(
                "QLabel#syncScrollStatus { color: #2d5a27; padding-right: 8px; "
                "font-size: 11px; font-weight: 500; }"
            )
            self.sync_scroll_status_label.setToolTip(tip)
            self._announce_sync_scroll_accessible_name(f"{widget_name}: an")
            self.sync_scroll_status_label.setAccessibleDescription(tip)
            self.sync_scroll_status_label.setVisible(True)
        else:
            tip = (
                "Sync-Scroll: Zustand an (bereit) — nur bei zwei PDF-Tabs aktiv"
                + tip_suffix
            )
            self.sync_scroll_status_label.setText("Sync bereit")
            self.sync_scroll_status_label.setStyleSheet(
                "QLabel#syncScrollStatus { color: #a60; padding-right: 8px; font-size: 11px; }"
            )
            self.sync_scroll_status_label.setToolTip(tip)
            # „an“ im Namen (bereit = an, aber ohne zwei PDFs) — 2.4.5
            self._announce_sync_scroll_accessible_name(
                f"{widget_name}: an (bereit)"
            )
            self.sync_scroll_status_label.setAccessibleDescription(tip)
            self.sync_scroll_status_label.setVisible(True)

    def _update_thumb_cache_debug_status(self) -> None:
        """Optional Hit/Miss in Statusleiste — 2.4.1."""
        if not hasattr(self, "thumb_cache_debug_label"):
            return
        from instantlensdoc.core.app_settings import get_thumb_cache_debug_hits
        from instantlensdoc.core.thumb_cache import hit_miss_stats

        if not get_thumb_cache_debug_hits():
            self.thumb_cache_debug_label.setVisible(False)
            self.thumb_cache_debug_label.setText("")
            return
        st = hit_miss_stats()
        self.thumb_cache_debug_label.setText(
            f"Cache {st['hits']}✓/{st['misses']}✗ ({st['hit_rate_pct']:.0f}%)"
        )
        self.thumb_cache_debug_label.setToolTip(
            f"Thumb-Cache Hit/Miss Debug: {st['hits']} Hits, {st['misses']} Misses "
            f"({st['hit_rate_pct']:.1f} %) — 2.4.1"
        )
        self.thumb_cache_debug_label.setVisible(True)

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

    def _on_primary_page_sync(self, page: int = 0) -> None:
        """PDF+PDF Split: Seite im Zweit-Panel mitziehen — 2.4.0."""
        if getattr(self, "_split_page_syncing", False):
            return
        if not self._split_both_pdf() or not get_editor_doc_split_sync_scroll():
            return
        self._split_page_syncing = True
        try:
            sec = self.secondary_pdf
            target = max(0, min(int(page), int(sec.page_count or 1) - 1))
            if int(getattr(sec, "page_index", -1)) != target:
                sec.goto_page(target)
        except Exception:
            pass
        finally:
            self._split_page_syncing = False

    def _on_secondary_page_sync(self, page: int = 0) -> None:
        """PDF+PDF Split: Seite im Haupt-Panel mitziehen — 2.4.0."""
        if getattr(self, "_split_page_syncing", False):
            return
        if not self._split_both_pdf() or not get_editor_doc_split_sync_scroll():
            return
        self._split_page_syncing = True
        try:
            prim = self.pdf_view
            target = max(0, min(int(page), int(prim.page_count or 1) - 1))
            if int(getattr(prim, "page_index", -1)) != target:
                prim.goto_page(target)
        except Exception:
            pass
        finally:
            self._split_page_syncing = False

    def _open_ann_templates(self) -> None:
        """Annotation-Vorlagen (ildtmpl-v1) laden/speichern — 2.4.0."""
        from instantlensdoc.core.app_settings import (
            get_ann_highlight_color,
            get_ann_pen_color,
        )
        from instantlensdoc.ui.ann_templates_dialog import AnnTemplatesDialog

        dlg = AnnTemplatesDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.applied is not None:
            t = dlg.applied
            # zuletzt verwendet wird in apply_template gemerkt — 2.4.2
            # Viewer-Farben aus Settings nachziehen
            try:
                if t.kind == "highlight":
                    self.pdf_view._highlight_color = get_ann_highlight_color()
                    if hasattr(self.pdf_view, "btn_hl_color") and hasattr(
                        self.pdf_view, "_style_color_btn"
                    ):
                        self.pdf_view._style_color_btn(
                            self.pdf_view.btn_hl_color, self.pdf_view._highlight_color
                        )
                else:
                    self.pdf_view._pen_color = get_ann_pen_color()
                    if hasattr(self.pdf_view, "btn_pen_color") and hasattr(
                        self.pdf_view, "_style_color_btn"
                    ):
                        self.pdf_view._style_color_btn(
                            self.pdf_view.btn_pen_color, self.pdf_view._pen_color
                        )
            except Exception:
                pass
            self.pdf_view.refresh()
            kind_de = "Stempel" if t.kind == "stamp" else "Highlight"
            self._set_status(f"Vorlage „{t.name}“ angewandt ({kind_de})")

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
                        self.secondary_pdf._persist_ann_lock = False
                        self.secondary_pdf.set_annotations_locked(True, persist=False)
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
        self._sync_book_layout_action()

    def _toggle_book_layout(self, checked: bool):
        self.pdf_view.set_book_layout(bool(checked))
        self._sync_book_layout_action(bool(checked))
        self._sync_spread_action()
        self._sync_continuous_action()
        if getattr(self, "ribbon_bar", None) is not None:
            self.ribbon_bar.set_checked("book_layout", bool(checked))

    def _toggle_continuous_scroll(self, checked: bool):
        self.pdf_view.set_continuous_scroll(bool(checked))
        self._sync_continuous_action(bool(checked))
        self._sync_spread_action()
        self._sync_book_layout_action()
        self._sync_page_by_page_action()

    def _toggle_page_by_page(self, checked: bool):
        self.pdf_view.set_page_by_page(bool(checked))
        self._sync_page_by_page_action(bool(checked))
        self._sync_continuous_action()
        if getattr(self, "ribbon_bar", None) is not None:
            self.ribbon_bar.set_checked("page_by_page", bool(checked))

    def _toggle_doc_tabs(self, checked: bool):
        from instantlensdoc.core.app_settings import set_doc_tabs_visible

        set_doc_tabs_visible(bool(checked))
        if getattr(self, "doc_tab_bar", None) is not None:
            if checked:
                self._refresh_doc_tab_bar()
            else:
                self.doc_tab_bar.setVisible(False)
        if getattr(self, "ribbon_bar", None) is not None:
            self.ribbon_bar.set_checked("toggle_doc_tabs", bool(checked))

    def _set_chrome_mode(self, mode: str) -> None:
        from instantlensdoc.ui.chrome import apply_chrome, set_chrome_mode

        resolved = set_chrome_mode(mode)
        apply_chrome(self, resolved)
        labels = {
            "klassisch": "Klassisch (Pull-down)",
            "ribbon": "Ribbon",
            "kombiniert": "Kombiniert",
        }
        self._set_status(f"Oberfläche: {labels.get(resolved, resolved)}")

    def _apply_chrome_mode(self, mode: str | None = None) -> None:
        from instantlensdoc.ui.chrome import apply_chrome

        apply_chrome(self, mode)

    def _toggle_style_pane(self) -> None:
        dock = getattr(self, "style_dock", None)
        if dock is None:
            return
        dock.setVisible(not dock.isVisible())
        pane = getattr(self, "style_pane", None)
        if pane is not None and hasattr(pane, "refresh"):
            pane.refresh()

    def _toggle_ribbon(self, checked: bool):
        from instantlensdoc.ui.chrome import CHROME_KLASSISCH, CHROME_KOMBINIERT

        self._set_chrome_mode(CHROME_KOMBINIERT if checked else CHROME_KLASSISCH)

    def _sync_table_tools(self) -> None:
        rb = getattr(self, "ribbon_bar", None)
        if rb is None or not hasattr(rb, "set_table_tools_visible"):
            return
        in_table = False
        try:
            if self.stack.currentWidget() is self.editor_pane:
                in_table = self.editor.current_qtext_table() is not None
        except Exception:
            in_table = False
        rb.set_table_tools_visible(bool(in_table))

    _RIBBON_ACTION_OBJECT_NAMES: dict[str, str] = {
        "open": "actFileOpen",
        "save": "actFileSave",
        "save_as": "actFileSaveAs",
        "bold": "actEditBold",
        "italic": "actEditItalic",
        "underline": "actEditUnderline",
        "strike": "actEditStrike",
        "font": "actEditFont",
        "font_color": "actEditFontColor",
        "highlight_color": "actEditBackgroundColor",
        "clear_formatting": "actEditClearFormatting",
        "align_left": "actEditAlignLeft",
        "align_center": "actEditAlignCenter",
        "align_right": "actEditAlignRight",
        "align_justify": "actEditAlignJustify",
        "bullet_list": "actEditBulletList",
        "numbered_list": "actEditNumberedList",
        "paragraph": "actEditParagraph",
        "page_size_a4": "actPageLayoutA4",
        "page_size_letter": "actPageLayoutLetter",
        "page_size_legal": "actPageLayoutLegal",
        "page_portrait": "actPageLayoutPortrait",
        "page_landscape": "actPageLayoutLandscape",
        "header_footer": "actHeaderFooter",
        "field_token": "actFieldToken",
        "find_replace": "actEditFindReplace",
        "spellcheck": "actEditSpellcheck",
        "insert_hyperlink": "actEditHyperlink",
        "insert_table": "actEditInsertTable",
        "insert_break": "actEditInsertPageBreak",
        "style_normal": "actEditStyle_normal",
        "style_h1": "actEditStyle_h1",
        "style_h2": "actEditStyle_h2",
        "style_h3": "actEditStyle_h3",
        "style_quote": "actEditStyle_quote",
        "style_title": "actEditStyle_title",
        "style_list": "actEditStyle_list",
        "mail_merge": "actMailMerge",
        "styles_pane": "actStylesPane",
        "chrome_klassisch": "actChrome_klassisch",
        "chrome_ribbon": "actChrome_ribbon",
        "chrome_kombiniert": "actChrome_kombiniert",
        "review_mode": "actReviewMode",
        "doc_comments": "actDocComments",
        "version_history": "actVersionHistory",
        "page_layout": "actPageLayout",
        "compare_pdfs": "actComparePdfs",
        "preflight": "actPreflight",
        "apply_bleed": "actBleed",
        "export_pdfx": "actExportPdfX",
        "insert_shape": "actInsertShape",
        "scan_import": "actScanImport",
        "devices_discover": "actDevicesDiscover",
        "devices_printers": "actDevicesPrinters",
        "devices_refresh": "actDevicesRefresh",
        "book_layout": "actBookLayout",
        "page_by_page": "actPageByPage",
        "continuous_scroll": "actContinuousScroll",
        "toggle_doc_tabs": "actDocTabs",
        "toggle_ribbon": "actRibbon",
        "auto_toc": "actEditAutoToc",
        "auto_lof": "actEditAutoLof",
        "auto_index": "actEditAutoIndex",
        "shared_review": "actSharedReview",
        "dtp_layout": "actLayoutMode",
        "ki_assistant": "actKiAssistant",
        "varfonts": "actVariableFonts",
        "pades_sign": "actPadesSign",
        "dtp_text_path": "actTextOnPath",
        "dtp_glyphs": "actGlyphPalette",
        "detach_window": "actDetachDocumentWindow",
    }

    def _bind_ribbon_qactions(self) -> None:
        """Pulldown und Ribbon klicken dieselbe QAction (Classic bleibt eine Spalte)."""
        by_name: dict[str, object] = {}
        try:
            from PySide6.QtGui import QAction

            for act in self.findChildren(QAction):
                n = (act.objectName() or "").strip()
                if n:
                    by_name[n] = act
        except Exception:
            by_name = {}
        mapping: dict[str, object] = {}
        for aid, objn in self._RIBBON_ACTION_OBJECT_NAMES.items():
            act = by_name.get(objn)
            if act is not None:
                mapping[aid] = act
        for aid, attr in (
            ("undo", "_undo_action"),
            ("redo", "_redo_action"),
            ("page_layout", "_page_layout_action"),
            ("book_layout", "_book_layout_action"),
            ("page_by_page", "_page_by_page_action"),
            ("continuous_scroll", "_continuous_action"),
            ("toggle_doc_tabs", "_doc_tabs_action"),
            ("toggle_ribbon", "_ribbon_action"),
            ("dtp_layout", "_layout_mode_action"),
        ):
            if aid not in mapping:
                act = getattr(self, attr, None)
                if act is not None:
                    mapping[aid] = act
        self._ribbon_qactions = mapping
        rb = getattr(self, "ribbon_bar", None)
        if rb is not None and hasattr(rb, "bind_qactions"):
            rb.bind_qactions(mapping)

    def _on_ribbon_action(self, action_id: str) -> None:
        """Ribbon: gebundene QAction (Pulldown-Parität), sonst Handler."""
        aid = str(action_id or "")
        if aid.startswith("style:"):
            self._apply_paragraph_style(aid.split(":", 1)[1])
            return
        act = (getattr(self, "_ribbon_qactions", None) or {}).get(aid)
        if act is not None:
            try:
                if act.isEnabled():
                    act.trigger()
                    return
            except Exception:
                pass
        handlers = {
            "open": self.open_dialog,
            "save": self.save_doc,
            "save_as": self.save_as,
            "auto_lof": self._update_figure_list,
            "auto_index": self._update_index,
            "auto_toc": self._update_auto_toc,
            "compare_pdfs": self._compare_pdfs,
            "find_replace": self._find_replace,
            "spellcheck": self._check_spelling,
            "undo": self._undo,
            "redo": self._redo,
            "bold": self._toggle_bold,
            "italic": self._toggle_italic,
            "underline": self._toggle_underline,
            "strike": self._toggle_strike,
            "highlight": self._mark_selection,
            "highlight_color": self._choose_highlight_color,
            "align_left": lambda: self._set_paragraph_alignment("left"),
            "align_center": lambda: self._set_paragraph_alignment("center"),
            "align_right": lambda: self._set_paragraph_alignment("right"),
            "align_justify": lambda: self._set_paragraph_alignment("justify"),
            "bullet_list": lambda: self._toggle_list(ordered=False),
            "numbered_list": lambda: self._toggle_list(ordered=True),
            "indent": self._indent_selection,
            "outdent": self._outdent_selection,
            "clear_formatting": self._clear_formatting,
            "font": self._choose_font,
            "font_color": self._choose_font_color,
            "insert_table": self._insert_table_dialog,
            "insert_break": lambda: self._insert_break("page"),
            "autocorrect_toggle": self._toggle_autocorrect,
            "insert_snippet": lambda: self._insert_snippet(0),
            "review_mode": self._show_review_dialog,
            "doc_comments": self._show_comments_dialog,
            "shared_review": self._show_shared_review_dialog,
            "version_history": self._show_version_history_dialog,
            "mail_merge": self._run_mail_merge_dialog,
            "batch_pdf": self._batch_convert,
            "esign": self._run_esign_dialog,
            "book_layout": lambda: self._toggle_book_layout(
                not self.pdf_view.book_layout_enabled()
            ),
            "page_by_page": lambda: self._toggle_page_by_page(
                not self.pdf_view.page_by_page_enabled()
            ),
            "continuous_scroll": lambda: self._toggle_continuous_scroll(
                not self.pdf_view.continuous_scroll_enabled()
            ),
            "toggle_doc_tabs": lambda: self._toggle_doc_tabs(
                not (
                    getattr(self, "doc_tab_bar", None) is not None
                    and self.doc_tab_bar.isVisible()
                )
            ),
            "toggle_ribbon": lambda: self._toggle_ribbon(
                not (
                    getattr(self, "ribbon_bar", None) is not None
                    and self.ribbon_bar.isVisible()
                )
            ),
            "doc_split": self._toggle_doc_split_from_ribbon,
            "detach_window": self._detach_current_document,
            "page_layout": self._show_page_layout_dialog,
            "preflight": self._run_preflight,
            "apply_bleed": self._apply_bleed_dialog,
            "export_pdfx": self._export_pdfx,
            "export_epub": lambda: self._export_editor("epub"),
            "export_pptx": lambda: self._export_editor("pptx"),
            "insert_hyperlink": self._insert_hyperlink_dialog,
            "insert_shape": self._insert_shape_frame,
            "scan_import": self._run_scan_import,
            "devices_discover": self._show_devices_dialog,
            "devices_printers": lambda: self._show_devices_dialog(filter_kind="printer"),
            "devices_refresh": lambda: self._show_devices_dialog(auto_refresh=True),
            "dtp_layout": self._enter_layout_mode,
            "dtp_text_frame": self._dtp_add_text_frame,
            "dtp_link": self._dtp_link_frames,
            "dtp_grid": self._dtp_toggle_grid,
            "dtp_export_pdf": self._dtp_export_pdf_dialog,
            "dtp_import": self._dtp_import_text,
            "dtp_image": self._dtp_replace_image,
            "dtp_graphic": self._dtp_import_graphic,
            "dtp_fill": self._dtp_apply_fill,
            "dtp_stroke": self._dtp_apply_stroke,
            "dtp_font": self._dtp_apply_font,
            "dtp_wrap": self._dtp_apply_wrap,
            "dtp_weld": self._dtp_weld,
            "dtp_symbol": self._dtp_symbol,
            "dtp_preflight": self._dtp_preflight,
            "dtp_pdfx": self._dtp_export_pdfx,
            "dtp_text_path": self._dtp_text_on_path,
            "dtp_glyphs": self._dtp_glyph_palette,
            "dtp_clip": self._dtp_clip_mask,
            "dtp_live_fill": self._dtp_live_fill,
            "ki_assistant": self._show_ki_assistant,
            "varfonts": self._show_variable_fonts,
            "pades_sign": self._show_pades_dialog,
            "paragraph": self._paragraph_format_dialog,
            "list_glyph": self._change_list_glyph_dialog,
            "list_restart": self._restart_list_numbering,
            "list_indent": lambda: self._adjust_list_indent(+1),
            "list_outdent": lambda: self._adjust_list_indent(-1),
            "section_break": self._insert_section_break,
            "page_size_a4": lambda: self._apply_page_size_preset("A4"),
            "page_size_letter": lambda: self._apply_page_size_preset("Letter"),
            "page_size_legal": lambda: self._apply_page_size_preset("Legal"),
            "page_size_custom": self._show_page_layout_dialog,
            "page_portrait": lambda: self._apply_page_orientation("portrait"),
            "page_landscape": lambda: self._apply_page_orientation("landscape"),
            "page_columns_1": lambda: self._apply_page_columns(1),
            "page_columns_2": lambda: self._apply_page_columns(2),
            "page_columns_3": lambda: self._apply_page_columns(3),
            "cell_align_top": lambda: self._set_cell_vertical_align("top"),
            "cell_align_middle": lambda: self._set_cell_vertical_align("middle"),
            "cell_align_bottom": lambda: self._set_cell_vertical_align("bottom"),
            "header_footer": self._header_footer_dialog,
            "field_token": self._field_token_dialog,
            "chrome_klassisch": lambda: self._set_chrome_mode("klassisch"),
            "chrome_ribbon": lambda: self._set_chrome_mode("ribbon"),
            "chrome_kombiniert": lambda: self._set_chrome_mode("kombiniert"),
            "styles_pane": self._toggle_style_pane,
            "insert_nbsp": self._insert_nbsp,
            "insert_shy": self._insert_soft_hyphen,
            "print": self._print,
            "settings": self._settings,
            "mail_merge_data": lambda: self._run_mail_merge_dialog(focus="data"),
            "mail_merge_field": lambda: self._run_mail_merge_dialog(focus="field"),
            "mail_merge_preview": lambda: self._run_mail_merge_dialog(focus="preview"),
            "mail_merge_finish": lambda: self._run_mail_merge_dialog(focus="run"),
            "table_add_row": lambda: self._table_op("add_row"),
            "table_add_col": lambda: self._table_op("add_col"),
            "table_del_row": lambda: self._table_op("del_row"),
            "table_del_col": lambda: self._table_op("del_col"),
            "table_merge": lambda: self._table_op("merge"),
            "table_split": lambda: self._table_op("split"),
            "table_borders": lambda: self._table_op("borders"),
            "table_header_row": lambda: self._table_op("header"),
            "table_align_left": lambda: self._table_op("align_left"),
            "table_align_center": lambda: self._table_op("align_center"),
            "table_align_right": lambda: self._table_op("align_right"),
        }
        fn = handlers.get(aid)
        if callable(fn):
            fn()
        else:
            self._set_status(f"Ribbon-Aktion ohne Handler: {aid}")

    def _rich_base_font_for_doc(self):
        """Standardschrift des aktuellen Rich-Dokuments (DOCX Normal-Stil) — 2.6.53."""
        meta = (self.doc.meta if self.doc is not None else None) or {}
        return self._rich_base_font_for_meta(meta)

    def _show_page_layout_dialog(self) -> None:
        """Seitenlayout des Texteditors (DTP-Presets, Ränder, Ausrichtung) — 2.6.53."""
        from instantlensdoc.ui.page_layout_dialog import PageLayoutDialog

        if not self._guard_editor_action("Seitenlayout"):
            return
        current = self.editor.page_layout()
        dlg = PageLayoutDialog(current, self, rich_document=self.editor.rich_mode())
        if dlg.exec() != QDialog.Accepted:
            return
        layout = dlg.result_layout()
        try:
            layout.save()
        except Exception as e:
            _log.warning("Seitenlayout konnte nicht gespeichert werden: %s", e)
        self.editor.set_page_layout(layout)
        try:
            sec = getattr(self, "secondary_editor", None)
            if sec is not None and hasattr(sec, "set_page_layout"):
                sec.set_page_layout(layout)
        except Exception:
            pass
        if self.editor.page_layout_active():
            self._set_status(
                f"Seitenlayout: {layout.describe()} · Spalte {self.editor.page_column_width_px()} px"
            )
        elif not layout.enabled or layout.scope == "off":
            self._set_status("Seitenlayout aus — Text bricht am Fensterrand um")
        else:
            self._set_status(
                f"Seitenlayout gespeichert ({layout.describe()}) — gilt für Word-/DOCX-Dokumente"
            )

    def _apply_editor_page_layout_pick(
        self,
        *,
        preset: str | None = None,
        orientation: str | None = None,
        columns: int | None = None,
    ) -> None:
        """Menü-Picker: bestehendes EditorPageLayout anwenden — kein neuer Dialog."""
        if not self._guard_editor_action("Seitenlayout"):
            return
        from instantlensdoc.core.editor_page_layout import EditorPageLayout

        lay = self.editor.page_layout()
        if lay is None:
            lay = EditorPageLayout.from_settings()
        else:
            try:
                lay = EditorPageLayout.from_dict(lay.to_dict())
            except Exception:
                lay = EditorPageLayout.from_settings()
        if preset:
            lay.with_preset(preset)
        if orientation in ("portrait", "landscape"):
            lay.orientation = orientation
        if columns is not None:
            lay.columns = columns if columns in (1, 2, 3) else 1
        lay.enabled = True
        if lay.scope == "off":
            lay.scope = "rich"
        self._commit_page_layout(lay)

    def _commit_page_layout(self, layout) -> None:
        try:
            layout.save()
        except Exception as e:
            _log.warning("Seitenlayout konnte nicht gespeichert werden: %s", e)
        self.editor.set_page_layout(layout)
        try:
            sec = getattr(self, "secondary_editor", None)
            if sec is not None and hasattr(sec, "set_page_layout"):
                sec.set_page_layout(layout)
        except Exception:
            pass
        self._set_status(f"Seitenlayout: {layout.describe()}")

    def _apply_page_size_preset(self, name: str) -> None:
        if (name or "").lower() in ("custom", "benutzerdefiniert"):
            self._show_page_layout_dialog()
            return
        self._apply_editor_page_layout_pick(preset=str(name))

    def _apply_page_orientation(self, orientation: str) -> None:
        self._apply_editor_page_layout_pick(orientation=orientation)

    def _apply_page_columns(self, columns: int) -> None:
        self._apply_editor_page_layout_pick(columns=int(columns))

    def _toggle_doc_split_from_ribbon(self) -> None:
        """Ribbon-Toggle für Fenster teilen — 2.6.20."""
        act = getattr(self, "_doc_split_action", None)
        if act is not None:
            act.trigger()
        else:
            from instantlensdoc.core.app_settings import (
                get_editor_doc_split,
                set_editor_doc_split,
            )

            want = not get_editor_doc_split()
            set_editor_doc_split(want)
            if getattr(self, "secondary_wrap", None) is not None:
                self.secondary_wrap.setVisible(want)
            if getattr(self, "ribbon_bar", None) is not None:
                self.ribbon_bar.set_checked("doc_split", want)
            self._set_status("Fenster geteilt" if want else "Fenster ungeteilt")

    def _detach_current_document(self) -> None:
        path = None
        if self.doc and self.doc.path:
            path = str(self.doc.path)
        elif getattr(self.pdf_view, "pdf_path", None):
            path = str(self.pdf_view.pdf_path)
        if path:
            self._detach_document_window(path)
        else:
            self._feature_dialog(
                "Separates Fenster",
                "Kein Dokument zum Trennen.",
                object_name="ildDetachDocumentDialog",
            )

    def _detach_document_window(self, path: str) -> None:
        """Dokument in schließbarem Vorschaudialog öffnen."""
        if not path:
            self._feature_dialog(
                "Separates Fenster",
                "Kein Dokument zum Trennen.",
                object_name="ildDetachDocumentDialog",
            )
            return
        from pathlib import Path as _P

        from instantlensdoc.ui.feature_dialog import DetachedDocumentDialog

        p = _P(path)
        if not p.is_file():
            self._feature_dialog(
                "Separates Fenster",
                f"Datei fehlt:\n{path}",
                object_name="ildDetachDocumentDialog",
            )
            return
        body = ""
        if p.suffix.lower() == ".pdf":
            body = f"PDF-Vorschau\n{p}\n\nVolleditor bleibt im Hauptfenster."
            try:
                from ild_pdf.render import render_page

                render_page(p, 0, scale=0.4)
                body = f"PDF geladen: {p.name}\nPfad: {p}"
            except Exception as e:
                body = f"PDF: {p}\nVorschau nicht verfügbar: {e}"
        else:
            try:
                body = p.read_text(encoding="utf-8", errors="replace")[:12000]
            except Exception:
                body = "(nicht lesbar)"
        DetachedDocumentDialog(self, path=str(p), body=body).exec()
        self._set_status(f"Separates Fenster: {p.name}")

    def _on_doc_tab_activated(self, path: str) -> None:
        if path:
            self.open_path(path)

    def _schedule_doc_tab_bar_sync(self, *_args) -> None:
        """Tab-Leiste nach Modelländerung der Dokumentliste nachziehen (gebündelt) — 2.6.54."""
        if getattr(self, "_doc_tab_bar_sync_pending", False):
            return
        self._doc_tab_bar_sync_pending = True

        def _run() -> None:
            self._doc_tab_bar_sync_pending = False
            try:
                self._refresh_doc_tab_bar()
            except Exception as e:
                _log.debug("Tab-Leiste sync: %s", e)

        QTimer.singleShot(0, _run)

    def _refresh_doc_tab_bar(self) -> None:
        """Dokument-Tabs aus Sidebar synchronisieren — 2.6.19."""
        self._doc_tab_bar_sync_pending = False
        if getattr(self, "doc_tab_bar", None) is None:
            return
        from instantlensdoc.core.app_settings import get_doc_tabs_visible

        if not get_doc_tabs_visible():
            self.doc_tab_bar.setVisible(False)
            return
        paths = (
            list(self.sidebar.document_paths())
            if hasattr(self.sidebar, "document_paths")
            else []
        )
        active = None
        if self.doc and self.doc.path:
            active = str(self.doc.path)
        elif getattr(self.pdf_view, "pdf_path", None):
            active = str(self.pdf_view.pdf_path)
        self.doc_tab_bar.set_documents(paths, active=active)

    def _toggle_panel_thumbs(self, checked: bool):
        """Sidebar-Panel Vorschaubilder — Session (0.9.5)."""
        try:
            self.sidebar.set_panel_visibility(thumbs=bool(checked))
        except Exception:
            pass
        self._save_session()
        self._set_status(
            "Vorschaubilder ein" if checked else "Vorschaubilder aus"
        )

    def _toggle_panel_ann(self, checked: bool):
        """Sidebar-Panel Annotationen — Session (0.9.5)."""
        try:
            self.sidebar.set_panel_visibility(ann=bool(checked))
        except Exception:
            pass
        self._save_session()
        self._set_status(
            "Annotationsliste ein" if checked else "Annotationsliste aus"
        )

    def _toggle_panel_bookmark(self, checked: bool):
        """Sidebar-Panel Lesezeichen/Outline — Session (0.9.5)."""
        try:
            self.sidebar.set_panel_visibility(bookmark=bool(checked))
        except Exception:
            pass
        self._save_session()
        self._set_status(
            "Lesezeichen ein" if checked else "Lesezeichen aus"
        )

    def _sync_panel_visibility_menu(self) -> None:
        """Menü-Checks an Sidebar-Panel-Sichtbarkeit anpassen (0.9.5)."""
        try:
            vis = self.sidebar.panel_visibility()
        except Exception:
            vis = {"thumbs": True, "ann": True, "bookmark": True}
        for attr, key in (
            ("_panel_thumbs_action", "thumbs"),
            ("_panel_ann_action", "ann"),
            ("_panel_bookmark_action", "bookmark"),
        ):
            act = getattr(self, attr, None)
            if act is None:
                continue
            act.blockSignals(True)
            act.setChecked(bool(vis.get(key, True)))
            act.blockSignals(False)

    def _toggle_ann_layer(self, checked: bool):
        self.pdf_view.set_annotations_visible(bool(checked))
        self._sync_ann_layer_action(bool(checked))

    def _toggle_ann_type_layer(self, group: str, checked: bool):
        """Annotation-Typ global ein-/ausblenden — 1.8.0; Session+Zähler — 1.8.1."""
        self.pdf_view.set_annotation_type_visible(str(group), bool(checked))
        self._sync_ann_type_actions()
        try:
            self._save_session()
        except Exception:
            pass

    def _set_all_ann_type_layers(self, visible: bool) -> None:
        """Alle Layer-Typen ein-/aus; Undo/Redo; A11y-Announcement — 1.8.3–1.8.5."""
        from instantlensdoc.core.app_settings import (
            ANN_LAYER_TYPE_KEYS,
            get_ann_layer_types_visible,
            set_ann_layer_types_visible,
        )

        prev = dict(get_ann_layer_types_visible())
        payload = {k: bool(visible) for k in ANN_LAYER_TYPE_KEYS}
        status_msg = "Layer: alle ein" if visible else "Layer: alle aus"
        if prev == payload:
            self._set_status(status_msg)
            self._announce_status_toast(status_msg)
            return
        stack = getattr(self, "_ann_layer_undo", None)
        if stack is None:
            self._ann_layer_undo = []
            stack = self._ann_layer_undo
        stack.append(prev)
        if len(stack) > 20:
            stack.pop(0)
        # Neuer Vorwärts-Schritt leert Redo — 1.8.4
        self._ann_layer_redo = []
        set_ann_layer_types_visible(payload)
        self.pdf_view.set_annotation_types_visible(payload)
        self._sync_ann_type_actions()
        try:
            self._save_session()
        except Exception:
            pass
        self._set_status(status_msg)
        self._announce_status_toast(status_msg)
        self._refresh_undo_hint()

    def _undo_ann_type_layers(self) -> bool:
        """Einen Layer-Alle-ein/aus-Eintrag rückgängig — 1.8.3; Redo-fähig — 1.8.4."""
        stack = getattr(self, "_ann_layer_undo", None) or []
        if not stack:
            return False
        from instantlensdoc.core.app_settings import (
            get_ann_layer_types_visible,
            set_ann_layer_types_visible,
        )

        current = dict(get_ann_layer_types_visible())
        prev = stack.pop()
        redo = getattr(self, "_ann_layer_redo", None)
        if redo is None:
            self._ann_layer_redo = []
            redo = self._ann_layer_redo
        redo.append(current)
        if len(redo) > 20:
            redo.pop(0)
        set_ann_layer_types_visible(prev)
        self.pdf_view.set_annotation_types_visible(prev)
        self._sync_ann_type_actions()
        try:
            self._save_session()
        except Exception:
            pass
        self._set_status("Layer: Sichtbarkeit rückgängig")
        self._refresh_undo_hint()
        return True

    def _redo_ann_type_layers(self) -> bool:
        """Layer-Alle-ein/aus wiederholen (Ctrl+Y) — 1.8.4."""
        redo = getattr(self, "_ann_layer_redo", None) or []
        if not redo:
            return False
        from instantlensdoc.core.app_settings import (
            get_ann_layer_types_visible,
            set_ann_layer_types_visible,
        )

        current = dict(get_ann_layer_types_visible())
        nxt = redo.pop()
        undo = getattr(self, "_ann_layer_undo", None)
        if undo is None:
            self._ann_layer_undo = []
            undo = self._ann_layer_undo
        undo.append(current)
        if len(undo) > 20:
            undo.pop(0)
        set_ann_layer_types_visible(nxt)
        self.pdf_view.set_annotation_types_visible(nxt)
        self._sync_ann_type_actions()
        try:
            self._save_session()
        except Exception:
            pass
        # Status analog zu Set: alle ein/aus wenn einheitlich
        vals = set(bool(v) for v in nxt.values()) if nxt else set()
        if vals == {True}:
            self._set_status("Layer: alle ein")
        elif vals == {False}:
            self._set_status("Layer: alle aus")
        else:
            self._set_status("Layer: Sichtbarkeit wiederholen")
        self._refresh_undo_hint()
        return True

    def _filter_ann_list_by_layer_group(self, group: str) -> None:
        """Ann.-Liste auf Layer-Typ filtern (Zähler-Klick) — 1.8.2."""
        try:
            self.sidebar.set_annotation_layer_group_filter(group)
        except Exception:
            return
        labels = getattr(self, "_ann_type_labels", None) or {}
        if group:
            name = labels.get(group, group)
            self._set_status(f"Ann.-Liste gefiltert: {name}")
        else:
            self._set_status("Ann.-Listenfilter zurückgesetzt")

    def _sync_ann_type_actions(self) -> None:
        vis = get_ann_layer_types_visible()
        labels = getattr(self, "_ann_type_labels", None) or {
            "highlight": "Markierungen",
            "note": "Notizen",
            "shape": "Formen",
            "redaction": "Schwärzungen",
        }
        vis_n, total_n = (0, 0)
        try:
            vis_n, total_n = self.pdf_view.count_visible_annotations()
        except Exception:
            vis_n, total_n = 0, 0
        by_group: dict[str, int] = {}
        try:
            by_group = self.pdf_view.count_annotations_by_layer_group()
        except Exception:
            by_group = {}
        for key, act in (getattr(self, "_ann_type_actions", None) or {}).items():
            act.blockSignals(True)
            act.setChecked(bool(vis.get(key, True)))
            base = labels.get(key, key)
            cnt = int(by_group.get(key, 0))
            act.setText(f"{base} ({cnt})")
            act.blockSignals(False)
        menu = getattr(self, "_m_ann_types", None)
        if menu is not None:
            menu.setTitle(f"Annotation-Typen ({vis_n}/{total_n})")

    def _pages_for_batch_transform(self) -> list[int]:
        """Thumbnail-Auswahl oder aktuelle Seite — 1.8.1."""
        pages: list[int] = []
        try:
            pages = list(self.sidebar.selected_thumb_pages() or [])
        except Exception:
            pages = []
        if not pages and self.pdf_view.pdf_path:
            pages = [int(self.pdf_view.page_index)]
        return pages

    def _batch_rotate_selection(self, degrees: int) -> None:
        """Batch-Drehen per Shortcut — 1.8.1."""
        if not self._require_pdf("Drehen"):
            return
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        pages = self._pages_for_batch_transform()
        if not pages:
            self._feature_dialog(
                "Drehen",
                "Keine Seite gewählt. Thumbnail-Auswahl oder aktuelles PDF nötig.",
            )
            return
        self._on_thumbs_batch_rotate(pages, int(degrees))

    def _batch_flip_selection(self, *, horizontal: bool, vertical: bool) -> None:
        """Batch-Spiegeln per Shortcut — 1.8.1."""
        if not self._require_pdf("Spiegeln"):
            return
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        pages = self._pages_for_batch_transform()
        if not pages:
            self._feature_dialog(
                "Spiegeln",
                "Keine Seite gewählt. Thumbnail-Auswahl oder aktuelles PDF nötig.",
            )
            return
        self._on_thumbs_batch_flip(pages, bool(horizontal), bool(vertical))

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

    def _sync_book_layout_action(self, enabled: bool | None = None):
        if enabled is None:
            enabled = self.pdf_view.book_layout_enabled()
        if hasattr(self, "_book_layout_action") and self._book_layout_action is not None:
            self._book_layout_action.blockSignals(True)
            self._book_layout_action.setChecked(bool(enabled))
            self._book_layout_action.blockSignals(False)
        if getattr(self, "ribbon_bar", None) is not None:
            self.ribbon_bar.set_checked("book_layout", bool(enabled))

    def _sync_page_by_page_action(self, enabled: bool | None = None):
        if enabled is None:
            enabled = self.pdf_view.page_by_page_enabled()
        if hasattr(self, "_page_by_page_action") and self._page_by_page_action is not None:
            self._page_by_page_action.blockSignals(True)
            self._page_by_page_action.setChecked(bool(enabled))
            self._page_by_page_action.blockSignals(False)
        if getattr(self, "ribbon_bar", None) is not None:
            self.ribbon_bar.set_checked("page_by_page", bool(enabled))

    def _sync_continuous_action(self, enabled: bool | None = None):
        if enabled is None:
            enabled = self.pdf_view.continuous_scroll_enabled()
        if hasattr(self, "_continuous_action") and self._continuous_action is not None:
            self._continuous_action.blockSignals(True)
            self._continuous_action.setChecked(bool(enabled))
            self._continuous_action.blockSignals(False)
        if getattr(self, "ribbon_bar", None) is not None:
            self.ribbon_bar.set_checked("continuous_scroll", bool(enabled))

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
        if not self._guard_editor_action("Textbausteine"):
            return
        from instantlensdoc.core.app_settings import get_editor_snippets
        from instantlensdoc.core.app_settings import EDITOR_SNIPPET_COUNT, set_editor_snippet
        from instantlensdoc.ui.feature_dialog import SnippetEditDialog

        snippets = get_editor_snippets()
        i = max(0, min(EDITOR_SNIPPET_COUNT - 1, int(index)))
        text = snippets[i] if i < len(snippets) else ""
        if not text:
            dlg = SnippetEditDialog(self, index=i, text="")
            if dlg.exec() != QDialog.Accepted:
                return
            text = dlg.text()
            if not text:
                return
            set_editor_snippet(i, text)
        self.editor.insertPlainText(text)
        self._set_status(f"Textbaustein {i + 1} eingefügt")

    def _save_snippet(self, index: int):
        if not self._guard_editor_action("Textbausteine"):
            return
        from instantlensdoc.core.app_settings import (
            EDITOR_SNIPPET_COUNT,
            set_editor_snippet,
        )

        cur = self.editor.textCursor()
        text = cur.selectedText().replace("\u2029", "\n")
        if not text.strip():
            # aktuelle Zeile
            from PySide6.QtGui import QTextCursor

            cur.select(QTextCursor.LineUnderCursor)
            text = cur.selectedText().replace("\u2029", "\n")
        i = max(0, min(EDITOR_SNIPPET_COUNT - 1, int(index)))
        set_editor_snippet(i, text)
        preview = (text[:40] + "…") if len(text) > 40 else text.replace("\n", "⏎")
        self._set_status(f"Textbaustein {i + 1} gespeichert: {preview}")

    def _toggle_case_selection(self):
        if not self._guard_editor_action("Groß-/Kleinschreibung"):
            return
        if self.editor.toggle_case_selection():
            scope = "Auswahl" if self.editor.textCursor().hasSelection() else "Dokument"
            self._set_status(f"Schreibweise umgeschaltet ({scope})")
        else:
            self._set_status("Keine Änderung")

    def _transform_document_case(self, mode: str):
        if not self._guard_editor_action("Alles groß/klein"):
            return
        if self.editor.transform_document_case(mode):
            label = "GROSS" if mode == "upper" else "klein"
            self._set_status(f"Datei → {label}")
        else:
            self._set_status("Keine Änderung (leer oder schon umgewandelt)")

    def _indent_selection(self):
        if not self._guard_editor_action("Einrückung"):
            return
        if self.editor.adjust_block_indent(+24.0):
            self._sync_editor_rich_meta()
            self._set_status("Einrückung erhöht")
        else:
            self._set_status("Einrückung nicht möglich")

    def _outdent_selection(self):
        if not self._guard_editor_action("Einrückung"):
            return
        if self.editor.adjust_block_indent(-24.0):
            self._sync_editor_rich_meta()
            self._set_status("Einrückung verringert")
        else:
            self._set_status("Einrückung nicht möglich")

    def _open_log_folder(self):
        from instantlensdoc.core.logging_setup import log_dir
        from instantlensdoc.ui.feature_dialog import PathOpenDialog

        PathOpenDialog(self, title="Logordner", path=log_dir()).exec()
        self._set_status(f"Logordner: {log_dir()}")

    def _continue_last_session(self) -> None:
        """Willkommen „Weiterarbeiten“: letzte Session-Tabs öffnen (Restore-Toggle aus) — 1.0.7."""
        try:
            self._restore_session(force=True)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Weiterarbeiten",
                f"Letzte Session konnte nicht geladen werden:\n{e}",
            )
            return
        # Wenn weiterhin leer: Hinweis
        paths = []
        try:
            paths = list(self.sidebar.document_paths())
        except Exception:
            paths = []
        if not paths and not (self.doc and self.doc.path):
            self._set_status("Keine wiederherstellbaren Session-Tabs")
        else:
            self._set_status("Weitergearbeitet — letzte Session-Tabs geöffnet")

    def _show_welcome_if_empty(self) -> bool:
        """Willkommensseite anzeigen wenn keine Tabs / kein Dokument — 1.0.0."""
        paths = []
        try:
            paths = list(self.sidebar.document_paths())
        except Exception:
            paths = []
        if paths or (self.doc and self.doc.path):
            return False
        if self.doc is not None and not self.doc.path:
            if (self.doc.text or "").strip() or getattr(self.doc, "dirty", False):
                return False
        try:
            self.welcome_page.refresh_recent()
        except Exception:
            pass
        try:
            if hasattr(self.welcome_page, "refresh_continue_button"):
                self.welcome_page.refresh_continue_button()
        except Exception:
            pass
        self.stack.setCurrentWidget(self.welcome_page)
        try:
            # Letzter Tab: Leiste aus Sidebar neu aufbauen — kein Rest-Tab bei Welcome — 2.6.54
            self._refresh_doc_tab_bar()
        except Exception:
            pass
        self.setWindowTitle(self._app_title())
        self._update_doc_status()
        return True

    def _manual_backup_now(self) -> None:
        """Aktuelles Dokument manuell sichern; bei Schreibfehler max. 3 Versuche — 1.0.3."""
        max_attempts = 3
        last_err: OSError | None = None
        source_hint = ""
        if self.doc and self.doc.path:
            source_hint = str(self.doc.path)
        elif self.pdf_view.pdf_path:
            source_hint = str(self.pdf_view.pdf_path)
        for attempt in range(1, max_attempts + 1):
            try:
                self._manual_backup_once()
                return
            except OSError as e:
                last_err = e
                if attempt >= max_attempts:
                    try:
                        append_backup_log(
                            source=source_hint,
                            ok=False,
                            message=f"Abbruch nach {max_attempts} Versuchen: {e}",
                        )
                    except Exception:
                        pass
                    QMessageBox.critical(
                        self,
                        "Backup",
                        f"Backup nach {max_attempts} Versuchen abgebrochen.\n\n"
                        f"Letzter Fehler:\n{e}",
                    )
                    self._set_status(
                        f"Backup abgebrochen nach {max_attempts} Versuchen"
                    )
                    return
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Critical)
                box.setWindowTitle("Backup")
                box.setText("Backup-Schreibfehler")
                box.setInformativeText(
                    f"Die Backup-Datei konnte nicht geschrieben werden:\n{e}\n\n"
                    f"Versuch {attempt}/{max_attempts}. Erneut versuchen?"
                )
                box.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
                box.setDefaultButton(QMessageBox.Retry)
                if box.exec() != QMessageBox.Retry:
                    try:
                        append_backup_log(
                            source=source_hint,
                            ok=False,
                            message=f"Abgebrochen: {e}",
                        )
                    except Exception:
                        pass
                    self._set_status("Backup abgebrochen")
                    return
            except Exception as e:
                try:
                    append_backup_log(
                        source=source_hint, ok=False, message=str(e)
                    )
                except Exception:
                    pass
                QMessageBox.critical(self, "Backup", f"Backup fehlgeschlagen:\n{e}")
                return
        if last_err is not None:
            self._set_status(f"Backup abgebrochen nach {max_attempts} Versuchen")

    def _manual_backup_once(self) -> None:
        """Ein Backup-Versuch; OSError bei Schreibfehlern durchreichen — 1.0.2/1.0.4."""
        if self.doc and self.doc.path and Path(self.doc.path).is_file():
            dest = manual_backup_file(self.doc.path)
            if dest is None:
                append_backup_log(
                    source=self.doc.path, ok=False, message="Quelle fehlt"
                )
                QMessageBox.warning(self, "Backup", "Backup fehlgeschlagen.")
                return
            self._last_backup_path = dest
            append_backup_log(dest=dest, source=self.doc.path, ok=True)
            self._set_status(f"Backup erstellt: {dest}")
            self._show_backup_result(dest)
            return
        if (
            self.stack.currentWidget() is self.pdf_view
            and self.pdf_view.pdf_path
            and Path(self.pdf_view.pdf_path).is_file()
        ):
            dest = manual_backup_file(self.pdf_view.pdf_path)
            if dest is None:
                append_backup_log(
                    source=str(self.pdf_view.pdf_path),
                    ok=False,
                    message="Quelle fehlt",
                )
                QMessageBox.warning(self, "Backup", "Backup fehlgeschlagen.")
                return
            self._last_backup_path = dest
            append_backup_log(
                dest=dest, source=str(self.pdf_view.pdf_path), ok=True
            )
            self._set_status(f"Backup erstellt: {dest}")
            self._show_backup_result(dest)
            return
        if self.stack.currentWidget() is self.editor_pane or (
            self.doc is not None and not self.doc.path
        ):
            text = self.editor.toPlainText() if hasattr(self, "editor") else ""
            body = text or (self.doc.text if self.doc else "") or ""
            title = (self.doc.title if self.doc else None) or "unbenannt"
            suffix = (
                ".md"
                if self.doc and self.doc.kind == DocKind.MARKDOWN
                else ".txt"
            )
            dest = manual_backup_text(body, title=title, suffix=suffix)
            self._last_backup_path = dest
            append_backup_log(dest=dest, source=title, ok=True, message="Text")
            self._set_status(f"Backup erstellt: {dest}")
            self._show_backup_result(dest)
            return
        self._show_backup_result(backup_dir())

    def _show_backup_result(self, dest) -> None:
        from instantlensdoc.ui.feature_dialog import PathOpenDialog

        PathOpenDialog(self, title="Backup jetzt", path=dest).exec()

    def _open_backup_folder(self) -> None:
        """Backup-Ordner anzeigen und optional im Dateimanager öffnen."""
        from instantlensdoc.ui.feature_dialog import PathOpenDialog

        path = backup_dir()
        PathOpenDialog(self, title="Backup-Ordner", path=path).exec()
        self._set_status(f"Backup-Ordner: {path}")

    def _create_crash_report(self):
        from instantlensdoc.ui.help_dialog import create_crash_report_zip_dialog

        path = create_crash_report_zip_dialog(self)
        if path is not None:
            self._set_status(f"Crash-Report: {path}")

    def _open_workdir(self):
        """Ordner der aktuellen Datei bzw. Prozess-CWD — schließbarer Pfaddialog."""
        from instantlensdoc.ui.feature_dialog import PathOpenDialog

        folder: Path | None = None
        if self.doc and self.doc.path:
            p = Path(self.doc.path)
            folder = p.parent if p.exists() else None
        if folder is None and self.pdf_view.pdf_path:
            p = Path(self.pdf_view.pdf_path)
            folder = p.parent if p.exists() else None
        if folder is None or not folder.is_dir():
            folder = Path.cwd()
        PathOpenDialog(self, title="Arbeitsverzeichnis", path=folder).exec()
        self._set_status(f"Arbeitsverzeichnis: {folder}")

    def _app_title(self, suffix: str | None = None) -> str:
        base = f"{DISPLAY_NAME} {__version__}"
        if suffix:
            return f"{base} — {suffix}"
        return base

    def _sync_theme_menu(self):
        pref = load_theme_mode()
        resolved = resolve_theme(pref)
        if getattr(self, "_theme_system_action", None) is not None:
            self._theme_system_action.setChecked(pref == "system")
        if self._theme_action is not None:
            dark = resolved == "dark"
            self._theme_action.setChecked(dark)
            if pref == "system":
                self._theme_action.setText(
                    "Helles Design (Override)" if dark else "Dunkles Design (Override)"
                )
            else:
                self._theme_action.setText(
                    "Helles Design" if dark else "Dunkles Design"
                )
        self._refresh_theme_status_label(pref)

    def _refresh_theme_status_label(self, pref: str | None = None) -> None:
        """Statusleisten-Indicator Theme; Klick → Schnellmenü — 1.4.3."""
        lbl = getattr(self, "theme_status_label", None)
        if lbl is None:
            return
        mode = pref if pref in ("system", "dark", "light") else load_theme_mode()
        text = theme_status_text(mode)  # type: ignore[arg-type]
        resolved = resolve_theme(mode)  # type: ignore[arg-type]
        if mode == "system":
            tip = (
                f"Theme: System folgen "
                f"(aktuell {'dunkel' if resolved == 'dark' else 'hell'}). "
                f"Klick: Schnellmenü System/Hell/Dunkel — 1.4.3"
            )
        else:
            tip = f"{text} (Override). Klick: Schnellmenü — 1.4.3"
        lbl.setText(text)
        lbl.setToolTip(tip)

    def _on_theme_status_clicked(self, event) -> None:
        """Klick auf Theme-Indicator → Schnellmenü System/Hell/Dunkel — 1.4.3."""
        from PySide6.QtGui import QMouseEvent

        if isinstance(event, QMouseEvent) and event.button() != Qt.LeftButton:
            QLabel.mousePressEvent(self.theme_status_label, event)
            return
        self._show_theme_quick_menu()
        event.accept()

    def _show_theme_quick_menu(self) -> None:
        """Theme-Schnellmenü an Statusleisten-Indicator — 1.4.3."""
        menu = QMenu(self)
        menu.setTitle("Theme")
        pref = load_theme_mode()
        act_sys = menu.addAction("System")
        act_sys.setCheckable(True)
        act_sys.setChecked(pref == "system")
        act_light = menu.addAction("Hell")
        act_light.setCheckable(True)
        act_light.setChecked(pref == "light")
        act_dark = menu.addAction("Dunkel")
        act_dark.setCheckable(True)
        act_dark.setChecked(pref == "dark")
        chosen = menu.exec(self.theme_status_label.mapToGlobal(
            self.theme_status_label.rect().bottomLeft()
        ))
        if chosen is None:
            return
        if chosen is act_sys:
            self._set_theme_mode("system")
        elif chosen is act_light:
            self._set_theme_mode("light")
        elif chosen is act_dark:
            self._set_theme_mode("dark")

    def _set_theme_mode(self, mode: str) -> None:
        """Theme setzen (system|light|dark) inkl. Menü/Status — 1.4.3."""
        if mode not in ("system", "light", "dark"):
            return
        apply_theme(mode=mode)  # type: ignore[arg-type]
        self._sync_theme_menu()
        self._set_status(theme_status_text(mode))  # type: ignore[arg-type]
        try:
            self._save_session()
        except Exception:
            pass

    def _cycle_theme_mode(self) -> None:
        """Ctrl+Shift+T: System → Hell → Dunkel → System; kurzer Status-Toast — 1.4.5."""
        mode = cycle_theme_mode(self)
        self._sync_theme_menu()
        # Kurz „Theme: …“ in der Statusleiste — 1.4.5
        self.statusBar().showMessage(theme_status_text(mode), 2500)
        try:
            self._save_session()
        except Exception:
            pass

    def _announce_hc_toast(self, msg: str) -> None:
        """
        Accessibility-Announcement für HC-Toast — gleiche Pipeline wie OCR-Defaults-Toast
        (AccessibleName/Description + AnnouncementEvent, Fallback NameChanged) — 2.0.5.
        """
        sb = self.statusBar()
        try:
            sb.setAccessibleName(msg)
            sb.setAccessibleDescription(msg)
        except Exception:
            pass
        try:
            from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent

            ev = QAccessibleAnnouncementEvent(sb, msg)
            QAccessible.updateAccessibility(ev)
        except Exception:
            try:
                from PySide6.QtGui import QAccessible, QAccessibleEvent

                ev = QAccessibleEvent(sb, QAccessible.Event.NameChanged)
                QAccessible.updateAccessibility(ev)
            except Exception:
                pass

    def _show_hc_toast(self, msg: str) -> None:
        """
        HC-Toast: Dauer aus OCR-Defaults-Toast-Settings, Announcement wie OCR,
        AccessibleName nach Timeout leeren — 2.0.5.
        """
        try:
            from instantlensdoc.core.app_settings import get_ocr_defaults_toast_sec

            ms = max(1, int(get_ocr_defaults_toast_sec())) * 1000
        except Exception:
            ms = 2000
        self._hc_toast_token = int(getattr(self, "_hc_toast_token", 0)) + 1
        token = self._hc_toast_token
        self._announce_hc_toast(msg)
        self.statusBar().showMessage(msg, ms)

        def _clear() -> None:
            if token != getattr(self, "_hc_toast_token", 0):
                return
            sb = self.statusBar()
            try:
                if (sb.currentMessage() or "") == msg:
                    # AccessibleName leeren wie OCR-Defaults-Toast — 2.0.5
                    sb.setAccessibleName("")
                    sb.setAccessibleDescription("")
            except Exception:
                pass

        from PySide6.QtCore import QTimer

        QTimer.singleShot(ms, _clear)

    def _toggle_high_contrast(self, checked: bool = False) -> None:
        """High-Contrast Theme Toggle — Ctrl+Alt+H — OCR-Toast-Pipeline — 2.0.5."""
        enabled = toggle_high_contrast(self)
        act = getattr(self, "_high_contrast_action", None)
        if act is not None:
            act.blockSignals(True)
            act.setChecked(bool(enabled))
            act.blockSignals(False)
        msg = "High-Contrast an" if enabled else "High-Contrast aus"
        self._show_hc_toast(msg)

    def _open_multi_doc_search(self) -> None:
        """Zentrale Multi-Dokument-Suche über alle offenen PDFs — 2.0.0."""
        from instantlensdoc.ui.multi_doc_search_dialog import MultiDocSearchDialog

        paths = []
        try:
            paths = list(self.sidebar.document_paths())
        except Exception:
            paths = []
        if self.doc and self.doc.path and str(self.doc.path) not in paths:
            paths.append(str(self.doc.path))
        # Offene Tabs (PDF) ergänzen
        try:
            for i in range(self.tabs.count()):
                w = self.tabs.widget(i)
                p = getattr(w, "pdf_path", None) or getattr(w, "path", None)
                if p and str(p) not in paths:
                    paths.append(str(p))
        except Exception:
            pass
        q = ""
        try:
            q = self.sidebar.search_text()
        except Exception:
            q = ""
        dlg = getattr(self, "_multi_doc_search_dlg", None)
        if dlg is None:
            dlg = MultiDocSearchDialog(self, paths=paths, initial_query=q)
            dlg.hit_activated.connect(self._on_multi_doc_hit)
            self._multi_doc_search_dlg = dlg
        else:
            dlg.set_paths(paths)
            if q:
                dlg.query_edit.setText(q)
        if q:
            try:
                dlg.run_search()
            except Exception:
                pass
        dlg.exec()

    def _on_multi_doc_hit(self, path: str, page, query: str = "") -> None:
        """Treffer aus zentraler Multi-Doc-Suche öffnen/hervorheben — 2.0.0."""
        self._on_fulltext_hit(str(path), page, query=query or "")

    def _refresh_portfolio_sidebar(self, path: str | None) -> None:
        """Portfolio-Inhaltsliste in Sidebar aktualisieren — 2.0.1."""
        clear = getattr(self.sidebar, "clear_portfolio_entries", None)
        set_entries = getattr(self.sidebar, "set_portfolio_entries", None)
        if not callable(set_entries):
            return
        if not path or not Path(path).is_file():
            if callable(clear):
                clear()
            return
        try:
            from ild_pdf.portfolio import has_collection, open_portfolio

            info = open_portfolio(path)
            entries = info.entries or []
            is_coll = bool(info.is_portfolio or has_collection(path))
            if not is_coll and not entries:
                if callable(clear):
                    clear()
                return
            set_entries(
                entries,
                title=info.title or Path(path).name,
                is_empty_collection=bool(is_coll and not entries),
            )
        except Exception:
            if callable(clear):
                clear()

    def _pdf_portfolio(self) -> None:
        """PDF-Portfolio erstellen/öffnen — 2.0.0/2.0.1."""
        from instantlensdoc.ui.portfolio_dialog import PortfolioDialog

        start = ""
        try:
            from instantlensdoc.core.app_settings import get_default_open_dir

            dod = get_default_open_dir()
            start = str(dod) if dod else ""
        except Exception:
            start = ""
        if not start and self.pdf_view.pdf_path:
            start = str(Path(self.pdf_view.pdf_path).parent)
        dlg = PortfolioDialog(self, start_dir=start)
        dlg.exec()
        created = getattr(dlg, "created_path", None) or getattr(dlg, "opened_path", None)
        if created and Path(created).is_file():
            try:
                self.open_path(created)
                self._set_status(f"Portfolio geöffnet: {Path(created).name}")
            except Exception:
                self._set_status(f"Portfolio erstellt: {Path(created).name}")
                self._refresh_portfolio_sidebar(created)

    def _toggle_follow_system(self, checked: bool = False):
        """System-Theme folgen Toggle — 1.4.0/1.4.2 Status-Indicator."""
        follow = bool(checked) if isinstance(checked, bool) else (
            self._theme_system_action.isChecked()
            if getattr(self, "_theme_system_action", None)
            else True
        )
        resolved = set_follow_system(follow)
        self._sync_theme_menu()
        self._set_status(
            theme_status_text("system" if follow else (
                "dark" if resolved == "dark" else "light"
            ))
        )
        try:
            self._save_session()
        except Exception:
            pass

    def _on_system_theme_live(self, resolved: str = "") -> None:
        """Callback: OS-Theme gewechselt bei aktivem „folgen“ — 1.4.1/1.4.2."""
        self._sync_theme_menu()
        mode = resolved or resolve_theme()
        self._set_status(
            f"Theme: System → {'Dunkel' if mode == 'dark' else 'Hell'} (live) — 1.4.2"
        )

    def _toggle_theme(self):
        mode = toggle_theme(self)
        self._sync_theme_menu()
        self._set_status(theme_status_text("dark" if mode == "dark" else "light"))
        # Theme in Session merken (0.9.4)
        try:
            self._save_session()
        except Exception:
            pass

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

    def _autosave_status_saved(self) -> str:
        """Statuszeile nach Autosave: „Gespeichert HH:MM:SS“ — 0.9.7."""
        from datetime import datetime

        return f"Gespeichert {datetime.now().strftime('%H:%M:%S')}"

    def _autosave_modal_open(self) -> bool:
        """True wenn ein modaler Dialog offen ist — Autosave pausiert (0.9.8)."""
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                return False
            return app.activeModalWidget() is not None
        except Exception:
            return False

    def _blink_autosave_error_status(self) -> None:
        """Status kurz blinken bei Autosave-Fehler — 0.9.8."""
        from PySide6.QtCore import QTimer

        try:
            self.statusBar().showMessage("Autosave fehlgeschlagen", 2000)
        except Exception:
            pass
        if not hasattr(self, "unsaved_status_label"):
            return
        if getattr(self, "_autosave_err_blink_active", False):
            return
        self._autosave_err_blink_active = True
        label = self.unsaved_status_label
        styles = (
            "padding-right: 10px; color: #fff; background-color: #C0392B; font-weight: 600;",
            "padding-right: 10px; color: #C0392B; font-weight: 600;",
        )
        self._autosave_err_blink_step = 0

        def _tick() -> None:
            i = int(getattr(self, "_autosave_err_blink_step", 0))
            if i >= len(styles):
                self._autosave_err_blink_active = False
                try:
                    self._update_unsaved_status()
                except Exception:
                    pass
                return
            label.setStyleSheet(styles[i])
            self._autosave_err_blink_step = i + 1
            QTimer.singleShot(100, _tick)

        _tick()

    def _autosave_maybe_backup(self, path) -> None:
        """Optionale .ildbak-Kopie vor Autosave-Überschreiben — 0.9.9."""
        try:
            from instantlensdoc.core.app_settings import (
                get_autosave_backup_enabled,
                get_autosave_backup_max,
            )

            if not get_autosave_backup_enabled():
                return
            p = Path(path) if path else None
            if p is None or not p.is_file():
                return
            backup_ildbak(p, max_backups=get_autosave_backup_max())
        except Exception:
            pass

    def _autosave_write_recovery_snapshot(self) -> None:
        """Dirty-Orphan-Snapshot für Crash-Recovery — 1.8.0."""
        if not get_crash_recovery_enabled():
            return
        if not self.doc or not self.doc.path:
            return
        try:
            from instantlensdoc.core.crash_recovery import write_recovery_snapshot

            if self.doc.kind == DocKind.PDF:
                side = None
                if self.pdf_view.store is not None:
                    side = getattr(self.pdf_view.store, "sidecar_path", None)
                if side is not None and Path(side).is_file():
                    write_recovery_snapshot(
                        self.doc.path,
                        kind="sidecar",
                        copy_from=side,
                        dirty=True,
                    )
                elif Path(self.doc.path).is_file():
                    write_recovery_snapshot(
                        self.doc.path,
                        kind="pdf",
                        copy_from=self.doc.path,
                        dirty=True,
                    )
                return
            if self.doc.kind in (
                DocKind.TEXT,
                DocKind.MARKDOWN,
                DocKind.HTML,
                DocKind.DOCX,
            ):
                write_recovery_snapshot(
                    self.doc.path,
                    kind="text",
                    text=self.editor.toPlainText(),
                    dirty=True,
                )
        except Exception:
            pass

    def _clear_recovery_for_current(self) -> None:
        if not self.doc or not self.doc.path:
            return
        try:
            from instantlensdoc.core.crash_recovery import clear_recovery_for

            clear_recovery_for(self.doc.path)
        except Exception:
            pass

    def _maybe_recover_orphans(self) -> None:
        """
        Beim Start: dirty Autosave-Orphans anbieten — 1.8.0; Alter·Als Kopie — 1.8.2.
        Mehrere Orphans als Liste, älteste zuerst — 1.8.4.
        Mehrfachauswahl Verwerfen · „Alle verwerfen“ mit Bestätigung — 1.8.5.
        """
        import os

        if os.environ.get("ILD_SMOKE_QT") or os.environ.get("ILD_NO_SESSION"):
            return
        if not get_crash_recovery_enabled():
            return
        try:
            from instantlensdoc.core.crash_recovery import (
                discard_orphan,
                format_orphan_age,
                list_orphans,
                orphan_meta_preview,
                restore_orphan,
                restore_orphan_as_copy,
            )

            orphans = list_orphans(
                max_age_hours=get_crash_recovery_max_age_hours()
            )
        except Exception:
            return
        if not orphans:
            return

        multi = len(orphans) > 1
        head = (
            f"{len(orphans)} ungespeicherte Autosave-Snapshots (Crash-Recovery), "
            "älteste zuerst — Mehrfachauswahl möglich:"
            if multi
            else "Ungespeicherter Autosave-Snapshot gefunden (Crash-Recovery):"
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Crash-Recovery")
        dlg.setMinimumWidth(520)
        dlg.setMinimumHeight(360)
        root = QVBoxLayout(dlg)
        lbl = QLabel(head)
        lbl.setWordWrap(True)
        root.addWidget(lbl)

        lst = QListWidget()
        lst.setSelectionMode(QAbstractItemView.ExtendedSelection)
        lst.setObjectName("recoveryOrphanList")
        for idx, o in enumerate(orphans):
            try:
                body = orphan_meta_preview(o)
            except Exception:
                try:
                    age_s = format_orphan_age(o.age_seconds())
                except Exception:
                    age_s = "Alter unbekannt"
                body = f"{o.label} ({o.kind}, {age_s})"
            text = f"{idx + 1}. {body}" if multi else body
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, int(idx))
            lst.addItem(item)
        lst.selectAll()
        root.addWidget(lst, 1)

        row = QHBoxLayout()
        btn_restore = QPushButton("Wiederherstellen")
        btn_restore.setToolTip("Ausgewählte Snapshots wiederherstellen")
        btn_copy = QPushButton("Als Kopie öffnen")
        btn_copy.setToolTip("Ausgewählte Snapshots als Kopie öffnen")
        btn_discard = QPushButton("Auswahl verwerfen")
        btn_discard.setToolTip("Nur ausgewählte Snapshots verwerfen — 1.8.5")
        btn_discard_all = QPushButton("Alle verwerfen")
        btn_discard_all.setToolTip(
            "Alle Snapshots verwerfen (mit Bestätigung) — 1.8.5"
        )
        btn_later = QPushButton("Später")
        for b in (
            btn_restore,
            btn_copy,
            btn_discard,
            btn_discard_all,
            btn_later,
        ):
            row.addWidget(b)
        root.addLayout(row)

        action: list[str] = ["later"]

        def _selected_orphans() -> list:
            idxs = []
            for it in lst.selectedItems():
                try:
                    idxs.append(int(it.data(Qt.UserRole)))
                except Exception:
                    pass
            idxs = sorted(set(idxs))
            return [orphans[i] for i in idxs if 0 <= i < len(orphans)]

        def _do_restore() -> None:
            action[0] = "restore"
            dlg.accept()

        def _do_copy() -> None:
            action[0] = "copy"
            dlg.accept()

        def _do_discard() -> None:
            action[0] = "discard"
            dlg.accept()

        def _do_discard_all() -> None:
            n = len(orphans)
            reply = QMessageBox.question(
                dlg,
                "Crash-Recovery — Alle verwerfen",
                f"Wirklich alle {n} Snapshot(s) unwiderruflich verwerfen?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            action[0] = "discard_all"
            dlg.accept()

        def _do_later() -> None:
            action[0] = "later"
            dlg.reject()

        btn_restore.clicked.connect(_do_restore)
        btn_copy.clicked.connect(_do_copy)
        btn_discard.clicked.connect(_do_discard)
        btn_discard_all.clicked.connect(_do_discard_all)
        btn_later.clicked.connect(_do_later)
        dlg.exec()

        chosen = action[0]
        if chosen == "later":
            return

        targets = orphans if chosen == "discard_all" else _selected_orphans()
        if not targets and chosen in ("restore", "copy", "discard"):
            QMessageBox.information(
                self,
                "Crash-Recovery",
                "Bitte mindestens einen Snapshot auswählen.",
            )
            return

        if chosen == "restore":
            for o in targets:
                try:
                    path = restore_orphan(o)
                    self.open_path(str(path))
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Crash-Recovery",
                        f"Konnte nicht wiederherstellen:\n{o.source_path}\n{e}",
                    )
            self._set_status(
                f"Crash-Recovery: {len(targets)} Snapshot(s) wiederhergestellt"
            )
        elif chosen == "copy":
            opened = 0
            for o in targets:
                try:
                    path = restore_orphan_as_copy(o)
                    self.open_path(str(path))
                    opened += 1
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Crash-Recovery",
                        f"Kopie fehlgeschlagen:\n{o.source_path}\n{e}",
                    )
            self._set_status(
                f"Crash-Recovery: {opened} Snapshot(s) als Kopie geöffnet"
            )
        elif chosen in ("discard", "discard_all"):
            for o in targets:
                try:
                    discard_orphan(o)
                except Exception:
                    pass
            left = []
            try:
                left = list_orphans(
                    max_age_hours=get_crash_recovery_max_age_hours()
                )
            except Exception:
                left = []
            label = (
                "alle Snapshots verworfen"
                if chosen == "discard_all"
                else f"{len(targets)} Snapshot(s) verworfen"
            )
            self._set_status(
                f"Crash-Recovery: {label}"
                + (f" ({len(left)} Rest)" if left else " (sauber)")
            )

    def _autosave_tick(self):
        if not self._autosave_enabled:
            return
        # Modal-Dialoge: Autosave pausieren; Ctrl+S (save_doc) bleibt aktiv — 0.9.8
        if self._autosave_modal_open():
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
                    # Sidecar vor Autosave sichern
                    try:
                        side = getattr(self.pdf_view.store, "sidecar_path", None)
                        if side is not None:
                            self._autosave_maybe_backup(side)
                    except Exception:
                        pass
                    # Snapshot vor Speichern; bei Crash bleibt Orphan — 1.8.0
                    self._autosave_write_recovery_snapshot()
                    self.pdf_view.schedule_sidecar_save(force=True)
                    self._clear_recovery_for_current()
                    if self.doc.path:
                        self._mark_unsaved(self.doc.path, False)
                    self._set_status(self._autosave_status_saved())
                except Exception:
                    self._blink_autosave_error_status()
            return
        if self.doc.kind not in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX):
            return
        self._sync_editor_text_before_save()
        self.doc.text = self.editor.toPlainText()
        try:
            self._autosave_maybe_backup(self.doc.path)
            # Snapshot vor Speichern; bei Crash bleibt Orphan — 1.8.0
            self._autosave_write_recovery_snapshot()
            save_document(self.doc)
            self.doc.dirty = False
            self._clear_recovery_for_current()
            if self.doc.path:
                self._mark_unsaved(self.doc.path, False)
                self._doc_cache_put(self.doc.path, self.doc)
            self._set_status(self._autosave_status_saved())
        except Exception:
            self._blink_autosave_error_status()

    def _update_license_status(self):
        from instantlensdoc.license import (
            format_ablaufdatum,
            resttage_phrase,
        )

        st = self.license_manager.status()
        self.version_label.setText(f"v{__version__}")
        rest = resttage_phrase(st.days_remaining)  # „noch X Tag(e)“ — konsistent About
        ablauf = format_ablaufdatum(st.expires_at, empty="")  # TT.MM.JJJJ — 1.0.3
        bis = f" · bis {ablauf}" if ablauf else ""
        urgent = st.allowed and st.days_remaining < 7
        if st.mode == "licensed":
            who = f" · {st.email}" if st.email else ""
            if urgent:
                text = f"⚠ Lizenz: {rest}!{who}{bis}"
                style = (
                    "color: #7B241C; background: #F5B7B1; font-weight: 800; "
                    "font-size: 12px; padding: 3px 8px; border-radius: 3px;"
                )
            else:
                text = f"Lizenz: Aktiviert{who} · {rest}{bis}"
                style = "color: #1B7A3D; font-weight: 600; padding-right: 6px;"
        elif st.mode == "trial":
            if urgent:
                text = f"⚠ Testversion: {rest}!{bis} — Hilfe → Lizenz"
                style = (
                    "color: #7B241C; background: #F9E79F; font-weight: 800; "
                    "font-size: 12px; padding: 3px 8px; border-radius: 3px;"
                )
            else:
                text = f"Lizenz: Testversion · {rest}{bis} — Hilfe → Lizenz"
                style = "color: #B9770E; font-weight: 600; padding-right: 6px;"
        else:
            text = (
                f"Lizenz: Abgelaufen{bis} — Hilfe → Lizenz · ame@sellerbach.de"
                if bis
                else "Lizenz: Abgelaufen — Hilfe → Lizenz · ame@sellerbach.de"
            )
            style = "color: #C0392B; font-weight: 700; padding-right: 6px;"
        self.license_label.setText(text)
        self.license_label.setStyleSheet(style)
        tip = st.message
        if ablauf:
            tip = f"Ablauf: {ablauf} — {tip}"
        if urgent:
            tip = f"Restlaufzeit unter 7 Tagen — {tip}"
        self.license_label.setToolTip(tip)
        # Ablaufwarnung ≤3 Tage: Banner Klick→About, Dismiss bis morgen — 1.0.5
        try:
            self._sync_expiry_warn_banner(st, ablauf)
        except Exception:
            pass
        if not st.allowed:
            QMessageBox.warning(
                self,
                "Lizenz abgelaufen",
                st.message + "\n\nDie App bleibt geöffnet, Speichern kann eingeschränkt sein.",
            )

    def _apply_expiry_banner_style(self, kind: str) -> None:
        """Warnung = Gelb, abgelaufen = Rot; Fokus-Ring sichtbar — 1.0.9."""
        banner = getattr(self, "expiry_warn_banner", None)
        if banner is None:
            return
        self._expiry_banner_kind = kind
        # Fokus-Ring (:focus) bleibt sichtbar trotz Background-Stylesheet — 1.0.9
        focus = (
            "QWidget#expiryWarnBanner:focus {"
            " border: 2px solid #0D6EFD;"
            " outline: 2px solid #0D6EFD;"
            " outline-offset: 1px;"
            "}"
        )
        if kind == "expired":
            banner.setStyleSheet(
                "QWidget#expiryWarnBanner {"
                " background: #F8D7DA; border-bottom: 1px solid #C0392B;"
                "}"
                + focus
            )
        else:
            banner.setStyleSheet(
                "QWidget#expiryWarnBanner {"
                " background: #FFF3CD; border-bottom: 1px solid #E0C36A;"
                "}"
                + focus
            )

    def _sync_expiry_warn_banner(self, st=None, ablauf: str = "") -> None:
        """Banner i18n: Warnung vs. abgelaufen mit unterschiedlicher Farbe — 1.0.6."""
        from instantlensdoc.core.i18n import tr
        from instantlensdoc.license import EXPIRY_WARN_DAYS, resttage_phrase

        if st is None:
            st = self.license_manager.status()
        banner = getattr(self, "expiry_warn_banner", None)
        if banner is None:
            return
        show = bool(self.license_manager.should_show_expiry_warning(st))
        if not show:
            banner.setVisible(False)
            return
        kind = "expired"
        if hasattr(self.license_manager, "expiry_banner_kind"):
            kind = self.license_manager.expiry_banner_kind(st)
        else:
            kind = "expired" if not st.allowed else "warn"
        self._apply_expiry_banner_style(kind)
        until = f" (bis {ablauf})" if ablauf else ""
        if kind == "expired":
            warn = tr("expiry_expired_banner").format(until=until)
        else:
            warn = tr("expiry_warn_banner").format(
                rest=resttage_phrase(st.days_remaining),
                until=until,
            )
        self.expiry_warn_label.setText(warn)
        self.expiry_warn_label.setToolTip(tr("expiry_warn_tooltip"))
        # Screenreader AccessibleName (Warnung vs. abgelaufen) — 1.0.8
        acc = tr(
            "expiry_banner_expired_accessible"
            if kind == "expired"
            else "expiry_banner_accessible"
        )
        banner.setAccessibleName(acc)
        self.expiry_warn_label.setAccessibleName(acc)
        if hasattr(self, "btn_expiry_warn_dismiss"):
            self.btn_expiry_warn_dismiss.setText(tr("expiry_dismiss_label"))
            self.btn_expiry_warn_dismiss.setToolTip(tr("expiry_dismiss_tooltip"))
            self.btn_expiry_warn_dismiss.setAccessibleName(
                tr("expiry_dismiss_accessible")
            )
        if hasattr(self, "btn_expiry_warn_close"):
            self.btn_expiry_warn_close.setToolTip(tr("expiry_close_tooltip"))
            self.btn_expiry_warn_close.setAccessibleName(
                tr("expiry_close_accessible")
            )
        was_visible = banner.isVisible()
        banner.setVisible(True)
        if not was_visible:
            # Fokus setzen → Fokus-Ring sichtbar; Enter öffnet Aktivierung — 1.0.9
            try:
                banner.setFocus(Qt.OtherFocusReason)
            except Exception:
                try:
                    banner.setFocus()
                except Exception:
                    pass
            self.statusBar().showMessage(warn, 8000)
            if (
                getattr(self, "_tray", None) is not None
                and self._tray is not None
                and self._tray.isVisible()
            ):
                try:
                    title = (
                        f"{DISPLAY_NAME}: Lizenz abgelaufen"
                        if kind == "expired"
                        else f"{DISPLAY_NAME}: Ablauf in ≤{EXPIRY_WARN_DAYS} Tagen"
                    )
                    self._tray.showMessage(
                        title,
                        warn,
                        QSystemTrayIcon.Warning,
                        8000,
                    )
                except Exception:
                    pass

    def _on_expiry_warn_clicked(self, _event=None) -> None:
        """Klick auf Warnung öffnet About (mit Lizenz aktivieren) — 1.0.5."""
        try:
            AboutDialog(self).exec()
        except Exception:
            try:
                self._license()
            except Exception:
                pass
        try:
            self._update_license_status()
        except Exception:
            pass

    def _dismiss_expiry_warning(self) -> None:
        """Dismiss speichert bis morgen — 1.0.5/1.0.6."""
        from instantlensdoc.core.i18n import tr

        try:
            if hasattr(self.license_manager, "dismiss_expiry_warning"):
                self.license_manager.dismiss_expiry_warning()
            else:
                self.license_manager.mark_expiry_warning_shown()
        except Exception:
            pass
        banner = getattr(self, "expiry_warn_banner", None)
        if banner is not None:
            banner.setVisible(False)
        try:
            self.statusBar().showMessage(tr("expiry_dismiss_status"), 4000)
        except Exception:
            pass

    def _on_text_changed(self):
        if self.doc and self.doc.kind in (
            DocKind.TEXT,
            DocKind.MARKDOWN,
            DocKind.HTML,
            DocKind.DOCX,
            DocKind.RTF,
        ):
            self._sync_editor_rich_meta()
            if self.doc.path:
                self._mark_unsaved(self.doc.path, True)
            else:
                self._update_unsaved_status()
        if self.stack.currentWidget() is self.editor_pane:
            words, chars = self.editor.word_stats()
            self.word_status_label.setText(f"{words} Wörter · {chars} Z.")

    def _on_pdf_document_changed(self):
        # Sticky 0-Treffer-Status bei Dokumentwechsel löschen — 1.1.8
        self._clear_ann_zero_sticky_status()
        self._update_doc_status()
        self._sync_pdf_page_shortcuts()
        if self.pdf_view.pdf_path:
            # Thumbs/Outline nach Erst-Render deferren — Open bleibt flüssig — 2.6.37
            open_gen = int(getattr(self.pdf_view, "_open_generation", 0) or 0)
            pages = int(getattr(self.pdf_view, "page_count", 0) or 0)

            def _deferred_sidebar():
                if not self.pdf_view.pdf_path:
                    return
                if int(getattr(self.pdf_view, "_open_generation", 0) or 0) != open_gen:
                    return
                self._refresh_thumbs()
                self._refresh_outline(self.pdf_view.pdf_path)
                self._refresh_page_favorites()
                # AcroForm-Vollscan nicht beim Open großer PDFs — 2.6.45
                try:
                    from ild_pdf.limits import FORM_SCAN_PAGE_THRESHOLD

                    form_ok = pages < int(FORM_SCAN_PAGE_THRESHOLD)
                except Exception:
                    form_ok = pages < 80
                if form_ok:
                    self._refresh_form_fields()
                else:
                    try:
                        self.sidebar.clear_form_fields()
                    except Exception:
                        pass

            QTimer.singleShot(0, _deferred_sidebar)
        else:
            self.sidebar.clear_thumbs()
            self.sidebar.clear_annotations()
            self.sidebar.set_outline([])
            self.sidebar.clear_form_fields()
            if hasattr(self.sidebar, "clear_redactions"):
                self.sidebar.clear_redactions()
            self.sidebar.clear_page_favorites()
            self.sidebar.clear_line_favorites()
        # Dokument-Statistik Auto-Update bei Doc-Wechsel — 1.6.1
        self._sync_doc_stats_panel()

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
        """Ctrl+F: Editor → Suchen/Ersetzen; PDF → Multi-Dokument-Suche."""
        if self._editor_document_active():
            self._find_replace()
            return
        if self._pdf_tab_active():
            self._open_multi_doc_search()
            return
        self.sidebar.setVisible(True)
        le = self.sidebar.search.lineEdit()
        if le is not None:
            le.setFocus()
            le.selectAll()
        else:
            self.sidebar.search.setFocus()

    def _pdf_tab_active(self) -> bool:
        """True wenn der aktuelle Tab ein PDF ist (Stack oder DocKind) — 2.6.54."""
        stack = getattr(self, "stack", None)
        pdf = getattr(self, "pdf_view", None)
        if stack is not None and pdf is not None and stack.currentWidget() is pdf:
            return True
        doc = getattr(self, "doc", None)
        if doc is not None and getattr(doc, "kind", None) == DocKind.PDF:
            return True
        return False

    def _editor_document_active(self) -> bool:
        """True nur bei sichtbarem Rich/Text-Editor — nie PDF/Bild/Welcome — 2.6.54.

        Editor-Aktionen (Zeilenabstand, Fett, Einrückung, Seitenlayout, …) dürfen
        keinen PDF-Tab umschalten, kein Geschwister-DOCX öffnen und kein neues
        Text-Dokument anlegen.
        """
        if self._pdf_tab_active():
            return False
        stack = getattr(self, "stack", None)
        pane = getattr(self, "editor_pane", None)
        if stack is None or pane is None or stack.currentWidget() is not pane:
            return False
        doc = getattr(self, "doc", None)
        if doc is not None and getattr(doc, "kind", None) in (DocKind.PDF, DocKind.IMAGE):
            return False
        return True

    def _layout_mode_active(self) -> bool:
        pane = getattr(self, "dtp_pane", None)
        stack = getattr(self, "stack", None)
        return pane is not None and stack is not None and stack.currentWidget() is pane

    def _guard_editor_action(self, what: str) -> bool:
        """Editor-only Aktion: bei PDF/anderem Tab no-op, kein Stack-Wechsel — 2.6.54."""
        if self._editor_document_active() or self._layout_mode_active():
            return True
        self._set_status(f"{what} nur im Editor")
        return False

    def _track_editor_action(self, act) -> object:
        lst = getattr(self, "_editor_only_actions", None)
        if lst is None:
            self._editor_only_actions = []
            lst = self._editor_only_actions
        lst.append(act)
        return act

    def _sync_editor_only_actions(self, *_args) -> None:
        on = self._editor_document_active() or self._layout_mode_active()
        for act in getattr(self, "_editor_only_actions", None) or []:
            try:
                act.setEnabled(on)
            except Exception:
                pass
        for menu in getattr(self, "_editor_only_menus", None) or []:
            try:
                menu.setEnabled(on)
            except Exception:
                pass

    def _toggle_bold(self) -> None:
        if self._layout_mode_active():
            self.dtp_pane.apply_font(bold=True, toggle=True)
            return
        if not self._guard_editor_action("Fett"):
            return
        self.editor.toggle_bold_selection()
        self._sync_editor_rich_meta()
        self._set_status("Fett (Zeichenformat)")

    def _toggle_italic(self) -> None:
        if self._layout_mode_active():
            self.dtp_pane.apply_font(italic=True, toggle=True)
            return
        if not self._guard_editor_action("Kursiv"):
            return
        self.editor.toggle_italic_selection()
        self._sync_editor_rich_meta()
        self._set_status("Kursiv (Zeichenformat)")

    def _toggle_underline(self) -> None:
        if self._layout_mode_active():
            self.dtp_pane.apply_font(underline=True, toggle=True)
            return
        if not self._guard_editor_action("Unterstrichen"):
            return
        self.editor.toggle_underline_selection()
        self._sync_editor_rich_meta()
        self._set_status("Unterstrichen (Zeichenformat)")

    def _toggle_strike(self) -> None:
        if not self._guard_editor_action("Durchgestrichen"):
            return
        self.editor.toggle_strike_selection()
        self._sync_editor_rich_meta()
        self._set_status("Durchgestrichen (Zeichenformat)")

    def _cut_editor(self) -> None:
        if not self._guard_editor_action("Ausschneiden"):
            return
        from PySide6.QtGui import QTextCursor

        cur = self.editor.textCursor()
        if not cur.hasSelection():
            line = QTextCursor(cur)
            line.select(QTextCursor.LineUnderCursor)
            self.editor.setTextCursor(line)
        self.editor.cut()
        self._sync_editor_rich_meta()

    def _paste_editor(self) -> None:
        if not self._guard_editor_action("Einfügen"):
            return
        from PySide6.QtGui import QGuiApplication

        clip = ""
        try:
            cb = QGuiApplication.clipboard()
            clip = cb.text() if cb is not None else ""
        except Exception:
            clip = ""
        if not (clip or "").strip():
            from instantlensdoc.ui.feature_dialog import FeatureDialog

            FeatureDialog(
                self,
                title="Einfügen",
                body="Die Zwischenablage ist leer.",
                object_name="ildEmptyClipboardDialog",
            ).exec()
            return
        self.editor.paste()
        self._sync_editor_rich_meta()

    def _defer_format_dialog(self, slot) -> None:
        """Menü zuerst schließen, dann modalen Dialog — kein Font-/Scan-Enum vorher."""
        import os

        if os.environ.get("ILD_SMOKE_QT") == "1":
            slot()
            return
        QTimer.singleShot(0, slot)

    def _choose_font(self) -> None:
        if not self._guard_editor_action("Schriftart"):
            return
        self._defer_format_dialog(self._run_font_dialog)

    def _run_font_dialog(self) -> None:
        """QFontDialog.getFont (QFontDatabase/Windows-Schriften), Auswahl oder Dokument."""
        if not self._guard_editor_action("Schriftart"):
            return
        from PySide6.QtGui import QFontDatabase
        from PySide6.QtWidgets import QFontDialog

        current = self.editor.currentCharFormat().font()
        if not current.family():
            try:
                current = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
            except Exception:
                current = self.editor.document().defaultFont()
        # Native QFontDialog liest die Plattform-Fontliste (Windows) selbst — nichts vorab enumerieren.
        result = QFontDialog.getFont(current, self, "Schriftart")
        if isinstance(result, tuple) and len(result) >= 2:
            font, ok = result[0], result[1]
        else:
            font, ok = result, True
        if not ok or font is None:
            return
        try:
            if not font.family():
                return
        except Exception:
            return
        self.editor.apply_qfont(font)
        self._sync_editor_rich_meta()
        self._set_status(f"Schriftart: {font.family()} {int(font.pointSize() or 0)} pt")

    def _choose_font_size(self) -> None:
        if not self._guard_editor_action("Schriftgröße"):
            return
        from PySide6.QtWidgets import QInputDialog

        probe = self.editor.currentCharFormat()
        cur_sz = int(probe.fontPointSize() or self.editor.document().defaultFont().pointSize() or 11)
        size, ok = QInputDialog.getInt(self, "Schriftgröße", "Punkt:", cur_sz, 6, 96)
        if not ok:
            return
        self.editor.apply_font_size(float(size))
        self._sync_editor_rich_meta()
        self._set_status(f"Schriftgröße: {size} pt")

    def _choose_font_color(self) -> None:
        if not self._guard_editor_action("Schriftfarbe"):
            return
        self._defer_format_dialog(self._run_font_color_dialog)

    def _run_font_color_dialog(self) -> None:
        if not self._guard_editor_action("Schriftfarbe"):
            return
        import os

        from PySide6.QtWidgets import QColorDialog

        initial = self.editor.currentCharFormat().foreground().color()
        if os.environ.get("ILD_SMOKE_QT") == "1":
            color = QColorDialog.getColor(initial, self, "Schriftfarbe")
            if color is None or not color.isValid():
                color = QColor("#cc0000")
        else:
            color = QColorDialog.getColor(initial, self, "Schriftfarbe")
        if color is None or not color.isValid():
            return
        self.editor.apply_font_color(color)
        self._sync_editor_rich_meta()
        self._set_status(f"Schriftfarbe: {color.name()}")

    def _choose_highlight_color(self) -> None:
        if not self._guard_editor_action("Texthervorhebung"):
            return
        self._defer_format_dialog(self._run_highlight_color_dialog)

    def _run_highlight_color_dialog(self) -> None:
        if not self._guard_editor_action("Texthervorhebung"):
            return
        import os

        from PySide6.QtWidgets import QColorDialog

        initial = QColor(self.editor.HIGHLIGHT_COLOR)
        try:
            probe = self.editor._selection_probe_format(self.editor.textCursor())
            if probe.background().style() != Qt.NoBrush:
                initial = probe.background().color()
        except Exception:
            pass
        if os.environ.get("ILD_SMOKE_QT") == "1":
            color = QColorDialog.getColor(initial, self, "Hintergrundfarbe")
            if color is None or not color.isValid():
                color = QColor(self.editor.HIGHLIGHT_COLOR)
        else:
            color = QColorDialog.getColor(initial, self, "Hintergrundfarbe")
        if color is None or not color.isValid():
            return
        self.editor.apply_highlight_color(color)
        self._sync_editor_rich_meta()
        scope = "Auswahl" if self.editor.textCursor().hasSelection() else "Dokument"
        self._set_status(f"Hintergrundfarbe ({scope}): {color.name()}")

    def _clear_formatting(self) -> None:
        if not self._guard_editor_action("Formatierungen löschen"):
            return
        self.editor.clear_formatting()
        self._sync_editor_rich_meta()
        self._set_status("Formatierungen gelöscht")

    def _apply_paragraph_style(self, style_id: str) -> None:
        if not self._guard_editor_action("Formatvorlage"):
            return
        self.editor.apply_style_paragraph(style_id)
        self._sync_editor_rich_meta()
        self._set_status(f"Formatvorlage: {style_id}")

    def _toggle_list(self, *, ordered: bool = False) -> None:
        if not self._guard_editor_action("Liste"):
            return
        self.editor.toggle_list(ordered=ordered)
        self._sync_editor_rich_meta()
        self._set_status("Nummerierung" if ordered else "Aufzählung")

    def _insert_break(self, kind: str = "line") -> None:
        if not self._guard_editor_action("Umbruch"):
            return
        self.editor.insert_break(kind)
        self._sync_editor_rich_meta()
        self._set_status("Seitenumbruch" if kind == "page" else "Zeilenumbruch")

    def _paragraph_format_dialog(self) -> None:
        if not self._guard_editor_action("Absatz"):
            return
        from instantlensdoc.ui.paragraph_dialog import ParagraphDialog

        dlg = ParagraphDialog(self.editor.current_paragraph_spec(), self)
        if dlg.exec() != QDialog.Accepted:
            return
        spec = dlg.result_spec()
        self.editor.apply_paragraph_spec(spec)
        self._sync_editor_rich_meta()
        self._set_status(
            f"Absatz: {spec.line_spacing:g} / davor {spec.space_before_pt:g} pt"
        )

    def _set_keep_with_next(self, enabled: bool = True) -> None:
        if not self._guard_editor_action("Absatz"):
            return
        self.editor.set_paragraph_spacing(keep_with_next=bool(enabled))
        self._sync_editor_rich_meta()
        self._set_status("Mit nächstem Absatz zusammenhalten")

    def _set_widow_orphan(self, enabled: bool = True) -> None:
        if not self._guard_editor_action("Absatz"):
            return
        self.editor.set_paragraph_spacing(widow_orphan=bool(enabled))
        self._sync_editor_rich_meta()
        self._set_status("Absatzkontrolle (Witwen/Waisen)")

    def _change_list_glyph_dialog(self) -> None:
        if not self._guard_editor_action("Aufzählungszeichen"):
            return
        from instantlensdoc.ui.list_glyph_dialog import ListGlyphDialog
        from instantlensdoc.ui.rich_lists import DEFAULT_BULLET, parse_list_prefix

        cur = parse_list_prefix(self.editor.textCursor().block().text() or "")
        glyph = cur.glyph if cur and not cur.ordered else DEFAULT_BULLET
        dlg = ListGlyphDialog(glyph, self)
        if dlg.exec() != QDialog.Accepted:
            return
        self.editor.set_list_glyph(dlg.result_glyph())
        self._sync_editor_rich_meta()
        self._set_status(f"Aufzählungszeichen: {dlg.result_glyph()}")

    def _restart_list_numbering(self) -> None:
        if not self._guard_editor_action("Nummerierung"):
            return
        if self.editor.restart_list_numbering():
            self._sync_editor_rich_meta()
            self._set_status("Nummerierung neu begonnen")
        else:
            self._set_status("Keine nummerierte Liste an der Auswahl")

    def _adjust_list_indent(self, delta: int) -> None:
        if not self._guard_editor_action("Listenebene"):
            return
        self.editor.adjust_list_indent(int(delta))
        self._sync_editor_rich_meta()
        self._set_status("Listenebene erhöht" if delta > 0 else "Listenebene verringert")

    def _set_cell_vertical_align(self, alignment: str) -> None:
        if not self._guard_editor_action("Zellenausrichtung"):
            return
        if self.editor.set_table_cell_vertical_alignment(alignment):
            self._sync_editor_rich_meta()
            self._set_status(f"Zelle: {alignment}")
        else:
            self._set_status("Keine Tabelle an der Auswahl — zuerst Tabelle markieren")

    def _insert_section_break(self) -> None:
        if not self._guard_editor_action("Abschnittsumbruch"):
            return
        self.editor.insert_section_break()
        self._sync_editor_rich_meta()
        self._set_status("Abschnittsumbruch eingefügt")

    def _header_footer_dialog(self) -> None:
        if not self._guard_editor_action("Kopf-/Fußzeile"):
            return
        from instantlensdoc.ui.header_footer_dialog import HeaderFooterDialog

        dlg = HeaderFooterDialog(
            self.editor.document_header(),
            self.editor.document_footer(),
            self,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        header, footer = dlg.result_header_footer()
        self.editor.set_document_header_footer(header, footer)
        self._sync_editor_rich_meta()
        self._set_status("Kopf-/Fußzeile gesetzt")

    def _field_token_dialog(self) -> None:
        if not self._guard_editor_action("Ersatzzeichen"):
            return
        from instantlensdoc.ui.field_token_dialog import FieldTokenDialog

        dlg = FieldTokenDialog(
            self,
            specs=self.editor.field_token_specs(),
            header=self.editor.document_header(),
            footer=self.editor.document_footer(),
        )

        def _insert_now() -> None:
            ident, display = dlg.result_field()
            target = dlg.result_target()
            self._apply_field_token_dialog_state(dlg, ident, display, target)
            dlg.mark_inserted()

        dlg.insert_requested.connect(_insert_now)
        if dlg.exec() != QDialog.Accepted:
            return
        ident, display = dlg.result_field()
        target = dlg.result_target()
        if not dlg.did_insert():
            self._apply_field_token_dialog_state(dlg, ident, display, target)
        else:
            self.editor.set_field_token_specs(dlg.result_specs())
            header, footer = dlg.result_header_footer()
            self.editor.set_document_header_footer(header, footer)
            self._sync_editor_rich_meta()
        self._set_status(f"Ersatzzeichen: {{{ident}}} → {dlg.target_combo.currentText()}")

    def _apply_field_token_dialog_state(self, dlg, ident: str, display: str, target: str) -> None:
        self.editor.set_field_token_specs(dlg.result_specs())
        dest = target or "body"
        if dest in {"header", "footer"}:
            dlg.insert_token_at_target(ident, display)
            header, footer = dlg.result_header_footer()
            self.editor.set_document_header_footer(header, footer)
        else:
            self.editor.insert_field_token(ident, display=display, target="body")
            header, footer = dlg.result_header_footer()
            self.editor.set_document_header_footer(header, footer)
        self._sync_editor_rich_meta()

    def _field_resolve_context(self, *, page: int = 1, page_count: int | None = None):
        from instantlensdoc.core.field_tokens import make_resolve_context

        filename = ""
        author = ""
        if self.doc is not None:
            try:
                if self.doc.path:
                    filename = Path(self.doc.path).name
                elif self.doc.title:
                    filename = str(self.doc.title)
            except Exception:
                filename = str(getattr(self.doc, "title", "") or "")
            author = str((self.doc.meta or {}).get("author") or "")
        if not author:
            try:
                import getpass

                author = getpass.getuser() or ""
            except Exception:
                author = ""
        total = page_count
        if total is None:
            try:
                total = int(self.editor.document().pageCount() or 1)
            except Exception:
                total = 1
        return make_resolve_context(
            page=page,
            page_count=max(1, int(total or 1)),
            filename=filename,
            author=author,
            specs=self.editor.field_token_specs(),
        )

    def _sync_editor_rich_meta(self) -> None:
        """Plaintext + HTML-Meta aus dem Editor für DOCX/HTML/RTF-Speichern — 2.6.49."""
        if not self.doc:
            return
        if self.doc.kind not in (
            DocKind.TEXT,
            DocKind.MARKDOWN,
            DocKind.HTML,
            DocKind.DOCX,
            DocKind.RTF,
        ):
            return
        try:
            self.doc.text = self.editor.toPlainText()
        except Exception:
            return
        if self.doc.kind in (DocKind.DOCX, DocKind.HTML, DocKind.RTF) or self.doc.meta.get(
            "rich_text"
        ) or bool(getattr(self.editor, "_rich_mode", False)):
            try:
                self.doc.meta["html"] = self.editor.to_rich_html()
                self.doc.meta["rich_text"] = True
            except Exception:
                pass
            try:
                hdr = self.editor.document_header()
                ftr = self.editor.document_footer()
                if hdr:
                    self.doc.meta["header"] = hdr
                else:
                    self.doc.meta.pop("header", None)
                if ftr:
                    self.doc.meta["footer"] = ftr
                else:
                    self.doc.meta.pop("footer", None)
            except Exception:
                pass
            try:
                ft = self.editor.field_tokens()
                if ft:
                    self.doc.meta["field_tokens"] = dict(ft)
                else:
                    self.doc.meta.pop("field_tokens", None)
                specs = self.editor.field_token_specs()
                if specs:
                    from instantlensdoc.core.field_tokens import serialize_field_specs

                    self.doc.meta["field_tokens"] = serialize_field_specs(specs)
            except Exception:
                pass
        self.doc.dirty = True

    def _set_paragraph_alignment(self, alignment: str) -> None:
        if self._layout_mode_active():
            self.dtp_pane.apply_alignment(alignment)
            return
        if not self._guard_editor_action("Absatzformat"):
            return
        if self.editor.set_paragraph_alignment(alignment):
            self._sync_editor_rich_meta()
            self._on_text_changed()
            self._set_status(f"Absatzausrichtung: {alignment}")
        else:
            self._set_status(f"Absatzausrichtung unverändert ({alignment})")

    def _set_paragraph_line_spacing(self, line_spacing: float) -> None:
        if self._layout_mode_active():
            self.dtp_pane.apply_line_spacing(line_spacing)
            return
        if not self._guard_editor_action("Zeilenabstand"):
            return
        if self.editor.set_paragraph_spacing(line_spacing=line_spacing):
            self._sync_editor_rich_meta()
            self._on_text_changed()
            self._set_status(f"Zeilenabstand: {line_spacing:g}")
        else:
            self._set_status("Zeilenabstand unverändert")

    def _set_typography(
        self,
        *,
        tracking: float | None = None,
        kerning: float | None = None,
        leading: float | None = None,
    ) -> None:
        """Tracking/Kerning/Leading — 2.6.13."""
        if self._layout_mode_active():
            self.dtp_pane.apply_typography(
                tracking=tracking, kerning=kerning, leading=leading
            )
            return
        if not self._guard_editor_action("Typografie"):
            return
        if self.editor.apply_typography(
            tracking=tracking, kerning=kerning, leading=leading
        ):
            self._sync_editor_rich_meta()
            self._on_text_changed()
            parts = []
            if tracking is not None:
                parts.append(f"Tracking={tracking:g}")
            if kerning is not None:
                parts.append(f"Kerning={kerning:g}")
            if leading is not None:
                parts.append(f"Leading={leading:g}")
            self._set_status("Typografie: " + (", ".join(parts) or "ok"))
        else:
            self._set_status("Typografie unverändert")

    def _apply_drop_cap(self) -> None:
        if self._layout_mode_active():
            self.dtp_pane.apply_drop_cap(lines=3, chars=1)
            return
        if not self._guard_editor_action("Drop Cap"):
            return
        if self.editor.apply_drop_cap(lines=3, chars=1):
            self._sync_editor_rich_meta()
            self._on_text_changed()
            self._set_status("Drop Cap gesetzt (3 Zeilen)")
        else:
            self._set_status("Drop Cap unverändert")

    def _hyphenate_document(self, lang: str = "de") -> None:
        if self._layout_mode_active():
            self.dtp_pane.hyphenate(lang=lang)
            return
        if not self._guard_editor_action("Silbentrennung"):
            return
        n = self.editor.hyphenate_document(lang=lang)
        if self.doc and self.doc.kind in (
            DocKind.TEXT,
            DocKind.MARKDOWN,
            DocKind.HTML,
            DocKind.DOCX,
        ):
            self.doc.text = self.editor.toPlainText()
            self.doc.dirty = True
        self._on_text_changed()
        self._set_status(f"Silbentrennung ({lang}): {n} Stellen")

    def _set_image_text_wrap(self) -> None:
        """Textumfluss: im Layout-Modus auf Auswahl, sonst layout_doc — 2.6.13/2.6.54."""
        if self._layout_mode_active():
            self.dtp_pane.apply_wrap_mode(dialog=True)
            return
        from PySide6.QtWidgets import QInputDialog

        if not self.layout_doc.image_frames:
            self._set_status("Kein Bildrahmen im Layout")
            return
        modes = ["bounding_box", "contour", "jump_object", "none"]
        mode, ok = QInputDialog.getItem(
            self, "Textumfluss", "Modus:", modes, 0, False
        )
        if not ok:
            return
        fr = self.layout_doc.image_frames[0]
        self.layout_doc.set_text_wrap(fr.id, mode)
        self._set_status(f"Textumfluss {mode} für Rahmen {fr.id}")

    def _insert_hyperlink_dialog(self) -> None:
        """Hyperlink (URL oder Dokumentziel) in Editor — 2.6.26."""
        from instantlensdoc.ui.hyperlink_dialog import HyperlinkDialog

        if not self._guard_editor_action("Hyperlink"):
            return
        cursor = self.editor.textCursor()
        selected = cursor.selectedText().replace("\u2029", "\n").strip()
        dlg = HyperlinkDialog(
            self,
            initial_text=selected,
            document_text=self.editor.toPlainText(),
        )
        if dlg.exec() != QDialog.Accepted:
            return
        snippet = dlg.result_snippet
        label = getattr(dlg, "result_text", "") or selected
        target = dlg.result_target
        if not self.editor.insert_hyperlink(label, target) and snippet:
            if selected and cursor.hasSelection():
                cursor.insertText(snippet)
            else:
                self.editor.insertPlainText(snippet)
        self._sync_editor_rich_meta()
        if self.doc and self.doc.kind in (
            DocKind.TEXT,
            DocKind.MARKDOWN,
            DocKind.HTML,
            DocKind.DOCX,
        ):
            self.doc.text = self.editor.toPlainText()
            self.doc.dirty = True
        self._on_text_changed()
        self._set_status(f"Hyperlink: {dlg.result_target}")

    def _insert_shape_frame(self) -> None:
        """Formrahmen ins Layout — 2.6.26."""
        from PySide6.QtWidgets import QInputDialog
        from instantlensdoc.core.layout import SHAPE_KINDS

        shape, ok = QInputDialog.getItem(
            self, "Form", "Formart:", list(SHAPE_KINDS), 0, False
        )
        if not ok:
            return
        if shape not in SHAPE_KINDS:
            self._set_status(f"Unbekannte Form: {shape}")
            return
        if self._layout_mode_active():
            self.dtp_pane.add_shape(str(shape))
            self._set_status(f"Form {shape} (DTP)")
            return
        try:
            fr = self.layout_doc.add_shape(shape)
        except Exception as e:
            QMessageBox.warning(self, "Form", str(e))
            return
        self._set_status(f"Form {shape} eingefügt ({fr.id})")

    def _insert_video_placeholder(self) -> None:
        """Video-Platzhalter mit URL — 2.6.26."""
        from PySide6.QtWidgets import QInputDialog

        url, ok = QInputDialog.getText(
            self, "Video-Platzhalter", "Video-URL (http/https):", text="https://"
        )
        if not ok or not (url or "").strip():
            return
        title, ok2 = QInputDialog.getText(self, "Video-Platzhalter", "Titel (optional):")
        if not ok2:
            title = ""
        try:
            fr = self.layout_doc.add_video_placeholder(url.strip(), title=title or "")
        except ValueError as e:
            QMessageBox.warning(self, "Video", str(e))
            return
        self._set_status(f"Video-Platzhalter: {fr.video_url} ({fr.id})")

    def _scale_image_frame(self) -> None:
        """Bild-/Formrahmen skalieren — 2.6.26."""
        from PySide6.QtWidgets import QInputDialog

        if self._layout_mode_active():
            sel = self.dtp_pane.scene.selected_frames()
            if not sel:
                self._feature_dialog(
                    "Skalieren",
                    "Zuerst einen Rahmen im Layout wählen.",
                    object_name="ildScaleImageDialog",
                )
                return
            factor, ok = QInputDialog.getDouble(
                self, "Skalieren", "Faktor:", 1.25, 0.1, 10.0, 2
            )
            if not ok:
                return
            self.dtp_pane.scale_selected(float(factor))
            return
        if not self.layout_doc.image_frames:
            self._feature_dialog(
                "Skalieren",
                "Kein Bild- oder Formrahmen im Layout. Zuerst Einfügen → Bild…",
                object_name="ildScaleImageDialog",
            )
            return
        factor, ok = QInputDialog.getDouble(
            self, "Skalieren", "Faktor:", 1.25, 0.1, 10.0, 2
        )
        if not ok:
            return
        fr = self.layout_doc.image_frames[0]
        self.layout_doc.scale_image(fr.id, float(factor))
        self._set_status(f"Rahmen {fr.id} skaliert ×{factor}")

    def _crop_image_frame(self) -> None:
        """Bild zuschneiden — 2.6.26."""
        from PySide6.QtWidgets import QInputDialog

        if not self.layout_doc.image_frames:
            self._feature_dialog(
                "Zuschneiden",
                "Kein Bildrahmen im Layout. Zuerst Einfügen → Bild…",
                object_name="ildCropImageDialog",
            )
            return
        fr = self.layout_doc.image_frames[0]
        if getattr(fr, "media_kind", "image") == "video":
            self._feature_dialog(
                "Zuschneiden",
                "Video-Platzhalter nicht zuschneidbar.",
                object_name="ildCropImageDialog",
            )
            return
        left, ok = QInputDialog.getDouble(self, "Zuschneiden", "Links (0–0.49):", 0.05, 0, 0.49, 2)
        if not ok:
            return
        top, ok = QInputDialog.getDouble(self, "Zuschneiden", "Oben (0–0.49):", 0.05, 0, 0.49, 2)
        if not ok:
            return
        right, ok = QInputDialog.getDouble(self, "Zuschneiden", "Rechts (0–0.49):", 0.05, 0, 0.49, 2)
        if not ok:
            return
        bottom, ok = QInputDialog.getDouble(self, "Zuschneiden", "Unten (0–0.49):", 0.05, 0, 0.49, 2)
        if not ok:
            return
        try:
            self.layout_doc.crop_image(fr.id, left=left, top=top, right=right, bottom=bottom)
        except ValueError as e:
            QMessageBox.warning(self, "Zuschneiden", str(e))
            return
        self._set_status(f"Rahmen {fr.id} zugeschnitten")

    def _toggle_rulers(self, checked: bool = False) -> None:
        on = bool(checked)
        if hasattr(self.pdf_view, "set_show_rulers"):
            self.pdf_view.set_show_rulers(on)
        if hasattr(self, "_rulers_action") and self._rulers_action is not None:
            self._rulers_action.blockSignals(True)
            self._rulers_action.setChecked(on)
            self._rulers_action.blockSignals(False)

    def _toggle_alignment_grid(self, checked: bool = False) -> None:
        on = bool(checked)
        if hasattr(self.pdf_view, "set_show_alignment_grid"):
            self.pdf_view.set_show_alignment_grid(on)
        if hasattr(self, "_grid_action") and self._grid_action is not None:
            self._grid_action.blockSignals(True)
            self._grid_action.setChecked(on)
            self._grid_action.blockSignals(False)

    def _toggle_satzspiegel(self, checked: bool = False) -> None:
        on = bool(checked)
        if hasattr(self.pdf_view, "set_show_satzspiegel"):
            self.pdf_view.set_show_satzspiegel(on)
        if hasattr(self, "_satzspiegel_action") and self._satzspiegel_action is not None:
            self._satzspiegel_action.blockSignals(True)
            self._satzspiegel_action.setChecked(on)
            self._satzspiegel_action.blockSignals(False)

    def _auto_format_document(self) -> None:
        """Automatische Formatierung Editor oder PDF — 2.6.10."""
        if self.stack.currentWidget() is self.editor_pane:
            n = self.editor.apply_auto_format()
            if not n:
                self.editor.apply_style_paragraph("h1")
                n = 1
            if self.doc and self.doc.kind in (
                DocKind.TEXT,
                DocKind.MARKDOWN,
                DocKind.HTML,
                DocKind.DOCX,
            ):
                self.doc.text = self.editor.toPlainText()
                self.doc.dirty = True
            self._on_text_changed()
            self._set_status(f"Automatische Formatierung: {n} Zeile(n) angepasst")
            return
        path = getattr(self.pdf_view, "pdf_path", None)
        if not path:
            self._set_status("Kein Dokument für Auto-Format")
            return
        from ild_pdf.auto_format import auto_format_pdf

        try:
            result = auto_format_pdf(path, update_toc=True)
            self._refresh_outline(path)
            self._set_status(
                f"Auto-Format PDF: {len(result.headings)} Überschrift(en), "
                "TOC/Outline aktualisiert"
            )
        except Exception as e:
            self._set_status(f"Auto-Format fehlgeschlagen: {e}")

    def _update_auto_toc(self) -> None:
        """TOC aktualisieren (Editor Markdown / PDF Outline) — 2.6.10."""
        if self.stack.currentWidget() is self.editor_pane:
            self.editor.update_auto_toc()
            if self.doc and self.doc.kind in (
                DocKind.TEXT,
                DocKind.MARKDOWN,
                DocKind.HTML,
                DocKind.DOCX,
            ):
                self.doc.text = self.editor.toPlainText()
                self.doc.dirty = True
            self._on_text_changed()
            self._set_status("Inhaltsverzeichnis (Markdown) aktualisiert")
            return
        path = getattr(self.pdf_view, "pdf_path", None)
        if not path:
            self._set_status("Kein PDF für Inhaltsverzeichnis")
            return
        from ild_pdf.auto_format import generate_toc_for_pdf

        try:
            result = generate_toc_for_pdf(path, write=True)
            self._refresh_outline(path)
            self._set_status(
                f"Inhaltsverzeichnis: {result.outline_count} Einträge → Outline/Sidebar"
            )
        except Exception as e:
            self._set_status(f"TOC fehlgeschlagen: {e}")

    def _update_figure_list(self) -> None:
        """Abbildungsverzeichnis aktualisieren — 2.6.28."""
        if not self._guard_editor_action("Abbildungsverzeichnis"):
            return
        self.editor.update_figure_list()
        if self.doc and self.doc.kind in (
            DocKind.TEXT,
            DocKind.MARKDOWN,
            DocKind.HTML,
            DocKind.DOCX,
        ):
            self.doc.text = self.editor.toPlainText()
            self.doc.dirty = True
        self._on_text_changed()
        self._set_status("Abbildungsverzeichnis aktualisiert")

    def _update_index(self) -> None:
        """Stichwortverzeichnis aktualisieren — 2.6.28."""
        if not self._guard_editor_action("Stichwortverzeichnis"):
            return
        self.editor.update_index()
        if self.doc and self.doc.kind in (
            DocKind.TEXT,
            DocKind.MARKDOWN,
            DocKind.HTML,
            DocKind.DOCX,
        ):
            self.doc.text = self.editor.toPlainText()
            self.doc.dirty = True
        self._on_text_changed()
        self._set_status("Stichwortverzeichnis aktualisiert")

    def _find_replace(self):
        if not self._guard_editor_action("Suchen und Ersetzen"):
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
        if not self._require_pdf("Gehe zu Seite"):
            return
        if int(getattr(self.pdf_view, "page_count", 0) or 0) < 1:
            self._feature_dialog("Gehe zu Seite", "PDF hat keine Seiten.")
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
            if self.editor.rich_mode():
                try:
                    meta["html"] = self.editor.to_rich_html()
                    meta["rich_text"] = True
                except Exception:
                    pass
            self.doc = Document(kind=self.doc.kind, title=title, text=text, dirty=True, meta=meta)
            self.editor.blockSignals(True)
            if meta.get("html"):
                try:
                    self.editor.set_rich_html(
                        str(meta["html"]), base_font=self._rich_base_font_for_meta(meta)
                    )
                except Exception:
                    self.editor.setPlainText(text)
            else:
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
        self._feature_dialog(
            "Tab duplizieren",
            "Tab duplizieren braucht Editor-Inhalt oder eine gespeicherte Datei.",
            object_name="ildDuplicateTabDialog",
        )

    def reopen_current(self):
        """Aktuelle Datei vom Datenträger neu laden."""
        if not self.doc or not self.doc.path:
            self._feature_dialog(
                "Erneut öffnen",
                "Keine gespeicherte Datei zum erneuten Öffnen.",
                object_name="ildReopenDialog",
            )
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
            self._feature_dialog("Seitenbild", "Kein PDF geladen.")
            return
        idx = self.pdf_view.page_index
        try:
            out = self._render_pdf_page_image_path(idx)
        except Exception as e:
            self._feature_dialog("Seitenbild", str(e))
            return
        from instantlensdoc.ui.feature_dialog import PathOpenDialog

        PathOpenDialog(
            self,
            title=f"Seitenbild Seite {idx + 1}",
            path=out,
            object_name="ildPageImageDialog",
        ).exec()
        self._set_status(f"Seitenbild Seite {idx + 1}: {out}")

    def _insert_all_page_images_to_editor(self):
        if not self.pdf_view.pdf_path:
            self._feature_dialog("Seitenbild", "Kein PDF geladen.")
            return
        n_pages = self.pdf_view.page_count
        if n_pages < 1:
            self._feature_dialog("Seitenbilder", "PDF hat keine Seiten.")
            return
        paths: list[Path] = []
        try:
            for i in range(n_pages):
                paths.append(self._render_pdf_page_image_path(i))
        except Exception as e:
            self._feature_dialog("Seitenbilder", str(e))
            return
        from instantlensdoc.ui.feature_dialog import PathOpenDialog

        PathOpenDialog(
            self,
            title=f"{len(paths)} Seitenbild(er)",
            path=paths[0].parent if paths else self.pdf_view.pdf_path,
            object_name="ildPageImagesDialog",
        ).exec()
        self._set_status(f"{len(paths)} Seitenbild(er) gespeichert")

    def _extract_page_text_to_editor(self):
        if not self.pdf_view.pdf_path:
            self._feature_dialog("Text extrahieren", "Kein PDF geladen.")
            return
        pdf_path = self.pdf_view.pdf_path
        page_index = int(self.pdf_view.page_index or 0)
        password = self.pdf_view.password
        text = ""
        try:
            from ild_pdf import extract_page_plain_text

            text = extract_page_plain_text(
                pdf_path,
                page_index,
                password=password,
            )
        except Exception as e:
            self._feature_dialog("Text extrahieren", str(e))
            return
        from instantlensdoc.ui.feature_dialog import DetachedDocumentDialog

        DetachedDocumentDialog(
            self,
            path=str(pdf_path),
            body=text or "(kein Text auf dieser Seite)",
        ).exec()
        self._set_status(
            f"Seite {page_index + 1}: Text → Vorschau ({len(text.split()) if (text or '').strip() else 0} Wörter)"
        )

    def _extract_all_text_to_editor(self):
        if not self.pdf_view.pdf_path:
            self._feature_dialog("Text extrahieren", "Kein PDF geladen.")
            return
        from PySide6.QtWidgets import QApplication, QProgressDialog

        from ild_pdf import extract_all_plain_text
        from ild_pdf.limits import TEXT_EXTRACT_ALL_WARN_PAGES

        n = int(self.pdf_view.page_count or 0)
        if n < 1:
            self._feature_dialog("Text extrahieren", "PDF hat keine Seiten.")
            return
        # Große PDFs: Bestätigung — Default nur aktuelle Seite — 2.6.37
        if n >= int(TEXT_EXTRACT_ALL_WARN_PAGES):
            r = QMessageBox.question(
                self,
                "Großes PDF — Text extrahieren",
                f"Dieses PDF hat {n} Seiten.\n\n"
                "Alle Seiten extrahieren kann lange dauern und viel Speicher brauchen.\n\n"
                "Ja = alle Seiten\n"
                "Nein = nur aktuelle Seite\n"
                "Abbrechen = nichts",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.No,
            )
            if r == QMessageBox.Cancel:
                return
            if r == QMessageBox.No:
                self._extract_page_text_to_editor()
                return

        prog = QProgressDialog(
            f"Text wird extrahiert ({n} Seite(n))…", "Abbrechen", 0, 0, self
        )
        prog.setWindowTitle("Text extrahieren")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(150)
        prog.show()
        QApplication.processEvents()
        try:
            text = extract_all_plain_text(
                self.pdf_view.pdf_path,
                password=self.pdf_view.password,
                page_headers=True,
                cancel_check=lambda: bool(prog.wasCanceled()),
            )
        except Exception as e:
            prog.close()
            self._feature_dialog("Text extrahieren", str(e))
            return
        canceled = bool(prog.wasCanceled())
        prog.close()
        if canceled:
            self._feature_dialog("Text extrahieren", "Text-Extraktion abgebrochen.")
            return
        pdf_path = self.pdf_view.pdf_path
        from instantlensdoc.ui.feature_dialog import DetachedDocumentDialog

        DetachedDocumentDialog(
            self,
            path=str(pdf_path),
            body=text or "(kein Text im Dokument)",
        ).exec()
        words = len(text.split()) if (text or "").strip() else 0
        self._set_status(
            f"Gesamter PDF-Text ({self.pdf_view.page_count} Seite(n)) → Vorschau ({words} Wörter)"
        )

    def _on_pdf_undo_state(self, can_u: bool, tu: str, can_r: bool, tr: str) -> None:
        if getattr(self, "stack", None) is None:
            return
        if self.stack.currentWidget() is not self.pdf_view:
            return
        self._apply_undo_redo_ui(can_u, tu, can_r, tr)

    def _sync_undo_redo_ui(self) -> None:
        if getattr(self, "stack", None) is None:
            return
        if self.stack.currentWidget() is self.pdf_view:
            try:
                can_u, tu, can_r, tr = self.pdf_view.undo_ui_state()
            except Exception:
                can_u, tu, can_r, tr = True, "", True, ""
            self._apply_undo_redo_ui(can_u, tu, can_r, tr)
            return
        try:
            in_editor = self.stack.currentWidget() is self.editor_pane
        except Exception:
            in_editor = False
        if in_editor:
            doc = self.editor.document()
            can_u = bool(doc.isUndoAvailable())
            can_r = bool(doc.isRedoAvailable())
            self._apply_undo_redo_ui(can_u, "", can_r, "")
            return
        self._apply_undo_redo_ui(True, "", True, "")

    def _apply_undo_redo_ui(self, can_u: bool, tu: str, can_r: bool, tr: str) -> None:
        u_tip = f"Rückgängig: {tu}" if tu else "Rückgängig (Ctrl+Z)"
        r_tip = f"Wiederholen: {tr}" if tr else "Wiederholen (Ctrl+Y / Ctrl+Shift+Z)"
        seen: set[int] = set()
        for act, en, tip in (
            (getattr(self, "_edit_undo_action", None), can_u, u_tip),
            (getattr(self, "_edit_redo_action", None), can_r, r_tip),
            (getattr(self, "_undo_action", None), can_u, u_tip),
            (getattr(self, "_redo_action", None), can_r, r_tip),
        ):
            if act is None:
                continue
            ident = id(act)
            if ident in seen:
                continue
            seen.add(ident)
            try:
                act.setEnabled(bool(en))
                act.setToolTip(tip)
            except Exception:
                pass
        rb = getattr(self, "ribbon_bar", None)
        if rb is None:
            return
        if hasattr(rb, "set_action_enabled"):
            rb.set_action_enabled("undo", bool(can_u))
            rb.set_action_enabled("redo", bool(can_r))
        elif hasattr(rb, "set_enabled"):
            rb.set_enabled("undo", bool(can_u))
            rb.set_enabled("redo", bool(can_r))
        if hasattr(rb, "set_action_tooltip"):
            rb.set_action_tooltip("undo", u_tip)
            rb.set_action_tooltip("redo", r_tip)

    def _undo(self):
        if self.stack.currentWidget() is self.pdf_view:
            # Sticky Clear bei Ann.-Undo (zusätzlich Seite/Dokument) — 1.1.9
            self.pdf_view.undo_annotation()
        else:
            self.editor.undo()

    def _redo(self):
        if self.stack.currentWidget() is self.pdf_view:
            # Sticky Clear bei Ann.-Redo (zusätzlich Seite/Dokument) — 1.1.9
            self.pdf_view.redo_annotation()
            self._last_tag_rename = None
        else:
            self.editor.redo()

    def _sync_undo_redo_enabled(self) -> None:
        """Menü- und Ribbon-Pfeile an Editor- bzw. PDF-Undo-Stack koppeln — 2.6.54."""
        self._sync_undo_redo_ui()

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
            pv = self.pdf_view
            if hasattr(pv, "set_scale"):
                base = getattr(pv, "_pending_scale", None)
                if base is None:
                    base = getattr(pv, "scale", 1.0) or 1.0
                pv.set_scale(float(base) + 0.25, immediate=True)
            else:
                pv.zoom_in()
            self._set_status(f"Zoom {int(round(float(getattr(pv, 'scale', 1) or 1) * 100))}%")
        else:
            self._feature_dialog("Vergrößern", "Zoom gilt für die PDF-Ansicht.")

    def _zoom_out(self):
        if self.stack.currentWidget() is self.pdf_view:
            pv = self.pdf_view
            if hasattr(pv, "set_scale"):
                base = getattr(pv, "_pending_scale", None)
                if base is None:
                    base = getattr(pv, "scale", 1.0) or 1.0
                pv.set_scale(max(0.25, float(base) - 0.25), immediate=True)
            else:
                pv.zoom_out()
            self._set_status(f"Zoom {int(round(float(getattr(pv, 'scale', 1) or 1) * 100))}%")
        else:
            self._feature_dialog("Verkleinern", "Zoom gilt für die PDF-Ansicht.")

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
                # Ctrl+P: aktuelle Seite; gesamtes Dokument über PDF → Dokument drucken…
                self.pdf_view.print_current_page()
                return
            if self.stack.currentWidget() is self.editor_pane:
                from PySide6.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter

                printer = QPrinter(QPrinter.HighResolution)
                printer.setDocName(self.doc.display_name if self.doc else "InstantLens Doc")
                ctx = self._field_resolve_context()

                def _paint(p) -> None:
                    self.editor.print_with_field_tokens(p, ctx)

                show_preview = True
                try:
                    from instantlensdoc.core.app_settings import get_print_preview

                    show_preview = bool(get_print_preview())
                except Exception:
                    show_preview = True
                if show_preview:
                    try:
                        preview = QPrintPreviewDialog(printer, self)
                        preview.setWindowTitle("Druckvorschau")
                        preview.paintRequested.connect(_paint)
                        preview.exec()
                        self._set_status("Editor-Druckvorschau")
                        return
                    except Exception:
                        pass
                dlg = QPrintDialog(printer, self)
                dlg.setWindowTitle("Editor drucken")
                if dlg.exec() == QPrintDialog.Accepted:
                    _paint(printer)
                    self._set_status("Editor gedruckt")
                return
            QMessageBox.information(
                self,
                "Drucken",
                "Drucken ist für Texteditor und PDF (Seite / Dokument) verfügbar.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Drucken", f"Druck fehlgeschlagen:\n{e}")

    def _on_search_export(self, fmt: str = "csv"):
        """Trefferliste der Sidebar als CSV oder JSON exportieren."""
        kind = str(fmt or "csv").strip().casefold()
        if kind not in ("csv", "json"):
            kind = "csv"
        hits = self.sidebar.search_hit_records()
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
            dest = fulltext_mod.export_search_hits_json(path, hits or [], query=query)
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

    def _on_search_annotate_page(self):
        """Kompatibilität: aktuelle Seite — 0.9.6."""
        self._on_search_annotate_hits(False)

    def _on_search_annotate_hits(self, all_pages: bool = False):
        """Suchtreffer als Highlight-Annotationen (Seite oder alle, ein Undo) — 0.9.6–0.9.9."""
        from PySide6.QtWidgets import QInputDialog

        if not self.pdf_view.pdf_path or not self.pdf_view.store:
            self._feature_dialog(
                "Treffer markieren",
                "Bitte zuerst ein PDF öffnen, dann suchen und Treffer als Highlight setzen.",
                object_name="ildSearchHighlightDialog",
            )
            return
        query = self.sidebar.search_text()
        if not query.strip():
            self._feature_dialog(
                "Treffer markieren",
                "Kein Suchbegriff. Zuerst suchen (Ctrl+F), dann Treffer als Highlight setzen.",
                object_name="ildSearchHighlightDialog",
            )
            return
        # Optionaler Tag: Combobox mit zuletzt genutzten Tags — 0.9.8/0.9.9
        recent = recent_tags_mod.load_recent_tags()
        items = [""] + list(recent)
        tag_text, tag_ok = QInputDialog.getItem(
            self,
            "Highlight-Tag",
            "Optionaler Tag für neue Highlights (leer = ohne Tag):",
            items,
            0,
            True,
        )
        if not tag_ok:
            self._set_status("Highlight-Batch abgebrochen")
            return
        tag = (tag_text or "").strip()
        case = getattr(self.sidebar, "search_case_sensitive", lambda: False)()
        whole = getattr(self.sidebar, "search_whole_word", lambda: False)()
        regex = getattr(self.sidebar, "search_regex_enabled", lambda: False)()
        try:
            n = self.pdf_view.annotate_search_hits(
                query,
                all_pages=bool(all_pages),
                case_sensitive=case,
                whole_word=whole,
                regex=regex,
                tag=tag or None,
            )
        except Exception as e:
            self._set_status(f"Highlight-Batch fehlgeschlagen: {e}")
            QMessageBox.warning(self, "Treffer markieren", str(e))
            return
        if n <= 0:
            self._feature_dialog(
                "Treffer markieren",
                "Keine Treffer im Dokument."
                if all_pages
                else "Keine Treffer auf der aktuellen Seite.",
                object_name="ildSearchHighlightDialog",
            )
            return
        if tag:
            try:
                recent_tags_mod.add_recent_tag(tag)
            except Exception:
                pass
        if self.doc and self.doc.path:
            self._mark_unsaved(self.doc.path, True)
        self._refresh_pdf_marks()
        tag_note = f", Tag „{tag}“" if tag else ""
        if all_pages:
            self._set_status(f"{n} Highlight(s) aus Suche (alle Seiten{tag_note})")
        else:
            self._set_status(
                f"{n} Highlight(s) aus Suche auf Seite {self.pdf_view.page_index + 1}{tag_note}"
            )

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
            try:
                from instantlensdoc.core.app_settings import (
                    get_search_snippet_context_chars,
                )

                snip_ctx = get_search_snippet_context_chars()
            except Exception:
                snip_ctx = 40
            # Klickbare Trefferliste: Seite + Snippet je Texttreffer (0.9.1)
            # Case-sensitive / Whole-word (0.9.2) / Regex (0.9.3)
            from ild_pdf.overlay import SearchPatternError

            case_sens = bool(
                getattr(self.sidebar, "search_case_sensitive", lambda: False)()
            )
            whole_word = bool(
                getattr(self.sidebar, "search_whole_word", lambda: False)()
            )
            use_regex = bool(
                getattr(self.sidebar, "search_regex_enabled", lambda: False)()
            )
            text_hits: list[tuple[int, int, str]] = []
            n_page = 0
            try:
                if pdf_path and hasattr(self.pdf_view, "collect_search_hits"):
                    text_hits = self.pdf_view.collect_search_hits(
                        query,
                        max_hits=100,
                        snippet_chars=snip_ctx,
                        case_sensitive=case_sens,
                        whole_word=whole_word,
                        regex=use_regex,
                    )
                # Aktuelle Seite: Texttreffer highlighten
                n_page = self.pdf_view.highlight_search(
                    query,
                    case_sensitive=case_sens,
                    whole_word=whole_word,
                    regex=use_regex,
                )
            except SearchPatternError as e:
                self.pdf_view.clear_search_highlights()
                self.sidebar.clear_search_hit_status()
                self.sidebar.set_marks([f"Regex-Fehler: {e}"])
                self._set_status(f"Regex-Fehler: {e}")
                return
            if text_hits or hits or n_page:
                lines = []
                payloads = []
                # text_hits: (Seite, Zeichen-Offset, Snippet) — CSV-Export 0.9.4
                for page_idx, offset, snip in text_hits:
                    lines.append(
                        fulltext_mod.format_hit_line(
                            Path(pdf_path).name if pdf_path else "PDF",
                            page=page_idx,
                            line=None,
                            snippet=snip,
                            kind="pdf",
                            query=query,
                        )
                    )
                    payloads.append((str(pdf_path), page_idx, query, offset))
                for h in hits:
                    ann_snip = fulltext_mod._snippet_around(
                        f"{h.type.value} {h.text}",
                        query,
                        context_chars=max(20, snip_ctx - 4),
                        width=80,
                    )
                    lines.append(f"S.{h.page + 1} Ann.: {ann_snip}")
                    payloads.append(h)
                if not lines and n_page:
                    lines.append(
                        f"Seite {self.pdf_view.page_index + 1}: "
                        f"{n_page} Texttreffer (hervorgehoben)"
                    )
                    payloads.append(("__search__", self.pdf_view.page_index, query, 0))
                self.sidebar.set_marks(lines, payloads)
                total_nav = len(
                    [
                        p
                        for p in payloads
                        if isinstance(p, tuple)
                        and len(p) >= 2
                        and p[0] not in (None, "", "__search__")
                    ]
                )
                if total_nav:
                    self.sidebar.set_search_hit_status(1 if n_page else 0, total_nav)
                elif n_page:
                    self.sidebar.set_search_hit_status(1, n_page)
                self._set_status(
                    f"{len(text_hits)} Texttreffer · {len(hits)} Ann. · "
                    f"Seite {self.pdf_view.page_index + 1}: {n_page} hervorgehoben — "
                    "Klick in Trefferliste springt"
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
        hit_i = payload[3] if len(payload) >= 4 else None
        self._on_fulltext_hit(str(payload[0]), payload[1], query=q, hit_index=hit_i)
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
            if not (q or "").strip():
                self._find_replace()
                return
            if self.editor.find_next(q or None):
                self._set_status("Nächster Treffer")
            else:
                self._set_status("Keine weiteren Treffer")
            return
        if self.stack.currentWidget() is self.pdf_view:
            if not q:
                self._open_multi_doc_search()
                return
            from ild_pdf.overlay import SearchPatternError

            case_sens = bool(
                getattr(self.sidebar, "search_case_sensitive", lambda: False)()
            )
            whole_word = bool(
                getattr(self.sidebar, "search_whole_word", lambda: False)()
            )
            use_regex = bool(
                getattr(self.sidebar, "search_regex_enabled", lambda: False)()
            )
            self.pdf_view.set_search_options(
                case_sensitive=case_sens, whole_word=whole_word, regex=use_regex
            )
            if self.pdf_view._search_query != q:
                try:
                    n = self.pdf_view.highlight_search(
                        q,
                        case_sensitive=case_sens,
                        whole_word=whole_word,
                        regex=use_regex,
                    )
                except SearchPatternError as e:
                    self.sidebar.clear_search_hit_status()
                    self._set_status(f"Regex-Fehler: {e}")
                    return
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
            if not (q or "").strip():
                self._find_replace()
                return
            if self.editor.find_prev(q or None):
                self._set_status("Vorheriger Treffer")
            else:
                self._set_status("Keine weiteren Treffer")
            return
        if self.stack.currentWidget() is self.pdf_view:
            if not q:
                self._open_multi_doc_search()
                return
            from ild_pdf.overlay import SearchPatternError

            case_sens = bool(
                getattr(self.sidebar, "search_case_sensitive", lambda: False)()
            )
            whole_word = bool(
                getattr(self.sidebar, "search_whole_word", lambda: False)()
            )
            use_regex = bool(
                getattr(self.sidebar, "search_regex_enabled", lambda: False)()
            )
            self.pdf_view.set_search_options(
                case_sensitive=case_sens, whole_word=whole_word, regex=use_regex
            )
            if self.pdf_view._search_query != q:
                try:
                    n = self.pdf_view.highlight_search(
                        q,
                        case_sensitive=case_sens,
                        whole_word=whole_word,
                        regex=use_regex,
                    )
                except SearchPatternError as e:
                    self.sidebar.clear_search_hit_status()
                    self._set_status(f"Regex-Fehler: {e}")
                    return
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

    def _sync_editor_toolbar_for_stack(self) -> None:
        """Text/DOCX: Editor-Toolbar sichtbar; PDF behält eigene Ann.-Leiste — 2.6.44."""
        pane = getattr(self, "editor_pane", None)
        if pane is None or not hasattr(pane, "set_toolbar_visible"):
            return
        on_editor = self.stack.currentWidget() is pane
        # Toolbar liegt im EditorPane → bei PDF-Tab ohnehin unsichtbar; explizit syncen
        pane.set_toolbar_visible(True)
        if on_editor:
            try:
                pane.set_active_tool(pane.active_tool() or "select")
            except Exception:
                try:
                    pane.set_active_tool("select")
                except Exception:
                    pass
        # PDF-Toolbar-Gruppen aus Settings wiederherstellen (auch nach Tab-Wechsel)
        try:
            if hasattr(self, "pdf_view") and hasattr(self.pdf_view, "apply_toolbar_groups"):
                self.pdf_view.apply_toolbar_groups()
        except Exception:
            pass

    def _on_editor_toolbar_action(self, action_id: str) -> None:
        """Word-Suite-Bearbeitungsleiste → Editor-Aktionen — 2.6.44.

        Bei PDF-Tab: kein Stack-Wechsel, kein Geschwister-DOCX, kein neues Text-Tab.
        """
        aid = str(action_id or "").strip().lower()
        if aid == "mark" and self.stack.currentWidget() is self.pdf_view:
            self._mark_selection()
            return
        if not self._guard_editor_action("Textformat"):
            return
        if aid == "select":
            pane = getattr(self, "editor_pane", None)
            if pane is not None and hasattr(pane, "set_active_tool"):
                pane.set_active_tool("select")
            try:
                self.editor.setFocus(Qt.OtherFocusReason)
            except Exception:
                pass
            self._set_status("Werkzeug: Auswahl — Text markieren, dann Markierungen/Format")
            return
        if aid == "edit":
            pane = getattr(self, "editor_pane", None)
            if pane is not None and hasattr(pane, "set_active_tool"):
                pane.set_active_tool("edit")
            try:
                self.editor.setReadOnly(False)
                self.editor.setFocus(Qt.OtherFocusReason)
            except Exception:
                pass
            self._set_status("Werkzeug: Text bearbeiten — Tippen im Dokument")
            return
        if aid == "mark":
            self._mark_selection()
            return
        if aid == "underline":
            self._toggle_underline()
            return
        if aid == "bold":
            self._toggle_bold()
            return
        if aid == "italic":
            self._toggle_italic()
            return
        if aid == "strike":
            self._toggle_strike()
            return
        if aid == "clear_format":
            self._clear_formatting()
            return
        if aid == "clear_marks":
            self._clear_editor_marks()
            return
        if aid == "find":
            self._find_replace()
            return
        extra = {
            "align_left": lambda: self._set_paragraph_alignment("left"),
            "align_center": lambda: self._set_paragraph_alignment("center"),
            "align_right": lambda: self._set_paragraph_alignment("right"),
            "align_justify": lambda: self._set_paragraph_alignment("justify"),
            "bullet_list": lambda: self._toggle_list(ordered=False),
            "numbered_list": lambda: self._toggle_list(ordered=True),
            "paragraph": self._paragraph_format_dialog,
            "page_layout": self._show_page_layout_dialog,
            "page_size_a4": lambda: self._apply_page_size_preset("A4"),
            "page_size_letter": lambda: self._apply_page_size_preset("Letter"),
            "page_size_legal": lambda: self._apply_page_size_preset("Legal"),
            "page_size_custom": self._show_page_layout_dialog,
            "header_footer": self._header_footer_dialog,
            "field_token": self._field_token_dialog,
        }
        fn = extra.get(aid)
        if callable(fn):
            fn()

    def _mark_selection(self):
        """Textmarker im Editor (Text/DOCX/HTML) — PDF nutzt das Highlight-Werkzeug — 2.6.52."""
        if self.stack.currentWidget() is self.pdf_view:
            # PDF: Highlight-Werkzeug der PDF-Leiste aktivieren statt Dialog
            try:
                self.pdf_view.set_tool_from_id("highlight")
                self._set_status(
                    "PDF: Highlight-Werkzeug aktiv — Bereich auf der Seite aufziehen"
                )
                return
            except Exception:
                pass
        if self.stack.currentWidget() is not self.editor_pane:
            self._feature_dialog(
                "Markieren",
                "Markieren funktioniert im Texteditor.",
                object_name="ildMarkDialog",
            )
            return
        was_marked = False
        try:
            was_marked = bool(self.editor.selection_highlighted())
        except Exception:
            was_marked = False
        if not self.editor.highlight_selection():
            return
        self._sync_editor_rich_meta()
        if was_marked:
            self._set_status("Markierung entfernt")
            return
        if self.editor.textCursor().hasSelection():
            snip = self.editor.selected_snippet() or "Auswahl"
            label = f"Markierung: {snip}"
            self._editor_marks.append(label)
            self.sidebar.append_mark(label)
            self._set_status("Auswahl markiert (Textmarker, wird mit DOCX/HTML gespeichert)")
        else:
            self._set_status("Dokument markiert (Textmarker)")

    def _clear_editor_marks(self):
        if self.stack.currentWidget() is self.pdf_view:
            self._refresh_pdf_marks()
            self._set_status("Markierungen gelöscht")
            return
        if not self._guard_editor_action("Markierungen"):
            return
        self.editor.clear_extra_selections()
        removed = 0
        try:
            removed = int(self.editor.clear_highlight_formats())
        except Exception:
            removed = 0
        if removed:
            self._sync_editor_rich_meta()
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
        self._refresh_redactions_list()
        self._refresh_links_list()
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
            if payload[0] in (None, "", "__search__"):
                q = payload[2] if len(payload) >= 3 else self.sidebar.search_text()
                hit_i = int(payload[3]) if len(payload) >= 4 else 0
                page = payload[1]
                if page is not None and self.stack.currentWidget() is self.pdf_view:
                    if q:
                        self.pdf_view._search_query = q
                        self.pdf_view._goto_search_page(int(page), hit_index=hit_i)
                    else:
                        self.pdf_view.goto_page(int(page))
                    self._set_status(f"Treffer Seite {int(page) + 1}")
                return
            q = payload[2] if len(payload) >= 3 else self.sidebar.search_text()
            hit_i = payload[3] if len(payload) >= 4 else None
            self._on_fulltext_hit(str(payload[0]), payload[1], query=q, hit_index=hit_i)
            return
        if payload is not None and hasattr(payload, "page"):
            self.stack.setCurrentWidget(self.pdf_view)
            self.pdf_view.focus_annotation(payload)
            self._set_status(f"Annotation Seite {payload.page + 1}")

    def _on_fulltext_hit(
        self,
        path: str,
        page,
        query: str | None = None,
        hit_index: int | None = None,
    ):
        if path in (None, "", "__search__"):
            return
        self.open_path(path)
        q = (query or self.sidebar.search_text() or "").strip()
        if page is not None and self.stack.currentWidget() is self.pdf_view:
            n = 0
            if q:
                from ild_pdf.overlay import SearchPatternError

                case_sens = bool(
                    getattr(self.sidebar, "search_case_sensitive", lambda: False)()
                )
                whole_word = bool(
                    getattr(self.sidebar, "search_whole_word", lambda: False)()
                )
                use_regex = bool(
                    getattr(self.sidebar, "search_regex_enabled", lambda: False)()
                )
                self.pdf_view.set_search_options(
                    case_sensitive=case_sens,
                    whole_word=whole_word,
                    regex=use_regex,
                )
                self.pdf_view._search_query = q
                try:
                    if hit_index is not None:
                        ok = self.pdf_view._goto_search_page(
                            int(page), hit_index=int(hit_index)
                        )
                        n = self.pdf_view.search_hit_count() if ok else 0
                    else:
                        self.pdf_view.goto_page(int(page))
                        n = self.pdf_view.highlight_search(
                            q,
                            case_sensitive=case_sens,
                            whole_word=whole_word,
                            regex=use_regex,
                        )
                except SearchPatternError as e:
                    self._set_status(f"Regex-Fehler: {e}")
                    return
            else:
                self.pdf_view.goto_page(int(page))
            if n:
                hi = (
                    int(hit_index) + 1
                    if hit_index is not None
                    else self.pdf_view.search_active_index() + 1
                )
                self._set_status(
                    f"Treffer: {Path(path).name} Seite {int(page) + 1} · "
                    f"{hi}/{n} hervorgehoben"
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
        if not self._require_pdf("Lesezeichen hinzufügen"):
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
        if not self._require_pdf("Lesezeichen löschen"):
            return
        path = self.sidebar.selected_outline_path()
        if path is None:
            self._feature_dialog(
                "Lesezeichen löschen",
                "Kein Lesezeichen ausgewählt. Zuerst ein Lesezeichen in der Dokumentstruktur markieren.",
            )
            return
        from ild_pdf.outline import delete_outline_item

        try:
            delete_outline_item(self.pdf_view.pdf_path, path)
            self._refresh_outline(self.pdf_view.pdf_path)
            self._set_status("Lesezeichen gelöscht")
        except Exception as e:
            QMessageBox.warning(self, "Lesezeichen löschen", str(e))

    def _refresh_outline(self, path: str | Path):
        """PDF-Lesezeichen + Text-Überschriften → Dokumentstruktur — 2.6.26."""
        self._refresh_document_outline(pdf_path=path)

    def _refresh_document_outline(self, pdf_path: str | Path | None = None) -> None:
        """Dokumentstruktur-Pane neu aufbauen (Überschriften/Lesezeichen/Favoriten)."""
        from instantlensdoc.core.doc_outline import build_document_outline

        text = ""
        try:
            if self.stack.currentWidget() is self.editor_pane:
                text = self.editor.toPlainText()
            elif self.doc and getattr(self.doc, "text", None):
                text = self.doc.text or ""
        except Exception:
            text = ""
        path = pdf_path
        if path is None:
            path = getattr(self.pdf_view, "pdf_path", None) if hasattr(self, "pdf_view") else None
            if path is None and self.doc and getattr(self.doc, "kind", None):
                from instantlensdoc.core.documents import DocKind as _DK

                if self.doc.kind == _DK.PDF and self.doc.path:
                    path = self.doc.path
        favs = None
        try:
            # Seitenfavoriten aus Sidebar falls vorhanden
            if hasattr(self.sidebar, "page_favorites"):
                favs = list(self.sidebar.page_favorites() or [])
        except Exception:
            favs = None
        data = build_document_outline(
            text=text or None,
            pdf_path=path,
            favorites=favs,
        )
        sections = data.get("sections") or []
        if hasattr(self.sidebar, "set_document_structure"):
            self.sidebar.set_document_structure(sections=sections)
        else:
            try:
                items = extract_outline(path) if path else []
            except Exception:
                items = []
            self.sidebar.set_outline(items)
        total = int(data.get("total") or 0)
        if total == 0 and hasattr(self, "file_status_label"):
            try:
                self._set_status(
                    "Keine Struktur — Überschriften (#) / Lesezeichen / + hinzufügen"
                )
            except Exception:
                pass
        elif total:
            try:
                c = data.get("counts") or {}
                self._set_status(
                    f"Struktur: {c.get('heading', 0)} Überschr. · "
                    f"{c.get('bookmark', 0)} Lesez. · {c.get('favorite', 0)} Fav."
                )
            except Exception:
                pass

    def _on_outline_line_jump(self, line: int) -> None:
        """Sprung zu Textzeile aus Dokumentstruktur — 2.6.26."""
        if line is None or int(line) < 1:
            self._set_status("Struktur: keine Zeile")
            return
        try:
            self.stack.setCurrentWidget(self.editor_pane)
            block = self.editor.document().findBlockByNumber(int(line) - 1)
            if block.isValid():
                cursor = self.editor.textCursor()
                cursor.setPosition(block.position())
                self.editor.setTextCursor(cursor)
                self.editor.setFocus()
                self._set_status(f"Struktur → Zeile {int(line)}")
            else:
                self._set_status(f"Zeile {int(line)} nicht gefunden")
        except Exception as e:
            self._set_status(f"Struktur-Sprung: {e}")

    def _show_extrude3d_dialog(self) -> None:
        if getattr(self, "dtp_pane", None) is not None:
            try:
                self._enter_layout_mode()
                self.dtp_pane.apply_extrude()
                self._set_status("3D-Extrusion auf DTP-Auswahl")
                return
            except Exception:
                pass
        from instantlensdoc.ui.extrude3d_dialog import Extrude3DDialog

        Extrude3DDialog(self).exec()

    def _activate_stylus_tool(self) -> None:
        """Drucksensitiver Stift: DTP-Canvas oder PDF-Freihand — 2.6.54."""
        try:
            if getattr(self, "dtp_pane", None) is not None and (
                self.stack.currentWidget() is self.dtp_pane
                or not getattr(self.pdf_view, "pdf_path", None)
            ):
                self._enter_layout_mode()
                self.dtp_pane._ink_btn.setChecked(True)
                self.dtp_pane.toggle_ink(True)
                from instantlensdoc.core.stylus import stylus_info

                self._set_status(stylus_info().get("message") or "Stift (DTP)")
                return
            if hasattr(self, "pdf_view") and hasattr(self.pdf_view, "set_tool"):
                from ild_pdf.annotate import AnnotationType

                self.stack.setCurrentWidget(self.pdf_view)
                self.pdf_view.set_tool(AnnotationType.INK)
            from instantlensdoc.core.stylus import stylus_info

            info = stylus_info()
            self._set_status(info.get("message") or "Stylus aktiv")
        except Exception as e:
            self._set_status(f"Stylus: {e}")

    def _show_hooks_info(self) -> None:
        from instantlensdoc.core.plugin_hooks import list_hooks, write_hook_example
        from instantlensdoc.features.plugins import install_sample_plugin

        try:
            write_hook_example()
        except Exception:
            pass
        try:
            sample = install_sample_plugin()
        except Exception:
            sample = ""
        data = list_hooks()
        events = ", ".join(data.get("known_events") or [])
        from instantlensdoc.ui.feature_dialog import FeatureDialog

        FeatureDialog(
            self,
            title="Script-/Plugin-Hooks",
            body=(
                f"Ordner: {data.get('hooks_dir')}\n"
                f"Geladen: {len(data.get('loaded') or [])}\n"
                f"Events: {events}\n"
                f"Aliase: on_open, on_save, on_scan\n"
                f"Beispiel-Plugin: {sample or '(siehe examples/ild_dtp_sample_plugin.py)'}"
            ),
            object_name="ildHooksDialog",
        ).exec()
        try:
            self._set_status(
                f"Hooks: {data.get('hooks_dir')} · "
                f"{len(data.get('loaded') or [])} geladen · "
                f"{len(data.get('known_events') or [])} Events"
            )
        except Exception:
            pass

    def _enter_layout_mode(self) -> None:
        """Ansicht → Layout-Modus: DTP-Canvas."""
        pane = getattr(self, "dtp_pane", None)
        if pane is None:
            return
        try:
            from instantlensdoc.dtp.model import DtpDocument

            if getattr(self, "layout_doc", None) is not None and self.layout_doc.text_frames:
                pane.set_document(DtpDocument.from_layout_document(self.layout_doc))
            elif pane.doc is None:
                pane.set_document(DtpDocument.sample("A5"))
        except Exception:
            pass
        self.stack.setCurrentWidget(pane)
        self._set_status("Layout-Modus (DTP)")
        try:
            self._sync_editor_only_actions()
            self._sync_menu_enablement()
        except Exception:
            pass

    def _dtp_apply_fill(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.apply_fill(dialog=True)

    def _dtp_apply_stroke(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.apply_stroke(dialog=True)

    def _dtp_apply_font(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.apply_font(dialog=True)

    def _dtp_apply_wrap(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.apply_wrap_mode(dialog=True)

    def _dtp_add_text_frame(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.add_text_frame()

    def _dtp_link_frames(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.link_selected()

    def _dtp_toggle_grid(self) -> None:
        pv = getattr(self, "pdf_view", None)
        if pv is not None and getattr(pv, "pdf_path", None):
            if hasattr(pv, "show_alignment_grid"):
                on = not bool(pv.show_alignment_grid())
            else:
                on = not bool(getattr(pv, "_show_alignment_grid", False))
            self._toggle_alignment_grid(on)
            return
        if self._layout_mode_active():
            self.dtp_pane.toggle_grid()
            return
        self._feature_dialog(
            "Raster",
            "Ausrichtungsraster gilt in der PDF-Ansicht (Ansicht → Ausrichtungsraster).",
        )

    def _dtp_export_pdf_dialog(self) -> None:
        self._enter_layout_mode()
        path, _ = QFileDialog.getSaveFileName(
            self, "DTP als PDF", "", "PDF (*.pdf)"
        )
        if not path:
            return
        out = self.dtp_pane.export_pdf_to(path)
        self._set_status(f"DTP-PDF: {out}")

    def _dtp_text_on_path(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.apply_text_on_path("ellipse")

    def _dtp_text_to_outlines(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.convert_to_outlines()

    def _dtp_clip_mask(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.apply_clip_mask()

    def _dtp_live_fill(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.apply_live_fill()

    def _dtp_glyph_palette(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.show_glyph_palette()

    def _dtp_import_text(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.import_text()

    def _dtp_replace_image(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.replace_image()

    def _dtp_import_graphic(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.import_graphic()

    def _dtp_weld(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.weld_selected()

    def _dtp_symbol(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.symbol_from_selection()

    def _dtp_preflight(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.run_preflight()

    def _dtp_export_pdfx(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.export_pdfx_dialog()

    def _show_ki_assistant(self) -> None:
        from instantlensdoc.features.ki_panel import KiAssistantDialog

        selected = ""
        try:
            if self.stack.currentWidget() is self.editor_pane:
                selected = self.editor.textCursor().selectedText()
                if not selected:
                    selected = self.editor.toPlainText()[:8000]
            elif getattr(self, "dtp_pane", None) is not None:
                frs = self.dtp_pane.scene.selected_frames()
                selected = "\n".join(f.text for f in frs if f.kind == "text")
        except Exception:
            pass
        KiAssistantDialog(self, selected_text=selected).exec()

    def _run_shape_recognition(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.view.recognize_on_finish = True
        self.dtp_pane.recognize_selected_ink()
        self._set_status("Formerkennung (DTP-Tinte)")

    def _show_variable_fonts(self) -> None:
        from instantlensdoc.features.varfont_dialog import VariableFontsDialog
        from instantlensdoc.features.variable_fonts import apply_axes_to_frame

        dlg = VariableFontsDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        fam = dlg.selected_family().split(" [")[0]
        pane = getattr(self, "dtp_pane", None)
        if pane is None:
            return
        self._enter_layout_mode()
        targets = pane.scene.selected_frames()
        if not targets:
            targets = pane.doc.story_frames() or pane.doc.text_frames()
        for fr in targets:
            if fr.kind != "text":
                continue
            fr.font_family = fam
            apply_axes_to_frame(fr, dlg.axes_values)
        pane.scene.rebuild()
        self._set_status(f"Variable Font: {fam}")

    def _apply_envelope_distort(self) -> None:
        self._enter_layout_mode()
        self.dtp_pane.apply_envelope()

    def _show_pades_dialog(self) -> None:
        from instantlensdoc.features.pades_dialog import PadesDialog

        pdf = ""
        try:
            pdf = str(getattr(self.pdf_view, "pdf_path", "") or "")
        except Exception:
            pdf = ""
        PadesDialog(self, pdf_path=pdf).exec()

    def _show_telemetry_settings(self) -> None:
        """Settings öffnen / Telemetrie-Info — 2.6.26."""
        try:
            self._settings()
            return
        except Exception:
            pass
        from instantlensdoc.ui.feature_dialog import FeatureDialog

        FeatureDialog(
            self,
            title="Telemetrie",
            body=(
                "Opt-in unter Extra → Einstellungen. "
                "Keine Datenübertragung in dieser Version."
            ),
            object_name="ildTelemetryDialog",
        ).exec()

    def _refresh_form_fields(self):
        """AcroForm-Feldliste Sidebar (Name/Typ/Wert) — 1.3.0."""
        path = self.pdf_view.pdf_path
        if not path:
            self.sidebar.clear_form_fields()
            return
        try:
            from ild_pdf.acroform import list_form_fields

            fields = list_form_fields(path)
        except Exception as e:
            _log.debug("Form fields: %s", e)
            fields = []
        self.sidebar.set_form_fields(fields)

    def _on_form_field_jump(self, info) -> None:
        """Sprung zur Seite des AcroForm-Feldes."""
        if self.stack.currentWidget() is not self.pdf_view or not self.pdf_view.pdf_path:
            self._set_status("Formularfeld: PDF öffnen")
            return
        page = getattr(info, "page_index", None)
        name = str(getattr(info, "name", "") or "")
        if page is None:
            self._set_status(f"Formularfeld „{name}“ ohne Seiten-Ziel")
            return
        idx = int(page)
        n = int(self.pdf_view.page_count or 0)
        if idx < 0 or idx >= n:
            self._set_status(f"Formularfeld „{name}“: Seite außerhalb")
            return
        self.pdf_view.goto_page(idx)
        self.sidebar.select_thumb(idx)
        self._set_status(f"Formularfeld „{name}“ → Seite {idx + 1}")

    def _on_form_fields_save(self, values) -> None:
        """Textfeld-Werte via pikepdf speichern — nur dirty — 1.3.0/1.3.1."""
        if not self.pdf_view.pdf_path:
            self._set_status("Formularfelder speichern: PDF öffnen")
            return
        if not isinstance(values, dict) or not values:
            self._set_status("Formularfelder: keine Änderungen")
            return
        try:
            from ild_pdf.acroform import set_form_values
            from ild_pdf.render import clear_render_cache

            set_form_values(self.pdf_view.pdf_path, values)
            clear_render_cache(self.pdf_view.pdf_path)
            self.pdf_view.refresh()
            self._refresh_form_fields()
            names = ", ".join(str(k) for k in values.keys())
            self._set_status(f"Formularfeld gespeichert ({len(values)} dirty): {names}")
        except Exception as e:
            QMessageBox.warning(self, "Formularfelder", str(e))

    def _on_form_fields_export_csv(self) -> None:
        """AcroForm CSV: Esc ohne Export; Enter auf OK; Zähler; Default persistiert — 1.3.6."""
        from instantlensdoc.core.app_settings import (
            get_forms_csv_visible_only,
            set_forms_csv_visible_only,
        )
        from instantlensdoc.ui.form_fields_dialog import ask_forms_csv_export_options

        path = self.pdf_view.pdf_path
        if not path:
            self._set_status("Feldliste CSV: PDF öffnen")
            return
        all_fields = []
        if hasattr(self.sidebar, "form_fields_for_export"):
            all_fields = list(self.sidebar.form_fields_for_export() or [])
        if not all_fields:
            try:
                from ild_pdf.acroform import list_form_fields

                all_fields = list_form_fields(path)
            except Exception as e:
                QMessageBox.warning(self, "Feldliste CSV", str(e))
                return
        if not all_fields:
            QMessageBox.information(
                self, "Feldliste CSV", "Keine AcroForm-Felder zum Export."
            )
            return
        visible = all_fields
        if hasattr(self.sidebar, "form_fields_visible"):
            visible = list(self.sidebar.form_fields_visible() or [])
        n_vis = len(visible)
        n_all = len(all_fields)

        choice = ask_forms_csv_export_options(
            self,
            n_all=n_all,
            n_vis=n_vis,
            prefer_visible=bool(get_forms_csv_visible_only()),
            checkbox_enabled=True,
        )
        if choice is None:
            return
        set_forms_csv_visible_only(choice)
        fields = visible if choice else all_fields
        if not fields:
            QMessageBox.information(
                self, "Feldliste CSV", "Keine Felder zum Export."
            )
            return
        from pathlib import Path as _Path

        from instantlensdoc.ui.file_dialogs import confirm_overwrite_export

        start_dir = dialog_start_dir(get_last_export_dir() or _Path(path).parent)
        start = str(_Path(start_dir) / f"{_Path(path).stem}_fields.csv")
        dest, _ = QFileDialog.getSaveFileName(
            self, "Feldliste als CSV", start, "CSV (*.csv)"
        )
        if not dest:
            return
        if not confirm_overwrite_export(dest, self):
            return
        try:
            from ild_pdf.acroform import export_form_fields_csv

            out = export_form_fields_csv(
                path, fields, out_path=dest, utf8_bom=True
            )
            set_last_export_dir(out.parent)
            filt = " (gefiltert)" if cb.isChecked() and filter_active else ""
            self._set_status(
                f"Feldliste CSV{filt}: {len(fields)} Feld(er) → {out}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Feldliste CSV", str(e))

    def _refresh_redactions_list(self) -> None:
        """Schwärzungs-Liste Sidebar — 1.3.1."""
        if not hasattr(self.sidebar, "set_redactions"):
            return
        store = getattr(self.pdf_view, "store", None)
        if store is None:
            self.sidebar.clear_redactions()
            return
        try:
            from ild_pdf.annotate import AnnotationType

            reds = [
                a
                for a in (store.annotations or [])
                if getattr(a, "type", None) == AnnotationType.REDACTION
            ]
        except Exception:
            reds = []
        self.sidebar.set_redactions(reds)

    def _refresh_links_list(self) -> None:
        """URL-Link-Liste Sidebar — 2.3.1."""
        if not hasattr(self.sidebar, "set_links"):
            return
        store = getattr(self.pdf_view, "store", None)
        if store is None:
            self.sidebar.clear_links()
            return
        try:
            from ild_pdf.annotate import AnnotationType

            links = [
                a
                for a in (store.annotations or [])
                if getattr(a, "type", None) == AnnotationType.LINK
            ]
        except Exception:
            links = []
        self.sidebar.set_links(links)

    def _on_link_activated(self, ann) -> None:
        """Doppelklick Sidebar springt zur Seite — 2.3.1/2.3.2."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if self.pdf_view.focus_annotation(ann):
            if ann is not None and hasattr(ann, "page"):
                self._set_status(f"Link → Seite {int(ann.page) + 1}")
            return
        if ann is not None and hasattr(ann, "page"):
            self.pdf_view.goto_page(int(ann.page))
            self.sidebar.select_thumb(int(ann.page))
            self._set_status(f"Link → Seite {int(ann.page) + 1}")

    def _export_links_txt(self) -> None:
        """
        Gefilterte URL-Liste als TXT: Live-Vorschau Dateiname,
        Quick-Insert {stem}/{date}, Reset Default, Zielordner, UTF-8-BOM — 2.3.4.
        """
        if not hasattr(self.sidebar, "filtered_link_uris"):
            return
        uris = self.sidebar.filtered_link_uris()
        if not uris:
            QMessageBox.information(
                self, "Links exportieren", "Keine URLs zum Export (Filter prüfen)."
            )
            return
        from ild_pdf.links import export_links_txt
        from instantlensdoc.core.app_settings import (
            DEFAULT_LINKS_TXT_FILENAME_TEMPLATE,
            dialog_start_dir,
            find_invalid_links_txt_placeholders,
            format_links_txt_filename,
            get_last_links_txt_dir,
            get_links_txt_filename_template,
            get_links_txt_utf8_bom,
            highlight_links_txt_template_html,
            set_last_links_txt_dir,
            set_links_txt_filename_template,
            set_links_txt_utf8_bom,
        )
        from instantlensdoc.ui.template_reset import (
            EscapeDiscardEditFilter,
            reset_line_edit_template,
        )

        stem = "links"
        if self.pdf_view.pdf_path:
            stem = Path(self.pdf_view.pdf_path).stem or "links"

        opts = QDialog(self)
        opts.setWindowTitle("URL-Liste als TXT")
        ol = QVBoxLayout(opts)
        ol.addWidget(
            QLabel(
                f"{len(uris)} URL(s) · Template "
                f"{DEFAULT_LINKS_TXT_FILENAME_TEMPLATE} — 2.3.5"
            )
        )
        chk_bom = QCheckBox("UTF-8 BOM (Excel)")
        chk_bom.setObjectName("linksTxtBom")
        chk_bom.setChecked(get_links_txt_utf8_bom())
        chk_bom.setToolTip("TXT mit UTF-8-BOM schreiben (Excel-freundlich) — 2.3.4")
        ol.addWidget(chk_bom)

        tpl_row = QHBoxLayout()
        tpl_row.addWidget(QLabel("Dateiname:"))
        tpl_edit = QLineEdit(get_links_txt_filename_template())
        tpl_edit.setObjectName("linksTxtTemplate")
        tpl_edit.setPlaceholderText(DEFAULT_LINKS_TXT_FILENAME_TEMPLATE)
        tpl_edit.setToolTip(
            "Live-Dateiname-Template; Platzhalter {stem}/{date}; "
            "Quick-Insert; Reset Default (Bestätigung nur bei Abweichung · "
            "Fokus+Selektion); Esc im Feld verwirft Edit — 2.3.5"
        )
        tpl_row.addWidget(tpl_edit, 1)
        preview = QLabel("")
        preview.setObjectName("linksTxtPreview")
        preview.setTextFormat(Qt.RichText)
        preview.setWordWrap(True)
        preview.setToolTip(
            "Live-Vorschau Dateiname; ungültige Platzhalter rot — 2.3.4"
        )
        preview.setAccessibleName("Links-TXT Live-Vorschau Dateiname")

        def _update_preview() -> None:
            import html as _html

            tpl = tpl_edit.text().strip() or DEFAULT_LINKS_TXT_FILENAME_TEMPLATE
            name = format_links_txt_filename(stem, template=tpl)
            html = highlight_links_txt_template_html(tpl)
            invalid = find_invalid_links_txt_placeholders(tpl)
            note = f" → <code>{_html.escape(name)}</code>"
            if invalid:
                note += f" · ungültig: {', '.join(invalid)}"
            preview.setText(f"TXT: {html}{note}")
            preview.setAccessibleName(f"Links-TXT Live-Vorschau {name}")

        tpl_esc = EscapeDiscardEditFilter(
            tpl_edit, on_discard=_update_preview, parent=opts
        )

        for token in ("{stem}", "{date}"):
            btn = QPushButton(token)
            btn.setObjectName(
                "linksTxtInsertStem" if token == "{stem}" else "linksTxtInsertDate"
            )
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.TabFocus)
            btn.setToolTip(f"Platzhalter {token} an Cursor einfügen — 2.3.4")

            def _insert(t=token) -> None:
                tpl_edit.insert(t)
                tpl_edit.setFocus()
                _update_preview()
                tpl_esc.commit()

            btn.clicked.connect(_insert)
            tpl_row.addWidget(btn)

        btn_reset_tpl = QPushButton("Reset Default")
        btn_reset_tpl.setObjectName("linksTxtResetDefault")
        btn_reset_tpl.setAutoDefault(False)
        btn_reset_tpl.setDefault(False)
        btn_reset_tpl.setFocusPolicy(Qt.TabFocus)
        btn_reset_tpl.setToolTip(
            f"Reset Default ({DEFAULT_LINKS_TXT_FILENAME_TEMPLATE}) "
            "Bestätigung nur bei Abweichung; danach Fokus+Selektion — 2.3.5"
        )
        btn_reset_tpl.setAccessibleName("Links-TXT Reset Default")
        btn_reset_tpl.setAccessibleDescription(
            "Template auf Default zurücksetzen. Bestätigung nur bei Abweichung; "
            "danach Fokus und Selektion im Template-Feld — 2.3.5"
        )

        def _reset_tpl() -> None:
            default = DEFAULT_LINKS_TXT_FILENAME_TEMPLATE

            def _after() -> None:
                _update_preview()
                tpl_esc.commit(default)

            # Bestätigung nur bei Abweichung; Fokus+Selektion via after_focus — 2.3.5
            reset_line_edit_template(
                opts,
                tpl_edit,
                default,
                title="Reset Default",
                body_prefix="Links-TXT-Template auf Default zurücksetzen?",
                on_updated=_after,
                after_focus=True,
            )

        btn_reset_tpl.clicked.connect(_reset_tpl)
        tpl_row.addWidget(btn_reset_tpl)
        ol.addLayout(tpl_row)
        ol.addWidget(preview)
        tpl_edit.textChanged.connect(lambda _t: _update_preview())
        _update_preview()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Speichern…")
        buttons.accepted.connect(opts.accept)
        buttons.rejected.connect(opts.reject)
        ol.addWidget(buttons)
        if opts.exec() != QDialog.Accepted:
            return

        utf8_bom = bool(chk_bom.isChecked())
        set_links_txt_utf8_bom(utf8_bom)
        tpl = tpl_edit.text().strip() or DEFAULT_LINKS_TXT_FILENAME_TEMPLATE
        set_links_txt_filename_template(tpl)

        start = dialog_start_dir(get_last_links_txt_dir())
        fname = format_links_txt_filename(stem, template=tpl)
        default = str(Path(start) / fname)
        path, _ok = QFileDialog.getSaveFileName(
            self,
            "URL-Liste als TXT exportieren",
            default,
            "Text (*.txt);;Alle Dateien (*)",
        )
        if not path:
            return
        dest = Path(path)
        if dest.suffix.lower() != ".txt":
            dest = dest.with_suffix(".txt")
        try:
            out = export_links_txt(dest, uris, utf8_bom=utf8_bom)
            set_last_links_txt_dir(out.parent)
            bom_s = "BOM" if utf8_bom else "ohne BOM"
            self._set_status(
                f"Links TXT: {len(uris)} URL(s) → {out.name} ({bom_s})"
            )
        except Exception as e:
            QMessageBox.warning(self, "Links exportieren", str(e))

    def _on_link_edit(self, ann) -> None:
        """Link-URL bearbeiten — 2.3.1."""
        if ann is None or not self.pdf_view.store:
            return
        aid = getattr(ann, "id", None)
        if not aid:
            return
        self.pdf_view._selected_ann_id = aid
        self.pdf_view.edit_link_uri(aid)

    def _on_link_delete(self, ann_or_list) -> None:
        """Link(s) löschen mit Bestätigung — 2.3.1."""
        if not self.pdf_view.store or ann_or_list is None:
            return
        anns = list(ann_or_list) if isinstance(ann_or_list, (list, tuple)) else [ann_or_list]
        anns = [a for a in anns if a is not None and getattr(a, "id", None)]
        if not anns:
            return
        n = len(anns)
        reply = QMessageBox.question(
            self,
            "Links löschen",
            f"{n} Link(s) wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        ids = [str(a.id) for a in anns]
        try:
            if hasattr(self.pdf_view.store, "remove_many"):
                self.pdf_view.store.remove_many(ids)
            else:
                for aid in ids:
                    self.pdf_view.store.remove(aid)
            self.pdf_view.schedule_sidecar_save()
            self.pdf_view.refresh()
            self.pdf_view.annotations_changed.emit()
            self._set_status(f"{n} Link(s) gelöscht")
        except Exception as e:
            QMessageBox.warning(self, "Links löschen", str(e))

    def _on_redaction_activated(self, ann) -> None:
        """Sprung zur Schwärzungs-Annotation (Doppelklick) — 1.3.2."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if self.pdf_view.focus_annotation(ann):
            return
        if ann is not None and hasattr(ann, "page"):
            self.pdf_view.goto_page(int(ann.page))
            self.sidebar.select_thumb(int(ann.page))
            self._set_status(f"Schwärzung → Seite {int(ann.page) + 1}")

    def _on_redaction_delete(self, ann_or_list) -> None:
        """Schwärzung(en) löschen — Bestätigung mit Zähler; ein Undo-Stack-Eintrag — 1.3.3."""
        if not self.pdf_view.store or ann_or_list is None:
            return
        if isinstance(ann_or_list, (list, tuple)):
            anns = [a for a in ann_or_list if a is not None]
        else:
            anns = [ann_or_list]
        if not anns:
            return
        try:
            from ild_pdf.annotate import AnnotationType

            ids: list[str] = []
            for ann in anns:
                aid = str(getattr(ann, "id", "") or "")
                if not aid:
                    continue
                target = self.pdf_view.store.get(aid)
                if target is None or target.type != AnnotationType.REDACTION:
                    continue
                ids.append(aid)
            if not ids:
                self._set_status("Schwärzung nicht gefunden")
                return
            n = len(ids)
            reply = QMessageBox.question(
                self,
                "Schwärzungen löschen",
                f"{n} Schwärzung(en) wirklich löschen?\n\n"
                "Ein Undo-Schritt stellt alle wieder her (Ctrl+Z).",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                self._set_status(f"Schwärzung löschen abgebrochen ({n})")
                return
            label = f"{n} Schwärzung(en)" if n > 1 else "Schwärzung"
            with self.pdf_view.store.atomic(label=label):
                removed = 0
                for aid in ids:
                    if self.pdf_view.store.remove(aid):
                        removed += 1
            if removed <= 0:
                self._set_status("Schwärzung löschen fehlgeschlagen")
                return
            self.pdf_view.clear_annotation_selection()
            self.pdf_view.schedule_sidecar_save(force=True)
            self.pdf_view.refresh()
            self.pdf_view.annotations_changed.emit()
            self._set_status(
                f"{removed} Schwärzung(en) gelöscht (Undo Ctrl+Z)"
            )
        except Exception as e:
            QMessageBox.warning(self, "Schwärzung", str(e))

    def _import_bookmarks_from_outline(self) -> None:
        """PDF-Outlines → Seiten-Favoriten (Bookmarks) — 1.3.0/1.3.1."""
        if not self._require_pdf("Bookmarks importieren"):
            return
        try:
            from ild_pdf.outline import extract_outline, flatten_outline_pages

            items = extract_outline(self.pdf_view.pdf_path)
            pages = flatten_outline_pages(items)
        except Exception as e:
            QMessageBox.warning(self, "Bookmarks importieren", str(e))
            return
        if not pages:
            self._feature_dialog(
                "Bookmarks importieren",
                "Keine Outline-Einträge mit Seiten-Ziel.",
            )
            return
        # Seiten in Favoriten übernehmen (Reihenfolge Outline DFS)
        n = int(self.pdf_view.page_count or 0)
        order = [p for p, _t in pages if 0 <= int(p) < n]
        if not order:
            self._feature_dialog(
                "Bookmarks importieren",
                "Keine gültigen Outline-Seiten.",
            )
            return
        existing = list(self.pdf_view.list_page_favorites())
        existing_set = set(existing)
        dupes = [p for p in order if p in existing_set]
        final_order = list(order)
        mode = "ersetzt"
        if existing:
            r = QMessageBox.question(
                self,
                "Bookmarks importieren",
                f"{len(order)} Outline-Seite(n) importieren.\n"
                f"Bereits {len(existing)} Favorit(en)"
                + (f", davon {len(dupes)} Duplikat(e)" if dupes else "")
                + ".\n\n"
                "Ja = Duplikate überspringen (neue anhängen).\n"
                "Nein = Favoritenliste durch Outline ersetzen.",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if r == QMessageBox.Cancel:
                return
            if r == QMessageBox.Yes:
                final_order = existing + [p for p in order if p not in existing_set]
                mode = "übersprungen"
            else:
                final_order = list(order)
                mode = "ersetzt"
        try:
            self.pdf_view.reorder_page_favorites(final_order)
            self._refresh_page_favorites()
            self._set_status(
                f"{len(final_order)} Bookmark(s) aus Outline importiert ({mode})"
            )
        except Exception as e:
            QMessageBox.warning(self, "Bookmarks importieren", str(e))

    def _export_bookmarks_to_outline(self) -> None:
        """Outlines-Export: Retry max. 3 wie Backup, dann Abbruch-Hinweis — 1.3.5."""
        if not self._require_pdf("Bookmarks exportieren"):
            return
        # Leere Outlines/Favoriten Hinweis — 1.3.2
        try:
            from ild_pdf.outline import extract_outline

            existing_ol = extract_outline(self.pdf_view.pdf_path)
        except Exception:
            existing_ol = []
        favs = self.pdf_view.list_page_favorites()
        if not favs:
            hint = ""
            if not existing_ol:
                hint = (
                    "\n\nHinweis: Das aktuelle PDF hat ebenfalls keine Outlines."
                )
            self._feature_dialog(
                "Bookmarks exportieren",
                "Keine Seiten-Favoriten — zuerst Bookmarks setzen oder Outline importieren."
                + hint,
            )
            return
        box_r = QMessageBox.question(
            self,
            "Bookmarks als Outlines exportieren",
            f"{len(favs)} Bookmark(s) als PDF-Outline schreiben.\n\n"
            "Ja = aktuelles PDF\nNein = anderes PDF wählen",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if box_r == QMessageBox.Cancel:
            return
        source = Path(self.pdf_view.pdf_path)
        target = source
        if box_r == QMessageBox.No:
            start = dialog_start_dir(get_last_export_dir() or source.parent)
            suggest = str(Path(start) / f"{source.stem}_outlines.pdf")
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Ziel-PDF für Outlines",
                suggest,
                "PDF (*.pdf)",
            )
            if not path:
                return
            target = Path(path)
            # Anderes PDF: bestehende Datei nutzen oder Kopie; fehlende Quelle abfangen — 1.3.3
            if target.is_file():
                pass
            else:
                if not source.is_file():
                    QMessageBox.warning(
                        self,
                        "Bookmarks exportieren",
                        f"Quell-PDF nicht gefunden:\n{source}",
                    )
                    return
                try:
                    import shutil

                    shutil.copy2(source, target)
                except FileNotFoundError:
                    QMessageBox.warning(
                        self,
                        "Bookmarks exportieren",
                        f"Datei nicht gefunden:\n{source}",
                    )
                    return
                except Exception as e:
                    QMessageBox.warning(self, "Bookmarks exportieren", str(e))
                    return
            if not target.is_file():
                QMessageBox.warning(
                    self,
                    "Bookmarks exportieren",
                    f"Ziel-PDF nicht gefunden:\n{target}",
                )
                return
            set_last_export_dir(target.parent)
        entries: list[tuple[int, str]] = []
        for p in favs:
            try:
                label = (
                    self.pdf_view.page_label(p)
                    if self.pdf_view.has_page_labels()
                    else ""
                )
            except Exception:
                label = ""
            entries.append((int(p), label or f"Seite {int(p) + 1}"))
        # Schreibfehler: max. 3 Versuche wie Backup, danach Abbruch-Hinweis — 1.3.5
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                from ild_pdf.outline import outline_from_pages, write_outline

                write_outline(target, outline_from_pages(entries))
                if target.resolve() == source.resolve():
                    self._refresh_outline(self.pdf_view.pdf_path)
                self._last_outline_export_dir = target.parent
                set_last_export_dir(target.parent)
                self._set_status(
                    f"{len(entries)} Bookmark(s) als PDF-Outline → {target}"
                )
                return
            except FileNotFoundError:
                QMessageBox.warning(
                    self,
                    "Bookmarks exportieren",
                    f"Datei nicht gefunden:\n{target}",
                )
                return
            except OSError as e:
                if attempt >= max_attempts:
                    QMessageBox.critical(
                        self,
                        "Bookmarks exportieren",
                        f"Versuch {attempt}/{max_attempts}\n\n"
                        f"Outlines-Export nach {max_attempts} Versuchen abgebrochen "
                        f"(max. {max_attempts} wie Backup).\n\n"
                        f"Letzter Fehler:\n{e}\n\n"
                        "Bitte Zielpfad, Schreibrechte oder Speicherplatz prüfen.",
                    )
                    self._set_status(
                        f"Outlines-Export abgebrochen nach {max_attempts} Versuchen"
                    )
                    return
                # Retry-Zähler prominent „Versuch k/3“ — 1.3.6
                err_box = QMessageBox(self)
                err_box.setIcon(QMessageBox.Critical)
                err_box.setWindowTitle("Bookmarks exportieren")
                err_box.setText(f"Versuch {attempt}/{max_attempts}")
                err_box.setInformativeText(
                    f"Outlines-Export fehlgeschlagen:\n{e}\n\n"
                    f"Erneut versuchen? (max. {max_attempts} wie Backup)"
                )
                err_box.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
                err_box.setDefaultButton(QMessageBox.Retry)
                if err_box.exec() != QMessageBox.Retry:
                    QMessageBox.information(
                        self,
                        "Bookmarks exportieren",
                        f"Outlines-Export abgebrochen "
                        f"(Versuch {attempt}/{max_attempts}).",
                    )
                    self._set_status(
                        f"Outlines-Export abgebrochen (Versuch {attempt}/{max_attempts})"
                    )
                    return
            except Exception as e:
                QMessageBox.warning(self, "Bookmarks exportieren", str(e))
                return

    def _refresh_thumbs(self):
        if not self.pdf_view.pdf_path:
            self._stop_thumb_lazy()
            self.sidebar.clear_thumbs()
            self._update_thumb_cache_debug_status()
            return
        # Lazy: Platzhalter; Prefetch ±N; große PDFs nur Viewport (virtual) — 2.6.37
        self._stop_thumb_lazy()
        try:
            from ild_pdf.limits import THUMB_LAZY_THRESHOLD, THUMB_VIRTUAL_THRESHOLD
            from instantlensdoc.core.app_settings import (
                get_thumb_lazy_threshold,
                get_thumb_prefetch_radius,
            )

            try:
                threshold = int(get_thumb_lazy_threshold())
            except Exception:
                threshold = int(THUMB_LAZY_THRESHOLD)
            try:
                radius = int(get_thumb_prefetch_radius())
            except Exception:
                radius = 2
            page_count = int(self.pdf_view.page_count or 0)
            current = int(self.pdf_view.page_index or 0)
            open_gen = int(getattr(self.pdf_view, "_open_generation", 0) or 0)
            max_pages = page_count if page_count > 0 else 0
            token = self.sidebar.prepare_lazy_thumbs(
                page_count,
                current=current,
                max_pages=max_pages or page_count,
                cancel_check=lambda: int(
                    getattr(self.pdf_view, "_open_generation", 0) or 0
                )
                != open_gen,
            )
            virtual = page_count >= int(THUMB_VIRTUAL_THRESHOLD)
            self._start_thumb_lazy(
                token,
                page_count=page_count,
                prefer=current,
                radius=radius,
                virtual_only=virtual,
            )
            if page_count > threshold and hasattr(self, "file_status_label"):
                mode = "Viewport±Prefetch" if virtual else "Lazy-Load"
                self._set_status(
                    f"Thumbnails: {mode} {page_count} Seiten "
                    f"(>{threshold}, Prefetch ±{radius})"
                )
            self._update_thumb_cache_debug_status()
        except Exception as e:
            _log.warning("Thumbnails: %s", e)
            self._stop_thumb_lazy()
            self.sidebar.clear_thumbs()
            self._update_thumb_cache_debug_status()

    def _stop_thumb_lazy(self):
        if self._thumb_lazy_timer is not None:
            try:
                self._thumb_lazy_timer.stop()
            except Exception:
                pass
            self._thumb_lazy_timer = None
        self._thumb_lazy_queue = []
        self._thumb_lazy_token = None
        self._thumb_lazy_loaded = set()
        self._thumb_lazy_page_count = 0
        self._thumb_lazy_virtual = False

    def _cancel_thumb_lazy_queue(self) -> None:
        """Warteschlange leeren (Token/Timer behalten) — schneller Scroll — 1.3.2."""
        self._thumb_lazy_queue = []

    def _prefetch_thumbs_around(self, center: int, *, radius: int | None = None, cancel: bool = False):
        """Prefetch Viewport ±radius (Settings 1/2/3); optional Queue cancel — 1.3.3."""
        n = int(self._thumb_lazy_page_count or 0)
        if n <= 0 or self._thumb_lazy_token is None:
            return
        if radius is None:
            try:
                from instantlensdoc.core.app_settings import get_thumb_prefetch_radius

                radius = int(get_thumb_prefetch_radius())
            except Exception:
                radius = 2
        radius = max(1, min(3, int(radius)))
        if cancel:
            self._cancel_thumb_lazy_queue()
        prefer: list[int] = []
        seen: set[int] = set()
        for d in range(0, radius + 1):
            for i in (center - d, center + d) if d else (center,):
                if 0 <= i < n and i not in seen and i not in self._thumb_lazy_loaded:
                    seen.add(i)
                    prefer.append(i)
        # Preferierte Seiten vorne; Rest der Queue behalten falls nicht cancel
        rest = [i for i in self._thumb_lazy_queue if i not in seen]
        self._thumb_lazy_queue = prefer + rest
        if self._thumb_lazy_timer is None and self._thumb_lazy_queue:
            self._thumb_lazy_timer = QTimer(self)
            self._thumb_lazy_timer.setInterval(16)
            self._thumb_lazy_timer.timeout.connect(self._thumb_lazy_tick)
            self._thumb_lazy_timer.start()

    def _on_thumbs_viewport_changed(self, center: int, cancel_fast: bool = False):
        """Sidebar-Thumb-Scroll: Prefetch ±N Settings; Cancel bei schnellem Scroll — 1.3.3."""
        if self._thumb_lazy_token is None:
            return
        self._prefetch_thumbs_around(int(center), cancel=bool(cancel_fast))

    def _start_thumb_lazy(
        self,
        token: int,
        *,
        page_count: int,
        prefer: int = 0,
        radius: int | None = None,
        virtual_only: bool | None = None,
    ):
        self._stop_thumb_lazy()
        if page_count <= 0:
            return
        if radius is None:
            try:
                from instantlensdoc.core.app_settings import get_thumb_prefetch_radius

                radius = int(get_thumb_prefetch_radius())
            except Exception:
                radius = 2
        radius = max(1, min(3, int(radius)))
        if virtual_only is None:
            try:
                from ild_pdf.limits import THUMB_VIRTUAL_THRESHOLD

                virtual_only = page_count >= int(THUMB_VIRTUAL_THRESHOLD)
            except Exception:
                virtual_only = page_count >= 80
        # Aktuelle Seite zuerst, dann Prefetch ±N.
        # Große PDFs: KEIN Rest-Queue (Scroll/Prefetch holt nach) — 2.6.37
        order: list[int] = []
        seen: set[int] = set()
        near = [prefer]
        for d in range(1, radius + 1):
            near.extend([prefer - d, prefer + d])
        rest = [] if virtual_only else list(range(page_count))
        for i in near + rest:
            if 0 <= i < page_count and i not in seen:
                seen.add(i)
                order.append(i)
        self._thumb_lazy_queue = order
        self._thumb_lazy_token = token
        self._thumb_lazy_loaded = set()
        self._thumb_lazy_page_count = page_count
        self._thumb_lazy_virtual = bool(virtual_only)
        self._thumb_lazy_open_gen = int(getattr(self.pdf_view, "_open_generation", 0) or 0)
        self._thumb_lazy_timer = QTimer(self)
        self._thumb_lazy_timer.setInterval(16)
        self._thumb_lazy_timer.timeout.connect(self._thumb_lazy_tick)
        self._thumb_lazy_timer.start()

    def _thumb_lazy_tick(self):
        if self._thumb_lazy_token is None:
            self._stop_thumb_lazy()
            return
        if not self.pdf_view.pdf_path:
            self._stop_thumb_lazy()
            return
        # Dokument-Token: Lauf gehört zu einem geschlossenen/ersetzten Dokument
        # (z. B. Tick während processEvents() im nächsten load()) — 2.6.54
        if int(getattr(self.pdf_view, "_open_generation", 0) or 0) != int(
            self._thumb_lazy_open_gen or 0
        ):
            self._stop_thumb_lazy()
            return
        # Leere Queue: Timer stoppen, Token behalten (Virtual-Prefetch bei Scroll) — 2.6.40
        if not self._thumb_lazy_queue:
            if self._thumb_lazy_timer is not None:
                try:
                    self._thumb_lazy_timer.stop()
                except Exception:
                    pass
                self._thumb_lazy_timer = None
            return
        idx = self._thumb_lazy_queue.pop(0)
        if idx in self._thumb_lazy_loaded:
            if not self._thumb_lazy_queue:
                if self._thumb_lazy_timer is not None:
                    try:
                        self._thumb_lazy_timer.stop()
                    except Exception:
                        pass
                    self._thumb_lazy_timer = None
            return
        try:
            img = self.pdf_view.render_thumbnail(idx, scale=get_pdf_thumbnail_scale())
            if self.sidebar.update_thumb(idx, img, token=self._thumb_lazy_token):
                self._thumb_lazy_loaded.add(idx)
        except Exception as e:
            _log.debug("Thumb lazy %s: %s", idx, e)
            self._thumb_lazy_loaded.add(idx)
        # Hit/Miss Debug periodisch aktualisieren — 2.4.1
        if len(self._thumb_lazy_loaded) % 5 == 0 or not self._thumb_lazy_queue:
            self._update_thumb_cache_debug_status()
        if not self._thumb_lazy_queue:
            if self._thumb_lazy_timer is not None:
                try:
                    self._thumb_lazy_timer.stop()
                except Exception:
                    pass
                self._thumb_lazy_timer = None

    def _on_thumb_jump(self, page_index: int):
        """Schnellvorschau-Klick: Seite in Hauptansicht zeigen (auch Virtual-Thumbs) — 2.6.40/2.6.47."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        try:
            self.pdf_view.show()
        except Exception:
            pass
        if not self.pdf_view.pdf_path:
            self._set_status("Kein PDF geladen")
            return
        idx = int(page_index)
        self.pdf_view.set_current_page(idx)
        # Fokus zurück auf die PDF-Ansicht, sonst schluckt die Thumbnail-Liste
        # PageUp/PageDown und die Nav-Shortcuts greifen nicht — 2.6.54
        try:
            self.pdf_view.canvas.setFocus(Qt.OtherFocusReason)
        except Exception:
            try:
                self.pdf_view.setFocus(Qt.OtherFocusReason)
            except Exception:
                pass
        # Immer Paint erzwingen (auch nach Continuous-Short-Circuit) — 2.6.47
        if not self.pdf_view._ensure_page_painted(warn=False):
            self._set_status(
                "Hauptansicht leer — Zoom verringern oder Seite erneut wählen"
            )
        self.sidebar.select_thumb(idx)
        self._prefetch_thumbs_around(idx, cancel=False)

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
        """Thumbnail-Mehrfachauswahl: Seiten batch-drehen (±90/180, Undo Ctrl+Z)."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            return
        idxs = [int(p) for p in (pages or [])]
        if self.pdf_view.rotate_many(idxs, int(degrees)):
            self._refresh_thumbs()
            self._update_doc_status()
            self._blink_status_briefly()

    def _on_thumb_flip(self, page_index: int, horizontal: bool, vertical: bool):
        """Thumbnail: Seite spiegeln (H/V) + Undo — 1.8.0."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            return
        if self.pdf_view.flip_at(
            int(page_index), horizontal=bool(horizontal), vertical=bool(vertical)
        ):
            self._refresh_thumbs()
            self._update_doc_status()

    def _on_thumbs_batch_flip(self, pages: list, horizontal: bool, vertical: bool):
        """Thumbnail-Mehrfachauswahl: spiegeln H/V + Undo — 1.8.0."""
        if self.stack.currentWidget() is not self.pdf_view:
            self.stack.setCurrentWidget(self.pdf_view)
        if not self.pdf_view.pdf_path:
            return
        idxs = [int(p) for p in (pages or [])]
        if self.pdf_view.flip_many(
            idxs, horizontal=bool(horizontal), vertical=bool(vertical)
        ):
            self._refresh_thumbs()
            self._update_doc_status()
            self._blink_status_briefly()

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
        # Sticky 0-Treffer-Status bei Seitenwechsel löschen — 1.1.8
        self._clear_ann_zero_sticky_status()
        self.sidebar.select_thumb(page_index)
        self.sidebar.set_annotation_current_page(page_index)
        self._refresh_page_favorites()
        self._update_doc_status()

    def _pdf_page_shortcut(self, direction: int) -> None:
        """Bild auf/ab: Seite blättern, nur wenn die PDF-Ansicht aktiv ist — 2.6.54."""
        if self.stack.currentWidget() is not self.pdf_view:
            return
        if not self.pdf_view.pdf_path:
            return
        if int(direction) < 0:
            self.pdf_view.prev_page()
        else:
            self.pdf_view.next_page()

    def _sync_pdf_page_shortcuts(self, *_args) -> None:
        on = (
            not bool(getattr(self, "_presentation_active", False))
            and self.stack.currentWidget() is self.pdf_view
            and bool(getattr(self.pdf_view, "pdf_path", None))
        )
        for sc in (
            getattr(self, "_sc_pdf_page_down", None),
            getattr(self, "_sc_pdf_page_up", None),
        ):
            if sc is not None:
                sc.setEnabled(bool(on))
        self._sync_editor_only_actions()

    def _offer_reload_pdf(
        self,
        out_path,
        *,
        title: str = "Passwort",
        password: str | None = None,
        prefill: bool = False,
    ) -> None:
        """Nach Encrypt/Decrypt optional Datei neu laden — 1.6.1/1.6.2."""
        from pathlib import Path as _Path

        from instantlensdoc.core.app_settings import get_crypto_reload_prefill_password

        path = _Path(out_path)
        if not path.is_file():
            return
        reply = QMessageBox.question(
            self,
            title,
            f"Gespeichert:\n{path}\n\nDatei jetzt neu laden?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            try:
                # Prefill nur wenn Toggle an (unsicher, default aus) — 1.6.2
                use_prefill = bool(prefill) or get_crypto_reload_prefill_password()
                if use_prefill and password:
                    self._crypto_reload_prefill = str(password)
                else:
                    self._crypto_reload_prefill = None
                self.open_path(str(path))
            except Exception as e:
                QMessageBox.warning(self, title, f"Neu laden fehlgeschlagen:\n{e}")
            finally:
                self._crypto_reload_prefill = None

    def _pdf_security_dialog(self):
        """Verschlüsselung & Rechte — zentraler Dialog — 2.6.7."""
        if not self._require_pdf("Verschlüsselung"):
            return
        dlg = PdfSecurityDialog(
            self,
            pdf_path=self.pdf_view.pdf_path,
            password=getattr(self.pdf_view, "password", None),
            pdf_name=self.pdf_view.pdf_path.name,
        )
        if not dlg.exec():
            return
        vals = dlg.values()
        action = str(vals.get("action") or PdfSecurityDialog.ACTION_NONE)
        if action == PdfSecurityDialog.ACTION_SET:
            self._apply_set_password(vals)
        elif action == PdfSecurityDialog.ACTION_REMOVE:
            self._apply_remove_password(vals)
        elif action == PdfSecurityDialog.ACTION_UPDATE_PERMS:
            self._apply_update_permissions(vals)

    def _apply_set_password(self, vals: dict) -> None:
        from ild_pdf import set_password
        from ild_pdf.render import clear_render_cache

        user_pw = str(vals.get("user_password") or "")
        if not user_pw.strip():
            QMessageBox.warning(self, "Passwort", "User-Passwort darf nicht leer sein.")
            return
        prefill = bool(vals.get("prefill_reload", False))
        src = self.pdf_view.pdf_path
        if vals.get("inplace"):
            out = src
        else:
            out = src.with_name(f"{src.stem}_locked.pdf")
        kwargs = {
            "user_password": user_pw,
            "owner_password": vals.get("owner_password"),
            "out_path": out,
            "aes256": bool(vals.get("aes256", True)),
            "open_password": getattr(self.pdf_view, "password", None),
        }
        if vals.get("permissions") is not None:
            kwargs["permissions"] = vals["permissions"]
        else:
            kwargs["allow_printing"] = bool(vals.get("allow_printing", True))
            kwargs["allow_modify"] = bool(vals.get("allow_modify", False))
            kwargs["allow_extract"] = bool(vals.get("allow_extract", False))
        try:
            set_password(src, **kwargs)
            clear_render_cache(src)
            self._set_status(f"Passwort gesetzt ({'AES-256' if kwargs.get('aes256') else 'AES'}) → {out.name}")
            _log.info("PDF encrypted: %s", out)
            self._offer_reload_pdf(
                out, title="Passwort", password=user_pw, prefill=prefill
            )
        except Exception as e:
            _log.exception("Passwort setzen fehlgeschlagen")
            QMessageBox.warning(self, "Passwort", str(e))

    def _apply_remove_password(self, vals: dict) -> None:
        from ild_pdf import remove_password
        from ild_pdf.render import clear_render_cache
        from ild_pdf.security import WRONG_PASSWORD_MSG_DE, is_wrong_password_error

        pw = str(vals.get("password") or "")
        if not pw.strip():
            QMessageBox.warning(self, "Passwort", "Passwort darf nicht leer sein.")
            return
        prefill = bool(vals.get("prefill_reload", False))
        src = self.pdf_view.pdf_path
        out = src if vals.get("inplace") else src.with_name(f"{src.stem}_unlocked.pdf")
        try:
            remove_password(src, pw, out_path=out)
            clear_render_cache(src)
            self._set_status(f"Passwort entfernt → {out.name}")
            _log.info("PDF decrypted: %s", out)
            self._offer_reload_pdf(
                out, title="Passwort", password=pw, prefill=prefill
            )
        except Exception as e:
            _log.exception("Passwort entfernen fehlgeschlagen")
            msg = WRONG_PASSWORD_MSG_DE if is_wrong_password_error(e) else str(e)
            QMessageBox.warning(self, "Passwort", msg)

    def _apply_update_permissions(self, vals: dict) -> None:
        from ild_pdf.security import update_permissions
        from ild_pdf.render import clear_render_cache

        user_pw = str(vals.get("user_password") or "")
        owner_pw = str(vals.get("owner_password") or "")
        if not user_pw.strip() or not owner_pw.strip():
            QMessageBox.warning(
                self, "Rechte", "User- und Owner-Passwort erforderlich."
            )
            return
        src = self.pdf_view.pdf_path
        out = src if vals.get("inplace") else src.with_name(f"{src.stem}_perms.pdf")
        try:
            update_permissions(
                src,
                user_password=user_pw,
                owner_password=owner_pw,
                permissions=vals["permissions"],
                out_path=out,
                aes256=bool(vals.get("aes256", True)),
                open_password=getattr(self.pdf_view, "password", None) or user_pw,
            )
            clear_render_cache(src)
            self._set_status(f"Rechte aktualisiert → {out.name}")
            _log.info("PDF permissions updated: %s", out)
            self._offer_reload_pdf(
                out,
                title="Rechte",
                password=user_pw,
                prefill=bool(vals.get("prefill_reload", False)),
            )
        except Exception as e:
            _log.exception("Rechte aktualisieren fehlgeschlagen")
            QMessageBox.warning(self, "Rechte", str(e))

    def _set_pdf_password(self):
        if not self._require_pdf("Passwort"):
            return
        dlg = SetPasswordDialog(self, pdf_name=self.pdf_view.pdf_path.name)
        if not dlg.exec():
            return
        vals = dlg.values()
        vals["inplace"] = False
        self._apply_set_password(vals)

    def _remove_pdf_password(self):
        """PDF entschlüsseln / Passwort entfernen — 1.6.0/1.6.2."""
        if not self._require_pdf("Passwort"):
            return
        dlg = RemovePasswordDialog(self, pdf_name=self.pdf_view.pdf_path.name)
        if not dlg.exec():
            return
        self._apply_remove_password(dlg.values())

    def _sync_doc_stats_panel(self) -> None:
        """Offenes Statistik-Panel bei Doc-Wechsel aktualisieren — 1.6.1."""
        dlg = getattr(self, "_doc_stats_dialog", None)
        if dlg is None:
            return
        try:
            if not dlg.isVisible():
                return
        except RuntimeError:
            self._doc_stats_dialog = None
            return
        ann_n = (
            len(self.pdf_view.store.annotations)
            if self.pdf_view.pdf_path and getattr(self.pdf_view, "store", None)
            else None
        )
        dlg.set_document(
            self.pdf_view.pdf_path if self.pdf_view.pdf_path else None,
            annotation_count=ann_n,
        )

    def _show_doc_stats(self):
        """Dokument-Statistik-Panel (Seiten/Wörter/Ann./Größe) — 1.6.0/1.6.1."""
        if not self._require_pdf("Dokument-Statistik"):
            return
        ann_n = (
            len(self.pdf_view.store.annotations)
            if getattr(self.pdf_view, "store", None)
            else None
        )
        dlg = getattr(self, "_doc_stats_dialog", None)
        if dlg is None:
            dlg = DocStatsDialog(
                self,
                pdf_path=self.pdf_view.pdf_path,
                annotation_count=ann_n,
            )
            self._doc_stats_dialog = dlg
        else:
            dlg.set_document(self.pdf_view.pdf_path, annotation_count=ann_n)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _refresh_workspace_layout_menu(self):
        """Ansicht → Workspace-Layouts Menü neu aufbauen — 1.6.1."""
        from instantlensdoc.core.app_settings import (
            WORKSPACE_LAYOUTS_MAX,
            get_default_workspace_layout_name,
            get_workspace_layouts,
        )

        menu = getattr(self, "_workspace_layout_menu", None)
        if menu is None:
            return
        menu.clear()
        act_save = QAction("Layout speichern…", self)
        act_save.setToolTip(
            f"Aktuelle Panels + Splitter speichern (max. {WORKSPACE_LAYOUTS_MAX}; "
            "Duplikat-Namen abgelehnt) — 1.6.2"
        )
        act_save.triggered.connect(self._save_workspace_layout)
        menu.addAction(act_save)
        act_export = QAction("Layouts exportieren…", self)
        act_export.setToolTip("Alle Layouts als ildlayouts-v1 JSON — 1.6.2")
        act_export.triggered.connect(self._export_workspace_layouts)
        menu.addAction(act_export)
        act_import = QAction("Layouts importieren…", self)
        act_import.setToolTip(
            "Layouts aus ildlayouts-v1 JSON; Merge Kollision skip/rename + Log; "
            "ungültiges Schema klar DE — 1.6.4"
        )
        act_import.triggered.connect(self._import_workspace_layouts)
        menu.addAction(act_import)
        menu.addSeparator()
        layouts = get_workspace_layouts()
        default_name = get_default_workspace_layout_name()
        default_key = default_name.casefold() if default_name else ""
        if not layouts:
            empty = QAction("(keine Layouts)", self)
            empty.setEnabled(False)
            menu.addAction(empty)
        else:
            for layout in layouts:
                name = str(layout.get("name") or "")
                label = f"{name} ★" if name.casefold() == default_key else name
                act = QAction(label, self)
                tip = f"Layout „{name}“ laden (Panels + Splitter)"
                if name.casefold() == default_key:
                    tip += " — Standard"
                act.setToolTip(tip)
                act.triggered.connect(
                    lambda checked=False, n=name: self._load_workspace_layout(n)
                )
                menu.addAction(act)
            menu.addSeparator()
            act_rename = QAction("Layout umbenennen…", self)
            act_rename.triggered.connect(self._rename_workspace_layout)
            menu.addAction(act_rename)
            act_default = QAction("Als Standard markieren…", self)
            act_default.setToolTip("Default-Layout markieren (★) — 1.6.1")
            act_default.triggered.connect(self._mark_default_workspace_layout)
            menu.addAction(act_default)
            act_del = QAction("Layout löschen…", self)
            act_del.triggered.connect(self._delete_workspace_layout)
            menu.addAction(act_del)

    def _current_workspace_layout_state(self) -> dict:
        panels = {}
        if hasattr(self, "sidebar") and hasattr(self.sidebar, "panel_visibility"):
            panels = dict(self.sidebar.panel_visibility())
        else:
            panels = {"thumbs": True, "ann": True, "bookmark": True}
        return {
            "panels": panels,
            "splitter_sizes": self._main_splitter_sizes() or [],
        }

    def _save_workspace_layout(self):
        from PySide6.QtWidgets import QInputDialog

        from instantlensdoc.core.app_settings import (
            WORKSPACE_LAYOUTS_MAX,
            get_workspace_layout,
            save_workspace_layout,
        )

        name, ok = QInputDialog.getText(
            self,
            "Workspace-Layout",
            f"Name für das Layout (max. {WORKSPACE_LAYOUTS_MAX}; Duplikate abgelehnt):",
        )
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            QMessageBox.warning(self, "Workspace-Layout", "Name darf nicht leer sein.")
            return
        if get_workspace_layout(name) is not None:
            QMessageBox.warning(
                self,
                "Workspace-Layout",
                f"Name bereits vergeben: {name}",
            )
            return
        try:
            save_workspace_layout(
                name,
                state=self._current_workspace_layout_state(),
                overwrite=False,
            )
            self._refresh_workspace_layout_menu()
            self._set_status(f"Layout gespeichert: {name}")
        except Exception as e:
            QMessageBox.warning(self, "Workspace-Layout", str(e))

    def _export_workspace_layouts(self):
        """Layouts als ildlayouts-v1 JSON exportieren — 1.6.2."""
        from pathlib import Path as _Path

        from instantlensdoc.core.app_settings import (
            dialog_start_dir,
            export_workspace_layouts_json,
            get_last_export_dir,
            get_workspace_layouts,
            set_last_export_dir,
        )

        if not get_workspace_layouts():
            QMessageBox.information(self, "Workspace-Layout", "Keine Layouts gespeichert.")
            return
        start = dialog_start_dir(get_last_export_dir())
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Layouts exportieren (ildlayouts-v1)",
            str(_Path(start) / "workspace_layouts.json"),
            "JSON (*.json);;Alle (*.*)",
        )
        if not path:
            return
        try:
            out = export_workspace_layouts_json(path)
            set_last_export_dir(_Path(out).parent)
            self._set_status(f"Layouts exportiert: {_Path(out).name}")
            QMessageBox.information(
                self, "Workspace-Layout", f"Exportiert (ildlayouts-v1):\n{out}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Workspace-Layout", str(e))

    def _show_layouts_import_log(self, result, *, mode: str, strat: str = "") -> None:
        """
        Import-Log-Dialog: Zusammenfassung importiert/übersprungen/umbenannt;
        Log kopieren / als TXT — 1.6.5.
        """
        from pathlib import Path as _Path

        from PySide6.QtGui import QGuiApplication

        from instantlensdoc.core.app_settings import (
            dialog_start_dir,
            export_layouts_import_log_txt,
            get_last_export_dir,
            set_last_export_dir,
        )

        summary = result.summary_text()
        log_body = result.log_text(include_summary=True).rstrip()
        while True:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("Workspace-Layout — Import-Log")
            box.setText(
                f"{len(result)} Layout(s) geladen "
                f"(ildlayouts-v1, {mode}{strat}).\n\n"
                f"Zusammenfassung: {summary}"
            )
            box.setInformativeText(log_body)
            btn_copy = box.addButton("Log kopieren", QMessageBox.ActionRole)
            btn_txt = box.addButton("Als TXT…", QMessageBox.ActionRole)
            btn_ok = box.addButton(QMessageBox.Ok)
            box.setDefaultButton(btn_ok)
            box.exec()
            clicked = box.clickedButton()
            if clicked is btn_copy:
                QGuiApplication.clipboard().setText(log_body + "\n")
                self._set_status("Import-Log kopiert")
                continue
            if clicked is btn_txt:
                start = dialog_start_dir(get_last_export_dir())
                path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Import-Log als TXT speichern",
                    str(_Path(start) / "ildlayouts-import-log.txt"),
                    "Textdatei (*.txt);;Alle Dateien (*)",
                )
                if not path:
                    continue
                if not str(path).lower().endswith(".txt"):
                    path = str(path) + ".txt"
                try:
                    out = export_layouts_import_log_txt(path, result, utf8_bom=True)
                    set_last_export_dir(_Path(out).parent)
                    self._set_status(f"Import-Log gespeichert: {_Path(out).name}")
                    QMessageBox.information(
                        self, "Workspace-Layout", f"Import-Log gespeichert:\n{out}"
                    )
                except Exception as exc:
                    QMessageBox.warning(
                        self,
                        "Workspace-Layout",
                        f"TXT-Export fehlgeschlagen:\n{exc}",
                    )
                continue
            break

    def _import_workspace_layouts(self):
        """
        Layouts aus ildlayouts-v1 JSON: Merge vs. Ersetzen;
        bei Merge Kollision überspringen/umbenennen (_2);
        Import-Log mit Zusammenfassung + kopieren/als TXT — 1.6.5.
        """
        from pathlib import Path as _Path

        from instantlensdoc.core.app_settings import (
            LayoutsImportError,
            dialog_start_dir,
            get_last_export_dir,
            import_workspace_layouts_json,
            set_last_export_dir,
        )

        start = dialog_start_dir(get_last_export_dir())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Layouts importieren (ildlayouts-v1)",
            start,
            "JSON (*.json);;Alle (*.*)",
        )
        if not path:
            return
        reply = QMessageBox.question(
            self,
            "Layouts importieren",
            "Vorhandene Layouts ersetzen?\n"
            "„Ja“ = Ersetzen (alle aktuellen Layouts werden verworfen).\n"
            "„Nein“ = Zusammenführen/Merge (Kollisionsstrategie wählen).",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.No,
        )
        if reply == QMessageBox.Cancel:
            return
        merge = reply == QMessageBox.No
        on_collision = "reject"
        if merge:
            coll = QMessageBox.question(
                self,
                "Namenskollision",
                "Bei gleichem Layout-Namen:\n"
                "„Ja“ = überspringen\n"
                "„Nein“ = umbenennen (_2, _3, …)",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if coll == QMessageBox.Cancel:
                return
            on_collision = "skip" if coll == QMessageBox.Yes else "rename"
        try:
            result = import_workspace_layouts_json(
                path, merge=merge, on_collision=on_collision
            )
            set_last_export_dir(_Path(path).parent)
            self._refresh_workspace_layout_menu()
            mode = "Merge" if merge else "Ersetzen"
            strat = ""
            if merge:
                strat = " · überspringen" if on_collision == "skip" else " · umbenennen"
            status = (
                f"Layouts importiert ({mode}{strat}): {len(result)} · "
                f"{result.summary_text()}"
            )
            self._set_status(status)
            self._show_layouts_import_log(result, mode=mode, strat=strat)
        except LayoutsImportError as e:
            QMessageBox.warning(self, "Workspace-Layout", str(e))
        except Exception as e:
            QMessageBox.warning(self, "Workspace-Layout", str(e))

    def _load_workspace_layout(self, name: str):
        from instantlensdoc.core.app_settings import get_workspace_layout

        layout = get_workspace_layout(name)
        if not layout:
            self._set_status(f"Layout nicht gefunden: {name}")
            return
        panels = layout.get("panels") or {}
        if hasattr(self, "sidebar") and hasattr(self.sidebar, "set_panel_visibility"):
            self.sidebar.set_panel_visibility(
                thumbs=bool(panels.get("thumbs", True)),
                ann=bool(panels.get("ann", True)),
                bookmark=bool(panels.get("bookmark", True)),
            )
            self._sync_panel_visibility_menu()
        sizes = list(layout.get("splitter_sizes") or [])
        if sizes:
            self._apply_main_splitter_sizes(sizes)
        self._save_session()
        self._set_status(f"Layout geladen: {name}")

    def _rename_workspace_layout(self):
        """Layout umbenennen — 1.6.1."""
        from PySide6.QtWidgets import QInputDialog

        from instantlensdoc.core.app_settings import (
            get_workspace_layouts,
            rename_workspace_layout,
        )

        layouts = get_workspace_layouts()
        if not layouts:
            QMessageBox.information(self, "Workspace-Layout", "Keine Layouts gespeichert.")
            return
        names = [str(p.get("name") or "") for p in layouts]
        old, ok = QInputDialog.getItem(
            self, "Layout umbenennen", "Layout:", names, 0, False
        )
        if not ok or not old:
            return
        new, ok2 = QInputDialog.getText(
            self, "Layout umbenennen", "Neuer Name:", text=old
        )
        if not ok2:
            return
        new = (new or "").strip()
        if not new:
            QMessageBox.warning(self, "Workspace-Layout", "Name darf nicht leer sein.")
            return
        try:
            rename_workspace_layout(old, new)
            self._refresh_workspace_layout_menu()
            self._set_status(f"Layout umbenannt: {old} → {new}")
        except Exception as e:
            QMessageBox.warning(self, "Workspace-Layout", str(e))

    def _mark_default_workspace_layout(self):
        """Default-Layout markieren — 1.6.1."""
        from PySide6.QtWidgets import QInputDialog

        from instantlensdoc.core.app_settings import (
            get_default_workspace_layout_name,
            get_workspace_layouts,
            set_default_workspace_layout,
        )

        layouts = get_workspace_layouts()
        if not layouts:
            QMessageBox.information(self, "Workspace-Layout", "Keine Layouts gespeichert.")
            return
        names = [str(p.get("name") or "") for p in layouts]
        current = get_default_workspace_layout_name()
        start = names.index(current) if current in names else 0
        name, ok = QInputDialog.getItem(
            self,
            "Als Standard markieren",
            "Default-Layout:",
            names,
            start,
            False,
        )
        if not ok or not name:
            return
        try:
            set_default_workspace_layout(name)
            self._refresh_workspace_layout_menu()
            self._set_status(f"Standard-Layout: {name}")
        except Exception as e:
            QMessageBox.warning(self, "Workspace-Layout", str(e))

    def _delete_workspace_layout(self):
        from PySide6.QtWidgets import QInputDialog

        from instantlensdoc.core.app_settings import (
            delete_workspace_layout,
            get_workspace_layouts,
        )

        layouts = get_workspace_layouts()
        if not layouts:
            QMessageBox.information(self, "Workspace-Layout", "Keine Layouts gespeichert.")
            return
        names = [str(p.get("name") or "") for p in layouts]
        name, ok = QInputDialog.getItem(
            self, "Workspace-Layout löschen", "Layout:", names, 0, False
        )
        if not ok or not name:
            return
        if delete_workspace_layout(name):
            self._refresh_workspace_layout_menu()
            self._set_status(f"Layout gelöscht: {name}")
        else:
            self._set_status(f"Layout nicht gelöscht: {name}")

    def _compress_pdf_images(self):
        if not self._require_pdf("Kompression"):
            return
        src = Path(self.pdf_view.pdf_path)
        dlg = CompressPdfDialog(self, source_path=src)
        if not dlg.exec():
            return
        vals = dlg.values()
        try:
            from ild_pdf import (
                CompressCancelled,
                compress_pdf_as_images,
                downsample_pdf_images,
                format_byte_size,
            )
            from ild_pdf.render import clear_render_cache
            from PySide6.QtWidgets import QApplication, QProgressDialog

            stem_suffix = "_optimized" if vals.get("downsample", True) else "_compressed"
            out = src.with_name(f"{src.stem}{stem_suffix}.pdf")
            path, _ok = QFileDialog.getSaveFileName(
                self,
                "Komprimiertes PDF speichern",
                str(out),
                "PDF (*.pdf)",
            )
            if not path:
                return
            out = Path(path)
            before_bytes = src.stat().st_size if src.is_file() else 0
            kw = dict(
                out_path=out,
                jpeg_quality=vals["jpeg_quality"],
                max_edge=vals["max_edge"],
                render_scale=float(vals.get("render_scale") or 1.5),
            )
            prog = QProgressDialog(
                "PDF wird komprimiert…", "Abbrechen", 0, 1, self
            )
            prog.setWindowTitle("Kompression")
            prog.setWindowModality(Qt.WindowModal)
            prog.setMinimumDuration(0)
            prog.setValue(0)
            prog.show()
            QApplication.processEvents()

            def on_progress(cur: int, total: int) -> bool:
                if prog.wasCanceled():
                    return False
                prog.setMaximum(max(1, int(total)))
                prog.setValue(max(0, int(cur)))
                dpi = vals.get("dpi") or int(round(float(vals.get("render_scale") or 1.5) * 72))
                prog.setLabelText(
                    f"Kompression: Seite {cur}/{total} · ≈{dpi} DPI · Q{vals['jpeg_quality']}"
                )
                QApplication.processEvents()
                return not prog.wasCanceled()

            kw["on_progress"] = on_progress
            try:
                if vals.get("downsample", True):
                    downsample_pdf_images(src, **kw)
                else:
                    compress_pdf_as_images(src, downsample=False, **kw)
            except CompressCancelled:
                prog.close()
                self._set_status("Kompression abgebrochen")
                QMessageBox.information(
                    self, "Kompression", "Abgebrochen — keine Zieldatei geschrieben."
                )
                return
            finally:
                prog.close()
            clear_render_cache(src)
            after_bytes = out.stat().st_size if out.is_file() else 0
            before_s = format_byte_size(before_bytes)
            after_s = format_byte_size(after_bytes)
            savings_pct: float | None = None
            if before_bytes > 0 and after_bytes >= 0:
                savings_pct = (1.0 - (after_bytes / before_bytes)) * 100.0
                size_line = (
                    f"Ersparnis {savings_pct:.1f} % · "
                    f"Vorher: {before_s} → Nachher: {after_s}"
                )
            else:
                size_line = f"Vorher: {before_s} → Nachher: {after_s}"
            # Größenersparnis % in Status — 2.3.2/2.3.3
            savings_suffix = (
                f" · Ersparnis {savings_pct:.1f} %" if savings_pct is not None else ""
            )
            status = f"Komprimiert → {out.name}{savings_suffix} · {before_s} → {after_s}"
            self._set_status(status)
            # Status-% auch für Screenreader announcen — 2.3.5
            self._announce_status_toast(status)
            # Dialog-Checkbox → Settings merken — 2.3.2/2.3.3
            try:
                from instantlensdoc.core.app_settings import set_compress_open_after

                set_compress_open_after(bool(vals.get("open_after")))
            except Exception:
                pass
            QMessageBox.information(
                self,
                "Kompression",
                f"Gespeichert:\n{out}\n\n{size_line}",
            )
            _log.info("PDF compressed: %s (%s)", out, size_line)
            if vals.get("open_after") and out.is_file():
                try:
                    self.open_path(str(out))
                    open_status = (
                        f"Komprimiert geöffnet: {out.name}{savings_suffix}"
                    )
                    self._set_status(open_status)
                    self._announce_status_toast(open_status)
                except Exception as open_err:
                    # Bei Öffnen-Fehler trotzdem Status mit % behalten — 2.3.3
                    _log.warning(
                        "Komprimiertes PDF öffnen fehlgeschlagen: %s", open_err
                    )
                    fail_open = (
                        f"Komprimiert → {out.name}{savings_suffix} · "
                        f"{before_s} → {after_s} · Öffnen fehlgeschlagen"
                    )
                    self._set_status(fail_open)
                    self._announce_status_toast(fail_open)
            try:
                from instantlensdoc.core.telemetry import report_anonymous_usage

                report_anonymous_usage("pdf.compress")
            except Exception:
                pass
        except Exception as e:
            _log.exception("Kompression fehlgeschlagen")
            # Auch bei Fehler Status mit %-Hinweis falls Größen bekannt — 2.3.3
            try:
                err_pct = locals().get("savings_pct")
                err_before = locals().get("before_s")
                err_after = locals().get("after_s")
                if err_pct is not None and err_before and err_after:
                    err_status = (
                        f"Kompression fehlgeschlagen · Ersparnis {err_pct:.1f} % · "
                        f"{err_before} → {err_after}"
                    )
                    self._set_status(err_status)
                    self._announce_status_toast(err_status)
                elif err_before and err_after:
                    err_status = (
                        f"Kompression fehlgeschlagen · {err_before} → {err_after}"
                    )
                    self._set_status(err_status)
                    self._announce_status_toast(err_status)
            except Exception:
                pass
            QMessageBox.warning(self, "Kompression", str(e))

    def _bake_uri_links(self):
        """Sidecar-URL-Links als native PDF-Annotationen backen — 2.3.0."""
        if not self.pdf_view.pdf_path:
            self._feature_dialog("Links backen", "Bitte zuerst ein PDF öffnen.")
            return
        store = getattr(self.pdf_view, "store", None)
        links = []
        try:
            from ild_pdf import sidecar_links_from_annotations

            if store is not None:
                links = sidecar_links_from_annotations(store.annotations)
        except Exception:
            links = []
        if not links:
            self._feature_dialog(
                "Links backen",
                "Keine gültigen URL-Link-Annotationen (http/https) im Sidecar.",
            )
            return
        out = self.pdf_view.bake_uri_links()
        if out:
            self._feature_dialog(
                "Links backen",
                f"Native Link-Annotationen geschrieben:\n{out}",
                object_name="ildBakeLinksDialog",
            )

    def _place_signature_field_menu(self) -> None:
        if not getattr(self.pdf_view, "pdf_path", None):
            self._feature_dialog("Signaturfeld", "Bitte zuerst ein PDF öffnen.")
            return
        try:
            self.pdf_view.place_signature_field()
        except Exception as e:
            self._feature_dialog("Signaturfeld", str(e))
            return
        self._set_status("Signaturfeld: auf die Seite klicken")

    def _insert_signature_image_menu(self) -> None:
        if not getattr(self.pdf_view, "pdf_path", None):
            self._feature_dialog("Signatur", "Bitte zuerst ein PDF öffnen.")
            return
        try:
            self.pdf_view.insert_signature_image()
        except Exception as e:
            self._feature_dialog("Signatur", str(e))

    def _open_command_palette(self):
        """Ctrl+K Schnellaktionen-Palette — 2.3.0."""
        from instantlensdoc.ui.command_palette import CommandPaletteDialog

        dlg = CommandPaletteDialog(self, runner=self._run_palette_command)
        dlg.exec()

    def _run_palette_command(self, cmd_id: str) -> None:
        """Führt einen Command-Palette-Befehl aus — 2.3.0."""
        cid = (cmd_id or "").strip().lower()

        def _about():
            AboutDialog(self).exec()

        def _kb():
            KeyboardHelpDialog(self).exec()

        def _export_menu():
            # HTML-Export als Default-Schnellaktion
            self._export_editor("html")

        def _ann_layer():
            vis = not bool(self.pdf_view.annotations_visible())
            self.pdf_view.set_annotations_visible(vis)
            if hasattr(self, "_ann_layer_action"):
                self._ann_layer_action.setChecked(vis)

        mapping = {
            "open": self.open_dialog,
            "save": self.save_doc,
            "save_all": self.save_all_docs,
            "search": lambda: self.sidebar.setFocus()
            if hasattr(self, "sidebar")
            else None,
            "multi_search": self._open_multi_doc_search,
            "find_replace": self._find_replace,
            "auto_format": self._auto_format_document,
            "auto_toc": self._update_auto_toc,
            "auto_lof": self._update_figure_list,
            "auto_index": self._update_index,
            "save_as": self.save_as,
            "toggle_bold": self._toggle_bold,
            "toggle_italic": self._toggle_italic,
            "toggle_underline": self._toggle_underline,
            "toggle_strike": self._toggle_strike,
            "select_all": self._select_all_annotations_on_page,
            "clear_formatting": self._clear_formatting,
            "bullet_list": lambda: self._toggle_list(ordered=False),
            "numbered_list": lambda: self._toggle_list(ordered=True),
            "insert_break": lambda: self._insert_break("line"),
            "font": self._choose_font,
            "font_color": self._choose_font_color,
            "highlight_color": self._choose_highlight_color,
            "para_align_left": lambda: self._set_paragraph_alignment("left"),
            "para_align_center": lambda: self._set_paragraph_alignment("center"),
            "para_align_right": lambda: self._set_paragraph_alignment("right"),
            "para_align_justify": lambda: self._set_paragraph_alignment("justify"),
            "paragraph": self._paragraph_format_dialog,
            "list_glyph": self._change_list_glyph_dialog,
            "header_footer": self._header_footer_dialog,
            "field_token": self._field_token_dialog,
            "toggle_rulers": lambda: self._toggle_rulers(
                not getattr(self.pdf_view, "_show_rulers", False)
            ),
            "toggle_grid": lambda: self._toggle_alignment_grid(
                not getattr(self.pdf_view, "_show_alignment_grid", False)
            ),
            "toggle_satzspiegel": lambda: self._toggle_satzspiegel(
                not getattr(self.pdf_view, "_show_satzspiegel", False)
            ),
            "apply_master_page": self._apply_master_page_dialog,
            "add_column_frames": self._add_column_frames,
            "move_frame": self._move_frame_dialog,
            "resize_frame": self._resize_frame_dialog,
            "typo_tracking": lambda: self._set_typography(tracking=50.0),
            "typo_leading": lambda: self._set_typography(leading=1.5),
            "drop_cap": self._apply_drop_cap,
            "hyphenate_de": lambda: self._hyphenate_document("de"),
            "hyphenate_en": lambda: self._hyphenate_document("en"),
            "hyphenate_fr": lambda: self._hyphenate_document("fr"),
            "hyphenate_ru": lambda: self._hyphenate_document("ru"),
            "hyphenate_es": lambda: self._hyphenate_document("es"),
            "hyphenate_zh": lambda: self._hyphenate_document("zh"),
            "hyphenate_pt": lambda: self._hyphenate_document("pt"),
            "hyphenate_ar": lambda: self._hyphenate_document("ar"),
            "hyphenate_it": lambda: self._hyphenate_document("it"),
            "insert_table": self._insert_table_dialog,
            "format_table": self._format_table_dialog,
            "sort_table": self._sort_table_dialog,
            "import_table_data": self._import_table_data,
            "export_xlsx": lambda: self._export_editor("xlsx"),
            "export_rtf": lambda: self._export_editor("rtf"),
            "export_epub": lambda: self._export_editor("epub"),
            "export_pptx": lambda: self._export_editor("pptx"),
            "insert_hyperlink": self._insert_hyperlink_dialog,
            "insert_shape": self._insert_shape_frame,
            "insert_video": self._insert_video_placeholder,
            "scale_image": self._scale_image_frame,
            "crop_image": self._crop_image_frame,
            "export_pdfx": self._export_pdfx,
            "preflight": self._run_preflight,
            "apply_bleed": self._apply_bleed_dialog,
            "page_layout": self._show_page_layout_dialog,
            "doc_layers": self._show_doc_layers,
            "compare_pdfs": self._compare_pdfs,
            "book_layout": lambda: self._toggle_book_layout(
                not self.pdf_view.book_layout_enabled()
            ),
            "page_by_page": lambda: self._toggle_page_by_page(
                not self.pdf_view.page_by_page_enabled()
            ),
            "toggle_doc_tabs": lambda: self._toggle_doc_tabs(
                not (
                    getattr(self, "doc_tab_bar", None) is not None
                    and self.doc_tab_bar.isVisible()
                )
            ),
            "toggle_ribbon": lambda: self._toggle_ribbon(
                not (
                    getattr(self, "ribbon_bar", None) is not None
                    and self.ribbon_bar.isVisible()
                )
            ),
            "chrome_klassisch": lambda: self._set_chrome_mode("klassisch"),
            "chrome_ribbon": lambda: self._set_chrome_mode("ribbon"),
            "chrome_kombiniert": lambda: self._set_chrome_mode("kombiniert"),
            "styles_pane": self._toggle_style_pane,
            "spellcheck": self._check_spelling,
            "spell_suggestions": self._show_spell_suggestions,
            "autocorrect_toggle": self._toggle_autocorrect,
            "detach_window": self._detach_current_document,
            "review_mode": self._show_review_dialog,
            "doc_comments": self._show_comments_dialog,
            "shared_review": self._show_shared_review_dialog,
            "version_history": self._show_version_history_dialog,
            "mail_merge": self._run_mail_merge_dialog,
            "batch_pdf": self._batch_convert,
            "esign": self._run_esign_dialog,
            "text_wrap": self._set_image_text_wrap,
            "ocr_page": self._run_ocr,
            "ocr_pdf": self._run_ocr_document,
            "ocr_region": self._run_ocr_region,
            "ocr_word_suite": self._ocr_word_suite_action,
            "ocr_handwriting": self._run_ocr_handwriting,
            "settings_ui_lang": self._settings,
            "ki_document_wizard": self._ki_document_wizard_action,
            "doc_tags": self._edit_doc_tags,
            "true_redact": lambda: self.pdf_view.apply_true_redactions()
            if hasattr(self.pdf_view, "apply_true_redactions")
            else None,
            "selection_redact": lambda: self.pdf_view.redactions_from_text_selection()
            if hasattr(self.pdf_view, "redactions_from_text_selection")
            else None,
            "page_manage": lambda: self.pdf_view.page_manage_dialog()
            if hasattr(self.pdf_view, "page_manage_dialog")
            else None,
            "scan_import": self._run_scan_import,
            "devices": self._show_devices_dialog,
            "inline_text_edit": lambda: self.pdf_view.inline_text_edit_dialog()
            if hasattr(self.pdf_view, "inline_text_edit_dialog")
            else None,
            "selection_text_edit": lambda: self.pdf_view.edit_inline_text_selection()
            if hasattr(self.pdf_view, "edit_inline_text_selection")
            else None,
            "object_edit": lambda: self.pdf_view.object_edit_dialog()
            if hasattr(self.pdf_view, "object_edit_dialog")
            else None,
            "object_transform": lambda: self.pdf_view.object_transform_dialog()
            if hasattr(self.pdf_view, "object_transform_dialog")
            else None,
            "form_fields": lambda: self.pdf_view.form_field_dialog()
            if hasattr(self.pdf_view, "form_field_dialog")
            else None,
            "form_field_create": lambda: self.pdf_view.form_field_create_dialog()
            if hasattr(self.pdf_view, "form_field_create_dialog")
            else None,
            "form_field_detect": lambda: self.pdf_view.form_field_detect_dialog()
            if hasattr(self.pdf_view, "form_field_detect_dialog")
            else None,
            "pdf_security": self._pdf_security_dialog,
            "pdf_encrypt": self._set_pdf_password,
            "pdf_decrypt": self._remove_pdf_password,
            "paragraph_highlight": lambda: self.pdf_view._toggle_paragraph_highlight(True)
            if hasattr(self.pdf_view, "_toggle_paragraph_highlight")
            else None,
            "stamp_pick": lambda: self.pdf_view._set_tool(
                __import__("ild_pdf.annotate", fromlist=["AnnotationType"]).AnnotationType.STAMP
            )
            if hasattr(self.pdf_view, "_set_tool")
            else None,
            "export": _export_menu,
            "export_page_images": lambda: self.pdf_view.export_pages_as_images()
            if hasattr(self.pdf_view, "export_pages_as_images")
            else None,
            "compress": self._compress_pdf_images,
            "bake_links": self._bake_uri_links,
            "page_labels": lambda: self.pdf_view.edit_page_labels()
            if hasattr(self.pdf_view, "edit_page_labels")
            else None,
            "doc_history": lambda: self.pdf_view.show_doc_history()
            if hasattr(self.pdf_view, "show_doc_history")
            else None,
            "goto_page": self._goto_page,
            "settings": self._settings,
            "ann_templates": self._open_ann_templates,
            "keyboard_help": _kb,
            "about": _about,
            "theme_cycle": self._cycle_theme_mode,
            "ann_layer": _ann_layer,
        }
        fn = mapping.get(cid)
        if callable(fn):
            try:
                fn()
            except Exception as e:
                self._set_status(f"Schnellaktion „{cid}“: {e}")
        else:
            self._set_status(f"Schnellaktion unbekannt: {cid}")

    def _settings(self):
        if SettingsDialog(self).exec():
            sync_from_settings()
            apply_ui_language(self)  # Persistierte Sprache + Retranslate/RTL — 2.6.18
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
            self._autosave_enabled = bool(get_autosave_enabled())
            self._autosave_timer.setInterval(get_autosave_interval_sec() * 1000)
            debounce_ms = self.pdf_view.apply_sidecar_debounce_ms(
                get_sidecar_save_debounce_ms()
            )
            self.pdf_view.apply_settings_colors()
            self.pdf_view.apply_toolbar_groups()
            if self.pdf_view.pdf_path:
                self._refresh_thumbs()
            as_label = (
                f"Autosave {get_autosave_interval_sec()}s"
                if get_autosave_enabled()
                else "Autosave aus"
            )
            self._set_status(
                f"Einstellungen gespeichert · {as_label} · "
                f"Sidecar-Debounce {debounce_ms} ms"
            )

    def _edit_pdf_metadata(self):
        if not self._require_pdf("Metadaten"):
            return
        # Dialog schon offen → Fokus/raise statt zweites Fenster — 1.5.5
        existing = getattr(self, "_meta_dialog", None)
        if existing is not None and existing.isVisible():
            existing.raise_()
            existing.activateWindow()
            return
        dlg = MetadataDialog(self.pdf_view.pdf_path, self)
        self._meta_dialog = dlg
        if dlg.exec():
            # Erfolgs-Toast: Dauer OCR-Settings; Klick→Dialog; A11y — 1.5.5
            from instantlensdoc.core.app_settings import get_ocr_defaults_toast_sec

            toast = getattr(dlg, "last_toast", "") or "Metadaten gespeichert"
            self._meta_toast_active = True
            self._announce_status_toast(toast)
            try:
                ms = max(1, int(get_ocr_defaults_toast_sec())) * 1000
            except Exception:
                ms = 2000
            self.statusBar().showMessage(toast, ms)
            self.statusBar().setToolTip(
                "Klick öffnet Metadaten-Dialog erneut — 1.5.5"
            )
            self.statusBar().setCursor(Qt.PointingHandCursor)

            def _clear_meta_toast_flag() -> None:
                cur = self.statusBar().currentMessage() or ""
                if "Metadaten gespeichert" not in cur:
                    self._meta_toast_active = False
                    if self.statusBar().toolTip().startswith("Klick öffnet Metadaten"):
                        self.statusBar().setToolTip("")
                        self.statusBar().unsetCursor()

            from PySide6.QtCore import QTimer

            QTimer.singleShot(ms + 50, _clear_meta_toast_flag)

    def _edit_pdf_form_fields(self):
        if not self._require_pdf("Formularfelder"):
            return
        # 2.6.6: Dialog auch ohne bestehende Felder (anlegen/erkennen)
        page = int(getattr(self.pdf_view, "page_index", 0) or 0)
        if FormFieldsDialog(self.pdf_view.pdf_path, self, page_index=page).exec():
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_view.pdf_path)
            self.pdf_view.refresh()
            self._refresh_form_fields()
            self._set_status("Formularfelder gespeichert")
        else:
            try:
                from ild_pdf.render import clear_render_cache

                clear_render_cache(self.pdf_view.pdf_path)
            except Exception:
                pass
            self.pdf_view.refresh()
            self._refresh_form_fields()

    def _pdf_attachments(self):
        if not self._require_pdf("Anhänge"):
            return
        dlg = AttachmentsDialog(self.pdf_view.pdf_path, self)
        dlg.exec()
        if getattr(dlg, "changed", False):
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_view.pdf_path)
            self.pdf_view.refresh()
            self._set_status("PDF-Anhänge aktualisiert")

    def _stamp_image_library(self):
        """Eigene Stempel-Bilder verwalten / Sidecar-Stempel setzen — 1.9.0."""
        from instantlensdoc.ui.stamp_library_dialog import StampLibraryDialog

        pdf = self.pdf_view.pdf_path
        page = int(getattr(self.pdf_view, "page_index", 0) or 0)
        dlg = StampLibraryDialog(
            self,
            pdf_path=pdf,
            page_index=page,
            allow_place=bool(pdf),
        )
        if dlg.exec() and dlg.placed_path:
            self.pdf_view.reload_annotations()
            self.pdf_view.refresh()
            self._set_status(f"Stempel-Bild gesetzt: {dlg.placed_path.name}")

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
            if bool(getattr(self, "_loading_document", False)):
                # Während open_path ist der Editor-Inhalt noch das alte Dokument
                return bool(self.doc.dirty)
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
        if self.doc.path and self.sidebar.is_document_pinned(str(self.doc.path)):
            self._set_status(
                f"Tab angeheftet: {Path(self.doc.path).name} — zuerst lösen (Rechtsklick)"
            )
            return
        if not self._confirm_close_current(allow_discard=True):
            return
        path = str(self.doc.path) if self.doc.path else None
        t0 = time.perf_counter()
        remaining: list[str] = []
        try:
            # Tab-Eintrag zuerst entfernen — bricht die Teardown-Kette ab, bleibt die
            # Tab-Leiste trotzdem nicht stehen (finally synchronisiert) — 2.6.54
            if path:
                self.sidebar.remove_document(path)
            remaining = list(self.sidebar.document_paths())
            self._release_current_document(path)
        finally:
            self._refresh_doc_tab_bar()
            try:
                self.setWindowTitle(self._app_title())
                self._update_doc_status()
                self._sync_preview_readonly_banner()
                self._update_unsaved_status()
            except Exception as e:
                _log.debug("close_current_tab UI-Sync: %s", e)
        self._last_tab_close_ms = (time.perf_counter() - t0) * 1000.0
        _log.debug("Tab geschlossen in %.1f ms: %s", self._last_tab_close_ms, path)
        if remaining:
            nxt = remaining[0]
            # Nachbar-Tab erst im nächsten Event-Loop-Durchlauf laden: Close kehrt
            # sofort zurück, Tab-Leiste/Status sind bereits aktualisiert — 2.6.54
            self._set_status(f"Geschlossen — wechsle zu {Path(nxt).name}…")
            self._activate_tab_deferred(nxt, status=f"Geschlossen — gewechselt zu {Path(nxt).name}")
        else:
            self._show_welcome_if_empty()
            self._set_status("Dokument geschlossen")
        try:
            self._save_session()
        except Exception:
            pass

    def _release_current_document(self, path: str | None = None) -> None:
        """Aktuelles Dokument aus Viewer/Editor/Sidebar lösen — nie blockierend — 2.6.54.

        Jeder Schritt ist einzeln abgesichert: Thumb-Lazy-Timer stoppen, Viewer
        ``unload`` (Dokument-Token erhöhen → späte Worker-Ergebnisse verworfen),
        Editor leeren, Sidebar-Panels leeren, Caches dieses Tabs freigeben. Es wird
        auf keinen Thread gewartet und kein PDFium aufgerufen.
        """
        key = self._path_key(path) if path else None
        if key is None and self.doc is not None and self.doc.path:
            key = self._path_key(self.doc.path)
        self.doc = None
        try:
            self._stop_thumb_lazy()
        except Exception:
            pass
        try:
            self.pdf_view.unload()
        except Exception as e:
            _log.warning("PdfViewer.unload: %s", e)
            try:
                self.pdf_view.pdf_path = None
                self.pdf_view.store = None
                self.pdf_view.page_count = 0
                self.pdf_view.page_index = 0
            except Exception:
                pass
        try:
            self.editor.blockSignals(True)
            try:
                self.editor.setPlainText("")
            finally:
                self.editor.blockSignals(False)
        except Exception:
            pass
        for fn in (
            self.sidebar.clear_thumbs,
            self.sidebar.clear_annotations,
            lambda: self.sidebar.set_marks([]),
            lambda: self.sidebar.set_outline([]),
            self.sidebar.clear_form_fields,
            self.sidebar.clear_page_favorites,
        ):
            try:
                fn()
            except Exception:
                pass
        if key:
            self._unsaved_paths.discard(key)
            self._tab_view_state.pop(key, None)
            self._doc_cache.pop(key, None)
        self._page_size_cache.clear()

    def _forget_tab(self, path: str | None) -> None:
        """Tab-bezogene Zustände eines (nicht aktiven) Pfads verwerfen — 2.6.54."""
        key = self._path_key(path) if path else None
        if not key:
            return
        self._unsaved_paths.discard(key)
        self._tab_view_state.pop(key, None)
        self._doc_cache.pop(key, None)

    def _activate_tab_deferred(self, path: str, *, status: str | None = None) -> None:
        """Nachbar-Tab nach Close im nächsten Event-Loop-Durchlauf aktivieren — 2.6.54.

        Guard: Wurde der Tab inzwischen ebenfalls geschlossen oder ein anderes
        Dokument geöffnet, wird der erste verbliebene Tab genommen bzw. die
        Willkommensseite gezeigt.
        """
        want = str(Path(path)) if path else ""

        def _run() -> None:
            if self.doc is not None:
                return
            paths = [str(Path(p)) for p in self.sidebar.document_paths()]
            target = want if want in paths else (paths[0] if paths else "")
            if not target or not Path(target).is_file():
                if target:
                    try:
                        self.sidebar.remove_document(target)
                    except Exception:
                        pass
                    self._forget_tab(target)
                    self._refresh_doc_tab_bar()
                    paths = [str(Path(p)) for p in self.sidebar.document_paths()]
                    if paths:
                        self._activate_tab_deferred(paths[0], status=status)
                        return
                self._show_welcome_if_empty()
                return
            try:
                self.open_path(target)
            except Exception as e:
                _log.warning("Tab nach Close aktivieren: %s", e)
                return
            if status and str(Path(target)) == want:
                self._set_status(status)

        QTimer.singleShot(0, _run)

    def _on_document_pin_toggled(self, path: str, pinned: bool) -> None:
        """Tab anheften/lösen (0.9.2) — visueller Indikator + Schutz vor Alle schließen."""
        if not path:
            return
        ok = self.sidebar.set_document_pinned(path, bool(pinned))
        if not ok:
            self._set_status("Tab nicht gefunden")
            return
        name = Path(path).name
        if pinned:
            self._set_status(f"Tab angeheftet: {name} — bleibt bei „Alle schließen“")
        else:
            self._set_status(f"Tab gelöst: {name}")
        self._refresh_document_dirty_labels()

        self._refresh_doc_tab_bar()

    def close_tab_path(self, path: str) -> None:
        """Sidebar-Tab schließen (Mittelklick / Kontextmenü) — dirty → Speichern-Dialog."""
        target = str(Path(path)) if path else ""
        if not target:
            self._set_status("Kein Tab zum Schließen")
            return
        if self.sidebar.is_document_pinned(target):
            self._set_status(
                f"Tab angeheftet: {Path(target).name} — zuerst lösen (Rechtsklick)"
            )
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
        try:
            if not self.sidebar.remove_document(target):
                self._set_status("Tab nicht in der Liste")
                return
            self._forget_tab(target)
        finally:
            self._refresh_doc_tab_bar()
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
        """Alle Sidebar-Dokumente schließen außer dem aktuellen (angeheftete bleiben)."""
        if not self.doc:
            self._set_status("Kein Dokument geöffnet")
            return
        keep = str(self.doc.path) if self.doc.path else None
        paths = list(self.sidebar.document_paths()) if hasattr(self.sidebar, "document_paths") else []
        if not paths:
            self._set_status("Keine weiteren Tabs")
            return
        closed = 0
        skipped_pin = 0
        try:
            for p in paths:
                if keep and str(Path(str(p))) == str(Path(keep)):
                    continue
                if self.sidebar.is_document_pinned(str(p)):
                    skipped_pin += 1
                    continue
                self.sidebar.remove_document(p)
                self._forget_tab(p)
                closed += 1
        finally:
            self._refresh_doc_tab_bar()
        if closed == 0:
            if skipped_pin:
                self._set_status(
                    f"Keine Tabs geschlossen — {skipped_pin} angeheftet"
                )
            else:
                self._set_status("Keine anderen Tabs zum Schließen")
            return
        try:
            self._save_session()
        except Exception:
            pass
        self._update_unsaved_status()
        self._refresh_document_dirty_labels()
        extra = f" · {skipped_pin} angeheftet" if skipped_pin else ""
        self._set_status(
            f"{closed} andere Tab(s) geschlossen — aktuell bleibt offen{extra}"
        )

    def _close_tabs_by_paths(self, targets: list[str], *, status_ok: str) -> int:
        """Hilfsfunktion: Tabs entfernen (ohne Dirty-Dialog, wie close_other_tabs)."""
        closed = 0
        skipped_pin = 0
        try:
            for p in targets:
                if self.sidebar.is_document_pinned(str(p)):
                    skipped_pin += 1
                    continue
                self.sidebar.remove_document(p)
                self._forget_tab(p)
                closed += 1
        finally:
            self._refresh_doc_tab_bar()
        if closed == 0:
            return 0
        try:
            self._save_session()
        except Exception:
            pass
        self._update_unsaved_status()
        self._refresh_document_dirty_labels()
        msg = status_ok.format(n=closed)
        if skipped_pin:
            msg = f"{msg} · {skipped_pin} angeheftet"
        self._set_status(msg)
        return closed

    def close_tabs_left_of(self, pivot_path: str) -> None:
        """Alle Tabs links vom angegebenen Pfad schließen (Kontextmenü)."""
        pivot = str(Path(pivot_path)) if pivot_path else ""
        paths = list(self.sidebar.document_paths()) if hasattr(self.sidebar, "document_paths") else []
        if not pivot or not paths:
            self._feature_dialog(
                "Tabs schließen",
                "Keine Tabs links zum Schließen.",
                object_name="ildCloseTabsDialog",
            )
            return
        idx = -1
        for i, p in enumerate(paths):
            if str(Path(str(p))) == pivot:
                idx = i
                break
        if idx <= 0:
            self._feature_dialog(
                "Tabs schließen",
                "Keine Tabs links zum Schließen.",
                object_name="ildCloseTabsDialog",
            )
            return
        cur = str(Path(self.doc.path)) if self.doc and self.doc.path else None
        # Wenn aktuelles Doc unter den zu schließenden liegt → zuerst Pivot aktivieren
        left = [str(Path(str(p))) for p in paths[:idx]]
        if cur and any(str(Path(c)) == str(Path(cur)) for c in left):
            if Path(pivot).is_file():
                self.open_path(pivot)
        n = self._close_tabs_by_paths(
            left, status_ok="{n} Tab(s) links geschlossen"
        )
        if n == 0:
            self._feature_dialog(
                "Tabs schließen",
                "Keine Tabs links zum Schließen.",
                object_name="ildCloseTabsDialog",
            )

    def close_tabs_right_of(self, pivot_path: str) -> None:
        """Alle Tabs rechts vom angegebenen Pfad schließen (Kontextmenü)."""
        pivot = str(Path(pivot_path)) if pivot_path else ""
        paths = list(self.sidebar.document_paths()) if hasattr(self.sidebar, "document_paths") else []
        if not pivot or not paths:
            self._feature_dialog(
                "Tabs schließen",
                "Keine Tabs rechts zum Schließen.",
                object_name="ildCloseTabsDialog",
            )
            return
        idx = -1
        for i, p in enumerate(paths):
            if str(Path(str(p))) == pivot:
                idx = i
                break
        if idx < 0 or idx >= len(paths) - 1:
            self._feature_dialog(
                "Tabs schließen",
                "Keine Tabs rechts zum Schließen.",
                object_name="ildCloseTabsDialog",
            )
            return
        cur = str(Path(self.doc.path)) if self.doc and self.doc.path else None
        right = [str(Path(str(p))) for p in paths[idx + 1 :]]
        if cur and any(str(Path(c)) == str(Path(cur)) for c in right):
            if Path(pivot).is_file():
                self.open_path(pivot)
        n = self._close_tabs_by_paths(
            right, status_ok="{n} Tab(s) rechts geschlossen"
        )
        if n == 0:
            self._feature_dialog(
                "Tabs schließen",
                "Keine Tabs rechts zum Schließen.",
                object_name="ildCloseTabsDialog",
            )

    def close_tabs_left_of_current(self) -> None:
        try:
            if not self.doc or not self.doc.path:
                self._feature_dialog(
                    "Tabs schließen",
                    "Kein Dokument geöffnet — keine Tabs links zum Schließen.",
                    object_name="ildCloseTabsDialog",
                )
                return
            self.close_tabs_left_of(str(self.doc.path))
        except Exception as e:
            self._feature_dialog(
                "Tabs schließen",
                str(e) or "Keine Tabs links zum Schließen.",
                object_name="ildCloseTabsDialog",
            )

    def close_tabs_right_of_current(self) -> None:
        if not self.doc or not self.doc.path:
            self._feature_dialog(
                "Tabs schließen",
                "Kein Dokument geöffnet — keine Tabs rechts zum Schließen.",
                object_name="ildCloseTabsDialog",
            )
            return
        self.close_tabs_right_of(str(self.doc.path))

    def close_all_tabs(self) -> None:
        """
        Alle nicht angehefteten Sidebar-Tabs schließen (0.9.2: Pin-Schutz).
        Aktuelles Doc mit Speichern-Dialog — außer es ist angeheftet.
        """
        paths = list(self.sidebar.document_paths()) if hasattr(self.sidebar, "document_paths") else []
        if not paths and not self.doc:
            self._set_status("Keine Tabs zum Schließen")
            return
        pinned_paths = set()
        try:
            pinned_paths = {
                str(Path(p)) for p in self.sidebar.pinned_document_paths()
            }
        except Exception:
            pinned_paths = set()
        cur_path = str(Path(self.doc.path)) if self.doc and self.doc.path else None
        cur_pinned = bool(cur_path and cur_path in pinned_paths)
        t0 = time.perf_counter()
        closed = 0
        kept_pin = 0
        kept: list[str] = []
        try:
            if self.doc and not cur_pinned:
                if not self._confirm_close_current(allow_discard=True):
                    return
                path = str(self.doc.path) if self.doc.path else None
                if path:
                    self.sidebar.remove_document(path)
                self._release_current_document(path)
            remaining = list(self.sidebar.document_paths())
            for p in remaining:
                key_p = str(Path(str(p)))
                if key_p in pinned_paths:
                    kept_pin += 1
                    continue
                self.sidebar.remove_document(p)
                self._forget_tab(p)
                closed += 1
            kept = list(self.sidebar.document_paths())
        finally:
            self._refresh_doc_tab_bar()
        self._last_tab_close_ms = (time.perf_counter() - t0) * 1000.0
        _log.debug("Alle Tabs geschlossen in %.1f ms (%d zu, %d angeheftet)", self._last_tab_close_ms, closed, kept_pin)
        if kept:
            # Angeheftete bleiben — ersten anzeigen falls aktuelles Doc weg (deferred)
            if not self.doc or not self.doc.path:
                self._activate_tab_deferred(kept[0])
            self._update_doc_status()
            try:
                self._save_session()
            except Exception:
                pass
            self._update_unsaved_status()
            self._refresh_document_dirty_labels()
            self._set_status(
                f"{closed} Tab(s) geschlossen · {len(kept)} angeheftet bleiben"
            )
            return
        self.sidebar.clear_thumbs()
        self.sidebar.clear_annotations()
        self.sidebar.set_marks([])
        self.setWindowTitle(self._app_title())
        self._update_doc_status()
        try:
            self._save_session()
        except Exception:
            pass
        self._update_unsaved_status()
        self._refresh_document_dirty_labels()
        self._show_welcome_if_empty()
        self._set_status("Alle Tabs geschlossen")

    def _pdf_page_size(self):
        if not self._require_pdf("Seitengröße"):
            return
        if PageSizeDialog(self.pdf_view.pdf_path, self.pdf_view.page_index, self).exec():
            from ild_pdf.render import clear_render_cache

            clear_render_cache(self.pdf_view.pdf_path)
            self.pdf_view.refresh()
            self._set_status("Seitengröße/Crop aktualisiert")

    def _check_updates(self, *, silent: bool = False, force: bool = False):
        from instantlensdoc.core.i18n import get_lang
        from instantlensdoc.core.update_check import (
            check_for_updates,
            check_local_version,
            format_checked_at,
            format_reference_source_tooltip,
        )

        lang = get_lang()
        # Primär lokal; Online optional; Offline → Status + Zeitstempel — 1.7.3/1.7.4
        try:
            result = check_local_version(record_timestamp=True)
            if not result.newer_available:
                # Online ergänzend; Offline → Status „offline / nicht geprüft“
                result = check_for_updates(allow_network=True)
        except Exception:
            # Nie Fehlerdialog bei Update-Prüfung — Status reicht
            result = check_local_version(record_timestamp=True)

        status_lbl = result.status_label(lang)
        msg = result.message(lang)
        checked = format_checked_at(getattr(result, "checked_at", ""), lang=lang)
        # Tooltip mit Quelle; Pfad für Status-Klick → Editor — 1.7.4/1.7.5
        from instantlensdoc.core.update_check import find_embedded_version_file

        ref_path, ref_label = find_embedded_version_file()
        src = getattr(result, "reference_source", "") or (ref_label or "")
        self._update_status_source_tip = format_reference_source_tooltip(
            src, lang=lang
        )
        self._update_status_reference_path = ref_path
        self._set_status(f"Update: {status_lbl} — letzter Check: {checked}")

        # Dismiss bis nächste Version — 1.7.1
        dismissed = get_update_dismissed_version()
        ref = str(result.remote_version or "").strip()
        if (
            result.newer_available
            and dismissed
            and ref
            and dismissed == ref
            and not force
        ):
            if silent:
                return
            # Force=False und manuell: trotzdem kurz Status, kein Dialog
            return

        if silent and not result.newer_available:
            return
        if result.newer_available:
            title = "Update — neuer Build Hinweis"
        elif getattr(result, "status", "") == "offline":
            title = "Update — offline / nicht geprüft"
        else:
            title = "Update — aktuell"
        if silent and result.newer_available:
            self._feature_dialog(title, msg, object_name="ildUpdateDialog")
            return
        # Manuell („Jetzt prüfen“): immer schließbarer Dialog
        if result.newer_available:
            if force and dismissed and ref and dismissed != ref:
                set_update_dismissed_version("")
            self._feature_dialog(title, msg, object_name="ildUpdateDialog")
        else:
            if force and dismissed:
                set_update_dismissed_version("")
            self._feature_dialog(title, msg, object_name="ildUpdateDialog")

    def _toggle_favorites_bar(self, checked: bool) -> None:
        from instantlensdoc.core.app_settings import set_favorites_bar_visible

        set_favorites_bar_visible(bool(checked))
        if getattr(self, "favorites_bar", None) is not None:
            self.favorites_bar.setVisible(bool(checked) and not self._presentation_active)
        if getattr(self, "_favorites_bar_action", None) is not None:
            self._favorites_bar_action.blockSignals(True)
            self._favorites_bar_action.setChecked(bool(checked))
            self._favorites_bar_action.blockSignals(False)
        if checked:
            self._refresh_favorites_bar()

    def _refresh_favorites_bar(self) -> None:
        """Globale ildfav-v1 Favoriten; fehlende grau; Drag-Reorder — 1.7.1."""
        from instantlensdoc.core.global_favorites import load_global_favorites

        lst = getattr(self, "favorites_list", None)
        if lst is None:
            return
        lst.blockSignals(True)
        lst.clear()
        self._fav_bar_buttons = []
        favs = load_global_favorites()
        if not favs:
            empty = QListWidgetItem("— keine —")
            empty.setFlags(Qt.NoItemFlags)
            empty.setForeground(QColor("#888888"))
            empty.setToolTip("PDF → Zur Lesezeichen-Leiste hinzufügen (Ctrl+Alt+Shift+B)")
            lst.addItem(empty)
            lst.blockSignals(False)
            return
        for fav in favs:
            label = fav.display_label()
            if len(label) > 28:
                label = label[:25] + "…"
            exists = Path(fav.path).is_file()
            if not exists:
                label = f"⚠ {label}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, (fav.path, fav.page))
            tip = f"{fav.path}\nSeite {fav.page + 1}"
            if not exists:
                tip += "\n(Datei fehlt — Rechtsklick → Entfernen)"
                item.setForeground(QColor("#888888"))
                item.setToolTip(tip)
            else:
                item.setToolTip(tip)
            lst.addItem(item)
            self._fav_bar_buttons.append(item)
        lst.blockSignals(False)

    def _on_global_fav_item_clicked(self, item) -> None:
        if item is None:
            return
        data = item.data(Qt.UserRole)
        if not isinstance(data, (tuple, list)) or len(data) < 2:
            return
        path, page = str(data[0]), int(data[1])
        if not Path(path).is_file():
            ask = QMessageBox.question(
                self,
                "Lesezeichen-Leiste",
                f"Datei nicht gefunden:\n{path}\n\nFavorit entfernen?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if ask == QMessageBox.Yes:
                from instantlensdoc.core.global_favorites import remove_global_favorite

                remove_global_favorite(path, page)
                self._refresh_favorites_bar()
                self._set_status("Fehlender Favorit entfernt")
            return
        self._jump_global_favorite(path, page)

    def _on_global_fav_item_double_clicked(self, item) -> None:
        """Doppelklick: Favoriten-Label editieren — 1.7.3."""
        if item is None:
            return
        data = item.data(Qt.UserRole)
        if not isinstance(data, (tuple, list)) or len(data) < 2:
            return
        path, page = str(data[0]), int(data[1])
        self._edit_global_favorite_label(path, page)

    def _on_global_favorites_reordered(self, order: list) -> None:
        from instantlensdoc.core.global_favorites import reorder_global_favorites

        reorder_global_favorites(order)
        self._refresh_favorites_bar()
        self._set_status("Favoriten-Reihenfolge gespeichert")

    def _on_global_fav_list_context(self, pos) -> None:
        lst = getattr(self, "favorites_list", None)
        if lst is None:
            return
        item = lst.itemAt(pos)
        if item is None:
            return
        data = item.data(Qt.UserRole)
        if not isinstance(data, (tuple, list)) or len(data) < 2:
            return
        path, page = str(data[0]), int(data[1])
        self._global_fav_context(lst, path, page, pos)

    def _global_fav_context(self, widget, path: str, page: int, pos) -> None:
        menu = QMenu(self)
        exists = Path(path).is_file()
        act_go = menu.addAction("Springen")
        act_go.setEnabled(exists)
        act_tab = menu.addAction("In neuem Tab öffnen")
        act_tab.setEnabled(exists)
        act_label = menu.addAction("Label bearbeiten…")
        act_rm = menu.addAction("Aus Leiste entfernen")
        if not exists:
            act_rm.setText("Fehlende Datei entfernen")
        chosen = menu.exec(widget.mapToGlobal(pos))
        if chosen is act_go:
            self._jump_global_favorite(path, page)
        elif chosen is act_tab:
            self._jump_global_favorite(path, page, force_open=True)
        elif chosen is act_label:
            self._edit_global_favorite_label(path, page)
        elif chosen is act_rm:
            from instantlensdoc.core.global_favorites import remove_global_favorite

            remove_global_favorite(path, page)
            self._refresh_favorites_bar()
            self._set_status("Favorit aus Leiste entfernt")

    def _focus_favorites_list_item(self, path: str, page: int) -> None:
        """Fokus zurück auf Favoriten-Liste + Eintrag — 1.7.4."""
        lst = getattr(self, "favorites_list", None)
        if lst is None:
            return
        try:
            lst.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass
        for i in range(lst.count()):
            item = lst.item(i)
            if item is None:
                continue
            data = item.data(Qt.UserRole)
            if not isinstance(data, (tuple, list)) or len(data) < 2:
                continue
            try:
                same = Path(str(data[0])).resolve() == Path(path).resolve()
            except OSError:
                same = str(data[0]) == str(path)
            if same and int(data[1]) == int(page):
                lst.setCurrentItem(item)
                break

    def _edit_global_favorite_label(self, path: str, page: int) -> None:
        """Favoriten-Label: Enter bestätigt; leer → Dateiname ohne extra Schritt — 1.7.5."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit

        from instantlensdoc.core.global_favorites import (
            load_global_favorites,
            set_global_favorite_label,
        )

        fallback = Path(path).name
        current = ""
        for fav in load_global_favorites():
            try:
                same = Path(fav.path).resolve() == Path(path).resolve()
            except OSError:
                same = str(Path(fav.path)) == str(Path(path))
            if same:
                # Echtes Label (kann leer sein) — Dateiname erst bei Enter — 1.7.5
                current = (fav.label or "").strip()
                break

        dlg = QDialog(self)
        dlg.setWindowTitle("Favoriten-Label")
        form = QFormLayout(dlg)
        edit = QLineEdit(current)
        edit.setClearButtonEnabled(True)
        edit.setPlaceholderText(fallback)
        edit.setToolTip(
            "Enter bestätigt Edit; Esc bricht ab (Fokus zurück auf Liste); "
            "leerer Edit → Dateiname ohne extra Schritt — 1.7.5"
        )
        form.addRow(
            "Anzeigename (Enter = OK / leer = Dateiname; Esc = Abbrechen):", edit
        )
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)
        # Enter im Feld bestätigt (Default-Button); Esc rejectet — 1.7.4/1.7.5
        buttons.button(QDialogButtonBox.Ok).setDefault(True)
        buttons.button(QDialogButtonBox.Ok).setAutoDefault(True)
        edit.setFocus(Qt.OtherFocusReason)
        if current:
            edit.selectAll()
        ok = dlg.exec() == QDialog.Accepted
        if not ok:
            self._set_status("Favoriten-Label: abgebrochen (Esc)")
            QTimer.singleShot(0, lambda: self._focus_favorites_list_item(path, page))
            return
        text = (edit.text() or "").strip()
        # Leerer Edit → Dateiname direkt setzen (kein Extra-Schritt) — 1.7.5
        if not text:
            text = fallback
        set_global_favorite_label(path, text, page=page)
        self._refresh_favorites_bar()
        self._set_status(f"Favoriten-Label: {text[:40]}")
        QTimer.singleShot(0, lambda: self._focus_favorites_list_item(path, page))

    def _export_global_favorites_json(self) -> None:
        from instantlensdoc.core.global_favorites import export_global_favorites_json

        last_dir = get_last_export_dir()
        start = str(Path(dialog_start_dir(last_dir)) / "global_favorites.ildfav.json")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Lesezeichen-Leiste exportieren (ildfav-v1)",
            start,
            "ildfav JSON (*.json)",
        )
        if not path:
            return
        try:
            out = export_global_favorites_json(path)
            set_last_export_dir(str(out))
            remember_recent_dir(str(out))
            self._set_status(f"Globale Favoriten exportiert: {out.name}")
        except Exception as e:
            QMessageBox.critical(self, "Lesezeichen-Leiste", f"Export fehlgeschlagen:\n{e}")

    def _import_global_favorites_json(self) -> None:
        from ild_pdf.annotate import FavoritesImportError
        from instantlensdoc.core.global_favorites import import_global_favorites_json

        last_dir = get_last_export_dir()
        start = str(dialog_start_dir(last_dir))
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Lesezeichen-Leiste importieren (ildfav-v1)",
            start,
            "ildfav JSON (*.json);;Alle Dateien (*)",
        )
        if not path:
            return
        merge = QMessageBox.question(
            self,
            "Lesezeichen-Leiste importieren",
            "Zusammenführen (Ja) oder ersetzen (Nein)?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if merge == QMessageBox.Cancel:
            return
        try:
            favs = import_global_favorites_json(path, merge=(merge == QMessageBox.Yes))
            self._refresh_favorites_bar()
            if getattr(self, "favorites_bar", None) is not None:
                from instantlensdoc.core.app_settings import set_favorites_bar_visible

                set_favorites_bar_visible(True)
                self.favorites_bar.setVisible(True)
            self._set_status(f"Globale Favoriten importiert: {len(favs)} Einträge")
        except FavoritesImportError as e:
            QMessageBox.warning(self, "Lesezeichen-Leiste", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Lesezeichen-Leiste", f"Import fehlgeschlagen:\n{e}")

    def _add_current_to_global_favorites(self) -> None:
        from instantlensdoc.core.global_favorites import add_global_favorite

        if not self._require_pdf("Lesezeichen-Leiste"):
            return
        path = str(Path(self.pdf_view.pdf_path))
        page = int(self.pdf_view.page_index or 0)
        label = Path(path).stem
        add_global_favorite(path, page, label=label)
        if getattr(self, "favorites_bar", None) is not None:
            from instantlensdoc.core.app_settings import set_favorites_bar_visible

            set_favorites_bar_visible(True)
            self.favorites_bar.setVisible(True)
            if getattr(self, "_favorites_bar_action", None) is not None:
                self._favorites_bar_action.blockSignals(True)
                self._favorites_bar_action.setChecked(True)
                self._favorites_bar_action.blockSignals(False)
        self._refresh_favorites_bar()
        self._set_status(f"Favorit: {Path(path).name} · S{page + 1}")
        self._feature_dialog(
            "Lesezeichen-Leiste",
            f"Hinzugefügt: {Path(path).name} · Seite {page + 1}",
            object_name="ildGlobalFavAddedDialog",
        )

    def _jump_global_favorite(
        self, path: str, page: int, *, force_open: bool = False
    ) -> None:
        """Favorit öffnen; force_open = immer open_path (neuer Tab-Fokus) — 1.7.2."""
        p = Path(path)
        if not p.is_file():
            QMessageBox.warning(
                self,
                "Lesezeichen-Leiste",
                f"Datei nicht gefunden:\n{path}",
            )
            return
        same_doc = False
        try:
            cur = self.pdf_view.pdf_path
            if cur and Path(cur).resolve() == p.resolve():
                same_doc = True
        except Exception:
            same_doc = False
        if force_open or not same_doc:
            self.open_path(str(p))
        try:
            if self.pdf_view.pdf_path and self.pdf_view.page_count > 0:
                self.pdf_view.goto_page(
                    max(0, min(int(page), self.pdf_view.page_count - 1))
                )
        except Exception:
            pass
        mode = "Tab" if force_open else "Jump"
        self._set_status(f"Favorit ({mode}) → {p.name} · S{int(page) + 1}")

    def _set_text_pdf_status(self, out: Path, msg: str) -> None:
        """Text→PDF Status: Pfad merken, A11y-Announcement, Klick→Ordner — 1.7.4."""
        self._last_text_pdf_status_path = Path(out)
        self._text_pdf_toast_active = True
        self._set_status(msg)
        self._announce_status_toast(msg)

    def _open_text_pdf_result(self, out: Path, pages: int) -> None:
        """Text→PDF öffnen: kein leeres Sidecar; Status mit Pfad — 1.7.3/1.7.4."""
        side = out.with_suffix(out.suffix + ".ildann.json")
        existed_before = side.is_file()
        self.open_path(str(out))
        # Nach Öffnen: frisch angelegtes leeres Sidecar entfernen
        try:
            if not existed_before and side.is_file():
                raw = side.read_text(encoding="utf-8")
                data = json.loads(raw) if raw.strip() else {}
                anns = data.get("annotations") if isinstance(data, dict) else None
                if not anns:
                    side.unlink(missing_ok=True)
        except Exception:
            pass
        # Store ggf. nochmals vor leerem Write schützen
        try:
            store = getattr(self.pdf_view, "store", None)
            if store is not None and not store.annotations and not store.dirty:
                if side.is_file():
                    pass  # bestehendes Sidecar belassen
        except Exception:
            pass
        self._set_text_pdf_status(
            out, f"Text → PDF geöffnet: {out} ({pages} Seite(n), ohne Sidecar)"
        )

    def _export_text_to_pdf(self) -> None:
        """Text→PDF: Ordner, öffnen ohne Sidecar, Status mit Pfad — 1.7.3."""
        text = ""
        title = "InstantLens Doc"
        if self.stack.currentWidget() is self.editor_pane:
            text = self.editor.toPlainText()
            if self.doc:
                title = self.doc.title or self.doc.display_name
        elif self.doc and self.doc.kind in (
            DocKind.TEXT,
            DocKind.MARKDOWN,
            DocKind.HTML,
            DocKind.DOCX,
        ):
            text = self.doc.text or self.editor.toPlainText()
            title = self.doc.display_name
        else:
            self._feature_dialog(
                "Text → PDF",
                "Bitte einen Text-Tab öffnen (TXT/MD/HTML/DOCX) oder Text eingeben.",
                object_name="ildTextPdfDialog",
            )
            return
        from ild_pdf.text_pdf import page_count_for_text, text_to_pdf
        from instantlensdoc.core.export import resolve_page_size

        page_size = resolve_page_size(None)
        font_size = get_text_pdf_font_size()
        margin = get_text_pdf_margin()
        pages = page_count_for_text(
            text, page_size=page_size, font_size=font_size, margin=margin
        )
        preview = QMessageBox.question(
            self,
            "Text → PDF — Seitenvorschau",
            (
                f"Geschätzte Seitenzahl: {pages}\n"
                f"Schriftgröße: {font_size:g} pt · Rand: {margin:g} pt\n"
                f"(Einstellungen → Text→PDF)\n\nAls PDF speichern?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if preview != QMessageBox.Yes:
            return
        default_name = (self.doc.display_name if self.doc else "export") + ".pdf"
        if "." in default_name and not default_name.lower().endswith(".pdf"):
            default_name = Path(default_name).stem + ".pdf"
        last_dir = get_last_text_pdf_dir() or get_last_export_dir()
        start = str(Path(dialog_start_dir(last_dir)) / default_name)
        path, _ = QFileDialog.getSaveFileName(
            self, "Text → PDF", start, "PDF (*.pdf)"
        )
        if not path:
            return
        if not confirm_overwrite_export(path, self):
            return
        try:
            out = text_to_pdf(
                text,
                path,
                title=title,
                page_size=page_size,
                font_size=font_size,
                margin=margin,
            )
            set_last_text_pdf_dir(str(out))
            set_last_export_dir(str(out))
            remember_recent_dir(str(out))
            self._set_text_pdf_status(
                out, f"Text → PDF gespeichert: {out} ({pages} Seite(n))"
            )
            if get_text_pdf_open_after():
                self._open_text_pdf_result(out, pages)
            else:
                ask = QMessageBox.question(
                    self,
                    "Text → PDF",
                    (
                        f"PDF gespeichert ({pages} Seite(n)):\n{out}\n\n"
                        f"Jetzt öffnen?\n(Optional dauerhaft: Einstellungen → "
                        f"Text→PDF nach Export öffnen)"
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if ask == QMessageBox.Yes:
                    self._open_text_pdf_result(out, pages)
        except Exception as e:
            QMessageBox.critical(self, "Text → PDF", f"Export fehlgeschlagen:\n{e}")

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
        """Schnelldialog: Seitenbereiche z. B. 1-3,5,8-10; DE-Validierung + Vorschau — 1.2.1."""
        if not self._require_pdf("Seitenbereich"):
            return
        from PySide6.QtWidgets import QInputDialog
        from ild_pdf.pages import extract_by_page_spec

        n = self.pdf_view.page_count
        cur = self.pdf_view.page_index + 1
        default_spec = f"{cur}-{n}" if cur < n else str(cur)
        spec, ok = QInputDialog.getText(
            self,
            "Seitenbereich extrahieren",
            f"Seitenbereiche (1…{n}), z. B. 1-3,5,8-10:",
            text=default_spec,
        )
        if not ok:
            return
        spec = (spec or "").strip()
        if not spec:
            return
        one_per = False
        if "," in spec:
            reply = QMessageBox.question(
                self,
                "Seitenbereich",
                "Mehrere Bereiche erkannt.\n\n"
                "Ja = eine Datei pro Bereich (Ordner wählen)\n"
                "Nein = alle Seiten in eine Datei",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.No,
            )
            if reply == QMessageBox.Cancel:
                return
            one_per = reply == QMessageBox.Yes
        src = Path(self.pdf_view.pdf_path)
        if one_per:
            out_dir = QFileDialog.getExistingDirectory(
                self,
                "Ausgabeordner (eine Datei pro Bereich)",
                dialog_start_dir(src.parent),
            )
            if not out_dir:
                return
            remember_recent_dir(out_dir)
            try:
                written = extract_by_page_spec(
                    src, out_dir, spec, one_based=True, one_file_per_range=True
                )
                self._set_status(f"{len(written)} Datei(en) aus „{spec}“ → {out_dir}")
                QMessageBox.information(
                    self,
                    "Seitenbereich",
                    f"{len(written)} Datei(en) erstellt in:\n{out_dir}",
                )
            except Exception as e:
                QMessageBox.critical(self, "Seitenbereich", str(e))
            return
        default = str(
            Path(dialog_start_dir(src.parent)) / f"{src.stem}_extract.pdf"
        )
        dest, _ = QFileDialog.getSaveFileName(self, "Ziel-PDF", default, "PDF (*.pdf)")
        if not dest:
            return
        remember_recent_dir(dest)
        if not dest.lower().endswith(".pdf"):
            dest += ".pdf"
        if not confirm_overwrite_export(dest, self):
            return
        try:
            written = extract_by_page_spec(
                src, dest, spec, one_based=True, one_file_per_range=False
            )
            out = written[0] if written else dest
            self._set_status(f"Seitenbereich {spec} → {Path(out).name}")
            QMessageBox.information(self, "Seitenbereich", f"Gespeichert:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Seitenbereich", str(e))

    def _split_into_single_page_pdfs(self):
        """Jede Seite des aktuellen PDFs als eigene Datei exportieren."""
        if not self._require_pdf("Einzel-PDFs"):
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

    def _batch_rename_tabs(self):
        """Offene Tabs mit Template {stem}_{n} umbenennen + Vorschau — 1.4.0."""
        paths = list(self.sidebar.document_paths()) if hasattr(self.sidebar, "document_paths") else []
        if not paths:
            self._set_status("Keine offenen Tabs zum Umbenennen")
            return
        dlg = BatchRenameDialog(self, paths=paths)
        if dlg.exec() != QDialog.Accepted and not dlg.renamed:
            return
        current_key = self._path_key(self.doc.path) if self.doc and self.doc.path else ""
        reopen = None
        for old, new in dlg.renamed:
            try:
                self.sidebar.update_document_path(old, new)
            except Exception:
                pass
            # View-State / Unsaved Keys migrieren
            ok = self._path_key(old)
            nk = self._path_key(new)
            if ok and nk and ok in self._tab_view_state:
                self._tab_view_state[nk] = self._tab_view_state.pop(ok)
            if ok and nk and ok in self._unsaved_paths:
                self._unsaved_paths.discard(ok)
                self._unsaved_paths.add(nk)
            if ok and current_key and ok == current_key:
                reopen = new
        if reopen:
            try:
                self.open_path(reopen)
            except Exception as e:
                self._set_status(f"Umbenannt, Öffnen fehlgeschlagen: {e}")
        try:
            self._save_session()
        except Exception:
            pass
        self._refresh_document_dirty_labels()
        self._set_status(f"Batch-Umbenennen: {len(dlg.renamed)} Datei(en) — 1.4.1")

    def _annotation_search_open_docs(self):
        """Volltext Sidecar-Notizen/Highlights über offene Docs — 1.4.0."""
        paths = list(self.sidebar.document_paths()) if hasattr(self.sidebar, "document_paths") else []
        if self._ann_search_dialog is None:
            self._ann_search_dialog = AnnotationSearchDialog(self, paths=paths)
            self._ann_search_dialog.hit_activated.connect(self._on_ann_search_hit)
        else:
            self._ann_search_dialog.set_paths(paths)
        self._ann_search_dialog.show()
        self._ann_search_dialog.raise_()
        self._ann_search_dialog.activateWindow()

    def _on_ann_search_hit(self, path: str, page: int, ann_id: str = "") -> None:
        """Treffer aus Annotation-Suche → Doc öffnen + Seite — 1.4.1."""
        if not path:
            return
        try:
            if not self.doc or not self.doc.path or self._path_key(self.doc.path) != self._path_key(path):
                self.open_path(path)
            if hasattr(self.pdf_view, "goto_page"):
                self.pdf_view.goto_page(int(page))
            else:
                self.pdf_view.page_index = int(page)
            self._set_status(
                f"Annotation-Treffer: {Path(path).name} S.{int(page) + 1} — 1.4.1"
            )
        except Exception as e:
            self._set_status(f"Annotation-Suche Sprung fehlgeschlagen: {e}")

    def _compare_text_tabs(self):
        """Zwei offene Text-Tabs: Wrap-Blink Dauer/Sound · Änderung i/n · Wrap-around · F7/Shift+F7 · Sync-Scroll · Ignore-Whitespace · Diff-TXT — 1.2.9."""
        _TEXT_EXT = {
            ".txt",
            ".md",
            ".markdown",
            ".html",
            ".htm",
            ".csv",
            ".json",
            ".py",
            ".log",
            ".docx",
            ".xml",
            ".yml",
            ".yaml",
            ".ini",
            ".cfg",
            ".toml",
        }
        all_paths = (
            self.sidebar.document_paths() if hasattr(self.sidebar, "document_paths") else []
        )
        tabs = [
            p
            for p in all_paths
            if Path(p).suffix.lower() in _TEXT_EXT
        ]
        open_tab_texts: list[tuple[str, str, str]] = []
        # Live-Inhalt des aktuellen Editors als Tab-Eintrag
        if self.doc and self.doc.kind not in (DocKind.PDF, DocKind.IMAGE):
            label = self.doc.display_name or "Aktuell"
            path_key = str(self.doc.path) if self.doc.path else ""
            open_tab_texts.append((path_key or "__editor__", label, self.editor.toPlainText()))
            if path_key and path_key not in tabs:
                tabs.insert(0, path_key)
        left_text = open_tab_texts[0][2] if open_tab_texts else None
        left_label = open_tab_texts[0][1] if open_tab_texts else None
        left_path = (
            str(self.doc.path)
            if self.doc and self.doc.path and self.doc.kind not in (DocKind.PDF, DocKind.IMAGE)
            else None
        )
        dlg = TextCompareDialog(
            self,
            tab_paths=tabs or ([open_tab_texts[0][0]] if open_tab_texts else []),
            left_path=left_path,
            left_text=left_text,
            left_label=left_label,
            panel_mode=True,
        )
        dlg.exec()
        self._text_diff_panel = dlg

    def _save_export_profile(self):
        from PySide6.QtWidgets import QFileDialog, QInputDialog
        from instantlensdoc.core.app_settings import (
            EXPORT_PROFILE_FORMATS,
            EXPORT_PROFILES_MAX,
            EXPORT_RASTER_DPI_CHOICES,
            LAST_EXPORT_PRESET_NAME,
            dialog_start_dir,
            export_profile_summary,
            get_export_profiles,
            get_export_raster_dpi,
            get_last_export_dir,
            get_last_export_format,
            save_export_profile,
        )

        existing = {str(p["name"]).casefold() for p in get_export_profiles()}
        name, ok = QInputDialog.getText(
            self,
            "Export-Preset",
            f"Name (leer = Zuletzt; max. {EXPORT_PROFILES_MAX}; "
            "Duplikate abgelehnt):",
            text=LAST_EXPORT_PRESET_NAME,
        )
        if not ok:
            return
        name = (name or "").strip() or LAST_EXPORT_PRESET_NAME
        # Duplikat-Namen ablehnen (außer „Zuletzt“) — 2.5.2
        if (
            name.casefold() != LAST_EXPORT_PRESET_NAME.casefold()
            and name.casefold() in existing
        ):
            QMessageBox.warning(
                self,
                "Export-Preset",
                f"Preset-Name „{name}“ existiert bereits.\n"
                "Bitte anderen Namen wählen oder das bestehende Preset löschen.",
            )
            return
        if (
            name.casefold() not in existing
            and len(existing) >= EXPORT_PROFILES_MAX
        ):
            QMessageBox.warning(
                self,
                "Export-Preset",
                f"Maximal {EXPORT_PROFILES_MAX} benannte Presets.\n"
                "Bitte zuerst eines löschen (Export-Presets verwalten…).",
            )
            return
        dpi_items = [str(d) for d in EXPORT_RASTER_DPI_CHOICES]
        default_dpi = str(get_export_raster_dpi())
        dpi_idx = dpi_items.index(default_dpi) if default_dpi in dpi_items else 1
        dpi_str, ok = QInputDialog.getItem(
            self, "Export-Preset", "DPI:", dpi_items, dpi_idx, False
        )
        if not ok:
            return
        fmt_items = list(EXPORT_PROFILE_FORMATS)
        last_fmt = get_last_export_format()
        fmt_idx = fmt_items.index(last_fmt) if last_fmt in fmt_items else 0
        fmt, ok = QInputDialog.getItem(
            self, "Export-Preset", "Format:", fmt_items, fmt_idx, False
        )
        if not ok:
            return
        start = dialog_start_dir(get_last_export_dir())
        target = QFileDialog.getExistingDirectory(self, "Zielordner für Preset", start)
        if not target:
            target = ""
        try:
            profile = save_export_profile(
                name, dpi=int(dpi_str), format=fmt, target=target or None
            )
            tip = export_profile_summary(profile)
            self._set_status(f"Export-Preset gespeichert: {profile['name']} ({tip})")
        except Exception as e:
            QMessageBox.warning(self, "Export-Preset", str(e))

    def _apply_export_profile(self):
        """Kompatibilität: öffnet Preset-Verwaltung — 2.5.1."""
        self._manage_export_presets()

    def _manage_export_presets(self):
        """Export-Presets: ★ · RMB Ordner · Entf · Summary/Pfad kopieren — 2.5.9."""
        from PySide6.QtCore import QEvent, QObject, QUrl
        from PySide6.QtGui import QDesktopServices, QKeyEvent
        from PySide6.QtWidgets import (
            QApplication,
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QHBoxLayout,
            QInputDialog,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QMenu,
            QPushButton,
            QVBoxLayout,
        )

        from instantlensdoc.core.app_settings import (
            EXPORT_PRESETS_SCHEMA_ID,
            EXPORT_PROFILES_MAX,
            ExportPresetsImportError,
            apply_export_profile,
            delete_export_profile,
            dialog_start_dir,
            duplicate_export_profile,
            export_export_presets_json,
            export_profile_path_preview,
            export_profile_summary,
            get_active_export_profile_name,
            get_export_profiles,
            get_last_export_dir,
            import_export_presets_json,
            move_export_profile,
            rename_export_profile,
            set_last_export_dir,
        )

        def _import_status_msg(result) -> str:
            msg = result.summary_text()
            return f"{msg} ({EXPORT_PRESETS_SCHEMA_ID})"

        profiles = get_export_profiles()
        if not profiles:
            # Auch ohne Presets Import erlauben — 2.5.2
            reply = QMessageBox.question(
                self,
                "Export-Presets",
                "Keine Presets gespeichert.\n"
                "Presets aus JSON importieren?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply != QMessageBox.Yes:
                return
            start = dialog_start_dir(get_last_export_dir())
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Export-Presets importieren",
                start,
                f"Export-Presets JSON (*{EXPORT_PRESETS_SCHEMA_ID}*.json *.json);;JSON (*.json)",
            )
            if not path:
                return
            try:
                imported = import_export_presets_json(path, merge=False)
                set_last_export_dir(str(Path(path).parent))
            except ExportPresetsImportError as e:
                QMessageBox.warning(self, "Export-Presets Import", str(e))
                return
            except Exception as e:
                QMessageBox.warning(self, "Export-Presets Import", str(e))
                return
            self._set_status(f"Export-Presets importiert: {_import_status_msg(imported)}")
            if not imported:
                return
            profiles = get_export_profiles()

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Export-Presets (max. {EXPORT_PROFILES_MAX})")
        dlg.setMinimumWidth(480)
        lay = QVBoxLayout(dlg)
        info = QLabel(
            f"Benannte Presets ({len(profiles)}/{EXPORT_PROFILES_MAX}). "
            "★ aktiv · RMB Zielordner · Summary/Pfad · F2 Umbenennen · "
            "Ctrl+D Duplizieren · Ctrl+Enter Anwenden (offen) · "
            "Ctrl+↑/↓ Reihenfolge · Ctrl+Home/End Anfang/Ende · "
            "Entf · Doppelklick Anwenden."
        )
        lay.addWidget(info)
        lst = QListWidget()
        lst.setToolTip(
            "★ = aktives Preset · Listen-Tooltip Summary DPI/Format/Pfad · "
            "Rechtsklick → Zielordner / Summary / Pfad kopieren · "
            "Ctrl+C Summary · Ctrl+Shift+C Pfad · F2 Umbenennen · "
            "Ctrl+D Duplizieren · Ctrl+Enter Anwenden ohne Schließen · "
            "Ctrl+↑/↓ Reihenfolge · Ctrl+Home/End Anfang/Ende · Entf löschen · "
            "Doppelklick/Enter Anwenden — 2.5.14"
        )
        lst.setContextMenuPolicy(Qt.CustomContextMenu)
        active = {"name": get_active_export_profile_name()}

        def _item_name(item: QListWidgetItem | None) -> str:
            if item is None:
                return ""
            data = item.data(Qt.UserRole) or {}
            return str(data.get("name") or "").strip()

        def _reload_list() -> None:
            lst.clear()
            cur = get_export_profiles()
            active["name"] = get_active_export_profile_name()
            info.setText(
                f"Benannte Presets ({len(cur)}/{EXPORT_PROFILES_MAX}). "
                "★ aktiv · RMB Zielordner · Summary/Pfad kopieren · Entf · Doppelklick Anwenden."
            )
            for p in cur:
                name = str(p["name"])
                label = f"{name} ★" if name == active["name"] else name
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, dict(p))
                tip = export_profile_summary(p)
                mark = " ★ aktiv" if name == active["name"] else ""
                item.setToolTip(f"{name}{mark}\n{tip}")
                lst.addItem(item)
                if name == active["name"]:
                    lst.setCurrentItem(item)
            if lst.currentRow() < 0 and lst.count() > 0:
                lst.setCurrentRow(0)

        _reload_list()
        lay.addWidget(lst, 1)
        summary = QLabel("")
        summary.setWordWrap(True)
        summary.setStyleSheet("color: #444; padding: 4px 0;")
        summary.setToolTip("Live-Zusammenfassung DPI · Format · Ziel — 2.5.1")
        lay.addWidget(summary)
        path_preview = QLabel("")
        path_preview.setWordWrap(True)
        path_preview.setStyleSheet("color: #333; font-family: monospace; padding: 2px 0;")
        path_preview.setToolTip("Live-Pfad-Vorschau Zielordner — 2.5.3")
        path_preview.setAccessibleName("Live-Pfad-Vorschau Export-Preset")
        lay.addWidget(path_preview)

        def _refresh_summary() -> None:
            item = lst.currentItem()
            if item is None:
                summary.setText("(kein Preset gewählt)")
                path_preview.setText("Pfad: (kein Preset)")
                path_preview.setAccessibleDescription("Kein Preset gewählt")
                return
            data = item.data(Qt.UserRole) or {}
            name = str(data.get("name") or _item_name(item))
            tip = export_profile_summary(data)
            mark = " ★ aktiv" if name == active["name"] else ""
            summary.setText(f"<b>{name}</b>{mark}<br>{tip}")
            path_txt = export_profile_path_preview(data)
            path_preview.setText(f"Pfad: {path_txt}")
            path_preview.setToolTip(f"Live-Pfad-Vorschau: {path_txt}")
            path_preview.setAccessibleDescription(f"Zielordner: {path_txt}")

        lst.currentItemChanged.connect(lambda *_: _refresh_summary())
        _refresh_summary()

        btn_row = QHBoxLayout()
        btn_apply = QPushButton("Anwenden")
        btn_apply.setDefault(True)
        btn_dup = QPushButton("Duplizieren")
        btn_dup.setToolTip("Gewähltes Export-Preset als Kopie anlegen — 2.5.5")
        btn_rename = QPushButton("Umbenennen…")
        btn_rename.setToolTip("Gewähltes Export-Preset umbenennen — 2.5.4")
        btn_delete = QPushButton("Löschen…")
        btn_export = QPushButton("Export JSON…")
        btn_export.setToolTip(
            f"Alle Presets als JSON exportieren ({EXPORT_PRESETS_SCHEMA_ID}) — 2.5.2"
        )
        btn_import = QPushButton("Import JSON…")
        btn_import.setToolTip(
            f"Presets JSON ({EXPORT_PRESETS_SCHEMA_ID}): ungültige überspringen+zählen · "
            "★ aktiv · RMB Zielordner · Summary/Pfad kopieren · Entf · Apply A11y — 2.5.9"
        )
        btn_row.addWidget(btn_apply)
        btn_row.addWidget(btn_dup)
        btn_row.addWidget(btn_rename)
        btn_row.addWidget(btn_delete)
        btn_row.addWidget(btn_export)
        btn_row.addWidget(btn_import)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        lay.addWidget(buttons)

        def _apply(*, close: bool = True) -> None:
            item = lst.currentItem()
            if item is None:
                return
            name = _item_name(item)
            profile = apply_export_profile(name)
            if not profile:
                msg = "Export-Preset nicht gefunden"
                self._set_status(msg)
                # Fail-Path A11y Apply fehlt — 2.5.19
                try:
                    self._announce_status_toast(msg)
                except Exception:
                    pass
                return
            tip = export_profile_summary(profile)
            msg = f"Export-Preset aktiv ★: {profile['name']} ({tip})"
            self._set_status(msg)
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            if close:
                dlg.accept()
            else:
                # Ctrl+Enter: ★ setzen, Dialog bleibt offen — 2.5.12
                _reload_list()
                for i in range(lst.count()):
                    it = lst.item(i)
                    if it and _item_name(it) == str(profile["name"]):
                        lst.setCurrentItem(it)
                        break
                _refresh_summary()

        def _duplicate() -> None:
            item = lst.currentItem()
            if item is None:
                return
            name = _item_name(item)
            try:
                dup = duplicate_export_profile(name)
            except ValueError as e:
                QMessageBox.warning(dlg, "Export-Preset duplizieren", str(e))
                return
            except Exception as e:
                QMessageBox.warning(dlg, "Export-Preset duplizieren", str(e))
                return
            msg = f"Export-Preset dupliziert: {name} → {dup['name']}"
            self._set_status(msg)
            # A11y Announce Duplizieren — 2.5.17
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            _reload_list()
            for i in range(lst.count()):
                it = lst.item(i)
                if it and _item_name(it) == str(dup["name"]):
                    lst.setCurrentItem(it)
                    break
            _refresh_summary()

        def _rename() -> None:
            item = lst.currentItem()
            if item is None:
                return
            old = _item_name(item)
            new_name, ok = QInputDialog.getText(
                dlg,
                "Export-Preset umbenennen",
                f"Neuer Name für „{old}“:",
                text=old,
            )
            if not ok:
                return
            new_name = (new_name or "").strip()
            if not new_name:
                QMessageBox.warning(dlg, "Export-Preset", "Name darf nicht leer sein.")
                return
            try:
                renamed = rename_export_profile(old, new_name)
            except ValueError as e:
                QMessageBox.warning(dlg, "Export-Preset umbenennen", str(e))
                return
            except Exception as e:
                QMessageBox.warning(dlg, "Export-Preset umbenennen", str(e))
                return
            msg = f"Export-Preset umbenannt: {old} → {renamed['name']}"
            self._set_status(msg)
            # A11y Announce Umbenennen — 2.5.17
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            _reload_list()
            # Fokus auf umbenanntes Preset
            for i in range(lst.count()):
                it = lst.item(i)
                if it and _item_name(it) == str(renamed["name"]):
                    lst.setCurrentItem(it)
                    break
            _refresh_summary()

        def _move(delta: int, *, status_msg: str | None = None) -> None:
            """Ctrl+↑/↓ Preset-Reihenfolge — 2.5.13; A11y Announce — 2.5.16."""
            item = lst.currentItem()
            if item is None:
                return
            name = _item_name(item)
            if not name:
                return
            if not move_export_profile(name, delta):
                return
            _reload_list()
            for i in range(lst.count()):
                it = lst.item(i)
                if it and _item_name(it) == name:
                    lst.setCurrentItem(it)
                    break
            _refresh_summary()
            direction = "oben" if delta < 0 else "unten"
            msg = status_msg or f"Export-Preset „{name}“ nach {direction} verschoben"
            self._set_status(msg)
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass

        def _move_to_edge(to_end: bool) -> None:
            """Ctrl+Home/End Preset an Anfang/Ende — 2.5.14; A11y — 2.5.16."""
            item = lst.currentItem()
            if item is None:
                return
            name = _item_name(item)
            if not name:
                return
            profiles_now = get_export_profiles()
            idx = next(
                (
                    i
                    for i, p in enumerate(profiles_now)
                    if str(p["name"]).casefold() == name.casefold()
                ),
                -1,
            )
            if idx < 0:
                return
            if to_end:
                delta = (len(profiles_now) - 1) - idx
            else:
                delta = -idx
            if delta == 0:
                return
            edge = "Ende" if to_end else "Anfang"
            _move(delta, status_msg=f"Export-Preset „{name}“ an {edge} verschoben")

        def _delete() -> None:
            item = lst.currentItem()
            if item is None:
                return
            name = _item_name(item)
            reply = QMessageBox.question(
                dlg,
                "Export-Preset löschen",
                f"Preset „{name}“ wirklich löschen?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            if not delete_export_profile(name):
                QMessageBox.warning(dlg, "Export-Preset", "Löschen fehlgeschlagen.")
                return
            msg = f"Export-Preset gelöscht: {name}"
            self._set_status(msg)
            # A11y Announce Löschen — 2.5.17
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            if not get_export_profiles():
                dlg.accept()
                return
            _reload_list()
            _refresh_summary()

        def _export_json() -> None:
            start = dialog_start_dir(get_last_export_dir())
            path, _ = QFileDialog.getSaveFileName(
                dlg,
                "Export-Presets exportieren",
                str(Path(start) / "ild-export-presets.json"),
                f"Export-Presets JSON (*{EXPORT_PRESETS_SCHEMA_ID}*.json *.json);;JSON (*.json)",
            )
            if not path:
                return
            try:
                dest = export_export_presets_json(path)
                set_last_export_dir(str(Path(dest).parent))
            except Exception as e:
                QMessageBox.warning(dlg, "Export-Presets Export", str(e))
                return
            QMessageBox.information(
                dlg,
                "Export-Presets",
                f"Exportiert ({EXPORT_PRESETS_SCHEMA_ID}):\n{dest}",
            )
            msg = f"Export-Presets exportiert: {dest.name}"
            self._set_status(msg)
            # A11y Announce JSON-Export — 2.5.18
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass

        def _import_json() -> None:
            start = dialog_start_dir(get_last_export_dir())
            path, _ = QFileDialog.getOpenFileName(
                dlg,
                "Export-Presets importieren",
                start,
                f"Export-Presets JSON (*{EXPORT_PRESETS_SCHEMA_ID}*.json *.json);;JSON (*.json)",
            )
            if not path:
                return
            reply = QMessageBox.question(
                dlg,
                "Export-Presets importieren",
                "Vorhandene Presets ersetzen?\n"
                "„Nein“ = Merge (neue Namen anhängen, Duplikate überspringen).\n"
                "Ungültige Einträge werden übersprungen und gezählt.\n"
                f"Schema: {EXPORT_PRESETS_SCHEMA_ID}",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Cancel:
                return
            merge = reply == QMessageBox.No
            try:
                imported = import_export_presets_json(path, merge=merge)
                set_last_export_dir(str(Path(path).parent))
            except ExportPresetsImportError as e:
                QMessageBox.warning(dlg, "Export-Presets Import", str(e))
                return
            except Exception as e:
                QMessageBox.warning(dlg, "Export-Presets Import", str(e))
                return
            mode = "Merge" if merge else "Ersetzen"
            QMessageBox.information(
                dlg,
                "Export-Presets",
                f"Import ({EXPORT_PRESETS_SCHEMA_ID}, {mode}):\n"
                f"{imported.summary_text()}",
            )
            msg = (
                f"Export-Presets importiert: {imported.summary_text()} ({mode})"
            )
            self._set_status(msg)
            # A11y Announce JSON-Import — 2.5.18
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            if not imported:
                dlg.accept()
                return
            _reload_list()
            _refresh_summary()

        def _open_target_folder(item: QListWidgetItem | None = None) -> None:
            """Rechtsklick: Zielordner des Presets öffnen — 2.5.7."""
            it = item if item is not None else lst.currentItem()
            if it is None:
                return
            data = it.data(Qt.UserRole) or {}
            name = str(data.get("name") or _item_name(it)).strip()
            target = str(data.get("target") or "").strip()
            if not target:
                QMessageBox.information(
                    dlg,
                    "Export-Preset",
                    "Kein Zielordner in diesem Preset gespeichert.",
                )
                msg = f"Export-Preset ohne Zielordner: {name or '(ohne Name)'}"
                self._set_status(msg)
                # Fail-Path A11y Ordner fehlt — 2.5.18
                try:
                    self._announce_status_toast(msg)
                except Exception:
                    pass
                return
            folder = Path(target)
            if not folder.is_dir():
                QMessageBox.warning(
                    dlg,
                    "Export-Preset",
                    f"Zielordner fehlt:\n{folder}",
                )
                msg = f"Export-Preset Zielordner fehlt: {folder}"
                self._set_status(msg)
                try:
                    self._announce_status_toast(msg)
                except Exception:
                    pass
                return
            try:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            except Exception as e:
                QMessageBox.warning(dlg, "Export-Preset", str(e))
                msg = f"Export-Preset Ordner öffnen fehlgeschlagen: {folder}"
                self._set_status(msg)
                try:
                    self._announce_status_toast(msg)
                except Exception:
                    pass
                return
            msg = f"Export-Preset Ordner geöffnet: {folder}"
            self._set_status(msg)
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass

        def _copy_summary(item: QListWidgetItem | None = None) -> None:
            """RMB/Ctrl+C: Preset-Summary (DPI·Format·Pfad) kopieren — 2.5.8."""
            it = item if item is not None else lst.currentItem()
            if it is None:
                return
            data = it.data(Qt.UserRole) or {}
            name = str(data.get("name") or _item_name(it)).strip()
            tip = export_profile_summary(data)
            path_txt = export_profile_path_preview(data)
            text = f"{name}\n{tip}\nPfad: {path_txt}".strip()
            try:
                clip = QApplication.clipboard()
                if clip is None:
                    raise RuntimeError("Zwischenablage nicht verfügbar")
                clip.setText(text)
            except Exception as e:
                QMessageBox.warning(dlg, "Export-Preset", str(e))
                msg = (
                    f"Export-Preset Summary kopieren fehlgeschlagen: "
                    f"{name or '(ohne Name)'}"
                )
                self._set_status(msg)
                # Fail-Path A11y Summary-Copy — 2.6.5
                try:
                    self._announce_status_toast(msg)
                except Exception:
                    pass
                return
            msg = f"Export-Preset Summary kopiert: {name}"
            self._set_status(msg)
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass

        def _copy_path(item: QListWidgetItem | None = None) -> None:
            """RMB/Ctrl+Shift+C: nur Zielordner-Pfad kopieren — 2.5.9."""
            it = item if item is not None else lst.currentItem()
            if it is None:
                return
            data = it.data(Qt.UserRole) or {}
            name = str(data.get("name") or _item_name(it)).strip()
            path_txt = export_profile_path_preview(data)
            if not path_txt or path_txt in ("(kein Preset)", "(kein Zielordner)"):
                path_txt = str(data.get("target") or "").strip()
            if not path_txt:
                QMessageBox.information(
                    dlg,
                    "Export-Preset",
                    "Kein Zielordner in diesem Preset gespeichert.",
                )
                msg = f"Export-Preset ohne Zielordner: {name or '(ohne Name)'}"
                self._set_status(msg)
                # Fail-Path A11y Pfad-Copy — 2.5.19
                try:
                    self._announce_status_toast(msg)
                except Exception:
                    pass
                return
            try:
                clip = QApplication.clipboard()
                if clip is None:
                    raise RuntimeError("Zwischenablage nicht verfügbar")
                clip.setText(path_txt)
            except Exception as e:
                QMessageBox.warning(dlg, "Export-Preset", str(e))
                msg = f"Export-Preset Pfad kopieren fehlgeschlagen: {name or '(ohne Name)'}"
                self._set_status(msg)
                try:
                    self._announce_status_toast(msg)
                except Exception:
                    pass
                return
            msg = f"Export-Preset Pfad kopiert: {name}"
            self._set_status(msg)
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass

        def _on_preset_context(pos) -> None:
            item = lst.itemAt(pos)
            if item is None:
                return
            lst.setCurrentItem(item)
            menu = QMenu(dlg)
            act_open = menu.addAction("Zielordner öffnen\tF4")
            act_copy = menu.addAction("Summary kopieren\tCtrl+C")
            act_copy_path = menu.addAction("Pfad kopieren\tCtrl+Shift+C")
            act_apply = menu.addAction("Anwenden\tEnter")
            act_apply_keep = menu.addAction("Anwenden (offen lassen)\tCtrl+Enter")
            act_dup = menu.addAction("Duplizieren\tCtrl+D")
            act_rename = menu.addAction("Umbenennen…\tF2")
            act_up = menu.addAction("Nach oben\tCtrl+↑")
            act_down = menu.addAction("Nach unten\tCtrl+↓")
            act_top = menu.addAction("An den Anfang\tCtrl+Home")
            act_bottom = menu.addAction("An das Ende\tCtrl+End")
            act_del = menu.addAction("Löschen…\tEntf")
            chosen = menu.exec(lst.mapToGlobal(pos))
            if chosen is act_open:
                _open_target_folder(item)
            elif chosen is act_copy:
                _copy_summary(item)
            elif chosen is act_copy_path:
                _copy_path(item)
            elif chosen is act_apply:
                _apply()
            elif chosen is act_apply_keep:
                _apply(close=False)
            elif chosen is act_dup:
                _duplicate()
            elif chosen is act_rename:
                _rename()
            elif chosen is act_up:
                _move(-1)
            elif chosen is act_down:
                _move(1)
            elif chosen is act_top:
                _move_to_edge(False)
            elif chosen is act_bottom:
                _move_to_edge(True)
            elif chosen is act_del:
                _delete()

        class _PresetListFilter(QObject):
            def eventFilter(self, obj, event):  # noqa: N802
                if obj is lst and event.type() == QEvent.KeyPress:
                    assert isinstance(event, QKeyEvent)
                    if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
                        _delete()
                        return True
                    if event.key() == Qt.Key_F2:
                        # F2 Umbenennen — 2.5.10
                        _rename()
                        return True
                    if event.key() == Qt.Key_D and bool(
                        event.modifiers() & Qt.ControlModifier
                    ):
                        # Ctrl+D Duplizieren — 2.5.11
                        _duplicate()
                        return True
                    if event.key() in (Qt.Key_Return, Qt.Key_Enter) and bool(
                        event.modifiers() & Qt.ControlModifier
                    ):
                        # Ctrl+Enter Anwenden ohne Schließen — 2.5.12
                        _apply(close=False)
                        return True
                    if event.key() in (Qt.Key_Up, Qt.Key_Down) and bool(
                        event.modifiers() & Qt.ControlModifier
                    ):
                        # Ctrl+↑/↓ Reihenfolge — 2.5.13
                        _move(-1 if event.key() == Qt.Key_Up else 1)
                        return True
                    if event.key() in (Qt.Key_Home, Qt.Key_End) and bool(
                        event.modifiers() & Qt.ControlModifier
                    ):
                        # Ctrl+Home/End Anfang/Ende — 2.5.14
                        _move_to_edge(event.key() == Qt.Key_End)
                        return True
                    if event.key() == Qt.Key_F4:
                        # F4 Zielordner öffnen — 2.5.15
                        _open_target_folder()
                        return True
                    if event.key() == Qt.Key_C and bool(
                        event.modifiers() & Qt.ControlModifier
                    ):
                        if bool(event.modifiers() & Qt.ShiftModifier):
                            _copy_path()
                        else:
                            _copy_summary()
                        return True
                return False

        _preset_filter = _PresetListFilter(dlg)
        lst.installEventFilter(_preset_filter)
        lst.customContextMenuRequested.connect(_on_preset_context)

        btn_apply.clicked.connect(_apply)
        btn_dup.clicked.connect(_duplicate)
        btn_rename.clicked.connect(_rename)
        btn_delete.clicked.connect(_delete)
        btn_export.clicked.connect(_export_json)
        btn_import.clicked.connect(_import_json)
        # Doppelklick / Enter → Anwenden — 2.5.4
        lst.itemDoubleClicked.connect(lambda *_: _apply())
        lst.itemActivated.connect(lambda *_: _apply())
        dlg.exec()

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
        if not self._guard_editor_action("Zwischenablage-Verlauf"):
            return
        if self.editor.paste_clipboard_history(index):
            self._set_status(f"Verlauf #{index + 1} eingefügt")
        else:
            self._set_status("Verlaufseintrag leer / ungültig")

    def _paste_clipboard_image(self):
        if self.stack.currentWidget() is self.pdf_view and self.pdf_view.pdf_path:
            if self.pdf_view.paste_clipboard_image():
                return
            # PDF-Tab: Editor nicht anheben, kein Geschwister-DOCX — 2.6.54
            self._set_status("Kein Bild in der Zwischenablage (PDF)")
            return
        if not self._guard_editor_action("Bild einfügen"):
            return
        if self.doc and self.doc.path:
            self.editor.set_paste_image_dir(Path(self.doc.path).parent)
        if self.editor.paste_clipboard_image():
            self._set_status("Bild aus Zwischenablage in Editor eingefügt")
            return
        from instantlensdoc.ui.feature_dialog import FeatureDialog

        FeatureDialog(
            self,
            title="Bild aus Zwischenablage",
            body="Kein Bild in der Zwischenablage.",
            object_name="ildClipboardImageDialog",
        ).exec()

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
        act_order.setEnabled(bool(templates))
        act_order.triggered.connect(self._reorder_user_templates_dialog)
        menu.addAction(act_order)
        act_folder = QAction("Vorlagen-Ordner öffnen…", self)
        act_folder.setToolTip("Spiegel-Ordner der Nutzer-Vorlagen im Explorer öffnen")
        act_folder.triggered.connect(self._open_user_templates_folder)
        menu.addAction(act_folder)
        act_export = QAction("Als Zip exportieren…", self)
        act_export.setToolTip("Vorlagen-Ordner als Zip speichern (templates.json + *.ildtpl.md)")
        act_export.setEnabled(bool(templates))
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
            self._feature_dialog(
                "Vorlagen exportieren",
                "Keine Nutzer-Vorlagen gespeichert — zuerst Datei → Als Vorlage speichern…",
                object_name="ildTemplatesEmptyDialog",
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
            self._feature_dialog(
                "Vorlagen-Reihenfolge",
                "Keine Nutzer-Vorlagen gespeichert — zuerst eine Vorlage anlegen.",
                object_name="ildTemplatesEmptyDialog",
            )
            return
        dlg = TemplatesOrderDialog(templates, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        ordered = reorder_user_doc_templates(dlg.ordered_ids())
        self._refresh_user_template_menu()
        self._set_status(f"Vorlagen-Reihenfolge gespeichert ({len(ordered)})")

    def _open_user_templates_folder(self) -> None:
        """Nutzer-Vorlagen spiegeln und Pfad in schließbarem Dialog zeigen."""
        from instantlensdoc.core.app_settings import sync_user_templates_folder
        from instantlensdoc.ui.feature_dialog import PathOpenDialog

        folder = sync_user_templates_folder()
        PathOpenDialog(self, title="Vorlagen-Ordner", path=folder).exec()
        self._set_status(f"Vorlagen-Ordner: {folder}")

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
            "Dokumente (*.ild *.txt *.md *.html *.htm *.docx *.rtf *.pdf *.png *.jpg *.jpeg);;"
            "Alle (*.*)",
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

    def open_path(
        self, path: str, *, encoding: str | None = None, readonly: bool = False
    ):
        # Vor Tab-Wechsel Last-Page/Scroll des aktuellen Docs merken (0.9.1)
        try:
            self._capture_current_tab_view_state()
        except Exception:
            pass
        # Verlassenes Dokument im Tab-Cache halten (DOCX-Import ist teuer) — 2.6.54
        try:
            self._doc_cache_store_current()
        except Exception:
            pass
        cached_dirty = False
        cached = None if encoding is not None else self._doc_cache_get(path)
        if cached is not None:
            self.doc = cached
            cached_dirty = bool(getattr(cached, "dirty", False))
        else:
            try:
                self.doc = open_document(path, encoding=encoding)
            except Exception as e:
                QMessageBox.critical(self, "Öffnen", f"Datei konnte nicht geöffnet werden:\n{e}")
                return
            self._doc_cache_put(path, self.doc)
        # Thumb-Lauf des vorherigen Dokuments beenden — Ticks dürfen nicht in den
        # Open des nächsten Dokuments hineinlaufen (processEvents in load) — 2.6.54
        try:
            self._stop_thumb_lazy()
        except Exception:
            pass

        path_key = str(Path(path).resolve()) if path else str(path)
        # Merge-Vorschau-Pfade bleiben readonly bis „Zum Bearbeiten öffnen“ — 1.1.5
        if readonly:
            self._readonly_preview_paths.add(path_key)
        is_preview = bool(readonly or path_key in self._readonly_preview_paths)
        if is_preview:
            self.doc.meta["readonly"] = True
        elif not self.doc.meta.get("kind_mismatch"):
            # Falsche Endung (.pdf mit DOCX-Inhalt) bleibt schreibgeschützt — 2.6.54
            self.doc.meta.pop("readonly", None)
        self.sidebar.add_document(path)
        self._refresh_doc_tab_bar()
        if not is_preview:
            self._remember_path(path)
        title_name = self.doc.display_name
        if is_preview:
            title_name = f"{title_name} [Vorschau]"
        self.setWindowTitle(self._app_title(title_name))

        try:
            if self.doc.kind == DocKind.PDF:
                self.stack.setCurrentWidget(self.pdf_view)
                self.pdf_view.show()
                if not self.pdf_view.load(path):
                    # Fehlgeschlagener Open darf den Zustand des vorherigen Dokuments
                    # (Seite 7/536, Thumbs, Outline, Banner) nicht stehen lassen — 2.6.54
                    try:
                        self.pdf_view.unload()
                    except Exception:
                        pass
                    self._stop_thumb_lazy()
                    self.sidebar.clear_thumbs()
                    self._update_doc_status()
                    self._refresh_doc_tab_bar()
                    return
                # Nach Open immer PDF-Stack + erste Seite in der zentralen Ansicht — 2.6.45
                self.stack.setCurrentWidget(self.pdf_view)
                self.pdf_view.show()
                try:
                    from PySide6.QtWidgets import QApplication

                    QApplication.processEvents()
                except Exception:
                    pass
                if not self.pdf_view._canvas_has_page_image():
                    self.pdf_view._ensure_page_painted(warn=False)
                open_gen = int(getattr(self.pdf_view, "_open_generation", 0) or 0)

                def _repaint_central() -> None:
                    if int(getattr(self.pdf_view, "_open_generation", 0) or 0) != open_gen:
                        return
                    # Anderes Dokument (DOCX/Tab) inzwischen aktiv: Stack nicht zurückstehlen — 2.6.54
                    if getattr(self.doc, "kind", None) != DocKind.PDF:
                        return
                    cur_p = str(getattr(self.doc, "path", "") or "")
                    try:
                        if Path(cur_p).resolve() != Path(path).resolve():
                            return
                    except Exception:
                        if cur_p != str(path):
                            return
                    if self.stack.currentWidget() is not self.pdf_view:
                        self.stack.setCurrentWidget(self.pdf_view)
                    if self.pdf_view.pdf_path and not self.pdf_view._canvas_has_page_image():
                        self.pdf_view._ensure_page_painted(warn=False)

                QTimer.singleShot(0, _repaint_central)
                QTimer.singleShot(80, _repaint_central)
                # Thumbs/Outline kommen deferred via document_changed — kein Doppel-Work — 2.6.37
                self._refresh_pdf_marks()
                self._refresh_portfolio_sidebar(path)
                _log.info("PDF geöffnet: %s", path)
            elif self.doc.kind == DocKind.IMAGE:
                from PySide6.QtGui import QPixmap

                self.stack.setCurrentWidget(self.image_label)
                pm = QPixmap(path)
                self.image_label.setPixmap(
                    pm.scaled(900, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.sidebar.set_marks([f"Bild: {Path(path).name}"])
                self._stop_thumb_lazy()
                self.sidebar.clear_thumbs()
                self.sidebar.clear_annotations()
                self._refresh_portfolio_sidebar(None)
            else:
                # Inhalt VOR dem Stack-Wechsel laden: currentChanged → _update_doc_status
                # → _current_is_dirty verglich sonst alten Editor-Text mit neuem Doc und
                # setzte doc.dirty dauerhaft („wurde geändert“ direkt nach Öffnen) — 2.6.52
                self._loading_document = True
                try:
                    self.editor.blockSignals(True)
                    html = (self.doc.meta or {}).get("html")
                    if html and self.doc.kind in (DocKind.DOCX, DocKind.HTML):
                        try:
                            self.editor.set_rich_html(
                                str(html), base_font=self._rich_base_font_for_doc()
                            )
                        except Exception:
                            self.editor.setPlainText(self.doc.text)
                    else:
                        self.editor.setPlainText(self.doc.text)
                    self.editor.blockSignals(False)
                    # Rich-Text: Plaintext des Docs an Qt-Normalisierung angleichen
                    if html and self.doc.kind in (DocKind.DOCX, DocKind.HTML):
                        try:
                            self.doc.text = self.editor.toPlainText()
                        except Exception:
                            pass
                    self.doc.dirty = False
                    self.stack.setCurrentWidget(self.editor_pane)
                finally:
                    self._loading_document = False
                self.doc.dirty = False
                if cached_dirty:
                    # Ungespeicherte Änderungen aus dem Tab-Cache bleiben dirty — 2.6.54
                    self.doc.dirty = True
                    self._mark_unsaved(path, True)
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
                self._stop_thumb_lazy()
                self.sidebar.clear_thumbs()
                self.sidebar.clear_annotations()
                self._refresh_portfolio_sidebar(None)
            # Last-Page / Scroll-Position für diesen Tab wiederherstellen
            try:
                self._restore_tab_view_state(path)
            except Exception:
                pass
            self._update_doc_status()
            self._sync_preview_readonly_banner()
            enc = self.doc.meta.get("encoding")
            mismatch = self.doc.meta.get("kind_mismatch")
            if mismatch:
                real = self.doc.meta.get("kind_mismatch_kind", "")
                self._set_status(
                    f"Endung .pdf, Inhalt {real}: als {real} geöffnet (schreibgeschützt) — {Path(path).name}"
                )
                _log.warning("Falsche Endung: %s", mismatch)
            elif is_preview or self.doc.meta.get("readonly"):
                self._set_status(f"Vorschau (readonly): {path}")
            elif enc:
                self._set_status(f"Geöffnet: {path} [{enc}]")
            else:
                self._set_status(f"Geöffnet: {path}")
            try:
                from instantlensdoc.core.plugin_hooks import emit as emit_hook

                kind = ""
                if self.doc is not None:
                    kind = str(getattr(self.doc.kind, "name", self.doc.kind) or "")
                emit_hook("document.opened", kind=kind[:32])
            except Exception:
                pass
            try:
                # PDF-Outline bereits deferred via document_changed — Text/Editor hier — 2.6.37
                is_pdf = (
                    self.doc is not None
                    and str(getattr(self.doc.kind, "name", "")) == "PDF"
                )
                if not is_pdf:
                    self._refresh_document_outline(pdf_path=None)
            except Exception:
                pass
        except Exception as e:
            _log.exception("Anzeige fehlgeschlagen: %s", path)
            QMessageBox.critical(self, "Öffnen", f"Anzeige fehlgeschlagen:\n{e}")

    def _sync_preview_readonly_banner(self) -> None:
        """Banner „Vorschau“ + Bearbeiten-Button bei Readonly-Tab — 1.1.5."""
        banner = getattr(self, "preview_readonly_banner", None)
        if banner is None:
            return
        is_ro = bool(self.doc and self.doc.meta.get("readonly"))
        mismatch = str((self.doc.meta.get("kind_mismatch") if self.doc else "") or "")
        label = getattr(self, "preview_readonly_label", None)
        hint = getattr(self, "preview_readonly_hint", None)
        btn = getattr(self, "btn_preview_open_edit", None)
        if mismatch:
            # .pdf-Datei mit DOCX/HTML/Text-Inhalt: Inhalt ist geladen, Datei trägt die
            # falsche Endung → Banner erklärt das und bietet das Speichern unter der
            # richtigen Endung an — 2.6.54
            real = str(self.doc.meta.get("kind_mismatch_kind", "") or "")
            if label is not None:
                label.setText("Falsche Dateiendung")
            if hint is not None:
                hint.setText(mismatch)
            if btn is not None:
                ext = {
                    "DOCX": ".docx",
                    "HTML": ".html",
                    "RTF": ".rtf",
                    "TEXT": ".txt",
                    "IMAGE": ".png",
                }.get(real, "")
                btn.setText(f"Als {ext or 'richtige Endung'} speichern…")
                try:
                    btn.clicked.disconnect()
                except Exception:
                    pass
                btn.clicked.connect(self._save_mismatched_with_real_extension)
        else:
            if label is not None:
                label.setText("Vorschau")
            if hint is not None:
                hint.setText("Schreibgeschützt — Änderungen werden nicht gespeichert.")
            if btn is not None and btn.text() != "Zum Bearbeiten öffnen":
                btn.setText("Zum Bearbeiten öffnen")
                try:
                    btn.clicked.disconnect()
                except Exception:
                    pass
                btn.clicked.connect(self._open_preview_for_edit)
        banner.setVisible(is_ro)

    def _save_mismatched_with_real_extension(self) -> None:
        """Falsch benannte .pdf (Inhalt DOCX/HTML/…) unter richtiger Endung kopieren — 2.6.54."""
        if not self.doc or not self.doc.path or not self.doc.meta.get("kind_mismatch"):
            self._set_status("Keine falsch benannte Datei geöffnet")
            return
        from ild_pdf.pdf_sniff import recover_misnamed_file, sniff_file

        src = Path(self.doc.path)
        sn = sniff_file(src)
        ext = sn.suggested_extension or ".bin"
        suggested = src.with_suffix(ext)
        filt = f"{ext.lstrip('.').upper()} (*{ext});;Alle (*.*)"
        path, _sel = QFileDialog.getSaveFileName(
            self, "Unter richtiger Endung speichern", str(suggested), filt
        )
        if not path:
            return
        try:
            out = recover_misnamed_file(src, path)
            if out is None:
                raise RuntimeError("Dateityp hat keine sichere Endung")
            self._set_status(f"Kopie mit richtiger Endung gespeichert: {out}")
            self.open_path(str(out))
        except Exception as e:
            QMessageBox.critical(self, "Speichern", f"Kopie fehlgeschlagen:\n{e}")

    def _open_preview_for_edit(self) -> None:
        """Readonly-Vorschau → echtes bearbeitbares Dokument — 1.1.5/1.1.6."""
        if not self.doc or not self.doc.path:
            self._set_status("Kein Vorschau-Dokument")
            return
        if not self.doc.meta.get("readonly"):
            self._set_status("Dokument ist bereits bearbeitbar")
            self._sync_preview_readonly_banner()
            return
        path = str(self.doc.path)
        try:
            path_key = str(Path(path).resolve())
        except Exception:
            path_key = path
        self._readonly_preview_paths.discard(path_key)

        close_preview = False
        try:
            from instantlensdoc.core.app_settings import get_merge_close_preview_on_edit

            close_preview = bool(get_merge_close_preview_on_edit())
        except Exception:
            close_preview = False

        if close_preview:
            # Readonly-Tab schließen und Datei neu bearbeitbar öffnen — 1.1.6
            try:
                self.sidebar.remove_document(path)
            except Exception:
                pass
            self.doc.meta.pop("readonly", None)
            self.open_path(path, readonly=False)
            self._set_status(f"Zum Bearbeiten geöffnet (Vorschau geschlossen): {path}")
            return

        self.doc.meta.pop("readonly", None)
        self._remember_path(path)
        title_name = self.doc.display_name
        self.setWindowTitle(self._app_title(title_name))
        self._sync_preview_readonly_banner()
        self._update_doc_status()
        self._set_status(f"Zum Bearbeiten geöffnet: {path}")

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
        if self.doc.meta.get("readonly"):
            if self.doc.meta.get("kind_mismatch"):
                real = self.doc.meta.get("kind_mismatch_kind", "")
                if not quiet:
                    QMessageBox.information(
                        self,
                        "Falsche Dateiendung",
                        f"Die Datei trägt die Endung .pdf, enthält aber {real}.\n"
                        "Speichern unter diesem Namen ist gesperrt — bitte über die Leiste "
                        "„Als … speichern…“ oder „Speichern unter“ mit der richtigen Endung sichern.",
                    )
                self._set_status("Falsche Endung (.pdf) — Speichern unter richtiger Endung nötig")
                return False
            if not quiet:
                QMessageBox.information(
                    self,
                    "Vorschau",
                    "Readonly-Vorschau — Speichern ist deaktiviert.",
                )
            self._set_status("Vorschau (readonly) — Speichern deaktiviert")
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
                self._clear_recovery_for_current()
                self._set_status(f"PDF-Annotationen (Sidecar) gespeichert: {side}")
                return True
            return False
        if not self.doc.path:
            self.save_as()
            return not self._current_is_dirty()
        if self.doc.kind in (DocKind.TEXT, DocKind.MARKDOWN, DocKind.HTML, DocKind.DOCX, DocKind.RTF):
            self._sync_editor_text_before_save()
        self._sync_editor_rich_meta()
        try:
            save_document(self.doc)
            try:
                if self.doc.kind == DocKind.DOCX and self.doc.path:
                    from instantlensdoc.ui.styles import persist_styles_in_docx

                    persist_styles_in_docx(
                        str(self.doc.path),
                        html=(self.doc.meta or {}).get("html"),
                    )
                from instantlensdoc.core.field_tokens import persist_document_field_tokens

                persist_document_field_tokens(
                    self.doc.path,
                    (self.doc.meta or {}).get("field_tokens"),
                    kind=getattr(self.doc.kind, "name", "") or "",
                )
            except Exception:
                pass
            self._remember_path(self.doc.path)
            self._mark_unsaved(self.doc.path, False)
            self._clear_recovery_for_current()
            self._doc_cache_put(self.doc.path, self.doc)
            enc = self.doc.meta.get("encoding")
            suffix = f" [{enc}]" if enc else ""
            self._set_status(f"Gespeichert: {self.doc.path}{suffix}")
            try:
                from instantlensdoc.core.plugin_hooks import emit as emit_hook

                emit_hook("document.saved", ok=True)
            except Exception:
                pass
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
            enc = self._pick_text_encoding(
                "Speichern mit Encoding",
                (self.doc.meta.get("encoding") if self.doc else None),
            )
            if not enc:
                return
            if self.doc is not None:
                self.doc.meta["encoding"] = enc
            self.save_doc()
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
        saved = 0
        errors: list[str] = []
        try:
            st = self.license_manager.status()
            if not st.allowed:
                self._feature_dialog(
                    "Lizenz",
                    "Speichern nicht möglich — Lizenz/Trial abgelaufen.",
                )
                return
            current = str(self.doc.path) if self.doc and self.doc.path else ""
            if self.doc:
                try:
                    if self.doc.kind == DocKind.PDF:
                        if self.pdf_view.store is not None:
                            self.pdf_view.store.save(force=True)
                            saved += 1
                    elif self.doc.path:
                        if self.doc.kind in (
                            DocKind.TEXT,
                            DocKind.MARKDOWN,
                            DocKind.HTML,
                            DocKind.DOCX,
                        ):
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
            from ild_pdf import AnnotationStore

            try:
                extra_paths = list(self.sidebar.document_paths() or [])
            except Exception:
                extra_paths = []
            for path in extra_paths:
                try:
                    p = Path(path)
                    if current and str(p.resolve()) == str(Path(current).resolve()):
                        continue
                    if p.suffix.lower() != ".pdf" or not p.is_file():
                        continue
                    store = AnnotationStore(p)
                    if store.annotations and store.sidecar_path.is_file():
                        store.dirty = True
                        store.save(force=True)
                        saved += 1
                except Exception as e:
                    errors.append(f"{Path(str(path)).name}: {e}")
        except Exception as e:
            errors.append(str(e))
        self._set_status(f"Alles speichern: {saved} Datei(en)/Sidecar(s)")
        body = (
            f"Gespeichert: {saved}\nFehler:\n" + "\n".join(errors[:8])
            if errors
            else (
                "Nichts zu speichern — keine Änderungen und keine Sidecars."
                if saved == 0
                else f"{saved} Datei(en)/Sidecar(s) gespeichert."
            )
        )
        self._feature_dialog("Alles speichern", body)

    def save_as(self):
        if not self.doc:
            return
        if self.doc.kind == DocKind.PDF:
            # Klar: Speichern-unter bei PDF = Sidecar-Annotationen, nicht die PDF-Datei
            if self.pdf_view.save_annotations_as():
                self._set_status("Annotation-Sidecar gespeichert unter…")
            return
        from instantlensdoc.ui.file_dialogs import (
            document_save_default_suffix,
            document_save_suggested_name,
            get_document_save_file_name,
        )

        # Default-Endung + Filter ohne *.py — sonst hängt Windows/python.exe .py an — 2.6.43
        default_suf = document_save_default_suffix(self.doc.kind)
        suggested = document_save_suggested_name(
            self.doc.display_name,
            kind=self.doc.kind,
            path=self.doc.path,
        )
        path, selected = get_document_save_file_name(
            self,
            "Speichern unter",
            dialog_start_dir(),
            suggested,
            default_suffix=default_suf,
        )
        if not path:
            return
        remember_recent_dir(path)
        if self.doc.kind in (
            DocKind.TEXT,
            DocKind.MARKDOWN,
            DocKind.HTML,
            DocKind.DOCX,
            DocKind.RTF,
            DocKind.XLSX,
        ):
            self._sync_editor_text_before_save()
            self.doc.text = self.editor.toPlainText()
        try:
            dest = Path(path)
            # Text → PDF ausschließlich über den PDF-Exporter — nie über save_document
            # (≤ 2.6.42 kopierte das die DOCX-Bytes unter .pdf-Namen → „Data format
            # error“ in PDFium/Edge). Formatiertes HTML (DOCX/HTML) geht mit — 2.6.54
            if dest.suffix.lower() == ".pdf" and self.doc.kind != DocKind.PDF:
                from ild_pdf.pdf_sniff import validate_pdf_file
                from instantlensdoc.core import export as exp

                self._sync_editor_rich_meta()
                title = self.doc.title or self.doc.display_name or "InstantLens Doc"
                rich_html = (self.doc.meta or {}).get("html") if self.doc.kind in (
                    DocKind.DOCX,
                    DocKind.HTML,
                    DocKind.RTF,
                ) or (self.doc.meta or {}).get("rich_text") else None
                exp.export_document(
                    self.doc.text or "",
                    dest,
                    fmt="pdf",
                    title=title,
                    html=str(rich_html) if rich_html else None,
                )
                check = validate_pdf_file(dest)
                if not check.ok:
                    raise RuntimeError(check.message_de())
                self.doc.path = dest
                self.doc.kind = DocKind.PDF
                self.doc.dirty = False
                self.doc.title = dest.name
                self._set_status(f"PDF gespeichert: {dest} ({check.page_count} Seite(n))")
            else:
                save_document(self.doc, dest)
            self.sidebar.add_document(str(dest))
            self._remember_path(str(dest))
            self.setWindowTitle(self._app_title(self.doc.display_name))
            filt_hint = f" [{selected}]" if selected else ""
            self._set_status(f"Gespeichert: {dest}{filt_hint}")
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
        """Editor-Inhalt nach HTML / DOCX / XLSX / PDF / TXT / RTF / JPG / EPUB / PPTX."""
        text = ""
        title = "InstantLens Doc"
        editor_kinds = (
            DocKind.TEXT,
            DocKind.MARKDOWN,
            DocKind.HTML,
            DocKind.DOCX,
            DocKind.RTF,
            DocKind.XLSX,
        )
        if self.stack.currentWidget() is self.editor_pane:
            text = self.editor.toPlainText()
            if self.doc:
                title = self.doc.title or self.doc.display_name
        elif self.doc and self.doc.kind in editor_kinds:
            text = self.doc.text or self.editor.toPlainText()
            title = self.doc.display_name
        else:
            self._set_status("Export nur im Editor")
            return
        filters = {
            "html": ("HTML (*.html)", ".html"),
            "docx": ("DOCX (*.docx)", ".docx"),
            "xlsx": ("Excel (*.xlsx)", ".xlsx"),
            "pdf": ("PDF (*.pdf)", ".pdf"),
            "txt": ("Text (*.txt)", ".txt"),
            "rtf": ("RTF (*.rtf)", ".rtf"),
            "jpg": ("JPEG (*.jpg)", ".jpg"),
            "epub": ("EPUB (*.epub)", ".epub"),
            "pptx": ("PowerPoint (*.pptx)", ".pptx"),
        }
        if fmt not in filters:
            QMessageBox.warning(self, "Export", f"Unbekanntes Format: {fmt}")
            return
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

            # Formatierter Inhalt (DOCX/HTML-Editor) für PDF/DOCX/RTF mitgeben — 2.6.54
            rich_html = None
            if fmt in ("pdf", "docx", "rtf") and self.stack.currentWidget() is self.editor_pane:
                try:
                    if self.editor.rich_mode():
                        rich_html = self.editor.to_rich_html()
                except Exception:
                    rich_html = None
            exp.export_document(text, path, fmt=fmt, title=title, html=rich_html)
            if fmt == "pdf":
                from ild_pdf.pdf_sniff import validate_pdf_file

                check = validate_pdf_file(path)
                if not check.ok:
                    raise RuntimeError(check.message_de())
            set_last_export_dir(path)
            remember_recent_dir(path)
            self._set_status(f"Exportiert: {path}")
            try:
                from instantlensdoc.core.plugin_hooks import emit as emit_hook

                emit_hook("document.exported", fmt=str(fmt), ok=True)
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "Export", f"Export fehlgeschlagen:\n{e}")

    def _insert_table_dialog(self) -> None:
        """Tabelle einfügen — Smoke: QInputDialog (2662), sonst Raster-Picker."""
        import os

        from PySide6.QtWidgets import QInputDialog

        if not self._guard_editor_action("Tabelle"):
            return
        if os.environ.get("ILD_SMOKE_QT") == "1":
            rows, ok = QInputDialog.getInt(self, "Tabelle", "Zeilen:", 3, 1, 200)
            if not ok:
                return
            cols, ok = QInputDialog.getInt(self, "Tabelle", "Spalten:", 3, 1, 50)
            if not ok:
                return
            if self.editor.insert_table(int(rows), int(cols)):
                self._sync_editor_rich_meta()
                self._sync_table_tools()
                self._set_status(f"Tabelle {rows}×{cols} eingefügt")
            else:
                self._set_status("Tabelle nicht eingefügt")
            return

        def _insert(rows: int, cols: int) -> None:
            if self.editor.insert_table(int(rows), int(cols)):
                self._sync_editor_rich_meta()
                self._sync_table_tools()
                self._set_status(f"Tabelle {rows}×{cols} eingefügt")
            else:
                self._set_status("Tabelle nicht eingefügt")

        from PySide6.QtGui import QCursor

        from instantlensdoc.ui.tables import show_table_picker

        show_table_picker(self, pos=QCursor.pos(), on_pick=_insert)

    def _table_op(self, op: str) -> None:
        if not self._guard_editor_action("Tabelle"):
            return
        from instantlensdoc.ui import tables as ild_tables

        table = self.editor.current_qtext_table()
        if table is None:
            self._set_status("Keine Tabelle am Cursor — zuerst Tabelle einfügen")
            return
        cur = self.editor.textCursor()
        ok = False
        if op == "add_row":
            ok = ild_tables.add_row(table)
        elif op == "add_col":
            ok = ild_tables.add_column(table)
        elif op == "del_row":
            ok = ild_tables.delete_row(table, cur)
        elif op == "del_col":
            ok = ild_tables.delete_column(table, cur)
        elif op == "merge":
            ok = ild_tables.merge_selected_cells(table, cur)
        elif op == "split":
            ok = ild_tables.split_current_cell(table, cur)
        elif op == "borders":
            fmt = table.format()
            ok = ild_tables.set_borders(table, enabled=fmt.border() <= 0.1)
        elif op == "header":
            ok = ild_tables.set_header_row(table, enabled=True)
        elif op.startswith("align_"):
            ok = ild_tables.set_cell_alignment(table, cur, op.split("_", 1)[1])
        if ok:
            self._sync_editor_rich_meta()
            self._sync_table_tools()
            self._set_status(f"Tabelle: {op}")
        else:
            self._set_status(f"Tabelle: {op} nicht möglich")

    def _format_table_dialog(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        if not self._guard_editor_action("Tabelle"):
            return
        align, ok = QInputDialog.getText(
            self, "Tabelle formatieren", "Ausrichtung (z. B. lcr):", text="lcr"
        )
        if not ok:
            return
        style, ok = QInputDialog.getItem(
            self,
            "Tabelle formatieren",
            "Stil:",
            ["default", "striped", "compact"],
            0,
            False,
        )
        if not ok:
            return
        if self.editor.format_current_table(align=align or None, style=style or None):
            self._set_status(f"Tabelle formatiert ({style})")
        else:
            self._set_status("Tabelle: bitte Tabelle auswählen")

    def _sort_table_dialog(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        if not self._guard_editor_action("Tabelle"):
            return
        col, ok = QInputDialog.getInt(self, "Tabelle sortieren", "Spalte (0-basiert):", 0, 0, 49)
        if not ok:
            return
        try:
            if self.editor.sort_current_table(col):
                self._set_status(f"Tabelle nach Spalte {col} sortiert")
            else:
                self._set_status("Tabelle: bitte Tabelle auswählen")
        except Exception as e:
            self._set_status(f"Tabelle sortieren: {e}")

    def _import_table_data(self) -> None:
        if not self._guard_editor_action("Tabelle"):
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Zahlen/Daten importieren",
            str(dialog_start_dir()),
            "Tabellen (*.csv *.xlsx);;CSV (*.csv);;Excel (*.xlsx);;Alle (*.*)",
        )
        if not path:
            return
        try:
            self.editor.import_table_file(path)
            remember_recent_dir(path)
            self._set_status(f"Tabelle importiert: {Path(path).name}")
        except Exception as e:
            QMessageBox.warning(self, "Tabellen-Import", str(e))

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

    def _add_column_frames(self):
        """Verkettete Spalten-Rahmen mit Textfluss — 2.6.12."""
        from PySide6.QtWidgets import QInputDialog

        cols, ok = QInputDialog.getInt(self, "Spalten-Rahmen", "Anzahl Spalten:", 2, 1, 6)
        if not ok:
            return
        source = self.editor.toPlainText() if self.stack.currentWidget() is self.editor_pane else ""
        if not source.strip():
            source = ("Spaltenfluss-Beispieltext für InstantLens Doc. " * 20)
        frames = self.layout_doc.create_column_chain(columns=cols)
        filled = self.layout_doc.flow_text_chain(source, frames[0])
        overflow = filled.pop("__overflow__", "")
        if self.stack.currentWidget() is self.editor_pane:
            lines = [f"\n=== Spalten-Kette ({cols}) ==="]
            for fr in frames:
                lines.append(f"--- Spalte {fr.column + 1} ({fr.id}) ---")
                lines.append(fr.text or "(leer)")
            if overflow:
                lines.append(f"--- Overflow ---\n{overflow[:400]}")
            self.editor.appendPlainText("\n".join(lines))
        self._set_status(f"{cols} Spalten verkettet, {len(filled)} gefüllt")

    def _pick_frame_id(self, title: str) -> str | None:
        from PySide6.QtWidgets import QInputDialog

        frames = self.layout_doc.list_frames()
        if not frames:
            QMessageBox.information(self, title, "Keine Rahmen vorhanden.")
            return None
        labels = [
            f"{f.get('kind', '?')} {f.get('id')} @({f.get('x')},{f.get('y')}) "
            f"{f.get('width')}×{f.get('height')}"
            for f in frames
        ]
        choice, ok = QInputDialog.getItem(self, title, "Rahmen:", labels, 0, False)
        if not ok:
            return None
        if choice not in labels:
            self._set_status("Rahmen-Auswahl ungültig")
            return None
        idx = labels.index(choice)
        return str(frames[idx]["id"])

    def _move_frame_dialog(self):
        from PySide6.QtWidgets import QInputDialog

        fid = self._pick_frame_id("Rahmen verschieben")
        if not fid:
            return
        fr = self.layout_doc.any_frame_by_id(fid)
        if fr is None:
            return
        x, ok = QInputDialog.getDouble(self, "Verschieben", "X (pt):", fr.x, -1000, 5000, 1)
        if not ok:
            return
        y, ok = QInputDialog.getDouble(self, "Verschieben", "Y (pt):", fr.y, -1000, 5000, 1)
        if not ok:
            return
        try:
            self.layout_doc.move_frame(fid, x, y)
            self._set_status(f"Rahmen {fid} → ({x:g},{y:g})")
        except Exception as e:
            QMessageBox.warning(self, "Verschieben", str(e))

    def _resize_frame_dialog(self):
        from PySide6.QtWidgets import QInputDialog

        fid = self._pick_frame_id("Rahmen skalieren")
        if not fid:
            return
        fr = self.layout_doc.any_frame_by_id(fid)
        if fr is None:
            return
        w, ok = QInputDialog.getDouble(
            self, "Skalieren", "Breite (pt):", fr.width, 8, 5000, 1
        )
        if not ok:
            return
        h, ok = QInputDialog.getDouble(
            self, "Skalieren", "Höhe (pt):", fr.height, 8, 5000, 1
        )
        if not ok:
            return
        try:
            self.layout_doc.resize_frame(fid, w, h)
            self._set_status(f"Rahmen {fid} → {w:g}×{h:g}")
        except Exception as e:
            QMessageBox.warning(self, "Skalieren", str(e))

    def _apply_master_page_dialog(self):
        """Musterseite (HF + Seitenzahlen) auf aktuelles PDF bakken — 2.6.12."""
        from PySide6.QtWidgets import QInputDialog
        from ild_pdf.page_layout import apply_master_page, list_master_presets

        if not self._require_pdf("Musterseite"):
            return
        presets = list_master_presets()
        names = [str(p.get("name") or p.get("id")) for p in presets]
        choice, ok = QInputDialog.getItem(
            self, "Musterseite", "Preset:", names, 0, False
        )
        if not ok:
            return
        title, ok = QInputDialog.getText(self, "Musterseite", "Titel:", text="")
        if not ok:
            return
        author, ok = QInputDialog.getText(self, "Musterseite", "Autor:", text="")
        if not ok:
            return
        try:
            dest = apply_master_page(
                self.pdf_view.pdf_path,
                choice,
                title=title or None,
                author=author or None,
            )
            self.pdf_view.load(str(dest))
            self._set_status(f"Musterseite „{choice}“ angewendet → {dest.name}")
        except Exception as e:
            QMessageBox.critical(self, "Musterseite", f"Fehler:\n{e}")

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

    def _run_scan_import(self):
        """Scan-Dialog: Gerät + Scannen → Bild im Dokument — 2.6.54."""
        try:
            from instantlensdoc.core.devices import SCAN_START_HINT_DE

            self._set_status(SCAN_START_HINT_DE)
        except Exception:
            pass
        try:
            prefer = str(getattr(self, "_preferred_scan_device_id", "") or "")
            if hasattr(self.pdf_view, "scan_import_dialog"):
                self.pdf_view.scan_import_dialog()
            else:
                from instantlensdoc.ui.scan_dialog import ScanDialog

                ScanDialog(
                    self.pdf_view, self, preferred_device_id=prefer or None
                ).exec()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Scannen / Import",
                f"Scan-Dialog konnte nicht geöffnet werden:\n{e}\n\n"
                "Menü Geräte → Scannen… · oder Bilder importieren.\n"
                "Shortcut: Ctrl+Shift+S (auch Ctrl+Alt+Shift+I)",
            )

    def _show_devices_dialog(self, filter_kind: str | None = None, auto_refresh: bool = False):
        """Drucker- & Scannerliste mit Aktualisieren (lokal + Netzwerk) — 2.6.38."""
        from PySide6.QtWidgets import QDialogButtonBox, QMessageBox

        try:
            from instantlensdoc.ui.scan_dialog import ScanDialog

            dlg = ScanDialog(self.pdf_view, self, auto_launch_scantuxio=False)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Geräte",
                f"Geräte-Dialog fehlgeschlagen:\n{e}",
            )
            return
        dlg.setWindowTitle("Drucker & Scanner")
        dlg.setObjectName("devicesDialog")
        dlg.btn_acquire.setVisible(False)
        dlg.btn_import.setVisible(False)
        for _w in (
            getattr(dlg, "btn_scantuxio", None),
            getattr(dlg, "btn_take_scan", None),
        ):
            if _w is not None:
                try:
                    _w.setVisible(False)
                except Exception:
                    pass
        dlg.ocr_enabled.setVisible(False)
        dlg.lang_combo.setVisible(False)
        dlg.tess_hint.setVisible(False)
        for _w in (
            getattr(dlg, "layout_hocr", None),
            getattr(dlg, "layout_tsv", None),
            getattr(dlg, "word_suite_check", None),
        ):
            if _w is not None:
                try:
                    _w.setVisible(False)
                except Exception:
                    pass
        dlg.pending_label.setText(
            "Druckerliste für Druckziele · Scanner für Scan-Dialog. "
            "Aktualisieren / Neu suchen. — 2.6.38"
        )
        if filter_kind == "printer":
            idx = dlg.filter_combo.findData("printer")
            if idx >= 0:
                dlg.filter_combo.setCurrentIndex(idx)
            dlg.setWindowTitle("Drucker")
        elif filter_kind == "scanner":
            idx = dlg.filter_combo.findData("scanner")
            if idx >= 0:
                dlg.filter_combo.setCurrentIndex(idx)
            dlg.setWindowTitle("Scanner")
        if auto_refresh:
            try:
                dlg.refresh_devices()
            except Exception:
                pass
        bbox = dlg.findChild(QDialogButtonBox)
        if bbox is not None:
            ok = bbox.button(QDialogButtonBox.Ok)
            if ok is not None:
                ok.setText("Schließen")
                try:
                    bbox.accepted.disconnect()
                except Exception:
                    pass
                bbox.accepted.connect(dlg.accept)
        dlg.exec()

    def _show_scan_ocr_text(self, text: str, title: str = "Scan-OCR") -> None:
        """OCR-Text aus Scan/Import im Editor zeigen — 2.6.5 / rich 2.6.54."""
        if self.open_ocr_result(
            text=text,
            title=title if title.startswith("Word-Suite") else f"Word-Suite — {title}",
            auto_format=False,
            source_path=str(self.doc.path) if self.doc and self.doc.path else None,
        ):
            return
        self.stack.setCurrentWidget(self.editor_pane)
        self.editor.setPlainText(text)
        self.doc = Document(kind=DocKind.TEXT, title=title, text=text)
        self.setWindowTitle(self._app_title(title))
        self._set_status(f"{title}: {len(text.split())} Wörter")
        try:
            from instantlensdoc.core.plugin_hooks import emit as emit_hook

            emit_hook("ocr.finished", mode="scan_import", lang="tesseract")
        except Exception:
            pass

    def _present_word_suite_document(self, doc_ws, *, status: str | None = None) -> bool:
        """Word-Suite-/OCR-Dokument im gleichen Editor wie geöffnetes DOCX zeigen.

        Stack → ``editor_pane``, ``self.editor`` (rich QTextDocument, DocKind.DOCX).
        Bearbeiten/Ribbon treffen danach dieselbe Instanz: Auswahl → Tool auf
        Selektion, keine Auswahl → gesamter OCR-Text.
        """
        from instantlensdoc.core.ocr_word_suite import (
            WordSuiteDocument,
            word_suite_to_document,
        )

        if doc_ws is None:
            return False
        if isinstance(doc_ws, WordSuiteDocument):
            doc = word_suite_to_document(doc_ws)
            ws = doc_ws
        elif isinstance(doc_ws, Document):
            doc = doc_ws
            ws = None
        else:
            return False
        try:
            self._capture_current_tab_view_state()
        except Exception:
            pass
        try:
            self._doc_cache_store_current()
        except Exception:
            pass
        try:
            self._stop_thumb_lazy()
        except Exception:
            pass
        html = str((doc.meta or {}).get("html") or (getattr(ws, "html", "") if ws else "") or "")
        body = doc.text or ""
        tab_title = doc.title or "Word-Suite — OCR"
        self._loading_document = True
        try:
            self.editor.blockSignals(True)
            if html.strip():
                try:
                    self.editor.set_rich_html(html, base_font=self._rich_base_font_for_meta(doc.meta))
                    try:
                        doc.text = self.editor.toPlainText()
                    except Exception:
                        doc.text = body
                    try:
                        self.editor._apply_page_layout()
                    except Exception:
                        pass
                    try:
                        h = str((doc.meta or {}).get("header") or "")
                        f = str((doc.meta or {}).get("footer") or "")
                        if h or f:
                            self.editor.set_document_header_footer(h, f)
                        else:
                            h = self.editor.document_header()
                            f = self.editor.document_footer()
                            if h:
                                doc.meta["header"] = h
                            if f:
                                doc.meta["footer"] = f
                        ft = dict((doc.meta or {}).get("field_tokens") or {})
                        if ft:
                            try:
                                self.editor.set_field_token_specs(ft)
                            except Exception:
                                self.editor._field_tokens = {
                                    str(k): str(v)
                                    for k, v in ft.items()
                                    if str(k).strip() and not isinstance(v, dict)
                                }
                        elif getattr(self.editor, "_field_tokens", None):
                            doc.meta["field_tokens"] = dict(self.editor.field_tokens())
                    except Exception:
                        pass
                except Exception:
                    self.editor.setPlainText(body)
            else:
                self.editor.setPlainText(body)
            self.editor.blockSignals(False)
            self.doc = doc
            self.doc.dirty = False
            self.stack.setCurrentWidget(self.editor_pane)
        finally:
            self._loading_document = False
            try:
                self.editor.blockSignals(False)
            except Exception:
                pass
        try:
            self.editor.clear_extra_selections()
        except Exception:
            pass
        try:
            self.editor.clear_line_bookmarks()
        except Exception:
            pass
        try:
            self._editor_marks.clear()
            self.sidebar.set_marks([])
            self.sidebar.clear_thumbs()
            self.sidebar.clear_annotations()
            self._refresh_portfolio_sidebar(None)
        except Exception:
            pass
        try:
            from PySide6.QtGui import QTextCursor

            cur = self.editor.textCursor()
            cur.movePosition(QTextCursor.Start)
            self.editor.setTextCursor(cur)
        except Exception:
            pass
        try:
            self.editor.setFocus(Qt.OtherFocusReason)
        except Exception:
            pass
        self.setWindowTitle(self._app_title(tab_title))
        self._last_ocr_word_suite = ws if ws is not None else getattr(self, "_last_ocr_word_suite", None)
        n_blocks = 0
        if ws is not None:
            n_blocks = ws.block_count
        else:
            n_blocks = int((doc.meta or {}).get("block_count") or 0)
        if not status:
            status = (
                f"Word-Suite: {tab_title} · {n_blocks} Block/Blöcke · "
                f"{len((doc.text or '').split())} Wörter"
            )
            if ws is not None and ws.auto_formatted:
                status += " · Auto-Format"
            sidecar = (doc.meta or {}).get("sidecar") or (ws.sidecar if ws else None)
            if sidecar:
                status += f" · {Path(str(sidecar)).name}"
        self._set_status(status)
        try:
            self._sync_preview_readonly_banner()
        except Exception:
            pass
        try:
            self._sync_pdf_page_shortcuts()
            self._sync_editor_only_actions()
            self._sync_menu_enablement()
            self._update_doc_status()
            self._refresh_doc_tab_bar()
        except Exception:
            pass
        try:
            from instantlensdoc.core.plugin_hooks import emit as emit_hook

            mode = (doc.meta or {}).get("ocr_mode") or (ws.mode if ws else "editable_text")
            lang = (ws.lang if ws else "") or "deu+eng"
            emit_hook("ocr.word_suite", mode=mode, lang=lang, blocks=n_blocks)
        except Exception:
            pass
        return True

    def _rich_base_font_for_meta(self, meta: dict | None):
        from PySide6.QtGui import QFont

        meta = meta or {}
        fam = str(meta.get("font_family") or "").strip() or "Calibri"
        try:
            size = float(meta.get("font_size_pt") or 0.0)
        except (TypeError, ValueError):
            size = 0.0
        if not (6.0 <= size <= 72.0):
            size = 11.0
        font = QFont(fam)
        font.setPointSizeF(size)
        font.setStyleHint(QFont.SansSerif)
        return font

    def open_ocr_result(
        self,
        source: str | Path | None = None,
        *,
        text: str | None = None,
        result=None,
        scan=None,
        path: str | Path | None = None,
        title: str | None = None,
        auto_format: bool = True,
        source_path: str | Path | None = None,
        source_page: int | None = None,
        pdf_extract: str | Path | None = None,
        pdf_extract_all: bool = False,
        page: int = 1,
        page_index: int | None = None,
        password: str | None = None,
        prefer_layout: bool = True,
        lang: str = "deu+eng",
    ) -> bool:
        """OCR/Sidecar/Scan/PDF-Text → Word-Suite-Editor (rich DOCX). Ctrl+Alt+Shift+W."""
        from instantlensdoc.core.ocr_word_suite import open_ocr_result as core_open

        src = path if path is not None else source
        try:
            doc = core_open(
                src,
                text=text,
                result=result,
                scan=scan,
                pdf_extract=pdf_extract,
                pdf_extract_all=pdf_extract_all,
                page=page,
                page_index=page_index,
                password=password,
                lang=lang,
                auto_format=auto_format,
                title=title,
                prefer_layout=prefer_layout,
                source_path=source_path,
                source_page=source_page,
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "OCR → Word-Suite",
                f"Übernahme fehlgeschlagen:\n{e}",
            )
            return False
        return self._present_word_suite_document(doc)

    def _handoff_ocr_to_word_suite(
        self,
        *,
        text: str | None = None,
        result=None,
        path: str | Path | None = None,
        title: str | None = None,
        auto_format: bool = True,
        scan=None,
        source_path: str | Path | None = None,
        source_page: int | None = None,
    ) -> bool:
        """OCR/Sidecar → editierbares Word-Suite-Dokument — 2.6.15 / rich 2.6.54."""
        return self.open_ocr_result(
            path=path,
            text=text,
            result=result,
            scan=scan,
            title=title,
            auto_format=auto_format,
            source_path=source_path,
            source_page=source_page,
        )

    def _open_ki_wizard_document(self, doc_ws) -> bool:
        """Wizard-Ergebnis als editierbares Word-Suite-/Editor-Dokument öffnen — 2.6.16."""
        if doc_ws is None:
            return False
        body = getattr(doc_ws, "text", None) or ""
        if isinstance(doc_ws, dict):
            body = doc_ws.get("text") or ""
            tab_title = doc_ws.get("title") or "Word-Suite — KI-Wizard"
        else:
            tab_title = getattr(doc_ws, "title", None) or "Word-Suite — KI-Wizard"
        self.stack.setCurrentWidget(self.editor_pane)
        self.editor.setPlainText(body)
        self.doc = Document(kind=DocKind.MARKDOWN, title=tab_title, text=body)
        self.setWindowTitle(self._app_title(tab_title))
        self._last_ki_wizard_doc = doc_ws
        kind = getattr(doc_ws, "kind", None) or (
            doc_ws.get("kind") if isinstance(doc_ws, dict) else ""
        )
        mode = getattr(doc_ws, "mode", None) or (
            doc_ws.get("mode") if isinstance(doc_ws, dict) else "template"
        )
        self._set_status(
            f"KI-Wizard: {tab_title} · {kind} · {mode} · {len(body.split())} Wörter"
        )
        try:
            from instantlensdoc.core.plugin_hooks import emit as emit_hook

            emit_hook("ki.wizard", kind=kind, mode=mode)
        except Exception:
            pass
        return True

    def _ki_document_wizard_action(self) -> None:
        """Extras/Palette: isolierter KI-Dokument-Wizard — 2.6.16."""
        from instantlensdoc.ui.ki_wizard_dialog import run_ki_document_wizard

        doc_ws = run_ki_document_wizard(self)
        if doc_ws is None:
            return
        self._open_ki_wizard_document(doc_ws)

    def _ocr_word_suite_action(self) -> None:
        """Menü/Palette: Sidecar wählen oder letztes OCR → Word-Suite — 2.6.15."""
        last = getattr(self, "_last_ocr_result", None)
        last_side = None
        if last is not None and getattr(last, "sidecar", None):
            last_side = Path(last.sidecar)
        # Prefer last OCR result in memory
        if last is not None:
            ok = self._handoff_ocr_to_word_suite(
                result=last,
                title=f"Word-Suite — {getattr(last, 'source_label', None) or 'OCR'}",
                auto_format=True,
            )
            if ok:
                return
        # Sidecar neben aktuellem PDF/Bild?
        if self.doc and self.doc.path:
            base = Path(self.doc.path)
            candidates = [
                base.with_suffix(base.suffix + ".ildocr.txt"),
                base.parent / f"{base.stem}.ildocr.txt",
                base.parent / f"{base.name}.ildocr.txt",
            ]
            for c in candidates:
                if c.is_file():
                    if self._handoff_ocr_to_word_suite(path=c, auto_format=True):
                        return
        if last_side and last_side.is_file():
            if self._handoff_ocr_to_word_suite(path=last_side, auto_format=True):
                return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "OCR → Word-Suite — Sidecar oder Bild",
            dialog_start_dir(),
            "OCR Sidecar / Bild (*.ildocr.txt *.ildocr.hocr *.ildocr.tsv "
            "*.hocr *.tsv *.png *.jpg *.jpeg *.tif *.tiff *.pdf);;Alle (*.*)",
        )
        if not path:
            return
        remember_recent_dir(path)
        self._handoff_ocr_to_word_suite(path=path, auto_format=True)

    def _run_ocr_handwriting(self):
        """Handschriftenerkennung: OCR-Dialog mit Handschrift-PSM vorausgewählt — 2.6.18."""
        from PySide6.QtWidgets import QDialog

        need_file = not (
            self.doc and self.doc.path and self.doc.kind in (DocKind.IMAGE, DocKind.PDF)
        )
        dlg = OcrDialog(
            self,
            need_file=need_file,
            default_label=Path(self.doc.path).name if self.doc and self.doc.path else "",
        )
        if hasattr(dlg, "handwriting_check"):
            dlg.handwriting_check.setChecked(True)
        if hasattr(dlg, "rb_editable"):
            dlg.rb_editable.setChecked(True)
        if dlg.exec() != QDialog.Accepted:
            return
        # Reuse normal OCR path by temporarily storing dialog — call core directly
        self._run_ocr_with_dialog(dlg)

    def _current_pdf_path(self) -> Path | None:
        """Aktuelles PDF für Druck/Preflight — Viewer oder aktiver Doc-Tab."""
        if self.doc and self.doc.path and self.doc.kind == DocKind.PDF:
            p = Path(self.doc.path)
            if p.is_file():
                return p
        pv = getattr(self, "pdf_view", None)
        raw = getattr(pv, "pdf_path", None) if pv is not None else None
        if raw:
            p = Path(raw)
            if p.is_file():
                return p
        return None

    def _run_preflight(self) -> None:
        """Preflight-Druckprüfung — 2.6.18."""
        from ild_pdf.print_prep import preflight_to_text, run_preflight

        if not self._require_pdf("Preflight"):
            return
        pdf = self._current_pdf_path()
        if pdf is None:
            return
        report = run_preflight(pdf, require_bleed=False, color_mode="cmyk")
        text = preflight_to_text(report)
        box = QMessageBox(self)
        box.setWindowTitle("Preflight (Druckprüfung)")
        box.setObjectName("preflightResultDialog")
        box.setText(
            f"{'OK' if report.ok else 'Probleme gefunden'} — "
            f"{report.summary.get('errors', 0)} Fehler, "
            f"{report.summary.get('warnings', 0)} Warnungen"
        )
        box.setDetailedText(text)
        box.setIcon(
            QMessageBox.Information if report.ok else QMessageBox.Warning
        )
        box.exec()
        self._set_status(
            f"Preflight: {'OK' if report.ok else 'Fehler'} "
            f"({report.summary.get('errors', 0)}/{report.summary.get('warnings', 0)})"
        )

    def _apply_bleed_dialog(self) -> None:
        """Anschnitt/Bleed setzen — 2.6.18."""
        from PySide6.QtWidgets import QInputDialog
        from ild_pdf.print_prep import BleedSettings, apply_bleed_boxes

        if not self._require_pdf("Anschnitt"):
            return
        pdf = self._current_pdf_path()
        if pdf is None:
            return
        mm, ok = QInputDialog.getDouble(
            self,
            "Anschnitt / Bleed",
            "Anschnitt (mm, alle Seiten):",
            3.0,
            0.0,
            20.0,
            1,
        )
        if not ok:
            return
        start = dialog_start_dir(get_last_export_dir() or pdf.parent)
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "PDF mit Anschnitt speichern",
            str(Path(start) / f"{pdf.stem}_bleed.pdf"),
            "PDF (*.pdf)",
        )
        if not dest:
            return
        out = apply_bleed_boxes(pdf, BleedSettings.uniform(mm), out=dest)
        set_last_export_dir(Path(out).parent)
        self._set_status(f"Anschnitt {mm:g} mm → {out}")
        QMessageBox.information(
            self, "Anschnitt", f"Bleed gesetzt ({mm:g} mm):\n{out}"
        )

    def _show_doc_layers(self) -> None:
        """PDF-OCG-Ebenen (pikepdf) plus DTP-Rahmen-Ebenen — 2.6.59."""
        from ild_pdf.print_prep import (
            LAYER_LABELS,
            list_layers,
            list_optional_content_groups,
        )

        if not self._require_pdf("Dokument-Ebenen"):
            return
        pdf = self._current_pdf_path()
        lines = ["Dokument-Ebenen", ""]
        ocgs = []
        if pdf is not None:
            try:
                ocgs = list_optional_content_groups(pdf)
            except Exception as e:
                ocgs = []
                lines.append(f"OCG-Lesen fehlgeschlagen: {e}")
                lines.append("")
        if ocgs:
            lines.append(f"PDF Optional Content ({pdf.name}):")
            for g in ocgs:
                vis = "sichtbar" if g.get("visible") else "ausgeblendet"
                extra = f" · {g.get('intent')}" if g.get("intent") else ""
                lines.append(f"• {g.get('name') or 'Ebene'} — {vis}{extra}")
            lines.append("")
        else:
            lines.append("Keine PDF-Optional-Content-Groups (OCG) in diesem Dokument.")
            lines.append("")
        layers = list_layers()
        by = {}
        if hasattr(self, "layout_doc") and self.layout_doc is not None:
            by = self.layout_doc.frames_by_layer()
        lines.append("DTP-Rahmen-Ebenen (Hintergrund / Bilder / Text):")
        for layer in layers:
            lid = layer["id"]
            frames = by.get(lid) or []
            lines.append(
                f"• {LAYER_LABELS.get(lid, layer['name'])}: "
                f"{len(frames)} Rahmen — sichtbar={layer.get('visible')}"
            )
            for fr in frames[:8]:
                lines.append(
                    f"    - {fr.get('kind', '?')} #{fr.get('id')} "
                    f"p{int(fr.get('page', 0)) + 1}"
                )
            if len(frames) > 8:
                lines.append(f"    … +{len(frames) - 8} weitere")
        self._feature_dialog(
            "Dokument-Ebenen",
            "\n".join(lines),
            object_name="ildDocLayersDialog",
        )

    def _export_pdfx(self) -> None:
        """PDF/X bzw. print-ready Export — 2.6.18."""
        from ild_pdf.print_prep import export_pdfx
        from ild_pdf.text_pdf import text_to_pdf
        from instantlensdoc.core.export import resolve_page_size

        pdf = self._current_pdf_path()
        temp_src: Path | None = None
        if pdf is None:
            # Texteditor → temp PDF → PDF/X
            text = ""
            title = "InstantLens Doc"
            if self.stack.currentWidget() is self.editor_pane:
                text = self.editor.toPlainText()
                if self.doc:
                    title = self.doc.title or self.doc.display_name
            elif self.doc and self.doc.kind in (
                DocKind.TEXT,
                DocKind.MARKDOWN,
                DocKind.HTML,
                DocKind.DOCX,
            ):
                text = self.doc.text or self.editor.toPlainText()
                title = self.doc.display_name
            else:
                QMessageBox.information(
                    self,
                    "PDF/X",
                    "Bitte ein PDF oder einen Text-Tab öffnen.",
                )
                return
            import tempfile

            tmp = Path(tempfile.mkdtemp(prefix="ild-pdfx-")) / "source.pdf"
            text_to_pdf(text, tmp, title=title, page_size=resolve_page_size(None))
            pdf = tmp
            temp_src = tmp
        start = dialog_start_dir(get_last_export_dir() or pdf.parent)
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Als PDF/X (druckreif) exportieren",
            str(Path(start) / f"{pdf.stem}_pdfx.pdf"),
            "PDF (*.pdf)",
        )
        if not dest:
            return
        try:
            result = export_pdfx(
                pdf,
                dest,
                profile="pdfx4",
                bleed_mm=3.0,
                title=None,
                run_preflight_first=True,
            )
            set_last_export_dir(Path(dest).parent)
            pf = result.get("preflight") or {}
            self._set_status(f"PDF/X exportiert: {dest}")
            QMessageBox.information(
                self,
                "PDF/X",
                f"Druckreifes PDF gespeichert:\n{dest}\n\n"
                f"Profil: {result.get('profile')} · Bleed: {result.get('bleed_mm')} mm\n"
                f"Preflight: {'OK' if pf.get('ok', True) else 'Hinweise vorhanden'}",
            )
        except Exception as e:
            QMessageBox.warning(self, "PDF/X", str(e))
        finally:
            if temp_src is not None:
                try:
                    temp_src.unlink(missing_ok=True)
                    temp_src.parent.rmdir()
                except Exception:
                    pass

    def _run_ocr_with_dialog(self, dlg) -> None:
        """OCR mit bereits akzeptiertem Dialog (Handschrift/Standard) — 2.6.18."""
        from PySide6.QtWidgets import QApplication, QDialog, QProgressDialog

        ok, msg = ocr_mod.tesseract_available()
        if not ok:
            self._feature_dialog("OCR — Tesseract fehlt", msg)
            self._set_status("OCR nicht verfügbar")
            return
        lang = dlg.lang_code()
        mode = dlg.output_mode()
        hw = bool(getattr(dlg, "handwriting_enabled", lambda: False)())
        hw_psm = int(getattr(dlg, "handwriting_psm_value", lambda: 6)())
        open_ws = bool(getattr(dlg, "open_in_word_suite", lambda: True)())
        ws_auto = bool(getattr(dlg, "word_suite_auto_format_enabled", lambda: True)())
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
                result = ocr_mod.run_ocr(
                    self.doc.path,
                    lang=lang,
                    mode=mode,
                    source_label=source_label,
                    handwriting=hw,
                    handwriting_psm=hw_psm,
                )
            elif self.doc and self.doc.kind == DocKind.PDF and self.doc.path:
                from ild_pdf import render_page

                source_label = f"{Path(self.doc.path).name} Seite {self.pdf_view.page_index + 1}"
                img = render_page(self.doc.path, self.pdf_view.page_index, scale=2.0)
                result = ocr_mod.run_ocr(
                    img,
                    lang=lang,
                    mode=mode,
                    source_label=source_label,
                    handwriting=hw,
                    handwriting_psm=hw_psm,
                )
            else:
                path = dlg.selected_path
                if not path:
                    return
                source_label = Path(path).name
                result = ocr_mod.run_ocr(
                    path,
                    lang=lang,
                    mode=mode,
                    source_label=source_label,
                    handwriting=hw,
                    handwriting_psm=hw_psm,
                )
        except ocr_mod.OcrUnavailable as e:
            self._feature_dialog("OCR — Tesseract fehlt", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "OCR", f"OCR fehlgeschlagen:\n{e}")
            return
        finally:
            prog.close()
        text = result.text or ""
        title_suffix = f"Handschrift — {source_label}" if hw else source_label
        src_page = None
        src_path = None
        if self.doc and self.doc.kind == DocKind.PDF and self.doc.path:
            src_path = str(self.doc.path)
            try:
                src_page = int(self.pdf_view.page_index) + 1
            except Exception:
                src_page = None
        if open_ws and text.strip():
            if self._handoff_ocr_to_word_suite(
                result=result,
                auto_format=ws_auto,
                title=f"Word-Suite — {title_suffix}",
                source_path=src_path,
                source_page=src_page,
            ):
                self._set_status(f"OCR → Word-Suite ({result.lang})")
                return
        if text.strip() and self.open_ocr_result(
            result=result,
            title=f"Word-Suite — {title_suffix}",
            auto_format=False,
            source_path=src_path,
            source_page=src_page,
        ):
            self._set_status(f"OCR → Word-Suite ({result.lang}, handwriting={hw})")
            return
        self.stack.setCurrentWidget(self.editor_pane)
        self.editor.setPlainText(text)
        self.doc = Document(
            kind=DocKind.TEXT,
            title=f"OCR — {title_suffix}",
            text=text,
        )
        self.setWindowTitle(self._app_title(f"OCR — {title_suffix}"))
        self._set_status(f"OCR ({result.lang}, handwriting={hw})")

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
            self._feature_dialog("OCR — Tesseract fehlt", msg)
            self._set_status("OCR nicht verfügbar")
            return

        lang = dlg.lang_code()
        mode = dlg.output_mode()
        csv_delim = dlg.csv_delimiter() if mode == ocr_mod.OcrOutputMode.TABLE_CSV else None
        csv_bom = dlg.csv_utf8_bom() if mode == ocr_mod.OcrOutputMode.TABLE_CSV else None
        write_hocr = bool(getattr(dlg, "write_hocr", lambda: True)())
        write_tsv = bool(getattr(dlg, "write_tsv", lambda: True)())
        open_ws = bool(getattr(dlg, "open_in_word_suite", lambda: True)())
        ws_auto = bool(getattr(dlg, "word_suite_auto_format_enabled", lambda: True)())
        hw = bool(getattr(dlg, "handwriting_enabled", lambda: False)())
        hw_psm = int(getattr(dlg, "handwriting_psm_value", lambda: 6)())
        # Tabellen-CSV: gemerkten Zielordner bevorzugen — 1.9.1
        csv_out_dir = None
        if mode == ocr_mod.OcrOutputMode.TABLE_CSV:
            from instantlensdoc.core.app_settings import (
                get_last_ocr_table_csv_dir,
                set_last_ocr_table_csv_dir,
            )

            remembered = get_last_ocr_table_csv_dir()
            start_csv = dialog_start_dir(remembered)
            picked = QFileDialog.getExistingDirectory(
                self, "Zielordner für Tabellen-CSV", start_csv
            )
            if picked:
                csv_out_dir = Path(picked)
                set_last_ocr_table_csv_dir(csv_out_dir)
                remember_recent_dir(str(csv_out_dir))
            elif remembered:
                csv_out_dir = remembered
        prog = QProgressDialog("OCR läuft…", None, 0, 0, self)
        prog.setWindowTitle("OCR")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        prog.setValue(0)
        prog.show()
        QApplication.processEvents()
        # Tabellen-CSV: erst OCR, dann 5-Zeilen-Vorschau, dann speichern — 1.9.2
        write_csv_now = mode != ocr_mod.OcrOutputMode.TABLE_CSV
        try:
            if self.doc and self.doc.kind == DocKind.IMAGE and self.doc.path:
                source_label = Path(self.doc.path).name
                prog.setLabelText(f"OCR: {source_label}")
                QApplication.processEvents()
                result = ocr_mod.run_ocr(
                    self.doc.path,
                    lang=lang,
                    mode=mode,
                    out_dir=csv_out_dir or Path(self.doc.path).parent,
                    source_label=source_label,
                    csv_delimiter=csv_delim,
                    csv_utf8_bom=csv_bom,
                    write_csv=write_csv_now,
                    write_hocr=write_hocr,
                    write_tsv=write_tsv,
                    handwriting=hw,
                    handwriting_psm=hw_psm,
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
                    out_dir=csv_out_dir or Path(self.doc.path).parent,
                    source_label=source_label,
                    csv_delimiter=csv_delim,
                    csv_utf8_bom=csv_bom,
                    write_csv=write_csv_now,
                    write_hocr=write_hocr,
                    write_tsv=write_tsv,
                    handwriting=hw,
                    handwriting_psm=hw_psm,
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
                    out_dir=csv_out_dir or Path(path).parent,
                    source_label=source_label,
                    csv_delimiter=csv_delim,
                    csv_utf8_bom=csv_bom,
                    write_csv=write_csv_now,
                    write_hocr=write_hocr,
                    write_tsv=write_tsv,
                    handwriting=hw,
                    handwriting_psm=hw_psm,
                )
        except ocr_mod.OcrUnavailable as e:
            self._feature_dialog("OCR — Tesseract fehlt", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "OCR", f"OCR fehlgeschlagen:\n{e}")
            return
        finally:
            prog.close()

        if mode == ocr_mod.OcrOutputMode.TABLE_CSV:
            from instantlensdoc.ui.ocr_dialog import CsvPreviewDialog

            out_base = csv_out_dir
            if out_base is None:
                if self.doc and self.doc.path:
                    out_base = Path(self.doc.path).parent
                else:
                    out_base = Path.cwd()
            stem = Path(source_label).stem if source_label else "ocr"
            target_csv = Path(out_base) / f"{stem}_table.csv"
            prev = CsvPreviewDialog(
                result.table_rows or [],
                self,
                max_rows=5,
                delimiter=str(csv_delim or ";"),
                target_hint=str(target_csv),
            )
            if prev.exec() != QDialog.Accepted or not prev.save_confirmed:
                self._set_status("Tabellen-CSV abgebrochen (nicht gespeichert)")
                return
            # Trennzeichen aus Live-Vorschau (1.9.3)
            csv_delim = getattr(prev, "selected_delimiter", None) or csv_delim or ";"
            try:
                from instantlensdoc.core.ocr import write_ocr_table_csv
                from instantlensdoc.core.app_settings import set_last_ocr_table_csv_dir

                written = write_ocr_table_csv(
                    target_csv,
                    result.table_rows or [],
                    delimiter=str(csv_delim or ";"),
                    utf8_bom=bool(csv_bom if csv_bom is not None else True),
                )
                result.sidecar = written
                set_last_ocr_table_csv_dir(written.parent)
            except Exception as e:
                QMessageBox.warning(self, "Tabellen-CSV", f"Speichern fehlgeschlagen:\n{e}")
                return

        self._last_ocr_result = result
        # Word-Suite-Handoff (Default an) — editierbarer Text / Layout / Sidecar — 2.6.15
        if open_ws and mode != ocr_mod.OcrOutputMode.TABLE_CSV:
            title_suffix = source_label
            if result.mode == ocr_mod.OcrOutputMode.LAYOUT_PRESERVE:
                title_suffix = f"Layout — {source_label}"
            elif result.mode == ocr_mod.OcrOutputMode.SEARCHABLE_IMAGE:
                title_suffix = f"Sidecar — {source_label}"
            if self._handoff_ocr_to_word_suite(
                result=result,
                title=f"Word-Suite — {title_suffix}",
                auto_format=ws_auto,
                source_path=str(self.doc.path) if self.doc and self.doc.path else None,
                source_page=(
                    int(self.pdf_view.page_index) + 1
                    if self.doc and self.doc.kind == DocKind.PDF
                    else None
                ),
            ):
                extra = ""
                if result.searchable_pdf:
                    extra = f" · PDF {result.searchable_pdf.name}"
                if result.sidecar:
                    extra += f" · {Path(result.sidecar).name}"
                if result.hocr_path:
                    extra += f" · {result.hocr_path.name}"
                if result.tsv_path:
                    extra += f" · {result.tsv_path.name}"
                self._set_status(
                    f"OCR → Word-Suite ({result.lang}, {result.mode.value}){extra}"
                )
                try:
                    from instantlensdoc.core.plugin_hooks import emit as emit_hook

                    emit_hook("ocr.finished", mode=result.mode.value, lang=result.lang)
                except Exception:
                    pass
                return

        if mode != ocr_mod.OcrOutputMode.TABLE_CSV and (result.text or "").strip():
            title_suffix = source_label
            if result.mode == ocr_mod.OcrOutputMode.LAYOUT_PRESERVE:
                title_suffix = f"Layout — {source_label}"
            if self.open_ocr_result(
                result=result,
                title=f"Word-Suite — {title_suffix}",
                auto_format=False,
                source_path=str(self.doc.path) if self.doc and self.doc.path else None,
            ):
                extra = ""
                if result.sidecar:
                    extra += f" · {Path(result.sidecar).name}"
                self._set_status(f"OCR → Word-Suite ({result.lang}, {result.mode.value}){extra}")
                return

        self.stack.setCurrentWidget(self.editor_pane)
        self.editor.setPlainText(result.text)
        title_suffix = "CSV" if result.mode == ocr_mod.OcrOutputMode.TABLE_CSV else source_label
        if result.mode == ocr_mod.OcrOutputMode.LAYOUT_PRESERVE:
            title_suffix = f"Layout — {source_label}"
        self.doc = Document(
            kind=DocKind.TEXT,
            title=f"OCR — {title_suffix}",
            text=result.text,
        )
        self.setWindowTitle(self._app_title(f"OCR — {title_suffix}"))
        extra = ""
        if result.searchable_pdf:
            extra = f" · PDF {result.searchable_pdf.name}"
            if result.sidecar:
                extra += f" + {result.sidecar.name}"
        elif result.mode == ocr_mod.OcrOutputMode.TABLE_CSV and result.sidecar:
            extra = f" · CSV {result.sidecar.name}"
        elif result.mode == ocr_mod.OcrOutputMode.LAYOUT_PRESERVE:
            n_blocks = len(result.blocks or [])
            extra = f" · {n_blocks} Block/Blöcke"
            if result.sidecar:
                extra += f" · {result.sidecar.name}"
            if result.hocr_path:
                extra += f" · {result.hocr_path.name}"
            if result.tsv_path:
                extra += f" · {result.tsv_path.name}"
        self._set_status(f"OCR ({result.lang}, {result.mode.value}){extra}")
        try:
            from instantlensdoc.core.plugin_hooks import emit as emit_hook

            emit_hook("ocr.finished", mode=result.mode.value, lang=result.lang)
        except Exception:
            pass

    def _run_ocr_document(self):
        """Batch-OCR aller PDF-Seiten mit Fortschrittsdialog."""
        from PySide6.QtWidgets import QApplication, QDialog, QProgressDialog

        if not self.doc or self.doc.kind != DocKind.PDF or not self.doc.path:
            self._feature_dialog("OCR gesamtes PDF", "Bitte zuerst ein PDF öffnen.")
            return

        ok, msg = ocr_mod.tesseract_available()
        # Seitenzahl vorab für Dialog (DPI + optional von–bis) — 1.1.2
        pdf_path = Path(self.doc.path)
        try:
            import pypdfium2 as pdfium

            from ild_pdf.pdfium_open import open_pdfium

            _doc = open_pdfium(pdf_path)
            total = len(_doc)
            _doc.close()
        except Exception:
            total = max(1, int(self.pdf_view.page_count or 1))

        try:
            dlg = OcrDialog(
                self,
                need_file=False,
                default_label=f"{Path(self.doc.path).name} (Batch)",
                page_count=total,
                show_page_range=True,
            )
        except Exception as e:
            self._feature_dialog("OCR gesamtes PDF", str(e))
            return
        # Batch-OCR: Sprach-Preset + DPI 150/300 + optional Seitenbereich — 1.1.2
        dlg.setWindowTitle("OCR gesamtes PDF — Sprach-Preset / DPI")
        dlg.rb_editable.setChecked(True)
        dlg.rb_searchable.setEnabled(False)
        if dlg.exec() != QDialog.Accepted:
            return
        if not ok:
            self._feature_dialog("OCR — Tesseract fehlt", msg)
            self._set_status("OCR nicht verfügbar")
            return

        lang = dlg.lang_code()
        dpi = dlg.dpi()
        page_from, page_to = dlg.page_range()
        attach_errors = dlg.attach_errors()
        try:
            from instantlensdoc.core.app_settings import (
                set_ocr_attach_errors,
                set_ocr_dpi,
                set_ocr_lang,
            )

            set_ocr_lang(lang)
            set_ocr_dpi(dpi)
            set_ocr_attach_errors(attach_errors)
        except Exception:
            pass
        cancelled = {"flag": False}

        range_hint = (
            f" S. {page_from}–{page_to}"
            if page_from is not None and page_to is not None
            else ""
        )
        prog = QProgressDialog(
            f"OCR gesamtes PDF ({dpi} DPI{range_hint})…",
            "Abbrechen",
            0,
            total,
            self,
        )
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
            prog.setLabelText(f"OCR: {pdf_path.name} — {label} @ {dpi} DPI")
            QApplication.processEvents()
            return True

        try:
            result = ocr_mod.ocr_pdf_document(
                pdf_path,
                lang=lang,
                dpi=dpi,
                page_from=page_from,
                page_to=page_to,
                attach_errors=attach_errors,
                progress=on_progress,
            )
        except ocr_mod.OcrUnavailable as e:
            self._feature_dialog("OCR — Tesseract fehlt", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "OCR gesamtes PDF", f"OCR fehlgeschlagen:\n{e}")
            return
        finally:
            prog.close()

        if result.cancelled or cancelled["flag"]:
            self._set_status(
                f"Batch-OCR abgebrochen — Teilergebnis "
                f"({result.pages_done}/{result.pages_total})"
                + (
                    f", {len(result.page_errors)} Fehler"
                    if result.page_errors
                    else ""
                )
            )
            if not (result.text or "").strip():
                return

        # Ergebnis als neue Textdatei-Tab (PDF-Tab bleibt) — 1.1.0
        out_txt = pdf_path.with_name(f"{pdf_path.stem}-ocr.txt")
        n = 1
        while out_txt.exists() and n < 1000:
            out_txt = pdf_path.with_name(f"{pdf_path.stem}-ocr-{n}.txt")
            n += 1
        try:
            out_txt.write_text(result.text, encoding="utf-8")
        except Exception as e:
            QMessageBox.warning(
                self,
                "OCR gesamtes PDF",
                f"OCR-Text konnte nicht gespeichert werden:\n{e}",
            )
            return
        opened = self.open_ocr_result(
            result=result,
            title=f"Word-Suite — {pdf_path.stem}",
            auto_format=True,
            source_path=str(pdf_path),
        )
        if not opened:
            opened = self._handoff_ocr_to_word_suite(
                path=out_txt,
                title=f"Word-Suite — {pdf_path.stem}",
                auto_format=True,
                source_path=str(pdf_path),
            )
        if not opened:
            self.open_path(str(out_txt))
        status = (
            f"Batch-OCR ({result.lang}, {result.dpi} DPI): "
            f"{result.pages_done}/{result.pages_total} Seiten"
            f" → Word-Suite {out_txt.name}"
        )
        if result.page_errors:
            status += f" · {len(result.page_errors)} Seitenfehler"
            if not attach_errors:
                status += " (nicht angehängt)"
        if result.cancelled:
            status += " (abgebrochen, Teilergebnis behalten)"
        self._set_status(status)

    def _ocr_region_text_preview(self, *, max_chars: int = 80) -> str:
        """Erste Zeilen des OCR-Region-Ergebnisses (ohne Fehlerabschnitt) — 2.5.9."""
        path = getattr(self, "_last_ocr_region_path", None)
        if not path:
            return ""
        p = Path(str(path))
        if not p.is_file():
            return ""
        try:
            body = p.read_text(encoding="utf-8")
        except Exception:
            return ""
        marker = "\n--- OCR-Fehler ---"
        if marker in body:
            body = body.split(marker, 1)[0]
        # Header-Zeile überspringen wenn vorhanden
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        if lines and lines[0].startswith("--- OCR Region"):
            lines = lines[1:]
        preview = " ".join(lines).strip()
        if not preview:
            return ""
        if len(preview) > max_chars:
            preview = preview[: max_chars - 1] + "…"
        return preview

    def _ocr_region_status_tooltip(self) -> str:
        """Status-Tooltip inkl. Textvorschau — 2.5.9–2.6.2."""
        path = getattr(self, "_last_ocr_region_path", None) or ""
        tip = (
            "Linksklick → Ergebnis-Tab · Rechtsklick → Menü · "
            "Mittelklick/Ctrl+Klick → Pfad · "
            "Shift+Klick → Text kopieren · "
            "Alt+Klick → Datei öffnen · "
            "Esc → Status schließen · "
            "Enter → Ergebnis-Tab · "
            "Ctrl+C Text · Ctrl+Shift+C Pfad · "
            "F4 → Ordner · F5 → Datei — 2.6.5"
        )
        if path:
            tip = f"{tip}\n{path}"
        preview = self._ocr_region_text_preview()
        if preview:
            tip = f"{tip}\nVorschau: {preview}"
        return tip

    def _dismiss_ocr_region_status(self) -> bool:
        """Esc / Menü: OCR-Region Status-Toast schließen — 2.5.11."""
        if not getattr(self, "_ocr_region_toast_active", False):
            return False
        self._ocr_region_toast_active = False
        try:
            sb = self.statusBar()
            if sb is not None:
                sb.clearMessage()
                sb.unsetCursor()
                sb.setToolTip("")
        except Exception:
            pass
        msg = "OCR-Region Status geschlossen"
        self._set_status(msg)
        try:
            self._announce_status_toast(msg)
        except Exception:
            pass
        return True

    def _show_ocr_region_status_menu(self) -> bool:
        """Status-Rechtsklick: Kontextmenü Tab/Ordner/Pfad/Text/Datei/Schließen — 2.5.10/2.5.11."""
        path = getattr(self, "_last_ocr_region_path", None)
        if not path and not getattr(self, "_ocr_region_toast_active", False):
            return False
        menu = QMenu(self)
        act_tab = menu.addAction("Ergebnis-Tab fokussieren\tEnter")
        act_folder = menu.addAction("Ordner öffnen\tF4")
        act_path = menu.addAction("Pfad kopieren\tCtrl+Shift+C")
        act_text = menu.addAction("Text kopieren\tCtrl+C")
        act_file = menu.addAction("Datei öffnen\tF5")
        menu.addSeparator()
        act_dismiss = menu.addAction("Status schließen\tEsc")
        if not path:
            for a in (act_tab, act_folder, act_path, act_text, act_file):
                a.setEnabled(False)
        # An Statusleiste verankern
        bar = self.statusBar()
        pos = bar.mapToGlobal(bar.rect().bottomLeft()) if bar is not None else None
        chosen = menu.exec(pos) if pos is not None else menu.exec()
        if chosen is act_tab:
            return self._focus_ocr_region_result_tab()
        if chosen is act_folder:
            return self._open_ocr_region_result_folder()
        if chosen is act_path:
            return self._copy_ocr_region_result_path()
        if chosen is act_text:
            return self._copy_ocr_region_result_text()
        if chosen is act_file:
            return self._open_ocr_region_result_file()
        if chosen is act_dismiss:
            return self._dismiss_ocr_region_status()
        return True  # Menü gezeigt (auch bei Abbruch)

    def _focus_ocr_region_result_tab(self) -> bool:
        """Status-Klick: OCR-Region Ergebnis-Tab fokussieren — 2.5.5."""
        path = getattr(self, "_last_ocr_region_path", None)
        if not path:
            msg = "OCR-Region Pfad fehlt"
            self._set_status(msg)
            # Fail-Path A11y Open-Pfad fehlt — 2.6.5
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        target = Path(str(path))
        if not target.is_file():
            msg = f"OCR-Region Ergebnis fehlt: {target.name}"
            self._set_status(msg)
            # Fail-Path A11y — 2.5.16
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        try:
            # Bereits offen → Tab wählen, sonst öffnen
            opened = False
            if hasattr(self, "sidebar") and self.sidebar is not None:
                for i in range(self.sidebar.files.count()):
                    it = self.sidebar.files.item(i)
                    if not it:
                        continue
                    p = it.data(256)
                    if p and str(Path(str(p))) == str(target):
                        self.sidebar.files.setCurrentItem(it)
                        opened = True
                        break
            if not opened:
                side = str((self.doc.meta or {}).get("sidecar") or "") if self.doc else ""
                already_ws = (
                    self.doc is not None
                    and self.doc.kind == DocKind.DOCX
                    and self.stack.currentWidget() is self.editor_pane
                    and (side == str(target) or "OCR" in (self.doc.title or ""))
                )
                if not already_ws:
                    if not self.open_ocr_result(
                        path=target,
                        title=f"Word-Suite — {target.stem}",
                        auto_format=False,
                    ):
                        self.open_path(str(target))
            self.stack.setCurrentWidget(self.editor_pane)
            self.editor.setFocus()
            self._set_status(f"OCR-Region Tab fokussiert: {target.name}")
            try:
                self._announce_status_toast(f"OCR-Region Tab: {target.name}")
            except Exception:
                pass
            return True
        except Exception:
            msg = f"OCR-Region Tab öffnen fehlgeschlagen: {target.name}"
            self._set_status(msg)
            # Fail-Path A11y Open-Exception — 2.6.5
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False

    def _open_ocr_region_result_folder(self) -> bool:
        """Status-Rechtsklick: OCR-Region Ergebnis-Ordner öffnen — 2.5.6."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        path = getattr(self, "_last_ocr_region_path", None)
        if not path:
            msg = "OCR-Region Pfad fehlt"
            self._set_status(msg)
            # Fail-Path A11y Open-Pfad fehlt — 2.6.5
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        target = Path(str(path))
        folder = target.parent if target.is_file() else target
        if not folder.is_dir():
            # Wie Text→PDF: fehlt → Neu anlegen anbieten
            return self._open_text_pdf_status_folder(folder)
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            self._set_status(f"OCR-Region Ordner geöffnet: {folder}")
            try:
                self._announce_status_toast(f"OCR-Region Ordner: {folder}")
            except Exception:
                pass
            return True
        except Exception:
            msg = f"OCR-Region Ordner öffnen fehlgeschlagen: {folder}"
            self._set_status(msg)
            # Fail-Path A11y Open-Exception — 2.6.5
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False

    def _open_ocr_region_result_file(self) -> bool:
        """Status-Alt+Klick: OCR-Region Ergebnisdatei mit Standardprogramm — 2.5.9."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        path = getattr(self, "_last_ocr_region_path", None)
        if not path:
            msg = "OCR-Region Pfad fehlt"
            self._set_status(msg)
            # Fail-Path A11y Open-Pfad fehlt — 2.6.5
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        target = Path(str(path))
        if not target.is_file():
            msg = f"OCR-Region Ergebnis fehlt: {target.name}"
            self._set_status(msg)
            # Fail-Path A11y — 2.5.16
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        except Exception:
            msg = f"OCR-Region Datei öffnen fehlgeschlagen: {target.name}"
            self._set_status(msg)
            # Fail-Path A11y Open-Exception — 2.6.5
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        self._ocr_region_toast_active = True
        msg = f"OCR-Region Datei geöffnet: {target.name}"
        self._set_status(msg)
        try:
            self._announce_status_toast(msg)
        except Exception:
            pass
        return True

    def _copy_ocr_region_result_path(self) -> bool:
        """Status-Mittelklick/Ctrl+Klick: OCR-Region Ergebnis-Pfad kopieren — 2.5.7."""
        path = getattr(self, "_last_ocr_region_path", None)
        if not path:
            msg = "OCR-Region Pfad fehlt"
            self._set_status(msg)
            # Fail-Path A11y Pfad-Copy — 2.5.18
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        text = str(path).strip()
        if not text:
            msg = "OCR-Region Pfad leer"
            self._set_status(msg)
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        try:
            from PySide6.QtWidgets import QApplication

            clip = QApplication.clipboard()
            if clip is None:
                msg = "OCR-Region Pfad: Zwischenablage nicht verfügbar"
                self._set_status(msg)
                try:
                    self._announce_status_toast(msg)
                except Exception:
                    pass
                return False
            clip.setText(text)
        except Exception:
            msg = "OCR-Region Pfad kopieren fehlgeschlagen"
            self._set_status(msg)
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        # Toast aktiv lassen (L/R bleiben nutzbar) — 2.5.7
        self._ocr_region_toast_active = True
        msg = f"OCR-Region Pfad kopiert: {Path(text).name}"
        self._set_status(msg)
        try:
            self._announce_status_toast(msg)
        except Exception:
            pass
        return True

    def _copy_ocr_region_result_text(self) -> bool:
        """Status-Shift+Klick: OCR-Region Ergebnistext in Zwischenablage — 2.5.8."""
        path = getattr(self, "_last_ocr_region_path", None)
        if not path:
            msg = "OCR-Region Text fehlt"
            self._set_status(msg)
            # Fail-Path A11y Text-Copy Clip/fehlt — 2.5.19
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        p = Path(str(path))
        if not p.is_file():
            msg = f"OCR-Region Ergebnis fehlt: {p.name}"
            self._set_status(msg)
            # Fail-Path A11y Text-Copy — 2.5.17
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        try:
            body = p.read_text(encoding="utf-8")
        except Exception:
            msg = f"OCR-Region Ergebnis fehlt: {p.name}"
            self._set_status(msg)
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        # Fehlerabschnitt weglassen (wie Batch-OCR) — 2.5.8
        marker = "\n--- OCR-Fehler ---"
        if marker in body:
            body = body.split(marker, 1)[0].rstrip()
        if not body.strip():
            msg = f"OCR-Region Text leer: {p.name}"
            self._set_status(msg)
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        try:
            from PySide6.QtWidgets import QApplication

            clip = QApplication.clipboard()
            if clip is None:
                msg = "OCR-Region Text: Zwischenablage nicht verfügbar"
                self._set_status(msg)
                # Fail-Path A11y Text-Copy Clip — 2.5.19
                try:
                    self._announce_status_toast(msg)
                except Exception:
                    pass
                return False
            clip.setText(body)
        except Exception:
            msg = "OCR-Region Text kopieren fehlgeschlagen"
            self._set_status(msg)
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass
            return False
        self._ocr_region_toast_active = True
        words = len([w for w in body.split() if w])
        msg = f"OCR-Region Text kopiert ({words} Wörter): {p.name}"
        self._set_status(msg)
        try:
            self._announce_status_toast(msg)
        except Exception:
            pass
        return True

    def _run_ocr_region(self):
        """OCR-Region: Rechteck → Defaults DPI/Sprache → Text-Tab — 2.5.1."""
        from instantlensdoc.core.app_settings import get_ocr_dpi, get_ocr_lang

        if not self._require_pdf("OCR Region"):
            return
        ok, msg = ocr_mod.tesseract_available()
        if not ok:
            self._feature_dialog("OCR — Tesseract fehlt", msg)
            self._set_status("OCR nicht verfügbar")
            return
        if not self.pdf_view.begin_ocr_region_select():
            self._feature_dialog("OCR Region", "Kein PDF geladen.")
            return
        self.stack.setCurrentWidget(self.pdf_view)
        self.pdf_view.setFocus()
        lang = get_ocr_lang()
        dpi = get_ocr_dpi()
        self._set_status(
            f"OCR-Region: Rechteck ziehen (Esc abbrechen) · Defaults {lang}, {dpi} DPI"
        )

    def _on_ocr_region_finished(
        self, page: int, x: float, y: float, w: float, h: float
    ) -> None:
        """Callback: Fortschritt · Tab Titel Seite/Region · Fehler anhängen — 2.5.2."""
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QLabel,
            QProgressDialog,
            QVBoxLayout,
        )

        from instantlensdoc.core.app_settings import (
            get_ocr_attach_errors,
            get_ocr_dpi,
            get_ocr_lang,
            set_ocr_attach_errors,
        )

        if not self.doc or self.doc.kind != DocKind.PDF or not self.doc.path:
            return
        pdf_path = Path(self.doc.path)
        # DPI/Sprache aus Settings-Defaults (kein Dialog) — 2.5.1
        lang = get_ocr_lang()
        dpi = get_ocr_dpi()
        page_1 = int(page) + 1
        rx, ry = int(round(float(x))), int(round(float(y)))
        rw, rh = max(1, int(round(float(w)))), max(1, int(round(float(h))))
        region_label = f"S.{page_1} Region {rx},{ry} {rw}×{rh}"

        # Fehler-anhängen-Toggle vor OCR (Settings-persistiert) — 2.5.2
        opt = QDialog(self)
        opt.setWindowTitle("OCR Region")
        opt_lay = QVBoxLayout(opt)
        opt_lay.addWidget(
            QLabel(
                f"OCR Region · {region_label}\n"
                f"Defaults: {lang}, {dpi} DPI"
            )
        )
        attach_cb = QCheckBox("Fehler anhängen")
        attach_cb.setToolTip(
            "OCR-Fehler als Abschnitt „OCR-Fehler“ an das Ergebnis-TXT anhängen "
            "(Einstellung wird gemerkt) — 2.5.2"
        )
        attach_cb.setChecked(get_ocr_attach_errors())
        opt_lay.addWidget(attach_cb)
        opt_btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        opt_btns.accepted.connect(opt.accept)
        opt_btns.rejected.connect(opt.reject)
        opt_lay.addWidget(opt_btns)
        if opt.exec() != QDialog.Accepted:
            self._set_status("OCR-Region abgebrochen")
            return
        attach_errors = bool(attach_cb.isChecked())
        try:
            set_ocr_attach_errors(attach_errors)
        except Exception:
            pass

        # Bestimmter Fortschritt: Vorbereiten → Rendern/OCR → Speichern — 2.5.2
        prog = QProgressDialog(
            f"OCR Region ({lang}, {dpi} DPI)…",
            "Abbrechen",
            0,
            3,
            self,
        )
        prog.setWindowTitle("OCR Region")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        prog.setCancelButtonText("Abbrechen")
        prog.setValue(0)
        prog.setLabelText(f"Vorbereiten… ({region_label})")
        prog.show()
        QApplication.processEvents()
        if prog.wasCanceled():
            prog.close()
            self._set_status("OCR-Region abgebrochen")
            return

        result = None
        ocr_error: str | None = None
        cancelled = False
        try:
            prog.setValue(1)
            prog.setLabelText(f"Region OCR… ({region_label} @ {dpi} DPI)")
            QApplication.processEvents()
            if prog.wasCanceled():
                cancelled = True
            else:
                result = ocr_mod.ocr_pdf_region(
                    pdf_path,
                    int(page),
                    (float(x), float(y), float(w), float(h)),
                    lang=lang,
                    dpi=dpi,
                    display_scale=float(getattr(self.pdf_view, "scale", 1.5) or 1.5),
                )
                prog.setValue(2)
                prog.setLabelText(f"Ergebnis speichern… ({region_label})")
                QApplication.processEvents()
                if prog.wasCanceled():
                    cancelled = True
        except ocr_mod.OcrUnavailable as e:
            prog.close()
            self._feature_dialog("OCR — Tesseract fehlt", str(e))
            return
        except Exception as e:
            ocr_error = str(e)
        finally:
            if prog.wasCanceled():
                cancelled = True
            if not cancelled:
                prog.setValue(3)
            prog.close()

        if cancelled:
            self._set_status("OCR-Region abgebrochen")
            return

        def _ocr_region_text_stats(raw: str) -> str:
            """Zeichen/Wörter ohne Header/Fehlerabschnitt — 2.5.4."""
            lines = (raw or "").splitlines()
            content_lines: list[str] = []
            in_errors = False
            for ln in lines:
                if ln.startswith("--- OCR-Fehler"):
                    in_errors = True
                    continue
                if in_errors:
                    continue
                if ln.startswith("--- OCR"):
                    continue
                if ln.strip():
                    content_lines.append(ln)
            content = "\n".join(content_lines).strip()
            words = len([w for w in content.split() if w])
            chars = len(content)
            return f"{words} Wörter · {chars} Zeichen"

        def _write_and_open(body: str, *, status_extra: str = "") -> None:
            out_txt = pdf_path.with_name(f"{pdf_path.stem}-ocr-region.txt")
            n = 1
            while out_txt.exists() and n < 1000:
                out_txt = pdf_path.with_name(f"{pdf_path.stem}-ocr-region-{n}.txt")
                n += 1
            try:
                out_txt.write_text(body, encoding="utf-8")
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "OCR Region",
                    f"OCR-Text konnte nicht gespeichert werden:\n{e}",
                )
                return
            if result is not None:
                try:
                    result.sidecar = out_txt
                except Exception:
                    pass
            opened = self.open_ocr_result(
                result=result,
                path=out_txt if result is None else None,
                text=body if result is None else None,
                title=f"Word-Suite — OCR {region_label}",
                auto_format=False,
                source_path=str(pdf_path),
                source_page=page_1,
            )
            if not opened:
                opened = self._handoff_ocr_to_word_suite(
                    text=body,
                    title=f"Word-Suite — OCR {region_label}",
                    auto_format=False,
                    source_path=str(pdf_path),
                    source_page=page_1,
                )
            if not opened:
                self.open_path(str(out_txt))
            # Tab-Titel: Ellipsis + Tooltip voll — 2.5.3
            full_title = f"OCR {region_label}"
            max_tab = 40
            tab_title = (
                full_title
                if len(full_title) <= max_tab
                else full_title[: max_tab - 1] + "…"
            )
            try:
                self.sidebar.set_document_label(str(out_txt), tab_title)
                target = str(out_txt)
                for i in range(self.sidebar.files.count()):
                    it = self.sidebar.files.item(i)
                    if not it:
                        continue
                    p = it.data(256)
                    if p and str(Path(str(p))) == target:
                        tip_parts = [str(p), f"Titel: {full_title}"]
                        it.setToolTip("\n".join(tip_parts))
                        break
            except Exception:
                pass
            self.setWindowTitle(self._app_title(full_title))
            # Zeichen/Wörter + A11y · Status-Klick → Tab — 2.5.4/2.5.5
            stats = _ocr_region_text_stats(body)
            msg = (
                f"OCR-Region ({lang}, {dpi} DPI) {region_label} → Tab „{tab_title}“"
            )
            if stats:
                msg += f" · {stats}"
            if status_extra:
                msg += f" · {status_extra}"
            self._last_ocr_region_path = str(out_txt)
            self._ocr_region_toast_active = True
            self._set_status(msg)
            try:
                self._announce_status_toast(msg)
            except Exception:
                pass

        if ocr_error:
            if attach_errors:
                # Fehlerabschnitt wie Batch-OCR — 2.5.3
                err_section = ocr_mod._format_ocr_errors_section(
                    [(page_1, str(ocr_error))]
                )
                err_body = f"--- OCR Region {region_label} ---\n\n{err_section}"
                _write_and_open(err_body, status_extra="Fehler angehängt")
            else:
                QMessageBox.warning(
                    self, "OCR Region", f"OCR fehlgeschlagen:\n{ocr_error}"
                )
            return

        assert result is not None
        text = (result.text or "").strip()
        if not text:
            # Leeres Ergebnis: Hinweis, kein leerer Tab — 2.5.1
            QMessageBox.information(
                self,
                "OCR Region",
                "Kein Text in der gewählten Region erkannt.\n"
                f"(Defaults: {lang}, {dpi} DPI — Einstellungen → OCR)",
            )
            self._set_status(
                f"OCR-Region: kein Text erkannt ({region_label}, {lang}, {dpi} DPI)"
            )
            return

        header = f"--- OCR Region {region_label} ({result.lang}, {dpi} DPI) ---\n\n"
        body = header + (result.text or "")
        if not body.endswith("\n"):
            body += "\n"
        _write_and_open(body)

    def _edit_doc_tags(self):
        """Dokument-Tags (ildtags-v1) bearbeiten — 2.5.0."""
        from PySide6.QtWidgets import QInputDialog

        from instantlensdoc.core import doc_tags as doc_tags_mod
        from instantlensdoc.core import recent_tags as recent_tags_mod

        if not self.doc or not self.doc.path:
            QMessageBox.information(
                self,
                "Dokument-Tags",
                "Bitte zuerst ein Dokument öffnen.",
            )
            return
        path = Path(self.doc.path)
        current = doc_tags_mod.load_tags_sidecar(path)
        suggestions = recent_tags_mod.load_recent_tags()
        tip = ""
        if suggestions:
            tip = "\nVorschläge: " + ", ".join(suggestions[:8])
        text, ok = QInputDialog.getText(
            self,
            "Dokument-Tags",
            f"Tags für {path.name} (Komma-getrennt):{tip}",
            text=", ".join(current),
        )
        if not ok:
            return
        tags = doc_tags_mod.normalize_doc_tags(text)
        try:
            doc_tags_mod.save_tags_sidecar(path, tags)
            for t in tags:
                try:
                    recent_tags_mod.add_recent_tag(t)
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.warning(self, "Dokument-Tags", str(e))
            return
        if hasattr(self, "welcome_page") and self.welcome_page is not None:
            try:
                self.welcome_page.refresh_recent()
            except Exception:
                pass
        label = ", ".join(tags) if tags else "(keine)"
        self._set_status(f"Dokument-Tags gespeichert: {label}")

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

        if not self._require_pdf("PDF bereinigen"):
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
