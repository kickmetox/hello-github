"""Lokaler stdlib-HTTP-Server für die Oberfläche und /api."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from crossos import __version__
from crossos.diagnostics import apply_allowlisted, diagnose, firmware_status, rescue_plan
from crossos.diagnostics.repair import allowlist_public
from crossos.hardware import (
    apply_ppd,
    apply_threshold,
    export_custom,
    export_profile,
    list_plans,
    load_offsets,
    probe,
    profile_names,
    save_offsets,
    vendor_map,
)
from crossos.hardware.battery import candidate_nodes
from crossos.migrator.apps import list_catalog, plan_apps
from crossos.migrator.gestures import gesture_bridge
from crossos.migrator.packages import PackageBridge
from crossos.migrator.paths import translate_path
from crossos.migrator.semantic import translate_document
from crossos.migrator.shortcuts import translate_shortcut, translate_vscode_keybindings
from crossos.migrator.theme import theme_bridge
from crossos.platform_detect import detect_platform
from crossos.safety import SafetyError
from crossos.stateutil import state_path

_MAX_BODY = 1_000_000
_BRIDGE = PackageBridge()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def web_root() -> Path:
    override = Path(__import__("os").environ["CROSSOS_WEB_ROOT"]) if __import__("os").environ.get("CROSSOS_WEB_ROOT") else None
    if override and override.is_dir():
        return override
    candidate = repo_root() / "web"
    if candidate.is_dir():
        return candidate
    cwd = Path.cwd() / "web"
    return cwd


def examples_root() -> Path:
    candidate = repo_root() / "examples"
    if candidate.is_dir():
        return candidate
    return Path.cwd() / "examples"


class CrossOSHandler(BaseHTTPRequestHandler):
    server_version = f"CrossOS/{__version__}"

    def log_message(self, fmt: str, *args) -> None:
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:
        self._route("GET")

    def do_POST(self) -> None:
        self._route("POST")

    def _route(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if method == "GET" and path in {"/", "/index.html"}:
                self._file(web_root() / "index.html")
                return
            if method == "GET" and path.startswith("/fonts/"):
                self._static(path[1:])
                return
            if method == "GET" and path in {"/styles.css", "/app.js"}:
                self._static(path[1:])
                return
            if method == "GET" and path == "/api/health":
                self._send(200, {"ok": True, "version": __version__, "dry_run_default": True})
                return
            if method == "GET" and path == "/api/overview":
                self._send(200, _overview())
                return
            if method == "GET" and path == "/api/examples":
                self._send(200, {"examples": _example_list()})
                return
            if method == "GET" and path.startswith("/api/examples/"):
                self._send(200, _example_one(path[len("/api/examples/") :]))
                return
            if method == "GET" and path == "/api/apps/catalog":
                self._send(200, {"apps": list_catalog()})
                return
            if method == "GET" and path == "/api/packages/detect":
                self._send(200, _BRIDGE.detect())
                return
            if method == "GET" and path == "/api/firmware":
                self._send(200, firmware_status())
                return
            if method == "GET" and path == "/api/repair/allowlist":
                self._send(200, {"actions": allowlist_public(), "dry_run_default": True})
                return
            if method == "GET" and path == "/api/hardware/probe":
                self._send(200, probe())
                return
            if method == "GET" and path == "/api/hardware/fans":
                self._send(200, {"profiles": [export_profile(name) for name in profile_names()]})
                return
            if method == "GET" and path == "/api/hardware/power":
                self._send(200, list_plans())
                return
            if method == "GET" and path == "/api/hardware/vendors":
                self._send(200, vendor_map())
                return
            if method == "GET" and path == "/api/hardware/undervolt":
                self._send(200, {"profile": load_offsets(state_path()), "applied": False})
                return
            if method == "GET" and path == "/api/hardware/battery":
                root = Path("/sys/class/power_supply")
                self._send(
                    200,
                    {
                        "nodes": [str(item) for item in candidate_nodes(root)],
                        "writable_note_de": "Geschrieben wird nur mit confirm=true und nur in einen vorhandenen, beschreibbaren Schwellen-Knoten.",
                    },
                )
                return
            if method == "POST":
                body = self._body()
                self._post(path, body)
                return
            self._send(404, {"error": "Nicht gefunden", "code": "not_found"})
        except SafetyError as exc:
            self._send(400, {"error": str(exc), "code": "safety"})
        except json.JSONDecodeError:
            self._send(400, {"error": "JSON ungültig", "code": "json"})
        except Exception as exc:  # noqa: BLE001 — die API soll eine JSON-Antwort behalten
            self._send(500, {"error": str(exc), "code": "internal"})

    def _post(self, path: str, body: dict) -> None:
        if path == "/api/translate":
            text = _need_str(body, "text")
            self._send(
                200,
                translate_document(
                    text,
                    source_format=body.get("source_format") or None,
                    target_format=_need_str(body, "target_format"),
                    target_os=_need_str(body, "target_os"),
                    user=body.get("user") or None,
                ),
            )
            return
        if path == "/api/paths":
            translated, unmapped = translate_path(_need_str(body, "path"), _need_str(body, "target_os"), body.get("user"))
            self._send(200, {"output": translated, "unmapped": unmapped, "executed": False})
            return
        if path == "/api/apps/plan":
            apps = body.get("apps") or []
            if not isinstance(apps, list) or not all(isinstance(item, str) for item in apps):
                raise SafetyError("apps muss eine Liste von Namen sein.")
            self._send(200, plan_apps(apps, target_os=_need_str(body, "target_os"), detect=bool(body.get("detect"))))
            return
        if path == "/api/packages/plan":
            self._send(
                200,
                _BRIDGE.plan(
                    _need_str(body, "manager"),
                    _need_list(body, "packages"),
                    str(body.get("action") or "install"),
                ),
            )
            return
        if path == "/api/packages/drive":
            self._send(
                200,
                _BRIDGE.drive(
                    _need_str(body, "manager"),
                    _need_list(body, "packages"),
                    str(body.get("action") or "install"),
                    confirm=body.get("confirm") is True,
                    dry_run=body.get("dry_run", True) is not False,
                ),
            )
            return
        if path == "/api/shortcuts":
            if "bindings" in body:
                self._send(200, translate_vscode_keybindings(body.get("bindings"), target_os=_need_str(body, "target_os")))
                return
            self._send(
                200,
                translate_shortcut(
                    _need_str(body, "shortcut"),
                    source_os=str(body.get("source_os") or "linux"),
                    target_os=_need_str(body, "target_os"),
                ),
            )
            return
        if path == "/api/gestures":
            profile = body.get("profile")
            if not isinstance(profile, dict):
                raise SafetyError("profile muss ein Objekt sein.")
            self._send(200, gesture_bridge(profile))
            return
        if path == "/api/theme":
            profile = body.get("profile")
            if not isinstance(profile, dict):
                raise SafetyError("profile muss ein Objekt sein.")
            self._send(200, theme_bridge(profile, user=body.get("user")))
            return
        if path == "/api/diagnose":
            self._send(200, diagnose(_need_str(body, "text"), shell=body.get("shell")))
            return
        if path == "/api/repair/apply":
            self._send(
                200,
                apply_allowlisted(
                    _need_str(body, "action_id"),
                    confirm=body.get("confirm"),
                    package=body.get("package"),
                    path=body.get("path"),
                    unit=body.get("unit"),
                    roots=[examples_root()],
                ),
            )
            return
        if path == "/api/rescue":
            self._send(
                200,
                rescue_plan(
                    host_os=_need_str(body, "host_os"),
                    filesystem=_need_str(body, "filesystem"),
                    device=_need_str(body, "device"),
                ),
            )
            return
        if path == "/api/hardware/fans":
            if body.get("name"):
                self._send(200, export_profile(str(body["name"])))
                return
            self._send(200, export_custom(body.get("points")))
            return
        if path == "/api/hardware/undervolt":
            self._send(200, save_offsets(body, state_path()))
            return
        if path == "/api/hardware/power":
            self._send(200, apply_ppd(_need_str(body, "id"), confirm=body.get("confirm")))
            return
        if path == "/api/hardware/battery":
            self._send(
                200,
                apply_threshold(
                    body.get("stop_percent"),
                    confirm=body.get("confirm"),
                    state_file=state_path(),
                    node=body.get("node"),
                    sysfs_root=Path("/sys/class/power_supply"),
                ),
            )
            return
        self._send(404, {"error": "Nicht gefunden", "code": "not_found"})

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 0 or length > _MAX_BODY:
            raise SafetyError("Anfragekörper zu groß.")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise SafetyError("JSON-Objekt erwartet.")
        return data

    def _send(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _static(self, relative: str) -> None:
        root = web_root().resolve()
        path = (root / relative).resolve()
        if path != root and root not in path.parents:
            self._send(403, {"error": "Pfad abgelehnt", "code": "safety"})
            return
        self._file(path)

    def _file(self, path: Path) -> None:
        if not path.is_file():
            self._send(404, {"error": "Nicht gefunden", "code": "not_found"})
            return
        data = path.read_bytes()
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix in {".css", ".js", ".html", ".svg"}:
            mime = {
                ".css": "text/css; charset=utf-8",
                ".js": "text/javascript; charset=utf-8",
                ".html": "text/html; charset=utf-8",
                ".svg": "image/svg+xml",
            }[path.suffix]
        if path.suffix == ".woff2":
            mime = "font/woff2"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _overview() -> dict:
    platform_info = detect_platform()
    return {
        "name": "CrossOS Intelligent Workflow & System Sync",
        "version": __version__,
        "dry_run_default": True,
        "platform": platform_info,
        "packages": _BRIDGE.detect(),
        "safety": {
            "one_click": "nur lesende Freigabeliste und nur mit confirm=true",
            "filesystem_repair": "plan",
            "firmware": "read-only oder plan, nie flash",
            "voltage": "nur speichern",
            "fan_pwm": "nicht schreiben",
            "charge_threshold": "nur vorhandener beschreibbarer sysfs-Knoten und confirm=true",
            "package_install": "plan, außer CROSSOS_ALLOW_PACKAGE_INSTALL=1 mit confirm und dry_run=false",
        },
    }


def _example_list() -> list[dict]:
    root = examples_root()
    if not root.is_dir():
        return []
    rows = []
    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix in {".sample", ".json", ".log", ".reg", ".txt", ".xml"}:
            rows.append({"name": path.name, "bytes": path.stat().st_size})
    return rows


def _example_one(name: str) -> dict:
    if "/" in name or "\\" in name or name.startswith("."):
        raise SafetyError("Beispielname abgelehnt.")
    path = examples_root() / name
    if not path.is_file() or path.suffix not in {".sample", ".json", ".log", ".reg", ".txt", ".xml"}:
        raise SafetyError("Beispiel nicht gefunden.")
    return {"name": path.name, "text": path.read_text(encoding="utf-8")}


def _need_str(body: dict, key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SafetyError(f"{key} fehlt.")
    return value


def _need_list(body: dict, key: str) -> list[str]:
    value = body.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise SafetyError(f"{key} muss eine Liste von Zeichenketten sein.")
    return value


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), CrossOSHandler)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = create_server(host, port)
    print(f"CrossOS UI: http://{host}:{port}/", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("CrossOS beendet.", flush=True)
    finally:
        httpd.server_close()
