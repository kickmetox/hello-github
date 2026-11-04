import Foundation
import Combine

@MainActor
final class ChannelStore: ObservableObject {
    @Published private(set) var channels: [Channel] = []
    @Published var searchText = ""
    @Published var selectedCategory = "Alle"
    @Published var isLoadingPlaylist = false
    @Published var statusMessage: String?
    @Published var playlistURLString = ""

    private let favoritesKey = "freitv.favorites"
    private let customChannelsKey = "freitv.customChannels"

    init() {
        reload()
    }

    var categories: [String] {
        let names = Set(channels.map(\.category))
        return ["Alle"] + names.sorted()
    }

    var filteredChannels: [Channel] {
        channels.filter { channel in
            let matchesCategory = selectedCategory == "Alle" || channel.category == selectedCategory
            let matchesSearch: Bool
            if searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                matchesSearch = true
            } else {
                let query = searchText.lowercased()
                matchesSearch =
                    channel.name.lowercased().contains(query)
                    || channel.category.lowercased().contains(query)
                    || channel.country.lowercased().contains(query)
            }
            return matchesCategory && matchesSearch
        }
    }

    var favoriteChannels: [Channel] {
        channels.filter(\.isFavorite)
    }

    func reload() {
        let favorites = loadFavoriteIDs()
        var merged = ChannelCatalog.builtIn
        merged.append(contentsOf: loadCustomChannels())

        channels = merged.map { channel in
            var copy = channel
            copy.isFavorite = favorites.contains(channel.id.uuidString) || favorites.contains(channel.streamURL.absoluteString)
            return copy
        }
    }

    func toggleFavorite(_ channel: Channel) {
        guard let index = channels.firstIndex(where: { $0.id == channel.id }) else { return }
        channels[index].isFavorite.toggle()
        persistFavorites()
    }

    func loadPlaylist(from urlString: String) async {
        let trimmed = urlString.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed), url.scheme == "http" || url.scheme == "https" else {
            statusMessage = "Ungültige Playlist-URL."
            return
        }

        isLoadingPlaylist = true
        statusMessage = nil
        defer { isLoadingPlaylist = false }

        do {
            let (data, response) = try await URLSession.shared.data(from: url)
            if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
                statusMessage = "Playlist nicht erreichbar (HTTP \(http.statusCode))."
                return
            }
            guard let text = String(data: data, encoding: .utf8) ?? String(data: data, encoding: .isoLatin1) else {
                statusMessage = "Playlist konnte nicht gelesen werden."
                return
            }

            let parsed = M3UParser.parse(text)
            guard !parsed.isEmpty else {
                statusMessage = "Keine Kanäle in der Playlist gefunden."
                return
            }

            saveCustomChannels(parsed)
            playlistURLString = trimmed
            reload()
            statusMessage = "\(parsed.count) Kanäle geladen."
        } catch {
            statusMessage = "Fehler: \(error.localizedDescription)"
        }
    }

    func clearCustomPlaylist() {
        UserDefaults.standard.removeObject(forKey: customChannelsKey)
        reload()
        statusMessage = "Eigene Playlist entfernt. Demo-Kanäle bleiben."
    }

    private func persistFavorites() {
        let ids = channels.filter(\.isFavorite).map(\.id.uuidString)
        UserDefaults.standard.set(ids, forKey: favoritesKey)
    }

    private func loadFavoriteIDs() -> Set<String> {
        Set(UserDefaults.standard.stringArray(forKey: favoritesKey) ?? [])
    }

    private func saveCustomChannels(_ channels: [Channel]) {
        guard let data = try? JSONEncoder().encode(channels) else { return }
        UserDefaults.standard.set(data, forKey: customChannelsKey)
    }

    private func loadCustomChannels() -> [Channel] {
        guard let data = UserDefaults.standard.data(forKey: customChannelsKey),
              let decoded = try? JSONDecoder().decode([Channel].self, from: data) else {
            return []
        }
        return decoded
    }
}
