"""Willkommens-/Startseite wenn keine Dokument-Tabs offen sind — 1.0.9."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc import __version__
from instantlensdoc.config import DISPLAY_NAME
from instantlensdoc.core import recent as recent_mod

_CONTINUE_PATH_SNIPPET_LEN = 48
_CONTINUE_TIP_MISSING = (
    "Keine Session-Datei — Weiterarbeiten nicht möglich — 1.0.9"
)
_CONTINUE_TIP_EMPTY = (
    "Session-Datei leer — keine wiederherstellbaren Tabs — 1.0.9"
)


def _path_snippet(path: str, max_len: int = _CONTINUE_PATH_SNIPPET_LEN) -> str:
    """Kurzes Pfad-Snippet (Ende bevorzugt) für Tooltips — 1.0.8."""
    p = str(path or "").strip()
    if not p:
        return ""
    if len(p) <= max_len:
        return p
    return "…" + p[-(max_len - 1) :]


def _session_file_status() -> tuple[bool, bool, list]:
    """
    Session-Datei-Status für Weiterarbeiten — 1.0.9.

    Rückgabe: ``(file_exists, file_nonempty, tabs)``.
    ``file_nonempty`` = Datei vorhanden und Inhalt (nicht nur Whitespace).
    """
    from instantlensdoc.core.session import load_session, session_path

    path = session_path()
    exists = path.is_file()
    nonempty = False
    if exists:
        try:
            nonempty = bool(path.read_text(encoding="utf-8").strip())
        except Exception:
            nonempty = False
    tabs: list = []
    try:
        tabs = list(load_session().tabs or [])
    except Exception:
        tabs = []
    return exists, nonempty, tabs


class WelcomePage(QWidget):
    """Startseite: Recent-Liste + Live-Filter + Weiterarbeiten (Session) + Aktionen."""

    open_requested = Signal()
    new_text_requested = Signal()
    recent_activated = Signal(str)
    recent_remove_requested = Signal(str)
    clear_recent_requested = Signal()
    files_dropped = Signal(list)  # list[str] lokale Dateipfade
    continue_session_requested = Signal()  # letzte Session-Tabs — 1.0.7–1.0.9

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._recent_entries: list[tuple[str, bool]] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 40, 48, 40)
        lay.setSpacing(12)

        title = QLabel(f"<h1>{DISPLAY_NAME}</h1>")
        title.setWordWrap(True)
        lay.addWidget(title)
        sub = QLabel(
            f"<p style='color:#555;'>Version {__version__} — Willkommen.<br>"
            "Kein Dokument geöffnet. Dateien per Drag &amp; Drop hierher ziehen, "
            "eine Aktion wählen oder einen Eintrag aus der Recent-Liste öffnen.</p>"
        )
        sub.setWordWrap(True)
        lay.addWidget(sub)

        btn_row = QHBoxLayout()
        self.btn_open = QPushButton("Dokument öffnen…")
        self.btn_open.setToolTip("Datei öffnen (PDF, Text, …)")
        self.btn_open.clicked.connect(self.open_requested.emit)
        btn_row.addWidget(self.btn_open)
        self.btn_empty = QPushButton("Leeres Text")
        self.btn_empty.setToolTip("Neues leeres Textdokument")
        self.btn_empty.clicked.connect(self.new_text_requested.emit)
        btn_row.addWidget(self.btn_empty)
        self.btn_continue = QPushButton("Weiterarbeiten")
        self.btn_continue.setToolTip(
            "Letzte Session-Tabs öffnen (wenn „Offene Tabs wiederherstellen“ aus) — 1.0.9"
        )
        self.btn_continue.clicked.connect(self.continue_session_requested.emit)
        self.btn_continue.setVisible(False)
        self.btn_continue.setEnabled(False)
        btn_row.addWidget(self.btn_continue)
        self.btn_clear_recent = QPushButton("Recent leeren")
        self.btn_clear_recent.setToolTip("Liste der zuletzt geöffneten Dateien leeren")
        self.btn_clear_recent.clicked.connect(self.clear_recent_requested.emit)
        btn_row.addWidget(self.btn_clear_recent)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

        lay.addWidget(QLabel("<b>Zuletzt geöffnet</b>"))
        filter_row = QHBoxLayout()
        self.recent_filter = QLineEdit()
        self.recent_filter.setPlaceholderText("Recent filtern (Pfad oder Tag)…")
        self.recent_filter.setClearButtonEnabled(True)
        self.recent_filter.setToolTip(
            "Live-Filter Pfad oder Dokument-Tags (ildtags-v1) · Tag-Vorschläge · "
            "Quick-Tag A–Z/Häufigkeit · Tags kopieren/einfügen (Ctrl+C/V) · "
            "Treffer A11y · Esc → Fokus Liste — 2.5.9"
        )
        self.recent_filter.textChanged.connect(self._apply_recent_filter)
        self.recent_filter.textChanged.connect(self._persist_recent_filter)
        self.recent_filter.installEventFilter(self)
        filter_row.addWidget(self.recent_filter, 1)
        # Quick-Tag-Filter A–Z/Häufigkeit · Tag-Anzahl (N Docs) — 2.5.5/2.5.6
        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.setMinimumWidth(160)
        self.tag_filter_combo.setToolTip(
            "Schnellfilter: bekanntes Dokument-Tag (A–Z oder Häufigkeit, N Docs) — 2.5.6"
        )
        self.tag_filter_combo.setAccessibleName("Quick-Tag-Filter")
        self.tag_filter_combo.activated.connect(self._on_tag_filter_chosen)
        filter_row.addWidget(self.tag_filter_combo)
        self.btn_tag_sort = QPushButton("A–Z")
        self.btn_tag_sort.setMinimumWidth(72)
        self.btn_tag_sort.setToolTip(
            "Quick-Tag Sortierung umschalten: A–Z ↔ Häufigkeit (persistiert) — 2.5.6"
        )
        self.btn_tag_sort.setAccessibleName("Quick-Tag Sortierung")
        self.btn_tag_sort.clicked.connect(self._toggle_tag_filter_sort)
        filter_row.addWidget(self.btn_tag_sort)
        self.btn_clear_filter = QPushButton("Filter Clear")
        self.btn_clear_filter.setToolTip(
            "Filter leeren (Clear) und Fokus zurück — Persistenz — 2.5.2"
        )
        self.btn_clear_filter.setAccessibleName("Filter Clear")
        self.btn_clear_filter.clicked.connect(self._clear_recent_filter)
        filter_row.addWidget(self.btn_clear_filter)
        self.filter_hits_label = QLabel("0 Treffer")
        self.filter_hits_label.setMinimumWidth(90)
        self.filter_hits_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.filter_hits_label.setStyleSheet("color: #555; padding-left: 6px;")
        self.filter_hits_label.setToolTip(
            "Trefferanzahl: angezeigte Treffer / Einträge in der Recent-Liste — 2.5.3"
        )
        self.filter_hits_label.setAccessibleName("Trefferanzahl Recent-Filter")
        self.filter_hits_label.setAccessibleDescription(
            "Recent-Filter Trefferanzahl: 0 Treffer"
        )
        filter_row.addWidget(self.filter_hits_label)
        lay.addLayout(filter_row)
        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(180)
        self.recent_list.setToolTip(
            "Enter / Doppelklick öffnet; Entf entfernt den Eintrag; "
            "Ctrl+C/V Tags kopieren/einfügen; "
            "Rechtsklick: Tag+/− · Tags kopieren/einfügen · Entfernen / Ordner; "
            "Quick-Tag A–Z/Häufigkeit (N Docs) · Treffer A11y · Esc → Fokus Liste — 2.5.9"
        )
        self.recent_list.setAcceptDrops(True)
        self.recent_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recent_list.customContextMenuRequested.connect(self._recent_context_menu)
        # itemActivated: Enter/Return (+ Doppelklick) — 1.0.3
        self.recent_list.itemActivated.connect(self._on_recent_dbl)
        self.recent_list.installEventFilter(self)
        lay.addWidget(self.recent_list, 1)

        self.refresh_recent()
        self.refresh_continue_button()
        # Persistierten Filter wiederherstellen — 2.5.1
        try:
            from instantlensdoc.core.app_settings import get_welcome_recent_filter

            saved = get_welcome_recent_filter()
            if saved:
                self.recent_filter.blockSignals(True)
                self.recent_filter.setText(saved)
                self.recent_filter.blockSignals(False)
                self._apply_recent_filter()
        except Exception:
            pass

    def refresh_continue_button(self) -> None:
        """Weiterarbeiten: disabled + Tooltip wenn Session fehlt/leer — 1.0.9."""
        show = False
        enabled = False
        tip = (
            "Letzte Session-Tabs öffnen (wenn „Offene Tabs wiederherstellen“ aus) — 1.0.9"
        )
        label = "Weiterarbeiten"
        try:
            from instantlensdoc.core.app_settings import get_restore_session_on_start

            if not get_restore_session_on_start():
                show = True
                exists, nonempty, tabs = _session_file_status()
                if not exists:
                    enabled = False
                    tip = _CONTINUE_TIP_MISSING
                elif not nonempty or not tabs:
                    enabled = False
                    tip = _CONTINUE_TIP_EMPTY
                else:
                    enabled = True
                    n = len(tabs)
                    label = f"Weiterarbeiten ({n})" if n > 0 else "Weiterarbeiten"
                    first = _path_snippet(getattr(tabs[0], "path", "") or "")
                    if n == 1:
                        tip = "Weiterarbeiten: 1 Tab"
                    else:
                        tip = f"Weiterarbeiten: {n} Tabs"
                    if first:
                        tip = f"{tip} — {first}"
                    tip += " (wenn „Offene Tabs wiederherstellen“ aus) — 1.0.9"
        except Exception:
            show = False
            enabled = False
            tip = _CONTINUE_TIP_MISSING
        self.btn_continue.setVisible(show)
        self.btn_continue.setEnabled(enabled)
        self.btn_continue.setText(label)
        self.btn_continue.setToolTip(tip)

    def eventFilter(self, obj, event):  # noqa: N802
        """Esc Filter; Del Recent; Shift+Del Tags; Ctrl+C/V/X Tags — 2.5.9–2.5.11."""
        if event.type() == QEvent.KeyPress:
            assert isinstance(event, QKeyEvent)
            key = event.key()
            if key == Qt.Key_Escape and obj in (self.recent_filter, self.recent_list):
                self._escape_recent_filter()
                return True
            if obj is self.recent_list:
                item = self.recent_list.currentItem()
                if item is not None and key in (Qt.Key_Return, Qt.Key_Enter):
                    self._on_recent_dbl(item)
                    return True
                if item is not None and key in (Qt.Key_Delete, Qt.Key_Backspace):
                    path = item.data(Qt.UserRole)
                    if path and bool(event.modifiers() & Qt.ShiftModifier):
                        # Shift+Entf/Backspace: Alle Tags entfernen — 2.5.11
                        self._clear_tags_for_recent(str(path))
                        return True
                    if path:
                        self.recent_remove_requested.emit(str(path))
                        return True
                # Ctrl+C / Ctrl+V / Ctrl+X: Tags kopieren/einfügen/ausschneiden — 2.5.9/2.5.10
                if item is not None and bool(event.modifiers() & Qt.ControlModifier):
                    path = item.data(Qt.UserRole)
                    if path and key == Qt.Key_C:
                        self._copy_tags_for_recent(str(path))
                        return True
                    if path and key == Qt.Key_V:
                        self._paste_tags_for_recent(str(path))
                        return True
                    if path and key == Qt.Key_X:
                        self._cut_tags_for_recent(str(path))
                        return True
        return super().eventFilter(obj, event)

    def refresh_recent(self) -> None:
        self._recent_entries = list(recent_mod.load_recent_entries())
        has_entries = bool(self._recent_entries)
        self.btn_clear_recent.setEnabled(has_entries)
        self.recent_filter.setEnabled(has_entries)
        self.btn_clear_filter.setEnabled(has_entries)
        if hasattr(self, "tag_filter_combo"):
            self.tag_filter_combo.setEnabled(has_entries)
        if hasattr(self, "btn_tag_sort"):
            self.btn_tag_sort.setEnabled(has_entries)
        self._refresh_tag_filter_combo()
        self._apply_recent_filter()
        self.refresh_continue_button()

    def _tag_filter_sort_mode(self) -> str:
        """Aktuelle Quick-Tag Sortierung (az|freq) — 2.5.6."""
        try:
            from instantlensdoc.core.app_settings import get_welcome_tag_filter_sort

            return get_welcome_tag_filter_sort()
        except Exception:
            return "az"

    def _sync_tag_sort_button(self) -> None:
        """Sort-Button Label/Tooltip an Mode anpassen — 2.5.6."""
        btn = getattr(self, "btn_tag_sort", None)
        if btn is None:
            return
        mode = self._tag_filter_sort_mode()
        if mode == "freq":
            btn.setText("Häufig")
            tip = "Sortierung: Häufigkeit (Klick → A–Z) — 2.5.6"
            desc = "Quick-Tag Sortierung: Häufigkeit absteigend"
        else:
            btn.setText("A–Z")
            tip = "Sortierung: A–Z (Klick → Häufigkeit) — 2.5.6"
            desc = "Quick-Tag Sortierung: alphabetisch A–Z"
        btn.setToolTip(tip)
        btn.setAccessibleName("Quick-Tag Sortierung")
        btn.setAccessibleDescription(desc)

    def _toggle_tag_filter_sort(self) -> None:
        """Quick-Tag Sort A–Z ↔ Häufigkeit umschalten — 2.5.6."""
        try:
            from instantlensdoc.core.app_settings import (
                get_welcome_tag_filter_sort,
                set_welcome_tag_filter_sort,
            )

            cur = get_welcome_tag_filter_sort()
            set_welcome_tag_filter_sort("az" if cur == "freq" else "freq")
        except Exception:
            pass
        self._refresh_tag_filter_combo()

    def _refresh_tag_filter_combo(self) -> None:
        """Quick-Tag-Filter: A–Z/Häufigkeit · Tag-Anzahl (N Docs) — 2.5.5/2.5.6."""
        combo = getattr(self, "tag_filter_combo", None)
        if combo is None:
            return
        current = str(combo.currentData() or "").strip()
        sort_mode = self._tag_filter_sort_mode()
        self._sync_tag_sort_button()
        # (display_label, tag_value, count)
        entries: list[tuple[str, str, int]] = []
        try:
            from instantlensdoc.core import doc_tags as doc_tags_mod
            from instantlensdoc.core import recent_tags as recent_tags_mod

            counted = list(
                doc_tags_mod.collect_known_tags_with_counts(
                    max_items=40, sort=sort_mode
                )
            )
            counts = {str(t).casefold(): int(n) for t, n in counted}
            known = [t for t, _n in counted]
            recent = list(recent_tags_mod.load_recent_tags())
            seen: set[str] = set()
            for t in known + recent:
                key = str(t).casefold()
                if key in seen:
                    continue
                seen.add(key)
                n = counts.get(key, 0)
                label = f"{t} ({n})" if n > 0 else str(t)
                entries.append((label, str(t), n))
            if sort_mode == "freq":
                entries.sort(key=lambda pair: (-int(pair[2]), pair[1].casefold()))
            else:
                entries.sort(key=lambda pair: pair[1].casefold())
        except Exception:
            entries = []
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("(Tag-Filter…)", "")
        for label, tag, _n in entries:
            combo.addItem(label, tag)
        if current:
            idx = combo.findData(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        combo.blockSignals(False)
        sort_label = "Häufigkeit" if sort_mode == "freq" else "A–Z"
        combo.setToolTip(
            f"Schnellfilter: bekanntes Dokument-Tag ({sort_label}, N Docs) — 2.5.6"
        )
        combo.setAccessibleName("Quick-Tag-Filter")
        combo.setAccessibleDescription(
            f"Dokument-Tags {sort_label} mit Anzahl Docs im Index"
        )

    def _on_tag_filter_chosen(self, index: int) -> None:
        """Quick-Tag gewählt → Filtertext setzen — 2.5.4."""
        combo = getattr(self, "tag_filter_combo", None)
        if combo is None:
            return
        tag = str(combo.itemData(index) or "").strip()
        if not tag:
            return
        self.recent_filter.setText(tag)
        self._persist_recent_filter(tag)
        self.recent_list.setFocus()

    def _persist_recent_filter(self, _text: str | None = None) -> None:
        """Welcome-Recent-Filter in Settings speichern — 2.5.1."""
        try:
            from instantlensdoc.core.app_settings import set_welcome_recent_filter

            set_welcome_recent_filter(self.recent_filter.text() or "")
        except Exception:
            pass

    def _reset_tag_filter_combo(self) -> None:
        """Quick-Tag-Combo auf Platzhalter zurücksetzen — 2.5.4."""
        combo = getattr(self, "tag_filter_combo", None)
        if combo is None:
            return
        combo.blockSignals(True)
        combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _clear_recent_filter(self) -> None:
        """Filter Clear: Text leeren + Persistenz + Fokus — 2.5.1."""
        self.recent_filter.clear()
        self._persist_recent_filter("")
        self._reset_tag_filter_combo()
        self.recent_filter.setFocus()

    def _escape_recent_filter(self) -> None:
        """Esc: Filter leeren und Fokus zurück auf die Recent-Liste — 2.5.2/2.5.3."""
        self.recent_filter.clear()
        self._persist_recent_filter("")
        self._reset_tag_filter_combo()
        self.recent_list.setFocus()
        if self.recent_list.count() > 0 and self.recent_list.currentRow() < 0:
            for i in range(self.recent_list.count()):
                it = self.recent_list.item(i)
                if it is not None and it.flags() & Qt.ItemIsEnabled and it.data(Qt.UserRole):
                    self.recent_list.setCurrentRow(i)
                    break
        # Fokus-Garantie: Liste aktiv — 2.5.3
        self.recent_list.setFocus()

    def _set_filter_hits_a11y(self, hits: str) -> None:
        """Trefferanzahl Text + AccessibleName/Description — 2.5.3."""
        self.filter_hits_label.setText(hits)
        self.filter_hits_label.setToolTip(
            f"Trefferanzahl: {hits} (Pfad oder Tag-Filter)"
        )
        self.filter_hits_label.setAccessibleName(f"Trefferanzahl: {hits}")
        self.filter_hits_label.setAccessibleDescription(
            f"Recent-Filter Trefferanzahl: {hits}"
        )

    def _apply_recent_filter(self, _text: str | None = None) -> None:
        """Live-Filter · Trefferanzahl A11y · fehlende getaggte Recent grau — 2.5.3."""
        self.recent_list.clear()
        entries = self._recent_entries
        total = len(entries)
        if not entries:
            item = QListWidgetItem("(keine zuletzt geöffneten Dateien)")
            item.setFlags(Qt.NoItemFlags)
            self.recent_list.addItem(item)
            self._set_filter_hits_a11y("0 Treffer")
            self.btn_clear_filter.setEnabled(False)
            return
        needle = (self.recent_filter.text() or "").strip().casefold()
        self.btn_clear_filter.setEnabled(bool(needle) or total > 0)
        # Tags für Recent-Pfade (Index + Sidecar) — 2.5.0
        tags_by_path: dict[str, list[str]] = {}
        try:
            from instantlensdoc.core import doc_tags as doc_tags_mod

            doc_tags_mod.refresh_index_for_paths([p for p, _ in entries])
            for path, _exists in entries:
                tags_by_path[str(path)] = doc_tags_mod.tags_for_path(path)
        except Exception:
            tags_by_path = {}
        shown = 0
        for path, exists in entries:
            hay = str(path).casefold()
            tags = tags_by_path.get(str(path)) or []
            tag_hay = " ".join(tags).casefold()
            if needle and needle not in hay and needle not in tag_hay:
                continue
            label = str(path) if exists else f"{path} (fehlt)"
            if tags:
                label = f"{label}  ·  {', '.join(tags[:6])}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, str(path))
            item.setData(Qt.UserRole + 1, bool(exists))
            item.setData(Qt.UserRole + 2, list(tags))
            if tags:
                tip = f"Tags: {', '.join(tags)}"
                if not exists:
                    tip = f"Datei fehlt · {tip}"
                item.setToolTip(tip)
            elif not exists:
                item.setToolTip("Datei fehlt")
            # Fehlende Recent (auch getaggte) grau — 2.5.2
            if not exists:
                item.setForeground(QColor("#888888"))
            self.recent_list.addItem(item)
            shown += 1
        if shown == 0:
            item = QListWidgetItem("(keine Treffer für Filter)")
            item.setFlags(Qt.NoItemFlags)
            self.recent_list.addItem(item)
        # Trefferanzahl + A11y — 2.5.3
        if needle:
            hits = f"{shown} / {total} Treffer"
        else:
            hits = f"{total} Treffer" if total != 1 else "1 Treffer"
        self._set_filter_hits_a11y(hits)

    def _on_recent_dbl(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if not path:
            return
        if not Path(str(path)).is_file():
            return
        self.recent_activated.emit(str(path))

    def _recent_context_menu(self, pos) -> None:
        item = self.recent_list.itemAt(pos)
        if item is None:
            return
        path = item.data(Qt.UserRole)
        if not path:
            return
        menu = QMenu(self)
        act_add_tag = menu.addAction("Tag hinzufügen…")
        act_remove_tag = menu.addAction("Tag entfernen…")
        act_clear_tags = menu.addAction("Alle Tags entfernen\tShift+Entf")
        act_copy_tags = menu.addAction("Tags kopieren")
        act_cut_tags = menu.addAction("Tags ausschneiden")
        act_paste_tags = menu.addAction("Tags einfügen")
        menu.addSeparator()
        act_remove = menu.addAction("Entfernen")
        act_folder = menu.addAction("Ordner öffnen")
        chosen = menu.exec(self.recent_list.mapToGlobal(pos))
        if chosen is act_add_tag:
            self._add_tag_for_recent(str(path))
        elif chosen is act_remove_tag:
            self._remove_tag_for_recent(str(path))
        elif chosen is act_clear_tags:
            self._clear_tags_for_recent(str(path))
        elif chosen is act_copy_tags:
            self._copy_tags_for_recent(str(path))
        elif chosen is act_cut_tags:
            self._cut_tags_for_recent(str(path))
        elif chosen is act_paste_tags:
            self._paste_tags_for_recent(str(path))
        elif chosen is act_remove:
            self.recent_remove_requested.emit(str(path))
        elif chosen is act_folder:
            self._open_containing_folder(str(path))

    def _add_tag_for_recent(self, path: str) -> None:
        """Dokument-Tag hinzufügen mit Vorschlägen (Recent/Index) — 2.5.4."""
        from PySide6.QtWidgets import QInputDialog, QMessageBox

        from instantlensdoc.core import doc_tags as doc_tags_mod
        from instantlensdoc.core import recent_tags as recent_tags_mod

        current = doc_tags_mod.load_tags_sidecar(path)
        suggestions: list[str] = []
        try:
            known = list(doc_tags_mod.collect_known_tags(max_items=32))
            recent = list(recent_tags_mod.load_recent_tags())
            seen: set[str] = {t.casefold() for t in current}
            for t in recent + known:
                key = str(t).casefold()
                if key in seen:
                    continue
                seen.add(key)
                suggestions.append(str(t))
        except Exception:
            suggestions = []
        if suggestions:
            text, ok = QInputDialog.getItem(
                self,
                "Tag hinzufügen",
                f"Tag für {Path(path).name} (Vorschläge oder neu):",
                suggestions,
                0,
                True,  # editable
            )
        else:
            text, ok = QInputDialog.getText(
                self,
                "Tag hinzufügen",
                f"Neuer Tag für {Path(path).name}:",
            )
        if not ok:
            return
        add = doc_tags_mod.normalize_doc_tags(text)
        if not add:
            return
        merged = doc_tags_mod.normalize_doc_tags(list(current) + list(add))
        try:
            doc_tags_mod.save_tags_sidecar(path, merged)
            for t in add:
                try:
                    recent_tags_mod.add_recent_tag(t)
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.warning(self, "Dokument-Tags", str(e))
            return
        self.refresh_recent()

    def _remove_tag_for_recent(self, path: str) -> None:
        """Dokument-Tag von Recent-Eintrag entfernen — 2.5.1."""
        from PySide6.QtWidgets import QInputDialog, QMessageBox

        from instantlensdoc.core import doc_tags as doc_tags_mod

        current = doc_tags_mod.load_tags_sidecar(path)
        if not current:
            QMessageBox.information(
                self, "Tag entfernen", "Keine Tags an diesem Dokument."
            )
            return
        chosen, ok = QInputDialog.getItem(
            self,
            "Tag entfernen",
            f"Tag entfernen von {Path(path).name}:",
            current,
            0,
            False,
        )
        if not ok or not chosen:
            return
        remaining = [t for t in current if t.casefold() != str(chosen).casefold()]
        try:
            doc_tags_mod.save_tags_sidecar(path, remaining)
        except Exception as e:
            QMessageBox.warning(self, "Dokument-Tags", str(e))
            return
        self.refresh_recent()

    def _copy_tags_for_recent(self, path: str) -> bool:
        """Alle Dokument-Tags des Recent-Eintrags in Zwischenablage — 2.5.7."""
        from PySide6.QtWidgets import QApplication, QMessageBox

        from instantlensdoc.core import doc_tags as doc_tags_mod

        current = doc_tags_mod.load_tags_sidecar(path)
        if not current:
            QMessageBox.information(
                self, "Tags kopieren", "Keine Tags an diesem Dokument."
            )
            return False
        text = ", ".join(str(t) for t in current)
        try:
            clip = QApplication.clipboard()
            if clip is None:
                raise RuntimeError("Zwischenablage nicht verfügbar")
            clip.setText(text)
        except Exception as e:
            QMessageBox.warning(self, "Tags kopieren", str(e))
            return False
        # Status über Parent-MainWindow wenn vorhanden — 2.5.7
        win = self.window()
        msg = f"Tags kopiert ({len(current)}): {text}"
        if win is not None and hasattr(win, "_set_status"):
            try:
                win._set_status(msg)
            except Exception:
                pass
        if win is not None and hasattr(win, "_announce_status_toast"):
            try:
                win._announce_status_toast(msg)
            except Exception:
                pass
        return True

    def _clear_tags_for_recent(self, path: str) -> bool:
        """Alle Dokument-Tags am Recent-Eintrag entfernen — 2.5.10."""
        from PySide6.QtWidgets import QMessageBox

        from instantlensdoc.core import doc_tags as doc_tags_mod

        current = doc_tags_mod.load_tags_sidecar(path)
        if not current:
            QMessageBox.information(
                self, "Tags entfernen", "Keine Tags an diesem Dokument."
            )
            return False
        n = len(current)
        try:
            doc_tags_mod.save_tags_sidecar(path, [])
        except Exception as e:
            QMessageBox.warning(self, "Tags entfernen", str(e))
            return False
        self.refresh_recent()
        win = self.window()
        msg = f"Alle Tags entfernt ({n}): {Path(path).name}"
        if win is not None and hasattr(win, "_set_status"):
            try:
                win._set_status(msg)
            except Exception:
                pass
        if win is not None and hasattr(win, "_announce_status_toast"):
            try:
                win._announce_status_toast(msg)
            except Exception:
                pass
        return True

    def _cut_tags_for_recent(self, path: str) -> bool:
        """Tags kopieren und am Dokument entfernen (Ctrl+X) — 2.5.10."""
        if not self._copy_tags_for_recent(path):
            return False
        # Ohne erneute „keine Tags“-Meldung leeren
        from instantlensdoc.core import doc_tags as doc_tags_mod

        try:
            current = doc_tags_mod.load_tags_sidecar(path)
            if not current:
                return True
            n = len(current)
            doc_tags_mod.save_tags_sidecar(path, [])
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Tags ausschneiden", str(e))
            return False
        self.refresh_recent()
        win = self.window()
        msg = f"Tags ausgeschnitten ({n}): {Path(path).name}"
        if win is not None and hasattr(win, "_set_status"):
            try:
                win._set_status(msg)
            except Exception:
                pass
        if win is not None and hasattr(win, "_announce_status_toast"):
            try:
                win._announce_status_toast(msg)
            except Exception:
                pass
        return True

    def _paste_tags_for_recent(self, path: str) -> None:
        """Zwischenablage-Tags (Komma/;/Zeile) an Dokument anhängen — 2.5.8."""
        from PySide6.QtWidgets import QApplication, QMessageBox

        from instantlensdoc.core import doc_tags as doc_tags_mod
        from instantlensdoc.core import recent_tags as recent_tags_mod

        try:
            clip = QApplication.clipboard()
            raw = (clip.text() if clip is not None else "") or ""
        except Exception:
            raw = ""
        # Zeilenumbrüche wie Komma behandeln — 2.5.8
        raw = raw.replace("\r\n", "\n").replace("\r", "\n").replace("\n", ",")
        add = doc_tags_mod.normalize_doc_tags(raw)
        if not add:
            QMessageBox.information(
                self,
                "Tags einfügen",
                "Zwischenablage enthält keine gültigen Tags "
                "(Komma, Semikolon oder Zeilen).",
            )
            return
        current = doc_tags_mod.load_tags_sidecar(path)
        before = {t.casefold() for t in current}
        merged = doc_tags_mod.normalize_doc_tags(list(current) + list(add))
        new_only = [t for t in merged if t.casefold() not in before]
        if not new_only:
            QMessageBox.information(
                self,
                "Tags einfügen",
                "Alle Tags aus der Zwischenablage sind bereits vorhanden.",
            )
            return
        try:
            doc_tags_mod.save_tags_sidecar(path, merged)
            for t in new_only:
                try:
                    recent_tags_mod.add_recent_tag(t)
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.warning(self, "Tags einfügen", str(e))
            return
        self.refresh_recent()
        win = self.window()
        text = ", ".join(new_only)
        msg = f"Tags eingefügt ({len(new_only)}): {text}"
        if win is not None and hasattr(win, "_set_status"):
            try:
                win._set_status(msg)
            except Exception:
                pass
        if win is not None and hasattr(win, "_announce_status_toast"):
            try:
                win._announce_status_toast(msg)
            except Exception:
                pass

    def _open_containing_folder(self, path: str) -> None:
        p = Path(path)
        folder = p if p.is_dir() else p.parent
        if not folder.is_dir():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _local_paths_from_mime(self, mime) -> list[str]:
        paths: list[str] = []
        if mime is None or not mime.hasUrls():
            return paths
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if path:
                paths.append(path)
        return paths

    def dragEnterEvent(self, event) -> None:
        if self._local_paths_from_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if self._local_paths_from_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        paths = self._local_paths_from_mime(event.mimeData())
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)
