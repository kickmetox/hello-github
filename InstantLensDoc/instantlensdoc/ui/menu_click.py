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
_BAR_FILTER: MenuBarExclusiveFilter | None = None


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


def _menubar_hits(mb: QMenuBar, pos) -> list[QAction]:
    """Alle Titel, deren Geometrie den Punkt enthält (überlappende Wrap-Hits)."""
    hits: list[QAction] = []
    try:
        for act in mb.actions():
            if act.menu() is None:
                continue
            g = mb.actionGeometry(act)
            if g.isValid() and g.contains(pos):
                hits.append(act)
    except Exception:
        hits = []
    if hits:
        return hits
    try:
        one = mb.actionAt(pos)
        if one is not None and one.menu() is not None:
            return [one]
    except Exception:
        pass
    return []


def _best_menubar_action(mb: QMenuBar, pos) -> QAction | None:
    hits = _menubar_hits(mb, pos)
    if not hits:
        return None
    hits.sort(key=lambda a: (mb.actionGeometry(a).width() * mb.actionGeometry(a).height(), mb.actionGeometry(a).x()))
    return hits[0]


def _popup_menubar_menu(mb: QMenuBar, act: QAction) -> None:
    menu = act.menu() if act is not None else None
    if menu is None:
        return
    close_other_menus(menu, menubar=mb)
    try:
        mb.setActiveAction(act)
    except Exception:
        pass
    geo = mb.actionGeometry(act)
    try:
        origin = mb.mapToGlobal(geo.bottomLeft()) if geo.isValid() else mb.mapToGlobal(QPoint(0, mb.height()))
    except Exception:
        origin = QCursor.pos()
    menu.popup(origin)


class MenuBarExclusiveFilter(QObject):
    """QMenuBar in QScrollArea verliert Qt-Exklusivität — ein Titel, ein Popup."""

    def eventFilter(self, obj, event):  # noqa: N802
        if isinstance(obj, QMenuBar) and event is not None:
            et = event.type()
            if et in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick):
                if not isinstance(event, QMouseEvent):
                    return False
                if event.button() != Qt.MouseButton.LeftButton:
                    return False
                pos = _event_pos(event)
                hit = _best_menubar_action(obj, pos)
                if hit is None or hit.menu() is None:
                    close_other_menus(None, menubar=obj)
                    return False
                menu = hit.menu()
                if menu.isVisible():
                    menu.hide()
                    try:
                        obj.setActiveAction(None)
                    except Exception:
                        pass
                    event.accept()
                    return True
                _popup_menubar_menu(obj, hit)
                event.accept()
                return True
            if et == QEvent.Type.MouseMove and isinstance(event, QMouseEvent):
                hit = _best_menubar_action(obj, _event_pos(event))
                if hit is None or hit.menu() is None:
                    return False
                cur = None
                try:
                    cur = obj.activeAction()
                except Exception:
                    cur = None
                cur_menu = cur.menu() if cur is not None else None
                if cur_menu is None or not cur_menu.isVisible():
                    return False
                if hit.menu() is cur_menu:
                    return False
                _popup_menubar_menu(obj, hit)
                event.accept()
                return True
        return super().eventFilter(obj, event)


class MenuClickFilter(QObject):
    """MouseButtonRelease auf QMenu → nur actionAt (kein Titel-Klick-Leak)."""

    def eventFilter(self, obj, event):  # noqa: N802
        if isinstance(obj, QMenu) and event is not None:
            et = event.type()
            if et == QEvent.Type.Show:
                prepare_menu_for_clicks(obj)
                close_other_menus(obj)
                return False
            if et == QEvent.Type.Hide:
                try:
                    obj.setProperty("ildMenuArmed", False)
                except Exception:
                    pass
                return False
            if et == QEvent.Type.MouseButtonPress and isinstance(event, QMouseEvent):
                if event.button() == Qt.MouseButton.LeftButton:
                    try:
                        obj.setProperty("ildMenuArmed", True)
                    except Exception:
                        pass
                return False
            if et == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
                if event.button() != Qt.MouseButton.LeftButton:
                    return False
                armed = False
                try:
                    armed = bool(obj.property("ildMenuArmed"))
                    obj.setProperty("ildMenuArmed", False)
                except Exception:
                    armed = False
                if not armed:
                    # Release stammt vom Menütitel (Press auf QMenuBar) — kein Blatt triggern.
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


def close_other_menus(keep: QMenu | None, *, menubar: QMenuBar | None = None) -> None:
    """Nur ``keep`` (plus Parent-/Kind-QMenus) bleibt sichtbar."""
    keep_ids: set[int] = set()
    cur: QWidget | None = keep
    while isinstance(cur, QMenu):
        keep_ids.add(id(cur))
        try:
            cur = cur.parentWidget()
        except Exception:
            break
    if keep is not None:
        try:
            for child in keep.findChildren(QMenu):
                keep_ids.add(id(child))
        except Exception:
            pass
    seen: set[int] = set()
    menus: list[QMenu] = []
    if menubar is not None:
        try:
            for act in menubar.actions():
                menu = act.menu() if hasattr(act, "menu") else None
                if isinstance(menu, QMenu):
                    menus.append(menu)
        except Exception:
            pass
    app = QApplication.instance()
    if app is not None:
        try:
            for w in app.allWidgets():
                if isinstance(w, QMenu):
                    menus.append(w)
        except Exception:
            pass
    for menu in menus:
        mid = id(menu)
        if mid in seen or mid in keep_ids:
            continue
        seen.add(mid)
        try:
            win = menu.window()
            from PySide6.QtWidgets import QFileDialog as _QFD

            if isinstance(win, _QFD):
                continue
        except Exception:
            pass
        try:
            if menu.isVisible():
                menu.hide()
        except Exception:
            continue


