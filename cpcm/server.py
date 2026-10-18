"""Lokale Oberfläche. Lauscht nur auf 127.0.0.1."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import os

from cpcm import AUTHOR_EMAIL, AUTHOR_NAME, LINUX_INSTALL_DIR, __version__
from cpcm.backup import create_snapshot, delete_snapshot, export_snapshot, import_snapshot, list_snapshots, load_snapshot, restore_snapshot
from cpcm.catalog import MANAGERS, detect_installed, plan
from cpcm.diagnose import analyze, lint_user_script, script_for
from cpcm.filesystems import repair_plan
from cpcm.hardware import load_profiles, probe, set_active, upsert_profile
from cpcm.paths import World, host_identity, identity_for_home
from cpcm.selection import add_path, load_selection, remove_item, save_selection, set_world_path
from cpcm.settings import ROOT, bundled_path, counterpart_identity, host_home_identity, load_settings, resource_root, save_settings, vault_dir
from cpcm.shortcuts import GESTURE_DEFAULTS, gesture_artifacts, translate_shortcut
from cpcm.themes import theme_artifacts
from cpcm.translate import identities_from_request, translate_config

WEB = resource_root() / "web"
MAX_BODY = 2 * 1024 * 1024
DEFAULT_PORT = 8910
# ShatuIDE belegt 8765 und sucht danach bis 8864. CPCM nutzt diesen Bereich nicht.
FOREIGN_PORT_START = 8765
FOREIGN_PORT_END = 8865


class App:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or ROOT
        self.host = host_identity()

    def settings(self) -> dict:
        return load_settings(self.root)

    def vault(self) -> Path:
        return vault_dir(self.settings(), self.root)

    def identities(self):
        data = self.settings()
        host = host_home_identity(data, self.host)
        return host, counterpart_identity(data, host)


def browse(path_text: str) -> dict:
    path = Path(os.path.abspath(os.path.expanduser(path_text.strip() or str(Path.home()))))
    if path.is_file():
        path = path.parent
    if not path.is_dir():
        raise FileNotFoundError(str(path))
    try:
        children = list(path.iterdir())
    except PermissionError as exc:
        raise PermissionError(f"Kein Zugriff auf {path}") from exc
    children.sort(key=lambda item: (not item.is_dir(), item.name.casefold()))
    entries = []
    for child in children[:400]:
        try:
            kind = "dir" if child.is_dir() else "file"
        except OSError:
            kind = "file"
        entries.append({"name": child.name, "path": str(child), "kind": kind})
    parent = None if path.parent == path else str(path.parent)
    return {"path": str(path), "parent": parent, "entries": entries, "truncated": len(children) > 400}


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        server_version = "CPCM"

        def log_message(self, fmt: str, *args) -> None:
            return

        def _send(self, code: int, payload, content_type: str = "application/json; charset=utf-8") -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if isinstance(payload, (dict, list)) else payload if isinstance(payload, bytes) else str(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or "0")
            if length > MAX_BODY:
                raise ValueError("Anfrage ist zu groß")
            data = json.loads(self.rfile.read(length).decode("utf-8") if length else "{}")
            if not isinstance(data, dict):
                raise ValueError("JSON-Objekt erwartet")
            return data

        def do_GET(self) -> None:  # noqa: N802
            try:
                parsed = urlparse(self.path)
                if parsed.path.startswith("/api/"):
                    self._send(200, self._get_api(parsed.path, parse_qs(parsed.query)))
                else:
                    self._static(parsed.path)
            except FileNotFoundError as exc:
                self._send(404, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                self._send(400, {"error": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            try:
                self._send(200, self._post_api(urlparse(self.path).path, self._read_json()))
            except FileNotFoundError as exc:
                self._send(404, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                self._send(400, {"error": str(exc)})

        def _static(self, path: str) -> None:
            mapping = {
                "/": (WEB / "index.html", "text/html; charset=utf-8"),
                "/index.html": (WEB / "index.html", "text/html; charset=utf-8"),
                "/app.js": (WEB / "app.js", "text/javascript; charset=utf-8"),
                "/styles.css": (WEB / "styles.css", "text/css; charset=utf-8"),
                "/icon.png": (bundled_path(app.root, "icon.png"), "image/png"),
                "/cpcm.ico": (bundled_path(app.root, "cpcm.ico"), "image/x-icon"),
            }
            if path not in mapping:
                self._send(404, {"error": "nicht gefunden"})
                return
            target, mime = mapping[path]
            if not target.is_file():
                raise FileNotFoundError(path)
            self._send(200, target.read_bytes(), mime)

        def _get_api(self, path: str, query: dict) -> dict:
            if path == "/api/status":
                host, other = app.identities()
                settings = app.settings()
                return {
                    "name": "CPCM", "version": __version__, "world": host.world.value, "home": str(host.home), "user": host.user,
                    "author": AUTHOR_NAME, "author_email": AUTHOR_EMAIL,
                    "vault": str(app.vault()), "homes": settings["homes"],
                    "install_dir_windows": settings["install_dir_windows"],
                    "install_dir_linux": LINUX_INSTALL_DIR,
                    "counterpart_home": str(other.home),
                    "managers": {world.value: list(names) for world, names in MANAGERS.items()},
                }
            if path == "/api/browse":
                return browse((query.get("path") or [""])[0])
            if path == "/api/selection":
                return load_selection(app.vault()).to_json()
            if path == "/api/snapshots":
                return {"snapshots": list_snapshots(app.vault())}
            if path.startswith("/api/snapshots/"):
                snap_id = path.removeprefix("/api/snapshots/")
                if not snap_id or "/" in snap_id:
                    raise ValueError("Sicherungs-ID fehlt")
                return load_snapshot(app.vault(), snap_id).to_json()
            if path == "/api/hardware":
                return {"probe": probe(), "store": load_profiles(app.vault())}
            if path == "/api/apps/detect":
                return {"installed": detect_installed()}
            if path == "/api/examples":
                folder = bundled_path(app.root, "examples")
                names = sorted(item.name for item in folder.glob("*") if item.is_file()) if folder.is_dir() else []
                return {"examples": names}
            if path.startswith("/api/examples/"):
                name = path.removeprefix("/api/examples/")
                if "/" in name or name in ("", ".", ".."):
                    raise ValueError("Beispielname ungültig")
                file = bundled_path(app.root, "examples") / name
                if not file.is_file():
                    raise FileNotFoundError(name)
                return {"name": name, "text": file.read_text(encoding="utf-8")}
            raise FileNotFoundError(path)

        def _post_api(self, path: str, payload: dict) -> dict:
            host, other = app.identities()
            vault = app.vault()
            if path == "/api/selection":
                selection = load_selection(vault)
                item = add_path(selection, Path(str(payload.get("path") or "")), host, other, kind=str(payload.get("kind") or "auto"))
                save_selection(vault, selection)
                return {"item": item.to_json(), "selection": selection.to_json()}
            if path == "/api/selection/remove":
                selection = load_selection(vault)
                remove_item(selection, str(payload.get("id") or ""))
                save_selection(vault, selection)
                return selection.to_json()
            if path == "/api/selection/path":
                selection = load_selection(vault)
                item = set_world_path(selection, str(payload.get("id") or ""), World(str(payload.get("world"))), str(payload.get("path") or ""))
                save_selection(vault, selection)
                return item.to_json()
            if path == "/api/homes":
                data = app.settings()
                for key in ("linux", "windows"):
                    if (payload.get("homes") or {}).get(key):
                        data["homes"][key] = str(payload["homes"][key])
                save_settings(data, app.root)
                return data
            if path == "/api/vault":
                data = app.settings()
                target = str(payload.get("path") or "").strip()
                if not target:
                    raise ValueError("Vault-Pfad fehlt")
                data["vault"] = target
                save_settings(data, app.root)
                Path(target).mkdir(parents=True, exist_ok=True)
                return {"vault": str(vault_dir(data, app.root))}
            if path == "/api/backup":
                return create_snapshot(vault, load_selection(vault), host).to_json()
            if path == "/api/restore":
                snap_id = str(payload.get("id") or "")
                snapshot = load_snapshot(vault, snap_id)
                source = identity_for_home(
                    World(snapshot.source_world) if snapshot.source_world else host.world,
                    Path(snapshot.source_home or str(host.home)),
                    snapshot.source_user or host.user,
                )
                report = restore_snapshot(
                    vault, snap_id, host, source=source,
                    overwrite=bool(payload.get("overwrite")),
                    translate_paths=bool(payload.get("translate_paths")),
                    destination=Path(str(payload["destination"])) if payload.get("destination") else None,
                )
                return report.to_json()
            if path == "/api/export":
                target = Path(str(payload.get("path") or ""))
                if target.suffix.lower() != ".cpcm":
                    target = target.with_suffix(".cpcm")
                export_snapshot(vault, str(payload.get("id") or ""), target)
                return {"path": str(target)}
            if path == "/api/import":
                return {"id": import_snapshot(vault, Path(str(payload.get("path") or "")))}
            if path == "/api/snapshots/delete":
                delete_snapshot(vault, str(payload.get("id") or ""))
                return {"ok": True}
            if path == "/api/translate":
                merged = dict(payload)
                merged.setdefault("homes", app.settings()["homes"])
                source, target = identities_from_request(merged, host)
                return translate_config(str(payload.get("text") or ""), source, target, fmt=payload.get("format") or None)
            if path == "/api/shortcuts":
                world = World(str(payload.get("world") or host.world.value))
                text = str(payload.get("shortcut") or "")
                return {"windows": translate_shortcut(text, World.WINDOWS), "linux": translate_shortcut(text, World.LINUX), "vscode": translate_shortcut(text, world, vscode=True)}
            if path == "/api/gestures":
                settings = {**GESTURE_DEFAULTS, **dict(payload.get("settings") or {})}
                return gesture_artifacts(settings, World(str(payload.get("world") or host.world.value)))
            if path == "/api/theme":
                return theme_artifacts(dict(payload.get("theme") or {}), World(str(payload.get("world") or host.world.value)), str(payload.get("desktop") or "gnome"))
            if path == "/api/apps/plan":
                names = payload.get("names") or []
                if isinstance(names, str):
                    names = [line.strip() for line in names.splitlines() if line.strip()]
                manager = str(payload.get("manager") or ("apt" if host.world == World.LINUX else "winget"))
                target = World(str(payload.get("target") or ("windows" if host.world == World.LINUX else "linux")))
                return plan(list(names), target, manager)
            if path == "/api/diagnose":
                findings = analyze(str(payload.get("text") or ""))
                world = World(str(payload.get("world") or host.world.value))
                for finding in findings:
                    finding["script"] = script_for(finding, world)
                return {"findings": findings}
            if path == "/api/diagnose/lint":
                lint_user_script(str(payload.get("script") or ""))
                return {"allowed": True}
            if path == "/api/filesystem":
                return repair_plan(str(payload.get("world") or host.world.value), str(payload.get("filesystem") or ""), str(payload.get("device") or ""))
            if path == "/api/hardware/profile":
                return upsert_profile(vault, dict(payload.get("profile") or payload))
            if path == "/api/hardware/active":
                return set_active(vault, str(payload.get("name") or ""))
            raise FileNotFoundError(path)

    return Handler


def effective_port(port: int | None) -> int:
    """8765–8864 bleiben ShatuIDE. CPCM startet bei 8910."""
    if port is None:
        return DEFAULT_PORT
    number = int(port)
    if FOREIGN_PORT_START <= number < FOREIGN_PORT_END:
        return DEFAULT_PORT
    if number <= 0 or number > 65535:
        return DEFAULT_PORT
    return number


def bind_server(host: str, port: int | None, handler):
    """Bindet CPCM. Ein belegter Wunschport fällt auf 8910–8929, nie auf den ShatuIDE-Bereich."""
    first = effective_port(port)
    candidates = [first]
    for extra in range(DEFAULT_PORT, DEFAULT_PORT + 20):
        if extra not in candidates:
            candidates.append(extra)
    last_error: OSError | None = None
    for candidate in candidates:
        try:
            return ThreadingHTTPServer((host, candidate), handler)
        except OSError as exc:
            last_error = exc
    raise OSError(f"Kein freier Port für CPCM ab {DEFAULT_PORT}") from last_error


def serve(host: str = "127.0.0.1", port: int = DEFAULT_PORT, root: Path | None = None, open_browser: bool = False) -> None:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("CPCM bindet nur an die lokale Schleife")
    application = App(root)
    server = bind_server(host, port, make_handler(application))
    bound = int(server.server_address[1])
    url = f"http://{host}:{bound}/"
    print(f"CPCM läuft auf {url}", flush=True)
    print(f"Vault: {application.vault()}", flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCPCM beendet")
    finally:
        server.server_close()
