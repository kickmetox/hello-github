from __future__ import annotations

import json
import time
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

    def create_design_generation(self, brief: str) -> dict:
        """POST /generations, dokumentiert als Create design generation job."""
        body = {
            "brief": brief[:5000],
            "design_type": {"type": "preset", "name": "presentation"},
        }
        return self._request("POST", "/generations", body)

    def get_design_generation(self, job_id: str) -> dict:
        """GET /generations/{jobId}, dokumentiert als Get design generation job."""
        return self._request("GET", f"/generations/{urllib.parse.quote(job_id)}")

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


def design_id_from_generation(payload: dict) -> str:
    job = payload.get("job") if isinstance(payload, dict) else None
    if not isinstance(job, dict):
        return ""
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    design = result.get("design") if isinstance(result.get("design"), dict) else {}
    return str(design.get("id") or "")


def request_canva_magic(
    token: str,
    base_url: str,
    brief: str,
    opener=None,
    polls: int = 4,
    pause: float = 0.4,
) -> str:
    """Canva Magic Design nur mit Token. Ohne Token bleibt urllib zu."""
    if not (token or "").strip():
        raise CanvaAPIError("Kein Canva-Zugriffstoken hinterlegt. Es wurde nichts gesendet.")
    sentence = " ".join((brief or "").split())
    if not sentence:
        raise CanvaAPIError("Bitte einen Satz eingeben.")
    client = CanvaClient(token.strip(), base_url or DEFAULT_BASE, opener=opener)
    payload = client.create_design_generation(sentence)
    design_id = design_id_from_generation(payload)
    job = payload.get("job") if isinstance(payload.get("job"), dict) else {}
    status = str(job.get("status") or "")
    job_id = str(job.get("id") or "")
    if status == "failed":
        raise CanvaAPIError(_generation_failure(job))
    attempts = 1
    while not design_id and status == "in_progress" and job_id and attempts < polls:
        if pause:
            time.sleep(pause)
        attempts += 1
        payload = client.get_design_generation(job_id)
        design_id = design_id_from_generation(payload)
        job = payload.get("job") if isinstance(payload.get("job"), dict) else {}
        status = str(job.get("status") or "")
        job_id = str(job.get("id") or job_id)
        if status == "failed":
            raise CanvaAPIError(_generation_failure(job))
    if design_id:
        return (
            f"Canva-Design-ID: {design_id}\n"
            "PPTX-Export: Canva → Studio und Connect, diese Design-ID eintragen, Export als PPTX."
        )
    if job_id:
        return f"Canva-Auftrag {job_id} läuft noch. Eine Design-ID liegt noch nicht vor."
    raise CanvaAPIError("Canva hat keine Design-ID geliefert.")


def _generation_failure(job: dict) -> str:
    error = job.get("error") if isinstance(job.get("error"), dict) else {}
    detail = str(error.get("message") or "").strip()
    if detail:
        return f"Canva konnte das Design nicht erzeugen. {detail}"
    return "Canva konnte das Design nicht erzeugen."