def bind_exclusive_menu(menu: QMenu) -> None:
    """aboutToShow schließt jedes andere Popup."""
    if menu is None or menu.property("ildExclusiveBound"):
        return
    menu.setProperty("ildExclusiveBound", True)
    menu.aboutToShow.connect(lambda m=menu: close_other_menus(m))


def mirror_menu_action(src: QAction, parent: QWidget | None = None) -> QAction:
    """Kopie für ein zweites Pulldown — gleicher Slot, keine gemeinsame QAction.

    Dieselbe QAction in zwei QMenuBar-Menüs lässt Qt alle zugehörigen Menüs
    gleichzeitig aufklappen (PDF/Format/Absatz/Seitenlayout/Fenster).
    """
    clone = QAction(src.text(), parent)
    try:
        clone.setIcon(src.icon())
    except Exception:
        pass
    clone.setToolTip(src.toolTip())
    clone.setStatusTip(src.statusTip())
    clone.setEnabled(src.isEnabled())
    clone.setVisible(src.isVisible())
    clone.setCheckable(src.isCheckable())
    if src.isCheckable():
        clone.setChecked(src.isChecked())
    clone.setProperty("ildMirrorOf", src)
    try:
        for key in ("ildPdfNeed", "ildAvailTip", "ild_i18n_src"):
            val = src.property(key)
            if val not in (None, ""):
                clone.setProperty(key, val)
    except Exception:
        pass

    def _sync(*_a) -> None:
        try:
            clone.setText(src.text())
            clone.setToolTip(src.toolTip())
            clone.setEnabled(src.isEnabled())
            clone.setVisible(src.isVisible())
            if src.isCheckable():
                clone.blockSignals(True)
                clone.setChecked(src.isChecked())
                clone.blockSignals(False)
        except RuntimeError:
            pass

    try:
        src.changed.connect(_sync)
    except Exception:
        pass
    clone.triggered.connect(lambda _checked=False: src.trigger())
    return clone


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
        _cap_menu_height(menu)
        return
    menu.setStyle(_scroll_style())
    menu.setProperty("ildScrollableMenu", True)
    _cap_menu_height(menu)


def _cap_menu_height(menu: QMenu) -> None:
    app = QApplication.instance()
    screen = app.primaryScreen() if app is not None else None
    if screen is not None:
        cap = max(160, int(screen.availableGeometry().height() * 0.55))
    else:
        cap = 360
    try:
        menu.setMaximumHeight(cap)
    except Exception:
        pass


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
    global _FILTER, _BAR_FILTER
    app = QApplication.instance()
    if _FILTER is None:
        parent = app if app is not None else root
        _FILTER = MenuClickFilter(parent)
        if app is not None:
            app.installEventFilter(_FILTER)
    if _BAR_FILTER is None:
        parent = app if app is not None else root
        _BAR_FILTER = MenuBarExclusiveFilter(parent)
    mb = root.menuBar() if isinstance(root, QMainWindow) else None
    if mb is None and isinstance(root, QMenuBar):
        mb = root
    if mb is not None:
        try:
            mb.setMouseTracking(True)
            mb.installEventFilter(_BAR_FILTER)
        except Exception:
            pass
        for act in mb.actions():
            menu = act.menu() if hasattr(act, "menu") else None
            if menu is not None:
                bind_exclusive_menu(menu)
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
    # QTest liefert an dieses QMenu; MenuClickFilter nimmt nur actionAt.
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
    qactions: dict | None = None,
) -> QMenu | None:
    """Einspaltiges QMenu (actionAt). Overflow löst die echte QAction aus."""
    specs = [(str(a), str(lbl)) for a, lbl in (items or ()) if a]
    if not specs:
        return None
    menu = QMenu(parent)
    menu.setObjectName("ildScrollableActionMenu")
    prepare_menu_for_clicks(menu)
    mapping = qactions or {}
    for aid, label in specs:
        real = mapping.get(aid)
        act = QAction(str(label or aid), menu)
        act.setObjectName(f"ildOverflowAction_{aid}")
        act.setProperty("ribbonActionId", aid)
        if real is not None:
            try:
                act.setEnabled(bool(real.isEnabled()))
            except Exception:
                pass
            try:
                tip = real.toolTip() or ""
                if tip:
                    act.setToolTip(str(tip))
            except Exception:
                pass
            act.triggered.connect(real.trigger)
        elif on_pick is not None:
            act.triggered.connect(lambda _=False, a=aid: on_pick(a))
        menu.addAction(act)
    where = pos
    if where is None:
        where = QCursor.pos()
    menu.popup(where)
    menu.show()
    app = QApplication.instance()
    if app is not None:
        app.processEvents()
    return menu
