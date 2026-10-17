"""HTTP- und GraphQL-Anfragen aus der IDE oder aus .http-Dateien."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def parse_http_file(text: str) -> dict:
    lines = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        cleaned.append(line)
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    if not cleaned:
        return {"ok": False, "error": "Leere Anfrage."}
    request_line = cleaned[0].strip()
    parts = request_line.split()
    if len(parts) == 1:
        method, url = "GET", parts[0]
    elif len(parts) >= 2:
        method, url = parts[0].upper(), parts[1]
    else:
        return {"ok": False, "error": "Erste Zeile muss 'METHODE URL' sein."}
    headers: dict[str, str] = {}
    index = 1
    while index < len(cleaned) and cleaned[index].strip():
        if ":" not in cleaned[index]:
            return {"ok": False, "error": f"Ungültiger Header: {cleaned[index]}"}
        key, value = cleaned[index].split(":", 1)
        headers[key.strip()] = value.strip()
        index += 1
    while index < len(cleaned) and not cleaned[index].strip():
        index += 1
    body = "\n".join(cleaned[index:])
    return {"ok": True, "method": method, "url": url, "headers": headers, "body": body}


def send_request(method: str, url: str, headers: dict | None = None, body: str = "", timeout: int = 30) -> dict:
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "Nur http- und https-URLs sind erlaubt."}
    data = body.encode("utf-8") if body and method.upper() not in {"GET", "HEAD"} else None
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(2_000_000)
            charset = response.headers.get_content_charset() or "utf-8"
            text = raw.decode(charset, errors="replace")
            return {
                "ok": True,
                "status": response.status,
                "reason": response.reason,
                "headers": dict(response.headers.items()),
                "body": text,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read(2_000_000)
        return {
            "ok": False,
            "status": exc.code,
            "reason": exc.reason,
            "headers": dict(exc.headers.items()) if exc.headers else {},
            "body": raw.decode("utf-8", errors="replace"),
            "error": f"HTTP {exc.code}",
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "status": 0, "body": ""}


def pretty_body(text: str) -> str:
    try:
        return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return text
