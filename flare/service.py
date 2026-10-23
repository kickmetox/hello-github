"""Laufender Dienst: Index, Suche, Oberfläche, Kürzel."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from flare.crawl import Crawler, dedupe_roots, default_roots
from flare.governor import Governor
from flare.hotkey import HotkeyThread, hotkey_label
from flare.launch import launch_target
from flare.paths import data_dir as default_data_dir
from flare.paths import norm
from flare.rank import Ranker
from flare.search import search
from flare.server import EventBus, Server
from flare.store import Index
from flare.watch import NullWatcher, start_watcher

log = logging.getLogger("flare")


def find_browser() -> str | None:
    names = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
        "msedge",
    ]
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    if sys.platform == "win32":
        roots = [
            os.environ.get("PROGRAMFILES", r"C:\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ]
        tails = [
            Path("Google") / "Chrome" / "Application" / "chrome.exe",
            Path("Microsoft") / "Edge" / "Application" / "msedge.exe",
        ]
        for root in roots:
            if not root:
                continue
            for tail in tails:
                candidate = Path(root) / tail
                if candidate.exists():
                    return str(candidate)
    return None


def spawn_ui(url: str, profile: Path) -> subprocess.Popen[bytes] | None:
    browser = find_browser()
    if browser is None:
        import webbrowser

        webbrowser.open(url)
        return None
    profile.mkdir(parents=True, exist_ok=True)
    command = [
        browser,
        f"--app={url}",
        "--window-size=740,640",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        f"--user-data-dir={profile}",
    ]
    return subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _raise_window() -> None:
    wmctrl = shutil.which("wmctrl")
    if not wmctrl:
        return
    subprocess.run([wmctrl, "-a", "Flare"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


class Service:
    def __init__(
        self,
        data_dir: Path | None = None,
        roots: list[tuple[str, int]] | None = None,
        *,
        config: dict[str, Any] | None = None,
        open_immediately: bool = True,
        allow_ui: bool = True,
        hotkey: bool = True,
        watch: bool = True,
        index_path: bool = True,
        fast: bool = False,
        port: int | None = None,
    ) -> None:
        cfg = config or {}
        self.data_path = Path(data_dir) if data_dir else default_data_dir()
        self.data_path.mkdir(parents=True, exist_ok=True)
        duty = float(cfg.get("duty", 0.08))
        content = bool(cfg.get("content", True))
        self.hotkey_spec = str(cfg.get("hotkey", "ctrl+alt+space"))
        try:
            hotkey_label(self.hotkey_spec)
        except ValueError:
            self.hotkey_spec = "ctrl+alt+space"
        self.port_pref = int(port if port is not None else cfg.get("port", 47731))
        extra = [(str(path), 1) for path in cfg.get("extra_roots", []) if isinstance(path, str)]
        if roots is None:
            self.roots = default_roots(extra)
        else:
            self.roots = dedupe_roots(list(roots) + extra)
        self.index = Index(self.data_path / "index.db")
        self.ranker = Ranker()
        self.bus = EventBus()
        self.stop = threading.Event()
        self.governor = Governor(duty=duty, fast=fast)
        self.allow_ui = allow_ui
        self.open_immediately = open_immediately and allow_ui
        self.use_hotkey = hotkey
        self.use_watch = watch
        self.index_path = index_path
        self.content = content
        self.httpd: Server | None = None
        self.port = 0
        self.ui_proc: subprocess.Popen[bytes] | None = None
        self.crawler: Crawler | None = None
        self.watcher: Any = None
        self.hotkey_thread: HotkeyThread | None = None
        self._threads: list[threading.Thread] = []

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def start(self) -> None:
        try:
            self.httpd = Server("127.0.0.1", self.port_pref, self)
        except OSError:
            self.httpd = Server("127.0.0.1", 0, self)
        self.port = int(self.httpd.server_address[1])
        (self.data_path / "port").write_text(str(self.port), encoding="ascii")
        http = threading.Thread(
            target=self.httpd.serve_forever,
            kwargs={"poll_interval": 0.25},
            name="flare-http",
            daemon=True,
        )
        http.start()
        self._threads.append(http)
        hot_roots = [path for path, tier in self.roots if tier <= 1]

        def on_change(path: str, descend: bool = False) -> None:
            if self.crawler is not None:
                self.crawler.poke(path, descend=descend)

        if self.use_watch:
            self.watcher = start_watcher(on_change, self.stop, hot_roots)
        else:
            self.watcher = NullWatcher()
        self.crawler = Crawler(
            self.index,
            self.governor,
            self.roots,
            self.stop,
            content=self.content,
            index_path=self.index_path,
            data_dir=str(self.data_path),
            watcher=self.watcher,
        )
        crawler = threading.Thread(target=self._crawl, name="flare-index", daemon=True)
        crawler.start()
        self._threads.append(crawler)
        if self.use_hotkey:
            self.hotkey_thread = HotkeyThread(self.hotkey_spec, self.activate, self.stop)
            self.hotkey_thread.start()
        if self.open_immediately:
            self.activate()

    def _crawl(self) -> None:
        assert self.crawler is not None
        try:
            self.crawler.run()
        except Exception:
            log.exception("index thread stopped")

    def run_forever(self) -> None:
        self.start()
        try:
            while not self.stop.wait(3600):
                pass
        finally:
            self.shutdown()

    def search(self, text: str, limit: int = 8) -> dict[str, Any]:
        return search(self.index, self.ranker, text, limit)

    def status(self) -> dict[str, Any]:
        counts = self.index.counts()
        hotkey_active = bool(self.hotkey_thread and self.hotkey_thread.active)
        return {
            **counts,
            "backend": self.ranker.mode,
            "phase": self.crawler.phase if self.crawler else "idle",
            "queued": self.crawler.queued() if self.crawler else 0,
            "duty": round(self.governor.duty, 2),
            "hotkey": self.hotkey_spec,
            "hotkey_label": hotkey_label(self.hotkey_spec) if self.use_hotkey else "",
            "hotkey_active": hotkey_active,
            "hotkey_error": self.hotkey_thread.error if self.hotkey_thread else "",
            "port": self.port,
            "readdirs": self.crawler.readdirs if self.crawler else 0,
            "url": self.url if self.port else "",
        }

    def open_result(self, body: dict[str, Any]) -> bool:
        if body.get("kind") == "calc":
            return True
        item_id = body.get("id")
        if not isinstance(item_id, int):
            return False
        item = self.index.get(item_id)
        if item is None:
            return False
        self.index.record_use(item_id, int(time.time()))
        launch_target(item)
        return True

    def activate(self) -> None:
        self.bus.push({"type": "focus"})
        if not self.allow_ui or not self.port:
            return
        if self.ui_proc is not None and self.ui_proc.poll() is None:
            _raise_window()
            return
        self.ui_proc = spawn_ui(self.url, self.data_path / "chrome-profile")

    def reindex(self) -> None:
        self.index.invalidate_all()
        if self.crawler is not None:
            self.crawler.enqueue_all()

    def shutdown(self) -> None:
        self.stop.set()
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
        if self.watcher is not None:
            self.watcher.close()
        if self.hotkey_thread is not None:
            self.hotkey_thread.close()
        for thread in self._threads:
            thread.join(timeout=2)
        port_file = self.data_path / "port"
        if port_file.exists():
            try:
                if port_file.read_text(encoding="ascii").strip() == str(self.port):
                    port_file.unlink()
            except OSError:
                pass
        self.ranker.close()
        self.index.close()


def roots_from_args(raw: list[str] | None) -> list[tuple[str, int]] | None:
    if not raw:
        return None
    return [(norm(path), 1) for path in raw]
