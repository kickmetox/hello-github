import Foundation

enum MediaLibraryCatalog {
    /// Freie öffentlich-rechtliche Mediatheken und Portale (DE/AT/CH/EU) – Öffnung in der In-App-Ansicht.
    static let all: [MediaLibrary] = [
        MediaLibrary(
            key: "ard",
            name: "ARD Mediathek",
            subtitle: "Das Erste, Dritte, Live & Archive",
            homeURL: URL(string: "https://www.ardmediathek.de")!
        ),
        MediaLibrary(
            key: "zdf",
            name: "ZDF Mediathek",
            subtitle: "ZDF, neo, info, Filme & Serien",
            homeURL: URL(string: "https://www.zdf.de")!
        ),
        MediaLibrary(
            key: "arte",
            name: "ARTE",
            subtitle: "Kultur, Dokus, Filme – DE/FR",
            homeURL: URL(string: "https://www.arte.tv/de/")!,
            region: "Europa"
        ),
        MediaLibrary(
            key: "3sat",
            name: "3sat Mediathek",
            subtitle: "Kultur und Wissenschaft",
            homeURL: URL(string: "https://www.3sat.de")!,
            region: "DACH"
        ),
        MediaLibrary(
            key: "phoenix",
            name: "phoenix",
            subtitle: "Politik, Ereignisse, Dokus",
            homeURL: URL(string: "https://www.phoenix.de")!
        ),
        MediaLibrary(
            key: "br",
            name: "BR Mediathek",
            subtitle: "Bayerischer Rundfunk",
            homeURL: URL(string: "https://www.br.de/mediathek/")!,
            region: "Bayern"
        ),
        MediaLibrary(
            key: "ndr",
            name: "NDR Mediathek",
            subtitle: "Norddeutscher Rundfunk",
            homeURL: URL(string: "https://www.ndr.de/fernsehen/")!,
            region: "Nord"
        ),
        MediaLibrary(
            key: "wdr",
            name: "WDR Mediathek",
            subtitle: "Westdeutscher Rundfunk",
            homeURL: URL(string: "https://www1.wdr.de/mediathek/video/index.html")!,
            region: "NRW"
        ),
        MediaLibrary(
            key: "swr",
            name: "SWR Mediathek",
            subtitle: "Südwestrundfunk",
            homeURL: URL(string: "https://www.swr.de")!,
            region: "Südwest"
        ),
        MediaLibrary(
            key: "mdr",
            name: "MDR Mediathek",
            subtitle: "Mitteldeutscher Rundfunk",
            homeURL: URL(string: "https://www.mdr.de/mediathek/")!,
            region: "Mitteldeutschland"
        ),
        MediaLibrary(
            key: "hr",
            name: "hr Mediathek",
            subtitle: "Hessischer Rundfunk",
            homeURL: URL(string: "https://www.hr-fernsehen.de/mediathek/index.html")!,
            region: "Hessen"
        ),
        MediaLibrary(
            key: "rbb",
            name: "rbb Mediathek",
            subtitle: "Rundfunk Berlin-Brandenburg",
            homeURL: URL(string: "https://www.rbb-online.de/fernsehen/")!,
            region: "Berlin-Brandenburg"
        ),
        MediaLibrary(
            key: "radiobremen",
            name: "Radio Bremen",
            subtitle: "Mediathek & Fernsehen",
            homeURL: URL(string: "https://www.radiobremen.de")!,
            region: "Bremen"
        ),
        MediaLibrary(
            key: "sr",
            name: "SR Mediathek",
            subtitle: "Saarländischer Rundfunk",
            homeURL: URL(string: "https://www.sr.de/sr/mediathek/")!,
            region: "Saarland"
        ),
        MediaLibrary(
            key: "kika",
            name: "KiKA",
            subtitle: "Kinderprogramm der ARD/ZDF",
            homeURL: URL(string: "https://www.kika.de")!
        ),
        MediaLibrary(
            key: "funk",
            name: "funk",
            subtitle: "Content-Netzwerk von ARD/ZDF",
            homeURL: URL(string: "https://www.funk.net")!
        ),
        MediaLibrary(
            key: "dw",
            name: "Deutsche Welle",
            subtitle: "Nachrichten & Live-TV weltweit",
            homeURL: URL(string: "https://www.dw.com/de/")!,
            region: "International",
            kind: .livePortal
        ),
        MediaLibrary(
            key: "tagesschau",
            name: "tagesschau",
            subtitle: "Nachrichten der ARD",
            homeURL: URL(string: "https://www.tagesschau.de")!
        ),
        MediaLibrary(
            key: "orf",
            name: "ORF ON",
            subtitle: "Österreichische Mediathek",
            homeURL: URL(string: "https://on.orf.at")!,
            region: "Österreich"
        ),
        MediaLibrary(
            key: "srf",
            name: "SRF Play",
            subtitle: "Schweizer Radio und Fernsehen",
            homeURL: URL(string: "https://www.srf.ch/play")!,
            region: "Schweiz"
        ),
        MediaLibrary(
            key: "archive-feature",
            name: "Internet Archive – Feature Films",
            subtitle: "Gemeinfreie und freie Kinofilme",
            homeURL: URL(string: "https://archive.org/details/feature_films")!,
            region: "International",
            kind: .kino
        ),
        MediaLibrary(
            key: "archive-opensource",
            name: "Internet Archive – Open Source Movies",
            subtitle: "Creative-Commons-Filme",
            homeURL: URL(string: "https://archive.org/details/opensource_movies")!,
            region: "International",
            kind: .kino
        ),
        MediaLibrary(
            key: "publicdomain",
            name: "Public Domain Movies",
            subtitle: "Freie Klassiker & Kurzfilme",
            homeURL: URL(string: "https://publicdomainmovie.net")!,
            region: "International",
            kind: .kino
        ),
        MediaLibrary(
            key: "blender-cloud",
            name: "Blender Open Movies",
            subtitle: "BBB, Sintel, Tears of Steel u. a.",
            homeURL: URL(string: "https://www.blender.org/about/projects/")!,
            region: "International",
            kind: .kino
        )
    ]
}
