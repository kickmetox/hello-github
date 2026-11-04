import SwiftUI

struct ProgramGuideView: View {
    @ObservedObject var store: MediaStore

    private var visibleRows: [(String, [ProgramEntry])] {
        let query = store.searchText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return store.programRows.compactMap { channelName, entries in
            let filtered: [ProgramEntry]
            if query.isEmpty {
                filtered = entries
            } else {
                filtered = entries.filter {
                    $0.title.lowercased().contains(query)
                        || $0.synopsis.lowercased().contains(query)
                        || $0.channelName.lowercased().contains(query)
                        || channelName.lowercased().contains(query)
                }
            }
            guard !filtered.isEmpty else { return nil }
            return (channelName, filtered)
        }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 18) {
                    header

                    ForEach(visibleRows, id: \.0) { channelName, entries in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(channelName)
                                .font(.headline)
                                .padding(.horizontal)

                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(alignment: .top, spacing: 12) {
                                    ForEach(entries) { entry in
                                        programCard(entry)
                                    }
                                }
                                .padding(.horizontal)
                            }
                        }
                    }
                }
                .padding(.vertical)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Programm")
            .searchable(text: $store.searchText, prompt: "Programm suchen")
            .refreshable { store.reload() }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Jetzt im freien TV")
                .font(.title2.bold())
            Text("Durchscrollbare Programminfos wie im Fernseher – Live, Mediathek und freies Kino.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal)
    }

    private func programCard(_ entry: ProgramEntry) -> some View {
        NavigationLink {
            destination(for: entry)
        } label: {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(entry.timeLabel)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(entry.isNow ? Color.white : Color.secondary)
                    Spacer()
                    if entry.isNow {
                        Text("JETZT")
                            .font(.caption2.bold())
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.red, in: Capsule())
                            .foregroundStyle(.white)
                    }
                }

                Text(entry.title)
                    .font(.headline)
                    .foregroundStyle(entry.isNow ? .white : .primary)
                    .lineLimit(2)

                Text(entry.synopsis)
                    .font(.caption)
                    .foregroundStyle(entry.isNow ? Color.white.opacity(0.85) : Color.secondary)
                    .lineLimit(4)

                Text(entry.category)
                    .font(.caption2)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(
                        entry.isNow ? Color.white.opacity(0.2) : Color(.secondarySystemFill),
                        in: Capsule()
                    )
                    .foregroundStyle(entry.isNow ? .white : .secondary)
            }
            .padding(14)
            .frame(width: 260, alignment: .leading)
            .background {
                RoundedRectangle(cornerRadius: 16)
                    .fill(cardBackground(isNow: entry.isNow))
            }
        }
        .buttonStyle(.plain)
    }

    private func cardBackground(isNow: Bool) -> AnyShapeStyle {
        if isNow {
            return AnyShapeStyle(
                LinearGradient(
                    colors: [
                        Color(red: 0.05, green: 0.35, blue: 0.42),
                        Color(red: 0.08, green: 0.12, blue: 0.28)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
        }
        return AnyShapeStyle(Color(.secondarySystemGroupedBackground))
    }

    @ViewBuilder
    private func destination(for entry: ProgramEntry) -> some View {
        if let playable = entry.playableURL {
            StreamPlayerView(title: entry.title, url: playable)
        } else if let deepLink = entry.deepLink {
            WebBrowserView(title: entry.channelName, url: deepLink)
        } else {
            Text("Keine Wiedergabe verfügbar.")
        }
    }
}
