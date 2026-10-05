"""Nativer eSCL/AirScan-Scan-Client - reines Python (HTTP), kein SANE
nötig. Funktioniert identisch unter Linux und Windows.

Ergänzt (ersetzt nicht) den bestehenden SANE-Pfad in scanner.py: Geräte,
die schon heute über SANE mit einem `escl:`-Präfix eingebunden sind,
laufen unverändert über `scanimage` weiter. Neue, über diesen Client
angesprochene Geräte nutzen den Präfix `native-escl:` (siehe DEVICE_PREFIX)
und brauchen weder SANE noch Avahi/mDNS auf dem Zielrechner.

Protokoll-Referenz: eSCL ("AirScan", Mopria/HP). Wichtige Details, die im
Code unten kommentiert sind: ScanRegion-Einheiten (immer 1/300 Zoll,
unabhängig von der gewählten Auflösung), zwei unterschiedliche
ADF-Terminierungsstrategien realer Geräte, Duplex als eigenes XML-Flag.

WICHTIG - Testabdeckung: Der Kern (Capabilities, Einzelscan, ADF-Batch,
beide Terminierungsstrategien) wurde gegen einen echten Kyocera-
Netzwerkscanner (eSCL/AirScan) getestet. Der Authentifizierungs-Pfad
(username/password) ist strukturell korrekt, aber NICHT gegen ein Gerät
getestet, das eine Anmeldung verlangt - der Kyocera des ursprünglichen
Testrechners braucht keine.
"""
from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from xml.etree import ElementTree as ET

from .scanner import ScannerError, DeviceOption, escl_ssl_context, escl_auth_header

DEVICE_PREFIX = "native-escl:"

_NS = {
    "pwg": "http://www.pwg.org/schemas/2010/12/sm",
    "scan": "http://schemas.hp.com/imaging/escl/2011/05/03",
}
for _prefix, _uri in _NS.items():
    ET.register_namespace(_prefix, _uri)

# SANE-Vokabular (aus der UI, siehe main_window.py MODE_ITEMS/
# FALLBACK_SOURCE_ITEMS) auf eSCL-Vokabular übersetzen - die UI schickt
# IMMER diese festen SANE-Begriffe, unabhängig vom tatsächlichen Backend.
_MODE_TO_ESCL = {"Color": "RGB24", "Gray": "Grayscale8", "Lineart": "BlackAndWhite1"}
_ADF_SOURCE_VALUES = {"ADF", "ADF Duplex"}

# Fallback-Scanbereich (A4 in 1/300-Zoll-Einheiten), falls die
# Capabilities nicht gelesen werden können oder keine Maximalgröße nennen.
_FALLBACK_WIDTH_UNITS = 2481
_FALLBACK_HEIGHT_UNITS = 3507


class AdfEmptyError(ScannerError):
    """Der automatische Einzug hat keine (weiteren) Seiten - erwartetes
    Ende eines Stapel-Scans, kein echter Fehler."""


def build_device_id(host: str, port: str, use_https: bool = True) -> str:
    scheme = "https" if use_https else "http"
    return f"{DEVICE_PREFIX}{scheme}://{host}:{port}"


def _base_url(device_id: str) -> str:
    return device_id[len(DEVICE_PREFIX):]


