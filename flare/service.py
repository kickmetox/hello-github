"""Laufender Dienst: Index, Suche, Oberfläche, Kürzel."""

from __future__ import annotations

import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

from flare.crawl import Crawler, dedupe_roots, default_roots, merge_volume_roots, roots_worth_watching
from flare.volumes import (
    drive_roots_for_config,
    drive_snapshot_for_config,
    exclude_drive_list,
    index_network_enabled,
    windows_cloud_roots,
)
from flare.governor import Governor
from flare.hotkey import HotkeyThread, hotkey_label
from flare.launch import launch_target
from flare.paths import data_dir as default_data_dir
from flare.paths import norm, place_key
from flare.rank import Ranker
from flare.search import search, search_index_file
from flare.server import EventBus, Server
from flare.store import Index
from flare.watch import NullWatcher, start_watcher

log = logging.getLogger("flare")


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
        duty = float(cfg.get("duty", 0.35))
        content = bool(cfg.get("content", True))
        self.hotkey_spec = str(cfg.get("hotkey", "ctrl+alt+space"))
        try:
            hotkey_label(self.hotkey_spec)
        except ValueError:
            self.hotkey_spec = "ctrl+alt+space"
        self.port_pref = int(port if port is not None else cfg.get("port", 47731))
        extra = [(str(path), 1) for path in cfg.get("extra_roots", []) if isinstance(path, str)]
        self.index_network = index_network_enabled(cfg)
        self.exclude_drives = exclude_drive_list(cfg)
        self._drive_poll = None
        dynamic: list[str] = []
        names_only: list[str] = []
        if roots is None:
            base = default_roots(extra)
            drives: list[tuple[str, int]] = []
            cloud: list[str] = []
            if sys.platform == "win32":
                drives = drive_roots_for_config(
                    index_network=self.index_network,
                    exclude=self.exclude_drives,
                )
                cloud = windows_cloud_roots()
                self._drive_poll = self._poll_drives
            self.roots, dynamic = merge_volume_roots(base, drives, cloud)
            known = {place_key(path) for path, _tier in base}
            light = {place_key(path) for path, _tier in drives}
            light.update(place_key(path) for path in cloud)
            names_only = [
                path
                for path, _tier in self.roots
                if place_key(path) in light and place_key(path) not in known
            ]
        else:
            self.roots = dedupe_roots(list(roots) + extra)
        self._dynamic_roots = dynamic
        self._names_only_roots = names_only
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
        self.window: Any = None
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
        # Namen-only-Wurzeln (Platte, USB, Cloud, Netz) nicht beobachten.
        # Sonst würde jede Änderung sie vor dem Tier-1-Takt von 300 s neu lesen.
        hot_roots = roots_worth_watching(
            self.roots,
            [*self._names_only_roots, *self._dynamic_roots],
        )

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
            drive_poll=self._drive_poll,
            dynamic_roots=self._dynamic_roots,
            names_only=self._names_only_roots,
        )
        crawler = threading.Thread(target=self._crawl, name="flare-index", daemon=True)
        crawler.start()
        self._threads.append(crawler)
        if self.use_hotkey:
            self.hotkey_thread = HotkeyThread(self.hotkey_spec, self.activate, self.stop)
            self.hotkey_thread.start()
        if self.open_immediately:
            self.activate()

    def _poll_drives(self) -> list[tuple[str, int, bool]]:
        return drive_snapshot_for_config(
            index_network=self.index_network,
            exclude=self.exclude_drives,
        )

    def _crawl(self) -> None:
        assert self.crawler is not None
        try:
            self.crawler.run()
        except Exception:
            log.exception("index thread stopped")

    def run_forever(self) -> None:
        show = self.open_immediately
        self.open_immediately = False
        self.start()
        try:
            if self.allow_ui and sys.platform == "win32":
                from flare.window import NativeWindow

                self.window = NativeWindow(
                    self._ui_search,
                    self._ui_open,
                    self._ui_status,
                    self.save_index_copy,
                )
                self.window.run(self.stop, visible=show)
            else:
                while not self.stop.wait(3600):
                    pass
        finally:
            self.shutdown()

    def _ui_search(self, text: str, similar: bool) -> dict[str, Any]:
        return self.search(text, 12, similar)

    def _ui_open(self, hit: dict[str, Any]) -> None:
        if hit.get("kind") == "calc":
            return
        if hit.get("id") is None:
            return
        self.open_result({"id": int(hit["id"])})

    def _ui_status(self) -> str:
        data = self.status()
        mode = "CPU+CUDA" if data["backend"] == "cpu+cuda" else "CPU"
        phase = "Index läuft" if data["phase"] == "scan" else "Bereit"
        return f"{data['items']} Einträge · {mode} · {phase} · {data.get('hotkey_label', '')}"

    def search(self, text: str, limit: int = 8, similar: bool = False) -> dict[str, Any]:
        return search(self.index, self.ranker, text, limit, similar)

    def search_file(self, path: str, text: str, limit: int = 8, similar: bool = False) -> dict[str, Any]:
        """Eigenen Index lesen. Der laufende Katalog bleibt unverändert."""
        return search_index_file(path, text, limit, similar)

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
        if self.window is not None:
            self.window.show()

    def save_index_copy(self, dest: str) -> str:
        """Zusätzliche Kopie. Die laufende Datenbank bleibt liegen."""
        return str(self.index.backup(dest))

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
