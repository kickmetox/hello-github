import Foundation

enum MovieCatalog {
    /// Freie Filme (Creative Commons / Public Domain / offene Demo-Streams).
    static let all: [Movie] = [
        Movie(
            key: "bbb",
            title: "Big Buck Bunny",
            year: 2008,
            durationMinutes: 10,
            genre: "Animation",
            synopsis: "Blender-Open-Movie: Ein friedliches Kaninchen wehrt sich gegen freche Nager.",
            license: "CC BY 3.0",
            streamURL: URL(string: "https://archive.org/download/BigBuckBunny_124/Content/big_buck_bunny_720p_surround.mp4")!,
            infoURL: URL(string: "https://peach.blender.org")!
        ),
        Movie(
            key: "elephants-dream",
            title: "Elephants Dream",
            year: 2006,
            durationMinutes: 11,
            genre: "Animation",
            synopsis: "Erstes Blender-Open-Movie: Proog und Emo in einer surrealen Maschinenwelt.",
            license: "CC BY 2.5",
            streamURL: URL(string: "https://archive.org/download/ElephantsDream/ed_hd.mp4")!,
            infoURL: URL(string: "https://orange.blender.org")!
        ),
        Movie(
            key: "tears-of-steel",
            title: "Tears of Steel",
            year: 2012,
            durationMinutes: 12,
            genre: "Sci-Fi",
            synopsis: "Open Movie Project: Roboter und Menschen im zerstörten Amsterdam.",
            license: "CC BY 3.0",
            streamURL: URL(string: "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8")!,
            infoURL: URL(string: "https://mango.blender.org")!
        ),
        Movie(
            key: "mux-demo",
            title: "Mux HLS Showcase",
            year: 2020,
            durationMinutes: 6,
            genre: "Demo",
            synopsis: "Öffentlicher HLS-Teststream – ideal zum Prüfen des Players.",
            license: "Demo / Test",
            streamURL: URL(string: "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8")!
        ),
        Movie(
            key: "apple-bipbop",
            title: "Apple BipBop Sample",
            year: 2016,
            durationMinutes: 30,
            genre: "Demo",
            synopsis: "Apples öffentlicher HLS-Beispielstream mit mehreren Qualitäten.",
            license: "Demo / Test",
            streamURL: URL(string: "https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8")!
        ),
        Movie(
            key: "archive-kino",
            title: "Freies Kino – Feature Films",
            year: 0,
            durationMinutes: 0,
            genre: "Kino",
            synopsis: "Sammlung gemeinfreier Kinofilme beim Internet Archive. In der Mediathek-Ansicht browsen und abspielen.",
            license: "Public Domain / verschieden",
            infoURL: URL(string: "https://archive.org/details/feature_films")!
        ),
        Movie(
            key: "opensource-movies",
            title: "Open Source Movies",
            year: 0,
            durationMinutes: 0,
            genre: "Kino",
            synopsis: "Creative-Commons- und Open-Source-Filme beim Internet Archive.",
            license: "Creative Commons / Open",
            infoURL: URL(string: "https://archive.org/details/opensource_movies")!
        ),
        Movie(
            key: "public-domain-net",
            title: "Public Domain Movie Night",
            year: 0,
            durationMinutes: 0,
            genre: "Klassiker",
            synopsis: "Portal mit gemeinfreien Spielfilmen und Kurzfilmen.",
            license: "Public Domain",
            infoURL: URL(string: "https://publicdomainmovie.net")!
        )
    ]
}
