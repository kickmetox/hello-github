"""Eigenständiger Vollbild-Player. Braucht nur PySide6 und show.oshow daneben."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


def _missing_pyside() -> None:
    print("PySide6 wird benötigt: python -m pip install PySide6", file=sys.stderr)


try:
    from PySide6.QtCore import QEvent, Qt, QUrl
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtWidgets import (
        QApplication,
        QLabel,
        QMainWindow,
        QStackedWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    _missing_pyside()
    raise SystemExit(1)


ROOT = Path(__file__).resolve().parent
SHOW = ROOT / "show.oshow"


def load_entries(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    media_dir = Path(str(path.with_suffix("")) + "_media")
    if media_dir.exists():
        import shutil

        shutil.rmtree(media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "r") as archive:
        payload = json.loads(archive.read("slideshow.json").decode("utf-8"))
        for info in archive.infolist():
            name = info.filename
            if name.startswith("media/") and not name.endswith("/"):
                archive.extract(info, media_dir)
    entries: list[dict] = []
    for item in payload.get("entries") or []:
        raw = item.get("path") or ""
        if isinstance(raw, str) and raw.startswith("media/"):
            raw = str(media_dir / raw)
        entries.append(
            {
                "kind": item.get("kind") or "text",
                "title": item.get("title") or "",
                "text": item.get("text") or "",
                "path": raw or "",
            }
        )
    return entries


class Surface(QWidget):
    """Bild mit Contain auf schwarzer oder weißer Fläche."""

    def __init__(self, owner: "Player") -> None:
        super().__init__()
        self.owner = owner
        self.image: QImage | None = None
        self.blank = ""

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        if self.blank == "white":
            painter.fillRect(self.rect(), QColor("#FFFFFF"))
            painter.end()
            return
        painter.fillRect(self.rect(), QColor("#000000"))
        if self.blank != "black" and self.image is not None and not self.image.isNull():
            scaled = self.image.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawImage(x, y, scaled)
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.owner.step(1)
            return
        super().mousePressEvent(event)


class Reader(QTextEdit):
    def __init__(self, owner: "Player") -> None:
        super().__init__()
        self.owner = owner
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFrameStyle(0)
        self.setStyleSheet("QTextEdit { background:#F4F6FB; color:#1B1F2A; font-size:32px; padding:48px; }")

    def keyPressEvent(self, event) -> None:
        self.owner.keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.owner.step(1)
            return
        super().mousePressEvent(event)


class Player(QMainWindow):
    def __init__(self, entries: list[dict]) -> None:
        super().__init__()
        self.entries = entries
        self.index = 0
        self.blank = ""
        self._fullscreen_set = False
        self._in_hint = False
        self._player = None
        self._audio = None
        self._video = None
        self.setWindowTitle("Slideshow")
        self.resize(1280, 720)
        self.setStyleSheet("QMainWindow { background:#000000; }")
        self.surface = Surface(self)
        self.reader = Reader(self)
        self.video_page = QWidget()
        self.video_page.setStyleSheet("background:#000000;")
        self.video_layout = QVBoxLayout(self.video_page)
        self.video_layout.setContentsMargins(0, 0, 0, 0)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setStyleSheet("background:#000000; color:#FFFFFF; font-size:22px; padding:48px;")
        self.stack = QStackedWidget()
        self.stack.addWidget(self.surface)
        self.stack.addWidget(self.reader)
        self.stack.addWidget(self.video_page)
        self.stack.addWidget(self.hint)
        self.setCentralWidget(self.stack)
        self.show_entry()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._fullscreen_set:
            self._fullscreen_set = True
            self.showFullScreen()
        self.setFocus()

    def step(self, delta: int) -> None:
        if not self.entries:
            return
        self.index = max(0, min(len(self.entries) - 1, self.index + delta))
        self.blank = ""
        self.show_entry()

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close()
            return
        if key == Qt.Key.Key_B:
            self.blank = "" if self.blank == "black" else "black"
            self.show_entry()
            return
        if key == Qt.Key.Key_W:
            self.blank = "" if self.blank == "white" else "white"
            self.show_entry()
            return
        if key == Qt.Key.Key_Home:
            self.index = 0
            self.blank = ""
            self.show_entry()
            return
        if key == Qt.Key.Key_End:
            self.index = max(0, len(self.entries) - 1)
            self.blank = ""
            self.show_entry()
            return
        if key in {Qt.Key.Key_Right, Qt.Key.Key_Space, Qt.Key.Key_PageDown}:
            self.step(1)
            return
        if key in {Qt.Key.Key_Left, Qt.Key.Key_PageUp}:
            self.step(-1)
            return
        super().keyPressEvent(event)

    def show_entry(self) -> None:
        self._stop_media()
        if self.blank in {"black", "white"}:
            self.surface.blank = self.blank
            self.surface.image = None
            self.stack.setCurrentWidget(self.surface)
            self.surface.update()
            return
        if not self.entries:
            self.hint.setText("Keine Einträge.")
            self.stack.setCurrentWidget(self.hint)
            return
        self.index = max(0, min(self.index, len(self.entries) - 1))
        entry = self.entries[self.index]
        kind = entry.get("kind") or "text"
        if kind == "text":
            self.reader.setPlainText(entry.get("text") or entry.get("title") or "")
            self.stack.setCurrentWidget(self.reader)
        elif kind == "video":
            self._show_video(entry.get("path") or "")
        else:
            self._show_image(entry.get("path") or "", entry.get("title") or "")

    def _show_image(self, path: str, title: str) -> None:
        image = QImage(path) if path else QImage()
        if image.isNull():
            self.hint.setText(f"Bild nicht lesbar.\n{path or title}")
            self.stack.setCurrentWidget(self.hint)
            return
        self.surface.blank = ""
        self.surface.image = image
        self.stack.setCurrentWidget(self.surface)
        self.surface.update()

    def _show_video(self, path: str) -> None:
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
            from PySide6.QtMultimediaWidgets import QVideoWidget
        except Exception:
            self._video_hint(path)
            return
        try:
            self._video = QVideoWidget(self.video_page)
            self._video.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._video.setStyleSheet("background:#000000;")
            self.video_layout.addWidget(self._video)
            self._player = QMediaPlayer(self)
            self._audio = QAudioOutput(self)
            self._audio.setVolume(1.0)
            self._player.setAudioOutput(self._audio)
            self._player.setVideoOutput(self._video)
            self._video.installEventFilter(self)
            self._player.errorOccurred.connect(lambda *_args, media=path: self._video_hint(media))
            self._player.setSource(QUrl.fromLocalFile(path))
            if self._player.error() != QMediaPlayer.Error.NoError:
                self._video_hint(path)
                return
            self.stack.setCurrentWidget(self.video_page)
            self._player.play()
        except Exception:
            self._video_hint(path)

    def eventFilter(self, watched, event) -> bool:
        if watched is self._video and event.type() == QEvent.Type.KeyPress:
            self.keyPressEvent(event)
            return True
        if watched is self._video and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.step(1)
            return True
        return super().eventFilter(watched, event)

    def _video_hint(self, path: str) -> None:
        if self._in_hint:
            return
        self._in_hint = True
        try:
            self._stop_media()
            self.hint.setText(
                "Qt Multimedia kann dieses Format nicht abspielen.\n"
                f"{path}\n"
                "Die Datei bleibt als Pfad sichtbar."
            )
            self.stack.setCurrentWidget(self.hint)
        finally:
            self._in_hint = False

    def _stop_media(self) -> None:
        if self._player is not None:
            try:
                self._player.stop()
                self._player.setSource(QUrl())
            except Exception:
                pass
            self._player.deleteLater()
            self._player = None
        if self._audio is not None:
            self._audio.deleteLater()
            self._audio = None
        if self._video is not None:
            self.video_layout.removeWidget(self._video)
            self._video.hide()
            self._video.deleteLater()
            self._video = None

    def closeEvent(self, event) -> None:
        self._stop_media()
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    try:
        entries = load_entries(SHOW)
    except Exception as exc:
        print(f"Die Slideshow lässt sich nicht öffnen.\n{exc}", file=sys.stderr)
        raise SystemExit(1)
    window = Player(entries)
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
