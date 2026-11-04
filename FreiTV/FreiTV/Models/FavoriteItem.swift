import Foundation

enum FavoriteKind: String, Codable, CaseIterable {
    case channel
    case mediathek
    case movie
}

struct FavoriteItem: Identifiable, Hashable, Codable {
    let id: UUID
    var kind: FavoriteKind
    var title: String
    var subtitle: String
    var addedAt: Date
    var sortIndex: Int
    var channelURL: URL?
    var openURL: URL?
    var movieStreamURL: URL?

    init(
        id: UUID,
        kind: FavoriteKind,
        title: String,
        subtitle: String,
        addedAt: Date = Date(),
        sortIndex: Int = 0,
        channelURL: URL? = nil,
        openURL: URL? = nil,
        movieStreamURL: URL? = nil
    ) {
        self.id = id
        self.kind = kind
        self.title = title
        self.subtitle = subtitle
        self.addedAt = addedAt
        self.sortIndex = sortIndex
        self.channelURL = channelURL
        self.openURL = openURL
        self.movieStreamURL = movieStreamURL
    }
}

enum FavoriteSortMode: String, CaseIterable, Identifiable {
    case manual = "Manuell"
    case name = "Name"
    case newest = "Neueste"
    case kind = "Typ"

    var id: String { rawValue }
}
