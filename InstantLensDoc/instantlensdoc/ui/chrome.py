"""Word/SoftMaker-Oberfläche: Klassisch / Ribbon / Kombiniert.

Default: Kombiniert (Pull-down-Menüs + Ribbon). Umschalten verwirft
kein offenes Dokument — nur Sichtbarkeit von Menüleiste und Ribbon.

Layout (diese Datei): Menü/Ribbon schrumpfen mit dem Fenster. Zu schmal:
horizontale Scrollbar, keine verlorenen Einträge. Overflow-» bleibt
Ribbon-Sache und löst die echte QAction aus.
"""

from __future__ import annotations

from typing import Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

ChromeMode = Literal["klassisch", "ribbon", "kombiniert"]

CHROME_KLASSISCH: ChromeMode = "klassisch"
CHROME_RIBBON: ChromeMode = "ribbon"
CHROME_KOMBINIERT: ChromeMode = "kombiniert"

CHROME_MODES: tuple[ChromeMode, ...] = (
    CHROME_KLASSISCH,
    CHROME_RIBBON,
    CHROME_KOMBINIERT,
)

CHROME_LABELS: dict[str, str] = {
    CHROME_KLASSISCH: "Klassisch (Pull-down)",
    CHROME_RIBBON: "Ribbon",
    CHROME_KOMBINIERT: "Kombiniert",
}

DEFAULT_CHROME_MODE: ChromeMode = CHROME_KOMBINIERT


def normalize_chrome_mode(value: object) -> ChromeMode:
    raw = str(value or "").strip().lower()
    aliases = {
        "classic": CHROME_KLASSISCH,
        "klassisch": CHROME_KLASSISCH,
        "pulldown": CHROME_KLASSISCH,
        "pull-down": CHROME_KLASSISCH,
        "menu": CHROME_KLASSISCH,
        "menus": CHROME_KLASSISCH,
        "ribbon": CHROME_RIBBON,
        "office": CHROME_RIBBON,
        "kombiniert": CHROME_KOMBINIERT,
        "combined": CHROME_KOMBINIERT,
        "both": CHROME_KOMBINIERT,
    }
    return aliases.get(raw, DEFAULT_CHROME_MODE)  # type: ignore[return-value]


def get_chrome_mode() -> ChromeMode:
    from instantlensdoc.core.app_settings import load_settings

    return normalize_chrome_mode(load_settings().get("chrome_mode", DEFAULT_CHROME_MODE))


def set_chrome_mode(mode: str) -> ChromeMode:
    from instantlensdoc.core.app_settings import save_settings

    resolved = normalize_chrome_mode(mode)
    save_settings(
        {
            "chrome_mode": resolved,
            "ribbon_visible": resolved != CHROME_KLASSISCH,
        }
    )
    return resolved


class HScrollHost(QScrollArea):
    """Chrome-Streifen: Inhalt behält Größe, bei zu schmalem Fenster Scrollbar."""

    def __init__(
        self,
        inner: QWidget,
        *,
        object_name: str = "ildChromeHScroll",
        widget_resizable: bool = False,
    ) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(bool(widget_resizable))
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setFocusPolicy(Qt.NoFocus)
        inner.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.setWidget(inner)
        self._inner = inner
        self._fit()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._fit()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._fit()

    def _fit(self) -> None:
        inner = getattr(self, "_inner", None)
        if inner is None:
            return
        hint = inner.sizeHint()
        min_h = max(hint.height(), inner.minimumSizeHint().height(), 24)
        vw = max(1, self.viewport().width())
        need = int(hint.width()) > int(vw)
        inner.setMinimumWidth(max(1, hint.width()))
        if not self.widgetResizable():
            inner.resize(max(int(hint.width()), vw), min_h)
        sbh = self.horizontalScrollBar().sizeHint().height() if need else 0
        self.setFixedHeight(min_h + sbh)


def wrap_hscroll(
    inner: QWidget,
    *,
    object_name: str,
    widget_resizable: bool = False,
) -> HScrollHost:
    return HScrollHost(
        inner, object_name=object_name, widget_resizable=widget_resizable
    )


def install_chrome_shrink_layout(window) -> None:
    """Menüleiste in horizontale Scrollbar legen — keine verlorenen Titel."""
    if getattr(window, "_ild_menubar_host", None) is not None:
        return
    if not hasattr(window, "menuBar"):
        return
    mb = window.menuBar()
    if mb is None:
        return
    try:
        mb.setNativeMenuBar(False)
    except Exception:
        pass
    host = wrap_hscroll(mb, object_name="ildMenuBarScroll")
    window._ild_chrome_menubar = mb
    window._ild_menubar_host = host
    try:
        window.setMenuWidget(host)
    except Exception:
        window._ild_menubar_host = None
        window._ild_chrome_menubar = None


def apply_chrome(window, mode: str | None = None) -> ChromeMode:
    """Menüleiste/Ribbon laut Modus — Dokument bleibt unangetastet."""
    resolved = normalize_chrome_mode(mode if mode is not None else get_chrome_mode())
    presentation = bool(getattr(window, "_presentation_active", False))
    menubar = window.menuBar() if hasattr(window, "menuBar") else None
    ribbon = getattr(window, "ribbon_bar", None)
    show_menu = (not presentation) and resolved in (CHROME_KLASSISCH, CHROME_KOMBINIERT)
    show_ribbon = (not presentation) and resolved in (CHROME_RIBBON, CHROME_KOMBINIERT)
    host = getattr(window, "_ild_menubar_host", None)
    if host is not None:
        host.setVisible(bool(show_menu))
    if menubar is not None:
        menubar.setVisible(bool(show_menu))
    if ribbon is not None:
        ribbon.setVisible(bool(show_ribbon))
    act = getattr(window, "_ribbon_action", None)
    if act is not None:
        try:
            act.blockSignals(True)
            act.setChecked(bool(show_ribbon))
            act.blockSignals(False)
        except Exception:
            pass
    group = getattr(window, "_chrome_mode_actions", None) or {}
    for key, action in group.items():
        try:
            action.blockSignals(True)
            action.setChecked(str(key) == resolved)
            action.blockSignals(False)
        except Exception:
            pass
    return resolved
