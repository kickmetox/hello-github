import SwiftUI

struct FavoritesView: View {
    @ObservedObject var store: MediaStore
    @State private var editMode: EditMode = .inactive

    var body: some View {
        NavigationStack {
            Group {
                if store.sortedFavorites.isEmpty {
                    ContentUnavailableView(
                        "Keine Favoriten",
                        systemImage: "star",
                        description: Text("Sterne bei Kanälen, Mediatheken oder Filmen setzen.")
                    )
                } else {
                    List {
                        ForEach(store.sortedFavorites) { item in
                            NavigationLink {
                                destination(for: item)
                            } label: {
                                HStack(spacing: 12) {
                                    Image(systemName: icon(for: item.kind))
                                        .frame(width: 32, height: 32)
                                        .foregroundStyle(Color(red: 0.15, green: 0.72, blue: 0.78))
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(item.title).font(.headline)
                                        Text("\(label(for: item.kind)) · \(item.subtitle)")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                        }
                        .onDelete { indexSet in
                            let items = store.sortedFavorites
                            for index in indexSet {
                                store.removeFavorite(items[index])
                            }
                        }
                        .onMove(perform: store.favoriteSortMode == .manual ? store.moveFavorites : nil)
                    }
                    .environment(\.editMode, $editMode)
                }
            }
            .navigationTitle("Favoriten")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Menu {
                        ForEach(FavoriteSortMode.allCases) { mode in
                            Button {
                                store.setFavoriteSortMode(mode)
                            } label: {
                                if store.favoriteSortMode == mode {
                                    Label(mode.rawValue, systemImage: "checkmark")
                                } else {
                                    Text(mode.rawValue)
                                }
                            }
                        }
                    } label: {
                        Label("Sortierung", systemImage: "arrow.up.arrow.down")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    if store.favoriteSortMode == .manual && !store.sortedFavorites.isEmpty {
                        EditButton()
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func destination(for item: FavoriteItem) -> some View {
        switch item.kind {
        case .channel:
            if let url = item.channelURL {
                StreamPlayerView(title: item.title, url: url)
            } else {
                Text("Kanal nicht verfügbar.")
            }
        case .mediathek:
            if let url = item.openURL {
                WebBrowserView(title: item.title, url: url)
            } else {
                Text("Mediathek nicht verfügbar.")
            }
        case .movie:
            if let stream = item.movieStreamURL {
                StreamPlayerView(title: item.title, url: stream)
            } else if let url = item.openURL {
                WebBrowserView(title: item.title, url: url)
            } else {
                Text("Film nicht verfügbar.")
            }
        }
    }

    private func icon(for kind: FavoriteKind) -> String {
        switch kind {
        case .channel: return "tv"
        case .mediathek: return "play.rectangle.on.rectangle"
        case .movie: return "film"
        }
    }

    private func label(for kind: FavoriteKind) -> String {
        switch kind {
        case .channel: return "Kanal"
        case .mediathek: return "Mediathek"
        case .movie: return "Film"
        }
    }
}
