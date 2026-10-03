"""Gemeinsame Template-Reset- und Esc-Discard-Helfer — 2.1.5."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QLineEdit, QMessageBox, QWidget


def focus_line_edit_select_all(edit: QLineEdit) -> None:
    """Fokus + Selektion ganzer Text (Mess/Diff/Ann./Multi-Doc) — 2.1.5."""
    edit.setFocus(Qt.OtherFocusReason)
    edit.selectAll()


def reset_line_edit_template(
    parent: Optional[QWidget],
    edit: QLineEdit,
    default: str,
    *,
    title: str = "Reset Default",
    body_prefix: str,
    on_updated: Optional[Callable[[], None]] = None,
    after_focus: bool = True,
) -> bool:
    """
    Template auf Default; Bestätigung nur bei Abweichung;
    Leer/Whitespace ≡ Default (keine Bestätigung);
    danach optional Live-Update + Fokus mit Selektion — 2.1.5.

    Returns True wenn Default gesetzt (oder bereits Default), False bei Abbruch.
    """
    current = edit.text() or ""
    if current.strip() == "" or current == default:
        if current != default:
            edit.selectAll()
            edit.insert(default)
        if on_updated is not None:
            on_updated()
        if after_focus:
            QTimer.singleShot(0, lambda e=edit: focus_line_edit_select_all(e))
        return True
    reply = QMessageBox.question(
        parent,
        title,
        f"{body_prefix}\n\nAktuell: {current}\nDefault: {default}",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if reply != QMessageBox.Yes:
        if after_focus:
            QTimer.singleShot(0, lambda e=edit: focus_line_edit_select_all(e))
        return False
    # selectAll + insert → ein Undo-Schritt (Ctrl+Z)
    edit.selectAll()
    edit.insert(default)
    if on_updated is not None:
        on_updated()
    if after_focus:
        QTimer.singleShot(0, lambda e=edit: focus_line_edit_select_all(e))
    return True


class EscapeDiscardEditFilter(QObject):
    """
    Esc im Feld verwirft Edit (stellt committed-Text wieder her),
    speichert nicht — 2.1.5.

    Bei FocusIn wird der aktuelle Text als committed gemerkt.
    ``commit()`` manuell nach Reset/Quick-Insert/Accept aufrufen.
    """

    def __init__(
        self,
        edit: QLineEdit,
        *,
        on_discard: Optional[Callable[[], None]] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent if parent is not None else edit)
        self._edit = edit
        self._committed = edit.text() or ""
        self._on_discard = on_discard
        edit.installEventFilter(self)

    def commit(self, text: Optional[str] = None) -> None:
        """Aktuellen (oder übergebenen) Text als committed merken."""
        self._committed = (
            self._edit.text() if text is None else str(text)
        ) or ""

    def committed(self) -> str:
        return self._committed

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is not self._edit:
            return False
        et = event.type()
        if et == QEvent.Type.FocusIn:
            self._committed = self._edit.text() or ""
            return False
        if et == QEvent.Type.KeyPress and event.key() == Qt.Key_Escape:
            current = self._edit.text() or ""
            if current != self._committed:
                self._edit.setText(self._committed)
                if self._on_discard is not None:
                    self._on_discard()
                event.accept()
                return True
            # unverändert → Esc an Dialog weiterreichen (Schließen)
            return False
        return False
