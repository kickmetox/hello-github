from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Repository- bzw. Programmordner (über src/officedisplay)."""
    return Path(__file__).resolve().parents[2]


def help_path() -> Path:
    return project_root() / "docs" / "HILFE.md"


def icon_path() -> Path:
    return project_root() / "assets" / "app-icon.png"


def model_path() -> Path:
    return project_root() / "models" / "layout_classifier.onnx"


def native_candidates() -> list[Path]:
    root = project_root()
    names = ("libodnative.so", "odnative.dll", "libodnative.dylib")
    bases = [
        root / "native" / "cpp" / "build",
        root / "native" / "cpp" / "build" / "Release",
        root / "native" / "cpp" / "build" / "Debug",
        root / "src" / "officedisplay" / "native",
    ]
    return [base / name for base in bases for name in names]


def dotnet_project() -> Path:
    return project_root() / "dotnet" / "OfficeDisplay.Tools" / "OfficeDisplay.Tools.csproj"


def secrets_path() -> Path:
    return Path.home() / ".config" / "officedisplay" / "secrets.json"


def dotnet_solution() -> Path:
    return project_root() / "OfficeDisplay.sln"


def macros_dir() -> Path:
    return project_root() / "macros"


def analytics_path() -> Path:
    return project_root() / "data" / "verweildauer.json"


def media_dir() -> Path:
    path = project_root() / "data" / "medien"
    path.mkdir(parents=True, exist_ok=True)
    return path


def weights_path() -> Path:
    return project_root() / "models" / "layout_weights.npz"


def default_brand_path() -> Path:
    return project_root() / "assets" / "brand.json"


def secrets_path() -> Path:
    """Ungenutzt. Office Display speichert keine Cloud-Schlüssel."""
    return Path.home() / ".config" / "officedisplay" / "unused-secrets.json"
