# FreiTV

iPhone-App (SwiftUI) für freie TV-Streams, öffentlich-rechtliche Mediatheken und freies Kino.

**Kontakt:** [ame@sellerbach.de](mailto:ame@sellerbach.de)

## Funktionen

- **Programm** – durchscrollbare Programminfos im TV-Stil (Now/Next)
- **Live** – freie Live-/Demo-Kanäle + eigene M3U/M3U8-Playlists
- **Mediathek** – ARD, ZDF, ARTE, 3sat, Dritte Programme, KiKA, funk, phoenix, DW, ORF ON, SRF Play u. a.
- **Kino & Filme** – Creative-Commons-/Public-Domain-Filme und freie Archive
- **Favoriten** – sortierbar (manuell per Drag & Drop, Name, Neueste, Typ)
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

## Hinweise

Mediatheken öffnen die offiziellen Portale der Anbieter in der App. Nur Streams und Playlists verwenden, die du rechtlich empfangen darfst.

## Tests (ohne Xcode)

```bash
python3 scripts/test_m3u_parser.py
python3 scripts/test_freitv_catalog.py
```
