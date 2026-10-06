"""QMenu-Mausklick: eine scrollbare Spalte, Release löst denselben Slot wie das Kürzel."""

from __future__ import annotations

from typing import Iterator

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QMenuBar,
    QProxyStyle,
    QStyle,
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


def _max_menu_height() -> int:
    app = QApplication.instance()
    h = 720
    if app is not None:
        screen = app.primaryScreen()
        if screen is not None:
            try:
                h = int(screen.availableGeometry().height())
            except Exception:
                h = int(screen.geometry().height())
    return max(240, h - 64)


def prepare_menu_for_clicks(menu: QMenu) -> None:
    """Eine Spalte, scrollbar, Höhe ≤ Bildschirm — Klickflächen bleiben im Widget."""
    if menu.property("ildScrollableMenu"):
        menu.setMaximumHeight(_max_menu_height())
        return
    menu.setStyle(_scroll_style())
    menu.setMaximumHeight(_max_menu_height())
    menu.setProperty("ildScrollableMenu", True)


def _action_at(menu: QMenu, event: QMouseEvent) -> QAction | None:
    if hasattr(event, "position"):
        pt = event.position().toPoint()
    else:
        pt = event.pos()
    try:
        return menu.actionAt(pt)
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
