"""Modul 3: Lüfter, Leistung, Ladeschwelle, Undervolt-Daten."""

from crossos.hardware.battery import apply_threshold
from crossos.hardware.fans import export_custom, export_profile, profile_names
from crossos.hardware.power import apply_ppd, list_plans
from crossos.hardware.probe import probe
from crossos.hardware.undervolt import load_offsets, save_offsets
from crossos.hardware.vendors import vendor_map

__all__ = [
    "apply_ppd",
    "apply_threshold",
    "export_custom",
    "export_profile",
    "list_plans",
    "load_offsets",
    "probe",
    "profile_names",
    "save_offsets",
    "vendor_map",
]