def _request(url: str, ctx, headers: dict, method: str = "GET", data: bytes | None = None,
             timeout: int = 15):
    req = urllib.request.Request(url, data=data, method=method)
    for key, value in headers.items():
        req.add_header(key, value)
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def get_capabilities(device_id: str, username: str | None = None, password: str | None = None,
                      timeout: int = 10) -> ET.Element:
    """Ruft GET /eSCL/ScannerCapabilities ab und liefert die geparste
    XML-Wurzel zurück."""
    base = _base_url(device_id)
    ctx = escl_ssl_context() if base.startswith("https://") else None
    headers = escl_auth_header(username, password)
    try:
        with _request(f"{base}/eSCL/ScannerCapabilities", ctx, headers, timeout=timeout) as resp:
            return ET.fromstring(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise ScannerError("Anmeldung erforderlich - Benutzername/Passwort prüfen.") from exc
        raise ScannerError(f"Capabilities nicht lesbar (HTTP {exc.code}).") from exc
    except urllib.error.URLError as exc:
        raise ScannerError(f"Scanner nicht erreichbar: {exc.reason}") from exc
    except ET.ParseError as exc:
        raise ScannerError("Scanner hat ungültige Capabilities-Antwort geliefert.") from exc


def _get_adf_state(base: str, ctx, headers: dict, timeout: int) -> str | None:
    """Liest <scan:AdfState> aus GET /eSCL/ScannerStatus - z.B.
    'ScannerAdfEmpty'/'ScannerAdfJam'/'ScannerAdfLoaded'/
    'ScannerAdfProcessing'. None, falls nicht lesbar (nicht jedes Gerät
    liefert diesen Status)."""
    try:
        with _request(f"{base}/eSCL/ScannerStatus", ctx, headers, timeout=timeout) as resp:
            root = ET.fromstring(resp.read())
    except Exception:
        return None
    node = root.find("scan:AdfState", _NS)
    return node.text if node is not None else None


def get_device_options(device_id: str, username: str | None = None, password: str | None = None,
                        timeout: int = 10) -> dict[str, DeviceOption]:
    """Liest die von einem eSCL-Gerät tatsächlich unterstützten
    Auflösungen aus den Capabilities (an echtem Kyocera getestet: liefert
    z.B. 200/300/400/600 dpi statt der festen SANE-Fallback-Liste in der
    UI). Nur quadratische Auflösungen (XResolution == YResolution) werden
    berücksichtigt - die UI kennt nur eine einzelne dpi-Zahl, kein
    getrenntes X/Y. Liefert ein leeres dict, falls die Capabilities nicht
    lesbar sind - die UI fällt dann automatisch auf ihre eingebauten
    Vorgaben zurück (siehe FALLBACK_RESOLUTIONS in main_window.py)."""
    try:
        caps = get_capabilities(device_id, username, password, timeout=timeout)
    except ScannerError:
        return {}
    resolutions: set[str] = set()
    for res_node in caps.iter(f"{{{_NS['scan']}}}DiscreteResolution"):
        x_node = res_node.find("scan:XResolution", _NS)
        y_node = res_node.find("scan:YResolution", _NS)
        if x_node is not None and y_node is not None and x_node.text == y_node.text:
            resolutions.add(x_node.text)
    if not resolutions:
        return {}
    choices = sorted(resolutions, key=lambda v: int(v))
    return {"resolution": DeviceOption(name="resolution", kind="choice", choices=choices, unit="dpi")}


def _max_region_units(caps_root: ET.Element | None, input_source: str) -> tuple[int, int]:
    """Liefert (Breite, Höhe) in 1/300-Zoll-Einheiten für den vollen
    Scanbereich - aus den Capabilities, falls lesbar, sonst A4-Fallback."""
    if caps_root is not None:
        if input_source == "Feeder":
            input_caps = (
                caps_root.find("scan:Adf/scan:AdfSimplexInputCaps", _NS)
                or caps_root.find("scan:Adf/scan:AdfDuplexInputCaps", _NS)
            )
        else:
            input_caps = caps_root.find("scan:Platen/scan:PlatenInputCaps", _NS)
        if input_caps is not None:
            w_node = input_caps.find("scan:MaxWidth", _NS)
            h_node = input_caps.find("scan:MaxHeight", _NS)
            if w_node is not None and h_node is not None and w_node.text and h_node.text:
                try:
                    return int(w_node.text), int(h_node.text)
                except ValueError:
                    pass
    return _FALLBACK_WIDTH_UNITS, _FALLBACK_HEIGHT_UNITS


def _build_scan_settings_xml(mode: str, resolution: str, source: str | None,
                              width_units: int, height_units: int) -> bytes:
    """Baut den <scan:ScanSettings>-Auftragskörper für POST /eSCL/ScanJobs.

    WICHTIG: Height/Width/XOffset/YOffset sind IMMER in 1/300-Zoll-
    Einheiten anzugeben, unabhängig von der gewählten Auflösung (auch bei
    z.B. 600 dpi bleibt es bei 300stel-Einheiten) - ein häufiger Fehler
    bei eSCL-Implementierungen."""
    input_source = "Feeder" if source in _ADF_SOURCE_VALUES else "Platen"
    color_mode = _MODE_TO_ESCL.get(mode, "RGB24")
    try:
        res_value = int(str(resolution).replace("dpi", ""))
    except ValueError:
        res_value = 300

    pwg = _NS["pwg"]
    scan = _NS["scan"]
    root = ET.Element(f"{{{scan}}}ScanSettings")
    ET.SubElement(root, f"{{{pwg}}}Version").text = "2.6"
    regions = ET.SubElement(root, f"{{{pwg}}}ScanRegions")
    region = ET.SubElement(regions, f"{{{pwg}}}ScanRegion")
    ET.SubElement(region, f"{{{pwg}}}Height").text = str(height_units)
    ET.SubElement(region, f"{{{pwg}}}Width").text = str(width_units)
    ET.SubElement(region, f"{{{pwg}}}XOffset").text = "0"
    ET.SubElement(region, f"{{{pwg}}}YOffset").text = "0"
    ET.SubElement(root, f"{{{pwg}}}InputSource").text = input_source
    ET.SubElement(root, f"{{{scan}}}ColorMode").text = color_mode
    ET.SubElement(root, f"{{{scan}}}XResolution").text = str(res_value)
    ET.SubElement(root, f"{{{scan}}}YResolution").text = str(res_value)
    ET.SubElement(root, f"{{{pwg}}}DocumentFormat").text = "image/jpeg"
    if source == "ADF Duplex":
        # Duplex ist in eSCL ein eigenes Flag, nicht Teil von InputSource.
        ET.SubElement(root, f"{{{scan}}}Duplex").text = "true"
    return b'<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(root)


def _create_job(base: str, ctx, headers: dict, body: bytes, timeout: int, is_feeder: bool = False) -> str:
    """POST /eSCL/ScanJobs. Liefert die (absolute) Job-URL aus dem
    Location-Header. Manche Geräte signalisieren einen leeren Einzug schon
    hier statt erst bei NextDocument - beobachtete Statuscodes dafür:
    500/503 (allgemein "nicht bereit") sowie 409 Conflict (bestätigt gegen
    einen echten Kyocera-Scanner: 409 bei leerem ADF, ohne Klartext-Grund
    im Antwortkörper - zusätzlich per ScannerStatus/AdfState abgesichert,
    siehe scan_batch_adf).

    WICHTIG: dieselben Statuscodes (409/500/503) als "Einzug leer" zu
    interpretieren ist nur bei einem ADF-Auftrag (is_feeder=True) sinnvoll -
    bei einem Flachbett-Auftrag (is_feeder=False) hat der abgelehnte
    Auftrag zwangsläufig einen anderen Grund (z.B. Netzwerk-Scan am Gerät
    deaktiviert, oder ein noch nicht aufgeräumter vorheriger Auftrag), da
    dort gar kein Einzug angefragt wurde - eine "Einzug leer"-Meldung wäre
    dort schlicht falsch und führt in die Irre."""
    job_headers = dict(headers)
    job_headers["Content-Type"] = "text/xml"
    try:
        with _request(f"{base}/eSCL/ScanJobs", ctx, job_headers, method="POST", data=body,
                       timeout=timeout) as resp:
            location = resp.headers.get("Location")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            raw = exc.read()
            if raw:
                detail = "\n\nAntwort des Geräts: " + raw.decode("utf-8", errors="replace").strip()[:500]
        except Exception:
            pass
        if exc.code in (409, 500, 503):
            if is_feeder:
                raise AdfEmptyError(
                    "Scanner nimmt keinen Auftrag an (Einzug leer oder nicht bereit)." + detail
                ) from exc
            raise ScannerError(
                f"Scanner lehnt den Scan-Auftrag ab (HTTP {exc.code}). Mögliche Ursachen: das Gerät "
                "ist noch mit einem vorherigen Auftrag beschäftigt (kurz warten und erneut "
                "versuchen), oder Netzwerk-Scan ist am Gerät deaktiviert (siehe README, Abschnitt "
                "'Wenn der Netzwerk-Scanner Aufträge ablehnt')." + detail
            ) from exc
        raise ScannerError(f"Scan-Auftrag abgelehnt (HTTP {exc.code})." + detail) from exc
    except urllib.error.URLError as exc:
        raise ScannerError(f"Scanner nicht erreichbar: {exc.reason}") from exc
    if not location:
        raise ScannerError("Scanner hat keinen Auftrags-Ort zurückgegeben.")
    return urllib.parse.urljoin(base + "/", location)


def _fetch_next_document(job_url: str, ctx, headers: dict, out_path: str, timeout: int,
                          base: str | None = None, poll_interval_s: float = 0.5) -> bool:
    """GET <job_url>/NextDocument. True = Bild wurde geschrieben, False =
    keine weitere Seite (HTTP 404, Job/Feeder erschöpft). 503 = Seite noch
    nicht bereit, kurz erneut versuchen.

    WICHTIG (an echtem Kyocera-Scanner beobachtet): manche Geräte
    beantworten diesen Request erst, wenn die physische Seite fertig
    gescannt ist (können bei höherer Auflösung/Duplex durchaus 30-90s
    dauern) - `timeout` muss deshalb großzügig sein (siehe Vorgabewerte in
    scan_single_page/scan_batch_adf). Ein reiner Verbindungs-Timeout
    (TimeoutError statt HTTPError - z.B. bei einem Papierstau, bei dem das
    Gerät gar nicht mehr antwortet) wird gegen ScannerStatus/AdfState
    geprüft, um eine klare Fehlermeldung statt eines rohen Absturzes zu
    liefern."""
    url = job_url.rstrip("/") + "/NextDocument"
    deadline = time.monotonic() + timeout
    while True:
        try:
            with _request(url, ctx, headers, timeout=timeout) as resp:
                with open(out_path, "wb") as f:
                    f.write(resp.read())
                return True
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False
            if exc.code == 503 and time.monotonic() < deadline:
                time.sleep(poll_interval_s)
                continue
            raise ScannerError(f"Bildabruf fehlgeschlagen (HTTP {exc.code}).") from exc
        except urllib.error.URLError as exc:
            raise ScannerError(f"Scanner nicht erreichbar: {exc.reason}") from exc
        except TimeoutError as exc:
            state = _get_adf_state(base, ctx, headers, 10) if base else None
            if state and "Jam" in state:
                raise ScannerError("Papierstau im Einzug - bitte Papier entfernen und erneut versuchen.") from exc
            raise ScannerError("Zeitüberschreitung beim Scannen (Gerät antwortet nicht mehr).") from exc


def _delete_job(job_url: str, ctx, headers: dict) -> None:
    """Best-effort: Job-Ressource freigeben, damit das Gerät einen neuen
    Auftrag annimmt. Fehler hier werden bewusst ignoriert."""
    try:
        with _request(job_url, ctx, headers, method="DELETE", timeout=5):
            pass
    except Exception:
        pass


def scan_single_page(
    device_id: str,
    out_path: str,
    mode: str = "Color",
    resolution: str = "300",
    source: str | None = None,
    available_options=None,
    username: str | None = None,
    password: str | None = None,
    timeout: int = 180,
) -> str:
    """Scannt eine einzelne Seite (Flachbett oder ein ADF-Blatt) nach
    out_path (JPEG). Vorgabe-Timeout an die SANE-Variante angeglichen
    (scanner.py: scan_single_page) - ein echter Scan-Vorgang kann je nach
    Auflösung/Gerät durchaus 30-90s dauern, manche Geräte antworten erst,
    wenn die physische Seite fertig gescannt ist."""
    base = _base_url(device_id)
    ctx = escl_ssl_context() if base.startswith("https://") else None
    headers = escl_auth_header(username, password)

    try:
        caps = get_capabilities(device_id, username, password, timeout=10)
    except ScannerError:
        caps = None
    input_source = "Feeder" if source in _ADF_SOURCE_VALUES else "Platen"
    width, height = _max_region_units(caps, input_source)
    body = _build_scan_settings_xml(mode, resolution, source, width, height)

    job_url = _create_job(base, ctx, headers, body, timeout, is_feeder=(input_source == "Feeder"))
    try:
        got = _fetch_next_document(job_url, ctx, headers, out_path, timeout, base=base)
    finally:
        _delete_job(job_url, ctx, headers)
    if not got:
        raise ScannerError("Scanner hat kein Bild geliefert.")
    return out_path


def scan_batch_adf(
    device_id: str,
    out_dir: str,
    mode: str = "Color",
    resolution: str = "300",
    source: str | None = None,
    available_options=None,
    username: str | None = None,
    password: str | None = None,
    timeout: int = 90,
) -> list[str]:
    """Scannt Seiten aus dem automatischen Einzug, bis dieser leer ist.
    `timeout` gilt PRO Seite (nicht für den gesamten Stapel) - an echter
    Hardware beobachtet, dass eine einzelne Seite je nach Auflösung
    durchaus 30-90s dauern kann, bevor das Gerät überhaupt antwortet.

    Reale Geräte terminieren einen ADF-Batch auf zwei unterschiedliche
    Arten - beide werden abgefangen:
    - Mehrseiten-pro-Job: ein Auftrag, wiederholt NextDocument bis 404.
    - Eine-Seite-pro-Job (u.a. verbreitet bei Kyocera/HP): jede Seite
      braucht einen eigenen Auftrag; "leer" zeigt sich als Fehler beim
      Auftrag selbst, nicht bei NextDocument.
    """
    base = _base_url(device_id)
    ctx = escl_ssl_context() if base.startswith("https://") else None
    headers = escl_auth_header(username, password)

    try:
        caps = get_capabilities(device_id, username, password, timeout=10)
    except ScannerError:
        caps = None
    width, height = _max_region_units(caps, "Feeder")
    body = _build_scan_settings_xml(mode, resolution, source or "ADF", width, height)

    produced: list[str] = []
    page_num = 1
    job_url: str | None = None
    # Zählt, wie oft direkt hintereinander ein frischer Auftrag ohne auch
    # nur eine gelieferte Seite endete - Sicherheitsnetz gegen eine
    # Endlosschleife, falls beide Terminierungsstrategien fehlschlagen.
    empty_fresh_jobs_in_a_row = 0
    try:
        while True:
            if job_url is None:
                try:
                    job_url = _create_job(base, ctx, headers, body, timeout, is_feeder=True)
                except AdfEmptyError:
                    if page_num == 1:
                        # Vor dem ersten Blatt: gegen ScannerStatus prüfen,
                        # ob das Gerät wirklich "leer" meldet, statt blind
                        # von einem echten Fehler auszugehen.
                        state = _get_adf_state(base, ctx, headers, timeout)
                        if state and "Loaded" in state:
                            raise ScannerError(
                                "Scanner meldet Papier im Einzug, nimmt den Auftrag aber "
                                "trotzdem nicht an."
                            )
                        return produced  # kein Papier eingelegt - leerer Stapel ist kein Fehler
                    break  # normales Ende nach mindestens einer Seite
            out_path = f"{out_dir.rstrip('/')}/page-{page_num:03d}.jpg"
            got = _fetch_next_document(job_url, ctx, headers, out_path, timeout, base=base)
            if got:
                produced.append(out_path)
                page_num += 1
                empty_fresh_jobs_in_a_row = 0
                # Mehrseiten-pro-Job-Strategie: denselben Auftrag weiter
                # abfragen (job_url NICHT zurücksetzen), bis 404 kommt.
                continue
            # 404 auf NextDocument: entweder wirklich das Ende des Stapels,
            # oder das Gerät braucht pro Seite einen eigenen Auftrag - genau
            # einmal mit frischem Auftrag nachfassen, bevor aufgegeben wird.
            _delete_job(job_url, ctx, headers)
            job_url = None
            empty_fresh_jobs_in_a_row += 1
            if empty_fresh_jobs_in_a_row > 1:
                break
    finally:
        if job_url:
            _delete_job(job_url, ctx, headers)
    return produced
