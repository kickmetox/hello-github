"""Undervolt- und OC-Datenmodell. Spannung wird nie geschrieben."""

from __future__ import annotations

import json
from pathlib import Path

from crossos.safety import SafetyError

_CPU = {"intel", "amd"}
_GPU = {"nvidia", "amd", "intel"}


def save_offsets(payload: dict, state_file: Path) -> dict:
    if not isinstance(payload, dict):
        raise SafetyError("Undervolt-Profil muss ein Objekt sein.")
    cpu = payload.get("cpu") or {}
    gpu = payload.get("gpu") or {}
    if not isinstance(cpu, dict) or not isinstance(gpu, dict):
        raise SafetyError("cpu und gpu müssen Objekte sein.")
    cpu_vendor = str(cpu.get("vendor", "intel")).lower()
    gpu_vendor = str(gpu.get("vendor", "nvidia")).lower()
    if cpu_vendor not in _CPU or gpu_vendor not in _GPU:
        raise SafetyError("CPU-Hersteller intel/amd, GPU-Hersteller nvidia/amd/intel.")
    record = {
        "cpu": {
            "vendor": cpu_vendor,
            "core_offset_mv": _millivolts(cpu.get("core_offset_mv", 0)),
            "cache_offset_mv": _millivolts(cpu.get("cache_offset_mv", 0)),
        },
        "gpu": {
            "vendor": gpu_vendor,
            "offset_mv": _millivolts(gpu.get("offset_mv", 0)),
            "core_clock_mhz": _megahertz(gpu.get("core_clock_mhz", 0)),
            "mem_clock_mhz": _megahertz(gpu.get("mem_clock_mhz", 0)),
        },
        "applied": False,
        "voltage_written": False,
        "notes": _notes(cpu_vendor, gpu_vendor),
    }
    state = _load(state_file)
    state["undervolt"] = record
    _store(state_file, state)
    return record


def load_offsets(state_file: Path) -> dict | None:
    return _load(state_file).get("undervolt")


def _millivolts(value: object) -> int:
    if type(value) is not int:
        raise SafetyError("Spannungs-Offset muss eine ganze Zahl in Millivolt sein.")
    if not -250 <= value <= 100:
        raise SafetyError("Spannungs-Offset muss zwischen -250 und 100 mV liegen.")
    return value


def _megahertz(value: object) -> int:
    if type(value) is not int:
        raise SafetyError("Takt-Offset muss eine ganze Zahl in MHz sein.")
    if not -1000 <= value <= 1000:
        raise SafetyError("Takt-Offset muss zwischen -1000 und 1000 MHz liegen.")
    return value


def _notes(cpu_vendor: str, gpu_vendor: str) -> list[str]:
    notes = [
        "Offsets werden nur gespeichert. Es wird kein MSR, kein ryzenadj und kein nvidia-smi -lgc aufgerufen.",
    ]
    if cpu_vendor == "intel":
        notes.append(
            "Moderne Intel-CPUs sperren Undervolting häufig: Plundervolt-Mitigation, "
            "IA32_OVERCLOCKING_POLICY bzw. Overclocking Lock / CFG-Lock, ab etwa Ice Lake und Comet Lake "
            "in vielen OEM-Firmwares. Ein gespeicherter Offset ändert die Spannung dann nicht, selbst wenn ein anderes Werkzeug ihn schriebe."
        )
    else:
        notes.append("AMD-CPU-Offsets bleiben gespeichert. ryzenadj oder ein SMU-Zugriff wird nicht gestartet.")
    if gpu_vendor == "nvidia":
        notes.append("NVIDIA-Offset wird nicht an nvidia-settings oder nvidia-smi übergeben.")
    elif gpu_vendor == "amd":
        notes.append("AMD-GPU-Offset wird nicht an CoreCtrl, LACT oder sysfs übergeben.")
    else:
        notes.append("Intel-GPU-Offset wird nicht an einen Treiber übergeben.")
    return notes


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _store(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
