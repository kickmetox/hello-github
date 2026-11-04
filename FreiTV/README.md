# FreiTV

iPhone-App (SwiftUI) zum Abspielen freier Internet-Streams und eigener M3U/M3U8-Playlists.

**Kontakt:** [ame@sellerbach.de](mailto:ame@sellerbach.de)

## Funktionen

- Eingebaute Demo-Kanäle (öffentliche HLS-Teststreams)
- HLS-Player mit AVKit
- Suche und Kategorien
- Favoriten
- M3U/M3U8-Playlist per URL laden
- App-Icon unter `FreiTV/Assets.xcassets/AppIcon.appiconset/`

## Voraussetzungen

- macOS mit Xcode 15+
- iOS 17+ (Simulator oder Gerät)
- Apple Developer Team in Xcode setzen (`Signing & Capabilities`)

## Start

1. `FreiTV.xcodeproj` in Xcode öffnen
2. Signing Team wählen (Bundle-ID: `de.sellerbach.freitv`)
3. iPhone-Simulator oder Gerät auswählen
4. Run (`⌘R`)

## Eigene freie Kanäle

In der App: **Playlist-Icon** → M3U-URL eintragen → **Playlist laden**.

Nur Streams verwenden, die du rechtlich empfangen darfst. Die App enthält keine illegalen Senderlisten.

## Projektstruktur

```
FreiTV/
├── FreiTV.xcodeproj
└── FreiTV/
    ├── FreiTVApp.swift
    ├── ContentView.swift
    ├── Models/
    ├── Services/
    ├── Views/
    ├── Resources/sample.m3u
    └── Assets.xcassets/
```
