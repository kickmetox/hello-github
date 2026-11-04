import Foundation
import Combine

@MainActor
final class MediaStore: ObservableObject {
    @Published private(set) var channels: [Channel] = []
    @Published private(set) var libraries: [MediaLibrary] = []
    @Published private(set) var movies: [Movie] = []
    @Published private(set) var programEntries: [ProgramEntry] = []
    @Published private(set) var favorites: [FavoriteItem] = []

    @Published var searchText = ""
    @Published var selectedCategory = "Alle"
    @Published var libraryFilter = "Alle"
    @Published var movieGenreFilter = "Alle"
    @Published var favoriteSortMode: FavoriteSortMode = .manual
    @Published var isLoadingPlaylist = false
    @Published var statusMessage: String?
    @Published var playlistURLString = ""

    private let favoritesKey = "freitv.favorites.v2"
    private let customChannelsKey = "freitv.customChannels"
    private let sortModeKey = "freitv.favoriteSortMode"

    init() {
        if let raw = UserDefaults.standard.string(forKey: sortModeKey),
           let mode = FavoriteSortMode(rawValue: raw) {
            favoriteSortMode = mode
        }
        reload()
    }

    var categories: [String] {
        ["Alle"] + Set(channels.map(\.category)).sorted()
    }

    var libraryFilters: [String] {
        ["Alle"] + Set(libraries.map(\.kind.rawValue)).sorted()
    }

    var movieGenres: [String] {
        ["Alle"] + Set(movies.map(\.genre)).sorted()
    }

    var filteredChannels: [Channel] {
        channels.filter { channel in
            let matchesCategory = selectedCategory == "Alle" || channel.category == selectedCategory
            return matchesCategory && matchesSearch(channel.name, channel.category, channel.country, channel.nowPlaying)
        }
    }

    var filteredLibraries: [MediaLibrary] {
        libraries.filter { library in
            let matchesKind = libraryFilter == "Alle" || library.kind.rawValue == libraryFilter
            return matchesKind && matchesSearch(library.name, library.subtitle, library.region, library.kind.rawValue)
        }
    }

    var filteredMovies: [Movie] {
        movies.filter { movie in
            let matchesGenre = movieGenreFilter == "Alle" || movie.genre == movieGenreFilter
            return matchesGenre && matchesSearch(movie.title, movie.genre, movie.license, movie.synopsis)
        }
    }

    var sortedFavorites: [FavoriteItem] {
        switch favoriteSortMode {
        case .manual:
            return favorites.sorted { $0.sortIndex < $1.sortIndex }
        case .name:
            return favorites.sorted {
                $0.title.localizedCaseInsensitiveCompare($1.title) == .orderedAscending
            }
        case .newest:
            return favorites.sorted { $0.addedAt > $1.addedAt }
        case .kind:
            return favorites.sorted {
                if $0.kind.rawValue == $1.kind.rawValue {
                    return $0.title.localizedCaseInsensitiveCompare($1.title) == .orderedAscending
                }
                return $0.kind.rawValue < $1.kind.rawValue
            }
        }
    }

    var programRows: [(String, [ProgramEntry])] {
        ProgramGuideService.groupedByChannel(programEntries)
    }

    func reload() {
        let favoriteIDs = Set(loadFavorites().map(\.id))

        var mergedChannels = ChannelCatalog.builtIn
        mergedChannels.append(contentsOf: loadCustomChannels())
        channels = mergedChannels.map { channel in
            var copy = channel
            copy.isFavorite = favoriteIDs.contains(channel.id)
            return copy
        }

        libraries = MediaLibraryCatalog.all.map { library in
            var copy = library
            copy.isFavorite = favoriteIDs.contains(library.id)
            return copy
        }

        movies = MovieCatalog.all.map { movie in
            var copy = movie
            copy.isFavorite = favoriteIDs.contains(movie.id)
            return copy
        }

        favorites = loadFavorites()
        programEntries = ProgramGuideService.buildGuide(
            channels: channels,
            libraries: libraries,
            movies: movies
        )
    }

