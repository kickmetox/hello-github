"""QMenu-Mausklick: eine scrollbare Spalte, Release löst denselben Slot wie das Kürzel."""

from __future__ import annotations

from typing import Callable, Iterator, Sequence

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QAction, QCursor, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QMainWindow,
    QMenu,
    QMenuBar,
    QProxyStyle,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

_SCROLL_HINT = int(getattr(QStyle.StyleHint, "SH_Menu_Scrollable", 30))
_STYLE: ScrollableMenuStyle | None = None
_FILTER: MenuClickFilter | None = None


class ScrollableMenuStyle(QProxyStyle):
    """SH_Menu_Scrollable: keine zweite, oft abgeschnittene Menüspalte."""

    def styleHint(self, hint, option=None, widget=None, returnData=None):  # noqa: N802
        try:
            if int(hint) == _SCROLL_HINT:
                return 1
        except Exception:
            pass
        if returnData is None:
            return super().styleHint(hint, option, widget)
        return super().styleHint(hint, option, widget, returnData)


class MenuClickFilter(QObject):
    """MouseButtonRelease auf QMenu → actionAt + trigger (gleicher Slot wie Shortcut)."""

    def eventFilter(self, obj, event):  # noqa: N802
        if isinstance(obj, QMenu) and event is not None:
            et = event.type()
            if et == QEvent.Type.Show:
                prepare_menu_for_clicks(obj)
                return False
            if et == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
                if event.button() != Qt.MouseButton.LeftButton:
                    return False
                act = _action_at(obj, event)
                if act is None:
                    act = obj.activeAction()
                elif not obj.rect().contains(_event_pos(event)):
                    highlighted = obj.activeAction()
                    if highlighted is not None:
                        act = highlighted
                if act is None or not act.isEnabled() or act.isSeparator():
                    return False
                if act.menu() is not None:
                    return False
                obj.hide()
                act.trigger()
                event.accept()
                return True
        return super().eventFilter(obj, event)


def _scroll_style() -> ScrollableMenuStyle:
    global _STYLE
    if _STYLE is None:
        app = QApplication.instance()
        base = app.style() if app is not None else None
        _STYLE = ScrollableMenuStyle(base)
    return _STYLE


def prepare_menu_for_clicks(menu: QMenu) -> None:
    """Eine Spalte, scrollbar — keine abgeschnittene zweite Spalte."""
    if menu.property("ildScrollableMenu"):
        return
    menu.setStyle(_scroll_style())
    menu.setProperty("ildScrollableMenu", True)


def _event_pos(event: QMouseEvent):
    if hasattr(event, "position"):
        return event.position().toPoint()
    return event.pos()


def _action_at(menu: QMenu, event: QMouseEvent) -> QAction | None:
    try:
        return menu.actionAt(_event_pos(event))
    except Exception:
        return None


def apply_clickable_popup_menus(root: QWidget) -> None:
    """Filter + Scroll-Style auf Menüleiste und alle QMenu-Kinder."""
    global _FILTER
    app = QApplication.instance()
    if _FILTER is None:
        parent = app if app is not None else root
        _FILTER = MenuClickFilter(parent)
        if app is not None:
            app.installEventFilter(_FILTER)
    prepare_all_menus(root)


def prepare_all_menus(root: QWidget) -> None:
    if isinstance(root, QMenu):
        prepare_menu_for_clicks(root)
        return
    mb = root.menuBar() if isinstance(root, QMainWindow) else None
    if mb is None and isinstance(root, QMenuBar):
        mb = root
    if mb is not None:
        for act in mb.actions():
            menu = act.menu() if hasattr(act, "menu") else None
            if menu is not None:
                _prepare_tree(menu)
    for menu in root.findChildren(QMenu):
        prepare_menu_for_clicks(menu)


def _prepare_tree(menu: QMenu) -> None:
    prepare_menu_for_clicks(menu)
    for act in menu.actions():
        sub = act.menu() if hasattr(act, "menu") else None
        if sub is not None:
            _prepare_tree(sub)


def find_menubar_menu(win: QWidget, title: str) -> QMenu | None:
    want = title.replace("&", "").strip().lower()
    mb = win.menuBar() if hasattr(win, "menuBar") else None
    if mb is None:
        return None
    for act in mb.actions():
        menu = act.menu() if hasattr(act, "menu") else None
        if menu is None:
            continue
        got = (menu.title() or act.text() or "").replace("&", "").strip().lower()
        if got == want:
            return menu
    return None


