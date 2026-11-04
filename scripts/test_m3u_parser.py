#!/usr/bin/env python3
"""Spiegel-Test der M3U-Parsing-Logik aus FreiTV/Services/M3UParser.swift."""

from __future__ import annotations

import re
import sys
from pathlib import Path


SAMPLE = """#EXTM3U
#EXTINF:-1 tvg-id="bbb" tvg-country="International" group-title="Demo",Big Buck Bunny
https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8
#EXTINF:-1 group-title="News",Alpha News
https://example.com/live.m3u8
# Kommentar
not-a-url
#EXTINF:-1,Ohne Attribute
https://cdn.example/stream.m3u8
"""


def extract_name(line: str) -> str:
    if "," in line:
        name = line.split(",", 1)[1].strip()
        return name or "Unbekannt"
    return "Unbekannt"


def extract_attribute(key: str, line: str) -> str | None:
    match = re.search(rf'{key}="([^"]*)"', line)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def parse(text: str) -> list[dict]:
    lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
    channels: list[dict] = []
    pending = {
        "name": "Unbekannt",
        "category": "Playlist",
        "country": "International",
        "logo": None,
    }

    for line in lines:
        if line.startswith("#EXTINF:"):
            pending = {
                "name": extract_name(line),
                "category": extract_attribute("group-title", line) or "Playlist",
                "country": extract_attribute("tvg-country", line) or "International",
                "logo": extract_attribute("tvg-logo", line),
            }
        elif line.startswith("#"):
            continue
        elif line.startswith("http://") or line.startswith("https://"):
            channels.append({**pending, "url": line})
            pending = {
                "name": "Unbekannt",
                "category": "Playlist",
                "country": "International",
                "logo": None,
            }
    return channels


def main() -> int:
    channels = parse(SAMPLE)
    assert len(channels) == 3, channels
    assert channels[0]["name"] == "Big Buck Bunny"
    assert channels[0]["category"] == "Demo"
    assert channels[0]["country"] == "International"
    assert channels[1]["name"] == "Alpha News"
    assert channels[1]["category"] == "News"
    assert channels[2]["name"] == "Ohne Attribute"
    assert channels[2]["category"] == "Playlist"

    sample_path = Path(__file__).resolve().parents[1] / "FreiTV" / "FreiTV" / "Resources" / "sample.m3u"
    sample_channels = parse(sample_path.read_text(encoding="utf-8"))
    assert len(sample_channels) == 5, sample_channels
    assert sample_channels[0]["name"] == "Big Buck Bunny"
    assert sample_channels[-1]["category"] == "Live"
    assert all(c["url"].startswith("https://") for c in sample_channels)

    required = [
        "FreiTV/FreiTV.xcodeproj/project.pbxproj",
        "FreiTV/FreiTV/FreiTVApp.swift",
        "FreiTV/FreiTV/ContentView.swift",
        "FreiTV/FreiTV/Services/M3UParser.swift",
        "FreiTV/FreiTV/Assets.xcassets/AppIcon.appiconset/AppIcon.png",
        "FreiTV/FreiTV/Views/AboutView.swift",
    ]
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in required if not (root / path).exists()]
    assert not missing, f"Fehlende Dateien: {missing}"

    about = (root / "FreiTV/FreiTV/Views/AboutView.swift").read_text(encoding="utf-8")
    assert "ame@sellerbach.de" in about

    print("OK: M3U-Parser und Projektstruktur verifiziert")
    print(f"  sample.m3u Kanäle: {len(sample_channels)}")
    for channel in sample_channels:
        print(f"  - {channel['name']} [{channel['category']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