    func setFavoriteSortMode(_ mode: FavoriteSortMode) {
        favoriteSortMode = mode
        UserDefaults.standard.set(mode.rawValue, forKey: sortModeKey)
    }

    func toggleFavorite(channel: Channel) {
        if let existing = favorites.first(where: { $0.id == channel.id }) {
            removeFavorite(existing)
        } else {
            addFavorite(
                FavoriteItem(
                    id: channel.id,
                    kind: .channel,
                    title: channel.name,
                    subtitle: "\(channel.category) · Live",
                    sortIndex: nextSortIndex(),
                    channelURL: channel.streamURL
                )
            )
        }
    }

    func toggleFavorite(library: MediaLibrary) {
        if let existing = favorites.first(where: { $0.id == library.id }) {
            removeFavorite(existing)
        } else {
            addFavorite(
                FavoriteItem(
                    id: library.id,
                    kind: .mediathek,
                    title: library.name,
                    subtitle: library.subtitle,
                    sortIndex: nextSortIndex(),
                    openURL: library.homeURL
                )
            )
        }
    }

    func toggleFavorite(movie: Movie) {
        if let existing = favorites.first(where: { $0.id == movie.id }) {
            removeFavorite(existing)
        } else {
            addFavorite(
                FavoriteItem(
                    id: movie.id,
                    kind: .movie,
                    title: movie.title,
                    subtitle: movie.genre,
                    sortIndex: nextSortIndex(),
                    openURL: movie.infoURL,
                    movieStreamURL: movie.streamURL
                )
            )
        }
    }

    func moveFavorites(from source: IndexSet, to destination: Int) {
        var manual = favorites.sorted { $0.sortIndex < $1.sortIndex }
        manual.move(fromOffsets: source, toOffset: destination)
        for index in manual.indices {
            manual[index].sortIndex = index
        }
        favorites = manual
        persistFavorites()
        favoriteSortMode = .manual
        UserDefaults.standard.set(FavoriteSortMode.manual.rawValue, forKey: sortModeKey)
        reloadFavoriteFlags()
    }

    func removeFavorite(_ item: FavoriteItem) {
        favorites.removeAll { $0.id == item.id }
        renumberSortIndices()
        persistFavorites()
        reloadFavoriteFlags()
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

    private func addFavorite(_ item: FavoriteItem) {
        favorites.append(item)
        persistFavorites()
        reloadFavoriteFlags()
    }

    private func nextSortIndex() -> Int {
        (favorites.map(\.sortIndex).max() ?? -1) + 1
    }

    private func renumberSortIndices() {
        var manual = favorites.sorted { $0.sortIndex < $1.sortIndex }
        for index in manual.indices {
            manual[index].sortIndex = index
        }
        favorites = manual
    }

    private func reloadFavoriteFlags() {
        let ids = Set(favorites.map(\.id))
        channels = channels.map {
            var copy = $0
            copy.isFavorite = ids.contains($0.id)
            return copy
        }
        libraries = libraries.map {
            var copy = $0
            copy.isFavorite = ids.contains($0.id)
            return copy
        }
        movies = movies.map {
            var copy = $0
            copy.isFavorite = ids.contains($0.id)
            return copy
        }
    }

    private func matchesSearch(_ fields: String?...) -> Bool {
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !query.isEmpty else { return true }
        return fields.compactMap { $0?.lowercased() }.contains { $0.contains(query) }
    }

    private func persistFavorites() {
        guard let data = try? JSONEncoder().encode(favorites) else { return }
        UserDefaults.standard.set(data, forKey: favoritesKey)
    }

    private func loadFavorites() -> [FavoriteItem] {
        guard let data = UserDefaults.standard.data(forKey: favoritesKey),
              let decoded = try? JSONDecoder().decode([FavoriteItem].self, from: data) else {
            return []
        }
        return decoded
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
