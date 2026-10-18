"""Modul 2: lokale Diagnose ohne Cloud-LLM."""

from crossos.diagnostics.firmware import firmware_status
from crossos.diagnostics.parser import parse_log
from crossos.diagnostics.repair import apply_allowlisted, link_apply, render_scripts
from crossos.diagnostics.rescue import rescue_plan
from crossos.platform_detect import default_shell_for_host


def diagnose(text: str, *, shell: str | None = None) -> dict:
    chosen = shell or default_shell_for_host()
    if chosen not in {"bash", "powershell"}:
        chosen = default_shell_for_host()
    findings = []
    for raw in parse_log(text):
        scripts = render_scripts(raw)
        raw["scripts"] = scripts
        raw["script"] = scripts[chosen]
        raw["apply"] = link_apply(raw["code"], unit=raw.get("unit"))
        findings.append(raw)
    if not findings:
        findings.append(
            {
                "code": "unmatched",
                "title": "Keine bekannte Signatur",
                "plain_de": "Im Text ist keiner der hinterlegten Codes oder Muster. Es wird kein Reparaturskript erfunden.",
                "likely": [],
                "evidence": text.strip()[:240],
                "scripts": {"bash": "", "powershell": ""},
                "script": "",
                "apply": link_apply("unmatched"),
            }
        )
    return {
        "shell": chosen,
        "findings": findings,
        "dry_run": True,
        "executed": False,
    }


__all__ = [
    "apply_allowlisted",
    "diagnose",
    "firmware_status",
    "rescue_plan",
]
