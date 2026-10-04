"""Dialog: Gemeinsames Review starten/beitreten — 2.6.25."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from instantlensdoc.core.i18n import tr
from instantlensdoc.core.shared_review import (
    LIMITATIONS_DE,
    POLL_DEFAULT_SEC,
    join_shared_review,
    shared_review_status,
    start_shared_review,
    sync_shared_review,
)


class SharedReviewDialog(QDialog):
    """UI: Review-Session starten / beitreten / syncen (Ordner + optional Endpoint)."""

    def __init__(
        self,
        doc_path: str | Path,
        parent=None,
        *,
        author: str = "local",
        on_synced: Optional[Callable[[dict], None]] = None,
    ):
        super().__init__(parent)
        self.doc_path = Path(doc_path)
        self._author_default = str(author or "local").strip() or "local"
        self._on_synced = on_synced
        self._active_share: Path | None = None
        self.setWindowTitle(
            tr("shared_review") or "Gemeinsames Review / Cloud-Ordner"
        )
        self.setWindowModality(Qt.WindowModal)
        self.resize(620, 560)
        self.setObjectName("ildSharedReviewDialog")

        layout = QVBoxLayout(self)
        self.lbl_doc = QLabel(f"Dokument: {self.doc_path.name}")
        self.lbl_doc.setObjectName("sharedReviewDocLabel")
        layout.addWidget(self.lbl_doc)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_start_tab(), tr("shared_review_start") or "Starten")
        self.tabs.addTab(self._build_join_tab(), tr("shared_review_join") or "Beitreten")
        self.tabs.addTab(self._build_active_tab(), tr("shared_review_active") or "Aktiv")
        layout.addWidget(self.tabs, 1)

        lim_box = QGroupBox(tr("shared_review_limits") or "Einschränkungen")
        lim_l = QVBoxLayout(lim_box)
        self.txt_limits = QTextEdit()
        self.txt_limits.setReadOnly(True)
        self.txt_limits.setMaximumHeight(110)
        self.txt_limits.setPlainText(LIMITATIONS_DE)
        self.txt_limits.setObjectName("sharedReviewLimits")
        lim_l.addWidget(self.txt_limits)
        layout.addWidget(lim_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._poll = QTimer(self)
        self._poll.timeout.connect(self._auto_sync)
        self._refresh_active()

    def _build_start_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.ed_start_folder = QLineEdit()
        self.ed_start_folder.setPlaceholderText(
            tr("shared_review_folder_hint")
            or "Freigabeordner (NAS / OneDrive / SMB)…"
        )
        btn_browse = QPushButton(tr("pick_dir") or "Ordner wählen")
        btn_browse.clicked.connect(self._browse_start)
        row = QHBoxLayout()
        row.addWidget(self.ed_start_folder, 1)
        row.addWidget(btn_browse)
        form.addRow(tr("shared_review_folder") or "Freigabeordner:", row)

        self.ed_start_author = QLineEdit(self._author_default)
        form.addRow(tr("review_author") or "Autor:", self.ed_start_author)

        self.ed_start_title = QLineEdit(self.doc_path.stem)
        form.addRow(tr("field_title") or "Titel:", self.ed_start_title)

        self.ed_start_endpoint = QLineEdit()
        self.ed_start_endpoint.setPlaceholderText(
            tr("shared_review_endpoint_hint")
            or "Optional: https://host/review-bundle.json"
        )
        form.addRow(tr("shared_review_endpoint") or "Cloud-Endpoint:", self.ed_start_endpoint)

        btn_start = QPushButton(tr("shared_review_start_btn") or "Session starten")
        btn_start.setObjectName("btnSharedReviewStart")
        btn_start.clicked.connect(self._do_start)
        form.addRow(btn_start)
        return w

    def _build_join_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.ed_join_folder = QLineEdit()
        self.ed_join_folder.setPlaceholderText(
            tr("shared_review_join_hint")
            or "Freigabeordner oder session.ildshare.json…"
        )
        btn_browse = QPushButton(tr("pick_dir") or "Ordner wählen")
        btn_browse.clicked.connect(self._browse_join)
        row = QHBoxLayout()
        row.addWidget(self.ed_join_folder, 1)
        row.addWidget(btn_browse)
        form.addRow(tr("shared_review_folder") or "Freigabeordner:", row)

        self.ed_join_author = QLineEdit(self._author_default)
        form.addRow(tr("review_author") or "Autor:", self.ed_join_author)

        btn_join = QPushButton(tr("shared_review_join_btn") or "Session beitreten")
        btn_join.setObjectName("btnSharedReviewJoin")
        btn_join.clicked.connect(self._do_join)
        form.addRow(btn_join)
        return w

    def _build_active_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.lbl_status = QLabel(tr("shared_review_none") or "Keine aktive Session.")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setObjectName("sharedReviewStatus")
        layout.addWidget(self.lbl_status)

        self.txt_status = QTextEdit()
        self.txt_status.setReadOnly(True)
        self.txt_status.setObjectName("sharedReviewStatusDetail")
        layout.addWidget(self.txt_status, 1)

        row = QHBoxLayout()
        self.chk_auto = QCheckBox(
            tr("shared_review_auto") or "Auto-Sync (Polling)"
        )
        self.chk_auto.toggled.connect(self._toggle_auto)
        row.addWidget(self.chk_auto)
        row.addWidget(QLabel(tr("shared_review_interval") or "Intervall (s):"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(3, 120)
        self.spin_interval.setValue(POLL_DEFAULT_SEC)
        self.spin_interval.valueChanged.connect(self._retune_poll)
        row.addWidget(self.spin_interval)
        row.addStretch(1)
        layout.addLayout(row)

        btn_row = QHBoxLayout()
        btn_sync = QPushButton(tr("shared_review_sync") or "Jetzt synchronisieren")
        btn_sync.setObjectName("btnSharedReviewSync")
        btn_sync.clicked.connect(self._do_sync)
        btn_row.addWidget(btn_sync)
        btn_leave = QPushButton(tr("shared_review_leave") or "Session verlassen")
        btn_leave.clicked.connect(self._leave)
        btn_row.addWidget(btn_leave)
        layout.addLayout(btn_row)
        return w

    def _browse_start(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, tr("pick_dir") or "Ordner wählen", self.ed_start_folder.text()
        )
        if d:
            self.ed_start_folder.setText(d)

    def _browse_join(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("shared_review_open_bundle") or "Session öffnen",
            self.ed_join_folder.text(),
            "ILD Share (*.ildshare.json);;Alle Dateien (*)",
        )
        if path:
            self.ed_join_folder.setText(path)
            return
        d = QFileDialog.getExistingDirectory(
            self, tr("pick_dir") or "Ordner wählen", self.ed_join_folder.text()
        )
        if d:
            self.ed_join_folder.setText(d)

    def _activate(self, share: str | Path, result: dict) -> None:
        self._active_share = Path(share)
        self.tabs.setCurrentIndex(2)
        self._show_result(result)
        self._refresh_active()
        if self._on_synced:
            try:
                self._on_synced(result)
            except Exception:
                pass

    def _do_start(self) -> None:
        folder = self.ed_start_folder.text().strip()
        if not folder:
            QMessageBox.warning(
                self,
                tr("shared_review") or "Review",
                tr("shared_review_need_folder") or "Bitte Freigabeordner wählen.",
            )
            return
        try:
            result = start_shared_review(
                self.doc_path,
                folder,
                author=self.ed_start_author.text().strip() or "local",
                title=self.ed_start_title.text().strip(),
                endpoint=self.ed_start_endpoint.text().strip() or None,
            )
        except Exception as e:
            QMessageBox.critical(self, tr("shared_review") or "Review", str(e))
            return
        self._activate(folder, result)

    def _do_join(self) -> None:
        folder = self.ed_join_folder.text().strip()
        if not folder:
            QMessageBox.warning(
                self,
                tr("shared_review") or "Review",
                tr("shared_review_need_folder") or "Bitte Freigabeordner wählen.",
            )
            return
        try:
            result = join_shared_review(
                folder,
                self.doc_path,
                author=self.ed_join_author.text().strip() or "local",
                apply=True,
            )
        except Exception as e:
            QMessageBox.critical(self, tr("shared_review") or "Review", str(e))
            return
        self._activate(folder, result)

    def _do_sync(self) -> None:
        if self._active_share is None:
            QMessageBox.information(
                self,
                tr("shared_review") or "Review",
                tr("shared_review_none") or "Keine aktive Session.",
            )
            return
        try:
            result = sync_shared_review(
                self._active_share,
                self.doc_path,
                author=(
                    self.ed_start_author.text().strip()
                    or self.ed_join_author.text().strip()
                    or self._author_default
                ),
            )
        except Exception as e:
            QMessageBox.warning(self, tr("shared_review") or "Review", str(e))
            return
        self._show_result(result)
        self._refresh_active()
        if self._on_synced:
            try:
                self._on_synced(result)
            except Exception:
                pass

    def _auto_sync(self) -> None:
        if self._active_share is None:
            return
        try:
            result = sync_shared_review(
                self._active_share,
                self.doc_path,
                author=(
                    self.ed_start_author.text().strip()
                    or self.ed_join_author.text().strip()
                    or self._author_default
                ),
            )
            self._show_result(result)
            self._refresh_active()
            if self._on_synced:
                try:
                    self._on_synced(result)
                except Exception:
                    pass
        except Exception:
            pass

    def _toggle_auto(self, on: bool) -> None:
        if on and self._active_share is not None:
            self._poll.start(int(self.spin_interval.value()) * 1000)
        else:
            self._poll.stop()

    def _retune_poll(self, _v: int) -> None:
        if self.chk_auto.isChecked() and self._active_share is not None:
            self._poll.start(int(self.spin_interval.value()) * 1000)

    def _leave(self) -> None:
        self._poll.stop()
        self.chk_auto.setChecked(False)
        self._active_share = None
        self._refresh_active()

    def _show_result(self, result: dict) -> None:
        kinds = result.get("kinds") or {}
        applied = result.get("applied") or {}
        lines = [
            f"Session: {result.get('session_id')} · {result.get('title')}",
            f"Aktion: {result.get('action')} · Items: {result.get('item_count')}",
            f"Teilnehmer: {result.get('participant_count')} · "
            f"Host: {result.get('host')}",
            f"Arten: {kinds}",
        ]
        if applied:
            lines.append(f"Lokal übernommen: {applied}")
        if result.get("endpoint"):
            lines.append(
                f"Endpoint: {result.get('endpoint')} · "
                f"ok={result.get('endpoint_ok')} push={result.get('endpoint_pushed')}"
            )
        lines.append(f"Aktualisiert: {result.get('updated_at')}")
        self.txt_status.setPlainText("\n".join(lines))

    def _refresh_active(self) -> None:
        if self._active_share is None:
            self.lbl_status.setText(
                tr("shared_review_none") or "Keine aktive Session."
            )
            return
        try:
            st = shared_review_status(self._active_share)
            self.lbl_status.setText(
                f"{st.get('title')} · {st.get('item_count')} Items · "
                f"{st.get('participant_count')} Teilnehmer · "
                f"{self._active_share}"
            )
            if not self.txt_status.toPlainText().strip():
                self._show_result(st)
        except Exception as e:
            self.lbl_status.setText(str(e))

    def closeEvent(self, event) -> None:  # noqa: N802
        self._poll.stop()
        super().closeEvent(event)
