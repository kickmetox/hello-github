from __future__ import annotations


def constrain_font(brand: dict, font: str, role: str = "body") -> str:
    if not brand or not brand.get("locked"):
        return font
    if role == "heading":
        return brand.get("heading_font") or font
    return brand.get("body_font") or font


def constrain_color(brand: dict, color: str) -> str:
    if not brand or not brand.get("locked"):
        return color
    allowed = brand.get("colors") or []
    if any(color.lower() == item.lower() for item in allowed):
        return color
    return allowed[0] if allowed else color


def palette_from_seed(seed: str) -> list[str]:
    """Dieselbe Hue-Verschiebung wie das optionale .NET-Werkzeug."""
    hex_color = seed.strip().lstrip("#")
    if len(hex_color) != 6:
        hex_color = "0B63E5"
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        h = s = 0.0
    else:
        d = mx - mn
        s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r:
            h = ((g - b) / d) % 6
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h /= 6
    colors = []
    for step in range(5):
        colors.append(_hsl_to_hex((h + step * 0.08) % 1, min(1, s + 0.05), min(0.72, max(0.28, l))))
    return colors


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    def hue(p, q, t):
        if t < 0:
            t += 1
        if t > 1:
            t -= 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    if s == 0:
        r = g = b = l
    else:
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        r = hue(p, q, h + 1 / 3)
        g = hue(p, q, h)
        b = hue(p, q, h - 1 / 3)
    return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


def dotnet_palette(seed: str) -> list[str]:
    import json
    import shutil
    import subprocess

    from officedisplay.paths import dotnet_project

    if shutil.which("dotnet") is None:
        return palette_from_seed(seed)
    try:
        result = subprocess.run(
            ["dotnet", "run", "--project", str(dotnet_project()), "--", seed],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return palette_from_seed(seed)
    if result.returncode != 0:
        return palette_from_seed(seed)
    try:
        data = json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return palette_from_seed(seed)
    if isinstance(data, list) and data:
        return [str(item) for item in data]
    return palette_from_seed(seed)
