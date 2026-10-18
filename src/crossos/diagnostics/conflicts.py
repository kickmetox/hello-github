"""Konkrete Paketvorschläge für fehlende DLLs und .so-Dateien.

Unbekannte Bibliotheken bekommen einen Suchplan, keinen erfundenen Paketnamen.
"""

from __future__ import annotations

import re

from crossos.migrator.packages import PackageBridge
from crossos.safety import SafetyError, validate_package_name

DLL_MAP: dict[str, dict] = {
    "vcruntime140.dll": {
        "winget": "Microsoft.VCRedist.2015+.x64",
        "note_de": "Visual C++ 2015–2022 Redistributable, x64. Die DLL nicht einzeln aus dem Netz legen.",
    },
    "vcruntime140_1.dll": {
        "winget": "Microsoft.VCRedist.2015+.x64",
        "note_de": "Gehört zum gleichen VC++-2015–2022-Paket wie VCRUNTIME140.dll.",
    },
    "msvcp140.dll": {
        "winget": "Microsoft.VCRedist.2015+.x64",
        "note_de": "C++-Standardbibliothek aus dem VC++-Redistributable.",
    },
    "msvcp140_1.dll": {
        "winget": "Microsoft.VCRedist.2015+.x64",
        "note_de": "Zusätzliche MSVCP-DLL aus demselben Redistributable.",
    },
    "python312.dll": {
        "winget": "Python.Python.3.12",
        "note_de": "Python-3.12-Laufzeit. Eine fremde python312.dll nicht ins System32 kopieren.",
    },
    "python3.dll": {
        "winget": "Python.Python.3.12",
        "note_de": "Stabile Python-3-DLL. Die passende Installation liefert sie mit.",
    },
}

SO_MAP: dict[str, dict] = {
    "libssl.so.3": {"apt": "libssl3", "dnf": "openssl-libs", "pacman": "openssl", "note_de": "OpenSSL-3-Bibliothek."},
    "libcrypto.so.3": {"apt": "libssl3", "dnf": "openssl-libs", "pacman": "openssl", "note_de": "Gehört zum OpenSSL-Paket, nicht zu einem zweiten Paket."},
    "libgl.so.1": {"apt": "libgl1", "dnf": "mesa-libGL", "pacman": "libglvnd", "note_de": "OpenGL-Loader. Der eigentliche Treiber (Mesa oder NVIDIA) ist davon getrennt."},
    "libgtk-3.so.0": {"apt": "libgtk-3-0t64", "dnf": "gtk3", "pacman": "gtk3", "note_de": "Auf Ubuntu vor 24.04 hieß das Paket libgtk-3-0."},
    "libstdc++.so.6": {"apt": "libstdc++6", "dnf": "libstdc++", "pacman": "gcc-libs", "note_de": "GNU-C++-Laufzeit der Distribution. Nicht aus einem Fremdpaket mischen."},
    "libffi.so.8": {"apt": "libffi8", "dnf": "libffi", "pacman": "libffi", "note_de": "libffi 8."},
    "libpcre2-8.so.0": {"apt": "libpcre2-8-0", "dnf": "pcre2", "pacman": "pcre2", "note_de": "PCRE2, 8-Bit."},
    "libnss3.so": {"apt": "libnss3", "dnf": "nss", "pacman": "nss", "note_de": "Network Security Services."},
    "libasound.so.2": {"apt": "libasound2t64", "dnf": "alsa-lib", "pacman": "alsa-lib", "note_de": "ALSA-Userspace. Auf älteren Ubuntu-Versionen: libasound2."},
    "libcuda.so.1": {
        "note_de": "libcuda kommt vom NVIDIA-Treiber, nicht aus einem generischen Bibliothekspaket. Kein blindes apt-Paket.",
    },
}

_DLL_RE = re.compile(r"\b([A-Za-z0-9_+.-]{1,80}\.dll)\b", re.IGNORECASE)
_SO_RE = re.compile(r"\b(lib[A-Za-z0-9_+.-]+\.so(?:\.[0-9]+)*)\b")
_SONAME_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+_-]{0,80}$")


def solve_text(text: str) -> list[dict]:
    found: list[dict] = []
    seen: set[str] = set()
    for match in _DLL_RE.finditer(text):
        name = match.group(1)
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append(_dll(name))
    for match in _SO_RE.finditer(text):
        name = match.group(1)
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append(_so(name))
    return found


def _dll(name: str) -> dict:
    spec = DLL_MAP.get(name.lower())
    plans = []
    if spec and "winget" in spec:
        plans.append(PackageBridge().plan("winget", [spec["winget"]], "install"))
    return {
        "kind": "dll",
        "name": name,
        "known": spec is not None,
        "note_de": (spec or {}).get("note_de", "Kein fester Paketname für diese DLL. Nicht aus einer Zufallsquelle nachladen."),
        "plans": plans,
        "executed": False,
    }


def _so(name: str) -> dict:
    spec = SO_MAP.get(name.lower(), {})
    plans = []
    bridge = PackageBridge()
    for manager in ("apt", "dnf", "pacman"):
        package = spec.get(manager)
        if not package:
            continue
        plans.append(bridge.plan(manager, [package], "install"))
    search = None
    if not plans and _SONAME_SAFE.fullmatch(name):
        # Suchbegriff ist der Dateiname, bereits durch die Extraktions-Regex begrenzt.
        try:
            validate_package_name(name.replace(".so", "").split(".so")[0])
        except SafetyError:
            name = name
        search = {
            "argv": ["apt-file", "search", name],
            "note_de": "Kein Katalogtreffer. apt-file search ist ein Plan und wird nicht ausgeführt.",
            "executed": False,
        }
    return {
        "kind": "so",
        "name": name,
        "known": bool(spec),
        "note_de": spec.get("note_de", "Bibliothek ist nicht im festen Katalog. Nur suchen, nicht raten."),
        "plans": plans,
        "search": search,
        "executed": False,
    }
