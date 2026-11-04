import Foundation

enum ChannelCatalog {
    /// Eingebaute Demo-/Teststreams mit frei nutzbaren Inhalten (öffentliche HLS-Test-Streams).
    /// Echte Sender-Playlists bitte selbst über „Playlist laden“ hinzufügen – nur rechtlich erlaubte Quellen.
    static let builtIn: [Channel] = [
        Channel(
            name: "Big Buck Bunny",
            streamURL: URL(string: "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8")!,
            category: "Demo",
            country: "International"
        ),
        Channel(
            name: "Mux Test 001",
            streamURL: URL(string: "https://test-streams.mux.dev/test_001/stream.m3u8")!,
            category: "Demo",
            country: "International"
        ),
        Channel(
            name: "Apple BipBop",
            streamURL: URL(string: "https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8")!,
            category: "Demo",
            country: "USA"
        ),
        Channel(
            name: "Apple HLS Advanced",
            streamURL: URL(string: "https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8")!,
            category: "Demo",
            country: "USA"
        ),
        Channel(
            name: "Tears of Steel",
            streamURL: URL(string: "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8")!,
            category: "Film",
            country: "International"
        ),
        Channel(
            name: "Akamai Live Test",
            streamURL: URL(string: "https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8")!,
            category: "Live",
            country: "International"
        )
    ]
}