def iter_leaf_actions(
    menu: QMenu, path: str = ""
) -> Iterator[tuple[str, QMenu, QAction]]:
    prefix = path or (menu.title() or "").replace("&", "").strip()
    for act in menu.actions():
        if act.isSeparator():
            continue
        text = (act.text() or "").replace("&", "").strip()
        sub = act.menu() if hasattr(act, "menu") else None
        leaf_path = f"{prefix} ▸ {text}" if prefix else text
        if sub is not None:
            yield from iter_leaf_actions(sub, leaf_path)
            continue
        yield leaf_path, menu, act


def mouse_click_menu_action(app, menu: QMenu, action: QAction) -> bool:
    """Popup, Aktion in den sichtbaren Bereich, QTest.mouseClick auf actionGeometry."""
    from PySide6.QtTest import QTest

    if app is None:
        app = QApplication.instance()
    prepare_menu_for_clicks(menu)
    try:
        menu.hide()
    except Exception:
        pass
    if app is not None:
        app.processEvents()
    origin = QPoint(48, 48)
    parent = menu.parentWidget()
    if parent is not None:
        try:
            origin = parent.mapToGlobal(QPoint(24, 24))
        except Exception:
            origin = QPoint(48, 48)
    menu.popup(origin)
    menu.show()
    if app is not None:
        app.processEvents()
    try:
        menu.setActiveAction(action)
    except Exception:
        pass
    if app is not None:
        app.processEvents()
    geo = menu.actionGeometry(action)
    if not geo.isValid() or geo.width() <= 0 or geo.height() <= 0:
        menu.hide()
        return False
    center = geo.center()
    if not menu.rect().contains(center):
        try:
            menu.setActiveAction(action)
        except Exception:
            pass
        if app is not None:
            app.processEvents()
        geo = menu.actionGeometry(action)
        center = geo.center()
    # Overflow-Spalte: local pos darf außerhalb von menu.rect() liegen —
    # QTest liefert an dieses QMenu; MenuClickFilter nimmt actionAt/activeAction.
    QTest.mouseClick(
        menu,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        center,
    )
    if app is not None:
        app.processEvents()
    if menu.isVisible():
        menu.hide()
        if app is not None:
            app.processEvents()
    return True


ActionSpec = tuple[str, str]  # (action_id, label)


class ScrollableActionMenu(QFrame):
    """Ribbon-Overflow: eine Spalte, scrollbar — keine toten Hits."""

    action_chosen = Signal(str)

    def __init__(
        self,
        items: Sequence[ActionSpec],
        parent: QWidget | None = None,
        *,
        max_height: int = 360,
    ) -> None:
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("ildScrollableActionMenu")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setStyleSheet(
            "#ildScrollableActionMenu {"
            " background: #FFFFFF; border: 1px solid #8FA3C0;"
            "}"
            "QToolButton#ildOverflowItem {"
            " text-align: left; padding: 6px 12px; border: none;"
            " background: transparent;"
            "}"
            "QToolButton#ildOverflowItem:hover { background: #D9E6F8; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(0)
        scroll = QScrollArea()
        scroll.setObjectName("ildOverflowScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        self._buttons: list[QToolButton] = []
        for aid, label in items:
            tb = QToolButton()
            tb.setObjectName("ildOverflowItem")
            tb.setText(str(label or aid))
            tb.setToolButtonStyle(Qt.ToolButtonTextOnly)
            tb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            tb.setCursor(Qt.PointingHandCursor)
            tb.clicked.connect(lambda _=False, a=str(aid): self._pick(a))
            col.addWidget(tb)
            self._buttons.append(tb)
        col.addStretch(1)
        scroll.setWidget(inner)
        root.addWidget(scroll)
        hint_h = max(28, len(items) * 28 + 8)
        self.setFixedWidth(220)
        self.setFixedHeight(min(int(max_height), hint_h + 6))

    def _pick(self, action_id: str) -> None:
        self.action_chosen.emit(action_id)
        self.close()


def show_scrollable_menu(
    items: Sequence[ActionSpec],
    parent: QWidget | None = None,
    *,
    pos: QPoint | None = None,
    on_pick: Callable[[str], None] | None = None,
) -> ScrollableActionMenu | None:
    """Popup an ``pos`` (global) oder Cursor. Leere Listen werden ignoriert."""
    specs = [(str(a), str(lbl)) for a, lbl in (items or ()) if a]
    if not specs:
        return None
    menu = ScrollableActionMenu(specs, parent)
    if on_pick is not None:
        menu.action_chosen.connect(on_pick)
    where = pos
    if where is None:
        where = QCursor.pos()
    menu.move(where)
    menu.show()
    menu.raise_()
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
    return menu
