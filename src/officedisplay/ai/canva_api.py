from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request


class CanvaAPIError(Exception):
    pass


DEFAULT_BASE = "https://api.canva.com/rest/v1"
AUTHORIZE_URL = "https://www.canva.com/api/oauth/authorize"
SCOPES = [
    "brandtemplate:meta:read",
    "brandtemplate:content:read",
    "design:content:read",
    "design:content:write",
]


def authorize_url(client_id: str, redirect_uri: str, state: str, code_challenge: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


class CanvaClient:
    """Canva Connect. Jeder Aufruf braucht einen Klick und ein eigenes Token."""

    def __init__(self, access_token: str, base_url: str = DEFAULT_BASE, opener=None):
        if not access_token:
            raise CanvaAPIError("Kein Canva-Zugriffstoken hinterlegt.")
        if not str(base_url).startswith("https://"):
            raise CanvaAPIError("Die Canva-Basisadresse muss HTTPS sein.")
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self.opener = opener

    def list_brand_templates(self, query: str = "") -> dict:
        path = "/brand-templates"
        if query:
            path += "?" + urllib.parse.urlencode({"query": query})
        return self._request("GET", path)

    def get_dataset(self, template_id: str) -> dict:
        return self._request("GET", f"/brand-templates/{urllib.parse.quote(template_id)}/dataset")

    def create_autofill(self, template_id: str, data: dict, title: str) -> dict:
        body = {
            "type": "create_from_brand_template",
            "brand_template_id": template_id,
            "title": title,
            "data": data,
        }
        return self._request("POST", "/autofills", body)

    def get_autofill(self, job_id: str) -> dict:
        return self._request("GET", f"/autofills/{urllib.parse.quote(job_id)}")

    def create_export(self, design_id: str, file_type: str = "pptx") -> dict:
        body = {"design_id": design_id, "format": {"type": file_type}}
        return self._request("POST", "/exports", body)

    def get_export(self, job_id: str) -> dict:
        return self._request("GET", f"/exports/{urllib.parse.quote(job_id)}")

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            open_fn = self.opener or urllib.request.urlopen
            with open_fn(request, timeout=45) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise CanvaAPIError(f"Canva HTTP {exc.code}. {detail}") from exc
        except CanvaAPIError:
            raise
        except Exception as exc:
            raise CanvaAPIError("Canva-API nicht erreichbar.") from exc
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CanvaAPIError("Canva-Antwort ist kein JSON.") from exc
