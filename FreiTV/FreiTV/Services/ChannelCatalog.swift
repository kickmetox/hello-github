import Foundation

enum ChannelCatalog {
    /// Live- und Demo-Kanäle mit frei nutzbaren Streams.
    static let builtIn: [Channel] = [
        Channel(
            key: "dw-en",
            name: "DW English",
            streamURL: URL(string: "https://dwamdstream102.akamaized.net/hls/live/2015525/dwstream102/index.m3u8")!,
            category: "Nachrichten",
            country: "International",
            nowPlaying: "DW News Live"
        ),
        Channel(
            key: "dw-es",
            name: "DW Español",
            streamURL: URL(string: "https://dwamdstream103.akamaized.net/hls/live/2015530/dwstream103/index.m3u8")!,
            category: "Nachrichten",
            country: "International",
            nowPlaying: "Noticias en vivo"
        ),
        Channel(
            key: "dw-ar",
            name: "DW Arabic",
            streamURL: URL(string: "https://dwamdstream104.akamaized.net/hls/live/2015526/dwstream104/index.m3u8")!,
            category: "Nachrichten",
            country: "International",
            nowPlaying: "البث المباشر"
        ),
        Channel(
            key: "akamai-live",
            name: "Akamai Live Test",
            streamURL: URL(string: "https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8")!,
            category: "Live",
            country: "International",
            nowPlaying: "Test Live Loop"
        ),
        Channel(
            key: "bbb-hls",
            name: "Big Buck Bunny (HLS)",
            streamURL: URL(string: "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8")!,
            category: "Demo",
            country: "International",
            nowPlaying: "Open Movie"
        ),
        Channel(
            key: "mux-001",
            name: "Mux Test 001",
            streamURL: URL(string: "https://test-streams.mux.dev/test_001/stream.m3u8")!,
            category: "Demo",
            country: "International",
            nowPlaying: "HLS Demo"
        ),
        Channel(
            key: "apple-bipbop",
            name: "Apple BipBop",
            streamURL: URL(string: "https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8")!,
            category: "Demo",
            country: "USA",
            nowPlaying: "Multi-Bitrate Sample"
        ),
        Channel(
            key: "apple-adv",
            name: "Apple HLS Advanced",
            streamURL: URL(string: "https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8")!,
            category: "Demo",
            country: "USA",
            nowPlaying: "fMP4 Sample"
        ),
        Channel(
            key: "tos",
            name: "Tears of Steel",
            streamURL: URL(string: "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8")!,
            category: "Film",
            country: "International",
            nowPlaying: "Open Movie"
        )
    ]
}
