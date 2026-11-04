import SwiftUI

struct ChannelRow: View {
    let channel: Channel
    let onFavorite: () -> Void

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 10)
                    .fill(
                        LinearGradient(
                            colors: [Color(red: 0.05, green: 0.35, blue: 0.42), Color(red: 0.08, green: 0.12, blue: 0.28)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 52, height: 52)

                Image(systemName: "play.tv.fill")
                    .foregroundStyle(.cyan)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(channel.name)
                    .font(.headline)
                    .foregroundStyle(.primary)
                    .lineLimit(1)

                if let nowPlaying = channel.nowPlaying {
                    Text(nowPlaying)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

                Text("\(channel.category) · \(channel.country)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer(minLength: 8)

            Button(action: onFavorite) {
                Image(systemName: channel.isFavorite ? "star.fill" : "star")
                    .foregroundStyle(channel.isFavorite ? .yellow : .secondary)
            }
            .buttonStyle(.plain)
            .accessibilityLabel(channel.isFavorite ? "Favorit entfernen" : "Als Favorit markieren")
        }
        .padding(.vertical, 4)
    }
}
