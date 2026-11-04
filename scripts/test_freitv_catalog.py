#!/usr/bin/env python3
"""Struktur- und Katalogtests für FreiTV (Mediathek, Filme, Streams)."""

from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "FreiTV" / "FreiTV"


def extract_urls(text: str) -> list[str]:
    return re.findall(r'URL\(string: "(https://[^"]+)"\)!', text)


def extract_names(text: str, key: str = "name") -> list[str]:
    return re.findall(rf'{key}:\s*"([^"]+)"', text)


def http_ok(url: str, timeout: int = 15) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "FreiTV-Test/1.1"}, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status
    except Exception:
        req = urllib.request.Request(url, headers={"User-Agent": "FreiTV-Test/1.1"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status


def main() -> int:
    required = [
        "Models/StableID.swift",
        "Models/MediaLibrary.swift",
        "Models/Movie.swift",
        "Models/ProgramEntry.swift",
        "Models/FavoriteItem.swift",
        "Services/MediaStore.swift",
        "Services/MediaLibraryCatalog.swift",
        "Services/MovieCatalog.swift",
        "Services/ProgramGuideService.swift",
        "Views/ProgramGuideView.swift",
        "Views/MediathekListView.swift",
        "Views/MoviesView.swift",
        "Views/FavoritesView.swift",
        "Views/WebBrowserView.swift",
        "Views/StreamPlayerView.swift",
    ]
    missing = [path for path in required if not (APP / path).exists()]
    assert not missing, f"Fehlende Dateien: {missing}"

    libraries = (APP / "Services/MediaLibraryCatalog.swift").read_text(encoding="utf-8")
    movies = (APP / "Services/MovieCatalog.swift").read_text(encoding="utf-8")
    channels = (APP / "Services/ChannelCatalog.swift").read_text(encoding="utf-8")
    about = (APP / "Views/AboutView.swift").read_text(encoding="utf-8")
    favorites = (APP / "Views/FavoritesView.swift").read_text(encoding="utf-8")
    content = (APP / "ContentView.swift").read_text(encoding="utf-8")

    library_names = extract_names(libraries)
    must_have = [
        "ARD Mediathek",
        "ZDF Mediathek",
        "ARTE",
        "3sat Mediathek",
        "BR Mediathek",
        "NDR Mediathek",
        "WDR Mediathek",
        "SWR Mediathek",
        "MDR Mediathek",
        "hr Mediathek",
        "rbb Mediathek",
        "Radio Bremen",
        "SR Mediathek",
        "KiKA",
        "funk",
        "Deutsche Welle",
        "ORF ON",
        "SRF Play",
        "Internet Archive – Feature Films",
    ]
    for name in must_have:
        assert name in library_names, f"Mediathek fehlt: {name}"
    assert len(library_names) >= 20, library_names

    movie_titles = extract_names(movies, key="title")
    assert "Big Buck Bunny" in movie_titles
    assert "Elephants Dream" in movie_titles
    assert any("Feature Films" in title or "Open Source" in title for title in movie_titles)

    assert "ame@sellerbach.de" in about
    assert "FavoriteSortMode" in favorites or "Sortierung" in favorites
    assert "ProgramGuideView" in content
    assert "MediathekListView" in content
    assert "MoviesView" in content
    assert "FavoritesView" in content

    stream_urls = extract_urls(channels) + [
        u for u in extract_urls(movies) if u.endswith((".m3u8", ".mp4"))
    ]
    # unique preserving order
    seen: set[str] = set()
    unique_streams: list[str] = []
    for url in stream_urls:
        if url not in seen:
            seen.add(url)
            unique_streams.append(url)

    print(f"Mediatheken: {len(library_names)}")
    print(f"Filme: {len(movie_titles)}")
    print(f"Stream-URLs prüfen: {len(unique_streams)}")
    failures: list[str] = []
    for url in unique_streams:
        try:
            code = http_ok(url)
            print(f"  HTTP {code}  {url}")
            if code >= 400:
                failures.append(f"{code} {url}")
        except Exception as exc:
            print(f"  ERR {url}: {exc}")
            failures.append(str(url))

    assert not failures, failures
    print("OK: Kataloge, UI-Hooks und Streams verifiziert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
