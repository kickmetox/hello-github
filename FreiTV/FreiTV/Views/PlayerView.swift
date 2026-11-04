import SwiftUI

/// Kompatibilitätsschicht für bestehende Navigation auf Channel-Basis.
struct PlayerView: View {
    let channel: Channel

    var body: some View {
        StreamPlayerView(title: channel.name, url: channel.streamURL)
    }
}
